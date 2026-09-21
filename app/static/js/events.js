/* Explicit allow-list for the original HTML event handlers. No eval or inline script. */
"use strict";
const monthlyActions = {
  abrirAdministracion, cargarCategoriasPDV, comenzarInventario,
  programarMostrarProductos, completarVaciosConCero, guardarProceso,
  finalizarInventario, volverMenuCategorias, nuevoInventario,
  abrirConteoConsolidado, descargarPlanoSiesaMensual, cerrarAdministracion,
  filtrarConteoConsolidado, descargarConteosMensuales, volverAdministracion
};
for (const eventName of ["click", "change", "input"]) {
  document.addEventListener(eventName, event => {
    const element = event.target.closest("[data-on" + eventName + "]");
    if (!element || element.disabled) return;
    const action = element.getAttribute("data-on" + eventName);
    const simple = action.match(/^\s*([A-Za-z]+)\(\)\s*$/);
    if (simple && Object.hasOwn(monthlyActions, simple[1])) {
      monthlyActions[simple[1]]();
      return;
    }
    const quantity = action.match(/^\s*registrarCantidad\(\s*(\d+),\s*'(cerrado|abierto)',\s*this\.value\s*\)\s*$/);
    if (quantity) registrarCantidad(Number(quantity[1]), quantity[2], element.value);
  });
}
