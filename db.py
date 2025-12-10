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

def get_person(person_id: int):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM persons WHERE id = ?", (person_id,))
    rows = cur.fetchone()
    conn.close()
    return rows

def add_person(first_name, last_name=None, birth_date=None, death_date=None, gender=None, notes=None):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO persons (first_name, last_name, birth_date, death_date, gender, notes)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (first_name, last_name, birth_date, death_date, gender, notes)
    )
    conn.commit()
    conn.close()