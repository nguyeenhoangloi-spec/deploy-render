import psycopg2  # Thư viện kết nối PostgreSQL cho Python

# Hàm tạo kết nối đến cơ sở dữ liệu PostgreSQL
def get_connection():
    return psycopg2.connect(
        host="localhost",      # Địa chỉ server PostgreSQL
        database="doanpythonc",# Tên database
        user="postgres",       # Tên user đăng nhập
        password="123456",     # Mật khẩu user
        port="5432"            # Cổng kết nối mặc định
    )
# Kiểm tra kết nối khi chạy trực tiếp file này
if __name__ == '__main__':
    try:
        conn = get_connection()      # Tạo kết nối
        print("Kết nối thành công!")# In ra nếu kết nối thành công
        conn.close()                # Đóng kết nối
    except Exception as e:
        print("Kết nối thất bại:", e) # In ra lỗi nếu kết nối thất bại