from models import User, Tree
from extensions import db
from db import get_person, get_all_persons


def create_user_login_and_tree(client, app, email="person@example.com", password="password123", title="Person Test Tree"):
    """Create a user, log in, and create one owned tree."""

    with app.app_context():
        user = User(email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        tree = Tree(title=title, owner_user_id=user.id)
        db.session.add(tree)
        db.session.commit()
        tree_id = tree.id

    client.post(
        "/login",
        data={
            "email": email,
            "password": password,
        },
        follow_redirects=True,
    )

    return tree_id


def test_user_can_add_person(client, app):
    tree_id = create_user_login_and_tree(client, app)

    response = client.post(
        f"/persons/add?tree_id={tree_id}",
        data={
            "first_name": "Bart",
            "middle_name": "",
            "last_name": "Simpson",
            "maiden_name": "",
            "birth_date": "",
            "death_date": "",
            "birth_year": "2010",
            "birth_month": "5",
            "birth_day": "12",
            "death_year": "",
            "death_month": "",
            "death_day": "",
            "gender": "male",
            "notes": "Test person",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    people = get_all_persons(tree_id)
    assert len(people) == 1
    assert people[0]["first_name"] == "Bart"
    assert people[0]["last_name"] == "Simpson"


def test_user_can_edit_person(client, app):
    tree_id = create_user_login_and_tree(client, app)

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
    person_id = people[0]["id"]

    response = client.post(
        f"/persons/{person_id}/edit?tree_id={tree_id}",
        data={
            "first_name": "Bartholomew",
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
            "notes": "Edited",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    person = get_person(person_id)
    assert person is not None
    assert person["first_name"] == "Bartholomew"
    assert person["notes"] == "Edited"


def test_user_can_delete_person(client, app):
    tree_id = create_user_login_and_tree(client, app)

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

    people = get_all_persons(tree_id)
    person_id = people[0]["id"]

    response = client.post(
        f"/persons/{person_id}/delete?tree_id={tree_id}",
        follow_redirects=True,
    )

    assert response.status_code == 200

    person = get_person(person_id)
    assert person is None