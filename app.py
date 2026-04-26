# ========= imports ===================================================
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
    get_cousins,
    get_uncles_aunts,
    get_nephews_nieces,
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
# ============================================================






# =========================================================
# App config / setup
# =========================================================

# create the main Flask application instance
# Создать основной экземпляр Flask-приложения
app = Flask(__name__)

# core Flask / SQLAlchemy configuration
# Основная конфигурация Flask / SQLAlchemy
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# file upload configuration
# Настройки загрузки файлов
app.config["UPLOAD_FOLDER"] = os.path.join("static", "uploads")
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB

# allowed image extensions for profile and gallery uploads
# Разрешённые расширения изображений для фото профиля и галереи
ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

# ensure the uploads directory exists before saving files
# Убедиться, что папка uploads существует до сохранения файлов
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# initialize Flask extensions
# Инициализировать расширения Flask
db.init_app(app)
migrate.init_app(app, db)
login_manager.init_app(app)
csrf.init_app(app)



# =========================================================
# Login manager
# =========================================================
@login_manager.user_loader
def load_user(user_id):
    """Load the currently authenticated user from the SQLAlchemy database."""
    # Загрузить аутентифицированного пользователя по id для Flask-Login
    return db.session.get(User, int(user_id))



# auth helpers



# =========================================================
# Tree access helpers
# =========================================================

def get_current_user_tree_or_404(tree_id):
    """Return the tree if the current user can view it, otherwise abort."""
    # Вернуть дерево только если текущий пользователь имеет право его просматривать
    return require_tree_view_access(tree_id)


def get_tree_role_for_current_user(tree_id):
    """Return owner/editor/viewer role for the current user in a tree."""

    # No tree id means there is no role to resolve
    # Если tree_id не передан, определить роль невозможно
    if not tree_id:
        return None

    # Make sure the tree exists before checking permissions
    # Сначала убедиться, что дерево существует
    tree = Tree.query.filter_by(id=tree_id).first()
    if tree is None:
        return None

    # The tree owner always has full access
    # Владелец дерева всегда имеет полный доступ
    if tree.owner_user_id == current_user.id:
        return "owner"

    # Otherwise check the shared access table
    # Иначе проверить таблицу общего доступа
    access = TreeAccess.query.filter_by(
        tree_id=tree.id,
        user_id=current_user.id
    ).first()

    if access:
        return access.role

    return None


def require_tree_view_access(tree_id):
    """Abort unless the current user has view access to the tree."""

    # Make sure the tree exists
    # Убедиться, что дерево существует
    tree = Tree.query.filter_by(id=tree_id).first()
    if tree is None:
        abort(404)

    # Validate the user's role in this tree
    # Проверить роль пользователя в этом дереве
    role = get_tree_role_for_current_user(tree_id)
    if role not in {"owner", "editor", "viewer"}:
        abort(404)

    return tree


def require_tree_edit_access(tree_id):
    """Abort unless the current user can modify the tree."""

    # Make sure the tree exists
    # Убедиться, что дерево существует
    tree = Tree.query.filter_by(id=tree_id).first()
    if tree is None:
        abort(404)

    # Only owner and editor can modify tree data
    # Только owner и editor могут изменять данные дерева
    role = get_tree_role_for_current_user(tree_id)
    if role not in {"owner", "editor"}:
        abort(403)

    return tree


def get_person_in_tree_or_404(person_id, tree_id):
    """Ensure the requested person belongs to the selected tree."""

    # Load the requested person record
    # Загрузить запись о запрашиваемом человеке
    person = get_person(person_id)
    if person is None:
        abort(404)

    # Prevent access to a person from another tree via manual URL editing
    # Не допустить доступ к человеку из другого дерева через ручное изменение URL
    if str(person["tree_id"]) != str(tree_id):
        abort(404)

    return person



# =========================================================
# Formatting helpers
# =========================================================

def to_int_or_none(value):
    """Convert form input to int when provided, otherwise return None."""
    # Convert non-empty form values to int
    # Преобразовать непустое значение из формы в int
    value = (value or "").strip()
    return int(value) if value else None


# Month names used to display partial dates in a readable format
# Названия месяцев для отображения неполных дат в читаемом виде
MONTH_NAMES = {
    1: "January", 2: "February", 3: "March", 4: "April",
    5: "May", 6: "June", 7: "July", 8: "August",
    9: "September", 10: "October", 11: "November", 12: "December"
}

def format_partial_date(year=None, month=None, day=None, fallback=None):
    """Format partial dates such as 'March 1999' or '18 March'."""

    # Support incomplete dates because the user may know only part of the date
    # Поддерживать неполные даты, потому что пользователь может знать только часть даты
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

def allowed_image_file(filename):
    """Return True if the uploaded file has an allowed image extension."""
    # Check file extension before accepting uploaded image files
    # Проверить расширение файла перед загрузкой изображения
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

@app.context_processor
def inject_helpers():
    """Expose shared formatting helpers to Jinja templates."""
    # Make the date formatter available in all templates
    # Сделать форматтер дат доступным во всех шаблонах
    return dict(format_partial_date=format_partial_date)



# =========================================================
# Snapshot helpers
# =========================================================

def build_tree_snapshot_data(tree_id):
    """Build a full JSON snapshot of one tree, including people, relations and photos."""

    # Make sure the tree exists before building the snapshot
    # Сначала убедиться, что дерево существует
    tree = Tree.query.filter_by(id=tree_id).first()
    if tree is None:
        return None

    conn = get_db()

    # Read all people that belong to the selected tree
    # Считать всех людей, которые принадлежат выбранному дереву
    persons = conn.execute("""
        SELECT *
        FROM persons
        WHERE tree_id = ?
        ORDER BY id
    """, (tree_id,)).fetchall()

    # Read only relationships fully contained inside this tree
    # Считать только те связи, которые полностью принадлежат этому дереву
    relationships = conn.execute("""
        SELECT r.person_id, r.relative_id, r.relation_type
        FROM relationships r
        JOIN persons p1 ON r.person_id = p1.id
        JOIN persons p2 ON r.relative_id = p2.id
        WHERE p1.tree_id = ? AND p2.tree_id = ?
        ORDER BY r.person_id, r.relative_id
    """, (tree_id, tree_id)).fetchall()

    # Read gallery photo records linked to people in this tree
    # Считать записи фотографий, привязанных к людям из этого дерева
    person_photos = conn.execute("""
        SELECT pp.*
        FROM person_photos pp
        JOIN persons p ON pp.person_id = p.id
        WHERE p.tree_id = ?
        ORDER BY pp.id
    """, (tree_id,)).fetchall()

    conn.close()

    # Store the complete tree state as JSON so it can be restored later
    # Сохранить полное состояние дерева в JSON, чтобы его можно было восстановить позже
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


def restore_tree_from_snapshot(tree_id, snapshot_json):
    """Replace current tree data with the data stored in a snapshot."""

    # Decode snapshot JSON back into Python structures
    # Преобразовать JSON снапшота обратно в структуры Python
    data = json.loads(snapshot_json)

    persons = data.get("persons", [])
    relationships = data.get("relationships", [])
    person_photos = data.get("person_photos", [])

    conn = get_db()
    cur = conn.cursor()

    # Delete current relationships first, because they depend on person ids
    # Сначала удалить текущие связи, потому что они зависят от id людей
    cur.execute("""
        DELETE FROM relationships
        WHERE person_id IN (SELECT id FROM persons WHERE tree_id = ?)
           OR relative_id IN (SELECT id FROM persons WHERE tree_id = ?)
    """, (tree_id, tree_id))

    # Delete current photo records for all people in this tree
    # Удалить текущие записи фотографий для всех людей в этом дереве
    cur.execute("""
        DELETE FROM person_photos
        WHERE person_id IN (SELECT id FROM persons WHERE tree_id = ?)
    """, (tree_id,))

    # Delete all current people in the tree before restoring snapshot data
    # Удалить всех текущих людей в дереве перед восстановлением данных из снапшота
    cur.execute("""
        DELETE FROM persons
        WHERE tree_id = ?
    """, (tree_id,))

    # Reinsert people with original ids so relationships remain valid
    # Вставить людей с исходными id, чтобы связи остались корректными
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

    # Restore gallery photo records linked to restored people
    # Восстановить записи фотографий, привязанные к восстановленным людям
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

    # Restore relationships after people have been recreated
    # Восстановить связи после того, как люди уже восстановлены
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

    # Save all restore operations as one completed restore action
    # Сохранить все операции восстановления как одно завершённое действие
    conn.commit()
    conn.close()



# =========================================================
# Auth routes
# =========================================================
# ------- register роут -----------------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    """Register a new user account and sign the user in."""

    # Redirect authenticated users away from the register page
    # Не показывать страницу регистрации уже вошедшему пользователю
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    form = RegisterForm()
    if form.validate_on_submit():
        # Normalize email before saving it
        # Привести email к единому виду перед сохранением
        email = form.email.data.lower().strip()

        # Prevent duplicate registration with the same email
        # Не допустить повторную регистрацию с тем же email
        existing = User.query.filter_by(email=email).first()
        if existing:
            form.email.errors.append("This email is already registered.")
            return render_template("register.html", form=form)

        # Create the user and store a hashed password
        # Создать пользователя и сохранить хэш пароля
        user = User(email=email)
        user.set_password(form.password.data)

        db.session.add(user)
        db.session.commit()

        # Log the user in immediately after successful registration
        # Сразу авторизовать пользователя после успешной регистрации
        login_user(user)
        return redirect(url_for("dashboard"))

    return render_template("register.html", form=form)


# ------- login роут --------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    """Authenticate an existing user and start a login session."""

    # Redirect authenticated users away from the login page
    # Не показывать страницу входа уже вошедшему пользователю
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    form = LoginForm()
    if form.validate_on_submit():
        # Normalize email before lookup
        # Привести email к единому виду перед поиском в базе
        email = form.email.data.lower().strip()
        user = User.query.filter_by(email=email).first()

        # Validate email/password pair
        # Проверить корректность пары email/пароль
        if user is None or not user.check_password(form.password.data):
            form.password.errors.append("Invalid email or password.")
            return render_template("login.html", form=form)

        # Log the user in and redirect to the originally requested page if present
        # Авторизовать пользователя и вернуть на исходную страницу, если она была запрошена
        login_user(user, remember=form.remember.data)
        next_url = request.args.get("next")
        return redirect(next_url or url_for("dashboard"))

    return render_template("login.html", form=form)


# ------- logout роут -------------------------------------
@app.route("/logout", methods=["POST"])
@login_required
def logout():
    """Log the current user out and return to the login page."""

    # End the current authenticated session
    # Завершить текущую авторизованную сессию
    logout_user()
    return redirect(url_for("login"))



# =========================================================
# General routes
# =========================================================
# ------- index роут --------------------------------------
@app.route("/")
def index():
    """Render the public landing page of the application."""
    return render_template("index.html")

# ------- dashboard роут ----------------------------------
@app.route("/dashboard")
@login_required
def dashboard():
    """Show the current user's own trees and trees shared with them."""

    # Load trees owned by the current user, newest first
    # Загрузить деревья, принадлежащие текущему пользователю, начиная с новых
    owned_trees = Tree.query.filter_by(owner_user_id=current_user.id).order_by(Tree.created_at.desc()).all()

    # Load all shared access entries for the current user
    # Загрузить все записи общего доступа для текущего пользователя
    shared_entries = TreeAccess.query.filter_by(user_id=current_user.id).all()
    shared_trees = [entry.tree for entry in shared_entries]

    # Build lightweight dashboard cards for owned trees
    # Подготовить краткие карточки для собственных деревьев
    owned_tree_cards = []
    for t in owned_trees:
        owned_tree_cards.append({
            "id": t.id,
            "title": t.title,
            "person_count": count_persons_in_tree(t.id)
        })

    # Build dashboard cards for trees shared with the current user
    # Подготовить карточки для деревьев, которыми поделились с текущим пользователем
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




# =========================================================
# Tree routes
# =========================================================
# ------- tree роут ---------------------------------------
@app.route("/tree")
@login_required
def tree():
    """Render the interactive tree page for the selected tree."""

    # A tree page always requires an explicit tree_id
    # Для страницы дерева всегда нужен явно переданный tree_id
    tree_id = request.args.get("tree_id")
    if not tree_id:
        return redirect(url_for("dashboard"))

    # Make sure the current user is allowed to view this tree
    # Убедиться, что текущий пользователь имеет право просматривать это дерево
    current_tree = get_current_user_tree_or_404(tree_id)

    # Prepare a safe fallback title for export and page rendering
    # Подготовить безопасный запасной заголовок для экспорта и отображения страницы
    tree_title = current_tree.title if current_tree and current_tree.title else "family-tree"

    return render_template(
        "tree.html",
        tree_id=tree_id,
        current_tree=current_tree,
        tree_title=tree_title
    )

# ------- persons роут ------------------------------------
@app.route("/persons")
@login_required
def persons():
    """Show the list of people that belong to the selected tree."""

    # The people page is always opened inside a specific tree
    # Страница со списком людей всегда открывается внутри конкретного дерева
    tree_id = request.args.get("tree_id")
    if not tree_id:
        return redirect(url_for("dashboard"))

    # Read the selected sorting option from the query string
    # Считать выбранный вариант сортировки из query-параметра
    sort = request.args.get("sort", "created_desc")

    # Ensure the current user can access this tree before loading people
    # Убедиться, что текущий пользователь имеет доступ к этому дереву перед загрузкой людей
    current_tree = get_current_user_tree_or_404(tree_id)
    people = get_all_persons(tree_id)

    # Apply in-memory sorting for the people list
    # Применить сортировку списка людей в памяти
    if sort == "name_asc":
        people = sorted(
            people,
            key=lambda p: (
                (p["first_name"] or "").lower(),
                (p["middle_name"] or "").lower(),
                (p["last_name"] or "").lower()
            )
        )
    elif sort == "name_desc":
        people = sorted(
            people,
            key=lambda p: (
                (p["first_name"] or "").lower(),
                (p["middle_name"] or "").lower(),
                (p["last_name"] or "").lower()
            ),
            reverse=True
        )
    elif sort == "created_asc":
        people = sorted(people, key=lambda p: p["id"])
    else:
        # Default: newest people first
        # По умолчанию: сначала самые новые записи
        people = sorted(people, key=lambda p: p["id"], reverse=True)
        sort = "created_desc"

    return render_template(
        "persons.html",
        people=people,
        tree_id=tree_id,
        current_tree=current_tree,
        current_sort=sort
    )

# ------- create_tree роут --------------------------------
@app.route("/trees/create", methods=["POST"])
@login_required
def create_tree():
    """Create a new tree owned by the current user."""

    # Use a default title if the input is left empty
    # Использовать заголовок по умолчанию, если поле оставлено пустым
    title = request.form.get("title", "").strip() or "My Family Tree"

    t = Tree(title=title, owner_user_id=current_user.id)
    db.session.add(t)
    db.session.commit()

    return redirect(url_for("dashboard"))

# ------- edit_tree роут ----------------------------------
@app.route("/trees/<int:tree_id>/edit", methods=["GET", "POST"])
@login_required
def edit_tree(tree_id):
    """Rename a tree owned by the current user."""

    # Only the tree owner can rename the tree
    # Только владелец дерева может переименовать дерево
    tree = Tree.query.filter_by(id=tree_id, owner_user_id=current_user.id).first()
    if tree is None:
        return "Tree not found", 404

    if request.method == "POST":
        title = request.form.get("title", "").strip()

        # Require a non-empty title
        # Требовать непустой заголовок
        if not title:
            return "Tree title is required", 400

        tree.title = title
        db.session.commit()

        return redirect(url_for("dashboard"))

    return render_template("tree_edit.html", tree=tree)


# ------- delete_tree_route роут --------------------------
@app.route("/trees/<int:tree_id>/delete", methods=["POST"])
@login_required
def delete_tree_route(tree_id):
    """Delete a tree owned by the current user together with its tree-scoped data."""

    # Only the tree owner can delete the tree
    # Только владелец дерева может удалить дерево
    tree = Tree.query.filter_by(id=tree_id, owner_user_id=current_user.id).first()
    if tree is None:
        return "Tree not found", 404

    # Delete all people and relationships stored for this tree in the SQLite data store
    # Удалить всех людей и все связи этого дерева из основной SQLite-базы данных
    delete_tree_data(tree_id)

    # Delete the tree record itself from app.db
    # Удалить саму запись дерева из app.db
    db.session.delete(tree)
    db.session.commit()

    return redirect(url_for("dashboard"))


# ------- manage_tree_access роут -------------------------
@app.route("/trees/<int:tree_id>/access", methods=["GET", "POST"])
@login_required
def manage_tree_access(tree_id):
    """Allow the owner to grant editor or viewer access to other users."""

    # Only the owner can manage sharing settings for the tree
    # Только владелец может управлять общим доступом к дереву
    tree = Tree.query.filter_by(id=tree_id, owner_user_id=current_user.id).first()
    if tree is None:
        return "Tree not found", 404

    error = None

    if request.method == "POST":
        # Read and normalize submitted sharing data
        # Прочитать и нормализовать данные общего доступа из формы
        email = request.form.get("email", "").strip().lower()
        role = request.form.get("role", "editor").strip().lower()

        # Fallback to editor if an unexpected role value is submitted
        # Использовать editor по умолчанию, если пришла некорректная роль
        if role not in {"editor", "viewer"}:
            role = "editor"

        if not email:
            error = "Email is required."
        else:
            user = User.query.filter_by(email=email).first()

            # Validate the target user before creating a shared access record
            # Проверить целевого пользователя перед созданием записи общего доступа
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

    # Load current sharing entries to display them in the access management page
    # Загрузить текущие записи общего доступа для отображения на странице управления доступом
    shared_entries = TreeAccess.query.filter_by(tree_id=tree.id).all()

    return render_template(
        "tree_access.html",
        tree=tree,
        shared_entries=shared_entries,
        error=error
    )


# ------- remove_tree_access роут -------------------------
@app.route("/trees/<int:tree_id>/access/<int:access_id>/delete", methods=["POST"])
@login_required
def remove_tree_access(tree_id, access_id):
    """Remove a shared access entry from a tree owned by the current user."""

    # Only the owner can revoke shared access
    # Только владелец может отозвать общий доступ
    tree = Tree.query.filter_by(id=tree_id, owner_user_id=current_user.id).first()
    if tree is None:
        return "Tree not found", 404

    access = TreeAccess.query.filter_by(id=access_id, tree_id=tree.id).first()
    if access is None:
        return "Access entry not found", 404

    db.session.delete(access)
    db.session.commit()

    return redirect(url_for("manage_tree_access", tree_id=tree.id))


# ------- update_tree_access_role роут --------------------
@app.route("/trees/<int:tree_id>/access/<int:access_id>/role", methods=["POST"])
@login_required
def update_tree_access_role(tree_id, access_id):
    """Change an existing shared access entry between editor and viewer."""

    # Only the owner can change another user's role in the tree
    # Только владелец может изменить роль другого пользователя в дереве
    tree = Tree.query.filter_by(id=tree_id, owner_user_id=current_user.id).first()
    if tree is None:
        return "Tree not found", 404

    access = TreeAccess.query.filter_by(id=access_id, tree_id=tree.id).first()
    if access is None:
        return "Access entry not found", 404

    # Accept only supported sharing roles
    # Принимать только поддерживаемые роли общего доступа
    new_role = request.form.get("role", "").strip().lower()
    if new_role not in {"editor", "viewer"}:
        return "Invalid role", 400

    access.role = new_role
    db.session.commit()

    return redirect(url_for("manage_tree_access", tree_id=tree.id))



# =========================================================
# Person routes
# =========================================================
# ------- add_person_route роут ---------------------------
@app.route('/persons/add', methods=["GET", "POST"])
@login_required
def add_person_route():
    """Create a new person inside the selected tree."""

    # Only users with edit access can add people to the tree
    # Только пользователи с правом редактирования могут добавлять людей в дерево
    tree_id = request.args.get("tree_id")
    require_tree_edit_access(tree_id)

    if request.method == "POST":
        # Read form fields and normalize empty values to None
        # Считать поля формы и преобразовать пустые значения в None
        first_name = request.form.get("first_name")
        middle_name = request.form.get("middle_name") or None
        last_name = request.form.get("last_name") or None
        maiden_name = request.form.get("maiden_name") or None
        birth_date = request.form.get("birth_date") or None
        death_date = request.form.get("death_date") or None

        # Parse partial date fields
        # Обработать отдельные части неполной даты
        birth_year = to_int_or_none(request.form.get("birth_year"))
        birth_month = to_int_or_none(request.form.get("birth_month"))
        birth_day = to_int_or_none(request.form.get("birth_day"))

        death_year = to_int_or_none(request.form.get("death_year"))
        death_month = to_int_or_none(request.form.get("death_month"))
        death_day = to_int_or_none(request.form.get("death_day"))

        gender = request.form.get("gender") or None
        notes = request.form.get("notes") or None

        # First name is the only required person field
        # Имя — единственное обязательное поле для человека
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


# ------- person_detail роут ------------------------------
@app.route("/persons/<int:person_id>")
@login_required
def person_detail(person_id):
    """Show the full profile page for one person and all derived relations."""

    # Resolve tree context and current user's role in that tree
    # Определить текущее дерево и роль пользователя внутри этого дерева
    tree_id = request.args.get("tree_id")
    tree_role = get_tree_role_for_current_user(tree_id)

    # Load the selected person and related media
    # Загрузить выбранного человека и связанные с ним фотографии
    person = get_person_in_tree_or_404(person_id, tree_id)
    photos = get_person_photos(person_id)

    # Load direct and computed family relations for display
    # Загрузить прямые и вычисляемые семейные связи для отображения
    parents = get_parents(person_id)
    children = get_children(person_id)
    spouses = get_spouses(person_id)
    siblings = get_siblings(person_id)
    cousins = get_cousins(person_id)
    uncles_aunts = get_uncles_aunts(person_id)
    nephews_nieces = get_nephews_nieces(person_id)
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
        cousins=cousins,
        uncles_aunts=uncles_aunts,
        nephews_nieces=nephews_nieces,
        grandparents=grandparents,
        great_grandparents=great_grandparents,
        great_great_grandparents=great_great_grandparents,
        ancestors=ancestors,
        photos=photos,
        tree_id=tree_id,
        tree_role=tree_role
    )


# ------- edit_person роут --------------------------------
@app.route("/persons/<int:person_id>/edit", methods=["GET", "POST"])
@login_required
def edit_person(person_id):
    """Edit an existing person inside the selected tree."""

    # Only users with edit access can modify person data
    # Только пользователи с правом редактирования могут изменять данные человека
    tree_id = request.args.get("tree_id")
    require_tree_edit_access(tree_id)

    person = get_person_in_tree_or_404(person_id, tree_id)

    if request.method == "POST":
        # Read updated form fields and normalize empty values to None
        # Считать обновлённые поля формы и преобразовать пустые значения в None
        first_name = request.form.get("first_name")
        middle_name = request.form.get("middle_name") or None
        last_name = request.form.get("last_name") or None
        maiden_name = request.form.get("maiden_name") or None
        birth_date = request.form.get("birth_date") or None
        death_date = request.form.get("death_date") or None

        # Parse partial date fields
        # Обработать отдельные части неполной даты
        birth_year = to_int_or_none(request.form.get("birth_year"))
        birth_month = to_int_or_none(request.form.get("birth_month"))
        birth_day = to_int_or_none(request.form.get("birth_day"))

        death_year = to_int_or_none(request.form.get("death_year"))
        death_month = to_int_or_none(request.form.get("death_month"))
        death_day = to_int_or_none(request.form.get("death_day"))

        gender = request.form.get("gender") or None
        notes = request.form.get("notes") or None

        # First name is still required when updating a person
        # Имя остаётся обязательным полем и при редактировании
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


# ------- delete_person_route роут ------------------------
@app.route("/persons/<int:person_id>/delete", methods=["POST"])
@login_required
def delete_person_route(person_id):
    """Delete a person from the selected tree."""

    # Only users with edit access can delete people
    # Только пользователи с правом редактирования могут удалять людей
    tree_id = request.args.get("tree_id")
    require_tree_edit_access(tree_id)

    person = get_person_in_tree_or_404(person_id, tree_id)

    delete_person(person_id)
    return redirect(url_for("persons", tree_id=tree_id))




# =========================================================
# Relation routes
# =========================================================

# ------- add_relation роут -------------------------------
@app.route("/persons/<int:person_id>/relations/add", methods=["GET", "POST"])
@login_required
def add_relation(person_id):
    """Add a parent, child or spouse relation for the selected person."""

    # Only users with edit access can modify relations
    # Только пользователи с правом редактирования могут изменять связи
    tree_id = request.args.get("tree_id")
    require_tree_edit_access(tree_id)

    # Allow the form to open with a preselected relation type from the URL
    # Позволить открыть форму с заранее выбранным типом связи из URL
    preset_relation_type = request.args.get("relation_type")

    person = get_person_in_tree_or_404(person_id, tree_id)

    # Exclude the current person from the selectable people list
    # Исключить текущего человека из списка доступных людей
    people = [p for p in get_all_persons(tree_id) if p["id"] != person_id]
    error = None

    if request.method == "POST":
        relation_type = request.form.get("relation_type")
        relative_id = request.form.get("relative_id")

        # Both relation type and target person are required
        # Нужно обязательно указать тип связи и второго человека
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

        # Validate that the selected related person id is numeric
        # Проверить, что id выбранного человека является числом
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

        # Prevent creating a relation from a person to themselves
        # Не допустить создание связи человека с самим собой
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
            # Parent relation is stored as: parent -> child
            # Связь родителя хранится в виде: родитель -> ребёнок
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
            # Child relation is also stored as: current person -> child using parent type
            # Связь ребёнка тоже хранится как: текущий человек -> ребёнок с типом parent
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
            # Spouse relation is stored in both directions
            # Связь супругов хранится в обе стороны
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


# ------- delete_relation роут ----------------------------
@app.route("/persons/<int:person_id>/relations/delete", methods=["POST"])
@login_required
def delete_relation(person_id):
    """Delete an existing relation for the selected person."""

    # Only users with edit access can remove relations
    # Только пользователи с правом редактирования могут удалять связи
    tree_id = request.args.get("tree_id")
    require_tree_edit_access(tree_id)
    person = get_person_in_tree_or_404(person_id, tree_id)

    relative_id = request.form.get("relative_id")
    relation_type = request.form.get("relation_type")

    # Both relation type and related person id must be provided
    # Нужно обязательно передать тип связи и id связанного человека
    if not relative_id or not relation_type:
        return "Missing relation data", 400

    # Validate the related person id before deletion
    # Проверить корректность id связанного человека перед удалением
    try:
        relative_id = int(relative_id)
    except ValueError:
        return "Invalid relative id", 400

    delete_relationship(person_id, relative_id, relation_type)

    return redirect(url_for("person_detail", person_id=person_id, tree_id=tree_id))



# =========================================================
# Photo routes
# =========================================================

# ------- upload_person_photo_route роут ------------------
@app.route("/persons/<int:person_id>/photo/upload", methods=["POST"])
@login_required
def upload_person_photo_route(person_id):
    """Upload or replace the main profile photo for a person."""

    # Only users with edit access can upload photos
    # Только пользователи с правом редактирования могут загружать фотографии
    tree_id = request.args.get("tree_id")
    require_tree_edit_access(tree_id)

    person = get_person_in_tree_or_404(person_id, tree_id)

    # Validate the uploaded file before saving it
    # Проверить загруженный файл перед сохранением
    file = request.files.get("photo")
    if not file or not file.filename:
        return "No file selected", 400

    if not allowed_image_file(file.filename):
        return "Invalid image format", 400

    # Remove the old profile photo from disk if it exists
    # Удалить старое фото профиля с диска, если оно существует
    old_filename = person["photo_filename"]
    if old_filename:
        old_path = os.path.join(app.config["UPLOAD_FOLDER"], old_filename)
        if os.path.exists(old_path):
            os.remove(old_path)

    # Generate a unique safe filename before saving
    # Сгенерировать уникальное и безопасное имя файла перед сохранением
    ext = file.filename.rsplit(".", 1)[1].lower()
    filename = secure_filename(f"person_{person_id}_{uuid.uuid4().hex}.{ext}")
    save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)

    file.save(save_path)
    update_person_photo(person_id, filename)

    return redirect(url_for("person_detail", person_id=person_id, tree_id=tree_id))


# ------- delete_person_photo_route роут ------------------
@app.route("/persons/<int:person_id>/photo/delete", methods=["POST"])
@login_required
def delete_person_photo_route(person_id):
    """Delete the main profile photo for a person."""

    # Only users with edit access can remove photos
    # Только пользователи с правом редактирования могут удалять фотографии
    tree_id = request.args.get("tree_id")
    require_tree_edit_access(tree_id)

    person = get_person_in_tree_or_404(person_id, tree_id)

    # Remove the file from disk first, then clear the database field
    # Сначала удалить файл с диска, затем очистить поле в базе данных
    filename = person["photo_filename"]
    if filename:
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        if os.path.exists(file_path):
            os.remove(file_path)

    remove_person_photo(person_id)

    return redirect(url_for("person_detail", person_id=person_id, tree_id=tree_id))


# ------- upload_gallery_photo_route роут -----------------
@app.route("/persons/<int:person_id>/gallery/upload", methods=["POST"])
@login_required
def upload_gallery_photo_route(person_id):
    """Upload a new gallery photo for a person."""

    # Only users with edit access can add gallery photos
    # Только пользователи с правом редактирования могут добавлять фотографии в галерею
    tree_id = request.args.get("tree_id")
    require_tree_edit_access(tree_id)

    person = get_person_in_tree_or_404(person_id, tree_id)

    # Validate the uploaded file before saving it
    # Проверить загруженный файл перед сохранением
    file = request.files.get("gallery_photo")
    if not file or not file.filename:
        return "No file selected", 400

    if not allowed_image_file(file.filename):
        return "Invalid image format", 400

    # Generate a unique safe filename for the gallery image
    # Сгенерировать уникальное и безопасное имя файла для фотографии галереи
    ext = file.filename.rsplit(".", 1)[1].lower()
    filename = secure_filename(f"gallery_{person_id}_{uuid.uuid4().hex}.{ext}")
    save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)

    file.save(save_path)
    add_gallery_photo(person_id, filename)

    return redirect(url_for("person_detail", person_id=person_id, tree_id=tree_id))


# ------- delete_gallery_photo_route роут -----------------
@app.route("/persons/<int:person_id>/gallery/<int:photo_id>/delete", methods=["POST"])
@login_required
def delete_gallery_photo_route(person_id, photo_id):
    """Delete one gallery photo that belongs to the selected person."""

    # Only users with edit access can remove gallery photos
    # Только пользователи с правом редактирования могут удалять фотографии из галереи
    tree_id = request.args.get("tree_id")
    require_tree_edit_access(tree_id)

    person = get_person_in_tree_or_404(person_id, tree_id)

    # Make sure the requested gallery photo belongs to this person
    # Убедиться, что выбранная фотография галереи принадлежит именно этому человеку
    photo = get_gallery_photo(photo_id)
    if photo is None or photo["person_id"] != person_id:
        return "Photo not found", 404

    # Remove the file from disk before deleting its database record
    # Удалить файл с диска перед удалением записи из базы данных
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], photo["filename"])
    if os.path.exists(file_path):
        os.remove(file_path)

    delete_gallery_photo(photo_id)

    return redirect(url_for("person_detail", person_id=person_id, tree_id=tree_id))





# =========================================================
# Snapshot routes
# =========================================================

# ------- create_tree_snapshot роут -----------------------
@app.route("/trees/<int:tree_id>/snapshots/create", methods=["POST"])
@login_required
def create_tree_snapshot(tree_id):
    """Create a new snapshot for a tree owned by the current user."""

    # Only the tree owner can create snapshots
    # Только владелец дерева может создавать снапшоты
    tree = Tree.query.filter_by(id=tree_id, owner_user_id=current_user.id).first()
    if tree is None:
        return "Tree not found", 404

    # Build a JSON snapshot of the current tree state
    # Собрать JSON-снапшот текущего состояния дерева
    snapshot_json = build_tree_snapshot_data(tree.id)
    if snapshot_json is None:
        return "Could not create snapshot", 400

    # Save snapshot metadata and JSON payload in app.db
    # Сохранить метаданные снапшота и JSON-данные в app.db
    snapshot = TreeSnapshot(
        tree_id=tree.id,
        created_by_user_id=current_user.id,
        title=f"{tree.title} snapshot",
        snapshot_json=snapshot_json
    )

    db.session.add(snapshot)
    db.session.commit()

    return redirect(url_for("list_tree_snapshots", tree_id=tree.id))


# ------- list_tree_snapshots роут ------------------------
@app.route("/trees/<int:tree_id>/snapshots")
@login_required
def list_tree_snapshots(tree_id):
    """Show all saved snapshots for a tree owned by the current user."""

    # Only the tree owner can browse snapshots
    # Только владелец дерева может просматривать снапшоты
    tree = Tree.query.filter_by(id=tree_id, owner_user_id=current_user.id).first()
    if tree is None:
        return "Tree not found", 404

    # Show newest snapshots first
    # Показывать сначала самые новые снапшоты
    snapshots = TreeSnapshot.query.filter_by(tree_id=tree.id) \
        .order_by(TreeSnapshot.created_at.desc()) \
        .all()

    return render_template(
        "tree_snapshots.html",
        tree=tree,
        snapshots=snapshots
    )


# ------- restore_tree_snapshot роут ----------------------
@app.route("/trees/<int:tree_id>/snapshots/<int:snapshot_id>/restore", methods=["POST"])
@login_required
def restore_tree_snapshot(tree_id, snapshot_id):
    """Restore a tree from one of its previously saved snapshots."""

    # Only the tree owner can restore snapshots
    # Только владелец дерева может восстанавливать снапшоты
    tree = Tree.query.filter_by(id=tree_id, owner_user_id=current_user.id).first()
    if tree is None:
        return "Tree not found", 404

    # The snapshot must belong to the same tree
    # Снапшот должен принадлежать этому же дереву
    snapshot = TreeSnapshot.query.filter_by(id=snapshot_id, tree_id=tree.id).first()
    if snapshot is None:
        return "Snapshot not found", 404

    # Replace current tree data with the selected snapshot data
    # Заменить текущие данные дерева данными выбранного снапшота
    restore_tree_from_snapshot(tree.id, snapshot.snapshot_json)

    return redirect(url_for("tree", tree_id=tree.id))


# ------- delete_tree_snapshot роут -----------------------
@app.route("/trees/<int:tree_id>/snapshots/<int:snapshot_id>/delete", methods=["POST"])
@login_required
def delete_tree_snapshot(tree_id, snapshot_id):
    """Delete one saved snapshot from a tree owned by the current user."""

    # Only the tree owner can delete snapshots
    # Только владелец дерева может удалять снапшоты
    tree = Tree.query.filter_by(id=tree_id, owner_user_id=current_user.id).first()
    if tree is None:
        return "Tree not found", 404

    # Make sure the snapshot exists and belongs to this tree
    # Убедиться, что снапшот существует и принадлежит этому дереву
    snapshot = TreeSnapshot.query.filter_by(id=snapshot_id, tree_id=tree.id).first()
    if snapshot is None:
        return "Snapshot not found", 404

    db.session.delete(snapshot)
    db.session.commit()

    return redirect(url_for("list_tree_snapshots", tree_id=tree.id))





# =========================================================
# API routes
# =========================================================

# ------- api_person_search роут --------------------------
@app.route("/api/persons/search")
@login_required
def api_person_search():
    """Return search results for people inside the selected tree."""

    # Read search query and optional filters from the request
    # Считать поисковый запрос и дополнительные фильтры из запроса
    q = request.args.get("q", "").strip()
    tree_id = request.args.get("tree_id")
    exclude_id = request.args.get("exclude_id")

    # Empty query returns an empty result list
    # Пустой запрос должен возвращать пустой список результатов
    if not q:
        return jsonify([])

    # Make sure the current user can access this tree before searching in it
    # Убедиться, что текущий пользователь имеет доступ к этому дереву перед поиском
    get_current_user_tree_or_404(tree_id)

    # Convert exclude_id to int if it was provided
    # Преобразовать exclude_id в int, если он был передан
    try:
        exclude_id = int(exclude_id) if exclude_id else None
    except ValueError:
        exclude_id = None

    # Return matching people as JSON for the relation search UI
    # Вернуть найденных людей в JSON для интерфейса поиска связей
    results = search_persons(q, tree_id=tree_id, exclude_id=exclude_id, limit=20)

    return jsonify([dict(r) for r in results])


# ------- api_tree роут -----------------------------------
@app.route("/api/tree")
@login_required
def api_tree():
    """Return tree-scoped people and relationships data for GoJS rendering."""

    conn = get_db()
    tree_id = request.args.get("tree_id")
    if not tree_id:
        conn.close()
        return jsonify({"persons": [], "relationships": []})

    # Make sure the current user can access this tree before loading its data
    # Убедиться, что текущий пользователь имеет доступ к этому дереву перед загрузкой данных
    get_current_user_tree_or_404(tree_id)

    # Load all people that belong to the selected tree
    # Загрузить всех людей, принадлежащих выбранному дереву
    persons = conn.execute("""
        SELECT id, first_name, middle_name, last_name, maiden_name,
            birth_date, death_date,
            birth_year, birth_month, birth_day,
            death_year, death_month, death_day,
            gender, notes, tree_id, photo_filename
        FROM persons
        WHERE tree_id = ?
    """, (tree_id,)).fetchall()

    # Load only relationships where both sides belong to the same tree
    # Загрузить только те связи, где обе стороны принадлежат одному дереву
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


# ------- api_tables роут ---------------------------------
@app.route("/api/tables")
@login_required
def api_tables():
    """Return the list of SQLite table names from the local data database."""

    # Useful mainly for debugging or checking the local SQLite structure
    # Полезно в основном для отладки или проверки структуры локальной SQLite-базы
    conn = get_db()
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    conn.close()
    return jsonify([r["name"] if isinstance(r, dict) else r[0] for r in rows])


# ------- init_db_route роут ------------------------------
@app.route("/init-db")
@login_required
def init_db_route():
    """Initialize the local SQLite database schema."""
    init_db()
    return "Database initialized."


# =========================================================
# Init / main
# =========================================================

# Run the app directly in development mode
# Запускать приложение напрямую в режиме разработки
if __name__ == "__main__":
    app.run(debug=True)