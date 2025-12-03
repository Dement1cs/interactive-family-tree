import sqlite3

DB_PATH = "database.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    with open("schema.sql", "r", encoding="utf-8") as f:
        sql = f.read()
    conn.executescript(sql)
    conn.commit()
    conn.close()

def get_all_persons():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM persons ORDER BY id")
    rows = cur.fetchall()
    conn.close()
    return rows