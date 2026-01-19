
# Import các thư viện cần thiết
import os, pickle                # Thao tác file, lưu dữ liệu nhị phân
import numpy as np               # Xử lý mảng số
import face_recognition          # Thư viện nhận diện khuôn mặt
import cv2                       # Thư viện xử lý ảnh


# Đường dẫn tới thư mục dữ liệu và file output
dataset_dir = "dataset"          # Thư mục chứa ảnh từng người
out_file = "encodings.pkl"       # File lưu embeddings khuôn mặt


# Danh sách lưu vector đặc trưng khuôn mặt và tên tương ứng
encodings = []
names = []


# Duyệt qua từng người trong dataset
for person in os.listdir(dataset_dir):
    person_dir = os.path.join(dataset_dir, person)
    if not os.path.isdir(person_dir):
        continue  # Bỏ qua nếu không phải thư mục

    # Duyệt qua từng file ảnh của người đó
    for fname in os.listdir(person_dir):
        if not fname.lower().endswith((".jpg", ".jpeg", ".png", ".bmp")):
            continue  # Bỏ qua file không phải ảnh

        path = os.path.join(person_dir, fname)
        try:
            # Load ảnh bằng OpenCV, chuyển sang RGB
            img = cv2.imread(path)
            if img is None:
                print("[SKIP] Không đọc được ảnh:", path)
                continue
            # Chuyển ảnh về dạng RGB nếu cần
            if img.ndim == 2:
                img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
            elif img.shape[2] == 4:
                img = cv2.cvtColor(img, cv2.COLOR_BGRA2RGB)
            else:
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            img = np.ascontiguousarray(img, dtype=np.uint8)

            # Dlib yêu cầu ảnh (H, W, 3) hoặc (H, W)
            if img.ndim != 3 or img.shape[2] != 3:
                print("[SKIP] Không hợp lệ:", path)
                continue


            # Tìm vị trí khuôn mặt trong ảnh
            boxes = face_recognition.face_locations(img, model="hog")
            if not boxes:
                print("[SKIP] Không tìm thấy mặt:", path)
                continue

            # Trích xuất vector đặc trưng khuôn mặt
            encoding = face_recognition.face_encodings(img, known_face_locations=boxes)[0]
            encodings.append(encoding)  # Lưu vector đặc trưng
            names.append(person)        # Lưu tên người tương ứng
            print("[OK]", person, fname)

        except Exception as e:
            print("[ERR]", path, e)


# Lưu danh sách embeddings và tên vào file nhị phân
with open(out_file, "wb") as f:
    pickle.dump({"encodings": encodings, "names": names}, f)


# In ra kết quả sau khi xử lý
print("Saved", len(encodings), "encodings ->", out_file)
