import logging
from flask import Flask, render_template
from config import Config

from routes import main
from analysis_routes import analysis
from auth_routes import auth
from utils.security import ensure_csrf_token, csrf_protect_request, get_current_user

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[logging.FileHandler("app.log"), logging.StreamHandler()],
    )

    @app.context_processor
    def inject_csrf_token():
        active_user = get_current_user()
        return {
            "csrf_token": ensure_csrf_token,
            "current_user": active_user,
            "current_role": active_user.get("role") if active_user else None,
        }

    @app.before_request
    def csrf_protect():
        csrf_protect_request()

    @app.errorhandler(404)
    def handle_404(error):
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def handle_500(error):
        return render_template("500.html"), 500


    app.register_blueprint(auth)
    app.register_blueprint(main)
    app.register_blueprint(analysis)

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=False)
