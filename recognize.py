
"""DEPRECATED: upload-image recognition has been removed. Do not import this module."""
raise RuntimeError("recognize.py removed. Use webcam_recognize.py instead.")

# Import các thư viện cần thiết
from flask import Blueprint, request, render_template, send_from_directory  # Flask web framework
from werkzeug.utils import secure_filename  # Đảm bảo tên file an toàn
import os, pickle, cv2, face_recognition    # Thao tác file, nhận diện khuôn mặt
import numpy as np                         # Xử lý mảng số
import json                                # Xử lý dữ liệu JSON
 # Đã xóa ghi lịch sử nhận diện vào DB


# Khai báo Blueprint cho module nhận diện khuôn mặt
recognize_bp = Blueprint("recognize", __name__)


# Tạo thư mục lưu ảnh upload & kết quả nếu chưa có
os.makedirs("uploads", exist_ok=True)
os.makedirs("outputs", exist_ok=True)


# Load dữ liệu khuôn mặt đã encode (encodings.pkl) một cách an toàn
known_encs = []
known_names = []
label_map = {}
try:
    if os.path.exists("encodings.pkl"):
        with open("encodings.pkl","rb") as f:
            data = pickle.load(f)
        known_encs = data.get("encodings", [])
        known_names = data.get("names", [])
    if os.path.exists("labels.json"):
        with open("labels.json", "r", encoding="utf-8") as f:
            label_map = json.load(f)
except Exception as e:
    print(f"[WARN] Failed to load encodings/labels: {e}")



# Ngưỡng để xác định Unknown (khoảng cách lớn hơn thì coi là không nhận diện được)
THRESH = 0.35  # Giống webcam_recognize.py
MIN_CONFIDENCE = 65.0  # Độ tin cậy tối thiểu


# Route nhận diện khuôn mặt từ ảnh upload
@recognize_bp.route("/", methods=["GET","POST"])
def index():
    out_fname = None      # Tên file kết quả
    infos = []            # Danh sách thông tin nhận diện

    if request.method=="POST" and 'file' in request.files:
        # Đã xóa ghi lịch sử nhận diện vào DB
        # Luôn load lại encodings và labels mới nhất để đảm bảo dữ liệu mới
        try:
            if os.path.exists("encodings.pkl"):
                with open("encodings.pkl","rb") as f:
                    data = pickle.load(f)
                known_encs = data.get("encodings", [])
                known_names = data.get("names", [])
            else:
                known_encs, known_names = [], []
            if os.path.exists("labels.json"):
                with open("labels.json", "r", encoding="utf-8") as f:
                    label_map = json.load(f)
            else:
                label_map = {}
        except Exception as e:
            print(f"[WARN] Reload encodings/labels failed: {e}")

        f = request.files['file']
        if not f.filename:
            return "Chưa chọn file", 400  # Nếu chưa chọn file thì báo lỗi

        name = secure_filename(f.filename)         # Đảm bảo tên file an toàn
        in_path = os.path.join("uploads", name)   # Đường dẫn lưu file upload
        f.save(in_path)                            # Lưu file upload


        # Nhận diện ảnh
        img_bgr = cv2.imread(in_path)              # Đọc ảnh bằng OpenCV
        if img_bgr is None:
            return "File ảnh không hợp lệ hoặc không hỗ trợ", 400

        img = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)  # Chuyển sang RGB
        boxes = face_recognition.face_locations(img)     # Tìm vị trí khuôn mặt
        encs = face_recognition.face_encodings(img, boxes) # Trích xuất vector đặc trưng

        # Duyệt qua từng khuôn mặt tìm được
        for (top,right,bottom,left), enc in zip(boxes, encs):
            # Nếu chưa có dữ liệu encodings, gán Unknown
            if not known_encs:
                label = "Unknown"
                confidence = 0.0
            else:
                dists = face_recognition.face_distance(known_encs, enc) # Tính khoảng cách với các khuôn mặt đã biết
                if len(dists) == 0:
                    label = "Unknown"
                    confidence = 0.0
                else:
                    idx = int(np.argmin(dists))                             # Vị trí gần nhất
                    min_dist = float(dists[idx])                            # Khoảng cách nhỏ nhất
                    confidence = (1 - min_dist) * 100
                    if min_dist <= THRESH and confidence >= MIN_CONFIDENCE:
                        label = known_names[idx]
                    else:
                        label = "Unknown"

            # Vẽ khung và tên lên ảnh kết quả
            color = (0,255,0) if label != "Unknown" else (0,165,255)
            cv2.rectangle(img_bgr, (left, top), (right, bottom), color, 2)
            cv2.putText(img_bgr, label, (left, top-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

            # Lấy thông tin chi tiết từ label_map
            if label in label_map:
                infos.append({
                    "fullname": label_map[label]["fullname"],
                    "classname": label_map[label].get("classname", ""),
                    "desc": label_map[label].get("desc", "Không có mô tả"),
                    "label": label,
                    "confidence": f"{confidence:.1f}%"
                })
            else:
                infos.append({
                    "fullname": "Unknown",
                    "classname": "",
                    "desc": "Không có dữ liệu",
                    "label": label,
                    "confidence": f"{confidence:.1f}%"
                })

            # Ghi lịch sử nhận diện vào DB (không chặn luồng chính nếu lỗi)
            try:
                fullname = label_map[label]["fullname"] if label in label_map else (label if label != "Unknown" else "Unknown")
                pass  # Đã xóa ghi lịch sử nhận diện vào DB
            except Exception as e:
                pass  # Đã xóa ghi lịch sử nhận diện vào DB

        out_fname = "res_" + name  # Tên file kết quả
        cv2.imwrite(os.path.join("outputs", out_fname), img_bgr)  # Lưu ảnh kết quả

    # Trả về giao diện nhận diện, kèm thông tin và ảnh kết quả
    return render_template("recognize.html", out=out_fname, infos=infos)


# Route phục vụ ảnh output (trả về file ảnh kết quả)
@recognize_bp.route("/outputs/<path:filename>")
def get_output(filename):
    return send_from_directory("outputs", filename)
