# =========================================================
# Flask extensions
# =========================================================

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

# Shared SQLAlchemy instance for ORM models
# Общий экземпляр SQLAlchemy для ORM-моделей
db = SQLAlchemy()

# Database migration helper
# Помощник для миграций базы данных
migrate = Migrate()

# Login manager for user session handling
# Менеджер входа для управления пользовательской сессией
login_manager = LoginManager()

# Redirect unauthorized users to the login page
# Перенаправлять неавторизованных пользователей на страницу входа
login_manager.login_view = "login"

# CSRF protection for forms and POST requests
# CSRF-защита для форм и POST-запросов
csrf = CSRFProtect()