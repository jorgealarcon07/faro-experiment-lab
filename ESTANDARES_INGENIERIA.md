# Estándares de ingeniería · Experimentos Faro

Vigentes desde el 22 de noviembre de 2026. El protocolo v1 queda comprometido en Git antes de simular resultados. La unidad es una cuenta elegible con una obligación sintética en COP.

| Área | Práctica y verificación |
|---|---|
| Arquitectura | Separar inscripción, simulación, adaptadores de archivos/SQL, controles de validez, estadística y consumo. El evaluador solo recibe observaciones y protocolo. Verificar dependencias y ejecutar cada etapa desde la CLI. |
| Diseño experimental | Congelar antes de generar resultados el horizonte, reloj, métricas, hipótesis, tamaño, decisión, semillas y métodos. Mantener ITT por asignación incluyendo los fallos de entrega. Contar cuentas a ambos lados de cada unión. |
| Configuración | Configuración versionada, Python 3.12 y dependencias fijadas. Conexión mediante PG*, contraseña local fuera del repositorio y los logs. Verificar instalación, pip check y ejecución desde una copia limpia. |
| Contratos y calidad | Namespaces sintéticos, dinero entero en COP, hora UTC y comprobación de huellas y esquemas. Persistir asignación inmutable. Distinguir falta de evento, cero explícito y observación futura. Probar cambio de variante, duplicados, pérdida diferencial y reloj incompatible. |
| Reproducibilidad | Semillas registradas, verdad generadora separada, hash canónico de archivos y tabla por cuenta. Congelar el dictamen por corte y versión de entrada. Probar repetición, linaje y recuperación con PostgreSQL real. |
| Inferencia | IC bilateral de Newcombe, curva de potencia antes de observar, guardrail y caja con incertidumbre. Comprobar con fixture analítico, fórmula independiente y 1.000 réplicas por escenario. Conservar todas las semillas y los bloqueos en denominadores explícitos. |
| Seguridad y licencias | Datos propios sintéticos CC0, código MIT, SQL parametrizado, sin servicio externo de mensajería. Consumidor de decisiones agregadas con rol lector. Revisar privilegios y contenido de los paquetes. |
| Publicación y errores | Registro transaccional por ejecución con idempotencia y detección de conflicto. Versiones corregidas conservan el incidente y apuntan a su antecedente. Una interrupción debe dejar intacta la versión anterior. |
| Observabilidad | Logs de etapa, identificadores de ejecución, estado y conteos. Ningún efecto estimado para pending o invalid. Guardar señales SRM, madurez, cobertura de eventos e informe de decisiones. |
| Pruebas y CI | Unitarias de fórmulas, aleatorización y contratos. Integración y E2E sobre PostgreSQL, reintento y escenarios adversos. CI por PR con fixture y release con batería completa. Distinguir ejecución local y remota. |
| Operación y mantenimiento | CLI, PostgreSQL nativo y configuración Compose. Documentar restauración, cambios de protocolo, límites, atribución, recursos y pasos de demo. HTML offline, métricas legibles por máquina y caso de estudio. |
| Git y alcance | Commits revisables, repo independiente, sin publicación remota. Cerrar con evidencia, paquete verificable y estado del plan. |
