from models import User
from extensions import db

def test_register_page_loads(client):
    response = client.get("/register")
    assert response.status_code == 200

def test_login_page_loads(client):
    response = client.get("/login")
    assert response.status_code == 200

def test_user_can_register(client, app):
    response = client.post(
        "/register",
        data={
            "email": "test@example.com",
            "password": "password123",
            "confirm": "password123",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    with app.app_context():
        user = User.query.filter_by(email="test@example.com").first()
        assert user is not None

def test_user_can_login(client, app):
    with app.app_context():
        user = User(email="login@example.com")
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()

    response = client.post(
        "/login",
        data={
            "email": "login@example.com",
            "password": "password123",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"dashboard" in response.data.lower() or b"tree" in response.data.lower()

def test_protected_page_redirects_when_not_logged_in(client):
    response = client.get("/dashboard", follow_redirects=False)

    assert response.status_code in (301, 302)
    assert "/login" in response.headers["Location"]

    