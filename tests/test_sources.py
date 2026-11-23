import ast
import shutil
from pathlib import Path

import pytest

from faro_exp import analysis
from faro_exp.io import bundle, clock, frame_contract, load_bundle
from faro_exp.simulator import enroll, observe

FIX = Path("data/fixtures")


def test_reproducible_assignment_and_separate_observation(tmp_path):
    a = enroll(tmp_path / "a", "aa", 200)
    assert set(a["files"]) == {"assignments.parquet", "eligible_accounts.parquet"}
    assert a == enroll(tmp_path / "b", "aa", 200)
    m = observe(tmp_path / "a", tmp_path / "x")
    assert m == observe(tmp_path / "b", tmp_path / "y")
    _, frames = load_bundle(tmp_path / "x", ["recorded", "outcome", "event"])
    assert "high_risk" not in frames["outcome"] and "paid" not in frames["recorded"]


def test_analyzer_is_independent_of_generator_truth():
    tree = ast.parse(Path(analysis.__file__).read_text(encoding="utf8"))
    imports = [node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
    assert "simulator" not in imports and "calibration" not in imports


def test_no_silent_replacement(tmp_path):
    enroll(tmp_path / "a", "aa", 200)
    with pytest.raises(ValueError, match="otra versión"):
        enroll(tmp_path / "a", "benefit", 200)


def test_corrupted_source_rejected(tmp_path):
    path = tmp_path / "test"
    shutil.copytree(FIX / "clean", path)
    with (path / "outcomes.parquet").open("ab") as f:
        f.write(b"broken")
    with pytest.raises(ValueError, match="Huella"):
        load_bundle(path, ["recorded", "outcome", "event"])


@pytest.mark.parametrize(
    "fault", ["extra", "wrong_experiment", "null", "naive_clock", "wrong_type", "category"]
)
def test_bad_schema(fault):
    m, f = load_bundle(FIX / "enrollment", ["eligible", "assignment"])
    a = f["assignment"].copy()
    if fault == "extra":
        a["paid"] = False
    if fault == "wrong_experiment":
        a.loc[0, "experiment_id"] = "another"
    if fault == "null":
        a.loc[0, "variant"] = None
    if fault == "naive_clock":
        a["assigned_at"] = a.assigned_at.dt.tz_localize(None)
    if fault == "wrong_type":
        a["account_id"] = a.account_id.astype(float)
    if fault == "category":
        a.loc[0, "variant"] = "U"
    with pytest.raises(ValueError):
        frame_contract("assignment", a, m["experiment_id"])


def test_missing_clock_zone():
    with pytest.raises(ValueError):
        clock("2026-01-04")


def test_empty_receipts_are_a_valid_input_shape(tmp_path):
    m, f = load_bundle(FIX / "clean", ["recorded", "outcome", "event"])
    f["event"] = f["event"].iloc[:0]
    bundle(tmp_path / "empty", {k: m[k] for k in ("experiment_id", "enrollment_sha256")}, f)
    _, loaded = load_bundle(tmp_path / "empty", list(f))
    assert loaded["event"].empty
