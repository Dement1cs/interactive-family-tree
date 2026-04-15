import os
from flask import Flask, render_template, request, redirect, url_for, jsonify, abort
from db import(
    get_db,
    init_db, 
    get_all_persons, 
    count_persons_in_tree,
    add_person, 
    get_person,
    update_person,
    delete_person,
    delete_tree_data,
    add_relationship,
    relationship_exists,
    delete_relationship,
    get_parents,
    get_children,
    get_spouses,
    get_siblings,
    get_grandparents,
    search_persons
    )
from extensions import db, migrate, login_manager, csrf

from models import User, Tree
from flask_login import login_user, logout_user, login_required, current_user
from forms import RegisterForm, LoginForm


# Основное приложение Flask
app = Flask(__name__)

#======== РЕГЕСТРАЦИЯ =============================
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)
migrate.init_app(app, db)
login_manager.init_app(app)
csrf.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def get_current_user_tree_or_404(tree_id):
    if not tree_id:
        return None

    tree = Tree.query.filter_by(id=tree_id, owner_user_id=current_user.id).first()
    if tree is None:
        abort(404)

    return tree

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
    if year:
        if month:
            month_name = MONTH_NAMES.get(int(month), str(month))
            if day:
                return f"{int(day)} {month_name} {year}"
            return f"{month_name} {year}"
        return str(year)
    return fallback or ""

@app.context_processor
def inject_helpers():
    return dict(format_partial_date=format_partial_date)
# better looks date end -------------------------

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
        return redirect(url_for("index"))

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
        next_url = request.args.get("next") # вернуть от куда пришел
        return redirect(next_url or url_for("index"))

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

    return render_template("tree.html", tree_id=tree_id, current_tree=current_tree)
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
    current_tree = get_current_user_tree_or_404(tree_id)

    if request.method == "POST":
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name") or None
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
            last_name,
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
    current_tree = get_current_user_tree_or_404(tree_id)

    person = get_person(person_id)
    if person is None:
        return "Person not found", 404
    parents = get_parents(person_id)
    children = get_children(person_id)
    spouses = get_spouses(person_id)
    siblings = get_siblings(person_id)
    grandparents = get_grandparents(person_id)

    return render_template(
        "person_detail.html", 
        person=person,
        parents=parents,
        children=children,
        spouses=spouses,
        siblings=siblings,
        grandparents=grandparents,
        tree_id=tree_id
    )
# ==========================================================

# ====== Редактирование данных человека ===================
@app.route("/persons/<int:person_id>/edit", methods=["GET", "POST"])
@login_required
def edit_person(person_id):
    tree_id = request.args.get("tree_id")
    current_tree = get_current_user_tree_or_404(tree_id)

    person = get_person(person_id)
    if person is None:
        return "Person is not found", 404
    
    if request.method == "POST":
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name") or None
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
            last_name,
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
    current_tree = get_current_user_tree_or_404(tree_id)
    preset_relation_type = request.args.get("relation_type")

    person = get_person(person_id)
    if person is None:
        return "Person not found", 404

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
    current_tree = get_current_user_tree_or_404(tree_id)

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
    current_tree = get_current_user_tree_or_404(tree_id)

    person = get_person(person_id)
    if person is None:
        return "Person not found", 404
    
    delete_person(person_id)
    return redirect(url_for("persons", tree_id=tree_id))
# =============================

# ====== DASHBOARD ==================================================
# --------показывает список деревьев текущего пользователя-----------
@app.route("/dashboard")
@login_required
def dashboard():
    trees = Tree.query.filter_by(owner_user_id=current_user.id).order_by(Tree.created_at.desc()).all()

    tree_cards = []
    for t in trees:
        tree_cards.append({
            "id": t.id,
            "title": t.title,
            "person_count": count_persons_in_tree(t.id)
        })

    return render_template("dashboard.html", trees=tree_cards)
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












# ======API==========================================================
# ===================================================================

# ======API persons=====================================================
@app.route("/api/persons")
@login_required
def api_persons():
    conn = get_db()
    persons = conn.execute("SELECT id, first_name, last_name, birth_date, death_date, notes FROM persons").fetchall()
    return jsonify([dict(p) for p in persons])
# =======================================


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

    if tree_id:
        persons = conn.execute("""
            SELECT id, first_name, last_name,
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
    else:
        persons = conn.execute("""
            SELECT id, first_name, last_name, birth_date, death_date, notes, tree_id
            FROM persons
        """).fetchall()

        relationships = conn.execute("""
            SELECT person_id, relative_id, relation_type
            FROM relationships
        """).fetchall()

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