import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data"
STATUS_FILE = DATA_DIR / "scrape_status.json"


def _load():
    if STATUS_FILE.exists():
        with open(STATUS_FILE) as f:
            return json.load(f)
    return {}


def _save(data):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATUS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def update_status(source, status, entries_count=0, error_msg=None):
    """Update scrape status for a source.

    Args:
        source: "wrestlingattitude", "wrestlenomics", "wrestlinginc", "youtube"
        status: "success" or "failed"
        entries_count: number of entries scraped
        error_msg: error message if failed
    """
    data = _load()
    data[source] = {
        "lastScrape": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "entriesFound": entries_count,
    }
    if error_msg:
        data[source]["error"] = str(error_msg)[:200]
    _save(data)


def get_status():
    return _load()
