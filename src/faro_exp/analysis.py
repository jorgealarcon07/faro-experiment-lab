import platform
import subprocess
from importlib.metadata import version

import pandas as pd
from psycopg.types.json import Jsonb

from . import database as db
from .inference import diagnostics, srm
from .io import clock, encoded, load_bundle, protocol, sha, validate_document


def arm_counts(series):
    return {arm: int(series.eq(arm).sum()) for arm in ["C", "T"]}


def assess(itt, integrity, cut, p):
    end = itt.assigned_at + pd.Timedelta(days=p["horizon_days"])
    final = end.max() + pd.Timedelta(days=p["grace_days"])
    closed = cut >= final
    if cut < itt.assigned_at.max():
        raise ValueError("El corte es anterior a la inscripción")
    joined = (itt.outcome_rows == 1) & (itt.recorded_rows == 1)
    arm = arm_counts(itt.variant)
    logged = {a: int(itt.loc[itt.logged_arm == a, "recorded_rows"].sum()) for a in ["C", "T"]}
    complete = arm_counts(itt.loc[joined, "variant"])

    def ratio(count):
        return srm(count["T"], count["C"], p["allocation"])

    flags = []

    def flag(condition, code):
        if condition:
            flags.append(code)

    flag(integrity["orphan_rows"] > 0, "orphan_account")
    flag(integrity["event_id_conflicts"] > 0, "conflicting_event_id")
    flag((itt.recorded_rows != 1).any(), "assignment_count")
    flag(
        (
            (itt.recorded_rows > 0)
            & (
                (itt.variant != itt.logged_arm)
                | (itt.probability != itt.logged_probability)
                | (itt.logged_time != itt.assigned_at)
            )
        ).any(),
        "assignment_changed",
    )
    flag(min(arm.values()) == 0, "empty_arm")
    flag(ratio(arm) < p["srm_alpha"], "srm_assignment")
    flag(ratio(logged) < p["srm_alpha"], "srm_recorded")
    flag((itt.outcome_rows > 1).any(), "duplicate_outcome")
    visible = itt.outcome_rows > 0
    flag(
        (visible & ((itt.window_end != end) | (itt.available_at < itt.window_end))).any(),
        "outcome_clock",
    )
    flag(
        (itt.event_clock | (itt.first_attempt < itt.assigned_at) | (itt.last_attempt > end)).any(),
        "event_clock",
    )
    flag(((itt.variant == "C") & (itt.attempts > 0)).any(), "control_exposed")
    flag((itt.attempts > 1).any(), "duplicate_attempt")
    if closed:
        flag((itt.outcome_rows == 0).any(), "missing_mature_outcome")
        flag(((itt.variant == "T") & (itt.attempts != 1)).any(), "attempt_count")
        flag(ratio(complete) < p["srm_alpha"], "srm_analytic_join")
    checks = {
        **integrity,
        "final_at": final.isoformat(),
        "closed": bool(closed),
        "registered": arm,
        "recorded": logged,
        "complete_join": complete,
        "srm_p_registered": ratio(arm),
        "srm_p_recorded": ratio(logged),
        "srm_p_join": ratio(complete) if closed else None,
        "missing_outcomes": int((itt.outcome_rows == 0).sum()),
        "unique_attempts": int(itt.attempts.sum()),
    }
    if flags:
        return "invalid", flags, checks, None, None, []
    if not closed:
        return "pending", ["horizon_or_arrival_grace_open"], checks, None, None, []
    stats, comparison, groups = diagnostics(itt, p)
    failed = [k for k, v in stats["gates"].items() if not v]
    return (
        "hold" if failed else "ship",
        failed or ["all_prespecified_gates_pass"],
        checks,
        stats,
        comparison,
        groups,
    )


def git_sha():
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=3
        )
        return proc.stdout.strip() if proc.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def analyze(conn, folder, as_of, parent=None):
    m, frames = load_bundle(folder, ["recorded", "outcome", "event"])
    p = protocol()
    cut = clock(as_of)
    experiment = m["experiment_id"]
    with conn.transaction():
        db.lock(conn, "evaluate:" + experiment)
        batch, seed = db.ingest(conn, m, frames)
        run = sha(
            encoded(
                [experiment, m["protocol_sha256"], batch, cut.isoformat(), parent, "analysis-v1"]
            )
        )
        if parent:
            ancestor = conn.execute(
                "SELECT experiment_id,as_of,state FROM faro_exp.run WHERE run_id=%s", (parent,)
            ).fetchone()
            if (
                not ancestor
                or ancestor[0] != experiment
                or ancestor[1] > cut
                or ancestor[2] not in ("invalid", "pending")
            ):
                raise ValueError(
                    "El antecedente debe ser pending/invalid del mismo experimento y anterior o simultáneo"
                )
        old = conn.execute(
            "SELECT record,manifest FROM faro_exp.run WHERE run_id=%s", (run,)
        ).fetchone()
        if old:
            return old[0], old[1], "replay"
        itt, quality = db.analytic_table(conn, experiment, batch, cut)
        state, reasons, checks, stats, comparison, segments = assess(itt, quality, cut, p)
        table_hash = db.fingerprint(itt)
        if state in ("ship", "hold"):
            sealed = conn.execute(
                """SELECT manifest->>'itt_sha256' FROM faro_exp.run WHERE experiment_id=%s
                AND state IN ('ship','hold') LIMIT 1""",
                (experiment,),
            ).fetchone()
            if sealed and sealed[0] != table_hash:
                raise ValueError("El análisis final ya está sellado para esta cohorte")
        record = {
            "run_id": run,
            "experiment_id": experiment,
            "state": state,
            "reasons": reasons,
            "as_of": cut.isoformat(),
            "checks": checks,
            "estimates": stats,
            "comparison": comparison,
            "segments": segments,
            "role": "operaciones simuladas",
        }
        manifest = {
            "run_id": run,
            "git_sha": git_sha(),
            "contract_version": "1.0",
            "dataset_sha256": batch,
            "source_namespace": p["namespace"],
            "data_kind": "synthetic",
            "seed": seed,
            "rows": len(itt),
            "as_of": cut.isoformat(),
            "enrollment_sha256": m["enrollment_sha256"],
            "protocol_sha256": m["protocol_sha256"],
            "parent_run": parent,
            "itt_sha256": table_hash,
            "environment": {
                "python": platform.python_version(),
                "statsmodels": version("statsmodels"),
                "scipy": version("scipy"),
                "numpy": version("numpy"),
                "timezone": "UTC",
            },
        }
        validate_document("decision_record", record)
        validate_document("run_manifest", manifest)
        conn.execute(
            "INSERT INTO faro_exp.run(run_id,experiment_id,batch_hash,as_of,parent_run,state,record,manifest) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",
            (run, experiment, batch, cut, parent, state, Jsonb(record), Jsonb(manifest)),
        )
    return record, manifest, "published"
