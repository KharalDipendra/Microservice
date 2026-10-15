"""
feedback microservice (Flask + psycopg2 + requests)

Lets students submit feedback on courses and stores it in its own Postgres
database (feedback-db).

Service-to-service communication (HTTP, synchronous):
  1. student-profile   GET  /students/<id>   - check the student exists, get their email
  2. course-catalogue  GET  /courses/<id>    - check the course exists, get its code
  3. notification      POST /notifications   - "email" the student a confirmation

If student-profile or course-catalogue is down we cannot validate the request,
so we return 503. If only notification is down the feedback is still saved
(it is not critical) and the response says notification_sent: false.

Reliable notifications (outbox pattern):
  The confirmation email is written to the notification_outbox table in the same
  transaction as the feedback. We try to deliver it straight away; if that fails,
  a background thread retries unsent emails every RETRY_INTERVAL seconds, so they
  are delivered automatically once the notification service is back.

Duplicate requests:
  A student can give one feedback per course (UNIQUE constraint). Submitting the
  same feedback twice returns 409 instead of creating a duplicate.
"""

import logging
import os
import threading
import time

import psycopg2
import psycopg2.errors
import psycopg2.extras
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [feedback] %(levelname)s %(message)s")
log = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://feedback:password@feedback-db:5432/feedback")
STUDENT_SERVICE_URL = os.getenv("STUDENT_SERVICE_URL", "http://student-profile:5001")
COURSE_SERVICE_URL = os.getenv("COURSE_SERVICE_URL", "http://course-catalogue:5002")
NOTIFICATION_SERVICE_URL = os.getenv("NOTIFICATION_SERVICE_URL", "http://notification:5004")
TIMEOUT = 3  # seconds; never let a slow downstream service hang this one
RETRY_INTERVAL = int(os.getenv("RETRY_INTERVAL", "15"))  # seconds between outbox retries

FEEDBACK_SELECT = """
    SELECT f.id, f.student_id, f.course_id, f.rating, f.comment, f.created_at,
           (o.sent_at IS NOT NULL) AS notification_sent
    FROM feedback f LEFT JOIN notification_outbox o ON o.feedback_id = f.id
"""


class UpstreamError(Exception):
    """A service we depend on was unreachable or returned an unexpected error."""


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


def fetch(url):
    """GET a resource from another service. Returns the JSON body, or None on 404."""
    try:
        resp = requests.get(url, timeout=TIMEOUT)
    except requests.RequestException as e:
        raise UpstreamError(f"{url} unreachable: {e}") from e
    if resp.status_code == 404:
        return None
    if not resp.ok:
        raise UpstreamError(f"{url} returned {resp.status_code}")
    return resp.json()


def notify(to, subject, message):
    """Send a mock email via the notification service. Returns True if it was accepted."""
    try:
        resp = requests.post(
            f"{NOTIFICATION_SERVICE_URL}/notifications",
            json={"to": to, "subject": subject, "message": message},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        return True
    except requests.RequestException as e:
        log.warning("Notification failed, will retry later: %s", e)
        return False


def deliver(email):
    """Try to send one outbox email and record the result. Returns True if delivered."""
    sent = notify(email["recipient"], email["subject"], email["message"])
    query(
        "UPDATE notification_outbox SET attempts = attempts + 1, sent_at = CASE WHEN %s THEN now() END WHERE id=%s",
        (sent, email["id"]),
    )
    return sent


def retry_unsent_notifications():
    """Background loop: re-send emails that could not be delivered earlier."""
    while True:
        time.sleep(RETRY_INTERVAL)
        try:
            # Only rows older than a few seconds, so we don't race the request that is
            # sending its own email right now.
            # Note: this assumes only one feedback container. With more than one, two
            # workers could grab the same row (would need SELECT ... FOR UPDATE SKIP LOCKED).
            pending = query(
                "SELECT id, recipient, subject, message FROM notification_outbox "
                "WHERE sent_at IS NULL AND created_at < now() - interval '5 seconds' ORDER BY id LIMIT 50"
            )
            for email in pending:
                if not deliver(email):
                    break  # notification service still down, try again next round
                log.info("Retry succeeded: delivered queued notification %s to %s", email["id"], email["recipient"])
        except Exception:
            log.exception("Outbox retry round failed")


@app.errorhandler(UpstreamError)
def upstream_error(e):
    log.error("Upstream error: %s", e)
    return jsonify({"error": "A dependent service is unavailable, please try again later"}), 503


@app.errorhandler(psycopg2.Error)
def db_error(e):
    log.error("Database error: %s", e)
    return jsonify({"error": "Database error"}), 500


@app.route("/")
def health():
    return jsonify({"service": "feedback", "status": "ok"})


@app.route("/feedback", methods=["GET"])
def list_feedback():
    """List feedback, optionally filtered with ?course_id= and/or ?student_id=."""
    filters, params = [], []
    for field in ("course_id", "student_id"):
        value = request.args.get(field)
        if value is not None:
            if not value.isdigit():
                return jsonify({"error": f"{field} must be an integer"}), 400
            filters.append(f"f.{field}=%s")
            params.append(int(value))
    where = f"WHERE {' AND '.join(filters)}" if filters else ""
    return jsonify(query(f"{FEEDBACK_SELECT} {where} ORDER BY f.created_at DESC", params))


@app.route("/feedback/<int:feedback_id>", methods=["GET"])
def get_feedback(feedback_id):
    row = query(f"{FEEDBACK_SELECT} WHERE f.id=%s", (feedback_id,), one=True)
    if not row:
        return jsonify({"error": "Feedback not found"}), 404
    return jsonify(row)


@app.route("/feedback/summary", methods=["GET"])
def summary():
    """Number of reviews and average rating per course."""
    return jsonify(query(
        "SELECT course_id, COUNT(*) AS count, ROUND(AVG(rating), 2)::float AS average_rating "
        "FROM feedback GROUP BY course_id ORDER BY course_id"
    ))


@app.route("/feedback", methods=["POST"])
def submit_feedback():
    data = request.get_json(silent=True) or {}

    # 1. Validate the request body
    try:
        student_id, course_id, rating = int(data["student_id"]), int(data["course_id"]), int(data["rating"])
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "student_id, course_id and rating are required integers"}), 400
    if not 1 <= rating <= 5:
        return jsonify({"error": "rating must be between 1 and 5"}), 400

    # 2. Validate references by asking the services that own that data
    student = fetch(f"{STUDENT_SERVICE_URL}/students/{student_id}")
    if not student:
        return jsonify({"error": f"Student {student_id} not found"}), 404
    course = fetch(f"{COURSE_SERVICE_URL}/courses/{course_id}")
    if not course:
        return jsonify({"error": f"Course {course_id} not found"}), 404

    # 3. Save the feedback and its confirmation email in ONE transaction (outbox pattern)
    email = {
        "recipient": student["email"],
        "subject": f"Thanks for your feedback on {course['code']}",
        "message": f"Kia ora {student['name']}, we received your {rating}/5 rating for {course['code']} {course['title']}.",
    }
    try:
        row = query(
            """
            WITH f AS (
                INSERT INTO feedback (student_id, course_id, rating, comment) VALUES (%s, %s, %s, %s)
                RETURNING id, student_id, course_id, rating, comment, created_at
            ), o AS (
                INSERT INTO notification_outbox (feedback_id, recipient, subject, message)
                SELECT id, %s, %s, %s FROM f
                RETURNING id
            )
            SELECT f.*, o.id AS outbox_id FROM f, o
            """,
            (student_id, course_id, rating, data.get("comment"), email["recipient"], email["subject"], email["message"]),
            one=True,
        )
    except psycopg2.errors.UniqueViolation:
        return jsonify({"error": f"{student['name']} has already submitted feedback for {course['code']}"}), 409
    log.info("Feedback %s saved: student=%s course=%s rating=%s", row["id"], student_id, course["code"], rating)

    # 4. Notify now (best effort); if it fails the background job retries it
    email["id"] = row.pop("outbox_id")
    row["notification_sent"] = deliver(email)
    return jsonify(row), 201


if __name__ == "__main__":
    threading.Thread(target=retry_unsent_notifications, daemon=True).start()
    app.run(host="0.0.0.0", port=5003)
