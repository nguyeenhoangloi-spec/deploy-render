from flask import Blueprint, request, render_template
from connect_postgres import get_connection
from werkzeug.security import generate_password_hash

register_bp = Blueprint("register", __name__)


@register_bp.route("/", methods=["GET", "POST"])
def index():
    # Thông báo trạng thái đăng ký
    message = ""
    # Lưu giá trị form để giữ lại khi lỗi
    form_data = {"fullname": "", "email": "", "phone": "", "username": ""}
    if request.method == "POST":
        # Lấy dữ liệu từ form
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        fullname = request.form.get("fullname", "")
        email = request.form.get("email", "")
        phone = request.form.get("phone", "")
        # Lưu lại dữ liệu đã nhập để hiển thị lại khi có lỗi
        form_data = {"fullname": fullname, "email": email, "phone": phone, "username": username}
        # Dùng regex để kiểm tra số điện thoại
        import re
        # Số điện thoại phải bắt đầu bằng 0, có 9-11 số
        phone_valid = re.fullmatch(r"0\d{8,10}", phone)
        # Báo lỗi nếu nhập sai định dạng
        if not phone_valid:
            message = "Số điện thoại không hợp lệ. Vui lòng nhập đúng định dạng số!"
        # Báo lỗi nếu xác nhận mật khẩu không khớp
        elif password != confirm_password:
            message = "Mật khẩu xác nhận không khớp."
        else:
            try:
                # Kết nối database
                conn = get_connection()
                cur = conn.cursor()
                # Kiểm tra tài khoản đã tồn tại chưa
                cur.execute("SELECT id FROM users WHERE username=%s", (username,))
                # Báo lỗi nếu username đã tồn tại
                if cur.fetchone():
                    message = "Tài khoản đã tồn tại."
                else:
                    # Thêm tài khoản mới vào database với mật khẩu được hash và role mặc định là giảng viên
                    pwd_hash = generate_password_hash(password)
                    cur.execute(
                        "INSERT INTO users (username, password, password_hash, fullname, email, phone, role) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                        (username, None, pwd_hash, fullname, email, phone, 'lecturer')
                    )
                    conn.commit()
                    # Thông báo thành công
                    message = "Đăng ký thành công!"
                    # Reset form nếu thành công
                    form_data = {"fullname": "", "email": "", "phone": "", "username": ""}
                cur.close()
                conn.close()
            # Báo lỗi nếu không kết nối được DB
            except Exception as e:
                message = "Lỗi kết nối cơ sở dữ liệu."
    # Trả về template với thông báo và dữ liệu form
    return render_template("register.html", message=message, form_data=form_data)