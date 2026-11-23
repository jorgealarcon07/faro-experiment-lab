from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from .io import bundle, clock, encoded, load_bundle, protocol, read, sha

FAULTS = ("clean", "loss", "switch", "duplicates", "clock", "assignment_loss", "conflict")


def config(name):
    cfg = yaml.safe_load(Path("config/scenarios.yaml").read_text(encoding="utf8"))
    if sha(encoded(cfg)) != read("contracts.lock.json")["generator"]:
        raise ValueError("La configuración del simulador difiere de la versión registrada")
    return cfg, cfg["scenarios"][name]


def enroll(path, name, n=None, experiment=None):
    p = protocol()
    cfg, s = config(name)
    n = p["planned_accounts"] if n is None else n
    if not 2 <= n <= 500_000:
        raise ValueError("Tamaño fuera del rango de laboratorio")
    experiment = experiment or f"reminder-{name}-{n}"
    rng = np.random.default_rng(np.random.SeedSequence([s["seed"], 0]))
    keys = np.arange(1, n + 1)
    start = clock(p["as_at"])
    accounts = pd.DataFrame(
        {
            "experiment_id": experiment,
            "account_id": keys,
            "balance_cop": p["balance_cop"],
            "high_risk": rng.random(n) < cfg["risk_high_probability"],
            "measured_at": start - pd.Timedelta(days=1),
            "eligible": True,
        }
    )
    assignments = pd.DataFrame(
        {
            "experiment_id": experiment,
            "account_id": keys,
            "variant": np.where(rng.random(n) < p["allocation"], "T", "C"),
            "probability": p["allocation"],
            "assigned_at": start,
        }
    )
    return bundle(
        path,
        {
            "experiment_id": experiment,
            "scenario": name,
            "seed": s["seed"],
            "accounts": n,
            "generator_sha256": sha(encoded(cfg)),
        },
        {"eligible": accounts, "assignment": assignments},
    )


def observe(enrollment, path, fault="clean"):
    if fault not in FAULTS:
        raise ValueError("Escenario de instrumentación desconocido")
    m, frames = load_bundle(enrollment, ["eligible", "assignment"])
    p = protocol()
    cfg, s = config(m["scenario"])
    rng = np.random.default_rng(np.random.SeedSequence([m["seed"], 1]))
    a = frames["assignment"].sort_values("account_id").reset_index(drop=True)
    risk = frames["eligible"].set_index("account_id").loc[a.account_id, "high_risk"].to_numpy()
    n = len(a)
    treated = a.variant.eq("T").to_numpy()
    delivered = treated & (
        rng.random(n) < np.where(risk, cfg["delivery_high_risk"], cfg["delivery_low_risk"])
    )
    mean_delivery = (
        cfg["risk_high_probability"] * cfg["delivery_high_risk"]
        + (1 - cfg["risk_high_probability"]) * cfg["delivery_low_risk"]
    )
    chance = (
        np.where(risk, cfg["payment_high_risk"], cfg["payment_low_risk"])
        + delivered * s["itt_payment"] / mean_delivery
    )
    paid = rng.random(n) < chance
    complained = rng.random(n) < cfg["complaint_base"] + treated * s["itt_complaint"]
    end = a.assigned_at + pd.Timedelta(days=p["horizon_days"])
    out = pd.DataFrame(
        {
            "experiment_id": m["experiment_id"],
            "account_id": a.account_id,
            "paid": paid,
            "complained": complained,
            "window_end": end,
            "available_at": end + pd.to_timedelta(rng.integers(0, 48, n), unit="h"),
        }
    )
    d = a.loc[treated, ["experiment_id", "account_id"]].copy()
    d["event_id"] = "attempt-" + d.account_id.astype(str)
    d["status"] = np.where(delivered[treated], "delivered", "failed")
    d["attempted_at"] = a.loc[treated, "assigned_at"] + pd.Timedelta(hours=1)
    d["received_at"] = d.attempted_at + pd.to_timedelta(rng.integers(1, 24, len(d)), unit="h")
    # One transport receipt per attempt plus identical redeliveries of a subset.
    events = pd.concat([d, d.iloc[::19]], ignore_index=True)
    if fault == "loss":
        out = out[~(treated & (a.account_id % 3 == 0))]
    elif fault == "switch":
        a.loc[0, "variant"] = "T" if a.loc[0, "variant"] == "C" else "C"
    elif fault == "duplicates":
        retries = events.copy()
        retries["received_at"] += pd.Timedelta(hours=3)
        events = pd.concat([events, retries], ignore_index=True)
    elif fault == "clock":
        out.loc[0, "available_at"] = a.loc[0, "assigned_at"] - pd.Timedelta(days=1)
    elif fault == "assignment_loss":
        a = a[~(treated & (a.account_id % 3 == 0))]
    elif fault == "conflict":
        if d.empty:
            raise ValueError("El caso de conflicto requiere al menos una cuenta tratada")
        wrong = d.iloc[[0]].copy()
        wrong["status"] = "failed" if wrong.iloc[0].status == "delivered" else "delivered"
        events = pd.concat([events, wrong], ignore_index=True)
    return bundle(
        path,
        {
            "experiment_id": m["experiment_id"],
            "enrollment_sha256": sha(encoded(m)),
            "generator_revision": "1",
            "instrumentation": fault,
        },
        {"recorded": a, "outcome": out, "event": events},
    )
