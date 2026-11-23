"""Create the hand-counted 200-account acceptance fixture (alternating assignment)."""

from pathlib import Path

import numpy as np
import pandas as pd

from faro_exp.io import bundle, clock, encoded, protocol, save, sha


def main():
    root = Path("data/fixtures")
    p = protocol()
    base = clock(p["as_at"])
    key = np.arange(1, 201)
    treated = key % 2 == 0
    exp = "manual-200"
    accounts = pd.DataFrame(
        {
            "experiment_id": exp,
            "account_id": key,
            "balance_cop": 50000,
            "high_risk": key % 4 < 2,
            "measured_at": base - pd.Timedelta(days=1),
            "eligible": True,
        }
    )
    assignments = pd.DataFrame(
        {
            "experiment_id": exp,
            "account_id": key,
            "variant": np.where(treated, "T", "C"),
            "probability": 0.5,
            "assigned_at": base,
        }
    )
    m = bundle(
        root / "enrollment",
        {"experiment_id": exp, "scenario": "manual_fixture", "seed": 1, "accounts": 200},
        {"eligible": accounts, "assignment": assignments},
    )
    end = base + pd.Timedelta(days=14)
    outcomes = pd.DataFrame(
        {
            "experiment_id": exp,
            "account_id": key,
            "paid": (treated & (key <= 46)) | (~treated & (key <= 39)),
            "complained": key <= 2,
            "window_end": end,
            "available_at": end + pd.Timedelta(days=1),
        }
    )
    attempts = pd.DataFrame(
        {
            "experiment_id": exp,
            "account_id": key[treated],
            "event_id": [f"m-{i}" for i in key[treated]],
            "status": np.where(key[treated] <= 160, "delivered", "failed"),
            "attempted_at": base + pd.Timedelta(hours=1),
            "received_at": base + pd.Timedelta(hours=2),
        }
    )
    for fault, out in [("clean", outcomes), ("loss", outcomes[~(treated & (key <= 100))])]:
        bundle(
            root / fault,
            {
                "experiment_id": exp,
                "enrollment_sha256": sha(encoded(m)),
                "instrumentation": fault,
                "generator_revision": "manual-v1",
            },
            {"recorded": assignments, "outcome": out, "event": attempts},
        )
    save(
        root / "oracle.json",
        {
            "n_control": 100,
            "n_treatment": 100,
            "paid_control": 20,
            "paid_treatment": 23,
            "complaints_control": 1,
            "complaints_treatment": 1,
            "attempts_treatment": 100,
            "delivered_treatment": 80,
            "effect": 0.03,
            "cash_cop": 1400,
            "lost_treatment": 50,
            "data_kind": "synthetic",
            "license": "CC0-1.0",
        },
    )


if __name__ == "__main__":
    main()
