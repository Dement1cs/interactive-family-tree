from flask import Flask, render_template, request, redirect, url_for
from db import init_db, get_all_persons, add_person, get_person

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
    return render_template("person_detail.html", person=person)

@app.route("/init-db")
def init_db_route():
    init_db()
    return "Database initialized."

if __name__ == "__main__":
    app.run(debug=True)