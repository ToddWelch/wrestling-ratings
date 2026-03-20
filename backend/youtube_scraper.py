import os
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data"
RATINGS_FILE = DATA_DIR / "ratings.json"

# Channel upload playlist IDs (UU + channel ID minus UC prefix)
CHANNELS = {
    "roh": {
        "playlist": "UUo7GEWMfad_JxLPkkfhKhHg",
        "patterns": ["ROH", "Ring of Honor"],
        "name": "ROH",
    },
    "nwa": {
        "playlist": "UU37OZkBkljNaGZWTnQbFwlg",
        "patterns": ["NWA Powerrr", "POWERRR", "NWA Power"],
        "name": "NWA Powerrr",
    },
}


def get_youtube_service():
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        logger.info("YOUTUBE_API_KEY not set, skipping YouTube scrape")
        return None

    from googleapiclient.discovery import build
    return build("youtube", "v3", developerKey=api_key)


def fetch_recent_uploads(youtube, playlist_id, max_results=50):
    """Get recent video IDs from a channel's uploads playlist."""
    response = youtube.playlistItems().list(
        part="snippet",
        playlistId=playlist_id,
        maxResults=max_results,
    ).execute()

    videos = []
    for item in response.get("items", []):
        snippet = item["snippet"]
        videos.append({
            "video_id": snippet["resourceId"]["videoId"],
            "title": snippet["title"],
            "published": snippet["publishedAt"][:10],
        })
    return videos


def filter_episodes(videos, patterns):
    """Filter videos to only episode content matching title patterns."""
    episodes = []
    for v in videos:
        title_lower = v["title"].lower()
        if any(p.lower() in title_lower for p in patterns):
            # Skip clips, promos, highlights
            skip_words = ["highlight", "clip", "promo", "preview", "backstage", "exclusive"]
            if not any(w in title_lower for w in skip_words):
                episodes.append(v)
    return episodes


def get_view_counts(youtube, video_ids):
    """Get view counts for a list of video IDs."""
    if not video_ids:
        return {}

    counts = {}
    # API allows up to 50 IDs per request
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i + 50]
        response = youtube.videos().list(
            part="statistics",
            id=",".join(batch),
        ).execute()

        for item in response.get("items", []):
            vid = item["id"]
            stats = item.get("statistics", {})
            counts[vid] = int(stats.get("viewCount", 0))

    return counts


def scrape_youtube():
    """Scrape YouTube view counts for ROH and NWA."""
    youtube = get_youtube_service()
    if not youtube:
        return None

    logger.info("Starting YouTube scrape")
    results = {}

    for show_id, config in CHANNELS.items():
        try:
            videos = fetch_recent_uploads(youtube, config["playlist"])
            episodes = filter_episodes(videos, config["patterns"])

            if not episodes:
                logger.info("No episodes found for %s", config["name"])
                results[show_id] = []
                continue

            video_ids = [e["video_id"] for e in episodes]
            view_counts = get_view_counts(youtube, video_ids)

            entries = []
            for ep in episodes:
                views = view_counts.get(ep["video_id"], 0)
                entries.append({
                    "date": ep["published"],
                    "views": views,
                })

            results[show_id] = sorted(entries, key=lambda e: e["date"])
            logger.info("Found %d episodes for %s", len(entries), config["name"])

        except Exception as e:
            logger.error("YouTube scrape failed for %s: %s", config["name"], e)
            results[show_id] = []

    return results


def save_youtube_data(new_data):
    """Merge YouTube data into ratings.json."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    current = {}
    if RATINGS_FILE.exists():
        with open(RATINGS_FILE) as f:
            current = json.load(f)

    if not current:
        current = {
            "lastUpdated": None,
            "scrapeStatus": {"nielsen": "pending", "youtube": "pending"},
            "nielsen": {"smackdown": [], "nxt": [], "dynamite": [], "collision": [], "tna": []},
            "streaming": {"raw": [], "roh": [], "nwa": []},
        }

    streaming = current.get("streaming", {})
    for show_id, entries in new_data.items():
        existing = streaming.get(show_id, [])
        if len(entries) >= len(existing):
            streaming[show_id] = entries
        else:
            logger.warning(
                "New YouTube data for %s has fewer entries (%d vs %d), keeping existing",
                show_id, len(entries), len(existing),
            )

    current["streaming"] = streaming
    current["lastUpdated"] = datetime.now(timezone.utc).isoformat()
    current["scrapeStatus"]["youtube"] = "ok"

    with open(RATINGS_FILE, "w") as f:
        json.dump(current, f, indent=2)

    logger.info("YouTube data saved")


def run_youtube_scrape():
    """Entry point for scheduled YouTube scrape."""
    try:
        data = scrape_youtube()
        if data is None:
            # No API key
            if RATINGS_FILE.exists():
                with open(RATINGS_FILE) as f:
                    current = json.load(f)
                current["scrapeStatus"]["youtube"] = "no_api_key"
                with open(RATINGS_FILE, "w") as f:
                    json.dump(current, f, indent=2)
            return
        save_youtube_data(data)
    except Exception as e:
        logger.error("YouTube scrape failed: %s", e)
        if RATINGS_FILE.exists():
            with open(RATINGS_FILE) as f:
                current = json.load(f)
            current["scrapeStatus"]["youtube"] = "error"
            with open(RATINGS_FILE, "w") as f:
                json.dump(current, f, indent=2)
