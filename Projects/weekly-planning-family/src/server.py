"""Local Flask server. GET / serves session.html; POST /save runs write_back; auto-shutdown after success."""
from __future__ import annotations

import os
import threading
import time

from flask import Flask, Response, jsonify, request

from src.config import Config
from src.constants import PROJECT_ROOT
from src.write_back import run_save


_SHUTDOWN_GRACE_SECONDS = 30


def create_app(cfg: Config) -> Flask:
    app = Flask(__name__)

    @app.route("/", methods=["GET"])
    def root():
        html_path = PROJECT_ROOT / "session.html"
        if not html_path.exists():
            return "<h1>session.html not yet generated — run the skill first.</h1>", 404
        return Response(html_path.read_text(), mimetype="text/html")

    @app.route("/save", methods=["POST"])
    def save():
        form = request.get_json(silent=True) or {}
        response = run_save(form, cfg)
        if response["status"] == "validation_error":
            return jsonify(response), 400
        threading.Thread(
            target=_delayed_shutdown,
            args=(_SHUTDOWN_GRACE_SECONDS,),
            daemon=True,
        ).start()
        return Response(response["summary_html"], mimetype="text/html"), 200

    return app


def _delayed_shutdown(delay_seconds: int) -> None:
    time.sleep(delay_seconds)
    os._exit(0)


def serve(cfg: Config) -> None:
    app = create_app(cfg)
    app.run(host="127.0.0.1", port=cfg.session.server_port, debug=False, use_reloader=False)


if __name__ == "__main__":
    from src.config import load_config
    from src.constants import CONFIG_PATH
    serve(load_config(CONFIG_PATH))
