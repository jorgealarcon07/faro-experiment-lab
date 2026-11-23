# Faro · Evaluación de recordatorios de pago

¿Conviene añadir un recordatorio a la comunicación habitual? Faro asigna cuentas sintéticas al azar y evalúa pagos a 14 días, costo de los intentos y quejas. El sistema entrega una decisión, los conteos que la justifican y un historial si hubo que reparar datos. [Abrir el informe](reports/release/index.html) · [Caso de estudio](CASO_DE_ESTUDIO.md) · [Video narrado en inglés](assets/web/walkthrough.mp4)

**Resultado del escenario beneficioso.** En 20.000 cuentas simuladas, pagaron 2.315 de 9.958 cuentas tratadas y 2.003 de 10.042 controles. La diferencia por asignación fue **+3,30 puntos porcentuales**, con IC 95 % **[+2,16, +4,44]**. El aumento de quejas quedó bajo el margen predefinido y el límite inferior de caja fue positivo. La recomendación de laboratorio fue `ship`. Una copia del mismo experimento con 3.250 resultados de tratamiento perdidos quedó `invalid`. [Decisiones y denominadores](reports/release/cases.json) · [Manifiestos](reports/release/manifests.json)

**English brief.** A reproducible experiment pipeline for a capacity-conscious payments team. Immutable assignment, event-time and arrival-time checks, intention-to-treat estimation and a complaint guardrail determine whether the simulated evidence supports an extra reminder. A fixed-horizon study and 5,000 independent replications distinguish an operational recommendation from a statistically detectable effect. All accounts and commercial assumptions are synthetic. [English walkthrough transcript](assets/web/walkthrough.en.txt)

## Recorrido para una entrevista

1. Abra el [informe offline](reports/release/index.html). Compare la estimación por asignación con la comparación restringida a mensajes entregados.
2. Consulte las [condiciones fijadas antes del ensayo](experiment_protocols/v1.json) y el [cálculo previo de potencia](experiment_protocols/power_before_run.json).
3. Siga la [cuenta 3](reports/release/trace.json). Se asignó a tratamiento, se cobró un intento y la entrega falló. Su pago sigue en el denominador tratado.
4. Busque `early`, `loss` y `benefit` en las [decisiones CSV](reports/release/decisions.csv) y siga el campo `parent_run` en los manifiestos. En una tabla incompleta el sistema retiene el motivo y deja vacío el efecto.
5. Compare rechazo frente a cero y frecuencia de `ship` en la [lectura de calibración y potencia](docs/CALIBRACION.md). El [resumen Monte Carlo](reports/release/monte_carlo.json) y las [5.000 réplicas individuales](reports/release/replicas.csv) permiten repetir la cuenta.

## Instalación

Trabaje en la raíz del repositorio. Para revisar el informe basta un navegador local. Para reconstruirlo use CPython 3.12 de 64 bits y PostgreSQL 17. La primera instalación requiere acceso a las dependencias.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.lock
python -m pip install --no-build-isolation --no-deps -e .
python -m pip check
faro-exp validate
```

En Linux, cree el entorno con `python3.12 -m venv .venv` y actívelo con `source .venv/bin/activate`. El comando `faro-exp` también está disponible como `python -m faro_exp.cli` o mediante [el script PowerShell](scripts/faro.ps1). Los contratos, protocolos y rutas predeterminadas se resuelven desde la raíz.

## Ejecutar la demo completa

Con los binarios de PostgreSQL instalados, esta ruta crea un clúster privado en loopback, ejecuta cinco experimentos y sus casos adversos y detiene el servidor. Ajuste la ruta de los binarios si corresponde. El informe reconstruido queda en `local/demo/index.html`.

```powershell
python scripts/native_pg.py --bin "C:\Program Files\PostgreSQL\17\bin" -- -m faro_exp.cli demo
faro-exp validate --out local/demo
```

Si ya dispone de una base **dedicada**, configure `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER` y la autenticación de libpq. El propietario inicial necesita crear el esquema del proyecto. Ejecute `faro-exp demo`. El archivo [.env.example](.env.example) describe las variables. Para PostgreSQL en Compose, defina `PGPASSWORD` localmente y ejecute `docker compose run --build --rm app demo`. Los archivos residen en el volumen `laboutput`. Para copiarlos, use `docker compose run --name faro-exp-export app demo`, `docker cp faro-exp-export:/app/local/demo ./demo-export` y `docker rm faro-exp-export`. La aceptación publicada corresponde a la ruta nativa.

## Reproducir un incidente con 200 cuentas

Con una base dedicada en marcha y las variables PG configuradas:

```powershell
faro-exp register --enrollment data/fixtures/enrollment
faro-exp analyze --input data/fixtures/clean --as-of 2026-01-08T00:00:00Z --out local/early.json
$earlyRun = (Get-Content -Raw local/early.json | ConvertFrom-Json).record.run_id
faro-exp analyze --input data/fixtures/loss --as-of 2026-01-17T00:00:00Z --parent $earlyRun --out local/incident.json
$incidentRun = (Get-Content -Raw local/incident.json | ConvertFrom-Json).record.run_id
faro-exp analyze --input data/fixtures/clean --as-of 2026-01-17T00:00:00Z --parent $incidentRun --out local/corrected.json
$finalRun = (Get-Content -Raw local/corrected.json | ConvertFrom-Json).record.run_id
faro-exp trace --run $finalRun --account 200 --out local/account.json
```

El fixture pasa por `pending → invalid → hold`. En el cierre íntegro tiene 20 pagos entre 100 controles y 23 entre 100 tratados. Su tamaño ilustra el cálculo y la recuperación. [Oráculo del fixture](data/fixtures/oracle.json)

Para crear desde cero otro experimento, use `faro-exp enroll --scenario benefit --experiment demo-b --out local/b/enrollment`, registre esa carpeta y ejecute `faro-exp observe --enrollment local/b/enrollment --out local/b/clean`. Las opciones de instrumentación incluyen `--fault loss` y `--fault duplicates`. El análisis consume archivos observados y la asignación persistida en PostgreSQL. La generación de datos y la batería Monte Carlo funcionan sin base de datos.

## Verificación y operación

```powershell
ruff check src tests scripts
ruff format --check src tests scripts
python -m pytest -q
faro-exp power --out local/design
faro-exp calibrate --out local/calibration
python scripts/native_pg.py --bin "C:\Program Files\PostgreSQL\17\bin" -- scripts/acceptance.py
```

El último comando requiere un clúster de verificación nuevo. Ejecuta la suite, prueba dos envíos concurrentes, permisos de lectura y reconstruye la release. Compara huellas para decisiones, tablas por cuenta y todas las réplicas. Los tests SQL usan `PGDATABASE`. [JUnit](reports/tests.xml) · [Aceptación](reports/acceptance.json) · [Estándares](ESTANDARES_INGENIERIA.md) · [Comprobación de cumplimiento](docs/CUMPLIMIENTO.md)

`faro-exp report --out local/demo` reconstruye HTML y CSV a partir de la evidencia. `faro-exp clean --confirm --out local/demo` elimina exclusivamente las salidas conocidas de un reporte propio. La documentación explica gestión de roles, claves, reintentos y restauración. [Arquitectura y contratos](docs/ARQUITECTURA.md) · [Runbook](docs/RUNBOOK.md)

Los resultados miden el comportamiento del método bajo supuestos simulados. La eficacia, la tolerancia a quejas y el costo de una operación real necesitarían evidencia prospectiva propia. [Datos y fuentes metodológicas](DATA_SOURCES.md)
