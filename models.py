# =========================================================
# SQLAlchemy models
# =========================================================

from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from extensions import db


class User(db.Model, UserMixin):
    """Application user model used for authentication and tree ownership."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def set_password(self, password: str) -> None:
        """Hash and store the user's password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Check whether the provided password matches the stored hash."""
        return check_password_hash(self.password_hash, password)


class Tree(db.Model):
    """Family tree model owned by one user."""

    __tablename__ = "trees"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False, default="My Family Tree")
    owner_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Owner relationship makes it easy to access the user who owns the tree
    # Связь owner позволяет удобно получить пользователя-владельца дерева
    owner = db.relationship("User", backref="trees")


class TreeAccess(db.Model):
    """Shared access entry that grants a user editor or viewer rights to a tree."""

    __tablename__ = "tree_access"

    id = db.Column(db.Integer, primary_key=True)
    tree_id = db.Column(db.Integer, db.ForeignKey("trees.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="editor")

    # Relationship to the shared tree
    # Связь с деревом, к которому выдан доступ
    tree = db.relationship("Tree", backref="shared_access")

    # Relationship to the user who received access
    # Связь с пользователем, которому выдан доступ
    user = db.relationship("User", backref="tree_access_entries")

    # Prevent duplicate access entries for the same tree/user pair
    # Не допускать дублирующих записей доступа для одной и той же пары tree/user
    __table_args__ = (
        db.UniqueConstraint("tree_id", "user_id", name="uq_tree_access_tree_user"),
    )


class TreeSnapshot(db.Model):
    """Saved snapshot of a tree that can later be restored."""

    __tablename__ = "tree_snapshots"

    id = db.Column(db.Integer, primary_key=True)
    tree_id = db.Column(db.Integer, db.ForeignKey("trees.id"), nullable=False)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    snapshot_json = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Tree that this snapshot belongs to
    # Дерево, к которому относится этот снапшот
    tree = db.relationship("Tree", backref="snapshots")

    # User who created the snapshot
    # Пользователь, который создал снапшот
    created_by = db.relationship("User")