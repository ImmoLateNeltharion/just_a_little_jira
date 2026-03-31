import sqlite3
import os
from datetime import datetime
from flask import Flask, render_template, request, jsonify, g

app = Flask(__name__)
DB_PATH = os.environ.get("DB_PATH", "data/jira.db")


def get_db():
    if "db" not in g:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db


@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db:
        db.close()


def init_db():
    db = get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            status TEXT DEFAULT 'open' CHECK(status IN ('open','in_progress','done')),
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
            text TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
            text TEXT NOT NULL,
            answer TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            answered_at TEXT
        );
    """)
    db.commit()


with app.app_context():
    init_db()


# --- Pages ---

@app.route("/")
def index():
    return render_template("index.html")


# --- Tasks API ---

@app.route("/api/tasks", methods=["GET"])
def list_tasks():
    db = get_db()
    status = request.args.get("status")
    if status:
        rows = db.execute(
            "SELECT * FROM tasks WHERE status = ? ORDER BY updated_at DESC", (status,)
        ).fetchall()
    else:
        rows = db.execute("SELECT * FROM tasks ORDER BY updated_at DESC").fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/tasks", methods=["POST"])
def create_task():
    data = request.json
    if not data or not data.get("title", "").strip():
        return jsonify({"error": "title is required"}), 400
    db = get_db()
    cur = db.execute(
        "INSERT INTO tasks (title, description) VALUES (?, ?)",
        (data["title"].strip(), data.get("description", "").strip()),
    )
    db.commit()
    task = db.execute("SELECT * FROM tasks WHERE id = ?", (cur.lastrowid,)).fetchone()
    return jsonify(dict(task)), 201


@app.route("/api/tasks/<int:task_id>", methods=["PUT"])
def update_task(task_id):
    data = request.json
    db = get_db()
    task = db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if not task:
        return jsonify({"error": "not found"}), 404
    title = data.get("title", task["title"]).strip()
    description = data.get("description", task["description"]).strip()
    status = data.get("status", task["status"])
    if status not in ("open", "in_progress", "done"):
        return jsonify({"error": "invalid status"}), 400
    db.execute(
        "UPDATE tasks SET title=?, description=?, status=?, updated_at=datetime('now') WHERE id=?",
        (title, description, status, task_id),
    )
    db.commit()
    task = db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return jsonify(dict(task))


@app.route("/api/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    db = get_db()
    db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    db.commit()
    return "", 204


# --- Comments API ---

@app.route("/api/tasks/<int:task_id>/comments", methods=["GET"])
def list_comments(task_id):
    db = get_db()
    rows = db.execute(
        "SELECT * FROM comments WHERE task_id = ? ORDER BY created_at ASC", (task_id,)
    ).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/tasks/<int:task_id>/comments", methods=["POST"])
def create_comment(task_id):
    data = request.json
    if not data or not data.get("text", "").strip():
        return jsonify({"error": "text is required"}), 400
    db = get_db()
    cur = db.execute(
        "INSERT INTO comments (task_id, text) VALUES (?, ?)",
        (task_id, data["text"].strip()),
    )
    db.execute("UPDATE tasks SET updated_at=datetime('now') WHERE id=?", (task_id,))
    db.commit()
    comment = db.execute("SELECT * FROM comments WHERE id = ?", (cur.lastrowid,)).fetchone()
    return jsonify(dict(comment)), 201


# --- Questions API ---

@app.route("/api/tasks/<int:task_id>/questions", methods=["GET"])
def list_questions(task_id):
    db = get_db()
    rows = db.execute(
        "SELECT * FROM questions WHERE task_id = ? ORDER BY created_at ASC", (task_id,)
    ).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/tasks/<int:task_id>/questions", methods=["POST"])
def create_question(task_id):
    data = request.json
    if not data or not data.get("text", "").strip():
        return jsonify({"error": "text is required"}), 400
    db = get_db()
    cur = db.execute(
        "INSERT INTO questions (task_id, text) VALUES (?, ?)",
        (task_id, data["text"].strip()),
    )
    db.execute("UPDATE tasks SET updated_at=datetime('now') WHERE id=?", (task_id,))
    db.commit()
    q = db.execute("SELECT * FROM questions WHERE id = ?", (cur.lastrowid,)).fetchone()
    return jsonify(dict(q)), 201


@app.route("/api/questions/<int:q_id>/answer", methods=["PUT"])
def answer_question(q_id):
    data = request.json
    if not data or not data.get("answer", "").strip():
        return jsonify({"error": "answer is required"}), 400
    db = get_db()
    q = db.execute("SELECT * FROM questions WHERE id = ?", (q_id,)).fetchone()
    if not q:
        return jsonify({"error": "not found"}), 404
    db.execute(
        "UPDATE questions SET answer=?, answered_at=datetime('now') WHERE id=?",
        (data["answer"].strip(), q_id),
    )
    db.execute("UPDATE tasks SET updated_at=datetime('now') WHERE id=?", (q["task_id"],))
    db.commit()
    q = db.execute("SELECT * FROM questions WHERE id = ?", (q_id,)).fetchone()
    return jsonify(dict(q))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=True)
