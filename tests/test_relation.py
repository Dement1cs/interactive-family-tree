from models import User, Tree
from extensions import db
from db import get_all_persons, get_parents, get_children, get_spouses


def create_user_login_tree_and_people(client, app):
    """Create a user, log in, create a tree, and add two people."""

    with app.app_context():
        user = User(email="relation@example.com")
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()

        tree = Tree(title="Relation Test Tree", owner_user_id=user.id)
        db.session.add(tree)
        db.session.commit()
        tree_id = tree.id

    client.post(
        "/login",
        data={
            "email": "relation@example.com",
            "password": "password123",
        },
        follow_redirects=True,
    )

    client.post(
        f"/persons/add?tree_id={tree_id}",
        data={
            "first_name": "Homer",
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
            "gender": "male",
            "notes": "",
        },
        follow_redirects=True,
    )

    client.post(
        f"/persons/add?tree_id={tree_id}",
        data={
            "first_name": "Bart",
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
            "gender": "male",
            "notes": "",
        },
        follow_redirects=True,
    )

    people = get_all_persons(tree_id)
    return tree_id, people


def test_user_can_add_parent_relation(client, app):
    tree_id, people = create_user_login_tree_and_people(client, app)

    homer = next(p for p in people if p["first_name"] == "Homer")
    bart = next(p for p in people if p["first_name"] == "Bart")

    response = client.post(
        f"/persons/{bart['id']}/relations/add?tree_id={tree_id}",
        data={
            "relation_type": "parent",
            "relative_id": homer["id"],
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    parents = get_parents(bart["id"])
    assert any(p["id"] == homer["id"] for p in parents)

    children = get_children(homer["id"])
    assert any(c["id"] == bart["id"] for c in children)


def test_user_can_add_spouse_relation(client, app):
    tree_id, people = create_user_login_tree_and_people(client, app)

    homer = next(p for p in people if p["first_name"] == "Homer")
    bart = next(p for p in people if p["first_name"] == "Bart")

    response = client.post(
        f"/persons/{homer['id']}/relations/add?tree_id={tree_id}",
        data={
            "relation_type": "spouse",
            "relative_id": bart["id"],
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    spouses_of_homer = get_spouses(homer["id"])
    spouses_of_bart = get_spouses(bart["id"])

    assert any(s["id"] == bart["id"] for s in spouses_of_homer)
    assert any(s["id"] == homer["id"] for s in spouses_of_bart)


def test_user_can_delete_relation(client, app):
    tree_id, people = create_user_login_tree_and_people(client, app)

    homer = next(p for p in people if p["first_name"] == "Homer")
    bart = next(p for p in people if p["first_name"] == "Bart")

    client.post(
        f"/persons/{bart['id']}/relations/add?tree_id={tree_id}",
        data={
            "relation_type": "parent",
            "relative_id": homer["id"],
        },
        follow_redirects=True,
    )

    response = client.post(
        f"/persons/{homer['id']}/relations/delete?tree_id={tree_id}",
        data={
            "relative_id": bart["id"],
            "relation_type": "parent",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    children = get_children(homer["id"])
    assert not any(c["id"] == bart["id"] for c in children)

    parents = get_parents(bart["id"])
    assert not any(p["id"] == homer["id"] for p in parents)