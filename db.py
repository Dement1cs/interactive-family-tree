# =========================================================
# imports
# =========================================================
import sqlite3

# =========================================================
# Database connection / init helpers
# =========================================================

# Path to the local SQLite database file used for tree data
# Путь к локальному файлу SQLite, в котором хранятся данные дерева
DB_PATH = "database.db"

def get_db():
    """Create and return a SQLite connection with row access by column name."""

    # Use sqlite3.Row so query results can be accessed like dictionaries
    # Использовать sqlite3.Row, чтобы к результатам запроса можно было обращаться по именам колонок
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the local SQLite database from schema.sql."""

    # Open a connection to the local data database
    # Открыть соединение с локальной базой данных
    conn = get_db()

    # Read the SQL schema file and execute it as a script
    # Прочитать SQL-схему из файла и выполнить её как единый скрипт
    with open("schema.sql", "r", encoding="utf-8") as f:
        sql = f.read()

    conn.executescript(sql)
    conn.commit()
    conn.close()


# =========================================================
# Person queries
# =========================================================

# --- get_all_persons -------------------------------------
def get_all_persons(tree_id=None):
    """Return all people, optionally filtered to a specific tree."""

    conn = get_db()
    cur = conn.cursor()

    # If tree_id is provided, return only people from that tree
    # Если передан tree_id, вернуть только людей из этого дерева
    if tree_id:
        cur.execute(
            "SELECT * FROM persons WHERE tree_id = ? ORDER BY id",
            (tree_id,)
        )
    else:
        # Otherwise return all people from the database
        # Иначе вернуть всех людей из базы данных
        cur.execute("SELECT * FROM persons ORDER BY id")

    rows = cur.fetchall()
    conn.close()
    return rows


# --- count_persons_in_tree -------------------------------
def count_persons_in_tree(tree_id):
    """Return the number of people that belong to the selected tree."""

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT COUNT(*) AS total FROM persons WHERE tree_id = ?",
        (tree_id,)
    )

    row = cur.fetchone()
    conn.close()

    return row["total"] if row else 0


# --- get_person ------------------------------------------
def get_person(person_id: int):
    """Return one person record by id."""

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM persons WHERE id = ?", (person_id,))
    row = cur.fetchone()
    conn.close()
    return row


# --- add_person ------------------------------------------
def add_person(first_name, middle_name=None, last_name=None, maiden_name=None,
               birth_date=None, death_date=None,
               birth_year=None, birth_month=None, birth_day=None,
               death_year=None, death_month=None, death_day=None,
               gender=None, notes=None, tree_id=None):
    """Insert a new person into the persons table."""

    conn = get_db()
    cur = conn.cursor()

    # Store both full date strings and partial date components
    # Сохранить как полные строки дат, так и отдельные части неполных дат
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


# --- update_person ---------------------------------------
def update_person(person_id, first_name, middle_name=None, last_name=None, maiden_name=None,
                  birth_date=None, death_date=None,
                  birth_year=None, birth_month=None, birth_day=None,
                  death_year=None, death_month=None, death_day=None,
                  gender=None, notes=None):
    """Update the editable fields of an existing person."""

    conn = get_db()
    cur = conn.cursor()

    # Update both textual and partial-date fields for the selected person
    # Обновить как текстовые поля, так и поля неполной даты для выбранного человека
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

# --- delete_person ---------------------------------------
def delete_person(person_id):
    """Delete a person together with their gallery records and relationships."""

    conn = get_db()
    cur = conn.cursor()

    # Delete gallery photo records linked to this person
    # Удалить записи фотографий галереи, связанные с этим человеком
    cur.execute("DELETE FROM person_photos WHERE person_id = ?", (person_id,))

    # Delete all relationships where this person participates
    # Удалить все связи, в которых участвует этот человек
    cur.execute(
        "DELETE FROM relationships WHERE person_id = ? OR relative_id = ?",
        (person_id, person_id)
    )

    # Delete the person record itself
    # Удалить саму запись человека
    cur.execute("DELETE FROM persons WHERE id = ?", (person_id,))

    conn.commit()
    conn.close()



# =========================================================
# Photo queries
# =========================================================

# --- update_person_photo ---------------------------------
def update_person_photo(person_id, photo_filename):
    """Store the main profile photo filename for a person."""

    conn = get_db()
    cur = conn.cursor()

    # Save the profile photo filename in the persons table
    # Сохранить имя файла фото профиля в таблице persons
    cur.execute(
        "UPDATE persons SET photo_filename = ? WHERE id = ?",
        (photo_filename, person_id)
    )

    conn.commit()
    conn.close()


# --- remove_person_photo ---------------------------------
def remove_person_photo(person_id):
    """Clear the main profile photo filename for a person."""

    conn = get_db()
    cur = conn.cursor()

    # Remove the profile photo reference from the persons table
    # Удалить ссылку на фото профиля из таблицы persons
    cur.execute(
        "UPDATE persons SET photo_filename = NULL WHERE id = ?",
        (person_id,)
    )

    conn.commit()
    conn.close()


# --- add_gallery_photo -----------------------------------
def add_gallery_photo(person_id, filename):
    """Insert a new gallery photo record for a person."""

    conn = get_db()
    cur = conn.cursor()

    # Store one gallery photo entry linked to the selected person
    # Сохранить одну запись фотографии галереи, привязанную к выбранному человеку
    cur.execute(
        "INSERT INTO person_photos (person_id, filename) VALUES (?, ?)",
        (person_id, filename)
    )

    conn.commit()
    conn.close()


# --- get_person_photos -----------------------------------
def get_person_photos(person_id):
    """Return all gallery photos for a person, newest first."""

    conn = get_db()
    cur = conn.cursor()

    # Return gallery photos ordered from newest to oldest
    # Вернуть фотографии галереи в порядке от новых к старым
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


# --- get_gallery_photo -----------------------------------
def get_gallery_photo(photo_id):
    """Return one gallery photo record by id."""

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


# --- delete_gallery_photo --------------------------------
def delete_gallery_photo(photo_id):
    """Delete one gallery photo record by id."""

    conn = get_db()
    cur = conn.cursor()

    cur.execute("DELETE FROM person_photos WHERE id = ?", (photo_id,))
    conn.commit()
    conn.close()




# =========================================================
# Tree cleanup / utility queries
# =========================================================

# --- delete_tree_data ------------------------------------
def delete_tree_data(tree_id):
    """Delete all SQLite data that belongs to one tree."""

    conn = get_db()
    cur = conn.cursor()

    # Delete gallery photo records for people in this tree
    # Удалить записи фотографий галереи для людей из этого дерева
    cur.execute("""
        DELETE FROM person_photos
        WHERE person_id IN (SELECT id FROM persons WHERE tree_id = ?)
    """, (tree_id,))

    # Delete relationships where either side belongs to this tree
    # Удалить связи, где любая из сторон принадлежит этому дереву
    cur.execute("""
        DELETE FROM relationships
        WHERE person_id IN (SELECT id FROM persons WHERE tree_id = ?)
           OR relative_id IN (SELECT id FROM persons WHERE tree_id = ?)
    """, (tree_id, tree_id))

    # Delete the people records themselves
    # Удалить сами записи людей
    cur.execute("DELETE FROM persons WHERE tree_id = ?", (tree_id,))

    conn.commit()
    conn.close()



# =========================================================
# Search helpers
# =========================================================

# --- search_persons --------------------------------------
def search_persons(query, tree_id=None, exclude_id=None, limit=10):
    """Search people by name, optionally limited to one tree and excluding one person."""

    conn = get_db()
    cur = conn.cursor()

    # Normalize the incoming search query
    # Нормализовать входящий поисковый запрос
    q = (query or "").strip()
    if not q:
        conn.close()
        return []

    like = f"%{q}%"

    # Build the SQL query step by step depending on optional filters
    # Построить SQL-запрос по шагам в зависимости от необязательных фильтров
    sql = """
        SELECT id, first_name, last_name, gender
        FROM persons
        WHERE 1=1
    """
    params = []

    # Limit search to one tree if tree_id was provided
    # Ограничить поиск одним деревом, если передан tree_id
    if tree_id:
        sql += " AND tree_id = ?"
        params.append(tree_id)

    # Exclude one person from search results when needed
    # Исключить одного человека из результатов поиска при необходимости
    if exclude_id is not None:
        sql += " AND id != ?"
        params.append(exclude_id)

    # Match by first name, last name, or combined full name
    # Искать по имени, фамилии или их объединённому полному имени
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




# =========================================================
# Relationship queries
# =========================================================

# --- add_relationship ------------------------------------
def add_relationship(person_id, relative_id, relation_type):
    """Insert one relationship record between two people."""

    conn = get_db()
    cur = conn.cursor()

    # Store one directed relationship record in the relationships table
    # Сохранить одну направленную запись связи в таблице relationships
    cur.execute(
        """
        INSERT INTO relationships (person_id, relative_id, relation_type)
        VALUES (?, ?, ?)
        """,
        (person_id, relative_id, relation_type)
    )

    conn.commit()
    conn.close()


# --- relationship_exists ---------------------------------
def relationship_exists(person_id, relative_id, relation_type):
    """Return True if the requested relationship already exists."""

    conn = get_db()
    cur = conn.cursor()

    # Spouse relation is treated as symmetric, so check both directions
    # Связь супругов считается симметричной, поэтому нужно проверить оба направления
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
        # Other relation types are stored as directed records
        # Остальные типы связей хранятся как направленные записи
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


# --- delete_relationship ---------------------------------
def delete_relationship(person_id, relative_id, relation_type):
    """Delete one relationship record, or both directions for spouse relations."""

    conn = get_db()
    cur = conn.cursor()

    # Spouse relation must be removed in both directions
    # Связь супругов нужно удалить в обоих направлениях
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
        # Other relation types are deleted as directed records
        # Остальные типы связей удаляются как направленные записи
        cur.execute(
            """
            DELETE FROM relationships
            WHERE person_id = ? AND relative_id = ? AND relation_type = ?
            """,
            (person_id, relative_id, relation_type)
        )

    conn.commit()
    conn.close()



# =========================================================
# Genealogy helpers
# =========================================================

# --- get_parents -----------------------------------------
def get_parents(person_id):
    """Return all parents of the selected person."""

    conn = get_db()
    cur = conn.cursor()

    # Parent relation is stored as: parent -> child
    # Связь родителя хранится в виде: родитель -> ребёнок
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


# --- get_children ----------------------------------------
def get_children(person_id):
    """Return all children of the selected person."""

    conn = get_db()
    cur = conn.cursor()

    # Child relation is derived from stored parent -> child records
    # Дети определяются на основе сохранённых связей родитель -> ребёнок
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


# --- get_spouses -----------------------------------------
def get_spouses(person_id):
    """Return all spouses of the selected person."""

    conn = get_db()
    cur = conn.cursor()

    # Spouse relation is symmetric, so check both directions
    # Связь супругов симметрична, поэтому нужно проверять оба направления
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


# --- get_siblings ----------------------------------------
def get_siblings(person_id):
    """Return all siblings of the selected person."""

    # Two people are siblings if they share at least one parent
    # Два человека считаются siblings, если у них есть хотя бы один общий родитель
    parents = get_parents(person_id)
    if not parents:
        return []

    seen = {}
    for parent in parents:
        children = get_children(parent["id"])
        for child in children:
            if child["id"] == person_id:
                continue

            # Deduplicate by person id while keeping the full row
            # Убирать дубликаты по id, сохраняя полную запись
            seen[child["id"]] = child

    return list(seen.values())


# --- get_grandparents ------------------------------------
def get_grandparents(person_id):
    """Return all grandparents of the selected person."""

    # Grandparents are the parents of the person's parents
    # Бабушки и дедушки — это родители родителей выбранного человека
    parents = get_parents(person_id)
    if not parents:
        return []

    seen = {}
    for parent in parents:
        gps = get_parents(parent["id"])
        for gp in gps:
            seen[gp["id"]] = gp

    return list(seen.values())


# --- get_uncles_aunts ------------------------------------
def get_uncles_aunts(person_id):
    """Return all uncles and aunts of the selected person."""

    conn = get_db()
    cur = conn.cursor()

    # First load the parents of the current person
    # Сначала загрузить родителей текущего человека
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

    # Uncles and aunts are siblings of the person's parents
    # Дяди и тёти — это братья и сёстры родителей выбранного человека
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

    # Exclude the parents themselves in case they appear in the result
    # Исключить самих родителей, если они случайно попали в результат
    result = [row for row in rows if row["id"] not in parent_ids]

    conn.close()
    return result


# --- get_nephews_nieces ----------------------------------
def get_nephews_nieces(person_id):
    """Return all nephews and nieces of the selected person."""

    conn = get_db()
    cur = conn.cursor()

    # First load the siblings of the current person
    # Сначала загрузить братьев и сестёр текущего человека
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

    # Nephews and nieces are the children of the person's siblings
    # Племянники и племянницы — это дети братьев и сестёр выбранного человека
    rows = cur.execute(f"""
        SELECT DISTINCT p.*
        FROM relationships r
        JOIN persons p ON p.id = r.relative_id
        WHERE r.relation_type = 'parent'
          AND r.person_id IN ({placeholders})
    """, tuple(sibling_ids)).fetchall()

    conn.close()
    return rows


# --- get_cousins -----------------------------------------
def get_cousins(person_id):
    """Return all cousins of the selected person."""

    conn = get_db()
    cur = conn.cursor()

    # First load the person's parents
    # Сначала загрузить родителей выбранного человека
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

    # Cousins are the children of the person's uncles and aunts
    # Двоюродные братья и сёстры — это дети дядь и тёть выбранного человека
    uncles_aunts = cur.execute(f"""
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

    if not uncles_aunts:
        conn.close()
        return []

    ua_ids = [u["id"] for u in uncles_aunts]
    ua_placeholders = ",".join("?" for _ in ua_ids)

    cousins = cur.execute(f"""
        SELECT DISTINCT p.*
        FROM relationships r
        JOIN persons p ON p.id = r.relative_id
        WHERE r.relation_type = 'parent'
          AND r.person_id IN ({ua_placeholders})
    """, tuple(ua_ids)).fetchall()

    # Exclude the current person if inconsistent data causes them to appear
    # Исключить текущего человека, если из-за некорректных данных он попал в результат
    result = [c for c in cousins if c["id"] != person_id]

    conn.close()
    return result


# --- get_ancestors_by_level ------------------------------
def get_ancestors_by_level(person_id, level):
    """Return ancestors at one exact level above the selected person."""

    # Level 1 = parents, level 2 = grandparents, level 3 = great-grandparents, etc.
    # Уровень 1 = родители, уровень 2 = бабушки/дедушки, уровень 3 = прародители и так далее
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

        # Move one generation upward by following parent relations
        # Подняться на одно поколение вверх по связям parent
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


# --- get_great_grandparents ------------------------------
def get_great_grandparents(person_id):
    """Return great-grandparents of the selected person."""
    return get_ancestors_by_level(person_id, 3)


# --- get_great_great_grandparents ------------------------
def get_great_great_grandparents(person_id):
    """Return great-great-grandparents of the selected person."""
    return get_ancestors_by_level(person_id, 4)


# --- get_ancestors ---------------------------------------
def get_ancestors(person_id, min_level=5, max_level=10):
    """Return all more distant ancestors within the specified level range."""

    # Group far ancestors into one list instead of creating endless named generations
    # Объединить дальних предков в один список вместо бесконечного перечисления поколений
    all_ancestors = []
    seen_ids = set()

    for level in range(min_level, max_level + 1):
        rows = get_ancestors_by_level(person_id, level)
        for row in rows:
            if row["id"] not in seen_ids:
                seen_ids.add(row["id"])
                all_ancestors.append(row)

    return all_ancestors