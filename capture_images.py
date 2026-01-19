import cv2  # Thư viện xử lý ảnh, video, camera
import os  # Thư viện thao tác file, thư mục
import numpy as np  # Thư viện mảng số học
import face_recognition  # Thư viện nhận diện khuôn mặt

# Nhập tên lớp và tên người dùng từ bàn phím
class_name = input("Nhập tên lớp: ")  # Ví dụ: lopA
user_name = input("Nhập tên người: ")  # Ví dụ: user1

# Định nghĩa thư mục lưu dữ liệu
dataset_dir = "dataset"  # Thư mục gốc chứa dữ liệu
user_dir = os.path.join(dataset_dir, class_name, user_name)  # Thư mục lớp/người

# Tạo thư mục người dùng nếu chưa tồn tại
os.makedirs(user_dir, exist_ok=True)

# Khởi tạo webcam
cap = cv2.VideoCapture(0)  # Mở camera mặc định (0)
count = 0  # Đếm số frame đã xử lý
max_images = 30  # Số lượng ảnh cần lưu cho mỗi người

# Thông báo bắt đầu quá trình chụp
print(f"Đang chụp {max_images} ảnh cho {user_name} ...")

while count < max_images * 10:  # Lặp qua nhiều frame để đủ số ảnh có mặt
    ret, frame = cap.read()  # Đọc frame từ camera
    if not ret:
        print("[ERR] Không thể truy cập camera!")  # Báo lỗi nếu không lấy được frame
        break

    cv2.imshow("Capture Images", frame)  # Hiển thị frame lên cửa sổ

    # Chuyển frame sang RGB để nhận diện khuôn mặt
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    rgb_frame = np.ascontiguousarray(rgb_frame, dtype=np.uint8)
    # Debug: In ra shape và dtype
    print(f"[DEBUG] rgb_frame shape: {rgb_frame.shape}, dtype: {rgb_frame.dtype}, contiguous: {rgb_frame.flags['C_CONTIGUOUS']}")
    # Kiểm tra đúng định dạng ảnh RGB uint8
    if rgb_frame.ndim == 3 and rgb_frame.shape[2] == 3 and rgb_frame.dtype == np.uint8 and rgb_frame.flags['C_CONTIGUOUS']:
        boxes = face_recognition.face_locations(rgb_frame, model="hog")  # Tìm vị trí khuôn mặt
    else:
        print("[ERR] Frame không đúng định dạng RGB uint8 hoặc không liên tục!")
        boxes = []

    # Mỗi 5 frame kiểm tra và lưu nếu có mặt
    if count % 5 == 0 and len(boxes) > 0:
        img_index = count // 5  # Số thứ tự ảnh
        img_path = os.path.join(user_dir, f"{user_name}_{img_index}.jpg")  # Đường dẫn lưu ảnh

        # Lưu ảnh gốc bằng OpenCV, chuyển sang RGB trước khi lưu
        rgb_save = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        cv2.imwrite(img_path, rgb_save)
        print(f"[SAVE] {img_path} -> {frame.shape} uint8 (Có mặt)")  # Thông báo đã lưu

        if img_index + 1 >= max_images:
            break  # Đủ số lượng ảnh thì dừng

    count += 1  # Tăng số frame

    # Nếu nhấn Enter thì thoát sớm
    if cv2.waitKey(1) == 13:  # 13 là mã phím Enter
        break  # Thoát vòng lặp nếu nhấn Enter

# Giải phóng camera sau khi đủ ảnh
cap.release()  # Giải phóng camera
cv2.destroyAllWindows()  # Đóng tất cả cửa sổ OpenCV

print(f"Hoàn tất! Đã lưu {max_images} ảnh vào thư mục {user_dir}")  # Thông báo kết thúc
