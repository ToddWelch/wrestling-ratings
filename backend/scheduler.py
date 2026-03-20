import logging
from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger(__name__)


def run_full_scrape():
    """Run all three scrapers and reconcile the data."""
    from scraper import scrape_nielsen
    from scraper_wrestlenomics import scrape_wrestlenomics
    from scraper_wrestlinginc import scrape_wrestlinginc
    from data_reconciler import merge_sources, save_reconciled_data

    logger.info("Starting full multi-source scrape")

    # Primary: WrestlingAttitude
    primary = None
    try:
        nielsen_data = scrape_nielsen()
        primary = {"nielsen": nielsen_data, "streaming": {"raw": []}}
        logger.info("WrestlingAttitude scrape complete")
    except Exception as e:
        logger.error("WrestlingAttitude scrape failed: %s", e)

    # Backup 1: Wrestlenomics
    backup1 = None
    try:
        backup1 = scrape_wrestlenomics()
        logger.info("Wrestlenomics scrape complete")
    except Exception as e:
        logger.error("Wrestlenomics scrape failed: %s", e)

    # Backup 2: WrestlingInc
    backup2 = None
    try:
        backup2 = scrape_wrestlinginc()
        logger.info("WrestlingInc scrape complete")
    except Exception as e:
        logger.error("WrestlingInc scrape failed: %s", e)

    # Reconcile and save
    if primary or backup1 or backup2:
        reconciled = merge_sources(primary, backup1, backup2)
        save_reconciled_data(reconciled)
        logger.info("Multi-source scrape and reconciliation complete")
    else:
        logger.error("All scrapers failed, keeping existing data")


def start_scheduler():
    from youtube_scraper import run_youtube_scrape

    scheduler = BackgroundScheduler()

    # Full multi-source scrape every 6 hours
    scheduler.add_job(run_full_scrape, "interval", hours=6, id="full_scrape")

    # YouTube scrape every 12 hours
    scheduler.add_job(run_youtube_scrape, "interval", hours=12, id="youtube_scrape")

    scheduler.start()
    logger.info("Scheduler started: Multi-source scrape every 6h, YouTube every 12h")

    # Run initial scrapes
    logger.info("Running initial scrapes")
    run_full_scrape()
    run_youtube_scrape()
