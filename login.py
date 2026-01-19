
# Import các thư viện cần thiết
from flask import Blueprint, render_template, request, redirect, session, url_for  # Flask web framework
from connect_postgres import get_connection  # Hàm kết nối tới cơ sở dữ liệu Postgres


# Tạo Blueprint cho module đăng nhập
login_bp = Blueprint("login", __name__)


# Route xử lý đăng nhập
@login_bp.route("/", methods=["GET", "POST"])
def index():
    # Nếu đã đăng nhập thì chuyển hướng sang dashboard
    if "username" in session:
        return redirect("/dashboard")

    error_message = ""  # Biến lưu thông báo lỗi
    username = ""       # Biến lưu tên đăng nhập
    from werkzeug.security import check_password_hash
    if request.method == "POST":  # Nếu người dùng gửi form đăng nhập
        username = request.form.get("username") or ""   # Lấy username từ form
        password = request.form.get("password") or ""   # Lấy password từ form
        try:
            conn = get_connection()                # Kết nối tới database
            cur = conn.cursor()                    # Tạo cursor để truy vấn
            # Lấy thông tin user, gồm role và password_hash (nếu có)
            cur.execute(
                "SELECT id, role, password, password_hash FROM users WHERE username=%s",
                (username,)
            )
            row = cur.fetchone()
            cur.close()
            conn.close()
            if row:
                user_id, role, legacy_password, password_hash = row
                valid = False
                if password_hash:  # Ưu tiên xác thực bằng password_hash
                    try:
                        valid = check_password_hash(password_hash, password)
                    except Exception:
                        valid = False
                else:
                    # Fallback cho tài khoản cũ dùng plaintext (sẽ loại bỏ dần)
                    valid = (legacy_password == password)
                if valid:
                    session["username"] = username
                    session["role"] = role or "lecturer"
                    session["user_id"] = user_id
                    return redirect("/dashboard")
            error_message = "Sai tài khoản hoặc mật khẩu."
        except Exception:
            error_message = "Lỗi kết nối cơ sở dữ liệu."        # Lỗi kết nối DB

    # Render template tách riêng HTML + CSS
    return render_template("login.html", error_message=error_message, username=username)  # Hiển thị trang đăng nhập
