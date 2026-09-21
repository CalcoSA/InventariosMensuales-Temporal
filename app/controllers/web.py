from urllib.parse import urlsplit
from flask import Blueprint, current_app, jsonify, render_template, request
from app.models.errors import AccessDenied, DomainError

web = Blueprint("web", __name__)


@web.get("/")
def index():
    return render_template("index.html")


@web.post("/api/<method>")
def rpc(method):
    # Same-origin JSON + non-simple header: no cookie-free cross-site form writes.
    if request.headers.get("X-Monthly-Request") != "1" or not request.is_json:
        raise AccessDenied("Solicitud no autorizada.")
    origin = request.headers.get("Origin")
    if origin and urlsplit(origin).netloc != request.host:
        raise AccessDenied("Solicitud no autorizada.")
    if request.headers.get("Sec-Fetch-Site") == "cross-site":
        raise AccessDenied("Solicitud no autorizada.")
    body = request.get_json(silent=True)
    if not isinstance(body, dict) or not isinstance(body.get("args"), list):
        raise DomainError("Los datos recibidos no son válidos.")
    c = current_app.extensions["monthly"]
    methods = {
        "obtenerPuntosVenta": (c.inventory.points, 0, 0),
        "obtenerCategorias": (c.inventory.categories, 1, 1),
        "obtenerProductos": (c.inventory.products, 1, 2),
        "obtenerEstadoCategoriasMensuales": (c.inventory.states, 2, 2),
        "guardarInventario": (c.inventory.finalize, 1, 1),
        "obtenerEstadoAdministrador": (lambda: {"esAdministrador": c.identity.is_admin()}, 0, 0),
        "obtenerConteoConsolidadoPDV": (c.admin.consolidated, 1, 1),
        "generarDescargaConteosMensuales": (c.admin.csv, 1, 1),
        "generarPlanoSiesaMensual": (c.admin.flat, 1, 1),
    }
    if method not in methods:
        return jsonify(error="Operación no disponible."), 404
    action, minimum, maximum = methods[method]
    args = body["args"]
    if not minimum <= len(args) <= maximum:
        raise DomainError("Los datos recibidos no son válidos.")
    if method in {"obtenerCategorias", "obtenerProductos", "obtenerEstadoCategoriasMensuales"} and any(not isinstance(a, str) for a in args):
        raise DomainError("Seleccione datos de inventario válidos.")
    return jsonify(result=action(*args))
