import os
import sys
import tempfile
from pathlib import Path

# Add project root to Python path
# Добавить корень проекта в Python path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pytest

from app import app as flask_app
from db import init_db
from extensions import db as sqlalchemy_db


@pytest.fixture
def app():
    """Create and configure a temporary Flask app for tests."""

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Temporary SQLite files for tests
        # Временные SQLite-файлы для тестов
        test_app_db = temp_path / "test_app.db"
        test_data_db = temp_path / "test_database.db"

        # Point db.py to a temporary SQLite file
        # Направить db.py на временную SQLite-базу
        os.environ["DATABASE_DB_PATH"] = str(test_data_db)

        flask_app.config.update(
            TESTING=True,
            WTF_CSRF_ENABLED=False,
            SQLALCHEMY_DATABASE_URI=f"sqlite:///{test_app_db}",
        )

        # Recreate SQLAlchemy tables for app.db models
        # Пересоздать таблицы SQLAlchemy для моделей app.db
        with flask_app.app_context():
            sqlalchemy_db.drop_all()
            sqlalchemy_db.create_all()
            init_db()

        yield flask_app

        # Clean up SQLAlchemy session after each test
        # Очистить SQLAlchemy-сессию после теста
        with flask_app.app_context():
            sqlalchemy_db.session.remove()

        os.environ.pop("DATABASE_DB_PATH", None)


@pytest.fixture
def client(app):
    """Return a Flask test client."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Return a Flask CLI test runner."""
    return app.test_cli_runner()