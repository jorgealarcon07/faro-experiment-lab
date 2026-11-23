import math

import numpy as np
from scipy.stats import chisquare
from statsmodels.stats.power import NormalIndPower
from statsmodels.stats.proportion import confint_proportions_2indep, proportion_effectsize


def power_plan(p):
    effect = abs(proportion_effectsize(p["power_base"] + p["power_delta"], p["power_base"]))
    power = NormalIndPower()
    per_arm = math.ceil(
        power.solve_power(effect_size=effect, alpha=p["alpha"], power=p["power_target"], ratio=1)
    )
    return {
        "baseline": p["power_base"],
        "alternative": p["power_base"] + p["power_delta"],
        "alpha": p["alpha"],
        "target_power": p["power_target"],
        "per_arm_required": per_arm,
        "planned_n": p["planned_accounts"],
        "expected_per_arm": p["planned_accounts"] / 2,
        "approx_power_at_planned_n": power.power(
            effect, p["planned_accounts"] / 2, p["alpha"], ratio=1
        ),
        "method": "two-sided normal approximation, arcsine effect size, balanced arms",
    }


def interval(yes_t, n_t, yes_c, n_c, alpha):
    lo, hi = confint_proportions_2indep(
        yes_t, n_t, yes_c, n_c, method="newcomb", compare="diff", alpha=alpha
    )
    return yes_t / n_t - yes_c / n_c, lo, hi


def srm(t, c, allocation):
    if t + c == 0:
        return 0.0
    return float(chisquare([t, c], [(t + c) * allocation, (t + c) * (1 - allocation)]).pvalue)


def gates(payment_lower, complaint_upper, p):
    return {
        "payment_above_minimum": payment_lower > p["min_effect"],
        "cash_above_zero": p["balance_cop"] * payment_lower - p["cost_per_attempt_cop"] > 0,
        "complaints_below_margin": complaint_upper < p["max_complaint_increase"],
    }


def measures(counts, p):
    t, c = counts["T"], counts["C"]

    def estimate(col):
        est, lo, hi = interval(t[col], t["n"], c[col], c["n"], p["alpha"])
        return {
            "difference": float(est),
            "lo": float(lo),
            "hi": float(hi),
            "rate_t": t[col] / t["n"],
            "rate_c": c[col] / c["n"],
        }

    pay, complaint = estimate("paid"), estimate("complained")

    def cash(cost):
        return {k: p["balance_cop"] * pay[k] - cost for k in ["difference", "lo", "hi"]}

    checks = {k: bool(v) for k, v in gates(pay["lo"], complaint["hi"], p).items()}
    return {
        "arms": counts,
        "payment": pay,
        "complaint": complaint,
        "net_cash_cop": cash(p["cost_per_attempt_cop"]),
        "cost_sensitivity_cop": {str(cost): cash(cost) for cost in p["cost_sensitivity_cop"]},
        "total_attempt_cost_cop": t["n"] * p["cost_per_attempt_cop"],
        "gates": checks,
    }


def diagnostics(itt, p):
    # Called only when every assigned account has exactly one valid mature outcome.
    counts = {}
    for arm in ["T", "C"]:
        group = itt[itt.variant == arm]
        counts[arm] = {
            "n": len(group),
            "paid": int(group.paid.sum()),
            "complained": int(group.complained.sum()),
            "attempts": int(group.attempts.sum()),
            "delivered": int(group.delivered.sum()),
        }
    result = measures(counts, p)
    recipients = itt[(itt.variant == "T") & (itt.delivered == 1)]
    c = itt[itt.variant == "C"]
    flawed = {
        "recipients": len(recipients),
        "control": len(c),
        "high_risk_control": float(c.high_risk.mean()),
        "high_risk_recipients": float(recipients.high_risk.mean()) if len(recipients) else None,
        "delivered_minus_control": float(recipients.paid.mean() - c.paid.mean())
        if len(recipients)
        else None,
    }
    groups = []
    for (arm, risk), group in itt.groupby(["variant", "high_risk"]):
        groups.append(
            {
                "variant": arm,
                "high_risk": bool(risk),
                "n": len(group),
                "paid": int(group.paid.sum()),
            }
        )
    return result, flawed, groups


def mc_se(rate, n):
    return float(np.sqrt(rate * (1 - rate) / n))
