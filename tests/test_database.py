import os
import uuid
from pathlib import Path

import pandas as pd
import pytest

from faro_exp import database as db
from faro_exp.analysis import analyze
from faro_exp.cli import main
from faro_exp.demo import EARLY, FINAL
from faro_exp.io import bundle, encoded, load_bundle, read, sha

FIX = Path("data/fixtures")
pytestmark = pytest.mark.postgres


@pytest.fixture(scope="module")
def sample(tmp_path_factory):
    folder = tmp_path_factory.mktemp("private_experiment")
    experiment = "pytest-" + uuid.uuid4().hex
    registration = None
    for part, kinds in [
        ("enrollment", ["eligible", "assignment"]),
        ("clean", ["recorded", "outcome", "event"]),
        ("loss", ["recorded", "outcome", "event"]),
    ]:
        old, frames = load_bundle(FIX / part, kinds)
        meta = {k: v for k, v in old.items() if k not in {"files", "protocol_sha256"}}
        meta["experiment_id"] = experiment
        for frame in frames.values():
            frame["experiment_id"] = experiment
        if part == "enrollment":
            registration = bundle(folder / part, meta, frames)
        else:
            meta["enrollment_sha256"] = sha(encoded(registration))
            bundle(folder / part, meta, frames)
    return folder


@pytest.fixture
def conn(sample):
    if not os.getenv("PGDATABASE"):
        pytest.skip("Configure a dedicated PostgreSQL with PGDATABASE")
    with db.connect() as c:
        db.initialize(c)
        with c.transaction(force_rollback=True):
            db.register(c, sample / "enrollment")
            yield c


def change(sample, tmp_path, fault):
    meta, frames = load_bundle(sample / "clean", ["recorded", "outcome", "event"])
    a, o, e = frames["recorded"], frames["outcome"], frames["event"]
    if fault == "switch":
        a.loc[0, "variant"] = "T"
    elif fault == "cross":
        e.loc[0, "account_id"] = 1
    elif fault == "missing_attempt":
        frames["event"] = e.iloc[1:]
    elif fault == "duplicate_outcome":
        frames["outcome"] = pd.concat([o, o.iloc[:1]])
    elif fault == "extra_key":
        o.loc[0, "account_id"] = 999
    elif fault == "conflict":
        frames["event"] = pd.concat([e, e.iloc[[0]].assign(status="failed")])
    elif fault == "retry":
        more = e.copy()
        more["received_at"] += pd.Timedelta(hours=6)
        frames["event"] = pd.concat([e, more])
    elif fault == "clock":
        o.loc[0, "window_end"] += pd.Timedelta(days=1)
    elif fault == "late":
        o.loc[0, "available_at"] += pd.Timedelta(days=4)
    elif fault == "changed_paid":
        o.loc[0, "paid"] = not o.loc[0, "paid"]
    folder = tmp_path / fault
    bundle(folder, {k: meta[k] for k in ("experiment_id", "enrollment_sha256")}, frames)
    return folder


def test_manual_and_replay(conn, sample):
    r, m, action = analyze(conn, sample / "clean", FINAL)
    oracle = read(FIX / "oracle.json")
    assert r["state"] == "hold" and r["estimates"]["arms"]["T"]["n"] == 100
    assert r["estimates"]["payment"]["difference"] == pytest.approx(oracle["effect"])
    assert r["estimates"]["net_cash_cop"]["difference"] == pytest.approx(oracle["cash_cop"])
    assert (
        r["estimates"]["arms"]["C"]["paid"] == 20 and r["estimates"]["arms"]["T"]["delivered"] == 80
    )
    assert action == "published" and analyze(conn, sample / "clean", FINAL) == (r, m, "replay")


def test_asof_pending_incident_and_lineage(conn, sample):
    early, _, _ = analyze(conn, sample / "clean", EARLY)
    assert early["state"] == "pending" and early["estimates"] is None and early["segments"] == []
    assert db.trace(conn, early["run_id"], 1)["paid"] is None
    loss, _, _ = analyze(conn, sample / "loss", FINAL, early["run_id"])
    assert (
        loss["state"] == "invalid"
        and loss["estimates"] is None
        and "srm_analytic_join" in loss["reasons"]
    )
    assert loss["checks"]["missing_outcomes"] == 50
    final, m, _ = analyze(conn, sample / "clean", FINAL, loss["run_id"])
    assert final["state"] == "hold" and m["parent_run"] == loss["run_id"]


@pytest.mark.parametrize(
    "fault,reason",
    [
        ("switch", "assignment_changed"),
        ("cross", "control_exposed"),
        ("missing_attempt", "attempt_count"),
        ("duplicate_outcome", "duplicate_outcome"),
        ("extra_key", "orphan_account"),
        ("conflict", "conflicting_event_id"),
        ("clock", "outcome_clock"),
        ("late", "missing_mature_outcome"),
    ],
)
def test_invalid_without_efficacy(conn, sample, tmp_path, fault, reason):
    r, _, _ = analyze(conn, change(sample, tmp_path, fault), FINAL)
    assert r["state"] == "invalid" and reason in r["reasons"] and r["estimates"] is None


def test_repeated_event_with_later_receipt_preserves_itt(conn, sample, tmp_path):
    r, m, _ = analyze(conn, sample / "clean", FINAL)
    retry, other, _ = analyze(conn, change(sample, tmp_path, "retry"), FINAL)
    assert other["itt_sha256"] == m["itt_sha256"] and retry["estimates"] == r["estimates"]
    assert retry["checks"]["raw_event_rows"] == 200


def test_rollback_and_final_seal(conn, sample, tmp_path):
    with pytest.raises(RuntimeError), conn.transaction():
        analyze(conn, sample / "clean", FINAL)
        raise RuntimeError("interrupted before commit")
    assert (
        conn.execute(
            "SELECT count(*) FROM faro_exp.run WHERE experiment_id=%s",
            (read(sample / "enrollment/manifest.json")["experiment_id"],),
        ).fetchone()[0]
        == 0
    )
    analyze(conn, sample / "clean", FINAL)
    with pytest.raises(ValueError, match="sellado"):
        analyze(conn, change(sample, tmp_path, "changed_paid"), FINAL)
    assert (
        conn.execute(
            "SELECT count(*) FROM faro_exp.run WHERE experiment_id=%s",
            (read(sample / "enrollment/manifest.json")["experiment_id"],),
        ).fetchone()[0]
        == 1
    )


def test_immutable_assignment(conn, sample, tmp_path):
    m, f = load_bundle(sample / "enrollment", ["eligible", "assignment"])
    f["assignment"].loc[0, "variant"] = "T"
    folder = tmp_path / "reregister"
    bundle(folder, {k: m[k] for k in ["experiment_id", "seed", "accounts"]}, f)
    with pytest.raises(ValueError, match="inmutable"):
        db.register(conn, folder)


def test_cli_rejects_bad_cut_before_writes(tmp_path):
    assert (
        main(
            [
                "analyze",
                "--input",
                str(FIX / "clean"),
                "--as-of",
                "not-a-date",
                "--out",
                str(tmp_path / "x"),
            ]
        )
        == 2
    )
    assert not (tmp_path / "x").exists()
