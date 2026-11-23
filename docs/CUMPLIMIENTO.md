# Verificación de ingeniería · 22 de noviembre de 2026

| Práctica | Evidencia de cierre |
|---|---|
| Estándares y protocolo anteriores a código y resultados | Primer commit `4e0ea60`. [Estándar](../ESTANDARES_INGENIERIA.md) · [Protocolo](../experiment_protocols/v1.json) · [Potencia previa](../experiment_protocols/power_before_run.json) |
| Procedencia y licencias | Simulador propio con semilla independiente por etapa. Fixtures CC0, proyecto MIT y supuestos explícitos. [Origen](../DATA_SOURCES.md) · [Fixture manual](../data/fixtures/oracle.json) |
| Identidad, contratos y SQL | Registro inmutable por cuenta, claves únicas y verificaciones contra copia observada, integridad de bytes y tipos. [Contratos](../contracts/v1) · [Tabla por cuenta](../src/faro_exp/itt.sql) |
| Inferencia | Oráculo de conteos calculable a mano, prueba independiente de Wilson/Newcombe y separación entre estimador y verdad generadora. [Pruebas](../tests/test_inference.py) · [Verdad poblacional](../tests/truth/scenarios.json) |
| Tiempo, calidad y elegibilidad | Tests sobre reloj, corte sin etiquetas, pérdida diferencial, intento faltante, duplicación, asignación incompatible y cuenta huérfana. [Pruebas PostgreSQL](../tests/test_database.py) · [Controles ejecutados](../reports/release/cases.json) |
| Recuperación | Transacción revertida antes de commit, doble envío concurrente, mismo ID económico con recepción tardía y filiación de incidente reparado. [Aceptación](../reports/acceptance.json) · [Manifiestos](../reports/release/manifests.json) |
| Reproducibilidad y calibración | Cinco escenarios con semillas congeladas. Las 5.000 réplicas, las tablas por cuenta y las decisiones se reconstruyeron con huellas idénticas en aceptación. [Réplicas](../reports/release/replicas.csv) · [Métricas y Monte Carlo SE](../reports/release/monte_carlo.json) |
| Seguridad y consumo | Vista agregada de lectura, denegación efectiva de acceso a crudos, credenciales solo en entorno y SQL parametrizado. [Permisos](../scripts/access.sql) · [Aceptación](../reports/acceptance.json) |
| Automatización y pruebas | Lock completo, instalación aislada, Ruff, pytest y aceptación desde CLI real. [JUnit](../reports/tests.xml) · [CI](../.github/workflows/ci.yml) |
| Recursos y evidencia visual | Medición del proceso Python durante generación, ingestión, decisiones y Monte Carlo. Se comprobó navegación, sensibilidad de costos y móvil. [Recursos](../reports/release/resources.json) · [Navegador](../reports/browser.json) · [Video](../assets/web/walkthrough.mp4) |

La medición de release fue de 25,62 s y 224,5 MiB de RSS máximo muestreado para Python. Los archivos de entrada generados ocuparon 25.148.036 bytes. La medición excluye la memoria del servidor PostgreSQL, la instalación, el arranque del clúster y la captura audiovisual. Los escenarios y sus métricas son simulados. La generalización a clientes y costos reales exige evaluación prospectiva.

La ruta nativa se ejecutó de extremo a extremo. La configuración de Docker Compose y la ejecución remota de GitHub Actions siguen pendientes.
