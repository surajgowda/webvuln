from flask import Flask, request, render_template, redirect, session
import sqlite3
import os
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)
DB_NAME = "tables.db"
app.secret_key = "super-secret-key"   # used to sign session cookie


def init_db():
    if not os.path.exists(DB_NAME):
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                password TEXT
            )
        """)
        # Sample users
        cur.execute("INSERT INTO users VALUES (NULL, 'admin', 'admin123')")
        cur.execute("INSERT INTO users VALUES (NULL, 'user', 'user123')")

        cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            price INTEGER
        )
    """)

        cur.execute("DELETE FROM users")
        cur.execute("DELETE FROM products")

        cur.execute("INSERT INTO users VALUES (NULL, 'admin', 'admin123')")
        cur.execute("INSERT INTO users VALUES (NULL, 'user', 'user123')")

        cur.execute("INSERT INTO products VALUES (NULL, 'Laptop', 50000)")
        cur.execute("INSERT INTO products VALUES (NULL, 'Phone', 30000)")
        cur.execute("INSERT INTO products VALUES (NULL, 'Tablet', 20000)")

        conn.commit()
        conn.close()


@app.route("/comment", methods=["GET", "POST"])
def comments():
    if "user" not in session:
        return redirect("/")
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    if request.method == "POST":
        comment = request.form.get("comment", "")
        # ❌ Store user input as-is (XSS vulnerability)
        cur.execute("INSERT INTO comments (content) VALUES (?)", (comment,))
        conn.commit()
        return redirect("/comment")

    # Fetch all comments
    cur.execute("SELECT content FROM comments ORDER BY id DESC")
    comments = cur.fetchall()
    conn.close()

    return render_template("comments.html", comments=comments)

def get_db():
    return sqlite3.connect(DB_NAME)

def delete_comments_job():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("DELETE FROM comments")
    conn.commit()

    conn.close()

def start_scheduler():
    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(
        delete_comments_job,
        trigger="interval",
        minutes=1,
        id="delete_comments_job",
        replace_existing=True
    )
    scheduler.start()  

@app.route("/search", methods=["GET", "POST"])
def search():
    results = []
    query_used = ""

    if request.method == "POST":
        keyword = request.form.get("keyword")

        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()

        # ❌ VULNERABLE QUERY
        query_used = f"SELECT name, price FROM products WHERE name LIKE '%{keyword}%'"
        cur.execute(query_used)
        results = cur.fetchall()

        conn.close()

    return render_template("search.html", results=results, query_used=query_used)


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        cur = conn.cursor()
        try:
            # ❌ Password stored in plaintext (intentional for demo)
            cur.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, password)
            )
            conn.commit()
        except:
            return "Username already exists"
        finally:
            conn.close()

        return redirect("/")

    return render_template("signup.html")


@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        cur = conn.cursor()
        print(password)
        cur.execute("SELECT id FROM users WHERE username='" + username + "' AND password='" + password +"'")
        user = cur.fetchone()
        conn.close()

        if user:
            session["user"] = username
            return redirect("/dashboard")
        else:
            return "Invalid credentials"
    if "user" in session:
        return redirect("/dashboard")
    return render_template("login.html")


@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/")

    return render_template("dashboard.html", user=session["user"])


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/blind", methods=["GET", "POST"])
def blind():
    message = ""
    query_used = ""

    if request.method == "POST":
        username = request.form.get("username")

        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()

        # ❌ BLIND SQL INJECTION (Boolean-based)
        query_used = f"SELECT id FROM users WHERE username = '{username}'"
        cur.execute(query_used)

        if cur.fetchone():
            message = "✅ User exists"
        else:
            message = "❌ User does NOT exist"

        conn.close()

    return render_template(
        "blind.html",
        message=message,
        query_used=query_used
    )



if __name__ == "__main__":
    init_db()
    start_scheduler()
    app.run(debug=True)
