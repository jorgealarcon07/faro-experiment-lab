import math

import numpy as np
import pytest
from scipy.stats import norm

from faro_exp.inference import gates, interval, measures, power_plan, srm
from faro_exp.io import protocol


def wilson(x, n):
    z = norm.ppf(0.975)
    y = x / n
    offset = z * z / (2 * n)
    half = z * math.sqrt(y * (1 - y) / n + z * z / (4 * n * n))
    den = 1 + z * z / n
    return (y + offset - half) / den, (y + offset + half) / den


@pytest.mark.parametrize(
    "t,nt,c,nc",
    [(23, 100, 20, 100), (0, 10, 0, 15), (10, 10, 0, 10), (1, 100, 15, 220), (90, 101, 100, 100)],
)
def test_newcombe_against_independent_wilson_construction(t, nt, c, nc):
    p1, p0 = t / nt, c / nc
    l1, u1 = wilson(t, nt)
    l0, u0 = wilson(c, nc)
    expect = [
        p1 - p0,
        p1 - p0 - math.hypot(p1 - l1, u0 - p0),
        p1 - p0 + math.hypot(u1 - p1, p0 - l0),
    ]
    np.testing.assert_allclose(interval(t, nt, c, nc, 0.05), expect, atol=1e-12)


def test_power_and_srm():
    result = power_plan(protocol())
    assert result["per_arm_required"] == 6508
    assert 0.93 < result["approx_power_at_planned_n"] < 0.94
    assert srm(100, 100, 0.5) == 1 and srm(30, 100, 0.5) < 0.001


@pytest.mark.parametrize(
    "lo,hi,ship",
    [(0.01, 0, False), (0.011, 0.005, False), (0.011, 0.0049, True), (-0.001, 0, False)],
)
def test_strict_gate_boundaries(lo, hi, ship):
    assert bool(all(gates(lo, hi, protocol()).values())) == ship


def test_manual_cash_includes_every_attempt():
    counts = {
        "C": {"n": 100, "paid": 20, "complained": 1},
        "T": {"n": 100, "paid": 23, "complained": 1},
    }
    stats = measures(counts, protocol())
    assert stats["net_cash_cop"]["difference"] == pytest.approx(1400)
    assert stats["total_attempt_cost_cop"] == 10000
    assert stats["cost_sensitivity_cop"]["250"]["lo"] == pytest.approx(
        stats["net_cash_cop"]["lo"] - 150
    )


def test_batched_interval_equals_per_run():
    t = np.array([50, 70, 92])
    actual = interval(t, np.full(3, 300), t - 3, np.full(3, 301), 0.05)
    for i, row in enumerate(t):
        np.testing.assert_allclose([a[i] for a in actual], interval(row, 300, row - 3, 301, 0.05))
