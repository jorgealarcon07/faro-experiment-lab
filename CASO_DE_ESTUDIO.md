# Caso de estudio · Un recordatorio adicional bajo prueba

[English](CASE_STUDY.md)

**Decisión.** Una responsable de operaciones quiere saber si enviar un recordatorio adicional adelanta suficientes pagos para justificar el costo y el posible aumento de quejas. El equipo de datos necesita distinguir entre un recordatorio que funciona y un sistema que observa mejor a quienes recibieron el mensaje. [Informe interactivo](reports/release/index.html)

## Cómo se planteó el ensayo

Congelé el protocolo, las semillas y los umbrales antes de generar resultados. La asignación fue Bernoulli 50/50 sobre cuentas elegibles. Cada cuenta tiene una obligación sintética de 50.000 COP. A los 14 días se cierra el horizonte y se reservan dos días adicionales para recibir eventos. La decisión exige superar 1 punto porcentual de pago con el límite inferior del intervalo, caja incremental positiva con ese mismo límite y un límite superior de quejas inferior a 0,5 puntos. El cálculo de potencia dio 6.508 cuentas por brazo para detectar 2 puntos frente a cero. Se conservaron las 20.000 previstas. [Protocolo](experiment_protocols/v1.json) · [Potencia previa](experiment_protocols/power_before_run.json)

## Resultado observado en el laboratorio

En el escenario beneficioso, los controles tuvieron 2.003 pagos completos entre 10.042 cuentas y los tratados 2.315 entre 9.958. De los 9.958 intentos adicionales se entregaron 7.543. Se mantuvieron en tratamiento las 2.415 cuentas cuya entrega falló. La diferencia ITT fue **+3,30 puntos porcentuales**, IC 95 % **[+2,16, +4,44]**. El límite superior de quejas fue **+0,20 puntos**. La caja incremental estimada bajo el supuesto de 100 COP por intento fue **1.551 COP por cuenta asignada a tratamiento**, IC aproximado **[981, 2.120] COP**. Los tres criterios produjeron `ship`. El escenario de mayor tasa de quejas produjo `hold`. [Decisiones y supuestos](reports/release/cases.json)

Restringir el grupo tratado a mensajes entregados habría dado **+5,93 puntos**. Incluso en A/A, con efecto generador cero, esa comparación dio +2,29 puntos y la comparación por asignación +0,29. Las cuentas de menor riesgo tienen simultáneamente mayor probabilidad de pago y mayor probabilidad de recibir el recordatorio. La selección por entrega introduce esa diferencia desde el diseño del ejemplo.

## El incidente que cambia la recomendación

Retiré de una copia observada los resultados de 3.250 cuentas tratadas y conservé el registro de asignaciones. La aleatorización registrada seguía equilibrada (p = 0,553). La unión analítica quedó con 10.042 controles y 6.708 tratados (SRM p ≈ 2,44 × 10⁻¹⁴⁶). El analizador guardó `invalid` con los motivos y suprimió estimaciones. Restaurar los resultados en un lote nuevo permitió cerrar el experimento. Ambos dictámenes siguen consultables y enlazados. Reenviar intentos con el mismo ID y otra hora de recepción conservó idéntica la tabla por cuenta. [Manifiestos e historial](reports/release/manifests.json) · [Verificación](reports/release/verification.json)

## Qué aporta la simulación

En 1.000 réplicas A/A el método rechazó cero en 46 ocasiones, **4,6 %** con error estándar Monte Carlo de unos **0,66 puntos porcentuales**. En 1.000 réplicas de beneficio real simulado de +3 puntos, el **93,5 %** pasó el mínimo primario y el **91,2 %** cumplió la regla operativa completa. Se conservaron las réplicas bloqueadas por SRM en el denominador operativo. La cobertura observada en los cinco escenarios osciló entre **93,0 % y 96,6 %**. [Calibración, sesgo y errores Monte Carlo](reports/release/monte_carlo.json)

La decisión de laboratorio depende de la definición de pago, la captura completa del resultado y el horizonte de 14 días. Un pago adelantado podría haberse realizado de todos modos más tarde. La simulación permite medir si el procedimiento se comporta como se diseñó. Para decidir una política comercial seguirían haciendo falta un piloto autorizado, costos reales y una evaluación de seguimiento.

[Video narrado](assets/web/walkthrough.mp4) · [Captura principal](assets/web/decision.png) · [Incidente](assets/web/incidente.png) · [Calibración](assets/web/calibracion.png) · [Guía de ejecución](README.es.md).
