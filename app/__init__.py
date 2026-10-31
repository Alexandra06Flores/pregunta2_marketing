import os
from flask import Flask, flash, redirect, url_for
from app.config import media_dir
from app.data.db import init_db
from app.presentation.routes import bp


def create_app():
    app = Flask(__name__)
    app.secret_key = os.getenv("SECRET_KEY", "dev-secret")
    app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024  # fotos de hasta 8 MB
    app.register_blueprint(bp)

    @app.errorhandler(413)
    def too_large(_e):
        flash("La foto pesa más de 8 MB. Sube una más liviana.", "error")
        return redirect(url_for("main.new"))

    os.makedirs(media_dir(), exist_ok=True)
    init_db()
    return app
