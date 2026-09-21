from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix
from .config import settings
from .container import Container
from .controllers.web import web
from .controllers.auth import register_auth
from .models.errors import DomainError


def create_app(config=None, *, container=None, identity_provider=None):
    app = Flask(__name__)
    # One Apache proxy sets proto/port; ProxyPreserveHost supplies the real Host.
    # The backend must remain reachable only through that trusted proxy.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=0, x_proto=1, x_host=0, x_port=1, x_prefix=0)
    app.config.update(settings())
    if config:
        app.config.update(config)
    app.extensions["monthly"] = container or Container(app.config, identity_provider=identity_provider)
    app.register_blueprint(web)

    @app.errorhandler(DomainError)
    def domain_error(error):
        return jsonify(error=str(error)), error.status

    @app.errorhandler(Exception)
    def unexpected_error(error):
        if isinstance(error, HTTPException):
            return jsonify(error="Solicitud no válida."), error.code
        # Never expose upstream response bodies, tokens, local paths or traceback.
        app.logger.error("Fallo interno de tipo %s.", type(error).__name__)
        return jsonify(error="Ocurrió un error inesperado. Intente nuevamente."), 500

    @app.after_request
    def security_headers(response):
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "connect-src 'self'; img-src 'self' data:; base-uri 'self'; form-action 'self'; frame-ancestors 'self'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Cache-Control"] = "no-store"
        return response
    register_auth(app)
    return app
