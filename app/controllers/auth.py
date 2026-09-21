"""WordPress SSO entry and the Uno a Uno activity-driven session contract."""
import math
from urllib.parse import urlsplit

import jwt
from flask import Blueprint, current_app, g, jsonify, make_response, redirect, render_template, request
from app.services.session_auth_service import SessionAuthService, validate_auth_config

auth = Blueprint("auth", __name__, url_prefix="/auth")
EXPIRED = "Sesión expirada. Ingrese nuevamente desde la intranet."


def service():
    return current_app.extensions["session_auth"]


def access_response(expired=False):
    return make_response(render_template("access.html", expired=expired), 401)


def unauthorized():
    if request.path.startswith(("/api/", "/auth/activity", "/auth/status", "/auth/logout")):
        return jsonify(error=EXPIRED), 401
    return access_response()


def register_auth(app):
    public_key = validate_auth_config(app.config)
    enabled = app.config["AUTH_ENABLED"]
    app.extensions["session_auth"] = SessionAuthService(app.config, public_key) if enabled else None
    if enabled:
        # Keep the existing admin abstraction, but only feed it a verified session.
        app.extensions["monthly"].identity.provider = lambda: getattr(g, "auth_session", {}).get("sub")
    app.register_blueprint(auth)

    @app.get("/healthz")
    def healthz():
        return jsonify(status="ok")

    @app.before_request
    def protect():
        if not enabled or request.endpoint in {"auth.sso", "auth.expired", "healthz"}:
            return None
        try:
            g.auth_session = service().read_session(request.cookies.get(app.config["SESSION_JWT_COOKIE_NAME"]))
        except jwt.InvalidTokenError:
            return unauthorized()
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            origin = request.headers.get("Origin")
            expected = urlsplit(request.host_url)
            actual = urlsplit(origin) if origin else None
            if (request.headers.get("X-Monthly-Request") != "1"
                    or (actual and (actual.scheme, actual.netloc) != (expected.scheme, expected.netloc))
                    or request.headers.get("Sec-Fetch-Site") == "cross-site"):
                return jsonify(error="Origen de solicitud no permitido."), 403
        return None

    @app.after_request
    def session_headers(response):
        if enabled or request.path.startswith("/auth/"):
            response.headers["Cache-Control"] = "no-store"
            response.headers["Referrer-Policy"] = "no-referrer"
        claims = getattr(g, "auth_session", None)
        if claims and response.status_code < 400:
            response.headers["X-Session-Expires-At"] = str(claims["exp"])
            response.headers["X-Session-Activity-At"] = str(claims["act"])
            response.headers["X-Server-Time"] = str(service().now())
            response.headers["X-Session-Context"] = service().context(claims)
        return response

    @app.context_processor
    def auth_template():
        claims = getattr(g, "auth_session", None)
        return {
            "auth_session_context": service().context(claims) if claims else "",
            "auth_remaining_seconds": max(0, claims["exp"] - service().now()) if claims else 0,
        }


@auth.post("/sso")
def sso():
    if not current_app.config["AUTH_ENABLED"]:
        return jsonify(error="SSO no está habilitado."), 404
    if request.query_string or request.content_length is None or request.content_length > 16384:
        return access_response()
    tokens = request.form.getlist("token")
    try:
        if len(tokens) != 1:
            raise jwt.InvalidTokenError("token faltante")
        g.auth_session = service().consume_sso(tokens[0])
    except jwt.InvalidTokenError:
        current_app.logger.info("SSO rechazado: token inválido, expirado o replay.")
        return access_response()
    response = redirect("/", code=303)
    service().set_cookie(response, g.auth_session)
    return response


@auth.post("/activity")
def activity():
    if not getattr(g, "auth_session", None):
        return unauthorized()
    data = request.get_json(silent=True)
    if data is None and not request.data:
        data = {}
    idle = data.get("idle_seconds", 0) if isinstance(data, dict) else None
    if (type(idle) not in {int, float} or not math.isfinite(idle)
            or not 0 <= idle < current_app.config["SESSION_IDLE_TIMEOUT_SECONDS"]):
        return jsonify(error="Actividad inválida."), 400
    try:
        g.auth_session = service().renew(g.auth_session, math.ceil(idle))
    except jwt.InvalidTokenError:
        return unauthorized()
    response = make_response("", 204)
    service().set_cookie(response, g.auth_session)
    return response


@auth.route("/status", methods=["GET", "POST"])
def status():
    # POST preserves Uno a Uno's heartbeat contract; GET is the same read-only action.
    if not getattr(g, "auth_session", None):
        return unauthorized()
    return "", 204


@auth.post("/logout")
def logout():
    if not getattr(g, "auth_session", None):
        return unauthorized()
    response = make_response("", 204)
    service().delete_cookie(response)
    return response


@auth.get("/expired")
def expired():
    return access_response(expired=True)
