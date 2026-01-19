# Import các thư viện cần thiết
from flask import Blueprint, render_template, Response, request, jsonify, redirect, url_for, current_app  # Flask web framework
import cv2, os, subprocess, json  # Xử lý ảnh, hệ thống, chạy lệnh ngoài, json
import numpy as np  # Xử lý mảng số
from ultralytics import YOLO  # Thêm YOLO để phát hiện khuôn mặt
from auth import role_required
from connect_postgres import get_connection



# Tạo Blueprint cho module thêm người dùng
add_user_bp = Blueprint("add_user", __name__)  # Khởi tạo blueprint cho chức năng thêm user



# Biến toàn cục để quản lý trạng thái chụp ảnh
cap: cv2.VideoCapture | None = None  # Đối tượng webcam (None nếu chưa mở)
running: bool = False                # Trạng thái đang chạy/quay webcam
save_dir: str = ""                   # Đường dẫn thư mục lưu ảnh
saved: int = 0                       # Số lượng ảnh đã lưu
frame_count: int = 0                 # Đếm số frame đã đọc từ webcam
MAX_IMAGES = 20      # Số ảnh tối đa lưu cho mỗi người
FRAME_STEP = 5       # Mỗi 5 frame mới lưu 1 ảnh
FORCE_MIRROR = True   # Nếu True, lật ngang frame trước khi lưu/stream (giúp ảnh thuận chiều)
FACE_CONF_THRESHOLD = 0.7  # Ngưỡng confidence YOLO để chấp nhận khuôn mặt
FRAME_WIDTH = 640      # Độ rộng khung hình mong muốn khi mở webcam (4:3)
FRAME_HEIGHT = 480     # Độ cao khung hình mong muốn khi mở webcam (4:3)
FACE_MARGIN_RATIO = 0.2  # Phần trăm lề thêm xung quanh khuôn mặt khi crop


_YOLO_MODEL: YOLO | None = None  # Cache model YOLO để tránh tải lại nhiều lần
_YOLO_MODEL_ERROR: Exception | None = None

_last_capture_key: str = ""
_last_capture_fullname: str = ""
_last_capture_classname: str = ""


def _get_face_model() -> YOLO | None:
    global _YOLO_MODEL, _YOLO_MODEL_ERROR
    if _YOLO_MODEL is not None or _YOLO_MODEL_ERROR is not None:
        return _YOLO_MODEL
    try:
        _YOLO_MODEL = YOLO("yolov11n-face.pt")
    except Exception as exc:  # Không cho phép crash nếu thiếu model
        _YOLO_MODEL_ERROR = exc
        print(f"[ERROR] Không tải được model YOLO: {exc}")
    return _YOLO_MODEL


def _crop_face(frame: np.ndarray, box: tuple[int, int, int, int], margin_ratio: float = FACE_MARGIN_RATIO) -> np.ndarray | None:
    x1, y1, x2, y2 = box
    h, w = frame.shape[:2]
    margin_x = int((x2 - x1) * margin_ratio)
    margin_y = int((y2 - y1) * margin_ratio)
    x1 = max(0, x1 - margin_x)
    y1 = max(0, y1 - margin_y)
    x2 = min(w, x2 + margin_x)
    y2 = min(h, y2 + margin_y)
    if x2 <= x1 or y2 <= y1:
        return None
    return frame[y1:y2, x1:x2]




def _ensure_labels_entry(key: str, fullname: str, classname: str) -> None:
    """Ghi trực tiếp thông tin form vào labels.json để tránh suy diễn từ tên thư mục."""
    if not key or not fullname:
        return
    labels_path = os.path.join(current_app.root_path, "labels.json")
    try:
        if os.path.exists(labels_path):
            with open(labels_path, "r", encoding="utf-8") as f:
                labels = json.load(f)
        else:
            labels = {}
        entry = {
            "fullname": fullname,
            "classname": classname,
            "desc": f"Sinh viên {classname}" if classname else "Người dùng hệ thống"
        }
        labels[key] = entry
        with open(labels_path, "w", encoding="utf-8") as f:
            json.dump(labels, f, ensure_ascii=False, indent=2)
        print(f"[INFO] Đã cập nhật labels.json cho {key}")
    except Exception as exc:
        print(f"[ERROR] Không thể ghi labels.json cho {key}: {exc}")


def _upsert_student_record(fullname: str, classname: str, face_label: str) -> dict:
    """Thêm hoặc cập nhật bản ghi sinh viên tương ứng với lần chụp.
    - Tìm `classes.id` theo `code = classname`; nếu chưa có, tự tạo lớp với `name = classname`.
    - Tìm `students` theo `face_label` hoặc theo `(fullname, class_id)`; nếu chưa có, thêm mới.
    - Cập nhật `face_label` để liên kết với thư mục dataset.
    Trả về dict thông tin kết quả: {status, student_id, class_id}.
    """
    result = {"status": "ok", "student_id": None, "class_id": None}
    conn = None
    cur = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        # Tìm hoặc tạo lớp
        class_id = None
        if classname:
            cur.execute("SELECT id FROM classes WHERE code=%s", (classname,))
            row = cur.fetchone()
            if row:
                class_id = row[0]
            else:
                try:
                    cur.execute("INSERT INTO classes (code, name) VALUES (%s, %s) RETURNING id", (classname, classname))
                    _row_new_class = cur.fetchone()
                    class_id = _row_new_class[0] if _row_new_class is not None else None
                except Exception:
                    conn.rollback()
                    # Thử lại chọn sau khi rollback (tránh lỗi cạnh tranh)
                    cur.execute("SELECT id FROM classes WHERE code=%s", (classname,))
                    r2 = cur.fetchone()
                    class_id = r2[0] if r2 is not None else None

        # Tìm sinh viên theo face_label trước
        student_id = None
        if face_label:
            cur.execute("SELECT id FROM students WHERE face_label=%s", (face_label,))
            s = cur.fetchone()
            if s:
                student_id = s[0]

        # Nếu chưa thấy theo face_label, thử theo fullname + class_id
        if student_id is None:
            if class_id is not None:
                cur.execute("SELECT id FROM students WHERE fullname=%s AND class_id=%s", (fullname, class_id))
            else:
                cur.execute("SELECT id FROM students WHERE fullname=%s AND class_id IS NULL", (fullname,))
            s2 = cur.fetchone()
            if s2:
                student_id = s2[0]

        # Thêm mới nếu chưa có
        if student_id is None:
            cur.execute(
                "INSERT INTO students (student_code, fullname, class_id, face_label) VALUES (%s, %s, %s, %s) RETURNING id",
                (None, fullname, class_id, face_label)
            )
            _row_new_student = cur.fetchone()
            student_id = _row_new_student[0] if _row_new_student is not None else None
        else:
            # Cập nhật face_label nếu chưa có hoặc khác
            cur.execute("UPDATE students SET face_label=%s WHERE id=%s", (face_label, student_id))

        conn.commit()
        result["student_id"] = student_id
        result["class_id"] = class_id
        return result
    except Exception as exc:
        if conn:
            conn.rollback()
        print(f"[ERROR] Không thể upsert sinh viên: {exc}")
        return {"status": "error", "error": str(exc)}
    finally:
        try:
            if cur: cur.close()
            if conn: conn.close()
        except Exception:
            pass


# --------- API xóa ảnh vừa chụp khi bấm Thử lại ----------
@add_user_bp.route("/capture/retry", methods=["POST"])
@role_required("admin", "lecturer")
def retry_capture():
    global save_dir, saved, frame_count
    # Kiểm tra thư mục lưu ảnh có tồn tại không
    if save_dir and os.path.exists(save_dir):
        count = 0
        # Duyệt qua các file ảnh trong thư mục
        for fname in os.listdir(save_dir):
            if fname.lower().endswith((".jpg", ".jpeg", ".png", ".bmp")):
                try:
                    os.remove(os.path.join(save_dir, fname))  # Xóa file ảnh
                    count += 1
                except Exception as e:
                    print(f"[WARN] Không xóa được ảnh: {fname}", e)
        saved = 0  # Reset số ảnh đã lưu
        frame_count = 0  # Reset số frame đã đọc
        # Trả về kết quả xóa thành công
        return jsonify({"status": "ok", "deleted": count, "message": f"Đã xóa {count} ảnh, bạn có thể chụp lại."})
    else:
        # Trả về lỗi nếu không tìm thấy thư mục
        return jsonify({"status": "error", "message": "Không tìm thấy thư mục lưu ảnh."}), 400


# --------- API trả về trạng thái lưu ảnh ----------
@add_user_bp.route("/capture/status")
@role_required("admin", "lecturer")
def capture_status():
    global saved, MAX_IMAGES, running
    status = "running"  # Mặc định trạng thái đang chạy
    if saved >= MAX_IMAGES:
        status = "done"  # Nếu đã đủ số ảnh thì trạng thái hoàn thành
    # Trả về thông tin trạng thái lưu ảnh dưới dạng JSON
    return jsonify({
        "saved": saved,           # Số ảnh đã lưu
        "max_images": MAX_IMAGES, # Số ảnh tối đa cần lưu
        "status": status          # Trạng thái hiện tại
    })


# --------- Trang nhập họ tên + lớp ----------
# Hiển thị trang nhập thông tin người dùng
@add_user_bp.route("/capture", methods=["GET"])
@role_required("admin", "lecturer")
def capture_page():
    # Cho phép điền sẵn họ tên/lớp qua query (dùng từ trang sinh viên)
    from flask import request
    fullname = (request.args.get("fullname") or "").strip()
    classname = (request.args.get("classname") or "").strip()
    return render_template("capture_user.html", fullname=fullname, classname=classname)


# --------- Bắt đầu chụp ----------
# Nhận thông tin người dùng, khởi tạo webcam và bắt đầu quá trình chụp
@add_user_bp.route("/capture/start", methods=["POST"])
@role_required("admin", "lecturer")
def start_capture():
    global cap, running, save_dir, saved, frame_count
    global _last_capture_key, _last_capture_fullname, _last_capture_classname
    fullname = request.form.get("fullname", "").strip()   # Lấy họ tên từ form
    classname = request.form.get("classname", "").strip() # Lấy lớp từ form
    if not fullname or not classname:
        return "Thiếu họ tên hoặc lớp", 400  # Nếu thiếu thông tin trả về lỗi
    return _begin_capture(fullname, classname)


def _begin_capture(fullname: str, classname: str):
    """Khởi tạo trạng thái chụp ảnh với họ tên và mã lớp."""
    global cap, running, save_dir, saved, frame_count
    global _last_capture_key, _last_capture_fullname, _last_capture_classname
    # Tạo tên thư mục lưu ảnh theo họ tên và lớp, chuyển về dạng key
    key = f"{fullname}_{classname}".lower().replace(" ", "_")
    base_dir = os.path.join(current_app.root_path, "dataset")
    save_dir = os.path.join(base_dir, key)
    _last_capture_key = key
    _last_capture_fullname = fullname
    _last_capture_classname = classname
    # Nếu thư mục đã tồn tại, xóa toàn bộ ảnh cũ trước khi chụp lại
    if os.path.exists(save_dir):
        for fname in os.listdir(save_dir):
            if fname.lower().endswith((".jpg", ".jpeg", ".png", ".bmp")):
                try:
                    os.remove(os.path.join(save_dir, fname))  # Xóa ảnh cũ
                except Exception as e:
                    print(f"[WARN] Không xóa được ảnh cũ: {fname}", e)
    os.makedirs(save_dir, exist_ok=True)  # Tạo thư mục nếu chưa có
    print("[INFO] Ảnh sẽ lưu vào:", save_dir)
    _ensure_labels_entry(key, fullname, classname)

    cap = cv2.VideoCapture(0)  # Mở webcam
    if cap is None or not cap.isOpened():
        if cap is not None:
            cap.release()  # Giải phóng webcam nếu có
        cap = None
        return "Không mở được webcam. Vui lòng kiểm tra lại thiết bị hoặc quyền truy cập.", 500

    # Thiết lập độ phân giải khung hình nếu phần cứng hỗ trợ, giúp ảnh sắc nét hơn
    if FRAME_WIDTH > 0:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    if FRAME_HEIGHT > 0:
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    # Cố gắng bật autofocus/autoexposure nếu được hỗ trợ
    cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)
    cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.75)
    real_w = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    real_h = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    print(f"[INFO] Webcam resolution: {real_w}x{real_h}")

    running = True      # Đánh dấu trạng thái đang chạy
    saved = 0           # Reset số ảnh đã lưu
    frame_count = 0     # Reset số frame
    return jsonify({"status": "started"})


@add_user_bp.route("/capture/start_by_student", methods=["POST"])
@role_required("admin", "lecturer")
def start_capture_by_student():
    """Bắt đầu chụp dựa trên student_id: tự lấy họ tên và mã lớp từ DB."""
    sid_raw = request.form.get("student_id") or ""
    try:
        sid = int(sid_raw)
    except Exception:
        return "Thiếu hoặc sai student_id", 400
    conn = get_connection(); cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT s.fullname, COALESCE(c.code,'') AS class_code
            FROM students s LEFT JOIN classes c ON s.class_id=c.id
            WHERE s.id=%s
            """,
            (sid,)
        )
        row = cur.fetchone()
    finally:
        cur.close(); conn.close()
    if not row:
        return "Không tìm thấy sinh viên", 404
    fullname, class_code = row[0], row[1]
    if not fullname or not class_code:
        return "Sinh viên chưa có thông tin lớp. Vui lòng cập nhật lớp trước.", 400
    return _begin_capture(fullname.strip(), class_code.strip())


# --------- Stream video & lưu ảnh ----------
# Hàm sinh luồng ảnh từ webcam, đồng thời lưu ảnh vào thư mục
def gen_frames():
    global cap, running, save_dir, saved, frame_count
    model = _get_face_model()
    if model is None:
        print("[ERROR] Không có model YOLO, dừng stream.")
        running = False
        if cap is not None and cap.isOpened():
            cap.release()
        return
    while running and cap is not None and cap.isOpened():
        ret, frame = cap.read()  # Đọc frame từ webcam
        if not ret:
            break  # Nếu không đọc được thì thoát

        # Lật ảnh sớm để model và dữ liệu lưu nhất quán
        if FORCE_MIRROR:
            try:
                frame = cv2.flip(frame, 1)
            except Exception:
                pass

        frame_count += 1  # Tăng số frame đã đọc
        # Mỗi FRAME_STEP frame thì lưu 1 ảnh, tối đa MAX_IMAGES ảnh
        if frame_count % FRAME_STEP == 0 and saved < MAX_IMAGES:
            if save_dir:
                # Dùng YOLO phát hiện khuôn mặt
                results = model(frame, verbose=False)
                faces = []
                for r in results:
                    for box in r.boxes:
                        conf = float(box.conf[0])  # Lấy độ tự tin của box
                        if conf >= FACE_CONF_THRESHOLD:
                            x1, y1, x2, y2 = map(int, box.xyxy[0])  # Tọa độ box
                            faces.append((x1, y1, x2, y2))
                if len(faces) == 1:
                    img_index = saved
                    fname = os.path.join(save_dir, f"{os.path.basename(save_dir)}_{img_index}.jpg")
                    face_region = _crop_face(frame, faces[0])
                    if face_region is None:
                        print("[SKIP] Crop khuôn mặt không hợp lệ.")
                        continue
                    ok = cv2.imwrite(fname, face_region)  # Lưu ảnh gốc ra file dạng BGR
                    print("[SAVE]", fname, "->", ok, frame.shape, frame.dtype)
                    if ok:
                        saved += 1  # Tăng số ảnh đã lưu
                else:
                    print(f"[SKIP] Không phát hiện đúng 1 khuôn mặt ở frame này.")
            else:
                print("[WARN] save_dir rỗng, bỏ qua lưu")

        if saved >= MAX_IMAGES:
            running = False  # Đủ số lượng thì dừng

        # Đảm bảo frame cho streaming cũng đúng định dạng
        if frame.dtype != np.uint8:
            frame = np.clip(frame, 0, 255).astype(np.uint8)

        ret2, buffer = cv2.imencode('.jpg', frame)  # Mã hóa frame thành JPEG để stream

        if not ret2:
            break  # Nếu mã hóa lỗi thì thoát
        # Trả về frame dạng stream cho trình duyệt
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

    # Sau khi kết thúc thì giải phóng webcam
    if cap is not None and cap.isOpened():
        cap.release()
        print(f"[INFO] Hoàn tất, đã lưu {saved} ảnh")

# Route trả về luồng video cho trình duyệt

# Route trả về luồng video cho trình duyệt
@add_user_bp.route("/capture/video")
@role_required("admin", "lecturer")
def video_feed():
    return Response(gen_frames(),
                    mimetype="multipart/x-mixed-replace; boundary=frame")


# --------- Dừng chụp + cập nhật embeddings ----------
# Khi người dùng dừng chụp, cập nhật dữ liệu nhận diện khuôn mặt
@add_user_bp.route("/capture/stop")
@role_required("admin", "lecturer")
def stop_capture():
    global running, cap, saved
    global _last_capture_key, _last_capture_fullname, _last_capture_classname
    running = False  # Dừng quá trình chụp
    if cap is not None and cap.isOpened():
        cap.release()  # Giải phóng webcam
        cap = None

    # 🔥 Cập nhật labels.json (danh sách người dùng)
    if _last_capture_key:
        _ensure_labels_entry(_last_capture_key, _last_capture_fullname, _last_capture_classname)
    update_labels_json()  # Tự động cập nhật thông tin người dùng

    # Ghi/ cập nhật vào cơ sở dữ liệu bảng students
    db_res = {}
    try:
        if _last_capture_fullname:
            db_res = _upsert_student_record(_last_capture_fullname, _last_capture_classname, _last_capture_key)
    except Exception as e:
        print("[ERROR] Lỗi cập nhật DB cho sinh viên:", e)

    # Chỉ cập nhật embeddings cho người mới vừa thêm
    # Lấy lại fullname và classname từ tên thư mục vừa lưu
    # (save_dir = .../dataset/<key>)
    try:
        key = os.path.basename(save_dir)  # Lấy tên thư mục vừa lưu
        update_path = os.path.join(current_app.root_path, "update_single_embedding.py")
        # Chạy script cập nhật embedding cho người mới
        result = subprocess.run(
            ["python", update_path, key],
            capture_output=True,
            text=True,
            check=True,
            encoding="utf-8"
        )
        print("[INFO] update_single_embedding.py output:\n", result.stdout)
        if result.stderr:
            print("[INFO] update_single_embedding.py error:\n", result.stderr)
            return jsonify({
                "status": "error",
                "error": result.stderr
            }), 500
    except subprocess.CalledProcessError as e:
        print("[ERROR] update_single_embedding.py lỗi:", e.stderr)
        return jsonify({
            "status": "error",
            "error": e.stderr
        }), 500
    # Trả về kết quả đã dừng và cập nhật xong
    return jsonify({
        "status": "stopped",
        "saved": saved,
        "student": db_res,
        "message": "Đã lưu ảnh, cập nhật DB và embeddings cho người mới."
    })


# --------- HÀM MỚI: Cập nhật labels.json ----------
# Tự động tạo/cập nhật file labels.json từ thư mục dataset
def update_labels_json():
    """Tự động tạo/cập nhật file labels.json từ thư mục dataset"""
    try:
        # Đọc labels.json hiện tại (nếu có)
        labels_file = "labels.json"
        if os.path.exists(labels_file):
            with open(labels_file, "r", encoding="utf-8") as f:
                labels = json.load(f)  # Đọc dữ liệu hiện tại
        else:
            labels = {}  # Nếu chưa có thì khởi tạo rỗng
        
        # Quét thư mục dataset để lấy danh sách người dùng
        dataset_dir = "dataset"
        if os.path.exists(dataset_dir):
            for person_dir in os.listdir(dataset_dir):
                person_path = os.path.join(dataset_dir, person_dir)
                if os.path.isdir(person_path):
                    # Nếu chưa có trong labels.json thì thêm vào
                    if person_dir not in labels:
                        # Tách tên và lớp từ tên thư mục (vd: nguyen_van_a_lop12a1)
                        parts = person_dir.split("_")
                        if len(parts) >= 2:
                            # Tìm phần "lop" để tách tên và lớp
                            lop_index = -1
                            for i, part in enumerate(parts):
                                if part.startswith("lop"):
                                    lop_index = i
                                    break
                            if lop_index > 0:
                                # Tách tên (trước "lop") và lớp (từ "lop" trở đi)
                                name_parts = parts[:lop_index]
                                class_parts = parts[lop_index:]
                                fullname = " ".join(name_parts).title()  # Ghép lại tên
                                classname = " ".join(class_parts).upper() # Ghép lại lớp
                                labels[person_dir] = {
                                    "fullname": fullname,
                                    "classname": classname,
                                    "desc": f"Sinh viên {classname}"
                                }
                            else:
                                # Nếu không tìm được pattern "lop", lấy phần cuối làm lớp
                                fullname = " ".join(parts[:-1]).title()
                                classname = parts[-1].upper()
                                labels[person_dir] = {
                                    "fullname": fullname,
                                    "classname": classname,
                                    "desc": "Người dùng hệ thống"
                                }
                        else:
                            # Nếu tên thư mục không đủ phần, gán mặc định
                            labels[person_dir] = {
                                "fullname": person_dir.replace("_", " ").title(),
                                "classname": "",
                                "desc": "Người dùng hệ thống"
                            }
        
        # Ghi lại file labels.json
        with open(labels_file, "w", encoding="utf-8") as f:
            json.dump(labels, f, ensure_ascii=False, indent=2)  # Lưu lại dữ liệu
        
        print(f"[INFO] Đã cập nhật labels.json với {len(labels)} người")
        
    except Exception as e:
        print(f"[ERROR] Không thể cập nhật labels.json: {e}")

# --------- Route gốc ----------
# Khi truy cập vào /add_user thì chuyển hướng sang trang nhập thông tin
@add_user_bp.route("/", methods=["GET"])
def index():
    return redirect(url_for("add_user.capture_page"))