# MISIÓN: MIGRAR 1:1 INVENTARIOS MENSUALES PDV DE APPS SCRIPT A PYTHON MVC

Trabaja sobre ESTE repositorio nuevo y vacío.

Necesito migrar DOS proyectos Apps Script existentes a una aplicación Python mantenible, siguiendo el mismo enfoque utilizado anteriormente para “Inventario Uno a Uno”.

La migración debe ser FUNCIONALMENTE 1:1.

NO quiero rediseñar el negocio.

NO quiero cambiar dónde se almacena la información.

NO quiero introducir una base de datos propia.

NO quiero inventar identificadores nuevos.

NO quiero cambiar nombres de Google Sheets, carpetas, hojas, columnas, categorías, reglas ni archivos generados.

Google Drive y Google Sheets existentes continúan siendo la FUENTE DE VERDAD.

---

# 1. OBJETIVO GENERAL

Construir una aplicación MVC en Python que reemplace funcionalmente:

## Proyecto Apps Script A

`Generador Inventario Mensual`

Actualmente contiene:

```text
Código.gs
```

Su responsabilidad es preparar/generar las bases mensuales para los PDV.

## Proyecto Apps Script B

`Inventarios Mensuales PDV`

Actualmente contiene:

```text
Código.gs
Index.html
```

Su responsabilidad es:

- mostrar la aplicación a los PDV;
- seleccionar PDV;
- seleccionar fecha;
- seleccionar categoría;
- realizar el inventario mensual;
- guardar borradores;
- finalizar categorías;
- almacenar conteos;
- visualizar estado de categorías;
- administración;
- consolidado;
- CSV;
- plano Siesa;
- limpieza de conteos antiguos.

La nueva aplicación debe reproducir ambos comportamientos.

---

# 2. FUENTES ORIGINALES

Antes de programar:

Lee TODO el material suministrado del Apps Script original.

No programes desde memoria ni desde supuestos.

Debes crear dentro del repositorio:

```text
legacy/
```

y conservar COPIAS exactas del código original suministrado, sin modificarlo:

```text
legacy/
├── generador_inventario_mensual.gs
├── inventarios_mensuales_pdv.gs
└── index_original.html
```

Estos archivos serán referencia de paridad y pruebas.

NO modificar funcionalmente el legacy.

---

# 3. TECNOLOGÍA

Utilizar una arquitectura similar a la migración de Inventario Uno a Uno:

```text
Python
Flask
HTML
CSS
JavaScript
Google APIs oficiales
```

No necesito React.

Prefiero mantener el frontend simple porque la interfaz original ya está completamente definida.

Arquitectura:

```text
Browser
   ↓
HTML / CSS / JavaScript
   ↓
Flask Controllers
   ↓
Services
   ↓
Repositories
   ↓
Google API
   ↓
Google Drive / Google Sheets
```

Usar MVC/separación equivalente.

Estructura orientativa:

```text
app/
├── controllers/
├── models/
├── repositories/
├── services/
├── static/
│   ├── css/
│   └── js/
├── templates/
├── config.py
├── constants.py
├── container.py
└── __init__.py

scripts/
tests/
legacy/
docs/
credentials/
run.py
requirements.txt
.env.example
.gitignore
README.md
```

Puedes ajustar nombres si existe una razón técnica, pero mantener una arquitectura clara.

---

# 4. NO CREAR BASE DE DATOS

PROHIBIDO agregar:

```text
MySQL
PostgreSQL
SQLite
MongoDB
Redis como persistencia
Firebase
Cloud SQL
```

Google Sheets y Google Drive continúan siendo el almacenamiento real.

No crear tabla de:

```text
PDV
productos
inventarios
categorías
conteos
```

en otra tecnología.

---

# 5. CREDENCIALES GOOGLE

Preparar integración OAuth igual al proyecto anterior.

Rutas locales:

```text
credentials/credentials.json
credentials/token.json
```

Ambos deben estar excluidos de Git.

Crear:

```text
scripts/verify_google_access.py
```

La aplicación debe soportar utilizar el MISMO OAuth client `credentials.json` utilizado por Inventario Uno a Uno.

Este proyecto tendrá su propio:

```text
credentials/token.json
```

aunque use el mismo OAuth client y la misma cuenta Google.

Scopes mínimos esperados:

```text
Google Sheets
Google Drive
```

No pedir Google Forms si no es necesario.

No utilizar Service Account.

No insertar secrets en código.

---

# 6. CARPETAS GOOGLE EXISTENTES

Conservar exactamente estas referencias del legacy.

## Generador

```text
CARPETA_MENSUAL_ID =
1DwPotMtT1Y-V4qIuob3TXmWjfAc2tbWm
```

```text
CARPETA_FORMATOS_ID =
1nzHsP8GAnkWDMWpMJpQPI4pLP0k6DUjk
```

## Aplicación mensual

La carpeta origen es:

```text
1nzHsP8GAnkWDMWpMJpQPI4pLP0k6DUjk
```

Dentro de ella existe/se utiliza:

```text
Bases Google - Inventarios Mensuales
```

No modificar IDs ni nombres.

Si los IDs se parametrizan en configuración, sus valores por defecto deben corresponder exactamente al legacy.

---

# 7. MIGRAR EL GENERADOR INVENTARIO MENSUAL

Replicar completamente `iniciarGeneracion()` y funciones relacionadas.

El flujo original es:

```text
CARPETA_MENSUAL_ID
        ↓
buscar archivos terminados en 09.xlsx
        ↓
CARPETA_FORMATOS_ID
        ↓
buscar formatos
        ↓
eliminar formatos duplicados
        ↓
buscar mejor formato para cada mensual
        ↓
abrir/convertir temporalmente XLSX
        ↓
leer Pedido Diario + Bodega
        ↓
extraer productos actualizados
        ↓
leer Mensual / Formato de Inventario Mensual
        ↓
asignar categoría por código
        ↓
generar BASE INVENTARIO.xlsx por PDV
        ↓
carpeta RESULTADOS INVENTARIO MENSUAL <fecha>
        ↓
generar INVENTARIOS_PDV_GENERADOS.zip
```

---

# 8. FILTRO DE ARCHIVOS MENSUALES

El original procesa únicamente archivos cuyo nombre termine aproximadamente:

```text
09.xlsx
```

Conservar exactamente la expresión/regla del legacy.

Si no encuentra archivos debe devolver:

```text
No se encontraron archivos .xlsx terminados en 09.
```

No ampliar el criterio.

---

# 9. FUENTES DE PRODUCTOS

Conservar:

```text
Pedido Diario
Bodega
```

como hojas fuente.

Detectar columnas usando exactamente las reglas del Apps Script.

Encabezados para código:

```text
CODIGO
COD
ITEM
CODIGO ITEM
REFERENCIA
CODIGO DEL PRODUCTO
```

Encabezados para producto:

```text
PRODUCTO
DESCRIPCION
NOMBRE PRODUCTO
NOMBRE DEL PRODUCTO
DESCRIPCION PRODUCTO
DESCRIPCION DEL PRODUCTO
DESCRIPCION ITEM
ARTICULO
```

Encabezados de unidad:

```text
UNIDAD
UM
U M
DESC UM
UNIDAD DE MEDIDA
UNIDAD DE EMPAQUE
PRESENTACION
DESC U M
```

Conservar normalizaciones originales.

---

# 10. UNIDAD / PRESENTACIÓN

Replicar exactamente:

```text
separarUnidadEmpaque_
normalizarUnidad_
```

Ejemplos conceptuales:

```text
X 12
X 750 ML
X 2 KG
X 6 UNIDADES
```

El nombre del producto debe conservarse COMPLETO tal como aparece en el archivo 09.

La presentación detectada se copia a:

```text
U.D MED
```

No cambiar esta regla.

---

# 11. DETECCIÓN DE CATEGORÍAS DEL GENERADOR

Buscar categorías en hojas:

```text
Mensual
Formato de Inventario Mensual
```

Replicar EXACTAMENTE:

```text
detectarTablaCategorias_
asignarCategoriasDesdeTabla_
detectarAnclasCategorias_
categoriaParaCelda_
categoriaEnMismaFila_
esCategoriaCandidata_
limpiarCategoria_
```

Incluyendo:

- celdas combinadas;
- títulos de sección;
- categoría más cercana;
- búsqueda en misma fila;
- palabras prohibidas;
- distancias;
- prioridades.

No simplificar este algoritmo sin pruebas que demuestren paridad.

---

# 12. EMPAREJAMIENTO MENSUAL ↔ FORMATO

Replicar exactamente:

```text
buscarMejorFormato_
puntajeCoincidencia_
claveNombre_
tipoPdv_
```

Tipos:

```text
HELADERIA
COCINA
RESTAURANTE
```

Mantener el umbral:

```text
0.45
```

No sustituirlo por coincidencia exacta simple.

---

# 13. ARCHIVO GENERADO

Por cada PDV se debe crear:

```text
<PDV> - BASE INVENTARIO.xlsx
```

Hoja:

```text
BASE
```

Columnas EXACTAS:

```text
ÍTEM
PRODUCTO
U.D MED
CATEGORÍA
```

Formato:

```text
COLOR_CAFE = #6B3F2A
COLOR_CREMA = #F3E9DC
```

Conservar:

- encabezado café;
- texto blanco;
- bold;
- columnas con anchos equivalentes;
- filtro;
- primera fila congelada;
- filas alternas crema;
- códigos como texto.

El resultado debe ser XLSX real.

---

# 14. CARPETA DE RESULTADOS

Crear dentro de la carpeta mensual:

```text
RESULTADOS INVENTARIO MENSUAL YYYY-MM-DD HH-mm
```

Finalmente generar dentro de ella:

```text
INVENTARIOS_PDV_GENERADOS.zip
```

conteniendo los XLSX.

No cambiar nombres.

---

# 15. PROCESAMIENTO LARGO

Apps Script usa PropertiesService + triggers porque posee límite de ejecución.

Python no necesita copiar artificialmente esa limitación.

Sin embargo debe conservar:

- procesamiento secuencial controlado;
- estado/progreso;
- errores por PDV;
- posibilidad de continuar;
- no duplicar resultados accidentalmente.

Implementar de manera simple para Python.

Crear un comando administrativo equivalente, por ejemplo:

```text
python scripts/generate_monthly_bases.py
```

No ejecutarlo contra Google real sin autorización explícita.

---

# 16. PREPARAR BASES MENSUALES

Replicar:

```text
prepararBasesMensuales()
```

Carpeta origen:

```text
1nzHsP8GAnkWDMWpMJpQPI4pLP0k6DUjk
```

Carpeta hija:

```text
Bases Google - Inventarios Mensuales
```

Flujo:

```text
buscar XLSX
→ comprobar si ya existe Google Sheet con mismo nombre
→ si no existe
→ convertir XLSX a Google Spreadsheet
→ verificar hoja Mensual
→ conservar si es válida
```

El legacy procesa hasta:

```text
5
```

por ejecución.

En Python puede procesarse controladamente, pero conservar una opción equivalente para evitar cargas descontroladas.

Crear comando administrativo:

```text
python scripts/prepare_monthly_bases.py
```

No ejecutarlo contra producción durante desarrollo sin confirmación.

---

# 17. WEB APP — INTERFAZ IDÉNTICA

La nueva interfaz debe verse prácticamente pixel-perfect respecto a `Index.html`.

NO rediseñar.

Mantener exactamente:

```text
CREPES & WAFFLES
Inventarios PDV
Inventario Mensual
```

Colores:

```text
--chocolate: #4A2B14
--cafe: #65401F
--beige: #F1E5D1
--dorado: #D5B88B
--fondo: #FCFAF6
--texto: #4B321F
--rojo: #A53527
--blanco: #FFFFFF
--verde: #477A52
```

Mantener:

- header;
- borde dorado;
- paneles;
- sombras;
- tarjetas;
- grid;
- diseño responsive;
- botones;
- barra de progreso;
- colores alternos;
- administración;
- consolidado.

Copiar el CSS original cuando sea posible.

No reinterpretar diseño.

---

# 18. PANTALLA INICIAL

Mantener:

```text
Punto de venta
Fecha del inventario
Categoría
```

Botón:

```text
Comenzar inventario
```

La fecha debe iniciar con la fecha actual.

PDV se obtienen desde:

```text
Bases Google - Inventarios Mensuales
```

Solo incluir archivos:

```text
application/vnd.google-apps.spreadsheet
```

Eliminar duplicados y ordenar alfabéticamente en español.

---

# 19. CACHÉ DESDE EL PRIMER DÍA

El legacy ya incluye:

```text
CACHE_PDV_SEGUNDOS = 600
CACHE_ARCHIVO_SEGUNDOS = 21600
CACHE_PRODUCTOS_SEGUNDOS = 600
```

En Python conservar el objetivo funcional, pero implementar una caché:

```text
thread-safe
en memoria
TTL
```

No Redis.

Además implementar single-flight/request coalescing para que solicitudes simultáneas iguales no generen múltiples llamadas Google.

Aprendiendo del proyecto Uno a Uno, preparar desde el principio el sistema para aproximadamente:

```text
36 usuarios concurrentes
```

y probar hasta:

```text
40 usuarios
```

sin cambiar resultados.

---

# 20. CATEGORÍAS

`obtenerCategorias(puntoVenta)` deriva las categorías desde los productos de:

```text
Mensual
```

Eliminar duplicados y ordenar en español.

Mantener EXACTAMENTE esta regla.

---

# 21. PRODUCTOS

La hoja es:

```text
Mensual
```

Buscar dinámicamente:

Categoría:

```text
categoria
```

Item:

```text
item
codigo
cod
id producto
```

Producto:

```text
nombre producto
producto
descripcion
desc item
```

UDM:

```text
desc u m
desc um
descripcion unidad de medida
udm
unidad de medida
unidad
um empaque
```

Fallbacks exactos:

```text
Categoría → columna 0
Item → columna 1
Producto → columna 2
UDM → columna 3
```

Filtrar registros que tengan:

```text
categoria != vacío
item != vacío
producto != vacío
producto != "no tiene"
```

Conservar exactamente.

---

# 22. ESTADO DE LAS CATEGORÍAS

Mantener los cuatro estados:

```text
Pendiente
En proceso
Completada
Ya guardada
```

Reglas:

## Pendiente

No existe borrador con cantidades.

## En proceso

Existe borrador parcial.

## Completada

El borrador local tiene todos los productos con Cerrado y Abierto completos.

## Ya guardada

Existe en Google Sheets un registro para:

```text
Fecha
+
Punto de venta
+
Categoría
```

dentro de:

```text
Conteos Mensuales
```

Las categorías ya guardadas deben aparecer deshabilitadas.

---

# 23. BORRADOR LOCAL

Conservar EXACTAMENTE la intención del localStorage.

Clave:

```text
inventario-mensual-v1-{PDV}-{FECHA}-{CATEGORIA}
```

Guardar únicamente:

```json
{
  "item": "...",
  "cerrado": "...",
  "abierto": "..."
}
```

El borrador:

```text
NO se guarda en Google.
```

Guardar con debounce equivalente a:

```text
500 ms
```

También guardar inmediatamente:

- cuando se oculta la pestaña;
- `beforeunload`;
- al pulsar Guardar.

---

# 24. IMPORTANTE: DIFERENCIA ENTRE “GUARDAR” Y “FINALIZAR”

Mantener EXACTAMENTE esta diferencia.

## Botón Guardar

El botón:

```text
Guardar
```

NO guarda en Google.

Solo:

```text
guarda borrador en localStorage
→ sale de la categoría
→ vuelve al menú
→ marca En proceso/Completada
```

Mostrar:

```text
El proceso de la categoría "<categoria>" quedó guardado. Puede continuar después.
```

## Botón Finalizar

Este SÍ realiza el guardado definitivo en Google.

Esta diferencia debe quedar muy clara en código y documentación.

No cambiarla.

---

# 25. COMPLETAR VACÍOS CON CERO

Mantener:

```text
Completar vacíos con 0
```

Debe:

- contar casillas vacías;
- pedir confirmación;
- poner `"0"` en Cerrado/Abierto vacíos;
- guardar borrador;
- actualizar pantalla;
- actualizar progreso.

---

# 26. GUARDADO DEFINITIVO

`Finalizar` debe enviar:

```json
{
  "puntoVenta": "...",
  "fecha": "...",
  "categoria": "...",
  "conteos": [
    {
      "item": "...",
      "producto": "...",
      "udm": "...",
      "cerrado": "...",
      "abierto": "..."
    }
  ]
}
```

Backend debe volver a validar:

- PDV;
- fecha;
- categoría;
- existencia de productos;
- integridad del catálogo;
- cantidades completas;
- números válidos;
- cantidades >= 0.

No confiar solamente en JavaScript.

---

# 27. INTEGRIDAD DEL CATÁLOGO

Replicar:

```text
validarIntegridadConteosMensuales_
```

Antes de guardar:

```text
productos recibidos
```

deben coincidir EXACTAMENTE con los productos esperados para:

```text
PDV + Categoría
```

usando:

```text
Item
Producto
UDM
```

La cantidad también debe coincidir.

No aceptar:

- productos faltantes;
- productos adicionales;
- producto distinto;
- UDM distinta.

---

# 28. CÁLCULO MENSUAL

IMPORTANTE:

Este inventario NO utiliza la fórmula del Uno a Uno.

Aquí la regla original es:

```text
Total = Cerrado + Abierto
```

NO utilizar factor.

NO multiplicar Cerrado.

Ejemplo:

```text
Cerrado = 4
Abierto = 2

Total = 6
```

Preservar números decimales.

---

# 29. DÓNDE SE GUARDA EL INVENTARIO

Para cada PDV:

```text
Bases Google - Inventarios Mensuales
        ↓
Google Spreadsheet del PDV
        ↓
Conteos Mensuales
```

Si no existe:

```text
Conteos Mensuales
```

se crea.

Encabezados EXACTOS:

```text
ID Registro
Fecha y hora
Fecha inventario
Punto de venta
Categoría
Item
Nombre Producto
Desc. U.M.
Cerrado
Abierto
Total
```

Son:

```text
11 columnas
```

---

# 30. ID REGISTRO

Cada Finalizar genera:

```text
UUID
```

Todas las filas correspondientes a ESA categoría guardada en ese envío deben compartir el mismo:

```text
ID Registro
```

Mantener.

---

# 31. DUPLICADOS

Antes de escribir comprobar en `Conteos Mensuales`:

```text
Fecha inventario
+
Punto de venta
+
Categoría
```

Si ya existe:

```text
La categoría "<categoria>" ya fue guardada para <PDV> en esta fecha.
```

No utilizar caché para decidir duplicados.

La comprobación debe utilizar información suficientemente fresca.

---

# 32. CONCURRENCIA DESDE EL INICIO

No repetir el problema que ocurrió con Uno a Uno.

Diseñar el guardado para múltiples usuarios.

Evitar:

- una llamada por celda;
- una llamada por fila;
- lecturas repetidas;
- formatos repetidos;
- loops contra Google.

Utilizar cuando sea apropiado:

```text
batchGet
batchUpdate
rangos completos
```

Mantener locking suficiente para impedir duplicados.

Si varios PDV guardan simultáneamente, analizar lock por Spreadsheet/PDV en vez de un único lock global si puede hacerse de forma segura.

No sacrificar consistencia.

---

# 33. RETRIES GOOGLE

Para operaciones idempotentes/transitorias:

```text
429
500
502
503
504
```

implementar:

```text
retry limitado
exponential backoff
jitter
```

NO reintentar ciegamente operaciones no idempotentes que podrían duplicar datos.

El frontend debe recibir mensajes claros, no traceback.

---

# 34. ADMINISTRACIÓN

Mantener botón:

```text
Administración
```

solo para administrador.

El Apps Script actual define:

```text
info.costos@crepesywafflesantioquia.com
```

como administrador.

NO conceder acceso administrativo a todos.

La migración a Flask debe aislar esta regla detrás de un servicio de identidad/autorización.

Si el repositorio hermano de Inventario Uno a Uno está disponible, puedes tomar como referencia su SSO seguro, PERO NO modificar ese proyecto.

Si no existe aún una identidad autenticada que permita reproducir exactamente el correo de Apps Script:

NO inventes una autenticación insegura.

Implementa la autorización desacoplada y documenta claramente qué debe suministrar producción para identificar al usuario.

No utilizar:

```text
?usuario=base64
```

como autenticación.

---

# 35. PANTALLA DE ADMINISTRACIÓN

Conservar:

```text
Fecha del inventario
Punto de venta
Bodega Siesa
Consecutivo
```

Acciones:

```text
Ver conteo del PDV
Descargar plano Siesa
Volver al inventario
```

Mantener estilos.

---

# 36. CONTEO CONSOLIDADO

Replicar:

```text
obtenerConteoConsolidadoPDV
```

Filtrar:

```text
Fecha + PDV
```

Agrupar por:

```text
Item
Producto
UDM
```

Acumular:

```text
Cerrado
Abierto
Total
```

Combinar categorías sin repetir.

Mostrar tabla con:

```text
Ítem
Producto
Categoría
Desc. U.M.
Cerrado
Abierto
Total
```

Mantener buscador.

Mantener tarjetas:

```text
Productos
Cerrado
Abierto
Total contado
```

---

# 37. DESCARGAR CSV

Replicar:

```text
generarDescargaConteosMensuales
```

Solo administrador.

Filtrar por:

```text
Fecha
PDV
```

Columnas:

```text
Fecha inventario
Punto de venta
Categoría
Item Siesa
Nombre Producto
Desc. U.M.
Cerrado
Abierto
Total
```

Separador:

```text
;
```

Encoding compatible con Excel:

```text
UTF-8 BOM
```

Nombre:

```text
Conteos_Mensuales_<fecha>_<PDV>.csv
```

Mantener formato Siesa del item con 8 dígitos cuando sea numérico.

---

# 38. PLANO SIESA

Replicar EXACTAMENTE:

```text
generarPlanoSiesaMensual
```

No reinterpretar el formato.

Validar:

```text
fecha
PDV
bodega
consecutivo
```

Bodega:

```text
exactamente 4 caracteres A-Z/0-9
```

Consecutivo:

```text
1 a 8 dígitos
```

Completar consecutivo a:

```text
8 posiciones
```

Mantener:

```text
header = 000000100000001009
```

Cada registro debe tener EXACTAMENTE:

```text
333 caracteres
```

Mantener todas las posiciones, ceros, espacios, cantidad e Item exactamente como el Apps Script.

Mantener cierre:

```text
99990001009
```

No simplificar.

Crear pruebas diferenciales contra la implementación JavaScript original.

---

# 39. LIMPIEZA AUTOMÁTICA

El sistema actual conserva los conteos únicamente:

```text
5 días
```

Config:

```text
DIAS_RETENCION_CONTEOS_MENSUALES = 5
HORA_LIMPIEZA_AUTOMATICA = 2
```

Replicar la función:

```text
limpiarConteosMensualesVencidos
```

La limpieza:

- revisa todos los Google Sheets de PDV;
- abre `Conteos Mensuales`;
- utiliza `Fecha y hora`;
- elimina registros con más de 5 días;
- conserva filas cuya fecha no sea válida;
- reescribe en bloque;
- no elimina catálogo, categorías ni bases.

IMPORTANTE:

Implementar la lógica y pruebas.

NO ejecutar la limpieza sobre Google real durante desarrollo.

Crear comando seguro:

```text
python scripts/cleanup_monthly_counts.py
```

con opción de:

```text
--dry-run
```

por defecto.

La ejecución destructiva debe requerir confirmación explícita.

Documentar cómo programarla diariamente alrededor de las 02:00, pero NO hacer despliegue.

---

# 40. PREPARAR BASES Y GENERADOR SON OPERACIONES ADMINISTRATIVAS

La aplicación de usuario cotidiano NO debe:

- generar las bases automáticamente cada vez;
- convertir XLSX cada vez;
- ejecutar el generador cada vez.

Separar:

```text
OPERACIÓN ADMINISTRATIVA
```

de:

```text
USO DEL INVENTARIO
```

Documentarlo claramente.

---

# 41. URL ORIGINAL

La Web App original actualmente está publicada en:

```text
https://script.google.com/a/macros/crepesywafflesantioquia.com/s/AKfycbxFTuitfHABvgRZqBKaC6lkARUrwt0c6zwL0KYQ19StGHKkb8YV6_Qn5aXj0HUXCjXd/exec
```

Puedes utilizarla ÚNICAMENTE para:

- inspección visual;
- comparación de textos;
- comparar flujo;
- comparar responsive;
- comparar colores.

NO:

- finalizar inventarios reales;
- ejecutar administración;
- descargar/generar archivos destructivamente;
- modificar producción.

Si requiere autenticación corporativa y no puedes acceder:

NO intentes saltarla.

Utiliza el código original como fuente de verdad.

---

# 42. PRUEBAS DE PARIDAD

Crear pruebas que comparen funciones Python con funciones originales Apps Script/JavaScript cuando sea viable.

Especialmente:

```text
normalización
detección columnas
separación UDM
normalización códigos
matching de formatos
tipos PDV
nombres salida
fechas
clave producto
duplicados
formato item Siesa
cantidad Siesa
nombre PDV Siesa
plano de 333 caracteres
```

Node puede utilizarse solo para pruebas diferenciales si está disponible.

---

# 43. PRUEBAS FRONTEND

Probar:

- carga PDV;
- cambio PDV;
- fecha;
- categorías;
- estados;
- inicio inventario;
- búsqueda;
- Cerrado;
- Abierto;
- progreso;
- completar vacíos;
- Guardar borrador;
- recuperar borrador;
- Finalizar;
- error incompleto;
- éxito;
- volver categorías;
- cambiar PDV;
- administración;
- consolidado;
- filtros.

No depender de Google real.

---

# 44. PRUEBAS DE CONCURRENCIA

Desde el inicio simular:

```text
10
20
36
40
```

usuarios concurrentes.

Separar pruebas de:

```text
lecturas
guardados distintos
guardados duplicados
```

Medir:

```text
éxitos
fallos
tiempo
llamadas Google simuladas
esperas
429
```

No usar Google real para prueba agresiva.

---

# 45. PRUEBA REAL GOOGLE — SOLO LECTURA

Después de implementar:

usar:

```text
scripts/verify_google_access.py
```

para comprobar de manera REAL pero READ-ONLY:

- autenticación;
- acceso carpeta mensual;
- acceso carpeta formatos;
- existencia `Bases Google - Inventarios Mensuales`;
- lista de PDV;
- apertura de una base;
- hoja `Mensual`;
- categorías;
- productos.

NO escribir.

NO convertir archivos.

NO crear carpetas.

NO ejecutar limpieza.

NO finalizar inventarios.

---

# 46. NO MODIFICAR GOOGLE DURANTE DESARROLLO

PROHIBIDO sin autorización explícita:

```text
generar bases reales
crear carpeta resultados real
crear ZIP real
convertir XLSX real
guardar Conteos Mensuales
limpiar Conteos Mensuales
generar archivos reales en Drive
```

Todo eso debe probarse con mocks/fakes primero.

---

# 47. MANEJO DE GOOGLE API

Crear servicios separados, como mínimo conceptualmente:

```text
GoogleAuthService
GoogleDriveService
GoogleSheetsService
```

Repositories orientados al dominio:

```text
MonthlyBasesRepository
MonthlyInventoryRepository
MonthlyGeneratorRepository
```

Services:

```text
MonthlyInventoryService
MonthlyGeneratorService
MonthlyAdminService
MonthlyCleanupService
```

Ajustar nombres si la arquitectura lo exige.

---

# 48. SEGURIDAD

Backend debe validar todo lo recibido.

Nunca confiar en:

```text
PDV
categoría
productos
UDM
cantidades
```

provenientes directamente del browser.

No exponer:

```text
credentials.json
token.json
stack traces
filesystem paths
```

No incluir secrets en Git.

Agregar:

```text
Content-Security / headers razonables
```

sin modificar visualmente la aplicación.

No implementar una autenticación improvisada.

---

# 49. DESARROLLO LOCAL

Debe poder iniciar con algo simple:

```powershell
.\.venv\Scripts\python.exe run.py
```

o:

```text
python run.py
```

según el entorno.

Debe abrir:

```text
http://127.0.0.1:5000
```

No dejar Flask ejecutándose al terminar tareas.

No hacer deployment.

---

# 50. NO TOCAR DESPLIEGUE

NO configurar:

```text
Apache
Nginx
systemd
Docker deployment
GCP VM
DNS
SSL
GitHub Actions
CI/CD
```

Yo me encargo del despliegue.

Puedes crear Dockerfile únicamente si forma parte del estándar inicial del proyecto y no afecta desarrollo, pero NO desplegar.

Si no es necesario, no lo crees todavía.

---

# 51. DOCUMENTACIÓN TÉCNICA

Crear:

```text
docs/FUNCIONAMIENTO_SISTEMA.md
```

Debe explicar:

1. arquitectura;
2. Google Drive;
3. carpetas;
4. generador;
5. bases mensuales;
6. web app;
7. categorías;
8. productos;
9. borrador;
10. Guardar vs Finalizar;
11. almacenamiento;
12. Conteos Mensuales;
13. duplicados;
14. administración;
15. consolidado;
16. CSV;
17. plano Siesa;
18. limpieza;
19. concurrencia;
20. APIs utilizadas;
21. qué operaciones escriben;
22. qué operaciones son solo lectura.

---

# 52. MANUAL DE USUARIO OBLIGATORIO

Crear:

```text
docs/MANUAL_USUARIO.md
```

Debe estar escrito para una persona NO técnica.

Debe poder leerlo cualquier usuario del PDV y saber usar la aplicación paso a paso.

Incluir:

# Inventarios Mensuales PDV — Manual de Usuario

## 1. Ingresar a la aplicación

Explicar qué verá.

## 2. Seleccionar Punto de Venta

## 3. Seleccionar Fecha

## 4. Ver categorías

Explicar:

```text
Pendiente
En proceso
Completada
Ya guardada
```

## 5. Seleccionar Categoría

## 6. Comenzar inventario

## 7. Buscar producto

## 8. Registrar Cerrado

## 9. Registrar Abierto

## 10. Barra de progreso

## 11. Completar vacíos con 0

## 12. Botón Guardar

MUY IMPORTANTE:

explicar que:

```text
Guardar = guardar temporalmente en ese navegador.
```

NO ha enviado todavía el inventario definitivo a Google.

## 13. Continuar un inventario después

## 14. Botón Finalizar

Explicar:

```text
Finalizar = guardar definitivamente la categoría.
```

## 15. Qué pasa después de finalizar

## 16. Volver al menú de categorías

## 17. Cambiar PDV

## 18. Errores comunes

Por ejemplo:

```text
faltan productos
categoría ya guardada
datos incompletos
problema temporal Google
```

---

# 53. MANUAL DE ADMINISTRACIÓN

Dentro del mismo manual agregar:

```text
Administración
```

Explicar:

- quién puede verla;
- seleccionar fecha;
- PDV;
- Bodega Siesa;
- Consecutivo;
- Ver conteo del PDV;
- buscar producto;
- total de productos;
- Cerrado;
- Abierto;
- Total;
- Descargar CSV;
- Descargar plano Siesa.

Explicar claramente que se debe verificar:

```text
Bodega
Consecutivo
```

antes de generar el plano.

---

# 54. DOCUMENTAR EXACTAMENTE DÓNDE SE GUARDA LA INFORMACIÓN

Crear una sección muy visible:

```text
## ¿Dónde se guarda el inventario?
```

Explicar para usuarios/soporte:

```text
Google Drive
└── carpeta:
    Bases Google - Inventarios Mensuales
        └── <PDV>
            ├── Mensual
            └── Conteos Mensuales
```

Explicar:

`Mensual`:

```text
catálogo utilizado por la aplicación
```

`Conteos Mensuales`:

```text
inventarios finalizados
```

Columnas:

```text
ID Registro
Fecha y hora
Fecha inventario
Punto de venta
Categoría
Item
Nombre Producto
Desc. U.M.
Cerrado
Abierto
Total
```

Explicar:

```text
Guardar
→ localStorage del navegador

Finalizar
→ Google Sheets / Conteos Mensuales
```

Esto debe quedar extremadamente claro.

---

# 55. DOCUMENTAR EL GENERADOR

En el manual técnico incluir:

```text
Generador Inventario Mensual
```

Explicar:

```text
archivos 09.xlsx
+
formatos
↓
cruce productos/categorías
↓
BASE INVENTARIO.xlsx
↓
ZIP
```

Incluir las dos carpetas Google utilizadas y dónde queda la salida.

---

# 56. PARIDAD

Crear:

```text
MIGRATION_PARITY.md
```

Tabla:

| Apps Script | Python | Estado |
|---|---|---|

Mapear función por función.

No declarar paridad si no está comprobada.

---

# 57. VALIDACIÓN

Crear:

```text
VALIDATION.md
```

Registrar:

- pruebas unitarias;
- pruebas diferenciales;
- pruebas frontend;
- pruebas concurrencia;
- Google read-only;
- elementos todavía pendientes.

No declarar que Google real fue validado si solo se probaron mocks.

---

# 58. README

Crear README claro con:

- qué es;
- arquitectura;
- instalación;
- ejecución;
- OAuth;
- credenciales;
- pruebas;
- estructura;
- operaciones administrativas;
- advertencias;
- documentación.

---

# 59. CREDENCIALES / GITIGNORE

`.gitignore` debe excluir como mínimo:

```text
.env
credentials/*.json
token.json
*.pem
*.key
.venv/
__pycache__/
*.pyc
.pytest_cache/
.runtime/
```

Conservar:

```text
credentials/.gitkeep
```

Nunca imprimir secretos.

---

# 60. NO HACER PUSH

NO ejecutar:

```text
git commit
git push
```

Yo me encargo.

Al terminar mostrar:

```text
git status
git diff --stat
```

---

# 61. NO DEJAR BASURA

Antes de terminar:

eliminar:

```text
scripts temporales
logs
caches
debug dumps
archivos de diagnóstico descartables
```

No dejar archivos creados únicamente para una prueba puntual si no sirven al proyecto.

---

# 62. RESPUESTA FINAL

Cuando termines necesito un resumen con:

1. arquitectura creada;
2. cantidad de archivos;
3. funciones migradas del Generador;
4. funciones migradas de la Web App;
5. dónde obtiene los PDV;
6. dónde obtiene categorías;
7. dónde obtiene productos;
8. cómo funciona el borrador;
9. diferencia Guardar/Finalizar;
10. dónde se guardan los inventarios;
11. columnas de `Conteos Mensuales`;
12. cómo evita duplicados;
13. cómo funciona administración;
14. cómo genera CSV;
15. cómo genera plano Siesa;
16. cómo funciona limpieza de 5 días;
17. cómo funciona el generador;
18. qué APIs Google utiliza;
19. resultado de pruebas unitarias;
20. resultado de pruebas diferenciales;
21. resultado de prueba con 36 usuarios;
22. resultado con 40;
23. llamadas Google estimadas;
24. resultado de Google read-only;
25. pendientes;
26. ubicación de `docs/MANUAL_USUARIO.md`;
27. ubicación de `docs/FUNCIONAMIENTO_SISTEMA.md`;
28. ubicación de `MIGRATION_PARITY.md`;
29. ubicación de `VALIDATION.md`;
30. confirmación de NO escritura real en Google;
31. confirmación de NO deployment;
32. confirmación de NO commit;
33. confirmación de NO push;
34. confirmación de que no quedaron servidores ejecutándose.

No agregues funcionalidades nuevas.

La prioridad absoluta es:

```text
PARIDAD FUNCIONAL 1:1
+
MISMA INTERFAZ
+
MISMOS GOOGLE SHEETS/DRIVE
+
MEJOR IMPLEMENTACIÓN TÉCNICA SIN CAMBIAR EL NEGOCIO
```