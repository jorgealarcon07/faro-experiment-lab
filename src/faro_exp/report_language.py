"""Localized labels for the offline report."""

import re
from html import escape

COPY = {
    "text_title": ("Faro · Ensayo de recordatorios", "Faro · Payment reminder experiment"),
    "text_brand": ("FARO / EXPERIMENTACIÓN", "FARO / EXPERIMENTATION"),
    "text_heading": (
        "¿Conviene enviar otro recordatorio de pago?",
        "Is an extra payment reminder worth sending?",
    ),
    "text_intro": (
        "Ensayo aleatorio con datos sintéticos. La decisión combina pagos completos a 14 "
        "días, costo por intento y un límite al aumento de quejas.",
        "A randomized experiment with synthetic data. The decision combines full payment "
        "within 14 days, cost per attempt and a limit on extra complaints.",
    ),
    "text_sections": ("Secciones", "Sections"),
    "text_decision": ("Decisión", "Decision"),
    "text_scenarios": ("Escenarios", "Scenarios"),
    "text_incident": ("Incidente", "Incident"),
    "text_calibration": ("Calibración", "Calibration"),
    "text_trace": ("Trazabilidad", "Trace"),
    "text_benefit": ("Escenario beneficioso · $primary", "Favorable scenario · $primary"),
    "text_assigned": (
        "Se asignaron $n cuentas al recordatorio habitual o al habitual más un "
        "intento adicional. Cada cuenta cuenta en el brazo que le tocó, incluso si la "
        "entrega falló.",
        "I assigned $n accounts to the usual reminder or to the usual reminder plus "
        "one extra attempt. Every account stays in its assigned group, even if "
        "delivery failed.",
    ),
    "text_payment": ("Pago a 14 días", "Payment within 14 days"),
    "text_ci": ("IC 95 % de $interval", "95% CI $interval"),
    "text_cash": (
        "Caja incremental por cuenta de tratamiento",
        "Incremental cash per treatment account",
    ),
    "text_cost": ("Supuesto de 100 COP por intento", "Assumes 100 COP per attempt"),
    "text_guard": ("Límite superior del aumento de quejas", "Upper bound on extra complaints"),
    "text_margin": ("Margen predefinido de 0,50 pp", "Prespecified limit of 0.50 pp"),
    "text_delivered": (
        "Comparar solo entregados con control daría $bad. La probabilidad de entrega "
        "depende del riesgo previo. El análisis principal conserva la asignación "
        "original.",
        "Comparing only successful deliveries with the control group gives $bad. "
        "Delivery depends on prior risk. The primary analysis keeps the original "
        "assignments.",
    ),
    "text_show_cost": (
        "Ver sensibilidad al costo por intento",
        "View sensitivity to cost per attempt",
    ),
    "text_scenario_heading": ("Qué cambia la decisión", "What changes the decision"),
    "text_thresholds": (
        "Para recomendar el envío, el límite inferior de pago debe superar 1 punto "
        "porcentual, el de caja debe ser positivo y el superior de quejas debe "
        "quedar por debajo de 0,5 puntos.",
        "Recommending the reminder requires a lower bound above one percentage "
        "point for payments, a positive lower bound for cash and an upper bound "
        "below 0.5 percentage points for extra complaints.",
    ),
    "text_intervals": (
        "Los intervalos corresponden al método de Newcombe. La caja representa un "
        "flujo simulado a 14 días, con 50.000 COP por pago completo. El experimento "
        "carece de evidencia sobre recuperación definitiva o rentabilidad comercial.",
        "The report uses Newcombe intervals. Cash represents simulated 14-day cash "
        "flow, with 50,000 COP per full payment. Long-term recovery and commercial "
        "profitability would require additional evidence.",
    ),
    "text_incident_heading": (
        "Cuando desaparecen resultados de tratamiento",
        "When treatment outcomes go missing",
    ),
    "text_incident_path": (
        "pending → invalid → nueva evaluación corregida",
        "pending → invalid → new run with corrected data",
    ),
    "text_incident_note": (
        "El primer corte precede a la maduración. En el corte final de una copia "
        "dañada faltan $loss resultados. La unión contiene $miss_c controles y "
        "$miss_t tratamientos (SRM p = $srm). El evaluador bloquea la "
        "estimación. La corrección conserva la asignación y enlaza la nueva "
        "ejecución con el incidente.",
        "The first check happens before all outcomes are available. At the final "
        "check, the damaged copy is missing $loss outcomes. The joined data "
        "contain $miss_c control accounts and $miss_t treatment accounts (sample "
        "ratio mismatch p = $srm). The evaluator blocks the estimate. The "
        "corrected run preserves the assignment and links back to the incident.",
    ),
    "text_calibration_heading": (
        "¿Con qué frecuencia acierta el método?",
        "How often does the method make the right call?",
    ),
    "text_power": (
        "1.000 réplicas independientes por escenario. La potencia aproximada para "
        "detectar 2 pp frente a cero es $power. La columna de recomendación incorpora "
        "también el mínimo empresarial, la caja, las quejas y el control de asignación.",
        "There are 1,000 independent replications per scenario. Approximate power to "
        "detect a 2 pp difference from zero is $power. The recommendation also accounts "
        "for the business threshold, cash, complaints and the assignment check.",
    ),
    "text_srm": (
        "Rechazo y cobertura se calculan sobre todas las réplicas para diagnosticar el "
        "estimador. Un SRM invalida el uso operativo de esa réplica. El JSON incluye tasas "
        "condicionadas, sesgo y error Monte Carlo.",
        "Rejection and coverage use all replications to assess the estimator. A sample "
        "ratio mismatch invalidates that replication for operational use. The JSON "
        "includes conditional rates, bias and Monte Carlo error.",
    ),
    "text_trace_heading": ("De la asignación al resultado", "From assignment to outcome"),
    "text_available": (
        "Los campos de resultado se hacen visibles una vez alcanzado su tiempo de "
        "disponibilidad. Los registros por cuenta son artificiales y pertenecen "
        "exclusivamente al experimento de Faro.",
        "Outcome fields appear when they become available. All account records are "
        "synthetic and belong to the Faro experiment.",
    ),
    "text_checks": ("Decisiones y controles", "Decisions and checks"),
    "text_manifests": ("Manifiestos", "Manifests"),
    "text_replicates": ("5.000 réplicas", "5,000 replications"),
    "text_protocol": ("Protocolo", "Protocol"),
    "py_aa": ("A/A · efecto nulo", "A/A · no effect"),
    "py_benefit": ("Recordatorio beneficioso", "Beneficial reminder"),
    "py_harm": ("Efecto perjudicial", "Harmful effect"),
    "py_complaint": ("Aumento de quejas", "Increase in complaints"),
    "py_mde": ("Efecto mínimo detectable", "Minimum detectable effect"),
    "py_payment_below": (
        "El límite inferior de pago no supera 1 pp",
        "The payment lower bound does not exceed 1 pp",
    ),
    "py_cash_below": (
        "El límite inferior de caja no supera cero",
        "The cash lower bound does not exceed zero",
    ),
    "py_complaint_above": (
        "El límite superior de quejas alcanza o supera 0,5 pp",
        "The complaint upper bound reaches or exceeds 0.5 pp",
    ),
    "py_gates_pass": ("Las tres condiciones se cumplen", "All three conditions pass"),
    "py_assignment": ("Asignación", "Assignment"),
    "py_accounts": ("Cuentas", "Accounts"),
    "py_attempts": ("Intentos", "Attempts"),
    "py_delivered": ("Entregados", "Delivered"),
    "py_paid": ("Pagos completos", "Full payments"),
    "py_complaints": ("Quejas", "Complaints"),
    "py_control": ("Habitual", "Usual reminder"),
    "py_treatment": ("Habitual + adicional", "Usual reminder + extra attempt"),
    "py_scenario": ("Escenario", "Scenario"),
    "py_decision": ("Decisión", "Decision"),
    "py_payment_ci": ("Pago · IC 95 %", "Payment · 95% CI"),
    "py_complaints_ci": ("Quejas · IC 95 %", "Complaints · 95% CI"),
    "py_cash_ci": ("Caja por cuenta · COP e IC", "Cash per account (COP) and CI"),
    "py_reason": ("Motivo", "Reason"),
    "py_cost": ("Costo por intento", "Cost per attempt"),
    "py_incremental": (
        "Caja incremental · COP por cuenta e IC",
        "Incremental cash per account (COP) and CI",
    ),
    "py_truth": ("Verdad de pago", "True payment effect"),
    "py_replications": ("Réplicas", "Replications"),
    "py_invalid": ("SRM inválidos", "Invalid due to SRM"),
    "py_reject": ("Rechazo de cero", "Reject zero effect"),
    "py_coverage": ("Cobertura IC", "CI coverage"),
    "py_ship": ("ship (todos)", "ship (all replications)"),
    "py_synthetic": ("Cuenta sintética", "Synthetic account"),
    "py_variant": ("Variante", "Variant"),
    "py_assigned_utc": ("Asignación UTC", "Assigned (UTC)"),
    "py_deliveries": ("Entregas", "Deliveries"),
    "py_payment": ("Pago a 14 días", "Payment within 14 days"),
    "py_available": ("Disponible desde", "Available from"),
    "py_yes": ("Sí", "Yes"),
    "py_no": ("No", "No"),
    "py_ship_state": ("Enviar (ship)", "Send (ship)"),
    "py_hold_state": ("Retener (hold)", "Hold"),
    "py_invalid_state": ("Inválido (invalid)", "Invalid"),
    "py_pending_state": ("Pendiente (pending)", "Pending"),
}


REPORT_FILES = {"es": "index.html", "en": "index.en.html"}


def labels(language):
    if language not in REPORT_FILES:
        raise ValueError(f"Unsupported report language: {language}")
    column = 0 if language == "es" else 1
    return {key: pair[column] for key, pair in COPY.items()}


def localize(template, language):
    copy = labels(language)
    alternate = "en" if language == "es" else "es"
    html = {
        **{key: escape(value) for key, value in copy.items()},
        "lang": language,
        "other_lang": alternate,
        "other_file": REPORT_FILES[alternate],
        "other_label": "English" if alternate == "en" else "Español",
    }

    return re.sub(r"@@([a-z_]+)@@", lambda match: html[match[1]], template)
