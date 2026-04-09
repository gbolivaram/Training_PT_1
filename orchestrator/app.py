"""
App Factory — ensambla Flask con Blueprints, DB y CORE.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask
from database import init_schema
from api.routes import api, views


def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY", "colbun-orchestrator-dev-key")

    # Inicializar schema DB
    init_schema()

    # Registrar blueprints
    app.register_blueprint(views)       # Vistas HTML en /
    app.register_blueprint(api, url_prefix="/api")  # API JSON en /api/

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5001)
