from flask import Flask, render_template
from db import init_db, get_all_persons

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


@app.route("/init-db")
def init_db_route():
    init_db()
    return "Database initialized."

if __name__ == "__main__":
    app.run(debug=True)