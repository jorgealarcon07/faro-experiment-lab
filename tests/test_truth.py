import pytest

from faro_exp.io import read
from faro_exp.simulator import config


@pytest.mark.parametrize("name", ["aa", "benefit", "harm", "complaint", "mde"])
def test_marginal_itt_matches_frozen_oracle(name):
    oracle = read("tests/truth/scenarios.json")
    cfg, scenario = config(name)
    high = cfg["risk_high_probability"]
    pd = oracle["mean_delivery_treatment"]
    expected_c = (1 - high) * cfg["payment_low_risk"] + high * cfg["payment_high_risk"]
    expected_t = 0.0
    for weight, risk in [(high, "high"), (1 - high, "low")]:
        delivery = cfg[f"delivery_{risk}_risk"]
        baseline = cfg[f"payment_{risk}_risk"]
        conditional = baseline + scenario["itt_payment"] / pd
        assert 0 <= conditional <= 1
        expected_t += weight * (delivery * conditional + (1 - delivery) * baseline)
    assert expected_c == pytest.approx(oracle["baseline_payment"])
    assert expected_t - expected_c == pytest.approx(oracle["itt"][name][0])
    assert cfg["complaint_base"] == oracle["baseline_complaint"]
    assert scenario["itt_complaint"] == oracle["itt"][name][1]
