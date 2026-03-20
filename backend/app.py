import os
import json
import logging
import threading
from pathlib import Path
from flask import Flask, send_from_directory, jsonify, request
from scheduler import start_scheduler
from seo import register_seo_routes

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder="../frontend/dist", static_url_path="")

DATA_DIR = Path(__file__).parent / "data"
RATINGS_FILE = DATA_DIR / "ratings.json"


def load_ratings():
    if RATINGS_FILE.exists():
        with open(RATINGS_FILE) as f:
            return json.load(f)
    return {
        "lastUpdated": None,
        "scrapeStatus": {"nielsen": "pending", "youtube": "pending"},
        "nielsen": {"smackdown": [], "nxt": [], "dynamite": [], "collision": [], "tna": []},
        "streaming": {"raw": [], "roh": [], "nwa": []},
    }


@app.route("/api/ratings")
def api_ratings():
    data = load_ratings()
    from scrape_status import get_status
    data["scrapeDetails"] = get_status()
    return jsonify(data)


@app.route("/api/health")
def api_health():
    return jsonify({"status": "ok"})


@app.route("/api/scrape-status")
def api_scrape_status():
    from scrape_status import get_status
    return jsonify(get_status())


@app.route("/api/scrape", methods=["POST"])
def api_scrape():
    """Manually trigger a full scrape. Requires SCRAPE_KEY env var."""
    key = os.environ.get("SCRAPE_KEY")
    if not key or request.headers.get("X-Scrape-Key") != key:
        return jsonify({"error": "unauthorized"}), 401

    from scheduler import run_full_scrape
    from youtube_scraper import run_youtube_scrape

    def do_scrape():
        run_full_scrape()
        run_youtube_scrape()

    threading.Thread(target=do_scrape, daemon=True).start()
    return jsonify({"status": "scrape started"})


register_seo_routes(app, RATINGS_FILE)


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_spa(path):
    dist = Path(app.static_folder)
    if path and (dist / path).exists():
        return send_from_directory(dist, path)
    return send_from_directory(dist, "index.html")


if __name__ == "__main__":
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    start_scheduler()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), debug=True)
