conda activate faceenv
D:
cd PythonDA
python app.py

.\ngrok http 5000

HỆ THỐNG ĐIỂM DANH SINH VIÊN (WEB)
│
├── 1. XÁC THỰC & PHÂN QUYỀN
│ ├── Đăng nhập / đăng xuất
│ ├── Phân quyền
│ │ ├── Giảng viên
│ │ └── Quản trị viên
│ └── Quản lý tài khoản
│
├── 2. QUẢN LÝ SINH VIÊN
│ ├── Thêm / sửa / xóa sinh viên
│ ├── Gán sinh viên vào lớp
│ ├── Quản lý khuôn mặt
│ │ ├── Thêm ảnh khuôn mặt
│ │ └── Cập nhật dữ liệu nhận diện
│ ├── Nhập danh sách sinh viên (Excel)
│ └── Tìm kiếm / lọc sinh viên
│
├── 3. QUẢN LÝ LỚP HỌC & MÔN HỌC
│ ├── Thêm / sửa / xóa lớp học
│ ├── Thêm / sửa / xóa môn học
│ ├── Gán môn học cho lớp
│ └── Gán giảng viên cho lớp
│
├── 4. QUẢN LÝ BUỔI HỌC
│ ├── Tạo buổi học
│ │ ├── Ngày học
│ │ ├── Ca học
│ │ └── Phòng học
│ ├── Bắt đầu điểm danh
│ ├── Kết thúc điểm danh
│ └── Xem lịch sử buổi học
│
├── 5. ĐIỂM DANH SINH VIÊN
│ ├── Điểm danh bằng Laptop
│ │ └── Sử dụng webcam
│ │
│ ├── Điểm danh bằng Điện thoại
│ │ ├── Tạo session điểm danh
│ │ ├── Kết nối bằng QR code / mã phiên
│ │ └── Giao diện camera di động
│ │
│ ├── Nhận diện khuôn mặt (AI)
│ │ ├── Phát hiện nhiều khuôn mặt (YOLO)
│ │ ├── Nhận diện danh tính
│ │ └── Hiển thị % độ giống
│ │
│ ├── Trạng thái điểm danh
│ │ ├── Có mặt
│ │ ├── Đi trễ
│ │ └── Vắng
│ │
│ └── Chỉnh sửa điểm danh thủ công
│ ├── Điểm danh bổ sung
│ └── Hủy điểm danh
│
├── 6. ĐỒNG BỘ REAL-TIME
│ ├── Đồng bộ kết quả giữa điện thoại & laptop
│ ├── Hiển thị kết quả tức thì
│ └── Trạng thái sinh viên theo thời gian thực
│
├── 7. THỐNG KÊ & BÁO CÁO
│ ├── Thống kê theo buổi học
│ ├── Thống kê theo sinh viên
│ ├── Thống kê theo lớp
│ ├── Xuất báo cáo Excel
│ └── Xuất báo cáo PDF (mô tả)
│
├── 8. NHẬT KÝ & LỊCH SỬ
│ ├── Lịch sử điểm danh
│ ├── Thời gian điểm danh
│ ├── Thiết bị điểm danh (laptop / điện thoại)
│ └── Ảnh minh chứng (tùy chọn)
│
└── 9. CẤU HÌNH HỆ THỐNG
├── Ngưỡng nhận diện (% độ giống)
├── Thời gian cho phép điểm danh
├── Bật / tắt điểm danh bằng điện thoại
└── Cấu hình bảo mật cơ bản
