# Import các thư viện cần thiết
from flask import Blueprint, session, redirect, url_for  # Flask web framework


# Tạo Blueprint cho module đăng xuất
logout_bp = Blueprint("logout", __name__)


# Route xử lý đăng xuất
@logout_bp.route("/")
def index():
    # Xóa thông tin đăng nhập trong session (đăng xuất)
    session.pop("username", None)
    session.pop("role", None)
    session.pop("user_id", None)
    # Sau khi đăng xuất thì chuyển về trang chủ (home)
    return redirect(url_for("home.index"))
