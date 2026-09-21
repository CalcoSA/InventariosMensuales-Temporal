from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException
from .config import settings
from .container import Container
from .controllers.web import web
from .models.errors import DomainError


def create_app(config=None, *, container=None, identity_provider=None):
    app = Flask(__name__)
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
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Cache-Control"] = "no-store"
        return response
    return app
