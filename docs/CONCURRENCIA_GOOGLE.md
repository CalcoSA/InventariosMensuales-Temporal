# Concurrencia Google — implementación y resultados

Validación del 18 de septiembre de 2026: 24 escenarios aprobados, dentro de una
suite completa de 168 pruebas. Todas las cargas usan fakes; no representan una
prueba de capacidad contra Google real. Datos reproducibles en
[concurrency_results.json](concurrency_results.json).

Inventario Uno a Uno e Inventario Mensual usan la misma cuenta Google corporativa,
pero operativamente no se utilizan simultáneamente. Se prueban exclusivamente
10, 20, 36 y 40 usuarios de Inventario Mensual; no se simulan 72 usuarios.

## Caché y consultas compartidas

ReadCache es thread-safe, limitada a 256 entradas y usa reloj monotónico. Cada
carga concurrente del mismo recurso comparte una Future (single-flight); los
consumidores reciben copias, los errores no se cachean y las claves distintas
pueden cargar simultáneamente.

| Recurso | TTL | Clave |
|---|---:|---|
| Archivos/lista PDV | 600 s | Lista de bases |
| Resolución del archivo | 21600 s | Nombre exacto del PDV |
| Carpeta hija de bases | 21600 s | Carpeta configurada |
| Productos y categorías derivadas | 600 s | ID del Spreadsheet |
| Conteos para pantalla/administración | 0 s | ID del Spreadsheet, solo solicitudes solapadas |

No se reutilizan conteos almacenados para decidir duplicados. Finalizar y limpieza
leen de nuevo dentro del bloqueo. La caché vive en RAM de cada proceso, sin Redis,
base de datos ni coordinación con Uno a Uno. No se comparte entre procesos.

## Llamadas por flujo

Cuenta de solicitudes REST sin OAuth, reintentos ni paginación adicional. Las
pruebas de contrato ejecutan los constructores oficiales de solicitudes sobre un
transporte simulado; las cargas cuentan las operaciones de los servicios fake.

| Flujo | Llamadas con caché fría | Con caché vigente |
|---|---:|---:|
| HTML y estado administrativo | 0 | 0 |
| Lista PDV | 2: carpeta + archivos | 0 |
| Categorías/productos, consulta directa | 3: carpeta + archivo + libro | 0 |
| Lista PDV → categorías → productos → cambio de categoría | 4 en total | 0 |
| Estados, consulta directa | 4: carpeta + archivo + catálogo + conteos | 1 lectura fresca |
| Finalizar | 4: carpeta + archivo + snapshot + batchUpdate | 2: snapshot + batchUpdate |
| Guardar borrador | 0 | 0 |
| Consolidado/plano con ID resuelto | 1 lectura | 1 lectura |
| CSV de un PDV | Listar bases + leer su libro; añade búsqueda de carpeta si está fría | 2 |

Inicio de la interfaz: dos llamadas para cargar la lista PDV; comprobar identidad
no llama a Google. Tras cargar esa lista, elegir PDV y obtener categorías/productos
añade dos llamadas (archivo y catálogo). Cambiar de categoría reutiliza ese catálogo:
cero llamadas adicionales para productos; refrescar estados añade una lectura fresca.
El presupuesto secuencial está comprobado en
`tests/test_inventory.py::test_google_calls_by_user_flow`. La tabla separa esos
servicios para no confundir llamadas de productos con las de estados.

En Finalizar, la misma lectura recupera catálogo y conteos; el batch crea/formatea
la hoja si falta y escribe el rango completo. No hay una llamada por fila/celda.
Un get con grid data conserva conjuntamente valores visibles, tipados, fechas y
metadatos; usar solo values.batchGet no cubre esas vistas en la misma petición.

40 guardados de PDV distintos con caché fría: 121 llamadas (1 carpeta + 40 archivos
+ 40 lecturas + 40 escrituras). Con todos los IDs resueltos serían 80 llamadas,
dos por Finalizar. Una ráfaga de 40 lecturas iguales comparte cuatro llamadas en
total en el escenario de prueba.

## Bloqueos y escrituras

FileLock por Spreadsheet coordina hilos y procesos del mismo host que compartan
.runtime/locks. Se prueba también exclusión entre procesos. Los PDV distintos no
comparten un bloqueo global de guardado. Limpieza utiliza el mismo bloqueo que
Finalizar. El generador y la preparación tienen bloqueos administrativos propios.

La transacción lectura/comprobación/escritura no protege frente a modificaciones
manuales, al Apps Script original o a instancias en otros hosts. El cambio operativo
a Python requiere un único escritor coordinado por base. No se incorporó
infraestructura distribuida ni se configuró despliegue.

## Reintentos y errores 429

Lecturas idempotentes: hasta cuatro intentos, ante 429/500/502/503/504. Esperas de
1, 2 y 4 segundos más jitter aleatorio [0,1). Los transportes HTTP son independientes
por operación; la carga/renovación OAuth se protege entre hilos.

Casos aprobados: 429 → 200, 429 → 429 → 200, cuatro 429 consecutivos y errores 5xx.
Chromium recorre los tres escenarios 429 con la política real de reintentos
y esperas simuladas: recuperación confirma una escritura y elimina el borrador;
agotamiento conserva borrador, botón habilitado y ausencia de pantalla de éxito.
Una escritura no confirmada tampoco se reintenta automáticamente y conserva borrador.

Las cargas normales registran cero 429 porque el fake no impone cuota. La inyección
de 429 es una prueba separada; no se afirma que Google real vaya a tener cero 429.

## Resultados medidos

Latencia artificial de 5 ms por operación de servicio e hilos sincronizados al inicio.
Los guardados distintos y duplicados contienen 40 productos por inventario;
las lecturas usan dos productos Bebidas y uno Cocina. El tiempo incluye ejecución
local y esperas de bloqueo. Se verifican UUID por envío, las 40 filas, los totales
y ausencia de filas mezcladas. El JSON registra el tamaño de cada escenario.
Los borradores se prueban en sesiones JavaScript aisladas con localStorage simulado;
sus flujos de interfaz también se verifican separadamente en Chromium.

| Usuarios | Flujo | Éxitos | Duplicados rechazados | Fallos | Tiempo s | Máx. espera s | Llamadas Google simuladas |
|---:|---|---:|---:|---:|---:|---:|---:|
| 10 | PDV, categorías, productos | 10 | 0 | 0 | 0.0404 | 0.0000 | 4 |
| 20 | PDV, categorías, productos | 20 | 0 | 0 | 0.0283 | 0.0000 | 4 |
| 36 | PDV, categorías, productos | 36 | 0 | 0 | 0.0331 | 0.0000 | 4 |
| 40 | PDV, categorías, productos | 40 | 0 | 0 | 0.0322 | 0.0000 | 4 |
| 10 | Finalizar PDV distintos (40 productos) | 10 | 0 | 0 | 0.0642 | 0.0000 | 31 |
| 20 | Finalizar PDV distintos (40 productos) | 20 | 0 | 0 | 0.1131 | 0.0160 | 61 |
| 36 | Finalizar PDV distintos (40 productos) | 36 | 0 | 0 | 0.1866 | 0.1090 | 109 |
| 40 | Finalizar PDV distintos (40 productos) | 40 | 0 | 0 | 0.1958 | 0.0470 | 121 |
| 10 | Finalizar misma clave (40 productos) | 1 | 9 | 0 | 0.4656 | 0.4370 | 13 |
| 20 | Finalizar misma clave (40 productos) | 1 | 19 | 0 | 0.4768 | 0.4380 | 23 |
| 36 | Finalizar misma clave (40 productos) | 1 | 35 | 0 | 0.4496 | 0.4070 | 39 |
| 40 | Finalizar misma clave (40 productos) | 1 | 39 | 0 | 0.5990 | 0.5470 | 43 |
| 10 | Estados de categorías | 10 | 0 | 0 | 0.0268 | 0.0000 | 4 |
| 20 | Estados de categorías | 20 | 0 | 0 | 0.0291 | 0.0000 | 4 |
| 36 | Estados de categorías | 36 | 0 | 0 | 0.0347 | 0.0000 | 4 |
| 40 | Estados de categorías | 40 | 0 | 0 | 0.0375 | 0.0000 | 4 |
| 10 | Administración / consolidado | 10 | 0 | 0 | 0.0109 | 0.0000 | 1 |
| 20 | Administración / consolidado | 20 | 0 | 0 | 0.0147 | 0.0000 | 1 |
| 36 | Administración / consolidado | 36 | 0 | 0 | 0.0177 | 0.0000 | 1 |
| 40 | Administración / consolidado | 40 | 0 | 0 | 0.0190 | 0.0000 | 1 |
| 10 | Borradores locales | 10 | 0 | 0 | 0.0069 | 0.0000 | 0 |
| 20 | Borradores locales | 20 | 0 | 0 | 0.0116 | 0.0000 | 0 |
| 36 | Borradores locales | 36 | 0 | 0 | 0.0188 | 0.0000 | 0 |
| 40 | Borradores locales | 40 | 0 | 0 | 0.0206 | 0.0000 | 0 |

## Interpretación y límites

Todos los flujos normales terminaron sin fallos. Los duplicados son rechazos
esperados, no fallos de infraestructura. Con 36/40 intentos de la misma clave solo
uno escribe; los restantes consultan el estado fresco y se rechazan.

Estos tiempos no estiman la latencia de Internet ni garantizan cuotas de producción.
OAuth y acceso real de lectura sí se comprobaron: 35 PDV, catálogo BC01 de 566
productos, 6 llamadas. Los XLSX y catálogos reales completos y el comportamiento
de Google bajo carga no se han validado. Nunca se ejecutó carga agresiva contra Google.

## Registro histórico de requisitos

El contenido siguiente corresponde a la preparación anterior a la implementación;
se conserva como historial. El estado actual está documentado arriba.

<details>
<summary>Requisitos de concurrencia registrados inicialmente</summary>

# Concurrencia Google: requisitos y validación pendiente

**Diseño requerido; todavía no implementado ni medido.**

Inventario Uno a Uno e Inventario Mensual utilizan la misma cuenta Google corporativa,
pero operativamente no se ejecutan al mismo tiempo. Las pruebas de carga se realizarán
únicamente sobre Inventario Mensual con 10, 20, 36 y hasta 40 usuarios concurrentes.
No se requiere coordinar ambos aplicativos ni simular 72 usuarios.

## Caché requerida

| Recurso | TTL exigido |
|---|---:|
| Lista de PDV | 600 segundos |
| Resolución de archivo por PDV | 21600 segundos |
| Catálogo de productos | 600 segundos |

Las categorías se derivan del catálogo de la hoja `Mensual`. La caché debe vivir
en memoria, ser segura entre hilos y compartir solicitudes simultáneas del mismo
recurso mediante single-flight. No utilizar Redis ni otra persistencia adicional.
La validación de duplicados nunca debe depender de la caché.

## Finalizar y consistencia

La implementación deberá reducir lecturas y escrituras mediante rangos completos,
batchGet/batchUpdate cuando correspondan y reutilización de resultados. No realizar
una solicitud por celda, fila o producto. Registrar el coste real simulado por flujo
y por Finalizar, diferenciando caché fría, caché vigente y creación inicial de hojas.

La comprobación fresca de Fecha + PDV + Categoría y la escritura deben quedar
protegidas frente a finalizaciones simultáneas. Evaluar bloqueo por Spreadsheet/PDV
para permitir trabajo entre PDV distintos sin perder consistencia. Documentar el
alcance efectivo del bloqueo; una prueba entre hilos no demuestra protección entre
procesos o contra escritores externos.

Guardar borrador opera únicamente en localStorage y debe generar cero llamadas a
Google. Finalizar utiliza `Total = Cerrado + Abierto`, sin factor.

## Reintentos requeridos

Para operaciones idempotentes, reintentos limitados con exponential backoff y jitter
ante 429, 500, 502, 503 y 504. No repetir ciegamente escrituras no idempotentes.
Probar recuperación y agotamiento de cuota; conservar el borrador y no informar
éxito sin confirmación de Google.

## Matriz de pruebas pendiente

Para cada carga de 10/20/36/40 usuarios, medir éxitos, fallos, duración, espera máxima,
solicitudes Google simuladas y respuestas 429, separando:

- Lecturas: PDV, categorías, productos y cambios de categoría.
- Borradores locales.
- Finalizaciones distintas.
- Finalizaciones de la misma clave: exactamente una aceptada.
- Administración y consolidado.

Probar 429 → 200, 429 → 429 → 200 y cuatro 429 consecutivos. Todas las pruebas de
carga usarán fakes/mocks. No hay resultados ni cifras de llamadas disponibles aún.

</details>
