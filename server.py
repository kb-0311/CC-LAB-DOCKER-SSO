"""Python Flask WebApp Auth0 integration example
"""

import json
import sqlite3
from os import environ as env
from urllib.parse import quote_plus, urlencode

from authlib.integrations.flask_client import OAuth
from dotenv import find_dotenv, load_dotenv
from flask import Flask, redirect, render_template, session, url_for , request

ENV_FILE = find_dotenv()
if ENV_FILE:
    load_dotenv(ENV_FILE)

app = Flask(__name__)
app.secret_key = env.get("APP_SECRET_KEY")

# SQLite database initialization and connection
DATABASE = 'database.db'

def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            note TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


oauth = OAuth(app)

oauth.register(
    "auth0",
    client_id=env.get("AUTH0_CLIENT_ID"),
    client_secret=env.get("AUTH0_CLIENT_SECRET"),
    client_kwargs={
        "scope": "openid profile email",
    },
    server_metadata_url=f'https://{env.get("AUTH0_DOMAIN")}/.well-known/openid-configuration',
)


# Controllers API
@app.route("/")
def home():
    user = session.get("user")
    if user:
        user_id = user.get("userinfo").get("sub")
        notes = get_user_notes(user_id)
        return render_template("home.html", notes=notes)
    else:
        # Redirect to login if user is not logged in
        return redirect("/login")



@app.route("/callback", methods=["GET", "POST"])
def callback():
    token = oauth.auth0.authorize_access_token()
    session["user"] = token
    return redirect("/")


@app.route("/login")
def login():
    return oauth.auth0.authorize_redirect(
        redirect_uri=url_for("callback", _external=True)
    )


@app.route("/logout")
def logout():
    session.clear()
    return redirect(
        "https://"
        + env.get("AUTH0_DOMAIN")
        + "/v2/logout?"
        + urlencode(
            {
                "returnTo": url_for("home", _external=True),
                "client_id": env.get("AUTH0_CLIENT_ID"),
            },
            quote_via=quote_plus,
        )
    )
    

@app.route("/add-note", methods=["POST"])
def add_note():
    if request.method == "POST":
        user_id = session.get("user").get("userinfo").get("sub")
        print(user_id)

        note = request.form.get("note")
        if note:
            conn = get_db()
            conn.execute("INSERT INTO notes (user_id, note) VALUES (?, ?)", (user_id, note))
            conn.commit()
            conn.close()
    return redirect("/")

@app.route("/delete-note/<int:note_id>", methods=["POST"])
def delete_note(note_id):
    if request.method == "POST":
        user_id = session.get("user").get("userinfo").get("sub")
        conn = get_db()
        conn.execute("DELETE FROM notes WHERE id=? AND user_id=?", (note_id, user_id))
        conn.commit()
        conn.close()
    return redirect("/")

@app.route("/update-note/<int:note_id>", methods=["POST"])
def update_note(note_id):
    if request.method == "POST":
        user_id = session.get("user").get("userinfo").get("sub")
        new_note = request.form.get("note")
        if new_note:
            conn = get_db()
            conn.execute("UPDATE notes SET note=? WHERE id=? AND user_id=?", (new_note, note_id, user_id))
            conn.commit()
            conn.close()
    return redirect("/")

def get_user_notes(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM notes WHERE user_id=?", (user_id,))
    notes = cursor.fetchall()
    conn.close()
    return notes


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=env.get("PORT", 3000))
