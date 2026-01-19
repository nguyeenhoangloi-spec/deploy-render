from flask import Blueprint, render_template, session, redirect, url_for
home_bp = Blueprint("home", __name__)

@home_bp.route("/")
def index():
    if "username" in session:
        # Nếu đã đăng nhập → chuyển sang Dashboard
        return redirect(url_for("dashboard.index"))
    else:
        # Nếu chưa đăng nhập → hiện trang home giống dashboard nhưng redirect về login
        return render_template("home.html")