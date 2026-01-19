# Import Flask và các module cần thiết
from flask import Flask, redirect, render_template, jsonify  # Flask web framework

# Import các Blueprint (module chức năng) của ứng dụng
from home import home_bp                # Blueprint cho trang chủ
from dashboard import dashboard_bp      # Blueprint cho dashboard quản trị
from login import login_bp              # Blueprint cho chức năng đăng nhập
from logout import logout_bp            # Blueprint cho chức năng đăng xuất
from register import register_bp        # Blueprint cho chức năng đăng ký tài khoản
from add_user import add_user_bp        # Blueprint cho chức năng thêm người dùng mới
from webcam_recognize import webcam_bp  # Blueprint cho chức năng nhận diện qua webcam
from students import students_bp         # Quản lý sinh viên
from classes import classes_bp           # Quản lý lớp
from subjects import subjects_bp         # Quản lý môn học
from attendance import attendance_bp     # Quản lý buổi học & điểm danh
from settings import settings_bp         # Cấu hình hệ thống

# Khởi tạo ứng dụng Flask
app = Flask(__name__)
# Khóa bí mật dùng cho session, bảo mật đăng nhập
app.secret_key = "abC!@#123_XYZ_long_random_string"

# Đăng ký các Blueprint vào ứng dụng Flask
app.register_blueprint(home_bp, url_prefix="/")            # Trang chủ
app.register_blueprint(dashboard_bp, url_prefix="/dashboard") # Dashboard quản trị
app.register_blueprint(login_bp, url_prefix="/login")          # Đăng nhập
app.register_blueprint(logout_bp, url_prefix="/logout")        # Đăng xuất
app.register_blueprint(register_bp, url_prefix="/register")    # Đăng ký tài khoản
app.register_blueprint(add_user_bp, url_prefix="/add_user")    # Thêm người dùng mới
app.register_blueprint(webcam_bp, url_prefix="/webcam")        # Nhận diện qua webcam
app.register_blueprint(students_bp, url_prefix="/students")    # Quản lý sinh viên
app.register_blueprint(classes_bp, url_prefix="/classes")      # Quản lý lớp
app.register_blueprint(subjects_bp, url_prefix="/subjects")    # Quản lý môn học
app.register_blueprint(attendance_bp, url_prefix="/attendance")# Quản lý buổi học
app.register_blueprint(settings_bp, url_prefix="/settings")    # Cấu hình hệ thống

# Xử lý lỗi tập trung: trả về trang lỗi với thông báo rõ ràng
@app.errorhandler(403)
def handle_forbidden(e):
    return render_template("error.html", code=403, message="Bạn không có quyền truy cập chức năng này."), 403

@app.errorhandler(404)
def handle_not_found(e):
    return render_template("error.html", code=404, message="Không tìm thấy trang hoặc tài nguyên yêu cầu."), 404

@app.errorhandler(500)
def handle_server_error(e):
    return render_template("error.html", code=500, message="Lỗi hệ thống. Vui lòng thử lại sau hoặc liên hệ quản trị viên."), 500

# Endpoint kiểm tra sức khỏe hệ thống để liên kết từ trang lỗi
@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200

# Chạy ứng dụng Flask ở chế độ debug khi thực thi trực tiếp
if __name__ == "__main__":
    import webbrowser                   # Import module mở trình duyệt web
    url = "http://127.0.0.1:5000"       # Địa chỉ truy cập ứng dụng
    print(f"\nTruy cập ứng dụng tại: {url}\n") # In ra địa chỉ truy cập ứng dụng
    from waitress import serve
    serve(app, host="0.0.0.0", port=5000)
