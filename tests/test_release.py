from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from faro_exp.demo import validate
from faro_exp.inference import gates, interval, srm
from faro_exp.io import protocol, read

OUT = Path("reports/release")


def test_release_contracts_and_incident():
    validate(OUT)
    cases = read(OUT / "cases.json")
    assert "srm_analytic_join" in cases["loss"]["reasons"]
    assert cases["loss"]["checks"]["srm_p_registered"] >= 0.001
    assert cases["conflict"]["estimates"] is None
    assert cases["early"]["comparison"] is None


@pytest.mark.parametrize("scenario", ["aa", "benefit", "harm", "complaint", "mde"])
def test_all_mc_draws_retained_and_reproducible_gates(scenario):
    p = protocol()
    rows = pd.read_csv(OUT / "replicas.csv").query("scenario==@scenario")
    assert list(rows.replica) == list(range(1000))
    assert (rows.nt + rows.nc == p["planned_accounts"]).all()
    for r in rows.iloc[::199].itertuples():
        _, lo, hi = interval(r.pay_t, r.nt, r.pay_c, r.nc, p["alpha"])
        _, _, upper = interval(r.complaint_t, r.nt, r.complaint_c, r.nc, p["alpha"])
        ok = srm(r.nt, r.nc, p["allocation"]) >= p["srm_alpha"]
        assert r.valid == ok and r.ship == (ok and all(gates(lo, upper, p).values()))
        np.testing.assert_allclose([r.lo, r.hi], [lo, hi], atol=1e-12)
    summary = read(OUT / "monte_carlo.json")["scenarios"][scenario]
    assert summary["invalid_srm"] == int((~rows.valid).sum())
    assert summary["cover"]["rate_all"] == pytest.approx(rows.cover.mean())
