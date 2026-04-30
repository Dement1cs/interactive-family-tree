from models import User, Tree, TreeSnapshot
from extensions import db
from db import get_all_persons


def create_user_login_tree_and_person(client, app):
    """Create a user, log in, create a tree, and add one person."""

    with app.app_context():
        user = User(email="snapshot@example.com")
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()

        tree = Tree(title="Snapshot Test Tree", owner_user_id=user.id)
        db.session.add(tree)
        db.session.commit()
        tree_id = tree.id

    client.post(
        "/login",
        data={
            "email": "snapshot@example.com",
            "password": "password123",
        },
        follow_redirects=True,
    )

    client.post(
        f"/persons/add?tree_id={tree_id}",
        data={
            "first_name": "Marge",
            "middle_name": "",
            "last_name": "Simpson",
            "maiden_name": "",
            "birth_date": "",
            "death_date": "",
            "birth_year": "",
            "birth_month": "",
            "birth_day": "",
            "death_year": "",
            "death_month": "",
            "death_day": "",
            "gender": "female",
            "notes": "",
        },
        follow_redirects=True,
    )

    return tree_id


def test_owner_can_create_snapshot(client, app):
    tree_id = create_user_login_tree_and_person(client, app)

    response = client.post(
        f"/trees/{tree_id}/snapshots/create",
        follow_redirects=True,
    )

    assert response.status_code == 200

    with app.app_context():
        snapshots = TreeSnapshot.query.filter_by(tree_id=tree_id).all()
        assert len(snapshots) == 1


def test_owner_can_restore_snapshot(client, app):
    tree_id = create_user_login_tree_and_person(client, app)

    # Create snapshot when only one person exists
    client.post(
        f"/trees/{tree_id}/snapshots/create",
        follow_redirects=True,
    )

    with app.app_context():
        snapshot = TreeSnapshot.query.filter_by(tree_id=tree_id).first()
        snapshot_id = snapshot.id

    # Add another person after snapshot creation
    client.post(
        f"/persons/add?tree_id={tree_id}",
        data={
            "first_name": "Lisa",
            "middle_name": "",
            "last_name": "Simpson",
            "maiden_name": "",
            "birth_date": "",
            "death_date": "",
            "birth_year": "",
            "birth_month": "",
            "birth_day": "",
            "death_year": "",
            "death_month": "",
            "death_day": "",
            "gender": "female",
            "notes": "",
        },
        follow_redirects=True,
    )

    people_before_restore = get_all_persons(tree_id)
    assert len(people_before_restore) == 2

    # Restore snapshot
    response = client.post(
        f"/trees/{tree_id}/snapshots/{snapshot_id}/restore",
        follow_redirects=True,
    )

    assert response.status_code == 200

    people_after_restore = get_all_persons(tree_id)
    assert len(people_after_restore) == 1
    assert people_after_restore[0]["first_name"] == "Marge"


def test_owner_can_delete_snapshot(client, app):
    tree_id = create_user_login_tree_and_person(client, app)

    client.post(
        f"/trees/{tree_id}/snapshots/create",
        follow_redirects=True,
    )

    with app.app_context():
        snapshot = TreeSnapshot.query.filter_by(tree_id=tree_id).first()
        snapshot_id = snapshot.id

    response = client.post(
        f"/trees/{tree_id}/snapshots/{snapshot_id}/delete",
        follow_redirects=True,
    )

    assert response.status_code == 200

    with app.app_context():
        snapshot = TreeSnapshot.query.filter_by(id=snapshot_id).first()
        assert snapshot is None