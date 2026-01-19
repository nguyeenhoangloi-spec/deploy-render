from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from connect_postgres import get_connection
from auth import role_required, login_required

classes_bp = Blueprint("classes", __name__)

@classes_bp.route("/")
@login_required
def index():
    conn = get_connection(); cur = conn.cursor()
    try:
        role = session.get("role", "lecturer")
        user_id = session.get("user_id")
        if role == "lecturer" and user_id:
            # Chỉ hiển thị các lớp do giảng viên hiện tại quản lý
            cur.execute(
                """
                SELECT c.id, c.code, c.name
                FROM classes c
                JOIN instructors_classes ic ON ic.class_id=c.id
                WHERE ic.user_id=%s
                ORDER BY c.code
                """,
                (user_id,)
            )
        else:
            cur.execute("SELECT id, code, name FROM classes ORDER BY code")
        rows = cur.fetchall()
    finally:
        cur.close(); conn.close()
    return render_template("classes_list.html", rows=rows)

@classes_bp.route("/new", methods=["GET", "POST"])
@role_required("admin")
def create():
    if request.method == "POST":
        code = request.form.get("code"); name = request.form.get("name")
        conn = get_connection(); cur = conn.cursor()
        try:
            cur.execute("INSERT INTO classes (code, name) VALUES (%s, %s)", (code, name))
            conn.commit(); flash("Đã thêm lớp", "success")
            return redirect(url_for("classes.index"))
        except Exception:
            conn.rollback(); flash("Lỗi thêm lớp", "error")
        finally:
            cur.close(); conn.close()
    return render_template("classes_form.html", form={})

@classes_bp.route("/<int:class_id>/edit", methods=["GET", "POST"])
@role_required("admin")
def edit(class_id):
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT id, code, name FROM classes WHERE id=%s", (class_id,))
    row = cur.fetchone()
    if not row:
        cur.close(); conn.close(); return redirect(url_for("classes.index"))
    if request.method == "POST":
        code = request.form.get("code"); name = request.form.get("name")
        try:
            cur.execute("UPDATE classes SET code=%s, name=%s WHERE id=%s", (code, name, class_id))
            conn.commit(); flash("Đã cập nhật", "success")
            return redirect(url_for("classes.index"))
        except Exception:
            conn.rollback(); flash("Lỗi cập nhật", "error")
    cur.close(); conn.close()
    form = {"id": row[0], "code": row[1], "name": row[2]}
    return render_template("classes_form.html", form=form)

@classes_bp.route("/<int:class_id>/delete", methods=["POST"])
@role_required("admin")
def delete(class_id):
    conn = get_connection(); cur = conn.cursor()
    try:
        cur.execute("DELETE FROM classes WHERE id=%s", (class_id,))
        conn.commit(); flash("Đã xóa", "success")
    except Exception:
        conn.rollback(); flash("Lỗi xóa", "error")
    finally:
        cur.close(); conn.close()
    return redirect(url_for("classes.index"))


@classes_bp.route("/<int:class_id>/subjects", methods=["GET", "POST"])
@role_required("admin", "lecturer")
def manage_subjects(class_id):
    """Gán/bỏ gán các môn học cho một lớp (bảng class_subjects)."""
    conn = get_connection(); cur = conn.cursor()
    # Nếu là giảng viên, kiểm tra quyền sở hữu lớp
    try:
        role = session.get("role", "lecturer")
        user_id = session.get("user_id")
        if role == "lecturer" and user_id:
            cur.execute("SELECT 1 FROM instructors_classes WHERE class_id=%s AND user_id=%s", (class_id, user_id))
            ok = cur.fetchone()
            if not ok:
                cur.close(); conn.close()
                flash("Bạn không được phân công quản lý lớp này", "error")
                return redirect(url_for("classes.index"))
    except Exception:
        pass
    # Lấy thông tin lớp
    cur.execute("SELECT id, code, name FROM classes WHERE id=%s", (class_id,))
    cls = cur.fetchone()
    if not cls:
        cur.close(); conn.close();
        flash("Không tìm thấy lớp", "error")
        return redirect(url_for("classes.index"))

    if request.method == "POST":
        selected = request.form.getlist("subject_ids")  # danh sách id dạng chuỗi
        try:
            # Lấy danh sách hiện có
            cur.execute("SELECT subject_id FROM class_subjects WHERE class_id=%s", (class_id,))
            current = {str(r[0]) for r in cur.fetchall()}
            desired = set(selected)

            to_add = desired - current
            to_del = current - desired

            # Xóa những cái không còn (xử lý lần lượt để tránh lỗi cast mảng)
            for sid in to_del:
                cur.execute(
                    "DELETE FROM class_subjects WHERE class_id=%s AND subject_id=%s",
                    (class_id, int(sid))
                )
            # Thêm mới
            for sid in to_add:
                cur.execute(
                    "INSERT INTO class_subjects (class_id, subject_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                    (class_id, int(sid))
                )
            conn.commit()
            flash("Đã cập nhật môn học cho lớp", "success")
        except Exception as e:
            conn.rollback(); flash(f"Lỗi cập nhật: {e}", "error")

    # Load danh sách môn và các gán hiện có
    cur.execute("SELECT id, code, name FROM subjects ORDER BY code")
    subjects = cur.fetchall()
    cur.execute("SELECT subject_id FROM class_subjects WHERE class_id=%s", (class_id,))
    selected_ids = {r[0] for r in cur.fetchall()}
    cur.close(); conn.close()
    return render_template("classes_subjects.html", cls=cls, subjects=subjects, selected_ids=selected_ids)

@classes_bp.route("/<int:class_id>/instructors", methods=["GET", "POST"])
@role_required("admin")
def manage_instructors(class_id):
    """Gán/bỏ gán giảng viên cho lớp và phân môn dạy trong lớp.
    - Bảng instructors_classes: giảng viên quản lý lớp
    - Bảng instructors_class_subjects: giảng viên dạy môn trong lớp
    Chỉ admin.
    """
    conn = get_connection(); cur = conn.cursor()
    # Thông tin lớp
    cur.execute("SELECT id, code, name FROM classes WHERE id=%s", (class_id,))
    cls = cur.fetchone()
    if not cls:
        cur.close(); conn.close();
        flash("Không tìm thấy lớp", "error")
        return redirect(url_for("classes.index"))

    if request.method == "POST":
        selected = set(request.form.getlist("user_ids"))
        try:
            # Hiện có
            cur.execute("SELECT user_id FROM instructors_classes WHERE class_id=%s", (class_id,))
            current = {str(r[0]) for r in cur.fetchall()}
            to_add = selected - current
            to_del = current - selected
            # Xóa bỏ
            for uid in to_del:
                cur.execute(
                    "DELETE FROM instructors_classes WHERE class_id=%s AND user_id=%s",
                    (class_id, int(uid))
                )
            # Thêm mới
            for uid in to_add:
                cur.execute(
                    "INSERT INTO instructors_classes (class_id, user_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                    (class_id, int(uid))
                )
            # Phân môn cho từng giảng viên trong lớp (instructors_class_subjects)
            # Danh sách môn của lớp
            cur.execute("SELECT subject_id FROM class_subjects WHERE class_id=%s", (class_id,))
            class_subject_ids = [r[0] for r in cur.fetchall()]
            # Duyệt từng giảng viên đang được chọn
            for uid in selected:
                # Danh sách môn tick cho giảng viên này
                assign_list = set(request.form.getlist(f"assign_{uid}"))
                # Hiện có trong DB
                cur.execute(
                    "SELECT subject_id FROM instructors_class_subjects WHERE class_id=%s AND user_id=%s",
                    (class_id, int(uid))
                )
                current_ics = {str(r[0]) for r in cur.fetchall()}
                # Chỉ cho phép gán các môn đang thuộc lớp
                valid_assign = {sid for sid in assign_list if sid.isdigit() and int(sid) in class_subject_ids}
                to_add_ics = valid_assign - current_ics
                to_del_ics = current_ics - valid_assign
                for sid in to_del_ics:
                    cur.execute(
                        "DELETE FROM instructors_class_subjects WHERE class_id=%s AND user_id=%s AND subject_id=%s",
                        (class_id, int(uid), int(sid))
                    )
                for sid in to_add_ics:
                    cur.execute(
                        "INSERT INTO instructors_class_subjects (class_id, subject_id, user_id) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                        (class_id, int(sid), int(uid))
                    )
            conn.commit(); flash("Đã cập nhật giảng viên và phân môn cho lớp", "success")
        except Exception as e:
            conn.rollback(); flash(f"Lỗi cập nhật: {e}", "error")

    # Tải danh sách giảng viên
    cur.execute("SELECT id, fullname, username FROM users WHERE role='lecturer' ORDER BY fullname")
    lecturers = cur.fetchall()
    # Các gán hiện có
    cur.execute("SELECT user_id FROM instructors_classes WHERE class_id=%s", (class_id,))
    selected_ids = {r[0] for r in cur.fetchall()}
    # Danh sách môn của lớp (để phân cho giảng viên)
    cur.execute("SELECT s.id, s.code, s.name FROM subjects s JOIN class_subjects cs ON cs.subject_id=s.id WHERE cs.class_id=%s ORDER BY s.code", (class_id,))
    subjects = cur.fetchall()
    # Map: các môn giảng viên đang được gán trong lớp
    ics_map = {}
    for u in lecturers:
        uid = u[0]
        cur.execute("SELECT subject_id FROM instructors_class_subjects WHERE class_id=%s AND user_id=%s", (class_id, uid))
        ics_map[uid] = {r[0] for r in cur.fetchall()}
    cur.close(); conn.close()
    return render_template("classes_instructors.html", cls=cls, lecturers=lecturers, selected_ids=selected_ids, subjects=subjects, ics_map=ics_map)
