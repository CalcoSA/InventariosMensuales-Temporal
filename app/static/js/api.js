/* Small immutable RPC adapter: original callbacks now call Flask, no Apps Script runtime. */
"use strict";
const monthlyMethods = new Set([
  "obtenerPuntosVenta", "obtenerCategorias", "obtenerProductos",
  "obtenerEstadoCategoriasMensuales", "guardarInventario",
  "obtenerEstadoAdministrador", "obtenerConteoConsolidadoPDV",
  "generarDescargaConteosMensuales", "generarPlanoSiesaMensual"
]);
function monthlyRunner(success, failure) {
  return new Proxy({}, {
    get(_target, name) {
      if (name === "withSuccessHandler") return callback => monthlyRunner(callback, failure);
      if (name === "withFailureHandler") return callback => monthlyRunner(success, callback);
      if (!monthlyMethods.has(name)) return undefined;
      return (...args) => {
        fetch("/api/" + name, {
          method: "POST", credentials: "same-origin",
          headers: {"Content-Type": "application/json", "X-Monthly-Request": "1"},
          body: JSON.stringify({args})
        }).then(async response => {
          let body;
          try { body = await response.json(); }
          catch (_error) { throw new Error("No fue posible comunicarse con el servidor. Su borrador se conserva."); }
          if (!response.ok || body.error) throw new Error(body.error || "No fue posible completar la solicitud.");
          if (success) success(body.result);
        }).catch(error => {
          if (failure) failure(error instanceof TypeError
            ? new Error("No fue posible comunicarse con el servidor. Su borrador se conserva.")
            : error);
        });
      };
    }
  });
}
const monthlyApi = monthlyRunner();
