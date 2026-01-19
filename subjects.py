from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from connect_postgres import get_connection
from auth import role_required, login_required

subjects_bp = Blueprint("subjects", __name__)

@subjects_bp.route("/")
@login_required
def index():
    conn = get_connection(); cur = conn.cursor()
    try:
        role = session.get("role", "lecturer")
        user_id = session.get("user_id")
        if role == "lecturer" and user_id:
            # Chỉ hiển thị các môn mà admin đã phân cho giảng viên (ICS)
            cur.execute(
                """
                SELECT DISTINCT s.id, s.code, s.name
                FROM subjects s
                JOIN instructors_class_subjects ics ON ics.subject_id=s.id
                WHERE ics.user_id=%s
                ORDER BY s.code
                """,
                (user_id,)
            )
        else:
            cur.execute("SELECT id, code, name FROM subjects ORDER BY code")
        rows = cur.fetchall()
    finally:
        cur.close(); conn.close()
    return render_template("subjects_list.html", rows=rows)

@subjects_bp.route("/new", methods=["GET", "POST"])
@role_required("admin")
def create():
    if request.method == "POST":
        code = request.form.get("code"); name = request.form.get("name")
        conn = get_connection(); cur = conn.cursor()
        try:
            cur.execute("INSERT INTO subjects (code, name) VALUES (%s, %s)", (code, name))
            conn.commit(); flash("Đã thêm môn học", "success")
            return redirect(url_for("subjects.index"))
        except Exception:
            conn.rollback(); flash("Lỗi thêm môn học", "error")
        finally:
            cur.close(); conn.close()
    return render_template("subjects_form.html", form={})

@subjects_bp.route("/<int:subject_id>/edit", methods=["GET", "POST"])
@role_required("admin")
def edit(subject_id):
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT id, code, name FROM subjects WHERE id=%s", (subject_id,))
    row = cur.fetchone()
    if not row:
        cur.close(); conn.close(); return redirect(url_for("subjects.index"))
    if request.method == "POST":
        code = request.form.get("code"); name = request.form.get("name")
        try:
            cur.execute("UPDATE subjects SET code=%s, name=%s WHERE id=%s", (code, name, subject_id))
            conn.commit(); flash("Đã cập nhật", "success")
            return redirect(url_for("subjects.index"))
        except Exception:
            conn.rollback(); flash("Lỗi cập nhật", "error")
    cur.close(); conn.close()
    form = {"id": row[0], "code": row[1], "name": row[2]}
    return render_template("subjects_form.html", form=form)

@subjects_bp.route("/<int:subject_id>/delete", methods=["POST"])
@role_required("admin")
def delete(subject_id):
    conn = get_connection(); cur = conn.cursor()
    try:
        cur.execute("DELETE FROM subjects WHERE id=%s", (subject_id,))
        conn.commit(); flash("Đã xóa", "success")
    except Exception:
        conn.rollback(); flash("Lỗi xóa", "error")
    finally:
        cur.close(); conn.close()
    return redirect(url_for("subjects.index"))


@subjects_bp.route("/<int:subject_id>/students", methods=["GET", "POST"])
@role_required("admin", "lecturer")
def manage_students(subject_id):
    """Chức năng chọn sinh viên theo môn đã được loại bỏ.
    Danh sách sinh viên sẽ lấy từ lớp của buổi điểm danh.
    """
    flash("Chức năng chọn sinh viên theo môn đã được loại bỏ.", "info")
    return redirect(url_for("subjects.index"))
