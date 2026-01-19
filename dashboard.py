from flask import Blueprint, render_template_string, render_template, session, redirect, url_for
from connect_postgres import get_connection
from datetime import datetime, date

dashboard_bp = Blueprint("dashboard", __name__)

HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .dashboard {
            max-width: 800px;
            margin: 0 auto;
            padding-top: 20px;
            position: relative;
        }
        
        .user-menu {
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 1000;
        }
        
        .user-avatar {
            display: flex;
            align-items: center;
            background: rgba(255,255,255,0.2);
            border: 1px solid rgba(255,255,255,0.3);
            padding: 8px 15px;
            border-radius: 25px;
            color: white;
            cursor: pointer;
            transition: all 0.3s ease;
            backdrop-filter: blur(10px);
        }
        
        .user-avatar:hover {
            background: rgba(255,255,255,0.3);
        }
        
        .avatar-icon {
            width: 28px;
            height: 28px;
            background: #fff;
            border-radius: 50%;
            margin-right: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 14px;
        }
        
        .dropdown {
            position: absolute;
            top: 100%;
            right: 0;
            background: white;
            border-radius: 8px;
            box-shadow: 0 8px 25px rgba(0,0,0,0.15);
            min-width: 180px;
            opacity: 0;
            visibility: hidden;
            transform: translateY(-10px);
            transition: all 0.3s ease;
            z-index: 1000;
            margin-top: 5px;
        }
        
        .user-menu:hover .dropdown {
            opacity: 1;
            visibility: visible;
            transform: translateY(0);
        }
        
        .dropdown-item {
            display: block;
            padding: 12px 18px;
            color: #333;
            text-decoration: none;
            border: none;
            background: none;
            width: 100%;
            text-align: left;
            cursor: pointer;
            transition: background 0.2s;
            font-size: 14px;
        }
        
        .dropdown-item:hover {
            background: #f8f9fa;
        }
        
        .dropdown-item:first-child {
            border-radius: 8px 8px 0 0;
        }
        
        .dropdown-item:last-child {
            border-radius: 0 0 8px 8px;
            color: #dc3545;
        }
        
        .header {
            text-align: center;
            color: white;
            margin-bottom: 40px;
            margin-top: 30px;
        }
        
        .header h1 {
            font-size: 2.5em;
            font-weight: 300;
            margin-bottom: 10px;
        }
        
        .header p {
            font-size: 1.1em;
            opacity: 0.9;
        }
        
        .card-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .card {
            background: white;
            border-radius: 12px;
            padding: 25px;
            box-shadow: 0 8px 25px rgba(0,0,0,0.15);
            transition: all 0.3s ease;
            cursor: pointer;
        }
        
        .card:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 35px rgba(0,0,0,0.2);
        }
        
        .card-icon {
            font-size: 2.5em;
            margin-bottom: 15px;
            display: block;
        }
        
        .card h3 {
            color: #333;
            font-size: 1.3em;
            margin-bottom: 8px;
            font-weight: 600;
        }
        
        .card p {
            color: #666;
            font-size: 0.95em;
            line-height: 1.4;
        }
        
        .card form {
            margin-top: 15px;
        }
        
        .card button {
            width: 100%;
            padding: 12px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 1em;
            font-weight: 500;
            cursor: pointer;
            transition: background 0.3s ease;
        }
        
        .card button:hover {
            background: #5a67d8;
        }
        
        .logout-section {
            display: none;
        }
        
        @media (max-width: 768px) {
            .card-grid {
                grid-template-columns: 1fr;
            }
            
            .header h1 {
                font-size: 2em;
            }
        }
    </style>
</head>
<body>
    <div class="dashboard">
        <div class="user-menu">
            <div class="user-avatar">
                <div class="avatar-icon">👤</div>
                <span>{{username}}</span>
            </div>
            <div class="dropdown">
                <button class="dropdown-item">Lịch sử nhận diện</button>
                <form action="{{ url_for('logout.index') }}" method="get" style="margin: 0;">
                    <button type="submit" class="dropdown-item">Đăng xuất</button>
                </form>
            </div>
        </div>
        
        <div class="header">
            <h1>Xin chào, {{username}}!</h1>
            <p>Chọn chức năng bạn muốn sử dụng</p>
        </div>
        
        <div class="card-grid">
            <div class="card">
                <span class="card-icon">📁</span>
                <h3>Upload Ảnh</h3>
                <p>Tải lên ảnh từ thiết bị để nhận diện khuôn mặt</p>
                <form action="{{ url_for('recognize.index') }}" method="get">
                    <button type="submit">Bắt đầu</button>
                </form>
            </div>
            
            <div class="card">
                <span class="card-icon">📸</span>
                <h3>Sử dụng Webcam</h3>
                <p>Chụp ảnh trực tiếp từ camera để nhận diện</p>
                <form action="{{ url_for('webcam.index') }}" method="get">
                    <button type="submit">Mở Camera</button>
                </form>
            </div>
            
            <div class="card">
                <span class="card-icon">👤</span>
                <h3>Thêm Người Dùng</h3>
                <p>Thêm thông tin và ảnh của người dùng mới</p>
                <form action="{{ url_for('add_user.index') }}" method="get">
                    <button type="submit">Thêm Mới</button>
                </form>
            </div>
        </div>
    </div>
</body>
</html>
"""

@dashboard_bp.route("/")
def index():
    if "username" not in session:
        return redirect(url_for("home.index"))
    
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        # Lấy tổng số sinh viên
        cur.execute("SELECT COUNT(*) FROM students")
        result = cur.fetchone()
        total_students = result[0] if result else 0
        
        # Lấy số buổi điểm danh hôm nay
        today = date.today()
        cur.execute("""
            SELECT COUNT(*) FROM attendance_sessions 
            WHERE DATE(session_date) = %s
        """, (today,))
        result = cur.fetchone()
        attendance_today = result[0] if result else 0
        
        # Lấy số lượt điểm danh hôm nay
        cur.execute("""
            SELECT COUNT(DISTINCT ar.student_id) 
            FROM attendance_records ar
            JOIN attendance_sessions ats ON ar.session_id = ats.id
            WHERE DATE(ats.session_date) = %s
        """, (today,))
        result = cur.fetchone()
        students_checked_today = result[0] if result else 0
        
        # Lấy tổng số lớp học
        cur.execute("SELECT COUNT(*) FROM classes")
        result = cur.fetchone()
        total_classes = result[0] if result else 0
        
        # Lấy tổng số môn học
        cur.execute("SELECT COUNT(*) FROM subjects")
        result = cur.fetchone()
        total_subjects = result[0] if result else 0
        
        stats = {
            'total_students': total_students,
            'attendance_today': attendance_today,
            'students_checked_today': students_checked_today,
            'total_classes': total_classes,
            'total_subjects': total_subjects
        }
        
    except Exception as e:
        print(f"Error fetching stats: {e}")
        stats = {
            'total_students': 0,
            'attendance_today': 0,
            'students_checked_today': 0,
            'total_classes': 0,
            'total_subjects': 0
        }
    finally:
        cur.close()
        conn.close()
    
    return render_template("dashboard.html", username=session["username"], stats=stats)