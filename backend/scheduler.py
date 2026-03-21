import os
import json
import logging
import requests
from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger(__name__)


def _send_alert(failed_sources):
    """Send Slack alert when 2+ scraper sources fail."""
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook_url:
        logger.warning("Slack alert skipped: SLACK_WEBHOOK_URL not configured")
        return

    source_list = "\n".join(f"  - {s}" for s in failed_sources)
    text = (
        f":warning: *Wrestling Ratings: {len(failed_sources)}/3 scrapers failed*\n\n"
        f"Failed sources:\n{source_list}\n\n"
        f"<https://wrestlingratings.welchcommercesystems.com/api/scrape-status|View Status>"
    )

    try:
        resp = requests.post(webhook_url, json={"text": text}, timeout=10)
        resp.raise_for_status()
        logger.info("Slack alert sent")
    except Exception as e:
        logger.error("Failed to send Slack alert: %s", e)


def run_full_scrape():
    """Run all three scrapers and reconcile the data."""
    from scraper import scrape_nielsen
    from scraper_wrestlenomics import scrape_wrestlenomics
    from scraper_wrestlinginc import scrape_wrestlinginc
    from data_reconciler import merge_sources, save_reconciled_data
    from scrape_status import update_status

    logger.info("Starting full multi-source scrape")

    # Primary: WrestlingAttitude
    primary = None
    try:
        from scraper import scrape_raw
        nielsen_data = scrape_nielsen()
        raw_data = scrape_raw()
        total = sum(len(v) for v in nielsen_data.values()) + len(raw_data)
        primary = {"nielsen": nielsen_data, "streaming": {"raw": raw_data}}
        update_status("wrestlingattitude", "success", total)
        logger.info("WrestlingAttitude scrape complete: %d entries", total)
    except Exception as e:
        update_status("wrestlingattitude", "failed", error_msg=str(e))
        logger.error("WrestlingAttitude scrape failed: %s", e)

    # Backup 1: Wrestlenomics
    backup1 = None
    try:
        backup1 = scrape_wrestlenomics()
        total = sum(len(v) for v in backup1.get("nielsen", {}).values())
        total += sum(len(v) for v in backup1.get("streaming", {}).values())
        update_status("wrestlenomics", "success", total)
        logger.info("Wrestlenomics scrape complete: %d entries", total)
    except Exception as e:
        update_status("wrestlenomics", "failed", error_msg=str(e))
        logger.error("Wrestlenomics scrape failed: %s", e)

    # Backup 2: WrestlingInc
    backup2 = None
    try:
        backup2 = scrape_wrestlinginc()
        total = sum(len(v) for v in backup2.get("nielsen", {}).values())
        total += sum(len(v) for v in backup2.get("streaming", {}).values())
        update_status("wrestlinginc", "success", total)
        logger.info("WrestlingInc scrape complete: %d entries", total)
    except Exception as e:
        update_status("wrestlinginc", "failed", error_msg=str(e))
        logger.error("WrestlingInc scrape failed: %s", e)

    # Check failure count and send alert if 2+ sources failed
    failures = []
    if not primary:
        failures.append("WrestlingAttitude")
    if not backup1:
        failures.append("Wrestlenomics")
    if not backup2:
        failures.append("WrestlingInc")

    if len(failures) >= 2:
        _send_alert(failures)

    # Reconcile and save
    if primary or backup1 or backup2:
        reconciled = merge_sources(primary, backup1, backup2)
        save_reconciled_data(reconciled)
        logger.info("Multi-source scrape and reconciliation complete")
    else:
        logger.error("All scrapers failed, keeping existing data")


def start_scheduler():
    from youtube_scraper import run_youtube_scrape
    from scrape_status import update_status

    def youtube_with_status():
        try:
            run_youtube_scrape()
            update_status("youtube", "success")
        except Exception as e:
            update_status("youtube", "failed", error_msg=str(e))

    scheduler = BackgroundScheduler()

    # Full multi-source scrape every 6 hours
    scheduler.add_job(run_full_scrape, "interval", hours=6, id="full_scrape")

    # YouTube scrape every 12 hours
    scheduler.add_job(youtube_with_status, "interval", hours=12, id="youtube_scrape")

    scheduler.start()
    logger.info("Scheduler started: Multi-source scrape every 6h, YouTube every 12h")

    # Run initial scrapes
    logger.info("Running initial scrapes")
    run_full_scrape()
    youtube_with_status()
