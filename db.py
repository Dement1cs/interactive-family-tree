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

# ========= Возвращает список всех людей из таблицы persons ==========
def get_all_persons(tree_id=None):
    conn = get_db()
    cur = conn.cursor()

    if tree_id:
        cur.execute(
            "SELECT * FROM persons WHERE tree_id = ? ORDER BY id",
            (tree_id,)
        )
    else:
        cur.execute("SELECT * FROM persons ORDER BY id")

    rows = cur.fetchall()
    conn.close()
    return rows
# =======================================

# ======= посчитать людей ===============
def count_persons_in_tree(tree_id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT COUNT(*) AS total FROM persons WHERE tree_id = ?",
        (tree_id,)
    )

    row = cur.fetchone()
    conn.close()

    return row["total"] if row else 0
# ==============================

# ====Возвращает ОДНУ запись о человеке по его id ===========
def get_person(person_id: int):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM persons WHERE id = ?", (person_id,))
    row = cur.fetchone()
    conn.close()
    return row
# ==============================

# ======= Добавляет нового человека ===============
def add_person(first_name, middle_name=None, last_name=None, maiden_name=None,
               birth_date=None, death_date=None,
               birth_year=None, birth_month=None, birth_day=None,
               death_year=None, death_month=None, death_day=None,
               gender=None, notes=None, tree_id=None):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO persons (
            first_name, middle_name, last_name, maiden_name,
            birth_date, death_date,
            birth_year, birth_month, birth_day,
            death_year, death_month, death_day,
            gender, notes, tree_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            first_name, middle_name, last_name, maiden_name,
            birth_date, death_date,
            birth_year, birth_month, birth_day,
            death_year, death_month, death_day,
            gender, notes, tree_id
        )
    )
    conn.commit()
    conn.close()
# ==============================

# ======= Обновляет данные о человеке с указанным id ==============
def update_person(person_id, first_name, middle_name=None, last_name=None, maiden_name=None,
                  birth_date=None, death_date=None,
                  birth_year=None, birth_month=None, birth_day=None,
                  death_year=None, death_month=None, death_day=None,
                  gender=None, notes=None):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE persons
        SET first_name = ?, middle_name = ?, last_name = ?, maiden_name = ?,
            birth_date = ?, death_date = ?,
            birth_year = ?, birth_month = ?, birth_day = ?,
            death_year = ?, death_month = ?, death_day = ?,
            gender = ?, notes = ?
        WHERE id = ?
        """,
        (
            first_name, middle_name, last_name, maiden_name,
            birth_date, death_date,
            birth_year, birth_month, birth_day,
            death_year, death_month, death_day,
            gender, notes, person_id
        )
    )
    conn.commit()
    conn.close()
# ==============================

# ==update_person_photo============================
def update_person_photo(person_id, photo_filename):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "UPDATE persons SET photo_filename = ? WHERE id = ?",
        (photo_filename, person_id)
    )
    conn.commit()
    conn.close()
# ==============================

# ==remove_person_photo============================
def remove_person_photo(person_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "UPDATE persons SET photo_filename = NULL WHERE id = ?",
        (person_id,)
    )
    conn.commit()
    conn.close()
# ==============================


# ===== GALLARY =========================
def add_gallery_photo(person_id, filename):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO person_photos (person_id, filename) VALUES (?, ?)",
        (person_id, filename)
    )
    conn.commit()
    conn.close()


def get_person_photos(person_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, person_id, filename, uploaded_at
        FROM person_photos
        WHERE person_id = ?
        ORDER BY uploaded_at DESC, id DESC
        """,
        (person_id,)
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def get_gallery_photo(photo_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, person_id, filename, uploaded_at
        FROM person_photos
        WHERE id = ?
        """,
        (photo_id,)
    )
    row = cur.fetchone()
    conn.close()
    return row


def delete_gallery_photo(photo_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM person_photos WHERE id = ?", (photo_id,))
    conn.commit()
    conn.close()
# ==========================================================================================



# ==========Удаляет человека по id из таблицы persons =================
def delete_person(person_id):
    conn = get_db()
    cur = conn.cursor()
    #удалить все связи, где участвует этот человек 
    cur.execute(
        "DELETE FROM relationships WHERE person_id = ? OR relative_id = ?",
        (person_id, person_id)
    )
    #удалить самого человека
    cur.execute("DELETE FROM persons WHERE id = ?", (person_id,))
    conn.commit()
    conn.close()
# ==============================

# ========= Удалить дерево =====================
def delete_tree_data(tree_id):
    conn = get_db()
    cur = conn.cursor()

    # Сначала удалить связи всех людей этого дерева
    cur.execute("""
        DELETE FROM relationships
        WHERE person_id IN (SELECT id FROM persons WHERE tree_id = ?)
           OR relative_id IN (SELECT id FROM persons WHERE tree_id = ?)
    """, (tree_id, tree_id))

    # Потом удалить самих людей
    cur.execute("DELETE FROM persons WHERE tree_id = ?", (tree_id,))

    conn.commit()
    conn.close()
# ==============================

# ========= Поиск ===============
def search_persons(query, tree_id=None, exclude_id=None, limit=10):
    conn = get_db()
    cur = conn.cursor()

    q = (query or "").strip()
    if not q:
        conn.close()
        return []

    like = f"%{q}%"

    sql = """
        SELECT id, first_name, last_name, gender
        FROM persons
        WHERE 1=1
    """
    params = []

    if tree_id:
        sql += " AND tree_id = ?"
        params.append(tree_id)

    if exclude_id is not None:
        sql += " AND id != ?"
        params.append(exclude_id)

    sql += """
       AND (
            first_name LIKE ?
         OR last_name LIKE ?
         OR (first_name || ' ' || IFNULL(last_name, '')) LIKE ?
       )
       ORDER BY first_name ASC
       LIMIT ?
    """
    params.extend([like, like, like, limit])

    cur.execute(sql, params)
    rows = cur.fetchall()
    conn.close()
    return rows
# ==============================


# =============== добавить связь ================
def add_relationship(person_id, relative_id, relation_type):
    """Добавляет связь между двумя людьми
        person_id   - основной человек в связи
        relative_id - связанный с ним родственник
    """
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
# ==============================   

# ======== нет дубликата ====================== 
def relationship_exists(person_id, relative_id, relation_type):
    conn = get_db()
    cur = conn.cursor()

    if relation_type == "spouse":
        cur.execute(
            """
            SELECT 1
            FROM relationships
            WHERE relation_type = 'spouse'
              AND (
                    (person_id = ? AND relative_id = ?)
                 OR (person_id = ? AND relative_id = ?)
              )
            LIMIT 1
            """,
            (person_id, relative_id, relative_id, person_id)
        )
    else:
        cur.execute(
            """
            SELECT 1
            FROM relationships
            WHERE person_id = ? AND relative_id = ? AND relation_type = ?
            LIMIT 1
            """,
            (person_id, relative_id, relation_type)
        )

    row = cur.fetchone()
    conn.close()
    return row is not None
# ============================== 

# =============== удалить связь ================
def delete_relationship(person_id, relative_id, relation_type):
    conn = get_db()
    cur = conn.cursor()

    if relation_type == "spouse":
        cur.execute(
            """
            DELETE FROM relationships
            WHERE relation_type = 'spouse'
              AND (
                    (person_id = ? AND relative_id = ?)
                 OR (person_id = ? AND relative_id = ?)
              )
            """,
            (person_id, relative_id, relative_id, person_id)
        )
    else:
        cur.execute(
            """
            DELETE FROM relationships
            WHERE person_id = ? AND relative_id = ? AND relation_type = ?
            """,
            (person_id, relative_id, relation_type)
        )

    conn.commit()
    conn.close()
# ==============================  


def get_parents(person_id):
    """Возвращает список родителей для данного человека
    
    relative_id = person_id и relation_type = 'parent'.
    В этих связях person_id - и есть родитель.
    
    """
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

    """
    Возвращает список супругов для данного человека
    связь симметрична.
    """
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
    """Возвращает список братьев/сестер для данного человека
    два человека считаются siblings, если у них есть хотя бы один общий родитель
    
    Берём всех родителей person_id (get_parents)
    Для каждого родителя берём его детей (get_children)
    Собираем всех таких детей в словарь по id чтобы убрать дубликаты
    Исключаем самого person_id.
    """
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
    """Возвращает список бабушек/дедушек для данного человека
    Берём родителей person_id.
    Для каждого родителя вызываем get_parents(parent_id).
    Все найденные родители родителей добавляем в словарь по id
        
    """
    parents = get_parents(person_id)
    if not parents:
        return []

    seen = {}
    for parent in parents:
        gps = get_parents(parent["id"])
        for gp in gps:
            seen[gp["id"]] = gp

    return list(seen.values())

# ========= UNCLE | AUNTS ==================================================
def get_uncles_aunts(person_id):
    conn = get_db()
    cur = conn.cursor()

    # родители текущего человека
    parents = cur.execute("""
        SELECT DISTINCT p.*
        FROM relationships r
        JOIN persons p ON p.id = r.person_id
        WHERE r.relation_type = 'parent'
          AND r.relative_id = ?
    """, (person_id,)).fetchall()

    if not parents:
        conn.close()
        return []

    parent_ids = [p["id"] for p in parents]
    placeholders = ",".join("?" for _ in parent_ids)

    # брать siblings родителей:
    # люди, у которых есть хотя бы один общий parent с любым из родителей текущего человека
    rows = cur.execute(f"""
        SELECT DISTINCT s.*
        FROM relationships rp1
        JOIN relationships rp2
          ON rp1.person_id = rp2.person_id
        JOIN persons s
          ON s.id = rp2.relative_id
        WHERE rp1.relation_type = 'parent'
          AND rp2.relation_type = 'parent'
          AND rp1.relative_id IN ({placeholders})
          AND rp2.relative_id != rp1.relative_id
    """, tuple(parent_ids)).fetchall()

    # убрать самих родителей, если вдруг попали
    result = [row for row in rows if row["id"] not in parent_ids]

    conn.close()
    return result
# =======================================================================

# ======== nephews | nieces ===============================================================
def get_nephews_nieces(person_id):
    conn = get_db()
    cur = conn.cursor()

    # siblings текущего человека
    siblings = cur.execute("""
        SELECT DISTINCT s.*
        FROM relationships rp1
        JOIN relationships rp2
          ON rp1.person_id = rp2.person_id
        JOIN persons s
          ON s.id = rp2.relative_id
        WHERE rp1.relation_type = 'parent'
          AND rp2.relation_type = 'parent'
          AND rp1.relative_id = ?
          AND rp2.relative_id != rp1.relative_id
    """, (person_id,)).fetchall()

    if not siblings:
        conn.close()
        return []

    sibling_ids = [s["id"] for s in siblings]
    placeholders = ",".join("?" for _ in sibling_ids)

    rows = cur.execute(f"""
        SELECT DISTINCT p.*
        FROM relationships r
        JOIN persons p ON p.id = r.relative_id
        WHERE r.relation_type = 'parent'
          AND r.person_id IN ({placeholders})
    """, tuple(sibling_ids)).fetchall()

    conn.close()
    return rows
# =======================================================================

def get_ancestors_by_level(person_id, level):
    if level < 1:
        return []

    conn = get_db()
    cur = conn.cursor()

    current_ids = {person_id}
    rows = []

    for _ in range(level):
        if not current_ids:
            conn.close()
            return []

        placeholders = ",".join("?" for _ in current_ids)

        rows = cur.execute(f"""
            SELECT DISTINCT p.*
            FROM relationships r
            JOIN persons p ON p.id = r.person_id
            WHERE r.relation_type = 'parent'
              AND r.relative_id IN ({placeholders})
        """, tuple(current_ids)).fetchall()

        current_ids = {row["id"] for row in rows}

    conn.close()
    return rows


def get_great_grandparents(person_id):
    return get_ancestors_by_level(person_id, 3)


def get_great_great_grandparents(person_id):
    return get_ancestors_by_level(person_id, 4)


def get_ancestors(person_id, min_level=5, max_level=10):
    conn = get_db()
    conn.close()

    all_ancestors = []
    seen_ids = set()

    for level in range(min_level, max_level + 1):
        rows = get_ancestors_by_level(person_id, level)
        for row in rows:
            if row["id"] not in seen_ids:
                seen_ids.add(row["id"])
                all_ancestors.append(row)

    return all_ancestors