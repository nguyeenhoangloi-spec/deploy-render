from connect_postgres import get_connection

def init():
    with open('schema.sql', 'r', encoding='utf-8') as f:
        sql = f.read()
    # Simple split by ';' while keeping semicolons
    statements = [s.strip() for s in sql.split(';') if s.strip()]
    conn = get_connection(); cur = conn.cursor()
    for stmt in statements:
        cur.execute(stmt + ';')
    conn.commit(); cur.close(); conn.close()
    print('Database schema initialized.')

if __name__ == '__main__':
    init()
