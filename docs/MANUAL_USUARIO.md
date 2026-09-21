# Inventarios Mensuales PDV — Manual de Usuario

Este manual explica el comportamiento de la aplicación migrada. La conexión Google
de este equipo ya fue verificada en solo lectura. Guardar y recuperar borradores
también fueron validados manualmente. Las escrituras reales siguen deshabilitadas.
La administración requiere que soporte conecte la identificación corporativa.

## 1. Ingresar a la aplicación

Abra la dirección que le entregue soporte. Verá CREPES & WAFFLES, Inventarios PDV,
Inventario Mensual y el panel Datos del inventario.
Espere a que aparezca la lista de puntos de venta.
En este equipo la aplicación no arranca sola: el usuario debe ejecutar manualmente
`.\.venv\Scripts\python.exe run.py` y abrir `http://127.0.0.1:5000`.
Al terminar, Ctrl+C detiene el servidor; cerrar VS Code no sustituye ese paso.

## 2. Seleccionar Punto de Venta

Elija su PDV en Punto de venta. Verifique el nombre antes de empezar.
Si no aparece, comuníquese con soporte: la lista proviene de las bases de Google.

## 3. Seleccionar Fecha

La fecha comienza en el día actual de su equipo. Seleccione la fecha del inventario
que va a realizar. Cambiarla muestra el estado correspondiente a esa fecha.

## 4. Ver categorías

El panel muestra el estado de cada categoría:

| Estado | Significado |
|---|---|
| Pendiente | No hay cantidades guardadas como borrador en este navegador. |
| En proceso | Hay cantidades en el borrador, pero faltan productos por completar. |
| Completada | Todos los productos tienen Cerrado y Abierto en el borrador; falta Finalizar. |
| Ya guardada | La categoría ya fue enviada a Google para ese PDV y esa fecha. No puede seleccionarse otra vez. |

Completada no significa que el inventario ya esté enviado.

## 5. Seleccionar Categoría

Seleccione una categoría disponible. Cada categoría se registra y finaliza por separado.

## 6. Comenzar inventario

Pulse Comenzar inventario. La pantalla muestra el PDV, la fecha, la categoría y los
productos. Cada producto muestra código, nombre y Desc. U.M.

## 7. Buscar producto

Escriba parte del nombre o del código en Buscar producto o código. Puede buscar
sin tildes. Borrar la búsqueda vuelve a mostrar todos los productos.
El buscador solo cambia lo que se ve: no elimina cantidades ni productos.

## 8. Registrar Cerrado

Digite la cantidad cerrada en el campo Cerrado. Se permiten decimales y cero.
No se permiten números negativos.

## 9. Registrar Abierto

Digite la cantidad abierta en Abierto. Si no hay cantidad, ingrese 0.
El total mensual es Cerrado + Abierto. Por ejemplo, 4 cerrado y 2 abierto dan 6.

## 10. Barra de progreso

Un producto cuenta como completo cuando tiene valores en ambos campos.
La barra muestra productos completos, total de productos y porcentaje.
Los valores cero también cuentan como completos.

## 11. Completar vacíos con 0

Pulse Completar vacíos con 0 si los campos restantes realmente corresponden a cero.
La aplicación informa cuántas casillas cambiará y solicita confirmación.
Las cantidades que ya escribió se conservan.

## 12. Botón Guardar

**Guardar = guardar temporalmente en ese navegador.**

Debe haber al menos una cantidad. Pulse Guardar para conservar el avance y volver
al menú de categorías. Verá:

> El proceso de la categoría "<categoría>" quedó guardado. Puede continuar después.

**Esto todavía no envía el inventario definitivo a Google.**
La categoría queda En proceso o Completada.

Mientras escribe, también se guarda automáticamente el borrador después de una
pausa breve. La aplicación intenta guardarlo al ocultar o cerrar la pestaña.

## 13. Continuar un inventario después

Regrese desde el mismo navegador y equipo, en la misma dirección de la aplicación.
Seleccione el mismo PDV, fecha y categoría y pulse Comenzar inventario.
Se recuperarán las cantidades disponibles.

El borrador no se traslada automáticamente a otro navegador o equipo.
No borre los datos del navegador ni dependa de una ventana privada para conservarlo.

## 14. Botón Finalizar

**Finalizar = guardar definitivamente la categoría en Google Sheets.**

Complete Cerrado y Abierto en todos los productos. Pulse Finalizar, revise el PDV
y la categoría de la confirmación y acepte. Espere la respuesta; no cierre la página
mientras envía. El sistema vuelve a comprobar productos, cantidades y duplicados.

## 15. Qué pasa después de finalizar

Si Google confirma el guardado, aparece Inventario finalizado y la cantidad de
productos registrados. Se elimina el borrador de esa categoría y su estado pasa
a Ya guardada. No vuelva a registrar el mismo PDV, fecha y categoría.

Si aparece un error, el borrador se conserva. Si el mensaje dice que Google no
confirmó el guardado, actualice el estado de la categoría antes de intentarlo otra vez.

## 16. Volver al menú de categorías

Después de finalizar, pulse Volver al menú de categorías para continuar con otra
categoría del mismo inventario.

## 17. Cambiar PDV

En la pantalla de inventario finalizado, pulse Cambiar punto de venta.
Verifique otra vez PDV, fecha y categoría antes de comenzar.

## 18. Errores comunes

| Mensaje o situación | Qué hacer |
|---|---|
| Faltan productos por completar | Complete ambos campos o use Completar vacíos con 0 cuando corresponda. |
| Categoría ya guardada | Revise el estado del PDV y fecha. No intente duplicar el envío. |
| Producto faltante, distinto o cantidad de productos diferente | Soporte pudo actualizar el catálogo. Actualice la página y revise los productos antes de reenviar. |
| Cantidad no válida | Revise números negativos, textos y decimales. |
| Google recibe demasiadas solicitudes | Espere un momento y vuelva a intentar. El borrador permanece. |
| Google no confirmó el guardado | Actualice el estado; puede haberse guardado. Si aparece Ya guardada, no reenvíe. |
| Escrituras deshabilitadas o falta autorizar Google | Solicite a soporte habilitar el entorno autorizado. |
| No aparece el PDV o la categoría | Solicite a soporte revisar las bases existentes. |

## ¿Dónde se guarda el inventario?

```text
Google Drive
└── Bases Google - Inventarios Mensuales
    └── <PDV> (archivo Google Sheets)
        ├── Mensual
        └── Conteos Mensuales
```

Mensual es el catálogo utilizado por la aplicación.
Conteos Mensuales contiene los inventarios finalizados, con estas 11 columnas:

1. ID Registro
2. Fecha y hora
3. Fecha inventario
4. Punto de venta
5. Categoría
6. Item
7. Nombre Producto
8. Desc. U.M.
9. Cerrado
10. Abierto
11. Total

**Guardar → borrador local del navegador.**

**Finalizar → Google Sheets / Conteos Mensuales.**

La limpieza administrativa conserva los conteos durante cinco días desde su
Fecha y hora de guardado. Soporte debe programarla; no se instaló automáticamente
durante la migración. El catálogo y las bases no se eliminan.

## Administración

Solo la identidad corporativa autenticada de
info.costos@crepesywafflesantioquia.com tiene autorización administrativa.
Si soporte aún no conectó la identidad, el botón no aparecerá.
Usar la cuenta técnica Google no concede por sí solo esta autorización.

1. Pulse Administración.
2. Seleccione Fecha del inventario y Punto de venta.
3. Para consultar, pulse Ver conteo del PDV.
4. Revise la tabla y las tarjetas Productos, Cerrado, Abierto y Total contado.
5. Use el buscador para filtrar código o nombre. Las tarjetas resumen todo el PDV,
   aunque la búsqueda muestre solo algunos productos.
6. Pulse Descargar CSV para obtener el archivo del PDV y fecha. El CSV contiene
   las filas guardadas; el consolidado en pantalla agrupa productos equivalentes.
7. Pulse Volver para regresar a Administración.
8. Para el plano, escriba Bodega Siesa y Consecutivo.
9. **Verifique Bodega y Consecutivo antes de pulsar Descargar plano Siesa.**

Bodega requiere cuatro letras o números, por ejemplo BR03. Consecutivo permite
de uno a ocho dígitos y se completa con ceros a la izquierda.
El plano incluye los conteos del PDV y fecha seleccionados. Descargarlo no lo
importa en Siesa ni modifica Google Drive.

Volver al inventario regresa al menú. Las operaciones de generar o convertir bases
y limpiar conteos son tareas de soporte; no se ejecutan al ingresar al inventario.
