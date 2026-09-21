# Funcionamiento técnico — Inventarios Mensuales PDV

## Arquitectura y fuente de verdad

Python/Flask con controladores HTTP, reglas/modelos, servicios y repositorios.
Google Drive y Sheets siguen siendo el almacenamiento del negocio. No se agregó
SQL, Redis, Forms ni una base propia. El estado operativo del generador en
.runtime/generator.json solo registra progreso, referencias a archivos y errores.
Los inventarios, catálogos y categorías no se persisten allí.

## Carpetas y flujo de datos

| Uso | Referencia |
|---|---|
| Archivos mensuales del generador | 1DwPotMtT1Y-V4qIuob3TXmWjfAc2tbWm |
| Formatos y origen de preparación | 1nzHsP8GAnkWDMWpMJpQPI4pLP0k6DUjk |
| Bases utilizadas por la web | Hija Bases Google - Inventarios Mensuales de la carpeta de formatos |

Los valores predeterminados coinciden con el legacy. La lectura ordinaria no crea
carpetas si faltan: informa un error y remite al comando administrativo.

Los PDV se obtienen de los archivos cuyo MIME es
application/vnd.google-apps.spreadsheet. La lista elimina nombres duplicados,
aplica trim y ordenación ICU española. La resolución del archivo usa el nombre
exacto, como getFilesByName del original.

## Generador Inventario Mensual

```text
Archivos terminados en 09.xlsx + formatos
→ Pedido Diario / Bodega
→ productos con nombre completo y presentación copiada
→ categorías por código desde Mensual / Formato de Inventario Mensual
→ <PDV> - BASE INVENTARIO.xlsx
→ INVENTARIOS_PDV_GENERADOS.zip
```

Se conserva el filtro /09\s*\.xlsx$/i, la selección de columnas hasta 60 filas y
40 columnas, y el matching de formatos con umbral 0.45 y tipos HELADERIA, COCINA,
RESTAURANTE. La deduplicación de formatos selecciona el más actualizado por la
misma clave que Apps Script; no elimina físicamente originales.

Las normalizaciones conservan incluso las particularidades del legacy: por
ejemplo normalizarTexto_ elimina puntuación antes de las sustituciones de
extensiones en claveNombre_. No se corrigió silenciosamente esa secuencia.

La presentación se detecta al final del nombre (X 12, X 750 ML, etc.).
El producto de salida conserva el nombre completo del archivo mensual. La columna
unidad de la hoja fuente se detecta pero no reemplaza la presentación extraída:
esa es la implementación suministrada.

La detección de categorías conserva tabla explícita, categoría arrastrada, anclas
combinadas con prioridad 10, títulos no combinados con prioridad 6/4, máximo 150
filas y cinco columnas de distancia. Puntaje = prioridad − filas × 0.08 − columnas
× 1.5. Se conserva el desempate por primera ancla y el respaldo de la misma fila.
Las hojas de categorías se examinan hasta 5000 filas y 40 columnas.

Los XLSX fuente se convierten temporalmente con Drive. Los temporales confirmados
se envían a papelera al salir, incluso si falla la extracción. Los originales se
conservan. Si Google no confirma una creación, se informa error y no se reintenta
ciegamente; un temporal cuya creación no fue confirmada puede requerir revisión.

La salida usa openpyxl en memoria para producir un XLSX real, hoja BASE, columnas
ÍTEM / PRODUCTO / U.D MED / CATEGORÍA, encabezado #6B3F2A blanco negrita, filas
pares #F3E9DC, filtro, fila congelada y códigos de texto. Los anchos equivalen a
110/390/180/190 píxeles mediante conversión a las unidades de Excel.

Carpeta de salida: RESULTADOS INVENTARIO MENSUAL YYYY-MM-DD HH-mm dentro de la
carpeta mensual. El ZIP contiene los XLSX allí generados.

El procesamiento es secuencial, con error por PDV, checkpoint atómico local y
opción --limit. Repetir el comando reanuda. Se comprueba la salida por nombre antes
de repetir conversiones tras una interrupción. El ZIP existente se actualiza por
ID. Colisiones de nombres o varios resultados del mismo nombre requieren revisión.
--reset-state borra solo el checkpoint y no los resultados de Google.

## Preparar bases mensuales

prepare_monthly_bases.py busca XLSX directamente en la carpeta de formatos.
Convierte a Google Sheets en la carpeta hija, sin extensión en el nombre.
Omite Google Sheets existentes del mismo nombre y comprueba la hoja Mensual.
Si falta, envía esa conversión a papelera e informa error.

El límite predeterminado es cinco intentos por ejecución, incluidos los fallidos.
El legacy limita cinco conversiones exitosas; contar intentos limita la carga
también cuando los archivos son inválidos. Es una adaptación técnica explícita
permitida por el requisito de procesamiento controlado.

El generador y la preparación son flujos diferentes. Los BASE INVENTARIO.xlsx
generados contienen BASE; la web y la preparación requieren Mensual. No se
inventó una conversión automática BASE → Mensual ni un vínculo nuevo entre carpetas.

## Catálogo y categorías

Mensual se encuentra por nombre normalizado. Se leen valores visibles para
conservar ceros iniciales y formatos de los códigos. La primera fila contiene
encabezados dinámicos; fallbacks: categoría 0, ítem 1, producto 2, UDM 3.
Se conservan registros con categoría, ítem y producto no vacíos y producto distinto
de no tiene después de normalizar. La UDM puede estar vacía.

Las categorías son los nombres distintos del catálogo, ordenados en español.
obtenerProductos filtra categoría por normalización sin tildes, espacios repetidos
ni diferencia entre mayúsculas/minúsculas.

## Interfaz y borradores

HTML y CSS provienen de Index.html. scripts/sync_frontend.py reproduce su extracción.
Las 48 funciones frontend se conservan. monthlyApi sustituye google.script.run;
events.js conecta los manejadores mediante una lista permitida y atributos data,
sin eval ni JavaScript inline. Se descartan respuestas antiguas de categorías si
el usuario ya cambió PDV o fecha.

Clave localStorage: inventario-mensual-v1-{PDV}-{FECHA}-{CATEGORIA}.
Solo se guardan item, cerrado y abierto. Debounce 500 ms, guardado inmediato al
ocultar/cerrar pestaña y al pulsar Guardar o antes de Finalizar.

Guardar conserva el borrador y vuelve al menú. Finalizar envía al backend y solo
elimina el borrador cuando recibe éxito confirmado. Los estados Pendiente,
En proceso y Completada dependen del borrador; Ya guardada se consulta en Sheets.

## Guardado y dónde se almacena

```text
Drive / Bases Google - Inventarios Mensuales / <PDV>
├── Mensual: catálogo
└── Conteos Mensuales: inventarios finalizados
```

11 columnas exactas:
ID Registro, Fecha y hora, Fecha inventario, Punto de venta, Categoría, Item,
Nombre Producto, Desc. U.M., Cerrado, Abierto, Total.

Un UUID por envío, compartido por todas sus filas. Total = Cerrado + Abierto,
sin factor. Fechas de guardado como valores tipados DATE_TIME en Sheets, cantidades
como números y textos/códigos como stringValue, sin interpretar fórmulas.

Se valida estructura, fecha calendario real, PDV, categoría, catálogo, multiplicidad
de productos, cantidades presentes, finitas y no negativas. La integridad usa la
misma clave normalizada Item + Producto + UDM del original, con separador U+001F.
Los nulos, vacíos, booleanos y no finitos se rechazan.

## Duplicados, atomicidad y cuotas

Bloqueo por ID de Spreadsheet compartido entre Finalizar y limpieza. FileLock
coordina hilos y procesos del mismo host que utilicen el mismo directorio .runtime.
Dentro del bloqueo se lee el libro fresco: catálogo y Conteos Mensuales en una
solicitud; nunca se decide un duplicado con caché.
Clave: Fecha inventario + PDV + Categoría, normalizada como el legacy.

Un batchUpdate agrega la hoja si hace falta, prepara encabezado/formato solo al
inicializar y escribe todas las filas. Si falta capacidad de grilla la amplía
dentro del mismo batch. Un guardado con ID de archivo resuelto requiere una
lectura y una escritura Google, sin solicitudes por producto.

No se reintenta automáticamente una escritura sin confirmación. El próximo envío
vuelve a leer duplicados. No existe una transacción que incluya lectura y escritura
frente a escritores externos: durante el uso de Python no debe continuar el Apps
Script original escribiendo esos mismos conteos ni otra instancia en otro host
sin el mismo mecanismo de exclusión. No se agregó coordinación distribuida.

## Administración e identidad

IdentityService conserva su proveedor callable. Con AUTH_ENABLED=true se conecta
al email de la sesión validada por el SSO WordPress RS256; el canje crea una cookie
HttpOnly con JWT interno HS256 independiente. No obtiene identidad de parámetros,
Base64, encabezados de usuario ni OAuth Google. Sin sesión se responde 401; una
sesión de usuario normal recibe 403 en operaciones administrativas.
Con autenticación deshabilitada en desarrollo no se asume identidad ni administrador.

Las direcciones administrativas son info.costos@crepesywafflesantioquia.com y,
temporalmente, juan.zapata@crepesywaffles.com, normalizadas con trim y minúsculas.
Se normaliza con strip y minúsculas. Los casos de autorización, suplantación,
ausencia de identidad y error del frontend están probados. Contrato completo y
responsabilidad del SSO en [AUTENTICACION_ADMIN.md](AUTENTICACION_ADMIN.md).
Se reutilizó el patrón de sesión de Uno a Uno, sin modificar ese repositorio.
SESSION_IDLE_TIMEOUT_SECONDS=1200 conserva su política exacta: actividad real,
heartbeat limitado a 45 segundos, comprobación cada 5 segundos, expiración
deslizante y coordinación entre pestañas. Lecturas y status no renuevan.
La autenticación no llama a Google ni altera caché, batching, locks o conteos.
Dominio, claves y publicación del snippet siguen a cargo del operador; no hay despliegue.

## Consolidado, CSV y Siesa

El consolidado filtra Fecha + PDV y agrupa por Item Siesa + producto normalizado
+ UDM normalizada. Acumula Cerrado, Abierto y Total, une categorías sin repetición,
redondea a seis decimales y ordena ítems con comparación numérica española.

CSV: filas originales guardadas, no el agregado de pantalla. Filtro por fecha y
PDV, o todos los PDV si el administrador invoca la API sin PDV; el frontend exige
seleccionar uno. Separador ;, campos entre comillas con comillas escapadas, CRLF
y UTF-8 BOM. Ítems numéricos se completan a ocho dígitos.
Nombre Conteos_Mensuales_<fecha>_<PDV seguro>.csv.

Siesa también exporta las filas guardadas sin consolidar. Bodega: cuatro caracteres
A-Z/0-9; consecutivo: 1–8 dígitos completados a ocho; ítem: hasta 11 dígitos completados
a once. Se reproduce Number.toFixed(15) usando el valor binario64 exacto.
Header 000000100000001009, cuerpo de 333 caracteres, cierre numerado + 99990001009,
separación CRLF. Nombre <PDV>-Mensual-<consecutivo>-PlanosPDV.txt.
Ambos archivos se generan en memoria y descargan al navegador; no se crean en Drive.

## Limpieza

Retención de cinco períodos de 24 horas a partir de Fecha y hora. Solo se eliminan
fechas tipadas válidas estrictamente anteriores al límite; el instante exacto del
límite se conserva, igual que fechas inválidas o texto no verificable.
Una actualización en bloque reescribe las filas vigentes y limpia el resto de A:K.
No cambia Mensual ni elimina archivos, carpetas, categorías o productos.

cleanup_monthly_counts.py es dry-run por defecto; --execute --confirm autoriza
la modificación real de esa invocación. Para programación posterior, el operador
puede crear una tarea diaria alrededor de las 02:00 America/Bogota que invoque el
intérprete del entorno con ese comando y el directorio de trabajo del proyecto.
No se configuró ni instaló esa tarea.

## Inicio local exclusivamente manual

Solo el usuario inicia la aplicación con `.\.venv\Scripts\python.exe run.py`.
El archivo protege su entrada con `if __name__ == "__main__"` y desactiva depurador
y recargador. Crear la aplicación para pruebas no sirve HTTP ni abre sockets.
Las pruebas Chromium interceptan las solicitudes hacia Flask test client.
No hay autoarranque, tareas programadas, servicios Windows ni inicio desde VS Code.
Durante el cierre se detuvo el servidor que ya estaba activo en el puerto 5000;
el asistente no ejecutó run.py ni inició otro servidor.

## Operaciones de lectura y escritura

| Operación | Google | Persistencia local |
|---|---|---|
| Pantallas, PDV, categorías, productos, estado | Lectura | Caché RAM |
| Guardar borrador | Ninguna | localStorage |
| Finalizar | Lectura + escritura | Archivos de bloqueo operativos |
| Administración, CSV, plano | Lectura | Descarga del usuario |
| verify_google_access.py | Solo lectura | Token OAuth propio al autorizar/renovar |
| Generador autorizado | Conversión, creación de carpeta/XLSX/ZIP, papelera de temporales | Checkpoint operativo |
| Preparación autorizada | Conversión, carpeta hija si falta, papelera de conversiones inválidas | Invalida caché |
| Limpieza dry-run | Solo lectura | Bloqueo operativo |
| Limpieza --execute --confirm | Lectura + escritura | Bloqueo operativo |

## APIs, seguridad y observabilidad

Google Drive API v3: files.list/get/get_media/create/update.
Google Sheets API v4: spreadsheets.get con grid data y spreadsheets.batchUpdate.
Se elige get con datos visibles y tipados en una sola respuesta para conservar la
semántica de getDisplayValues/getValues del original; batchGet por sí solo requeriría
consultas separadas para ambas vistas y metadatos.

Transportes httplib2 independientes por operación; carga/renovación OAuth protegida
entre hilos. Reintentos de lectura: cuatro intentos para 429/500/502/503/504 con
esperas 1/2/4 segundos más jitter [0,1). No se muestran secretos ni tracebacks en HTTP.
CSP restringe scripts al propio origen; estilos inline se conservan para mantener
el original. POST JSON exige encabezado no simple y origen propio, sin habilitar CORS.

Referencias oficiales consultadas:

- [BatchUpdate y atomicidad de solicitudes](https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets/batchUpdate).
- [Carga y conversión de archivos Drive](https://developers.google.com/workspace/drive/api/guides/manage-uploads).
- [Seguridad entre hilos del cliente Python](https://googleapis.github.io/google-api-python-client/docs/thread_safety.html).

Resultados y límites de carga: CONCURRENCIA_GOOGLE.md. Evidencia y pendientes:
VALIDATION.md y MIGRATION_PARITY.md en la raíz.
