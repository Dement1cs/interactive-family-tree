from models import User, Tree
from extensions import db


def create_and_login_user(client, app, email="tree@example.com", password="password123"):
    """Create a user in the test database and log them in."""

    with app.app_context():
        user = User(email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

    client.post(
        "/login",
        data={
            "email": email,
            "password": password,
        },
        follow_redirects=True,
    )


def test_dashboard_loads_for_logged_in_user(client, app):
    create_and_login_user(client, app)

    response = client.get("/dashboard")
    assert response.status_code == 200


def test_user_can_create_tree(client, app):
    create_and_login_user(client, app)

    response = client.post(
        "/trees/create",
        data={"title": "My Test Tree"},
        follow_redirects=True,
    )

    assert response.status_code == 200

    with app.app_context():
        tree = Tree.query.filter_by(title="My Test Tree").first()
        assert tree is not None


def test_owner_can_open_tree_page(client, app):
    create_and_login_user(client, app)

    with app.app_context():
        user = User.query.filter_by(email="tree@example.com").first()
        tree = Tree(title="Open Tree", owner_user_id=user.id)
        db.session.add(tree)
        db.session.commit()
        tree_id = tree.id

    response = client.get(f"/tree?tree_id={tree_id}")
    assert response.status_code == 200


def test_tree_page_redirects_without_tree_id(client, app):
    create_and_login_user(client, app)

    response = client.get("/tree", follow_redirects=False)
    assert response.status_code in (301, 302)
    assert "/dashboard" in response.headers["Location"]