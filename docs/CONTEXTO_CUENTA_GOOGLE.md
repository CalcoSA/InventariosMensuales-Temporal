# CONTEXTO REAL DE USO DE LA CUENTA GOOGLE

Este proyecto de Inventarios Mensuales utilizará la misma cuenta Google corporativa y podrá reutilizar el mismo OAuth Client utilizado por `Inventario Uno a Uno`.

Sin embargo, existe una condición operativa importante:

```text
Inventario Uno a Uno
y
Inventario Mensual

NO se utilizarán al mismo tiempo.

Son procesos de inventario que se realizan en momentos diferentes.

Por lo tanto, NO es necesario diseñar ni probar escenarios como:

36 usuarios de Inventario Uno a Uno
+
36 usuarios de Inventario Mensual
=
72 usuarios simultáneos consumiendo Google

Ese escenario no corresponde al uso real esperado.

Aun así, este proyecto debe quedar optimizado desde el inicio porque el Inventario Mensual por sí mismo puede tener aproximadamente:

36 usuarios concurrentes

y debe probarse hasta:

40 usuarios concurrentes

como margen de seguridad.

EXPERIENCIA DEL PROYECTO INVENTARIO UNO A UNO

Aunque ambos aplicativos no se utilizarán simultáneamente, debemos aprovechar lo aprendido en Inventario Uno a Uno.

En ese proyecto se presentó en producción:

HTTP 429 - Too Many Requests

cuando varios usuarios utilizaban el sistema al mismo tiempo.

Las causas principales fueron:

consultas repetidas hacia Google;
múltiples usuarios solicitando exactamente la misma información;
demasiadas llamadas Google por cada guardado;
lecturas y escrituras que podían agruparse;
un bloqueo global que mantenía esperando otros guardados.

Inicialmente cada guardado podía realizar aproximadamente:

35 llamadas Google

Después de optimizar:

cache
single-flight
batchGet
batchUpdate
reutilización de lecturas
backoff + jitter
optimización del locking

se redujo aproximadamente a:

10 llamadas Google por guardado

y las pruebas simuladas con 36 y 40 usuarios mejoraron considerablemente.

NO quiero que Inventario Mensual tenga que ser corregido posteriormente por el mismo problema.

La optimización de cuotas y concurrencia debe formar parte de la arquitectura inicial.

OBJETIVO DE CONCURRENCIA PARA INVENTARIO MENSUAL

Diseñar y probar este aplicativo para:

uso normal esperado:
hasta aproximadamente 36 usuarios concurrentes

prueba de margen:
40 usuarios concurrentes

Todos corresponden exclusivamente a:

Inventario Mensual

No sumar usuarios del proyecto Uno a Uno.

Probar independientemente:

1. carga de PDV;
2. carga de categorías;
3. carga de productos;
4. cambios de categoría;
5. guardados de borrador;
6. Finalizar inventarios;
7. administración;
8. consolidado.

El objetivo es que Inventario Mensual sea eficiente por sí mismo.

GOOGLE SHEETS Y DRIVE SIGUEN TENIENDO CUOTAS

Aunque los dos aplicativos no se utilicen simultáneamente, Google Sheets API y Google Drive API continúan teniendo cuotas y límites.

Por eso mantener obligatoriamente:

cache TTL
single-flight
batchGet
batchUpdate
rangos completos
reutilización de lecturas
retries limitados
exponential backoff
jitter
locking seguro

cuando correspondan.

NO realizar consultas innecesarias simplemente porque el otro aplicativo estará inactivo.

La ausencia de concurrencia entre aplicaciones reduce el riesgo, pero no elimina el riesgo de HTTP 429 dentro del propio Inventario Mensual.

CACHE Y SINGLE-FLIGHT

Diseñar desde el inicio para que:

40 usuarios solicitan el mismo PDV/categoría

NO signifique:

40 llamadas idénticas a Google

sino idealmente:

1 carga Google
→ cache
→ respuesta compartida

cuando sea funcionalmente seguro.

Aplicar principalmente a:

lista PDV
ID del Spreadsheet por PDV
catálogo de productos
categorías
metadatos relativamente estáticos

Nunca utilizar cache para decidir duplicados de inventarios.

GUARDADO / FINALIZAR

Especial atención al botón:

Finalizar

porque este es el que realmente escribe en Google.

Diseñar desde el inicio para reducir al mínimo razonable:

lecturas
validaciones contra Google
escrituras
formato
aperturas de Spreadsheet

por cada inventario.

NO realizar una llamada por:

producto
fila
celda

si se puede trabajar con rangos completos o batches.

Medir y documentar:

¿Cuántas llamadas Google realiza un Finalizar?

No aceptar simplemente que funciona con un solo usuario.

PRUEBAS DE CONCURRENCIA OBLIGATORIAS

Simular con mocks/fakes:

10 usuarios
20 usuarios
36 usuarios
40 usuarios

para:

Lecturas
PDV
categorías
productos
Guardados
Finalizar categorías distintas
Duplicados
varios usuarios intentando finalizar:
mismo PDV
+
misma fecha
+
misma categoría

Debe aceptarse únicamente uno.

Medir:

Usuarios	Éxitos	Fallos	Tiempo	Máx. espera	Llamadas Google simuladas
PRUEBAS HTTP 429

Simular también:

429 → 200
429 → 429 → 200

y verificar recuperación mediante reintentos.

También simular cuota persistentemente agotada:

429 → 429 → 429 → 429

y comprobar:

error controlado;
mensaje entendible;
ningún duplicado;
borrador preservado;
no informar éxito cuando Google no confirmó el guardado.
NO SOBRE-DISEÑAR POR LA OTRA APLICACIÓN

IMPORTANTE:

No agregar infraestructura innecesaria para coordinar:

Inventario Uno a Uno
con
Inventario Mensual

porque operativamente no se usarán al mismo tiempo.

NO agregar por esta razón:

Redis
RabbitMQ
Pub/Sub
base de datos compartida
servicio de cuotas común
coordinación distribuida

Mantener la solución simple.

La optimización debe estar centrada exclusivamente en que:

Inventario Mensual

funcione de manera rápida, eficiente y segura con sus propios 36-40 usuarios concurrentes.

DOCUMENTACIÓN

En:

docs/CONCURRENCIA_GOOGLE.md

dejar explícito:

Inventario Uno a Uno e Inventario Mensual utilizan la misma cuenta Google corporativa, pero operativamente no se ejecutan al mismo tiempo.

Por tanto, las pruebas de carga se realizan únicamente sobre:

Inventario Mensual

con hasta:

40 usuarios concurrentes.

También documentar:

qué se cachea;
TTL;
qué NO se cachea;
single-flight;
llamadas Google por flujo;
llamadas Google por Finalizar;
estrategia de retries;
manejo 429;
resultados con 10/20/36/40 usuarios.

Y al principio del prompt, donde describes la prioridad del proyecto, yo agregaría esta frase:

> **Importante: aunque Inventario Uno a Uno e Inventario Mensual usarán la misma cuenta Google, operativamente no se utilizarán simultáneamente. No es necesario diseñar para la suma de usuarios de ambos aplicativos. Sin embargo, Inventario Mensual debe quedar preparado desde el inicio para aproximadamente 36 usuarios concurrentes y probarse hasta 40, aplicando desde el diseño las optimizaciones de caché, single-flight, batching, retries y locking aprendidas del incidente HTTP 429 del proyecto Uno a Uno.**

Así Codex entiende exactamente el escenario: **no hay que prepararse para 72 usuarios entre dos sistemas**, pe