from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from services.auth_service import get_user_by_login, verify_password, update_user_last_seen
from utils.security import login_required


auth = Blueprint("auth", __name__)


@auth.route("/login", methods=["GET", "POST"])
def login():
    """Authenticate user using username/email + password and store user session."""
    errors = {}
    login_value = ""

    if request.method == "POST":
        login_value = request.form.get("login", "").strip()
        password = request.form.get("password", "")

        if not login_value:
            errors["login"] = "Username or email is required."
        if not password:
            errors["password"] = "Password is required."

        if not errors:
            user = get_user_by_login(login_value)
            if not user or not verify_password(password, user["password_hash"]):
                errors["global"] = "Invalid credentials."
            else:
                session["user_id"] = user["id"]
                session["username"] = user["username"]
                session["role"] = user["role"]
                update_user_last_seen(user["id"])
                flash(f"Welcome, {user['username']}!", "success")
                return redirect(url_for("main.dashboard"))

    return render_template("login.html", errors=errors, login_value=login_value)


@auth.route("/register", methods=["GET", "POST"])
def register():
    flash("Public registration is disabled. Please contact Admin.", "danger")
    return redirect(url_for("auth.login"))


@auth.route("/logout", methods=["POST"])
@login_required
def logout():
    """Logout current user by clearing session."""
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("auth.login"))
