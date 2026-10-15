"""
student-profile microservice (Flask + psycopg2)

Purpose
-------
This file implements a small HTTP API that exposes CRUD operations for a
"students" resource and an endpoint for recording attendance.

How it fits into a microservice architecture
--------------------------------------------
- This application is a *backend microservice* that owns student data.
- It runs in its own Docker container and talks to a Postgres database
  running in a different container (service name: student-db).
- A separate frontend microservice (React) communicates with this API over HTTP.
- Containers are composed with docker-compose so services can reach each other
  by service name (e.g. student-db).

Important notes for students
----------------------------
- DATABASE_URL is read from the environment so the same code runs locally and
  in Docker. Example value used in docker-compose:
    postgresql://studentuser:studentpass@student-db:5432/studentsdb

- This is a teaching example: it uses direct psycopg2 connections (no pooling).
  For production you would use a connection pool or an ORM like SQLAlchemy.

- The Postgres database must be seeded (init.sql) with a `students` table that
  has at least columns: id (serial primary key), name (text), email (text),
  attendance (JSONB or text storing JSON array).
"""

from flask import Flask, jsonify, request
from flask_cors import CORS            # allows the React frontend to call this API
import psycopg2                        # PostgreSQL client library
import os
import json
import time

app = Flask(__name__)
CORS(app)  # permit Cross-Origin requests from the frontend during development

# DATABASE_URL read from environment so we can change DB location without changing code.
# Default value is useful for Docker Compose; in production put a secure value in env.
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgres://studentuser:studentpass@student-db:5432/studentsdb"
)

# -----------------------------
# Wait-and-retry for database
# -----------------------------
# When containers start, Postgres may take a few seconds to become ready.
# This loop tries to connect multiple times before giving up (useful in Docker).
max_retries = 20
for i in range(max_retries):
    try:
        conn = psycopg2.connect(DATABASE_URL)
        print("Connected to DB!")
        conn.close()
        break
    except psycopg2.OperationalError:
        # If the connection failed, wait and try again.
        print(f"DB connection failed ({i+1}/{max_retries}), retrying in 2s...")
        time.sleep(2)
else:
    # If we've retried max_retries times, raise an error and stop the service.
    raise Exception(f"Could not connect to the database after {max_retries} retries")

def get_connection():
    """
    Create and return a new psycopg2 database connection.

    Note:
    - Each call returns a *new* connection. Handlers must close connections and cursors.
    - For production, use a connection pool (psycopg2.pool or SQLAlchemy engine).
    """
    return psycopg2.connect(DATABASE_URL)


# -----------------------------
# Simple health endpoint
# -----------------------------
@app.route("/")
def home():
    """
    Health check and human-readable message.
    Frontend or a human tester can hit this endpoint to confirm the service is running.
    """
    return (
        "Hello from student-profile service (with Postgres DB)! "
        "This is a line of text to let you know that the API service is running smoothly with full CRUD capability"
    )


# -------------------------------------------
# GET /students  - List all students
# -------------------------------------------
# Example:
# curl http://localhost:5001/students
@app.route("/students", methods=["GET"])
def get_students():
    """
    Query the students table and return a JSON list of student objects.

    Each student object:
      { "id": int, "name": str, "email": str, "attendance": list }

    Notes:
    - We ORDER BY id to provide predictable results for students learning/testing.
    - attendance is stored in the DB as JSON (JSONB). We default to [] if null.
    """
    conn = get_connection()
    cur = conn.cursor()

    # Execute a SELECT query to retrieve the relevant columns.
    cur.execute("SELECT id, name, email, attendance FROM students ORDER BY id ASC")
    rows = cur.fetchall()

    # Close DB resources to avoid leaking connections.
    cur.close()
    conn.close()

    # Transform DB rows (tuples) into dictionaries for JSON serialization.
    students = [
        {"id": r[0], "name": r[1], "email": r[2], "attendance": r[3] or []}
        for r in rows
    ]
    return jsonify(students), 200


# -------------------------------------------
# GET /students/<id> - Get a single student
# -------------------------------------------
# Example:
# curl http://localhost:5001/students/3
@app.route("/students/<int:student_id>", methods=["GET"])
def get_student(student_id):
    """
    Return the student with the given id or a 404 error if not found.
    Uses parameterized SQL to prevent SQL injection (important security practice).
    """
    conn = get_connection()
    cur = conn.cursor()

    # Parameterized query: %s placeholders and tuple of values avoids SQL injection.
    cur.execute(
        "SELECT id, name, email, attendance FROM students WHERE id=%s",
        (student_id,)
    )
    row = cur.fetchone()

    cur.close()
    conn.close()

    if not row:
        return jsonify({"error": "Student not found"}), 404

    student = {"id": row[0], "name": row[1], "email": row[2], "attendance": row[3] or []}
    return jsonify(student), 200


# -------------------------------------------
# POST /students - Add a new student
# -------------------------------------------
# Example:
# curl -X POST -H "Content-Type: application/json" \
#   -d '{"name":"New Student","email":"new@student.example"}' \
#   http://localhost:5001/students
@app.route("/students", methods=["POST"])
def add_student():
    """
    Create a new student.

    Validates that 'name' and 'email' are provided.
    Inserts a new row and returns the created resource with its new id (HTTP 201).
    """
    data = request.get_json() or {}

    # Basic validation for required fields.
    if "name" not in data or "email" not in data:
        return jsonify({"error": "name and email are required"}), 400

    conn = get_connection()
    cur = conn.cursor()

    # Use parameterized INSERT to safely add the row; attendance starts as an empty JSON array.
    cur.execute(
        "INSERT INTO students (name, email, attendance) VALUES (%s, %s, %s) RETURNING id",
        (data["name"], data["email"], json.dumps([]))
    )
    new_id = cur.fetchone()[0]
    conn.commit()

    cur.close()
    conn.close()

    # Return the new resource with HTTP 201 "Created"
    return jsonify({
        "id": new_id,
        "name": data["name"],
        "email": data["email"],
        "attendance": []
    }), 201


# -------------------------------------------
# PUT /students/<id> - Update a student
# -------------------------------------------
# Example:
# curl -X PUT -H "Content-Type: application/json" \
#   -d '{"name":"Updated Name"}' \
#   http://localhost:5001/students/5
@app.route("/students/<int:student_id>", methods=["PUT"])
def update_student(student_id):
    """
    Update one or more fields of an existing student.

    We build the SET clause dynamically based on fields provided in the JSON payload.
    The values themselves remain parameterized to avoid SQL injection.

    Note: Be careful if you accept field names from users (not done here) — never
    insert raw user input into SQL fragments.
    """
    data = request.get_json() or {}
    fields = []
    values = []

    # Collect only updated fields; these strings are static, values are parameterized.
    if "name" in data:
        fields.append("name=%s")
        values.append(data["name"])
    if "email" in data:
        fields.append("email=%s")
        values.append(data["email"])

    if not fields:
        return jsonify({"error": "No updatable fields provided"}), 400

    # Append student_id as the last parameter for the WHERE clause
    values.append(student_id)

    conn = get_connection()
    cur = conn.cursor()

    # The SQL string includes placeholders for values and uses parameterized values tuple.
    cur.execute(
        f"UPDATE students SET {', '.join(fields)} WHERE id=%s RETURNING id, name, email, attendance",
        tuple(values)
    )
    row = cur.fetchone()
    conn.commit()

    cur.close()
    conn.close()

    if not row:
        return jsonify({"error": "Student not found"}), 404

    return jsonify({"id": row[0], "name": row[1], "email": row[2], "attendance": row[3] or []}), 200


# -------------------------------------------
# DELETE /students/<id> - Remove a student
# -------------------------------------------
# Example:
# curl -X DELETE http://localhost:5001/students/7
@app.route("/students/<int:student_id>", methods=["DELETE"])
def delete_student(student_id):
    """
    Delete the student row and return a 200 message or 404 if the row did not exist.
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM students WHERE id=%s RETURNING id", (student_id,))
    deleted = cur.fetchone()
    conn.commit()

    cur.close()
    conn.close()

    if not deleted:
        return jsonify({"error": "Student not found"}), 404

    return jsonify({"message": "Deleted"}), 200


# -------------------------------------------
# POST /students/<id>/attendance - record attendance
# -------------------------------------------
# Example:
# curl -X POST -H "Content-Type: application/json" \
#   -d '{"date":"2025-10-05","status":"Present"}' \
#   http://localhost:5001/students/3/attendance
@app.route("/students/<int:student_id>/attendance", methods=["POST"])
def record_attendance(student_id):
    """
    Append an attendance record (dict with 'date' and 'status') to the student's
    attendance JSON array in the database.

    Notes:
    - This implementation reads the current JSON value into Python, appends to it,
      then writes it back. This is simple and good for teaching, but it has
      race conditions if multiple writers update the same row concurrently.
    - For production, consider using a DB-side JSONB operation or a transaction
      with SELECT ... FOR UPDATE to ensure correctness under concurrency.
    """
    data = request.get_json() or {}

    if "date" not in data or "status" not in data:
        return jsonify({"error": "date and status are required"}), 400

    conn = get_connection()
    cur = conn.cursor()

    # Fetch current attendance JSON array from DB
    cur.execute("SELECT attendance FROM students WHERE id=%s", (student_id,))
    row = cur.fetchone()

    if not row:
        cur.close()
        conn.close()
        return jsonify({"error": "Student not found"}), 404

    attendance = row[0] or []
    attendance.append({"date": data["date"], "status": data["status"]})

    # Store the updated attendance array back in the DB (as JSON text)
    cur.execute("UPDATE students SET attendance=%s WHERE id=%s", (json.dumps(attendance), student_id))
    conn.commit()

    cur.close()
    conn.close()

    return jsonify({"id": student_id, "attendance": attendance}), 200


# -----------------------------
# Run the Flask dev server
# -----------------------------
if __name__ == "__main__":
    """
    For local development we run the Flask built-in server.
    In production (inside Docker), use a real WSGI server like gunicorn for stability:
      gunicorn -w 4 -b 0.0.0.0:5001 app:app
    """
    app.run(host="0.0.0.0", port=5001, debug=True)
