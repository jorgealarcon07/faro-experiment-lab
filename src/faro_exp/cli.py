import argparse
import sys
from pathlib import Path

import jsonschema
import psycopg

from . import database as db
from .analysis import analyze
from .io import clock, log, save


def main(argv=None):
    parser = argparse.ArgumentParser(prog="faro-exp")
    subs = parser.add_subparsers(dest="cmd", required=True)
    p = subs.add_parser("enroll")
    p.add_argument(
        "--scenario", choices=["aa", "benefit", "harm", "complaint", "mde"], required=True
    )
    p.add_argument("--n", type=int)
    p.add_argument("--experiment")
    p.add_argument("--out", type=Path, required=True)
    p = subs.add_parser("register")
    p.add_argument("--enrollment", type=Path, required=True)
    p = subs.add_parser("observe")
    p.add_argument("--enrollment", type=Path, required=True)
    p.add_argument("--fault", default="clean")
    p.add_argument("--out", type=Path, required=True)
    p = subs.add_parser("analyze")
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--as-of", required=True)
    p.add_argument("--parent")
    p.add_argument("--out", type=Path, required=True)
    p = subs.add_parser("trace")
    p.add_argument("--run", required=True)
    p.add_argument("--account", type=int, required=True)
    p.add_argument("--out", type=Path, required=True)
    for cmd in ["demo", "validate", "report", "clean", "calibrate", "power"]:
        p = subs.add_parser(cmd)
        p.add_argument(
            "--out",
            type=Path,
            default=Path("reports/release" if cmd in ("validate", "report") else "local/" + cmd),
        )
        if cmd == "demo":
            p.add_argument("--inputs", type=Path, default=Path("local/inputs"))
        if cmd == "clean":
            p.add_argument("--confirm", action="store_true", required=True)
    a = parser.parse_args(argv)
    try:
        if a.cmd in ("enroll", "observe"):
            from .simulator import enroll, observe

            if a.cmd == "enroll":
                m = enroll(a.out, a.scenario, a.n, a.experiment)
            else:
                m = observe(a.enrollment, a.out, a.fault)
            log(a.cmd, experiment=m["experiment_id"])
        elif a.cmd in ("register", "analyze", "trace"):
            if a.cmd == "analyze":
                a.as_of = clock(a.as_of)
            with db.connect() as conn:
                if a.cmd == "register":
                    db.initialize(conn)
                    log("assignment", status=db.register(conn, a.enrollment))
                elif a.cmd == "trace":
                    save(a.out, db.trace(conn, a.run, a.account))
                else:
                    record, manifest, action = analyze(conn, a.input, a.as_of, a.parent)
                    save(a.out, {"record": record, "manifest": manifest})
                    log("decision", state=record["state"], run_id=record["run_id"], storage=action)
        elif a.cmd == "report":
            from .report import render

            render(a.out)
        elif a.cmd in ("power", "calibrate"):
            from .inference import power_plan
            from .io import protocol

            if a.cmd == "power":
                save(a.out / "power.json", power_plan(protocol()))
            else:
                from .calibration import calibrate

                mc, rows = calibrate(protocol())
                save(a.out / "monte_carlo.json", mc)
                rows.to_csv(a.out / "replicas.csv", index=False, lineterminator="\n")
        else:
            from .demo import clean, demo, validate

            if a.cmd == "clean":
                clean(a.out)
            elif a.cmd == "demo":
                demo(a.out, a.inputs)
            else:
                validate(a.out)
    except psycopg.Error as exc:
        log("database_error", type=type(exc).__name__, sqlstate=exc.sqlstate)
        return 2
    except (OSError, ValueError, KeyError, jsonschema.ValidationError) as exc:
        log("input_error", message=str(exc))
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
