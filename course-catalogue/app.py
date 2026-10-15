"""
course-catalogue microservice (Flask + psycopg2)

Owns course data (code, title, credits, semester, lecturer) in its own
Postgres database (course-db). Other services, such as feedback, read
courses only through this API and never touch course-db directly.
"""

import logging
import os

import psycopg2
import psycopg2.errors
import psycopg2.extras
from flask import Flask, jsonify, request
from flask_cors import CORS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [course-catalogue] %(levelname)s %(message)s")
log = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://course:password@course-db:5432/courses")
COLUMNS = "id, code, title, credits, semester, lecturer"


def query(sql, params=(), one=False):
    """Run one SQL statement in its own transaction and return the rows as dicts."""
    conn = psycopg2.connect(DATABASE_URL)
    try:
        # `with conn` commits on success and rolls back on error
        with conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall() if cur.description else []
    finally:
        conn.close()
    return (rows[0] if rows else None) if one else rows


@app.errorhandler(psycopg2.DataError)
def bad_value(e):
    return jsonify({"error": f"Invalid value: {e.diag.message_primary}"}), 400


@app.errorhandler(psycopg2.Error)
def db_error(e):
    log.error("Database error: %s", e)
    return jsonify({"error": "Database error"}), 500


@app.route("/")
def health():
    return jsonify({"service": "course-catalogue", "status": "ok"})


@app.route("/courses", methods=["GET"])
def list_courses():
    return jsonify(query(f"SELECT {COLUMNS} FROM courses ORDER BY code"))


@app.route("/courses/<int:course_id>", methods=["GET"])
def get_course(course_id):
    course = query(f"SELECT {COLUMNS} FROM courses WHERE id=%s", (course_id,), one=True)
    if not course:
        return jsonify({"error": "Course not found"}), 404
    return jsonify(course)


@app.route("/courses", methods=["POST"])
def add_course():
    data = request.get_json(silent=True) or {}
    missing = [f for f in ("code", "title") if not data.get(f)]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400
    try:
        course = query(
            f"INSERT INTO courses (code, title, credits, semester, lecturer) VALUES (%s, %s, %s, %s, %s) RETURNING {COLUMNS}",
            (data["code"].upper(), data["title"], data.get("credits", 15), data.get("semester"), data.get("lecturer")),
            one=True,
        )
    except psycopg2.errors.UniqueViolation:
        return jsonify({"error": f"Course {data['code']} already exists"}), 409
    log.info("Created course %s", course["code"])
    return jsonify(course), 201


@app.route("/courses/<int:course_id>", methods=["DELETE"])
def delete_course(course_id):
    if not query("DELETE FROM courses WHERE id=%s RETURNING id", (course_id,), one=True):
        return jsonify({"error": "Course not found"}), 404
    log.info("Deleted course %s", course_id)
    return jsonify({"message": "Deleted"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002)
