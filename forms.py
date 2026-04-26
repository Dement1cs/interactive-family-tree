# =========================================================
# WTForms forms
# =========================================================

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Email, Length, EqualTo


class RegisterForm(FlaskForm):
    """Form used to register a new user account."""

    # Email field with required, valid email, and max length validation
    # Поле email с проверкой на обязательность, корректный формат и максимальную длину
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=255)])

    # Password field with minimum length validation
    # Поле пароля с проверкой минимальной длины
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8)])

    # Confirmation field that must match the password field
    # Поле подтверждения, которое должно совпадать с полем пароля
    confirm = PasswordField("Confirm password", validators=[DataRequired(), EqualTo("password")])

    # Submit button for account creation
    # Кнопка отправки формы для создания аккаунта
    submit = SubmitField("Create account")


class LoginForm(FlaskForm):
    """Form used to authenticate an existing user."""

    # Email field with required, valid email, and max length validation
    # Поле email с проверкой на обязательность, корректный формат и максимальную длину
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=255)])

    # Password field required for login
    # Поле пароля, обязательное для входа
    password = PasswordField("Password", validators=[DataRequired()])

    # Optional checkbox to keep the user logged in
    # Необязательный флажок для сохранения входа в систему
    remember = BooleanField("Remember me")

    # Submit button for login
    # Кнопка отправки формы для входа
    submit = SubmitField("Log in")