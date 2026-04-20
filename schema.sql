CREATE TABLE IF NOT EXISTS persons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name TEXT NOT NULL,
    middle_name TEXT,
    last_name TEXT,
    maiden_name TEXT,
    birth_date TEXT,
    death_date TEXT,
    birth_year INTEGER,
    birth_month INTEGER,
    birth_day INTEGER,
    death_year INTEGER,
    death_month INTEGER,
    death_day INTEGER,
    gender TEXT,
    notes TEXT,
    photo_filename TEXT,
    tree_id INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id INTEGER NOT NULL,
    relative_id INTEGER NOT NULL,
    relation_type TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (person_id) REFERENCES persons(id),
    FOREIGN KEY (relative_id) REFERENCES persons(id)
);

CREATE TABLE IF NOT EXISTS person_photos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id INTEGER NOT NULL,
    filename TEXT NOT NULL,
    uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (person_id) REFERENCES persons(id)
);