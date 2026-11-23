"""Verify CLI, concurrency, reader permissions, stable regeneration and SQL totals."""

import argparse
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from psycopg.errors import InsufficientPrivilege

from faro_exp import database as db
from faro_exp.analysis import analyze
from faro_exp.demo import FINAL
from faro_exp.io import file_hash, read, save


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("local/acceptance"))
    args = parser.parse_args()
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    fix = Path("data/fixtures")

    def cli(*parts):
        subprocess.run([sys.executable, "-m", "faro_exp.cli", *map(str, parts)], check=True)

    def submit(_):
        with db.connect() as c:
            return analyze(c, fix / "clean", FINAL)

    tmp = Path(tempfile.mkdtemp(dir=out))
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "--basetemp",
            str(tmp),
            "--junitxml",
            str(out / "tests.xml"),
        ],
        check=True,
    )
    cli("validate")
    cli("register", "--enrollment", fix / "enrollment")
    with ThreadPoolExecutor(2) as pool:
        responses = list(pool.map(submit, range(2)))
    statuses = sorted(entry[2] for entry in responses)
    if statuses != ["published", "replay"] or responses[0][:2] != responses[1][:2]:
        raise RuntimeError("Concurrent retry mismatch; use a fresh dedicated verification database")
    run = responses[0][0]["run_id"]
    cli("trace", "--run", run, "--account", 200, "--out", out / "trace.json")
    trace = read(out / "trace.json")
    assert trace["variant"] == "T" and trace["attempts"] == 1 and trace["delivered"] == 0
    with db.connect() as c:
        c.execute(Path("scripts/access.sql").read_text(encoding="utf8"))
        with c.transaction():
            c.execute("SET LOCAL ROLE faro_exp_reader")
            assert (
                c.execute(
                    "SELECT state FROM faro_exp.decisions WHERE run_id=%s", (run,)
                ).fetchone()[0]
                == "hold"
            )
            try:
                with c.transaction():
                    c.execute("SELECT * FROM faro_exp.outcome LIMIT 1")
            except InsufficientPrivilege:
                denied = True
            else:
                raise RuntimeError("Reader accessed raw outcomes")
        version = c.execute("SHOW server_version").fetchone()[0]
    cli("demo", "--out", out / "report", "--inputs", out / "inputs")
    previous = read("reports/release/manifests.json")
    current = read(out / "report/manifests.json")
    same_tables = all(previous[k]["itt_sha256"] == v["itt_sha256"] for k, v in current.items())
    same_decisions = file_hash(out / "report/cases.json") == file_hash("reports/release/cases.json")
    same_mc = file_hash(out / "report/replicas.csv") == file_hash("reports/release/replicas.csv")
    if not (same_decisions and same_tables and same_mc):
        raise RuntimeError("Reconstructed evidence differs")
    save(
        out / "acceptance.json",
        {
            "postgresql": version,
            "concurrent_submissions": statuses,
            "reader_denied_raw": denied,
            "reader_can_read_decision": True,
            "same_itt_tables": same_tables,
            "same_decisions": same_decisions,
            "same_5000_replicas": same_mc,
            "manual_fixture_run": run,
            "python": sys.version.split()[0],
            "decision_sha256": file_hash(out / "report/cases.json"),
            "monte_carlo_csv_sha256": file_hash(out / "report/replicas.csv"),
            "database_host_mode": "loopback"
            if os.environ.get("PGHOST") == "127.0.0.1"
            else "configured",
        },
    )
    print("Released experiment reproduced", flush=True)


if __name__ == "__main__":
    main()
