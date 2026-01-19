from flask import Blueprint, render_template, request, redirect, url_for, flash
from connect_postgres import get_connection
from auth import role_required

settings_bp = Blueprint("settings", __name__)

DEFAULTS = {
    "recognition_min_confidence": "65",
    "phone_attendance_enabled": "0",
    "late_grace_minutes": "10",
    "public_base_url": ""
}

def get_all_settings():
    conn = get_connection(); cur = conn.cursor()
    data = DEFAULTS.copy()
    try:
        cur.execute("SELECT name, value FROM settings")
        rows = cur.fetchall()
        for name, value in rows:
            data[str(name)] = str(value)
    except Exception:
        # Bảng chưa có? Tạo nhanh để tránh lỗi, rồi trả về mặc định
        try:
            cur.execute("CREATE TABLE IF NOT EXISTS settings (name VARCHAR(50) PRIMARY KEY, value TEXT)")
            conn.commit()
        except Exception:
            conn.rollback()
    finally:
        cur.close(); conn.close()
    return data

@settings_bp.route("/", methods=["GET", "POST"]) 
@role_required("admin")
def index():
    if request.method == "POST":
        recog = request.form.get("recognition_min_confidence") or DEFAULTS["recognition_min_confidence"]
        phone = "1" if request.form.get("phone_attendance_enabled") == "on" else "0"
        late = request.form.get("late_grace_minutes") or DEFAULTS["late_grace_minutes"]
        base = (request.form.get("public_base_url") or DEFAULTS["public_base_url"]).strip()
        conn = get_connection(); cur = conn.cursor()
        try:
            for name, value in [("recognition_min_confidence", recog), ("phone_attendance_enabled", phone), ("late_grace_minutes", late), ("public_base_url", base)]:
                cur.execute("INSERT INTO settings (name, value) VALUES (%s, %s) ON CONFLICT (name) DO UPDATE SET value=EXCLUDED.value", (name, value))
            conn.commit(); flash("Đã lưu cấu hình", "success")
        except Exception:
            conn.rollback(); flash("Lỗi lưu cấu hình", "error")
        finally:
            cur.close(); conn.close()
        return redirect(url_for("settings.index"))
    data = get_all_settings()
    try:
        return render_template("settings.html", data=data)
    except Exception as e:
        # Hiển thị lỗi chi tiết để dễ chẩn đoán thay vì trang 500 chung chung
        return f"Settings template error: {e}", 500
