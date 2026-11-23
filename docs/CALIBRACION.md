# Calibración del procedimiento experimental

Cada fila resume 1.000 experimentos independientes de 20.000 cuentas. El sesgo es la media de la diferencia estimada menos la verdad generadora, en puntos porcentuales (pp). El error estándar Monte Carlo (EE) cuantifica la precisión de esta batería finita. El rechazo de cero se calcula cuando el intervalo bilateral de pago excluye cero. La recomendación ship exige superar los controles y las tres condiciones empresariales.

| Escenario | ITT verdadero de pago | Sesgo en pp (EE) | Rechazo de cero | Cobertura 95 % | Bloqueos SRM | Recomendación ship |
|---|---:|---:|---:|---:|---:|---:|
| A/A | 0 pp | +0,0164 (0,0181) | 4,6 % | 95,4 % | 1 | 0 % |
| Beneficio | +3 pp | −0,0171 (0,0177) | 99,9 % | 96,6 % | 2 | 91,2 % |
| Perjuicio | −2 pp | +0,0176 (0,0173) | 96,0 % | 95,5 % | 4 | 0 % |
| Quejas | +3 pp | +0,0425 (0,0176) | 100,0 % | 95,9 % | 1 | 0 % |
| MDE | +2 pp | −0,0165 (0,0194) | 92,0 % | 93,0 % | 1 | 40,4 % |

El error tipo I bajo A/A fue 4,6 %, con EE de 0,66 pp, dentro de la banda diagnóstica predefinida de 3–7 %. La cobertura observada estuvo dentro de la banda 92–98 % en los cinco escenarios. Estas bandas corresponden a este generador y al tamaño simulado. Un valor observado de cero recomendaciones en 1.000 ensayos sigue siendo compatible con una probabilidad poblacional pequeña.

Para detectar +2 pp frente a cero, el cálculo previo predijo 93,49 % a 10.000 cuentas por brazo. El 92,0 % empírico tiene EE de 0,86 pp. La distancia de 1,49 pp equivale a unas 1,7 veces ese error. La aproximación de diseño usa brazos iguales y tamaño de efecto arcoseno. Las réplicas usan brazos de tamaño aleatorio y rechazo según el IC de Newcombe. No se modificaron semillas para acercar los dos cálculos.

Para un efecto verdadero de +3 pp sin incremento de quejas, el límite inferior de pago superó el umbral empresarial en 935 de 1.000 ensayos. Al exigir además caja, límite de quejas y proporción de muestra válida se obtuvieron 912 recomendaciones, con EE de 0,90 pp. En el escenario de +3 pp de pago y +1,2 pp de quejas, las 1.000 réplicas excluyeron cero para el pago y ninguna recomendó aplicar el recordatorio. Esta última distinción explica por qué el informe separa potencia estadística de probabilidad de decisión.

Se pueden recalcular todos los denominadores desde el CSV usando scenario, valid, cover, reject_zero, primary_above_minimum y ship. El JSON conserva también las tasas restringidas a experimentos válidos, la semilla raíz, el índice de flujo y los errores Monte Carlo. [Réplicas](../reports/release/replicas.csv) · [Resumen numérico](../reports/release/monte_carlo.json) · [Protocolo preregistrado](../experiment_protocols/v1.json)
