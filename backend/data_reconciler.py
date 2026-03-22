import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data"
RATINGS_FILE = DATA_DIR / "ratings.json"

NIELSEN_SHOWS = ["smackdown", "nxt", "dynamite", "collision", "tna"]
STREAMING_SHOWS = ["raw"]


def reconcile_entry(entries, tolerance=0.05):
    """Given a list of entries from different sources for the same date,
    pick the best value. If 2+ sources agree (within tolerance), use their average.
    Otherwise use the value from the most trusted source (first in list)."""
    if not entries:
        return None
    if len(entries) == 1:
        return entries[0]

    # Check if at least 2 sources agree on viewers
    for i in range(len(entries)):
        for j in range(i + 1, len(entries)):
            v1 = entries[i].get("viewers", 0)
            v2 = entries[j].get("viewers", 0)
            if v1 and v2 and abs(v1 - v2) / max(v1, v2) <= tolerance:
                # Agreement - average the two
                result = {"date": entries[i]["date"]}
                result["viewers"] = round((v1 + v2) / 2, 3)
                d1 = entries[i].get("demo")
                d2 = entries[j].get("demo")
                if d1 is not None and d2 is not None:
                    result["demo"] = round((d1 + d2) / 2, 2)
                elif d1 is not None:
                    result["demo"] = d1
                elif d2 is not None:
                    result["demo"] = d2
                return result

    # No agreement - use first source (WrestlingAttitude is primary)
    return entries[0]


def merge_sources(primary, backup, _unused=None):
    """Merge Nielsen and streaming data from two sources.

    Args:
        primary: WrestlingAttitude data {"nielsen": {...}, "streaming": {...}}
        backup: Wrestlenomics data (same format)
        _unused: Reserved for future third source. Pass None.

    Returns:
        Reconciled data in the same format.
    """
    sources = [("wrestlingattitude", primary), ("wrestlenomics", backup)]

    result_nielsen = {}
    result_streaming = {}

    # Reconcile Nielsen shows
    for show_id in NIELSEN_SHOWS:
        by_date = {}

        for source_name, source in sources:
            if not source:
                continue
            entries = source.get("nielsen", {}).get(show_id, [])
            for entry in entries:
                date = entry["date"]
                if date not in by_date:
                    by_date[date] = []
                by_date[date].append(entry)

        reconciled = []
        for date in sorted(by_date.keys()):
            entry = reconcile_entry(by_date[date])
            if entry:
                reconciled.append(entry)

        result_nielsen[show_id] = reconciled
        sources_count = sum(1 for _, s in sources
                          if s and s.get("nielsen", {}).get(show_id))
        logger.info("Reconciled %s: %d entries from %d sources",
                    show_id, len(reconciled), sources_count)

    # Reconcile streaming shows
    for show_id in STREAMING_SHOWS:
        by_date = {}

        for source_name, source in sources:
            if not source:
                continue
            entries = source.get("streaming", {}).get(show_id, [])
            for entry in entries:
                date = entry["date"]
                if date not in by_date:
                    by_date[date] = []
                by_date[date].append(entry)

        reconciled = []
        for date in sorted(by_date.keys()):
            entry = reconcile_entry(by_date[date])
            if entry:
                reconciled.append(entry)

        result_streaming[show_id] = reconciled

    # Keep ROH/NWA from primary only (YouTube data, not from backup sources)
    if primary:
        for show_id in ["roh", "nwa"]:
            result_streaming[show_id] = primary.get("streaming", {}).get(show_id, [])
    else:
        result_streaming["roh"] = []
        result_streaming["nwa"] = []

    return {"nielsen": result_nielsen, "streaming": result_streaming}


def save_reconciled_data(reconciled):
    """Save reconciled data to ratings.json. Never overwrite with less data."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    current = {}
    if RATINGS_FILE.exists():
        with open(RATINGS_FILE) as f:
            current = json.load(f)

    if not current:
        current = {
            "lastUpdated": None,
            "scrapeStatus": {"nielsen": "pending", "youtube": "pending"},
            "nielsen": {s: [] for s in NIELSEN_SHOWS},
            "streaming": {"raw": [], "roh": [], "nwa": []},
        }

    # Only update if we have more or equal data
    nielsen = current.get("nielsen", {})
    for show_id, entries in reconciled["nielsen"].items():
        existing = nielsen.get(show_id, [])
        if len(entries) >= len(existing):
            nielsen[show_id] = entries
        else:
            logger.warning(
                "Reconciled %s has fewer entries (%d vs %d), keeping existing",
                show_id, len(entries), len(existing),
            )

    streaming = current.get("streaming", {})
    for show_id, entries in reconciled["streaming"].items():
        existing = streaming.get(show_id, [])
        if len(entries) >= len(existing):
            streaming[show_id] = entries

    current["nielsen"] = nielsen
    current["streaming"] = streaming
    current["lastUpdated"] = datetime.now(timezone.utc).isoformat()
    current["scrapeStatus"]["nielsen"] = "ok"

    from file_utils import atomic_json_write
    atomic_json_write(RATINGS_FILE, current)

    logger.info("Reconciled data saved")
