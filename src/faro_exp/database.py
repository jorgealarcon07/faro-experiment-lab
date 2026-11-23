from pathlib import Path

import numpy as np
import pandas as pd
import psycopg

from .io import clock, encoded, load_bundle, protocol, sha

SQL = Path(__file__).parent


def connect():
    return psycopg.connect(
        connect_timeout=8,
        autocommit=True,
        application_name="faro_experiment_lab",
        options="-c timezone=UTC",
    )


def lock(conn, key):
    conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", (key,))


def initialize(conn):
    with conn.transaction():
        lock(conn, "faro_exp.schema.v1")
        conn.execute((SQL / "store.sql").read_text(encoding="utf8"))


def copy(conn, table, frame, batch=None):
    from psycopg import sql

    frame = frame.copy()
    if batch is not None:
        frame.insert(0, "batch_hash", batch)
    cols = sql.SQL(",").join(map(sql.Identifier, frame.columns))
    stmt = sql.SQL("COPY faro_exp.{} ({}) FROM STDIN WITH (FORMAT csv)").format(
        sql.Identifier(table), cols
    )
    with conn.cursor().copy(stmt) as cp:
        cp.write(frame.to_csv(index=False, header=False, lineterminator="\n").encode())


def register(conn, folder):
    m, f = load_bundle(folder, ["eligible", "assignment"])
    e = f["eligible"].set_index("account_id").sort_index()
    a = f["assignment"].set_index("account_id").sort_index()
    p = protocol()
    if (
        not a.index.is_unique
        or not e.index.is_unique
        or not a.index.equals(e.index)
        or len(a) != m["accounts"]
        or len(a) < 2
        or not e.eligible.all()
        or not (e.measured_at < a.assigned_at).all()
        or not a.assigned_at.eq(clock(p["as_at"])).all()
        or not a.probability.eq(p["allocation"]).all()
        or not e.balance_cop.eq(p["balance_cop"]).all()
    ):
        raise ValueError("Registro incompatible: identidad, elegibilidad, tiempo o asignación")
    key = sha(encoded(m))
    with conn.transaction():
        lock(conn, "register:" + m["experiment_id"])
        old = conn.execute(
            "SELECT enrollment_hash FROM faro_exp.experiment WHERE experiment_id=%s",
            (m["experiment_id"],),
        ).fetchone()
        if old:
            if old[0] != key:
                raise ValueError("La asignación registrada es inmutable")
            return "replay"
        conn.execute(
            "INSERT INTO faro_exp.experiment VALUES(%s,%s,%s,%s)",
            (m["experiment_id"], key, m["protocol_sha256"], m["seed"]),
        )
        copy(conn, "account", f["eligible"])
        copy(conn, "assignment", f["assignment"])
    return "registered"


def ingest(conn, m, frames):
    batch = sha(encoded(m))
    row = conn.execute(
        "SELECT enrollment_hash,seed FROM faro_exp.experiment WHERE experiment_id=%s",
        (m["experiment_id"],),
    ).fetchone()
    if not row or row[0] != m["enrollment_sha256"]:
        raise ValueError("Se requiere la inscripción original antes de ingerir resultados")
    lock(conn, "ingest:" + batch)
    if not conn.execute("SELECT 1 FROM faro_exp.batch WHERE batch_hash=%s", (batch,)).fetchone():
        conn.execute("INSERT INTO faro_exp.batch VALUES(%s,%s)", (batch, m["experiment_id"]))
        for name in ["recorded", "outcome", "event"]:
            copy(conn, name, frames[name], batch)
    return batch, row[1]


def analytic_table(conn, experiment, batch, as_of):
    args = {"experiment": experiment, "batch": batch, "as_of": as_of}
    with conn.cursor() as cur:
        cur.execute((SQL / "itt.sql").read_text(encoding="utf8"), args)
        frame = pd.DataFrame(cur.fetchall(), columns=[c.name for c in cur.description])
    for c in [
        "assigned_at",
        "logged_time",
        "window_end",
        "available_at",
        "first_attempt",
        "last_attempt",
    ]:
        frame[c] = pd.to_datetime(frame[c], utc=True)
    extra = conn.execute(
        """WITH visible AS (
          SELECT account_id FROM faro_exp.recorded WHERE batch_hash=%(batch)s UNION ALL
          SELECT account_id FROM faro_exp.outcome WHERE batch_hash=%(batch)s AND available_at<=%(as_of)s UNION ALL
          SELECT account_id FROM faro_exp.event WHERE batch_hash=%(batch)s AND received_at<=%(as_of)s)
          SELECT count(*) FROM visible v WHERE NOT EXISTS (SELECT 1 FROM faro_exp.assignment a
          WHERE a.experiment_id=%(experiment)s AND a.account_id=v.account_id)""",
        args,
    ).fetchone()[0]
    receipts, conflicts = conn.execute(
        """SELECT coalesce(sum(n),0)::bigint, count(*) FILTER(WHERE versions>1)
          FROM (SELECT event_id,count(*) n,count(DISTINCT (account_id,status,attempted_at,received_at)) versions
          FROM faro_exp.event WHERE batch_hash=%(batch)s AND received_at<=%(as_of)s GROUP BY event_id) grouped""",
        args,
    ).fetchone()
    return frame, {
        "orphan_rows": extra,
        "event_id_conflicts": conflicts,
        "raw_event_rows": receipts,
    }


def fingerprint(frame):
    # SQL orders by ID. Explicit null and timestamp formatting are independent of OS newlines.
    return sha(
        frame.to_csv(
            index=False, na_rep="NULL", date_format="%Y-%m-%dT%H:%M:%SZ", lineterminator="\n"
        ).encode()
    )


def trace(conn, run_id, account_id):
    run = conn.execute(
        "SELECT experiment_id,batch_hash,as_of FROM faro_exp.run WHERE run_id=%s", (run_id,)
    ).fetchone()
    if not run:
        raise ValueError("Ejecución desconocida")
    frame, _ = analytic_table(conn, *run)
    row = frame[frame.account_id == account_id]
    if row.empty:
        raise ValueError("Cuenta fuera del experimento")
    result = {}
    for col, v in row.iloc[0].items():
        result[col] = None if pd.isna(v) else v.item() if isinstance(v, np.generic) else v
    return result
