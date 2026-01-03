# app.py
from flask import Flask
from config import Config
from models import engine, metadata  # ✅ import Core engine and metadata
from routes import main

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)



    # Register blueprints/routes
    app.register_blueprint(main)
    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
