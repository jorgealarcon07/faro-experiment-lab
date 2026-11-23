from html import escape
from pathlib import Path
from string import Template

import pandas as pd

from .io import read
from .report_language import REPORT_FILES, labels, localize


def bounds(row, formatter):
    return f"{formatter(row['difference'])} [{formatter(row['lo'])}, {formatter(row['hi'])}]"


def table(headers, rows):
    head = "".join(f"<th scope=col>{escape(str(x))}</th>" for x in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{escape(str(x))}</td>" for x in r) + "</tr>" for r in rows
    )
    return f'<div class="scroll"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def render(folder):
    """Write one shared decision CSV and both presentation views."""
    folder = Path(folder)
    all_cases = read(folder / "cases.json")
    flat = []
    for name, c in all_cases.items():
        r = c["estimates"]
        flat.append(
            {
                "case": name,
                "state": c["state"],
                "run_id": c["run_id"],
                "accounts": sum(c["checks"]["registered"].values()),
                "payment_diff": r["payment"]["difference"] if r else None,
                "lower": r["payment"]["lo"] if r else None,
                "upper": r["payment"]["hi"] if r else None,
                "reasons": "|".join(c["reasons"]),
            }
        )
    pd.DataFrame(flat).to_csv(folder / "decisions.csv", index=False, lineterminator="\n")
    render_pages(folder)


def render_pages(folder, *, languages=REPORT_FILES):
    """Render from saved results without changing the audited evidence."""
    folder = Path(folder)
    all_cases = read(folder / "cases.json")
    mc = read(folder / "monte_carlo.json")
    evidence = read(folder / "trace.json")
    template = (Path(__file__).parent / "report.html").read_text(encoding="utf-8")
    for language in languages:
        values = page_values(all_cases, mc, evidence, language)
        content = Template(localize(template, language)).substitute(values)
        (folder / REPORT_FILES[language]).write_bytes(content.encode("utf-8"))


def page_values(all_cases, mc, evidence, language):
    text = labels(language)

    def num(value, digits=2):
        formatted = f"{value:,.{digits}f}"
        return formatted.translate(str.maketrans(".,", ",.")) if language == "es" else formatted

    def pp(value):
        return num(value * 100) + " pp"

    scenarios = {
        "aa": text["py_aa"],
        "benefit": text["py_benefit"],
        "harm": text["py_harm"],
        "complaint": text["py_complaint"],
        "mde": text["py_mde"],
    }
    reasons = {
        "payment_above_minimum": text["py_payment_below"],
        "cash_above_zero": text["py_cash_below"],
        "complaints_below_margin": text["py_complaint_above"],
        "all_prespecified_gates_pass": text["py_gates_pass"],
    }
    states = {key: text[f"py_{key}_state"] for key in ("ship", "hold", "invalid", "pending")}

    case = all_cases["benefit"]
    stats = case["estimates"]
    arm = stats["arms"]
    payment = stats["payment"]
    incident = all_cases["loss"]
    rows = []
    for name in ["aa", "benefit", "harm", "complaint", "mde"]:
        c = all_cases[name]
        est = c["estimates"]
        row = [scenarios[name], states.get(c["state"], c["state"])]
        if est:
            row.extend(
                [
                    bounds(est["payment"], pp),
                    bounds(est["complaint"], pp),
                    bounds(est["net_cash_cop"], lambda v: num(v, 0)),
                    ". ".join(reasons.get(r, r) for r in c["reasons"]),
                ]
            )
        else:
            row.extend(["—", "—", "—", ", ".join(c["reasons"])])
        rows.append(row)

    def rate(r):
        return num(100 * r, 1) + (" %" if language == "es" else "%")

    values = {
        "primary": case["state"] if language == "es" else states.get(case["state"], case["state"]),
        "delta": pp(payment["difference"]),
        "interval": f"{pp(payment['lo'])} – {pp(payment['hi'])}",
        "cash": num(stats["net_cash_cop"]["difference"], 0),
        "guard": pp(stats["complaint"]["hi"]),
        "n": num(sum(a["n"] for a in arm.values()), 0),
        "arm_table": table(
            [
                text["py_assignment"],
                text["py_accounts"],
                text["py_attempts"],
                text["py_delivered"],
                text["py_paid"],
                text["py_complaints"],
            ],
            [
                [label, *[arm[a][k] for k in ["n", "attempts", "delivered", "paid", "complained"]]]
                for a, label in [("C", text["py_control"]), ("T", text["py_treatment"])]
            ],
        ),
        "cases": table(
            [
                text["py_scenario"],
                text["py_decision"],
                text["py_payment_ci"],
                text["py_complaints_ci"],
                text["py_cash_ci"],
                text["py_reason"],
            ],
            rows,
        ),
        "bad": pp(case["comparison"]["delivered_minus_control"]),
        "costs": table(
            [text["py_cost"], text["py_incremental"]],
            [
                [k, bounds(v, lambda x: num(x, 0))]
                for k, v in sorted(stats["cost_sensitivity_cop"].items(), key=lambda kv: int(kv[0]))
            ],
        ),
        "loss": num(incident["checks"]["missing_outcomes"], 0),
        "miss_c": num(incident["checks"]["complete_join"]["C"], 0),
        "miss_t": num(incident["checks"]["complete_join"]["T"], 0),
        "srm": f"{incident['checks']['srm_p_join']:.2e}",
        "mc_table": table(
            [
                text["py_truth"],
                text["py_replications"],
                text["py_invalid"],
                text["py_reject"],
                text["py_coverage"],
                text["py_ship"],
            ],
            [
                [
                    f"{scenarios[k]} · {pp(v['truth_payment'])}",
                    v["n_replicas"],
                    v["invalid_srm"],
                    rate(v["reject_zero"]["rate_all"]),
                    rate(v["cover"]["rate_all"]),
                    rate(v["ship"]["rate_all"]),
                ]
                for k in scenarios
                if (v := mc["scenarios"][k])
            ],
        ),
        "power": rate(mc["power"]["approx_power_at_planned_n"]),
        "trace": table(
            [
                text["py_synthetic"],
                text["py_variant"],
                text["py_assigned_utc"],
                text["py_attempts"],
                text["py_deliveries"],
                text["py_payment"],
                text["py_available"],
            ],
            [
                [
                    evidence["account_id"],
                    evidence["variant"],
                    evidence["assigned_at"],
                    evidence["attempts"],
                    evidence["delivered"],
                    text["py_yes"] if evidence["paid"] else text["py_no"],
                    evidence["available_at"],
                ]
            ],
        ),
    }
    return values
