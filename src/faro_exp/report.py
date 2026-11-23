from html import escape
from pathlib import Path
from string import Template

import pandas as pd

from .io import read


def num(x, digits=2):
    return f"{x:,.{digits}f}".translate(str.maketrans(".,", ",."))


def pp(x):
    return num(x * 100) + " pp"


def bounds(row, formatter):
    return f"{formatter(row['difference'])} [{formatter(row['lo'])}, {formatter(row['hi'])}]"


def table(headers, rows):
    head = "".join(f"<th scope=col>{escape(str(x))}</th>" for x in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{escape(str(x))}</td>" for x in r) + "</tr>" for r in rows
    )
    return f'<div class="scroll"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


LABEL = {
    "aa": "A/A · efecto nulo",
    "benefit": "Recordatorio beneficioso",
    "harm": "Efecto perjudicial",
    "complaint": "Aumento de quejas",
    "mde": "Efecto mínimo detectable",
}
REASONS = {
    "payment_above_minimum": "El límite inferior de pago no supera 1 pp",
    "cash_above_zero": "El límite inferior de caja no supera cero",
    "complaints_below_margin": "El límite superior de quejas alcanza o supera 0,5 pp",
    "all_prespecified_gates_pass": "Las tres condiciones se cumplen",
}


def render(folder):
    folder = Path(folder)
    all_cases = read(folder / "cases.json")
    case = all_cases["benefit"]
    stats = case["estimates"]
    arm = stats["arms"]
    payment = stats["payment"]
    mc = read(folder / "monte_carlo.json")
    incident = all_cases["loss"]
    evidence = read(folder / "trace.json")
    rows = []
    for name in ["aa", "benefit", "harm", "complaint", "mde"]:
        c = all_cases[name]
        est = c["estimates"]
        row = [LABEL[name], c["state"]]
        if est:
            row.extend(
                [
                    bounds(est["payment"], pp),
                    bounds(est["complaint"], pp),
                    bounds(est["net_cash_cop"], lambda v: num(v, 0)),
                    ". ".join(REASONS.get(r, r) for r in c["reasons"]),
                ]
            )
        else:
            row.extend(["—", "—", "—", ", ".join(c["reasons"])])
        rows.append(row)

    def rate(r):
        return num(100 * r, 1) + " %"

    values = {
        "primary": case["state"],
        "delta": pp(payment["difference"]),
        "interval": f"{pp(payment['lo'])} a {pp(payment['hi'])}",
        "cash": num(stats["net_cash_cop"]["difference"], 0),
        "guard": pp(stats["complaint"]["hi"]),
        "n": num(sum(a["n"] for a in arm.values()), 0),
        "arm_table": table(
            ["Asignación", "Cuentas", "Intentos", "Entregados", "Pagos completos", "Quejas"],
            [
                [label, *[arm[a][k] for k in ["n", "attempts", "delivered", "paid", "complained"]]]
                for a, label in [("C", "Habitual"), ("T", "Habitual + adicional")]
            ],
        ),
        "cases": table(
            [
                "Escenario",
                "Decisión",
                "Pago · IC 95 %",
                "Quejas · IC 95 %",
                "Caja por cuenta · COP e IC",
                "Motivo",
            ],
            rows,
        ),
        "bad": pp(case["comparison"]["delivered_minus_control"]),
        "costs": table(
            ["Costo por intento", "Caja incremental · COP por cuenta e IC"],
            [
                [k, bounds(v, lambda x: num(x, 0))]
                for k, v in sorted(stats["cost_sensitivity_cop"].items(), key=lambda kv: int(kv[0]))
            ],
        ),
        "loss": incident["checks"]["missing_outcomes"],
        "miss_c": incident["checks"]["complete_join"]["C"],
        "miss_t": incident["checks"]["complete_join"]["T"],
        "srm": f"{incident['checks']['srm_p_join']:.2e}",
        "mc_table": table(
            [
                "Verdad de pago",
                "Réplicas",
                "SRM inválidos",
                "Rechazo de cero",
                "Cobertura IC",
                "ship (todos)",
            ],
            [
                [
                    f"{LABEL[k]} · {pp(v['truth_payment'])}",
                    v["n_replicas"],
                    v["invalid_srm"],
                    rate(v["reject_zero"]["rate_all"]),
                    rate(v["cover"]["rate_all"]),
                    rate(v["ship"]["rate_all"]),
                ]
                for k in LABEL
                if (v := mc["scenarios"][k])
            ],
        ),
        "power": rate(mc["power"]["approx_power_at_planned_n"]),
        "trace": table(
            [
                "Cuenta sintética",
                "Variante",
                "Asignación UTC",
                "Intentos",
                "Entregas",
                "Pago a 14 días",
                "Disponible desde",
            ],
            [
                [
                    evidence["account_id"],
                    evidence["variant"],
                    evidence["assigned_at"],
                    evidence["attempts"],
                    evidence["delivered"],
                    "Sí" if evidence["paid"] else "No",
                    evidence["available_at"],
                ]
            ],
        ),
    }
    html = Template((Path(__file__).parent / "report.html").read_text(encoding="utf8")).substitute(
        values
    )
    (folder / "index.html").write_bytes(html.encode())
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
