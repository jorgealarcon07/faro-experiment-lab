# Operación y respuesta a incidentes

## Preparar e inscribir

Use un directorio de trabajo por experimento y una base dedicada. Configure el entorno descrito en el [README](../README.md). `faro-exp power` y `faro-exp enroll` funcionan localmente. La etapa `register` inicializa el esquema, valida elegibilidad y asignación y entrega `registered` o `replay`. Cada inscripción es inmutable. Antes de procesar outcomes confirme que el SHA de inscripción del paquete observado coincide con el que se registró.

Con el esquema inicializado, un administrador puede aplicar `psql -v ON_ERROR_STOP=1 -f scripts/access.sql`. El grupo NOLOGIN `faro_exp_reader` obtiene SELECT sobre la vista `faro_exp.decisions`. Se asigna a los usuarios que solo deben ver informes. Reserve escritura y la CLI de trazas para operadores autorizados. La aceptación comprueba en PostgreSQL que el lector puede consultar una decisión y recibe denegación al leer outcomes crudos. [SQL de privilegios](../scripts/access.sql)

## Interpretar el estado

| Estado | Qué hacer |
|---|---|
| pending | Consultar final_at. Esperar hasta el cierre de horizonte y margen. No calcular diferencias de eficacia a partir del progreso. |
| invalid | Inspeccionar reasons, registered, recorded, complete_join y missing_outcomes. Conservar los archivos y el run problemático. |
| hold | Leer las tres condiciones y la precisión de los intervalos. El escenario A/A tampoco prueba equivalencia. |
| ship | Resultado del procedimiento simulado con el protocolo fijado. Registrar qué suposición de costo y qué guardrail sostienen la decisión. |

Un dictamen `invalid` o `pending` es una ejecución correctamente registrada y devuelve código de proceso 0. La automatización debe leer `record.state`. Un fallo de contrato, conexión, inscripción o colisión devuelve 2 y un diagnóstico de etapa. Los logs de base incluyen clase de error y SQLSTATE. Los parámetros de autenticación se mantienen fuera de Git.

## Reparar una entrega

1. Identifique en `cases.json` o en la vista los conteos de asignación y la pérdida tras la unión. Si existen fallos de reloj, compare attempted_at y received_at o window_end y available_at.
2. Restaure los datos de origen en un paquete nuevo. Mantenga la inscripción y los IDs de intento. La herramienta comprueba la huella de cada archivo. Un lote cuya integridad falla se rechaza antes de alterar PostgreSQL.
3. Ejecute `analyze` indicando el run bloqueado en `--parent` y un corte igual o posterior. El padre debe pertenecer al mismo experimento y tener estado pending o invalid. Falta diferencial o cambio de variante impiden publicar una estimación.
4. Compare denominadores, efectos y huellas con el registro anterior. El antecedente conserva su decisión original. Si el cliente perdió la respuesta tras el commit, repita exactamente la solicitud. El ID determinista devuelve la ejecución existente.

La base no realiza reenvío de mensajes. Las operaciones de recuperación se limitan al análisis. Si ya existe una tabla ITT terminal diferente, se exige revisar el caso y diseñar una nueva versión de estudio antes de interpretar otro resultado.

## Comprobaciones SQL para la mesa de operaciones

```sql
SELECT experiment_id, state, as_of, run_id, parent_run,
       record->'checks'->'registered' AS asignadas,
       record->'checks'->'complete_join' AS con_resultado
FROM faro_exp.decisions
ORDER BY experiment_id, as_of, run_id;
```

El archivo de trazabilidad muestra una cuenta con intento fallido. En un corte anterior a disponibilidad la CLI devuelve paid nulo. En el cierre, la cuenta permanece en el denominador tratado y su outcome binario es visible. [Traza reproducida](../reports/release/trace.json)

## Despliegue y mantenimiento

La demo nativa inicia un clúster con contraseña efímera y acceso loopback bajo `.runtime/`. El proceso detiene solo su propio servidor al salir. Compose almacena base y salidas en volúmenes nombrados. `docker compose down` detiene el entorno. El comando `clean --confirm` solo admite un directorio de reporte marcado y retira nombres de salida conocidos. El chequeo de aceptación debe usar una base nueva porque comprueba la primera publicación concurrente.

Para recuperar un entorno persistente, conserve las revisiones de Git, protocolos, paquetes originales y copia PostgreSQL obtenida con `pg_dump -Fc`. Restaure en una base nueva, prepare los roles y valide los hashes antes de consumirla. Los contratos y el protocolo se fijan mediante lock. Un cambio de unidad, ventana, métrica o umbral requiere una nueva versión anterior a observar nuevos resultados. Validar dependencias actualizadas exige ejecutar pruebas, regenerar el oráculo, repetir la calibración y revisar las diferencias en una rama propia.

Se comprobaron PostgreSQL nativo 17.12, Python 3.12, el informe en Chromium y los roles SQL. Docker Compose y el workflow de GitHub Actions incluyen las rutas de despliegue y comprobación, pendientes de ejecución en sus respectivos entornos. [Compose](../compose.yaml) · [CI](../.github/workflows/ci.yml)
