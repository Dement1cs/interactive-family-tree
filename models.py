from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from extensions import db

class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

class Tree(db.Model):
    __tablename__ = "trees"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False, default="My Family Tree")
    owner_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    owner = db.relationship("User", backref="trees")

class TreeAccess(db.Model):
    __tablename__ = "tree_access"

    id = db.Column(db.Integer, primary_key=True)
    tree_id = db.Column(db.Integer, db.ForeignKey("trees.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="editor")

    tree = db.relationship("Tree", backref="shared_access")
    user = db.relationship("User", backref="tree_access_entries")

    __table_args__ = (
        db.UniqueConstraint("tree_id", "user_id", name="uq_tree_access_tree_user"),
    )

class TreeSnapshot(db.Model):
    __tablename__ = "tree_snapshots"

    id = db.Column(db.Integer, primary_key=True)
    tree_id = db.Column(db.Integer, db.ForeignKey("trees.id"), nullable=False)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    snapshot_json = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    tree = db.relationship("Tree", backref="snapshots")
    created_by = db.relationship("User")