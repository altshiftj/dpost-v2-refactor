"""Small Flask app exposing health and log viewing endpoints for operators."""

from flask import Flask, Response, request, render_template_string
import threading
import os
import json
from waitress import serve

LOG_PATH = os.getenv("LOG_FILE_PATH", "C:/Watchdog/logs/watchdog.log")

app = Flask(__name__)

@app.route("/health")
def health():
    return {"status": "ok"}, 200

@app.route("/logs")
def logs_html():
    if not os.path.exists(LOG_PATH):
        return Response("Log file not found", status=404, mimetype="text/plain")

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

    parsed = []
    for line in lines:
        try:
            obj = json.loads(line)
            parsed.append(json.dumps(obj, indent=2))
        except json.JSONDecodeError:
            parsed.append(line.strip())

    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Log Viewer</title>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/themes/prism.css">
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            input[type="text"] { width: 100%; padding: 10px; font-size: 1em; margin-bottom: 10px; }
            pre { background: #f5f5f5; padding: 10px; border-radius: 6px; overflow: auto; }
        </style>
    </head>
    <body>
        <h2>Log Viewer</h2>
        <input type="text" id="filterInput" placeholder="Filter logs (case-insensitive)...">
        <div id="logContainer">
            {% for log in logs %}
            <pre class="language-json"><code>{{ log }}</code></pre>
            {% endfor %}
        </div>

        <script src="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/prism.js"></script>
        <script>
            const input = document.getElementById('filterInput');
            input.addEventListener('input', function() {
                const query = input.value.toLowerCase();
                const blocks = document.querySelectorAll('#logContainer pre');
                blocks.forEach(block => {
                    const text = block.innerText.toLowerCase();
                    block.style.display = text.includes(query) ? '' : 'none';
                });
            });
        </script>
    </body>
    </html>
    """

    return render_template_string(html_template, logs=parsed)

def start_observability_server(host: str = "0.0.0.0", port: int = 8001, threads: int = 4) -> threading.Thread:
    """Start the Waitress-powered observability server in a background thread."""
    thread = threading.Thread(
        target=serve,
        kwargs={"app": app, "host": host, "port": port, "threads": threads},
        name="observability-server",
        daemon=True,
    )
    thread.start()
    return thread
