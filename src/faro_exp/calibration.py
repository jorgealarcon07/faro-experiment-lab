import numpy as np
import pandas as pd
from scipy.stats import chi2

from .inference import gates, interval, mc_se, power_plan
from .simulator import config


def calibrate(p):
    # Sufficient-statistic sampler for the same marginal DGP. Random risk/delivery
    # integrate out to Bernoulli(base+ITT). Complaints are independent given arm.
    scenarios = ["aa", "benefit", "harm", "complaint", "mde"]
    records = []
    summaries = {}
    for index, name in enumerate(scenarios):
        cfg, truth = config(name)
        base = (
            cfg["risk_high_probability"] * cfg["payment_high_risk"]
            + (1 - cfg["risk_high_probability"]) * cfg["payment_low_risk"]
        )
        rows = []
        seeds = np.random.SeedSequence([p["mc_root_seed"], index]).spawn(p["replicates"])
        for rep, seed in enumerate(seeds):
            rng = np.random.default_rng(seed)
            nt = int(rng.binomial(p["planned_accounts"], p["allocation"]))
            nc = p["planned_accounts"] - nt
            rows.append(
                (
                    name,
                    rep,
                    index,
                    nt,
                    nc,
                    rng.binomial(nt, base + truth["itt_payment"]),
                    rng.binomial(nc, base),
                    rng.binomial(nt, cfg["complaint_base"] + truth["itt_complaint"]),
                    rng.binomial(nc, cfg["complaint_base"]),
                )
            )
        df = pd.DataFrame(
            rows,
            columns=[
                "scenario",
                "replica",
                "stream",
                "nt",
                "nc",
                "pay_t",
                "pay_c",
                "complaint_t",
                "complaint_c",
            ],
        )
        est, lo, hi = interval(
            df.pay_t.to_numpy(), df.nt.to_numpy(), df.pay_c.to_numpy(), df.nc.to_numpy(), p["alpha"]
        )
        _, _, guard_hi = interval(
            df.complaint_t.to_numpy(),
            df.nt.to_numpy(),
            df.complaint_c.to_numpy(),
            df.nc.to_numpy(),
            p["alpha"],
        )
        expected = p["planned_accounts"] * p["allocation"]
        df["valid"] = (
            chi2.sf(
                (df.nt - expected) ** 2 / expected
                + (df.nc - (p["planned_accounts"] - expected)) ** 2
                / (p["planned_accounts"] - expected),
                1,
            )
            >= p["srm_alpha"]
        )
        df["estimate"], df["lo"], df["hi"] = est, lo, hi
        df["cover"] = (lo <= truth["itt_payment"]) & (hi >= truth["itt_payment"])
        df["reject_zero"] = (lo > 0) | (hi < 0)
        gate = gates(lo, guard_hi, p)
        df["primary_above_minimum"] = gate["payment_above_minimum"]
        df["ship"] = df.valid & np.logical_and.reduce(list(gate.values()))
        df["guard_hi"] = guard_hi
        df["decision"] = np.where(~df.valid, "invalid", np.where(df.ship, "ship", "hold"))
        summary = {
            "n_replicas": len(df),
            "valid": int(df.valid.sum()),
            "invalid_srm": int((~df.valid).sum()),
            "truth_payment": truth["itt_payment"],
            "truth_complaint": truth["itt_complaint"],
            "bias": float(est.mean() - truth["itt_payment"]),
            "bias_mcse": float(np.std(est, ddof=1) / np.sqrt(len(df))),
        }
        for field in ["cover", "reject_zero", "primary_above_minimum", "ship"]:
            raw = float(df[field].mean())
            summary[field] = {
                "rate_all": raw,
                "mcse_all": mc_se(raw, len(df)),
                "rate_valid": float(df.loc[df.valid, field].mean()),
            }
        summaries[name] = summary
        records.append(df)
    aa = summaries["aa"]["reject_zero"]["rate_all"]
    low, high = p["coverage_band"]
    return {
        "root_seed": p["mc_root_seed"],
        "per_scenario": p["replicates"],
        "power": power_plan(p),
        "seed_recipe": "SeedSequence([root_seed, stream]).spawn(per_scenario)[replica]",
        "scenarios": summaries,
        "aa_in_band": p["aa_band"][0] <= aa <= p["aa_band"][1],
        "coverage_in_band": {
            name: low <= r["cover"]["rate_all"] <= high for name, r in summaries.items()
        },
    }, pd.concat(records, ignore_index=True)
