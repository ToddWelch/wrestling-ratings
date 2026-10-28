"""Gunicorn settings for production (see the Dockerfile CMD).

Gunicorn imports app:app and never runs app.py's __main__ block, so the
scrape scheduler is started here instead. It runs inside the worker, so
this must stay one worker: each extra worker would run its own scheduler
and scrape the sources again.
"""

workers = 1
# One worker serves every request, so give it threads (gthread worker)
# instead of the sync worker's one-request-at-a-time.
threads = 4


def post_worker_init(worker):
    from scheduler import start_scheduler
    start_scheduler()
