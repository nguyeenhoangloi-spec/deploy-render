# Thiết lập biến môi trường để tránh lỗi khi dùng nhiều thư viện C++ (đặc biệt với numpy, OpenCV)
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# Import các thư viện cần thiết
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')  # Thiết lập log chi tiết
from typing import Any  # Định nghĩa kiểu dữ liệu cho biến
from flask import Blueprint, Response, render_template, jsonify  # Flask web framework
import cv2, face_recognition, pickle, numpy as np, json, time   # Xử lý ảnh, nhận diện khuôn mặt, lưu dữ liệu
from datetime import datetime                                   # Xử lý thời gian
import threading, queue  # Quản lý luồng và hàng đợi (nếu cần xử lý đa luồng)
# Thiết lập kích thước khung hình chuẩn
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
FRAME_SIZE = (FRAME_WIDTH, FRAME_HEIGHT)
 # Đã xóa ghi lịch sử nhận diện vào DB
# Đổi sang dùng model YOLOv8m-face.pt để nhận diện chính xác hơn
try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None
    yolo_model = None
else:
    try:
        yolo_model = YOLO('yolov11n-face.pt')  # Đổi tên model nếu bạn dùng model khác
        yolo_model.overrides['verbose'] = False
        print("[INFO] Loaded YOLOv11n-face model (global)")
    except Exception as e:
        print(f"[WARNING] Không tải YOLO: {e}")
        yolo_model = None


from flask import request
# Khai báo Blueprint cho module nhận diện qua webcam
webcam_bp = Blueprint("webcam", __name__)  # Khởi tạo blueprint cho chức năng nhận diện webcam

# Route reload dữ liệu nhận diện (embeddings, labels)

# Hàm load_data: Đọc dữ liệu embeddings và labels từ file
def load_data():
    """
    Đọc dữ liệu embeddings và labels từ file
    """
    global known_encs, known_names, label_map  # Khai báo biến toàn cục để lưu dữ liệu khuôn mặt và nhãn
    # Đọc encodings.pkl (dữ liệu vector khuôn mặt)
    try:
        # Mở file encodings.pkl ở chế độ đọc nhị phân
        with open("encodings.pkl", "rb") as f:
            data = pickle.load(f)  # Đọc dữ liệu đã lưu bằng pickle
        known_encs = data["encodings"]  # Lấy danh sách vector đặc trưng khuôn mặt
        known_names = data["names"]     # Lấy danh sách tên tương ứng với từng vector
        logging.info(f"Loaded {len(known_encs)} encodings")  # Ghi log số lượng khuôn mặt đã nạp
        if len(known_encs) == 0:
            logging.warning("File encodings.pkl tồn tại nhưng không có dữ liệu!")  # Cảnh báo nếu file rỗng
            logging.info("Hãy chạy 'python prepare_embeddings.py' để tạo dữ liệu từ thư mục dataset")  # Hướng dẫn tạo dữ liệu
    except FileNotFoundError:
        logging.error("File encodings.pkl không tồn tại!")  # Báo lỗi nếu không tìm thấy file
        logging.info("Hãy chạy 'python prepare_embeddings.py' để tạo dữ liệu từ thư mục dataset")  # Hướng dẫn tạo dữ liệu
        known_encs = []  # Khởi tạo danh sách rỗng nếu không có dữ liệu
        known_names = []
    except Exception as e:
        logging.error(f"Lỗi khi đọc encodings.pkl: {e}")  # Báo lỗi nếu có vấn đề khi đọc file
        known_encs = []
        known_names = []

    # Đọc labels.json (thông tin chi tiết từng người)
    try:
        # Mở file labels.json ở chế độ đọc văn bản với mã hóa utf-8
        with open("labels.json", "r", encoding="utf-8") as f:
            label_map = json.load(f)  # Đọc dữ liệu nhãn từ file json
        logging.info(f"Loaded {len(label_map)} labels")  # Ghi log số lượng nhãn đã nạp
    except FileNotFoundError:
        logging.error("labels.json not found!")  # Báo lỗi nếu không tìm thấy file
        label_map = {}  # Khởi tạo dict rỗng nếu không có dữ liệu

load_data()  # Gọi hàm để nạp dữ liệu khi khởi động


 # Ngưỡng để xác định Unknown (khoảng cách lớn hơn thì coi là không nhận diện được)
THRESH = 0.35         # Ngưỡng khoảng cách: nếu >0.35 thì coi là không nhận diện được (tương đương ~65% độ tin cậy)
MIN_CONFIDENCE = 65.0 # Yêu cầu độ tin cậy tối thiểu 65% để xác nhận danh tính

# Biến toàn cục quản lý trạng thái webcam và thông tin nhận diện
cap = None  # Đối tượng quản lý webcam
running = False  # Trạng thái đang chạy của webcam
current_person_info = None  # Thông tin người vừa nhận diện
track_cache = {}  # Bộ nhớ tạm cho các track nhận diện
recognized_tracks = {}  # Lưu track ID đã nhận diện để tránh nhận lại
latest_boxes = []  # Lưu bounding box khuôn mặt mới nhất
prev_boxes = []    # Lưu bounding box khuôn mặt trước đó
boxes_lock = threading.Lock()  # Khóa luồng để đồng bộ hóa truy cập bounding box
last_box_update = 0  # Thời điểm cập nhật bounding box cuối cùng
recognition_thread = None  # Luồng nhận diện khuôn mặt
MIRROR = True  # Có lật ảnh ngang khi stream không (giúp giống gương)

# Hàm reload lại dữ liệu embeddings và labels từ file
def reload_data():
    """Reload encodings và labels từ file"""
    load_data()  # Gọi lại hàm load_data để nạp lại dữ liệu

# Hàm chuyển đổi ảnh về RGB đúng chuẩn
def to_rgb(img):
    if img is None:
        return None  # Nếu ảnh rỗng thì trả về None
    if img.ndim == 2:
        return cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)  # Chuyển ảnh xám sang RGB
    elif img.shape[2] == 4:
        return cv2.cvtColor(img, cv2.COLOR_BGRA2RGB)  # Chuyển ảnh BGRA sang RGB
    elif img.shape[2] == 3:
        return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)   # Chuyển ảnh BGR sang RGB
    return img  # Nếu đã đúng chuẩn thì trả về nguyên trạng


# Hàm sinh luồng ảnh từ webcam, đồng thời nhận diện khuôn mặt bằng YOLO
def gen_frames():
    global cap, running, recognition_thread, latest_boxes, prev_boxes, last_box_update

        # FRAME_SIZE đã được khai báo toàn cục phía trên
    class RecognitionThread(threading.Thread):
        def __init__(self):
            super().__init__(daemon=True)  # Khởi tạo luồng ở chế độ daemon
            self.frame_queue = queue.Queue(maxsize=2)  # Hàng đợi lưu frame để nhận diện
            self.running = True  # Trạng thái chạy của luồng
            # self.yolo_model = None  # Bỏ dòng này

        def add_frame(self, frame):
            # Hàm nhận frame để xử lý nhận diện
            try:
                if self.frame_queue.full():  # Nếu hàng đợi đầy
                    try:
                        self.frame_queue.get_nowait()  # Lấy ra 1 frame cũ để tránh tràn bộ nhớ
                    except:
                        pass
                self.frame_queue.put_nowait(frame.copy())  # Đưa frame mới vào hàng đợi
            except:
                pass  # Bỏ qua nếu có lỗi

        # Hàm chạy luồng nhận diện
        def run(self):
            global current_person_info, latest_boxes, track_cache, recognized_tracks
            frame_count = 0  # Đếm số frame đã xử lý
            while self.running:
                try:
                    frame_rgb = self.frame_queue.get(timeout=1.0)  # Lấy frame từ hàng đợi, timeout 1 giây
                except queue.Empty:
                    continue  # Nếu không có frame thì tiếp tục vòng lặp
                frame_count += 1
                if frame_count % 3 != 0:
                    continue  # Chỉ xử lý mỗi 3 frame để tăng tốc độ nhận diện
                current_time = time.time()  # Lấy thời gian hiện tại
                try:
                    if len(known_encs) == 0:  # Nếu chưa có dữ liệu khuôn mặt
                        with boxes_lock:
                            latest_boxes = []  # Xóa danh sách bounding box
                            current_person_info = [{
                                "label": "No Data",  # Gán thông báo chưa có dữ liệu
                                "fullname": "Chưa có dữ liệu",
                                "desc": "Chạy: python prepare_embeddings.py",
                                "confidence": "0%",
                                "time": datetime.now().strftime("%H:%M:%S")
                            }]
                        continue  # Bỏ qua nhận diện nếu chưa có dữ liệu
                    detected_persons = []  # Danh sách người nhận diện được
                    detected_boxes = []    # Danh sách bounding box khuôn mặt
                    h, w = frame_rgb.shape[:2]  # Lấy kích thước ảnh gốc
                    small_frame = cv2.resize(frame_rgb, FRAME_SIZE)  # Resize ảnh về FRAME_SIZE để xử lý
                    current_track_ids = set()  # Tập hợp các track ID hiện tại
                    if yolo_model is not None:
                        # Nhận diện khuôn mặt bằng YOLO, trả về kết quả tracking
                        results = yolo_model.track(
                            small_frame,
                            imgsz=FRAME_WIDTH,      # Kích thước ảnh đầu vào cho YOLO
                            conf=0.5,       # Ngưỡng confidence
                            iou=0.5,        # Ngưỡng IOU
                            device='cpu',   # Chạy trên CPU
                            persist=True,   # Giữ trạng thái tracking
                            verbose=False   # Không in log chi tiết
                        )
                        scale_x = w / FRAME_WIDTH  # Tính hệ số scale lại bounding box về kích thước gốc
                        scale_y = h / FRAME_HEIGHT
                        if results and len(results) > 0 and results[0].boxes is not None:
                            for box in results[0].boxes:
                                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())  # Lấy tọa độ bounding box
                                track_id = int(box.id.item()) if box.id is not None else -1  # Lấy track ID nếu có
                                x1 = int(x1 * scale_x)  # Scale lại tọa độ về ảnh gốc
                                x2 = int(x2 * scale_x)
                                y1 = int(y1 * scale_y)
                                y2 = int(y2 * scale_y)
                                x1 = max(0, min(x1, w-1))  # Đảm bảo tọa độ không vượt quá kích thước ảnh
                                x2 = max(0, min(x2, w-1))
                                y1 = max(0, min(y1, h-1))
                                y2 = max(0, min(y2, h-1))
                                if x2 <= x1 or y2 <= y1:
                                    continue  # Bỏ qua nếu bounding box không hợp lệ
                                current_track_ids.add(track_id)  # Thêm track ID vào danh sách hiện tại
                                need_recognition = False  # Biến kiểm tra có cần nhận diện lại không
                                if track_id not in recognized_tracks:
                                    need_recognition = True  # Nếu track mới thì nhận diện
                                elif (current_time - recognized_tracks[track_id]["last_seen"]) > 2:
                                    need_recognition = True  # Nếu track đã lâu không xuất hiện thì nhận diện lại (2 giây)
                                if track_id in recognized_tracks:
                                    recognized_tracks[track_id]["last_seen"] = current_time  # Cập nhật thời gian xuất hiện cuối
                                if need_recognition:
                                    # Chuyển bounding box về tọa độ ảnh nhỏ (YOLO)
                                    sx1 = int(x1 / scale_x)
                                    sx2 = int(x2 / scale_x)
                                    sy1 = int(y1 / scale_y)
                                    sy2 = int(y2 / scale_y)
                                    face_box = (sy1, sx2, sy2, sx1)  # Định dạng box cho face_recognition
                                    try:
                                        # Trích xuất vector đặc trưng khuôn mặt
                                        enc = face_recognition.face_encodings(small_frame, [face_box], num_jitters=0)
                                        if enc and len(enc) > 0:
                                            enc = enc[0]  # Lấy vector đầu tiên
                                            dists = face_recognition.face_distance(known_encs, enc)  # Tính khoảng cách với các khuôn mặt đã biết
                                            idx = int(np.argmin(dists))  # Tìm vị trí có khoảng cách nhỏ nhất
                                            min_dist = float(dists[idx])  # Lấy giá trị khoảng cách nhỏ nhất
                                            if min_dist <= THRESH:
                                                label = known_names[idx]  # Nếu đủ gần thì gán tên nhận diện
                                                confidence = (1 - min_dist) * 100  # Tính độ tin cậy
                                            else:
                                                label = "Unknown"  # Nếu không đủ gần thì gán Unknown
                                                confidence = (1 - min_dist) * 100
                                            if label != "Unknown":
                                                recognized_tracks[track_id] = {
                                                    "name": label,
                                                    "confidence": confidence,
                                                    "last_seen": current_time,
                                                    "first_recognized": current_time
                                                }  # Lưu kết quả nhận diện vào dict
                                                track_cache[track_id] = {
                                                    "name": label,
                                                    "confidence": confidence,
                                                    "last_update": current_time
                                                }  # Lưu cache cho track
                                                print(f"[RECOGNIZED] Track {track_id}: {label} ({confidence:.1f}%)")  # In log nhận diện
                                        else:
                                            label = "Unknown"  # Nếu không trích xuất được khuôn mặt
                                            confidence = 0
                                            recognized_tracks[track_id] = {
                                                "name": label,
                                                "confidence": confidence,
                                                "last_seen": current_time,
                                                "first_recognized": current_time
                                            }
                                    except Exception as e:
                                        label = "Unknown"  # Nếu có lỗi thì gán Unknown
                                        confidence = 0
                                else:
                                    # Nếu không cần nhận diện lại, lấy thông tin từ recognized_tracks
                                    if track_id in recognized_tracks:
                                        label = recognized_tracks[track_id]["name"]
                                        confidence = recognized_tracks[track_id]["confidence"]
                                    else:
                                        label = "Processing..."  # Đang xử lý nhận diện
                                        confidence = 0
                                # Lưu thông tin bounding box và kết quả nhận diện vào danh sách
                                detected_boxes.append({
                                    "box": (x1, y1, x2, y2),
                                    "label": label,
                                    "track_id": track_id,
                                    "confidence": confidence
                                })
                                # Nếu nhận diện thành công, có thông tin đầy đủ và độ tin cậy đủ lớn
                                if need_recognition and label != "Unknown" and label in label_map and confidence >= MIN_CONFIDENCE:
                                    detected_persons.append({
                                        "label": label,
                                        "fullname": label_map[label]["fullname"],
                                        "classname": label_map[label].get("classname", ""),
                                        "desc": label_map[label].get("desc", ""),
                                        "confidence": f"{confidence:.1f}%",
                                        "time": datetime.now().strftime("%H:%M:%S")
                                    })
                                    # Ghi lịch sử nhận diện vào DB (webcam) - CHỈ GHI KHI CÓ TRACK_ID HỢP LỆ (>= 0)
                                    if track_id >= 0:
                                        try:
                                            pass  # Đã xóa ghi lịch sử nhận diện vào DB
                                        except Exception as e:
                                            pass  # Đã xóa ghi lịch sử nhận diện vào DB
                                    else:
                                        pass  # Đã xóa ghi lịch sử nhận diện vào DB
                                # Nếu nhận diện thành công nhưng chưa có thông tin chi tiết
                                elif need_recognition and label != "Unknown" and confidence >= MIN_CONFIDENCE:
                                    detected_persons.append({
                                        "label": label,
                                        "fullname": label,
                                        "classname": "",
                                        "desc": "Chưa có thông tin",
                                        "confidence": f"{confidence:.1f}%",
                                        "time": datetime.now().strftime("%H:%M:%S")
                                    })
                                    # Ghi lịch sử nhận diện vào DB (webcam) - CHỈ GHI KHI CÓ TRACK_ID HỢP LỆ (>= 0)
                                    if track_id >= 0:
                                        try:
                                            pass  # Đã xóa ghi lịch sử nhận diện vào DB
                                        except Exception as e:
                                            pass  # Đã xóa ghi lịch sử nhận diện vào DB
                                    else:
                                        pass  # Đã xóa ghi lịch sử nhận diện vào DB
                    else:
                        # Nếu không có YOLO, dùng face_recognition để nhận diện khuôn mặt
                        boxes = face_recognition.face_locations(small_frame, model='hog')  # Tìm vị trí khuôn mặt
                        scale_x = w / FRAME_WIDTH
                        scale_y = h / FRAME_HEIGHT
                        for (top, right, bottom, left) in boxes:
                            x1 = int(left * scale_x)
                            x2 = int(right * scale_x)
                            y1 = int(top * scale_y)
                            y2 = int(bottom * scale_y)
                            face_box = (top, right, bottom, left)
                            try:
                                enc = face_recognition.face_encodings(small_frame, [face_box], num_jitters=0)  # Trích xuất vector đặc trưng
                                if enc and len(enc) > 0:
                                    enc = enc[0]
                                    dists = face_recognition.face_distance(known_encs, enc)  # Tính khoảng cách với các khuôn mặt đã biết
                                    idx = int(np.argmin(dists))  # Tìm vị trí có khoảng cách nhỏ nhất
                                    min_dist = float(dists[idx])  # Lấy giá trị khoảng cách nhỏ nhất
                                    if min_dist <= THRESH:
                                        label = known_names[idx]  # Nếu đủ gần thì gán tên nhận diện
                                        confidence = (1 - min_dist) * 100  # Tính độ tin cậy
                                    else:
                                        label = "Unknown"  # Nếu không đủ gần thì gán Unknown
                                        confidence = (1 - min_dist) * 100
                                else:
                                    label = "Unknown"  # Nếu không trích xuất được khuôn mặt
                                    confidence = 0
                            except:
                                label = "Unknown"  # Nếu có lỗi thì gán Unknown
                                confidence = 0
                            # Lưu thông tin bounding box và kết quả nhận diện vào danh sách
                            detected_boxes.append({
                                "box": (x1, y1, x2, y2),
                                "label": label,
                                "track_id": -1,
                                "confidence": confidence
                            })
                            # Nếu nhận diện thành công, có thông tin đầy đủ và độ tin cậy đủ lớn
                            if label != "Unknown" and label in label_map and confidence >= MIN_CONFIDENCE:
                                detected_persons.append({
                                    "label": label,
                                    "fullname": label_map[label]["fullname"],
                                    "classname": label_map[label].get("classname", ""),
                                    "desc": label_map[label].get("desc", ""),
                                    "confidence": f"{confidence:.1f}%",
                                    "time": datetime.now().strftime("%H:%M:%S")
                                })
                    # Xóa các track đã nhận diện nhưng không còn xuất hiện
                    tracks_to_remove = []
                    for tid in recognized_tracks:
                        if tid not in current_track_ids and (current_time - recognized_tracks[tid]["last_seen"]) > 5:
                            tracks_to_remove.append(tid)
                    for tid in tracks_to_remove:
                        del recognized_tracks[tid]  # Xóa khỏi cache
                        print(f"[REMOVED] Track {tid} removed from recognition cache")
                    # Xóa các track trong track_cache đã quá hạn
                    old_ids = [tid for tid, info in track_cache.items() if current_time - info["last_update"] > 5]
                    for tid in old_ids:
                        del track_cache[tid]
                    # Cập nhật kết quả nhận diện và bounding box cho các luồng khác sử dụng
                    try:
                        boxes_lock.acquire()
                        global prev_boxes, last_box_update
                        prev_boxes = latest_boxes[:] if latest_boxes else []  # Lưu lại bounding box trước đó
                        latest_boxes = detected_boxes  # Cập nhật bounding box mới nhất
                        last_box_update = time.time()  # Cập nhật thời gian
                        if detected_persons:
                            current_person_info = detected_persons  # Cập nhật thông tin người nhận diện
                    finally:
                        boxes_lock.release()
                except Exception as e:
                    print(f"[ERROR] Recognition: {e}")  # In lỗi nếu có
        def stop(self):
            self.running = False  # Dừng luồng nhận diện

    # Khởi động luồng nhận diện nếu chưa chạy
    if recognition_thread is None or not recognition_thread.is_alive():
        recognition_thread = RecognitionThread()
        recognition_thread.start()

    WEBCAM_SIZE = FRAME_SIZE  # Kích thước khung hình webcam
    JPEG_QUALITY = 90  # Chất lượng nén JPEG. Giá trị từ 0 đến 100 (100 là tốt nhất)
    frame_count = 0  # Đếm số frame đã xử lý
    boxes_to_draw = []  # Danh sách bounding box để vẽ lên khung hình
    last_boxes_update = 0  # Thời điểm cập nhật bounding box cuối cùng
    while running and cap is not None and cap.isOpened():
        success, frame = cap.read()  # Đọc frame từ webcam
        if not success:
            print("[ERROR] Không đọc được frame")  # Báo lỗi nếu không đọc được frame
            break
        frame_count += 1
        frame = cv2.resize(frame, WEBCAM_SIZE)  # Resize frame về kích thước chuẩn
        # Lật ảnh ngang nếu MIRROR bật (giúp giống gương)
        if MIRROR:
            try:
                frame = cv2.flip(frame, 1)
            except Exception:
                pass
        # Mỗi 4 frame thì gửi frame RGB cho luồng nhận diện
        if frame_count % 4 == 0:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            recognition_thread.add_frame(frame_rgb)
        current_time = time.time()
        time_since_update = current_time - last_box_update  # Thời gian từ lần cập nhật bounding box gần nhất
        alpha = min(time_since_update / 0.3, 1.0)  # Tính hệ số chuyển động mượt cho bounding box
        # Cập nhật danh sách bounding box để vẽ nếu đã đủ thời gian
        if current_time - last_boxes_update > 0.05:
            try:
                if boxes_lock.acquire(blocking=False):
                    try:
                        if alpha < 1.0 and prev_boxes:
                            boxes_to_draw = interpolate_boxes(prev_boxes, latest_boxes, alpha)  # Chuyển động mượt
                        else:
                            boxes_to_draw = latest_boxes[:]  # Dùng bounding box mới nhất
                        last_boxes_update = current_time
                    finally:
                        boxes_lock.release()
            except:
                pass
        # Vẽ bounding box và nhãn lên khung hình
        for det in boxes_to_draw:
            x1, y1, x2, y2 = det["box"]
            label = det["label"]
            color = (0, 255, 0) if label != "Unknown" else (0, 165, 255)  # Màu xanh nếu nhận diện, cam nếu Unknown
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)  # Vẽ khung
            text = f"{label}"
            (text_w, text_h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
            cv2.rectangle(frame, (x1, y1-text_h-8), (x1+text_w+4, y1), color, -1)  # Vẽ nền cho text
            cv2.putText(frame, text, (x1+2, y1-5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,0), 2)  # Vẽ text nhãn
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY]  # Tham số nén JPEG
        ret, buffer = cv2.imencode('.jpg', frame, encode_param)  # Encode frame thành JPEG
        if not ret:
            continue  # Nếu encode lỗi thì bỏ qua
        # Trả về luồng ảnh JPEG cho client (streaming)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
    if cap is not None and cap.isOpened():
        cap.release()  # Giải phóng tài nguyên webcam
        print("[INFO] Webcam released")  # In log đã giải phóng

# Hàm chuyển động mượt cho bounding box giữa 2 frame
def interpolate_boxes(prev_boxes, curr_boxes, alpha):
    if not prev_boxes or not curr_boxes:
        return curr_boxes  # Nếu không có dữ liệu thì trả về box hiện tại
    prev_map = {}
    for box in prev_boxes:
        key = box["track_id"] if box["track_id"] >= 0 else box["label"]  # Dùng track_id hoặc label làm key
        prev_map[key] = box
    interpolated = []
    for curr in curr_boxes:
        key = curr["track_id"] if curr["track_id"] >= 0 else curr["label"]
        if key in prev_map:
            prev = prev_map[key]
            px1, py1, px2, py2 = prev["box"]
            cx1, cy1, cx2, cy2 = curr["box"]
            # Tính toán vị trí box mới dựa trên alpha (giúp chuyển động mượt)
            new_box = (
                int(px1 + (cx1 - px1) * alpha),
                int(py1 + (cy1 - py1) * alpha),
                int(px2 + (cx2 - px2) * alpha),
                int(py2 + (cy2 - py2) * alpha)
            )
            interpolated.append({
                "box": new_box,
                "label": curr["label"],
                "track_id": curr["track_id"],
                "confidence": curr["confidence"]
            })
        else:
            interpolated.append(curr)  # Nếu không có box trước đó thì giữ nguyên
    return interpolated

# Route hiển thị giao diện nhận diện qua webcam
@webcam_bp.route("/")  # Đường dẫn gốc của blueprint này
def index():
    # Nhận session_id từ query để liên kết điểm danh
    try:
        from flask import request as _req
        session_id = _req.args.get("session_id")
    except Exception:
        session_id = None
    return render_template("webcam.html", session_id=session_id)  # Trả về giao diện nhận diện webcam

# Route khởi động webcam
@webcam_bp.route("/start")  # Đường dẫn khởi động webcam
def start():
    global cap, running
    global MIRROR
    # Mirror is forced server-side (MIRROR=True)

    if cap is None or not cap.isOpened():
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)  # Mở webcam với DirectShow (Windows)
        # Tối ưu thuộc tính webcam cho Windows
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)  # Đặt chiều rộng khung hình
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)  # Đặt chiều cao khung hình
        cap.set(cv2.CAP_PROP_FPS, 30)  # Đặt số khung hình/giây
        # In ra kích thước thực tế của camera sau khi set
        print(f"[INFO] Actual camera size: {cap.get(cv2.CAP_PROP_FRAME_WIDTH)}x{cap.get (cv2.CAP_PROP_FRAME_HEIGHT)}, FPS: {cap.get(cv2.CAP_PROP_FPS)}")
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Đặt kích thước buffer
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M','J','P','G'))  # Đặt codec MJPG
        if not cap.isOpened():
            print("[ERROR] Không mở được webcam")  # Báo lỗi nếu không mở được webcam
            return "Camera error", 500
    running = True  # Đánh dấu trạng thái webcam đang chạy
    print("[INFO] Webcam started")  # In log đã khởi động webcam
    return "Started"  # Trả về thông báo đã khởi động

# Route trả về luồng video nhận diện
@webcam_bp.route("/video_feed")  # Đường dẫn trả về video nhận diện
def video_feed():
    if not running:
        return "Camera chưa bật", 400  # Nếu webcam chưa bật thì báo lỗi
    return Response(gen_frames(),  # Trả về luồng video dạng MJPEG
                    mimetype="multipart/x-mixed-replace; boundary=frame")

# API lấy thông tin người được nhận diện từ frame hiện tại
@webcam_bp.route("/get_person_info")  # Đường dẫn lấy thông tin người nhận diện
def get_person_info():
    global current_person_info
    return jsonify(current_person_info if current_person_info else [])  # Trả về thông tin người nhận diện (dạng JSON)

# Route reload lại dữ liệu embeddings và labels
# SỬA ROUTE /reload THÀNH POST VÀ TRẢ VỀ ĐẦY ĐỦ THÔNG TIN
@webcam_bp.route("/reload", methods=["POST"])
def reload():
    reload_data()
    return jsonify({"status": "success", "message": "Reloaded embeddings and labels.", "encodings": len(known_encs), "labels": len(label_map)})  # Trả về trạng thái và số lượng dữ liệu

# Route dừng webcam và giải phóng tài nguyên
@webcam_bp.route("/stop")
def stop():
    global running, cap, current_person_info, track_cache, latest_boxes, prev_boxes, last_box_update, recognition_thread, recognized_tracks
    running = False  # Đánh dấu trạng thái webcam đã dừng
    current_person_info = None  # Xóa thông tin người nhận diện
    track_cache.clear()  # Xóa cache track
    recognized_tracks.clear()  # Xóa cache nhận diện
    with boxes_lock:
        latest_boxes = []  # Xóa bounding box mới nhất
        prev_boxes = []    # Xóa bounding box trước đó
        last_box_update = 0  # Reset thời gian cập nhật
    if recognition_thread is not None:
        try:
            recognition_thread.stop()  # Dừng luồng nhận diện
        except Exception:
            pass
    if cap is not None and cap.isOpened():
        cap.release()  # Giải phóng webcam
        cap = None
        print("[INFO] Webcam stopped")  # In log đã dừng webcam
    return "Stopped"  # Trả về thông báo đã dừng