from flask import Flask, Response
import threading
import os

LOG_PATH = os.getenv("LOG_FILE_PATH", "Data/watchdog.log")

app = Flask(__name__)

@app.route("/health")
def health():
    return {"status": "ok"}, 200

@app.route("/logs")
def logs():
    if not os.path.exists(LOG_PATH):
        return "Log file not found", 404

    with open(LOG_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    return Response(content, mimetype="text/plain")


def start_observability_server():
    thread = threading.Thread(
        target=app.run,
        kwargs={"host": "0.0.0.0", "port": 8001, "debug": False, "use_reloader": False}
    )
    thread.daemon = True
    thread.start()
