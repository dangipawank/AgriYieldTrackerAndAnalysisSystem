import secrets
from functools import wraps
from flask import session, request, abort, flash, redirect, url_for

from services.auth_service import get_user_by_id


SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}


def ensure_csrf_token() -> str:
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(24)
    return session["csrf_token"]


def csrf_protect_request():
    if request.method in SAFE_METHODS:
        ensure_csrf_token()
        return

    token_in_session = session.get("csrf_token")
    token_from_form = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")

    if not token_in_session or token_in_session != token_from_form:
        abort(400, description="Invalid CSRF token")


def login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login to continue.", "danger")
            return redirect(url_for("auth.login"))
        return view_func(*args, **kwargs)

    return wrapper


def role_required(*allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(*args, **kwargs):
            user_role = session.get("role")
            if user_role not in allowed_roles:
                flash("You are not authorized to access this page.", "danger")
                return redirect(url_for("main.dashboard"))
            return view_func(*args, **kwargs)

        return wrapper

    return decorator


def get_current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return get_user_by_id(user_id)


def get_current_user_id() -> int | None:
    return session.get("user_id")
