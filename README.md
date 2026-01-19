# Đề tài: Hệ thống điểm danh nhận diện khuôn mặt

## Mục tiêu

Xây dựng hệ thống quản lý điểm danh sinh viên sử dụng nhận diện khuôn mặt, hỗ trợ quản lý lớp, môn học, sinh viên, lịch sử điểm danh, và các chức năng liên quan.

---

## Chức năng & Vai trò từng file chính

### 1. app.py

- **Khởi tạo Flask app, đăng ký các Blueprint** (module chức năng)
- **Xử lý lỗi tập trung** (403, 404, 500)
- **Cung cấp endpoint kiểm tra hệ thống** (`/health`)

### 2. home.py

- Trang chủ, chuyển hướng dashboard nếu đã đăng nhập

### 3. dashboard.py

- Giao diện chính sau khi đăng nhập, truy cập nhanh các chức năng quản trị

### 4. login.py / logout.py

- Đăng nhập, đăng xuất hệ thống

### 5. register.py

- Đăng ký tài khoản mới

### 6. auth.py

- Định nghĩa decorator kiểm tra đăng nhập/quyền truy cập

### 7. add_user.py

- Thêm người dùng mới, chụp ảnh khuôn mặt, lưu nhãn

### 8. webcam_recognize.py

- Nhận diện khuôn mặt từ webcam
- Lưu ý: chức năng upload ảnh đã được gỡ bỏ khỏi giao diện và backend (không đăng ký route `recognize`).

### 9. students.py

- Quản lý sinh viên: thêm, sửa, xóa, nhập Excel, gán lớp

### 10. classes.py

- Quản lý lớp học: thêm, sửa, xóa, gán môn, gán giảng viên
- Phân quyền: **chỉ Admin** được thêm/sửa/xóa lớp; **Giảng viên** chỉ xem các lớp được phân công (không có quyền tạo/sửa/xóa). Các thao tác gán môn/giảng viên là của Admin.

### 11. subjects.py

- Quản lý môn học: thêm, sửa, xóa
- Phân quyền: **chỉ Admin** được thêm/sửa/xóa môn học; **Giảng viên** chỉ xem các môn được phân công (không có quyền tạo/sửa/xóa).

### 12. attendance.py

- Quản lý buổi học, tạo phiên điểm danh, điểm danh qua QR/webcam/điện thoại

### 13. (Đã loại bỏ) history.py / history_db_recognition.py

- Các file này đã được xóa, không còn sử dụng trong hệ thống.

### 14. Hướng dẫn nhập sinh viên từ Excel

- File Excel cần có 5 cột theo thứ tự: Mã SV | Họ tên | Email | SĐT | Lớp (dạng "Mã - Tên" hoặc chỉ "Mã").
- Hệ thống sẽ tự động nhận diện lớp nếu đã tồn tại trong database.

### 14. settings.py

- Cấu hình hệ thống: ngưỡng nhận diện, cho phép điểm danh điện thoại, v.v.

### 15. connect_postgres.py

- Kết nối cơ sở dữ liệu PostgreSQL

### 16. init_db.py / schema.sql

- Khởi tạo, cập nhật cấu trúc database

### 17. prepare_embeddings.py / update_single_embedding.py

- Xử lý embedding khuôn mặt cho nhận diện

### 18. templates/

- Thư mục chứa các file giao diện HTML (Jinja2)
  - **\_flash.html**: Hiển thị thông báo
  - **error.html**: Trang lỗi chung
  - **home.html, dashboard.html, ...**: Giao diện từng chức năng

### 19. dataset/, outputs/, uploads/

- Lưu trữ ảnh khuôn mặt, kết quả nhận diện, file upload

### 20. labels.json, yolov8n-face.pt, yolov11n-face.pt

- File nhãn khuôn mặt, model nhận diện YOLO

---

## Sơ đồ tổng quan

- Người dùng đăng nhập → dashboard → chọn chức năng (quản lý sinh viên, lớp, môn, điểm danh...)
- Điểm danh: tạo phiên → sinh viên quét QR hoặc nhận diện webcam → lưu lịch sử
- Quản trị viên cấu hình hệ thống, xem lịch sử, xuất báo cáo

---

## Ghi chú

- Mỗi file Python là một module chức năng riêng biệt, dễ bảo trì và mở rộng.
- Giao diện chia nhỏ theo template, dễ chỉnh sửa.
- Có thể mở rộng thêm API, mobile, hoặc tích hợp AI khác nếu cần.

---
