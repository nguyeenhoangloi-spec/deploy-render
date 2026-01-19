from functools import wraps
from flask import session, redirect, url_for, abort, flash


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "username" not in session:
            flash("Vui lòng đăng nhập để tiếp tục", "info")
            return redirect(url_for("login.index"))
        return f(*args, **kwargs)
    return wrapper


def role_required(*roles):
    """Decorate a view to require one of the given roles."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if "username" not in session:
                return redirect(url_for("login.index"))
            user_role = session.get("role", "lecturer")
            if roles and user_role not in roles:
                return abort(403)
            return f(*args, **kwargs)
        return wrapper
    return decorator
