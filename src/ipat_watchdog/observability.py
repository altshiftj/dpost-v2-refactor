from flask import Flask, Response, request
import threading
import os
from waitress import serve

LOG_PATH = os.getenv("LOG_FILE_PATH", "C:/Watchdog/logs/watchdog.log")

app = Flask(__name__)

@app.route("/health")
def health():
    return {"status": "ok"}, 200

@app.route("/logs")
def logs():
    if not os.path.exists(LOG_PATH):
        return Response("Log file not found", status=404, mimetype="text/plain")

    # Optional tail query param
    try:
        tail_lines = int(request.args.get("tail", "0"))
    except ValueError:
        return Response("Invalid 'tail' parameter", status=400, mimetype="text/plain")

    try:
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        return Response(f"Failed to read log: {str(e)}", status=500, mimetype="text/plain")

    if tail_lines > 0:
        lines = lines[-tail_lines:]

    return Response("".join(lines), mimetype="text/plain")

def start_observability_server():
    # Waitress blocks the main thread, so we run it in a background thread
    thread = threading.Thread(
        target=serve,
        kwargs={"app": app, "host": "0.0.0.0", "port": 8001, "threads": 4}
    )
    thread.daemon = True
    thread.start()
