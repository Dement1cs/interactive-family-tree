import os
import uuid
import json
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, url_for, jsonify, abort
from db import(
    get_db,
    init_db, 
    get_all_persons, 
    count_persons_in_tree,
    add_person, 
    get_person,
    update_person,
    update_person_photo,
    remove_person_photo,
    add_gallery_photo,
    get_person_photos,
    get_gallery_photo,
    delete_gallery_photo,
    delete_person,
    delete_tree_data,
    add_relationship,
    relationship_exists,
    delete_relationship,
    get_parents,
    get_children,
    get_spouses,
    get_siblings,
    get_uncles_aunts,
    get_grandparents,
    get_great_grandparents,
    get_great_great_grandparents,
    get_ancestors,
    search_persons
    )
from extensions import db, migrate, login_manager, csrf

from models import User, Tree, TreeAccess, TreeSnapshot
from flask_login import login_user, logout_user, login_required, current_user
from forms import RegisterForm, LoginForm


# Основное приложение Flask
app = Flask(__name__)

#======== РЕГЕСТРАЦИЯ =============================
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
#==================================================

#==images===============
app.config["UPLOAD_FOLDER"] = os.path.join("static", "uploads")
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
#=======================

db.init_app(app)
migrate.init_app(app, db)
login_manager.init_app(app)
csrf.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def get_current_user_tree_or_404(tree_id):
    return require_tree_view_access(tree_id)

#=== Запросить роль для текущего юзера ========================================
def get_tree_role_for_current_user(tree_id):
    if not tree_id:
        return None

    tree = Tree.query.filter_by(id=tree_id).first()
    if tree is None:
        return None

    if tree.owner_user_id == current_user.id:
        return "owner"

    access = TreeAccess.query.filter_by(
        tree_id=tree.id,
        user_id=current_user.id
    ).first()

    if access:
        return access.role

    return None
#===========================================

#==== запросить просмотр ===================
def require_tree_view_access(tree_id):
    tree = Tree.query.filter_by(id=tree_id).first()
    if tree is None:
        abort(404)

    role = get_tree_role_for_current_user(tree_id)
    if role not in {"owner", "editor", "viewer"}:
        abort(404)

    return tree
#===========================================

#==== запросить едитор ===================
def require_tree_edit_access(tree_id):
    tree = Tree.query.filter_by(id=tree_id).first()
    if tree is None:
        abort(404)

    role = get_tree_role_for_current_user(tree_id)
    if role not in {"owner", "editor"}:
        abort(403)

    return tree
#===========================================

def to_int_or_none(value):
    value = (value or "").strip()
    return int(value) if value else None

# better looks date -------------------------
MONTH_NAMES = {
    1: "January", 2: "February", 3: "March", 4: "April",
    5: "May", 6: "June", 7: "July", 8: "August",
    9: "September", 10: "October", 11: "November", 12: "December"
}

def format_partial_date(year=None, month=None, day=None, fallback=None):
    month_name = MONTH_NAMES.get(int(month), str(month)) if month else None

    if day and month and year:
        return f"{int(day)} {month_name} {year}"

    if month and year:
        return f"{month_name} {year}"

    if year:
        return str(year)

    if day and month:
        return f"{int(day)} {month_name}"

    if month:
        return str(month_name)

    if day:
        return str(day)

    return fallback or ""

#======image helper function================
def allowed_image_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS
#===========================================

#=========================================================================
def get_person_in_tree_or_404(person_id, tree_id):
    person = get_person(person_id)
    if person is None:
        abort(404)

    if str(person["tree_id"]) != str(tree_id):
        abort(404)

    return person
#=========================================================================

#======= snapshot of tree ==================================================================
def build_tree_snapshot_data(tree_id):
    tree = Tree.query.filter_by(id=tree_id).first()
    if tree is None:
        return None

    conn = get_db()

    persons = conn.execute("""
        SELECT *
        FROM persons
        WHERE tree_id = ?
        ORDER BY id
    """, (tree_id,)).fetchall()

    relationships = conn.execute("""
        SELECT r.person_id, r.relative_id, r.relation_type
        FROM relationships r
        JOIN persons p1 ON r.person_id = p1.id
        JOIN persons p2 ON r.relative_id = p2.id
        WHERE p1.tree_id = ? AND p2.tree_id = ?
        ORDER BY r.person_id, r.relative_id
    """, (tree_id, tree_id)).fetchall()

    person_photos = conn.execute("""
        SELECT pp.*
        FROM person_photos pp
        JOIN persons p ON pp.person_id = p.id
        WHERE p.tree_id = ?
        ORDER BY pp.id
    """, (tree_id,)).fetchall()

    conn.close()

    snapshot_data = {
        "tree": {
            "id": tree.id,
            "title": tree.title
        },
        "persons": [dict(p) for p in persons],
        "relationships": [dict(r) for r in relationships],
        "person_photos": [dict(pp) for pp in person_photos]
    }

    return json.dumps(snapshot_data)
#=========================================================================

#======== restore tree =================================================================
def restore_tree_from_snapshot(tree_id, snapshot_json):
    data = json.loads(snapshot_json)

    persons = data.get("persons", [])
    relationships = data.get("relationships", [])
    person_photos = data.get("person_photos", [])

    conn = get_db()
    cur = conn.cursor()

    # удалить связи текущего дерева
    cur.execute("""
        DELETE FROM relationships
        WHERE person_id IN (SELECT id FROM persons WHERE tree_id = ?)
           OR relative_id IN (SELECT id FROM persons WHERE tree_id = ?)
    """, (tree_id, tree_id))

    # удалить photos текущего дерева
    cur.execute("""
        DELETE FROM person_photos
        WHERE person_id IN (SELECT id FROM persons WHERE tree_id = ?)
    """, (tree_id,))

    # удалить persons текущего дерева
    cur.execute("""
        DELETE FROM persons
        WHERE tree_id = ?
    """, (tree_id,))

    # восстановить persons с теми же id
    for p in persons:
        cur.execute("""
            INSERT INTO persons (
                id,
                first_name,
                middle_name,
                last_name,
                maiden_name,
                birth_date,
                death_date,
                birth_year,
                birth_month,
                birth_day,
                death_year,
                death_month,
                death_day,
                gender,
                notes,
                photo_filename,
                tree_id,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            p.get("id"),
            p.get("first_name"),
            p.get("middle_name"),
            p.get("last_name"),
            p.get("maiden_name"),
            p.get("birth_date"),
            p.get("death_date"),
            p.get("birth_year"),
            p.get("birth_month"),
            p.get("birth_day"),
            p.get("death_year"),
            p.get("death_month"),
            p.get("death_day"),
            p.get("gender"),
            p.get("notes"),
            p.get("photo_filename"),
            tree_id,
            p.get("created_at"),
        ))

    # восстановить person_photos
    for pp in person_photos:
        cur.execute("""
            INSERT INTO person_photos (
                id,
                person_id,
                filename,
                uploaded_at
            )
            VALUES (?, ?, ?, ?)
        """, (
            pp.get("id"),
            pp.get("person_id"),
            pp.get("filename"),
            pp.get("uploaded_at"),
        ))

    # восстановить relationships
    for r in relationships:
        cur.execute("""
            INSERT INTO relationships (
                person_id,
                relative_id,
                relation_type
            )
            VALUES (?, ?, ?)
        """, (
            r.get("person_id"),
            r.get("relative_id"),
            r.get("relation_type"),
        ))

    conn.commit()
    conn.close()
#=========================================================================

@app.context_processor
def inject_helpers():
    return dict(format_partial_date=format_partial_date)

#======== register роут =============================
@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    form = RegisterForm()
    if form.validate_on_submit():
        email = form.email.data.lower().strip()

        # проверка что email не занят
        existing = User.query.filter_by(email=email).first()
        if existing:
            form.email.errors.append("This email is already registered.")
            return render_template("register.html", form=form)

        user = User(email=email)
        user.set_password(form.password.data)

        db.session.add(user)
        db.session.commit()

        login_user(user)
        return redirect(url_for("dashboard"))

    return render_template("register.html", form=form)
#========================================================

#======== login роут =============================
@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.lower().strip()
        user = User.query.filter_by(email=email).first()

        if user is None or not user.check_password(form.password.data):
            form.password.errors.append("Invalid email or password.")
            return render_template("login.html", form=form)

        login_user(user, remember=form.remember.data)
        next_url = request.args.get("next")
        return redirect(next_url or url_for("dashboard"))

    return render_template("login.html", form=form)
#========================================================

#======== logout роут =============================
@app.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))
#========================================================

# ====== Главная страница ================================
@app.route("/")
def index():
    return render_template("index.html")
# ========================================================

# ====== Тут дерево =================================
@app.route("/tree")
@login_required
def tree():
    tree_id = request.args.get("tree_id")
    if not tree_id:
        return redirect(url_for("dashboard"))

    current_tree = get_current_user_tree_or_404(tree_id)

    tree_title = current_tree.title if current_tree and current_tree.title else "family-tree"

    return render_template(
        "tree.html",
        tree_id=tree_id,
        current_tree=current_tree,
        tree_title=tree_title
    )
# =========================================================

# ====== Список всех людей =================================
@app.route("/persons")
@login_required
def persons():
    tree_id = request.args.get("tree_id")
    if not tree_id:
        return redirect(url_for("dashboard"))

    current_tree = get_current_user_tree_or_404(tree_id)
    people = get_all_persons(tree_id)

    return render_template("persons.html", people=people, tree_id=tree_id, current_tree=current_tree)
# ==========================================================

# ====== ДОБАВИТЬ ЧЕЛОВЕКА =================================
@app.route('/persons/add', methods=["GET", "POST"])
@login_required
def add_person_route():
    tree_id = request.args.get("tree_id")
    current_tree = require_tree_edit_access(tree_id)

    if request.method == "POST":
        first_name = request.form.get("first_name")
        middle_name = request.form.get("middle_name") or None
        last_name = request.form.get("last_name") or None
        maiden_name = request.form.get("maiden_name") or None
        birth_date = request.form.get("birth_date") or None
        death_date = request.form.get("death_date") or None

        birth_year = to_int_or_none(request.form.get("birth_year"))
        birth_month = to_int_or_none(request.form.get("birth_month"))
        birth_day = to_int_or_none(request.form.get("birth_day"))

        death_year = to_int_or_none(request.form.get("death_year"))
        death_month = to_int_or_none(request.form.get("death_month"))
        death_day = to_int_or_none(request.form.get("death_day"))

        gender = request.form.get("gender") or None
        notes = request.form.get("notes") or None

        if not first_name:
            return "First name is required", 400
        
        add_person(
            first_name,
            middle_name,
            last_name,
            maiden_name,
            birth_date,
            death_date,
            birth_year, birth_month, birth_day,
            death_year, death_month, death_day,
            gender,
            notes,
            tree_id
        )
        return redirect(url_for("persons", tree_id=tree_id))

    return render_template("person_add.html", tree_id=tree_id)
# =========================================================

# ====== ДЕТАЛИ ПРОФИЛЬ ЧЕЛОВЕКА ===========================
@app.route("/persons/<int:person_id>")
@login_required
def person_detail(person_id):
    tree_id = request.args.get("tree_id")
    tree_role = get_tree_role_for_current_user(tree_id)
    current_tree = get_current_user_tree_or_404(tree_id)

    person = get_person_in_tree_or_404(person_id, tree_id)
    photos = get_person_photos(person_id)

    parents = get_parents(person_id)
    children = get_children(person_id)
    spouses = get_spouses(person_id)
    siblings = get_siblings(person_id)
    uncles_aunts = get_uncles_aunts(person_id)
    grandparents = get_grandparents(person_id)
    great_grandparents = get_great_grandparents(person_id)
    great_great_grandparents = get_great_great_grandparents(person_id)
    ancestors = get_ancestors(person_id)

    return render_template(
        "person_detail.html",
        person=person,
        parents=parents,
        children=children,
        spouses=spouses,
        siblings=siblings,
        uncles_aunts=uncles_aunts,
        grandparents=grandparents,
        great_grandparents=great_grandparents,
        great_great_grandparents=great_great_grandparents,
        ancestors=ancestors,
        photos=photos,
        tree_id=tree_id,
        tree_role=tree_role
    )
# ==========================================================

# ====== Редактирование данных человека ===================
@app.route("/persons/<int:person_id>/edit", methods=["GET", "POST"])
@login_required
def edit_person(person_id):
    tree_id = request.args.get("tree_id")
    current_tree = require_tree_edit_access(tree_id)

    person = get_person_in_tree_or_404(person_id, tree_id)
    
    if request.method == "POST":
        first_name = request.form.get("first_name")
        middle_name = request.form.get("middle_name") or None
        last_name = request.form.get("last_name") or None
        maiden_name = request.form.get("maiden_name") or None
        birth_date = request.form.get("birth_date") or None
        death_date = request.form.get("death_date") or None

        birth_year = to_int_or_none(request.form.get("birth_year"))
        birth_month = to_int_or_none(request.form.get("birth_month"))
        birth_day = to_int_or_none(request.form.get("birth_day"))

        death_year = to_int_or_none(request.form.get("death_year"))
        death_month = to_int_or_none(request.form.get("death_month"))
        death_day = to_int_or_none(request.form.get("death_day"))

        gender = request.form.get("gender") or None
        notes = request.form.get("notes") or None

        if not first_name:
            return "First name is required", 400
        
        update_person(
            person_id,
            first_name,
            middle_name,
            last_name,
            maiden_name,
            birth_date,
            death_date,
            birth_year, birth_month, birth_day,
            death_year, death_month, death_day,
            gender,
            notes
        )
        return redirect(url_for("person_detail", person_id=person_id, tree_id=tree_id))
    
    return render_template("person_edit.html", person=person, tree_id=tree_id)
# ======================================================

# ====== Добавление связи ========================
@app.route("/persons/<int:person_id>/relations/add", methods=["GET", "POST"])
@login_required
def add_relation(person_id):
    tree_id = request.args.get("tree_id")
    current_tree = require_tree_edit_access(tree_id)
    preset_relation_type = request.args.get("relation_type")

    person = get_person_in_tree_or_404(person_id, tree_id)

    people = [p for p in get_all_persons(tree_id) if p["id"] != person_id]
    error = None

    if request.method == "POST":
        relation_type = request.form.get("relation_type")
        relative_id = request.form.get("relative_id")

        if not relation_type or not relative_id:
            error = "Relation type and person are required."
            return render_template(
                "relation_add.html",
                person=person,
                people=people,
                tree_id=tree_id,
                error=error,
                preset_relation_type=preset_relation_type
            ), 400

        try:
            relative_id = int(relative_id)
        except ValueError:
            error = "Invalid person selected."
            return render_template(
                "relation_add.html",
                person=person,
                people=people,
                tree_id=tree_id,
                error=error,
                preset_relation_type=preset_relation_type
            ), 400

        if relative_id == person_id:
            error = "You cannot create a relation with the same person."
            return render_template(
                "relation_add.html",
                person=person,
                people=people,
                tree_id=tree_id,
                error=error,
                preset_relation_type=preset_relation_type
            ), 400

        if relation_type == "parent":
            if relationship_exists(relative_id, person_id, "parent"):
                error = "This parent relation already exists."
                return render_template(
                    "relation_add.html",
                    person=person,
                    people=people,
                    tree_id=tree_id,
                    error=error,
                    preset_relation_type=preset_relation_type
                ), 400

            add_relationship(
                person_id=relative_id,
                relative_id=person_id,
                relation_type="parent"
            )

        elif relation_type == "child":
            if relationship_exists(person_id, relative_id, "parent"):
                error = "This child relation already exists."
                return render_template(
                    "relation_add.html",
                    person=person,
                    people=people,
                    tree_id=tree_id,
                    error=error,
                    preset_relation_type=preset_relation_type
                ), 400

            add_relationship(
                person_id=person_id,
                relative_id=relative_id,
                relation_type="parent"
            )

        elif relation_type == "spouse":
            if relationship_exists(person_id, relative_id, "spouse"):
                error = "This spouse relation already exists."
                return render_template(
                    "relation_add.html",
                    person=person,
                    people=people,
                    tree_id=tree_id,
                    error=error,
                    preset_relation_type=preset_relation_type
                ), 400

            add_relationship(
                person_id=person_id,
                relative_id=relative_id,
                relation_type="spouse"
            )
            add_relationship(
                person_id=relative_id,
                relative_id=person_id,
                relation_type="spouse"
            )
        else:
            error = "Unknown relation type."
            return render_template(
                "relation_add.html",
                person=person,
                people=people,
                tree_id=tree_id,
                error=error,
                preset_relation_type=preset_relation_type
            ), 400

        return redirect(url_for("person_detail", person_id=person_id, tree_id=tree_id))

    return render_template(
        "relation_add.html",
        person=person,
        people=people,
        tree_id=tree_id,
        error=error,
        preset_relation_type=preset_relation_type
    )
# ==================================================

# ====== Удаление связи ============================
@app.route("/persons/<int:person_id>/relations/delete", methods=["POST"])
@login_required
def delete_relation(person_id):
    tree_id = request.args.get("tree_id")
    current_tree = require_tree_edit_access(tree_id)
    person = get_person_in_tree_or_404(person_id, tree_id)

    relative_id = request.form.get("relative_id")
    relation_type = request.form.get("relation_type")

    if not relative_id or not relation_type:
        return "Missing relation data", 400

    try:
        relative_id = int(relative_id)
    except ValueError:
        return "Invalid relative id", 400

    delete_relationship(person_id, relative_id, relation_type)

    return redirect(url_for("person_detail", person_id=person_id, tree_id=tree_id))
# ==================================================

# ====== Удаление человека ======
@app.route("/persons/<int:person_id>/delete", methods=["POST"])
@login_required
def delete_person_route(person_id):
    tree_id = request.args.get("tree_id")
    current_tree = require_tree_edit_access(tree_id)

    person = get_person_in_tree_or_404(person_id, tree_id)
    
    delete_person(person_id)
    return redirect(url_for("persons", tree_id=tree_id))
# =============================

# === photo upload route ==========================
@app.route("/persons/<int:person_id>/photo/upload", methods=["POST"])
@login_required
def upload_person_photo_route(person_id):
    tree_id = request.args.get("tree_id")
    current_tree = require_tree_edit_access(tree_id)

    person = get_person_in_tree_or_404(person_id, tree_id)

    file = request.files.get("photo")
    if not file or not file.filename:
        return "No file selected", 400

    if not allowed_image_file(file.filename):
        return "Invalid image format", 400

    # удалить старое фото с диска, если было
    old_filename = person["photo_filename"]
    if old_filename:
        old_path = os.path.join(app.config["UPLOAD_FOLDER"], old_filename)
        if os.path.exists(old_path):
            os.remove(old_path)

    ext = file.filename.rsplit(".", 1)[1].lower()
    filename = secure_filename(f"person_{person_id}_{uuid.uuid4().hex}.{ext}")
    save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)

    file.save(save_path)
    update_person_photo(person_id, filename)

    return redirect(url_for("person_detail", person_id=person_id, tree_id=tree_id))
# ===================================================================

# === photo delete route ==========================
@app.route("/persons/<int:person_id>/photo/delete", methods=["POST"])
@login_required
def delete_person_photo_route(person_id):
    tree_id = request.args.get("tree_id")
    current_tree = require_tree_edit_access(tree_id)

    person = get_person_in_tree_or_404(person_id, tree_id)

    filename = person["photo_filename"]
    if filename:
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        if os.path.exists(file_path):
            os.remove(file_path)

    remove_person_photo(person_id)

    return redirect(url_for("person_detail", person_id=person_id, tree_id=tree_id))


# ===== uploading photos to the gallery =============================
@app.route("/persons/<int:person_id>/gallery/upload", methods=["POST"])
@login_required
def upload_gallery_photo_route(person_id):
    tree_id = request.args.get("tree_id")
    current_tree = require_tree_edit_access(tree_id)

    person = get_person_in_tree_or_404(person_id, tree_id)

    file = request.files.get("gallery_photo")
    if not file or not file.filename:
        return "No file selected", 400

    if not allowed_image_file(file.filename):
        return "Invalid image format", 400

    ext = file.filename.rsplit(".", 1)[1].lower()
    filename = secure_filename(f"gallery_{person_id}_{uuid.uuid4().hex}.{ext}")
    save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)

    file.save(save_path)
    add_gallery_photo(person_id, filename)

    return redirect(url_for("person_detail", person_id=person_id, tree_id=tree_id))
# ===================================================================

# ======= Delete from gallery ============================================================
@app.route("/persons/<int:person_id>/gallery/<int:photo_id>/delete", methods=["POST"])
@login_required
def delete_gallery_photo_route(person_id, photo_id):
    tree_id = request.args.get("tree_id")
    current_tree = require_tree_edit_access(tree_id)

    person = get_person_in_tree_or_404(person_id, tree_id)

    photo = get_gallery_photo(photo_id)
    if photo is None or photo["person_id"] != person_id:
        return "Photo not found", 404

    file_path = os.path.join(app.config["UPLOAD_FOLDER"], photo["filename"])
    if os.path.exists(file_path):
        os.remove(file_path)

    delete_gallery_photo(photo_id)

    return redirect(url_for("person_detail", person_id=person_id, tree_id=tree_id))
# ===================================================================


# ====== DASHBOARD ==================================================
# --------показывает список деревьев текущего пользователя-----------
@app.route("/dashboard")
@login_required
def dashboard():
    owned_trees = Tree.query.filter_by(owner_user_id=current_user.id).order_by(Tree.created_at.desc()).all()

    shared_entries = TreeAccess.query.filter_by(user_id=current_user.id).all()
    shared_trees = [entry.tree for entry in shared_entries]

    owned_tree_cards = []
    for t in owned_trees:
        owned_tree_cards.append({
            "id": t.id,
            "title": t.title,
            "person_count": count_persons_in_tree(t.id)
        })

    shared_tree_cards = []
    for t in shared_trees:
        shared_tree_cards.append({
            "id": t.id,
            "title": t.title,
            "person_count": count_persons_in_tree(t.id),
            "owner_email": t.owner.email if t.owner else None
        })

    return render_template(
        "dashboard.html",
        trees=owned_tree_cards,
        shared_trees=shared_tree_cards
    )
# -------------------------------------------------------------------

# ----- создаёт новое дерево (POST) и возвращает на dashboard -------
@app.route("/trees/create", methods=["POST"])
@login_required
def create_tree():
    title = request.form.get("title", "").strip() or "My Family Tree"
    t = Tree(title=title, owner_user_id=current_user.id)
    db.session.add(t)
    db.session.commit()
    return redirect(url_for("dashboard"))
# -------------------------------------------------------------------

# -------- Rename -----------------------------------------------
@app.route("/trees/<int:tree_id>/edit", methods=["GET", "POST"])
@login_required
def edit_tree(tree_id):
    tree = Tree.query.filter_by(id=tree_id, owner_user_id=current_user.id).first()
    if tree is None:
        return "Tree not found", 404

    if request.method == "POST":
        title = request.form.get("title", "").strip()

        if not title:
            return "Tree title is required", 400

        tree.title = title
        db.session.commit()

        return redirect(url_for("dashboard"))

    return render_template("tree_edit.html", tree=tree)
# -------------------------------------------------------------------

# ----------- Удалить дерево ----------------------------------------
@app.route("/trees/<int:tree_id>/delete", methods=["POST"])
@login_required
def delete_tree_route(tree_id):
    tree = Tree.query.filter_by(id=tree_id, owner_user_id=current_user.id).first()
    if tree is None:
        return "Tree not found", 404

    # удалить людей и связи этого дерева из database.db
    delete_tree_data(tree_id)

    # удалить само дерево из app.db
    db.session.delete(tree)
    db.session.commit()

    return redirect(url_for("dashboard"))
# -------------------------------------------------------------------
# ===================================================================

#======= create snapshot ==================================================================
@app.route("/trees/<int:tree_id>/snapshots/create", methods=["POST"])
@login_required
def create_tree_snapshot(tree_id):
    tree = Tree.query.filter_by(id=tree_id, owner_user_id=current_user.id).first()
    if tree is None:
        return "Tree not found", 404

    snapshot_json = build_tree_snapshot_data(tree.id)
    if snapshot_json is None:
        return "Could not create snapshot", 400

    snapshot = TreeSnapshot(
        tree_id=tree.id,
        created_by_user_id=current_user.id,
        title=f"{tree.title} snapshot",
        snapshot_json=snapshot_json
    )

    db.session.add(snapshot)
    db.session.commit()

    return redirect(url_for("list_tree_snapshots", tree_id=tree.id))
# =========================================================================================

#======= list snapshots ==================================================================
@app.route("/trees/<int:tree_id>/snapshots")
@login_required
def list_tree_snapshots(tree_id):
    tree = Tree.query.filter_by(id=tree_id, owner_user_id=current_user.id).first()
    if tree is None:
        return "Tree not found", 404

    snapshots = TreeSnapshot.query.filter_by(tree_id=tree.id) \
        .order_by(TreeSnapshot.created_at.desc()) \
        .all()

    return render_template(
        "tree_snapshots.html",
        tree=tree,
        snapshots=snapshots
    )
# =========================================================================================

#======= restore snapshot ==================================================================
@app.route("/trees/<int:tree_id>/snapshots/<int:snapshot_id>/restore", methods=["POST"])
@login_required
def restore_tree_snapshot(tree_id, snapshot_id):
    tree = Tree.query.filter_by(id=tree_id, owner_user_id=current_user.id).first()
    if tree is None:
        return "Tree not found", 404

    snapshot = TreeSnapshot.query.filter_by(id=snapshot_id, tree_id=tree.id).first()
    if snapshot is None:
        return "Snapshot not found", 404

    restore_tree_from_snapshot(tree.id, snapshot.snapshot_json)

    return redirect(url_for("tree", tree_id=tree.id))
# =========================================================================================

# ======= delelte snapshot ==================================================================================
@app.route("/trees/<int:tree_id>/snapshots/<int:snapshot_id>/delete", methods=["POST"])
@login_required
def delete_tree_snapshot(tree_id, snapshot_id):
    tree = Tree.query.filter_by(id=tree_id, owner_user_id=current_user.id).first()
    if tree is None:
        return "Tree not found", 404

    snapshot = TreeSnapshot.query.filter_by(id=snapshot_id, tree_id=tree.id).first()
    if snapshot is None:
        return "Snapshot not found", 404

    db.session.delete(snapshot)
    db.session.commit()

    return redirect(url_for("list_tree_snapshots", tree_id=tree.id))
# =========================================================================================

# ====== manage access rout =============================================================
@app.route("/trees/<int:tree_id>/access", methods=["GET", "POST"])
@login_required
def manage_tree_access(tree_id):
    tree = Tree.query.filter_by(id=tree_id, owner_user_id=current_user.id).first()
    if tree is None:
        return "Tree not found", 404

    error = None

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        role = request.form.get("role", "editor").strip().lower()

        if role not in {"editor", "viewer"}:
            role = "editor"

        if not email:
            error = "Email is required."
        else:
            user = User.query.filter_by(email=email).first()

            if user is None:
                error = "User not found."
            elif user.id == current_user.id:
                error = "You already own this tree."
            else:
                existing = TreeAccess.query.filter_by(tree_id=tree.id, user_id=user.id).first()
                if existing:
                    error = "This user already has access."
                else:
                    access = TreeAccess(tree_id=tree.id, user_id=user.id, role=role)
                    db.session.add(access)
                    db.session.commit()
                    return redirect(url_for("manage_tree_access", tree_id=tree.id))
    shared_entries = TreeAccess.query.filter_by(tree_id=tree.id).all()

    return render_template(
        "tree_access.html",
        tree=tree,
        shared_entries=shared_entries,
        error=error
    )
# ===================================================================

# ====== remove access rout =============================================================
@app.route("/trees/<int:tree_id>/access/<int:access_id>/delete", methods=["POST"])
@login_required
def remove_tree_access(tree_id, access_id):
    tree = Tree.query.filter_by(id=tree_id, owner_user_id=current_user.id).first()
    if tree is None:
        return "Tree not found", 404

    access = TreeAccess.query.filter_by(id=access_id, tree_id=tree.id).first()
    if access is None:
        return "Access entry not found", 404

    db.session.delete(access)
    db.session.commit()

    return redirect(url_for("manage_tree_access", tree_id=tree.id))
# ===================================================================

# ====== update access rout =============================================================
@app.route("/trees/<int:tree_id>/access/<int:access_id>/role", methods=["POST"])
@login_required
def update_tree_access_role(tree_id, access_id):
    tree = Tree.query.filter_by(id=tree_id, owner_user_id=current_user.id).first()
    if tree is None:
        return "Tree not found", 404

    access = TreeAccess.query.filter_by(id=access_id, tree_id=tree.id).first()
    if access is None:
        return "Access entry not found", 404

    new_role = request.form.get("role", "").strip().lower()
    if new_role not in {"editor", "viewer"}:
        return "Invalid role", 400

    access.role = new_role
    db.session.commit()

    return redirect(url_for("manage_tree_access", tree_id=tree.id))
# ===================================================================








# ======API==========================================================
# ===================================================================


# ==========API Поиск ============
@app.route("/api/persons/search")
@login_required
def api_person_search():
    q = request.args.get("q", "").strip()
    tree_id = request.args.get("tree_id")
    exclude_id = request.args.get("exclude_id")

    if not q:
        return jsonify([])

    current_tree = get_current_user_tree_or_404(tree_id)

    try:
        exclude_id = int(exclude_id) if exclude_id else None
    except ValueError:
        exclude_id = None

    results = search_persons(q, tree_id=tree_id, exclude_id=exclude_id, limit=20)

    return jsonify([dict(r) for r in results])
# ================================

# ======API tree==========================================
@app.route("/api/tree")
@login_required
def api_tree():
    conn = get_db()
    tree_id = request.args.get("tree_id")
    if not tree_id:
        conn.close()
        return jsonify({"persons": [], "relationships": []})

    current_tree = get_current_user_tree_or_404(tree_id)

    persons = conn.execute("""
        SELECT id, first_name, middle_name, last_name, maiden_name,
            birth_date, death_date,
            birth_year, birth_month, birth_day,
            death_year, death_month, death_day,
            notes, tree_id
        FROM persons
        WHERE tree_id = ?
    """, (tree_id,)).fetchall()

    relationships = conn.execute("""
        SELECT r.person_id, r.relative_id, r.relation_type
        FROM relationships r
        JOIN persons p1 ON r.person_id = p1.id
        JOIN persons p2 ON r.relative_id = p2.id
        WHERE p1.tree_id = ? AND p2.tree_id = ?
    """, (tree_id, tree_id)).fetchall()

    conn.close()

    return jsonify({
        "persons": [dict(p) for p in persons],
        "relationships": [dict(r) for r in relationships]
    })
# ==============================================================


# ======API tables==========================================
@app.route("/api/tables")
@login_required
def api_tables():
    conn = get_db()
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    return jsonify([r["name"] if isinstance(r, dict) else r[0] for r in rows])
# ==============================================================

# ====== Инициализация базы данных ========
@app.route("/init-db")
@login_required
def init_db_route():
    init_db()
    return "Database initialized."
# =========================================

# Точка входа
if __name__ == "__main__":
    app.run(debug=True)