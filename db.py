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
    row = cur.fetchone()
    conn.close()
    return row

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

def update_person(person_id, first_name, last_name=None, birth_date=None, death_date=None, gender=None, notes=None):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE persons
        SET first_name = ?, last_name = ?, birth_date = ?, death_date = ?, gender = ?, notes = ?
        WHERE id = ?
        """,
        (first_name, last_name, birth_date, death_date, gender, notes, person_id)
    )
    conn.commit()
    conn.close()


def delete_person(person_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM persons WHERE id = ?", (person_id,))
    conn.commit()
    conn.close()

def add_relationship(person_id, relative_id, relation_type):
    """Добавляет связь между двумя людьми"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO relationships (person_id, relative_id, relation_type)
        VALUES (?, ?, ?)
        """,
        (person_id, relative_id, relation_type)
    )
    conn.commit()
    conn.close()
    
def get_parents(person_id):
    """Возвращает список родителей для данного человека"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT p.*
        FROM persons p
        JOIN relationships r ON r.person_id = p.id
        WHERE r.relative_id = ? AND r.relation_type = 'parent'
        """,
        (person_id,)
    )
    rows = cur.fetchall()
    conn.close()
    return rows

def get_children(person_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT p.*
        FROM persons p
        JOIN relationships r ON r.relative_id = p.id
        WHERE r.person_id = ? AND r.relation_type = 'parent'
        """,
        (person_id,)
    )
    rows = cur.fetchall()
    conn.close()
    return rows

def get_spouses(person_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT DISTINCT p.*
        FROM persons p
        JOIN relationships r
          ON (
                (r.person_id = ? AND r.relative_id = p.id)
             OR (r.relative_id = ? AND r.person_id = p.id)
             )
        WHERE r.relation_type = 'spouse'
        """,
        (person_id, person_id)
    )
    rows = cur.fetchall()
    conn.close()
    return rows

def get_siblings(person_id):
    """Возвращает список братьев/сестер для данного человека"""
    parents = get_parents(person_id)
    if not parents:
        return []

    seen = {}
    for parent in parents:
        children = get_children(parent["id"])
        for child in children:
            if child["id"] == person_id:
                continue
            # dedupe по id, но храним целую строку
            seen[child["id"]] = child

    return list(seen.values())

def get_grandparents(person_id):
    """Возвращает список бабушек/дедушек для данного человека"""
    parents = get_parents(person_id)
    if not parents:
        return []

    seen = {}
    for parent in parents:
        gps = get_parents(parent["id"])
        for gp in gps:
            seen[gp["id"]] = gp

    return list(seen.values())