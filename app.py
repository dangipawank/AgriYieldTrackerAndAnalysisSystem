import logging
import os
from flask import Flask, render_template, request

from config import Config
from routes import main
from analysis_routes import analysis
from auth_routes import auth
from init_db import init_database
from utils.security import (
    ensure_csrf_token,
    csrf_protect_request,
    get_current_user
)


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # ---------------- Logging ----------------
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[logging.StreamHandler()],
    )

    # ---------------- Context Processor ----------------
    @app.context_processor
    def inject_globals():
        user = get_current_user()
        return {
            "csrf_token": ensure_csrf_token,
            "current_user": user,
            "current_role": user.get("role") if user else None,
        }

    # ---------------- CSRF Protection ----------------
    @app.before_request
    def before_request():
        csrf_protect_request()

    # ---------------- Error Handlers ----------------
    @app.errorhandler(404)
    def not_found(error):
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def server_error(error):
        return render_template("500.html"), 500

    # ---------------- Blueprints ----------------
    app.register_blueprint(auth)
    app.register_blueprint(main)
    app.register_blueprint(analysis)

    # ---------------- Init DB on startup ----------------
    try:
        init_database()
    except Exception as e:
        app.logger.error(f"Database initialization failed: {e}")

    return app


# ---------------- ENTRY POINT ----------------
app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)