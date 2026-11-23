import threading
import time
from pathlib import Path

import psutil

from . import database as db
from .analysis import analyze
from .calibration import calibrate
from .io import file_hash, log, protocol, read, save, validate_document
from .report import render
from .report_language import REPORT_FILES
from .simulator import enroll, observe

EARLY = "2026-01-08T00:00:00Z"
FINAL = "2026-01-17T00:00:00Z"
SCENARIOS = ("aa", "benefit", "harm", "complaint", "mde")
ARTIFACTS = (
    "cases.json",
    "manifests.json",
    "trace.json",
    "monte_carlo.json",
    "replicas.csv",
    "protocol.json",
    "decisions.csv",
    "index.html",
    "resources.json",
    "verification.json",
)


def demo(out, inputs):
    out, inputs = Path(out), Path(inputs)
    for folder, kind in [(out, "report"), (inputs, "inputs")]:
        folder.mkdir(parents=True, exist_ok=True)
        marker = folder / "owner.json"
        if any(folder.iterdir()) and (not marker.exists() or read(marker) != {"faro_exp": kind}):
            raise ValueError("Se requiere una carpeta propia de Faro o vacía")
        save(marker, {"faro_exp": kind})
    process = psutil.Process()
    peak = [process.memory_info().rss]
    stop = threading.Event()

    def sample():
        while not stop.wait(0.1):
            peak[0] = max(peak[0], process.memory_info().rss)

    worker = threading.Thread(target=sample, daemon=True)
    worker.start()
    start = time.perf_counter()
    try:
        _demo(out, inputs)
    finally:
        stop.set()
        worker.join()
    save(
        out / "resources.json",
        {
            "elapsed_seconds": time.perf_counter() - start,
            "peak_python_rss_mib": peak[0] / 2**20,
            "sampling_seconds": 0.1,
            "excludes": "PostgreSQL server, installation, capture and packaging",
            "input_bytes": sum(f.stat().st_size for f in inputs.rglob("*") if f.is_file()),
        },
    )
    save(out / "inventory.json", {name: file_hash(out / name) for name in ARTIFACTS})
    validate(out)


def _demo(out, inputs):
    cases, manifests = {}, {}

    def run(conn, label, folder, cut=FINAL, parent=None):
        r, m, action = analyze(conn, folder, cut, parent)
        cases[label], manifests[label] = r, m
        log("evaluation", case=label, state=r["state"], storage=action)
        return r["run_id"]

    with db.connect() as conn:
        db.initialize(conn)
        for name in SCENARIOS:
            root = inputs / name
            registration = root / "enrollment"
            clean = root / "clean"
            enroll(registration, name)
            db.register(conn, registration)
            observe(registration, clean)
            if name != "benefit":
                run(conn, name, clean)
                continue
            early = run(conn, "early", clean, EARLY)
            for fault in ["loss", "switch", "assignment_loss", "clock", "conflict", "duplicates"]:
                observe(registration, root / fault, fault)
            incident = run(conn, "loss", root / "loss", parent=early)
            for fault in ["switch", "assignment_loss", "clock", "conflict"]:
                run(conn, fault, root / fault)
            final = run(conn, name, clean, parent=incident)
            run(conn, "duplicates", root / "duplicates")
            repeat, _, action = analyze(conn, clean, FINAL, incident)
            if action != "replay" or repeat != cases[name]:
                raise RuntimeError("Replay divergente")
            acct = conn.execute(
                """SELECT account_id FROM faro_exp.event WHERE batch_hash=%s AND status='failed'
                                  ORDER BY account_id LIMIT 1""",
                (manifests[name]["dataset_sha256"],),
            ).fetchone()[0]
            save(out / "trace.json", db.trace(conn, final, acct))
        version = conn.execute("SHOW server_version").fetchone()[0]
    if (
        manifests["duplicates"]["itt_sha256"] != manifests["benefit"]["itt_sha256"]
        or cases["duplicates"]["estimates"] != cases["benefit"]["estimates"]
    ):
        raise RuntimeError("Redelivery changed ITT")
    save(out / "cases.json", cases)
    save(out / "manifests.json", manifests)
    save(out / "protocol.json", protocol())
    moment = time.perf_counter()
    mc, replicas = calibrate(protocol())
    save(out / "monte_carlo.json", mc)
    replicas.to_csv(out / "replicas.csv", index=False, lineterminator="\n")
    save(
        out / "verification.json",
        {
            "postgresql": version,
            "duplicated_receipts_same_itt": True,
            "identical_replay": True,
            "monte_carlo_seconds": time.perf_counter() - moment,
            "scenarios": len(SCENARIOS),
            "replicates_total": len(replicas),
            "incident_run": manifests["loss"]["run_id"],
            "corrected_run": manifests["benefit"]["run_id"],
        },
    )
    render(out)


def validate(folder):
    folder = Path(folder)
    hashes = read(folder / "inventory.json")
    if set(hashes) != set(ARTIFACTS) or any(
        file_hash(folder / name) != h for name, h in hashes.items()
    ):
        raise ValueError("Inventario de release alterado")
    records = read(folder / "cases.json")
    manifests = read(folder / "manifests.json")
    for name, r in records.items():
        validate_document("decision_record", r)
        validate_document("run_manifest", manifests[name])
        if r["run_id"] != manifests[name]["run_id"] or (
            (r["state"] in ("invalid", "pending")) != (r["estimates"] is None)
        ):
            raise ValueError("Estado o linaje inconsistente")
    if records["early"]["state"] != "pending" or any(
        records[k]["state"] != "invalid"
        for k in ["loss", "switch", "assignment_loss", "clock", "conflict"]
    ):
        raise ValueError("Un control de calidad no bloqueó el caso sembrado")
    if (
        read(folder / "protocol.json") != protocol()
        or manifests["benefit"]["parent_run"] != records["loss"]["run_id"]
    ):
        raise ValueError("Protocolo o referencia al incidente divergente")
    log("release_validated", cases=len(records), files=len(hashes))


def clean(out):
    out = Path(out)
    if read(out / "owner.json") != {"faro_exp": "report"}:
        raise ValueError("Directorio de reporte incompatible")
    for name in (*ARTIFACTS, REPORT_FILES["en"], "inventory.json", "owner.json"):
        (out / name).unlink(missing_ok=True)
