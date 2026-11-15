"""GameVault Flask application factory."""
import hmac
import logging
import os
import re
import secrets
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, abort, render_template, request, session
from werkzeug.exceptions import HTTPException

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

_STEAM_HEADER = re.compile(r"(/steam/apps/\d+/)header\.jpg$")


def format_price(value):
    return f"₹{value:,}" if value else "Free"


def format_date(value, fallback="—"):
    """ISO date or timestamp string -> '25 Feb 2022'."""
    if not value:
        return fallback
    try:
        return datetime.fromisoformat(value).strftime("%d %b %Y").lstrip("0")
    except ValueError:
        return fallback


def hero_image(url):
    """Steam header images are 460px wide; use the wide artwork where one exists."""
    return _STEAM_HEADER.sub(r"\1library_hero.jpg", url)


def csrf_token():
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_urlsafe(32)
    return session["_csrf"]


def _check_csrf():
    if request.method != "POST":
        return
    expected = session.get("_csrf")
    sent = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token", "")
    if not expected or not hmac.compare_digest(sent, expected):
        abort(400, description="Your session expired. Go back, refresh the page and try again.")


def create_app():
    app = Flask(
        __name__,
        template_folder=str(ROOT / "templates"),
        static_folder=str(ROOT / "static"),
    )

    secret_key = os.environ.get("SECRET_KEY")
    if not secret_key:
        secret_key = secrets.token_hex(32)
        app.logger.warning("SECRET_KEY is not set; sessions will reset on every restart.")
    app.config.update(
        SECRET_KEY=secret_key,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE") == "1",
    )
    logging.basicConfig(level=logging.INFO)

    app.jinja_env.filters.update(inr=format_price, date=format_date, hero_image=hero_image)
    app.jinja_env.globals["csrf_token"] = csrf_token
    app.before_request(_check_csrf)

    from backend.routes.auth import auth_bp
    from backend.routes.main import main_bp
    from backend.routes.shop import shop_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(shop_bp)

    @app.errorhandler(HTTPException)
    def http_error(error):
        return render_template("error.html", error=error), error.code

    @app.errorhandler(Exception)
    def unexpected_error(error):
        app.logger.exception("Unhandled error on %s %s", request.method, request.path)
        return render_template("error.html", error=None), 500

    return app
