"""
notification microservice (Flask, no database)

Mock email sender. Other services POST a notification here; instead of
sending a real email we write it to the container log and keep it in memory
so it can be listed via GET /notifications.
"""

import logging
import threading
from datetime import datetime, timezone

from flask import Flask, jsonify, request
from flask_cors import CORS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [notification] %(levelname)s %(message)s")
log = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Kept in memory only, so this list is lost when the container restarts. Fine for a mock service.
notifications = []
lock = threading.Lock()


@app.route("/")
def health():
    return jsonify({"service": "notification", "status": "ok"})


@app.route("/notifications", methods=["POST"])
def send_notification():
    data = request.get_json(silent=True) or {}
    missing = [f for f in ("to", "subject", "message") if not data.get(f)]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400

    with lock:
        note = {
            "id": len(notifications) + 1,
            "to": data["to"],
            "subject": data["subject"],
            "message": data["message"],
            "sent_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        notifications.append(note)
    log.info("EMAIL SENT to=%s subject=%r message=%r", note["to"], note["subject"], note["message"])
    return jsonify(note), 201


@app.route("/notifications", methods=["GET"])
def list_notifications():
    recipient = request.args.get("to")
    result = [n for n in notifications if not recipient or n["to"] == recipient]
    return jsonify(result[::-1])  # newest first


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5004)
