# Manual de usuario — Inventarios Mensuales

## Ingresar

Inicie sesión en la intranet y abra **Inventarios Mensuales**. La sesión vence después de **20 minutos sin actividad**. Para continuar, vuelva a ingresar desde la intranet; el borrador guardado en ese navegador se conserva.

## Registrar un inventario

1. Seleccione el **Punto de Venta** correcto.
2. Revise la **fecha** del inventario: inicialmente aparece la fecha de hoy.
3. Consulte el estado de las categorías.
4. Seleccione una categoría disponible y pulse **Comenzar inventario**.
5. Ingrese **Cerrado** para cada producto.
6. Ingrese **Abierto** para cada producto. Se permiten ceros y decimales; no cantidades negativas. La unidad o presentación aparece junto al producto.
7. Pulse **Guardar** si necesita hacer una pausa. Conserva el avance en este navegador, vuelve al menú y deja la categoría **En proceso**, aunque todos los campos estén completos.
8. Para continuar, seleccione el mismo PDV, fecha y categoría: se recuperarán sus cantidades.
9. Cuando termine, revise los valores, pulse **Finalizar** y confirme. Espere el mensaje de éxito: registra definitivamente la categoría y elimina su borrador local.

Puede buscar por código, producto o unidad. El indicador de progreso cuenta los productos con ambos campos diligenciados. **Completar vacíos con 0** llena únicamente campos vacíos, previa confirmación: revise que esos ceros correspondan al conteo real.

## Entender los estados

| Estado mostrado | Significado |
|---|---|
| **Pendiente** | No hay cantidades en un borrador local ni registro definitivo para ese PDV, fecha y categoría. |
| **En proceso** | Hay cantidades guardadas en este navegador. Falta finalizar, incluso si el progreso es 100 %. |
| **Ya guardada** | Inventario completado y registrado definitivamente. La categoría queda deshabilitada para evitar duplicados. |

**Guardar** conserva un borrador local; **Finalizar** registra el inventario compartido. Guardar no envía cantidades a Google. Al finalizar, los registros quedan en **Conteos Mensuales** de la base del PDV. El total normal continúa siendo **Cerrado + Abierto**.

## Retomar después

El sistema conserva automáticamente el avance mientras digita; antes de salir, use **Guardar** y compruebe el mensaje de confirmación. Puede recargar, cerrar el navegador o volver después de una sesión vencida y recuperar el borrador usando el mismo navegador, perfil, equipo y dirección del aplicativo.

Cada borrador corresponde a un PDV, fecha y categoría. Cambiar de selección no lo elimina. Los borradores no se trasladan a otro equipo: borrar los datos del navegador o cerrar una sesión de navegación privada puede eliminarlos. Los inventarios finalizados permanecen en la base compartida, sujetos a la limpieza que realice soporte.

## Administración

Solo los usuarios autorizados ven **Administración**. Seleccione la fecha y el PDV que desea consultar.

- **Ver conteo:** muestra el consolidado por producto, con Cerrado, Abierto y Total. El buscador filtra la tabla; los totales del resumen corresponden al conteo completo.
- **Descargar CSV:** descarga los registros guardados de la selección. Puede incluir varias filas del mismo producto cuando corresponden a categorías diferentes.
- **Descargar plano Siesa:** ingrese una bodega de cuatro letras o números y un consecutivo de uno a ocho dígitos. Descarga el archivo para importarlo posteriormente en Siesa.

El plano aplica exclusivamente esta conversión:

**Cantidad Siesa = (Cerrado × Factor de Base general) + Abierto**

Ejemplo: Cerrado **2**, Factor **24**, Abierto **5** → cantidad Siesa **53**.

**Base general** es la fuente oficial del factor. Esta conversión solo afecta la cantidad del plano Siesa: no modifica los totales del inventario normal, el CSV, el consolidado ni los históricos. Descargar el archivo no lo importa automáticamente en Siesa.

La **generación y preparación de bases** y la **limpieza de conteos** son tareas de soporte, sin botones en esta pantalla. La limpieza puede retirar registros de más de cinco días; coordine con soporte la conservación de la información necesaria.

## Resolver problemas

- **No cargan los PDV o las categorías:** revise su conexión y vuelva a intentar. Si continúa, informe a soporte el PDV, la fecha y el mensaje mostrado.
- **La categoría no cambia a En proceso:** confirme que ingresó al menos una cantidad y que Guardar mostró éxito. Revise que seleccionó el mismo PDV, fecha y categoría. Si aparece un error de almacenamiento, conserve la pantalla y contacte a soporte antes de cerrar o borrar datos del navegador.
- **La sesión expiró:** vuelva a ingresar desde la intranet y seleccione el mismo PDV, fecha y categoría para retomar.
- **Finalizar indica campos pendientes:** diligencie Cerrado y Abierto de todos los productos. Use cero cuando corresponda.
- **Finalizar no confirma el guardado:** conserve el borrador y revise el estado antes de reenviar. Si aparece Ya guardada, el registro ya existe. Si cambió el catálogo o persiste el error, contacte a soporte.
- **Siesa informa un factor faltante, inválido o contradictorio:** entregue a soporte la lista de ítems del mensaje para corregir Base general y vuelva a intentar. El sistema bloquea el plano; no reemplaza factores faltantes por 1.
