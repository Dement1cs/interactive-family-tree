from flask import Flask, render_template, request, redirect, url_for
from db import(
    init_db, 
    get_all_persons, 
    add_person, 
    get_person,
    update_person,
    delete_person,
    add_relationship,
    get_parents,
    get_children,
    get_spouses,
    )

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/tree")
def tree():
    return render_template("tree.html")

@app.route("/persons")
def persons():
    people = get_all_persons()
    return render_template("persons.html", people=people)

@app.route('/persons/add', methods=["GET", "POST"])
def add_person_route():
    if request.method == "POST":
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name") or None
        birth_date = request.form.get("birth_date") or None
        death_date = request.form.get("death_date") or None
        gender = request.form.get("gender") or None
        notes = request.form.get("notes") or None

        if not first_name:
            return "First nemae is required", 400
        
        add_person(first_name, last_name, birth_date, death_date, gender, notes)
        return redirect(url_for("persons"))
    return render_template("person_add.html")

@app.route("/persons/<int:person_id>")
def person_detail(person_id):
    person = get_person(person_id)
    if person is None:
        return "Person not found", 404
    
    parents = get_parents(person_id)
    children = get_children(person_id)
    spouses = get_spouses(person_id)

    return render_template(
        "person_detail.html", 
        person=person,
        parents=parents,
        children=children,
        spouses=spouses,
    )

@app.route("/persons/<int:person_id>/edit", methods=["GET", "POST"])
def edit_person(person_id):
    person = get_person(person_id)
    if person is None:
        return "Person is not found", 404
    
    if request.method == "POST":
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name") or None
        birth_date = request.form.get("birth_date") or None
        death_date = request.form.get("death_date") or None
        gender = request.form.get("gender") or None
        notes = request.form.get("notes") or None

        if not first_name:
            return "First name is required", 400
        
        update_person(person_id, first_name, last_name, birth_date, death_date, gender, notes)
        return redirect(url_for("person_detail", person_id=person_id))
    
    return render_template("person_edit.html", person=person)

@app.route("/persons/<int:person_id>/relations/add", methods=["GET", "POST"])
def add_relation(person_id):
    person = get_person(person_id)
    if person is None:
        return "Person not found", 404

    people = get_all_persons()

    if request.method == "POST":
        relation_type = request.form.get("relation_type")
        relative_id = request.form.get("relative_id")

        if not relation_type or not relative_id:
            return "Relation type and relative are required", 400

        try:
            relative_id = int(relative_id)
        except ValueError:
            return "Invalid relative id", 400

        # защита от самосвязи
        if relative_id == person_id:
            return "Cannot create relation with self", 400

        if relation_type == "parent":
            # relative = родитель current
            add_relationship(
                person_id=relative_id,
                relative_id=person_id,
                relation_type="parent"
            )
        elif relation_type == "child":
            # relative = ребёнок current
            add_relationship(
                person_id=person_id,
                relative_id=relative_id,
                relation_type="parent"
            )
        elif relation_type == "spouse":
            # супруги — симметрично
            add_relationship(
                person_id=person_id,
                relative_id=relative_id,
                relation_type="spouse"
            )
            add_relationship(
                person_id=relative_id,
                relative_id=person_id,
                relation_type="spouse"
            )
        else:
            return "Unknown relation type", 400

        return redirect(url_for("person_detail", person_id=person_id))

    return render_template("relation_add.html", person=person, people=people)

@app.route("/persons/<int:person_id>/delete", methods=["POST"])
def delete_person_route(person_id):
    person = get_person(person_id)
    if person is None:
        return "Person not found", 404
    
    delete_person(person_id)
    return redirect(url_for("persons"))

@app.route("/init-db")
def init_db_route():
    init_db()
    return "Database initialized."

if __name__ == "__main__":
    app.run(debug=True)