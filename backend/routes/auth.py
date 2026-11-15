from functools import wraps

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from backend import queries

auth_bp = Blueprint('auth', __name__)

MIN_PASSWORD_LENGTH = 6


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if 'user_id' not in session:
            next_url = request.full_path.rstrip('?') if request.method == 'GET' else None
            return redirect(url_for('auth.login', next=next_url))
        return view(*args, **kwargs)
    return wrapped


def _safe_next(target):
    """Only follow redirects to paths on this site."""
    if target and target.startswith('/') and not target.startswith(('//', '/\\')):
        return target
    return url_for('main.home')


@auth_bp.route("/login", methods=['GET', 'POST'])
def login():
    error = None
    email = ''
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not email or not password:
            error = "Email and password are required"
        else:
            user = queries.find_user_by_email(email)
            if user and check_password_hash(user['password_hash'], password):
                session.clear()
                session['user_id'] = user['id']
                session['username'] = user['username']
                return redirect(_safe_next(request.form.get('next')))
            error = "Invalid email or password"

    next_url = request.values.get('next', '')
    return render_template("login.html", error=error, email=email, next_url=next_url)


@auth_bp.route("/register", methods=['GET', 'POST'])
def register():
    error = None
    username = email = ''
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not username or not email or not password or not confirm_password:
            error = "All fields are required"
        elif not 3 <= len(username) <= 30:
            error = "Username must be 3 to 30 characters"
        elif password != confirm_password:
            error = "Passwords do not match"
        elif len(password) < MIN_PASSWORD_LENGTH:
            error = f"Password must be at least {MIN_PASSWORD_LENGTH} characters"
        elif not queries.create_user(username, email, generate_password_hash(password)):
            error = "Email already registered"
        else:
            flash("Account created! Please log in.", "success")
            return redirect(url_for('auth.login'))

    return render_template("register.html", error=error, username=username, email=email)


@auth_bp.post("/logout")
def logout():
    session.clear()
    return redirect(url_for('main.home'))
