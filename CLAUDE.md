# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Global rules pointer

Behavior rules, orchestrator process, agent system, coding discipline,
and infrastructure gotchas live in the global Claude config:

- `/home/todd/.claude/CLAUDE.md` (always-loaded rule book)
- `/home/todd/.claude/persona-rules.md` (Todd's identity + personal-style layer)

This file (`/home/todd/projects/Wrestling Ratings/CLAUDE.md`) holds
Wrestling-Ratings-specific guidance only: project overview, current
state, development commands, architecture (Flask backend + scrapers
+ Recharts SPA), key constraints (Nielsen parsing quirks, SEO
rendering, color theme), and environment variables.

---

## Project Overview

A Flask + React single-page application that displays interactive historical TV ratings charts for professional wrestling shows. Nielsen TV ratings (viewers + key demo) for 5 shows, plus a separate streaming/digital views section for Netflix/YouTube-based shows. Uses Recharts for charting.

**Deploy target:** Railway at `wrestlingratings.welchcommercesystems.com`

## Current State (2026-10-28)

Built and deployed; see `SESSION_LOG.md` (newest first) for what changed and what is open.

- **Railway:** project "Pro Wrestling Ratings" (id `aeca7a55-6196-4248-8a08-55a30de8bdfd`), service `wrestling-ratings`, environment `production`, region asia-southeast1. Auto-deploys from `main`. Service URL `wrestling-ratings-production.up.railway.app`. Variables (names only): `SCRAPE_KEY`, `SLACK_WEBHOOK_URL`, `YOUTUBE_API_KEY`.
- **Custom domain:** attached in Railway, but Cloudflare (zone `welchcommercesystems.com`) has never had the `wrestlingratings` CNAME, so the hostname does not resolve. Required record: `CNAME wrestlingratings -> xn0jbavb.up.railway.app`. The Cloudflare token on this box cannot write that zone; it is a Todd action.
- **Data pipeline:** `backend/gunicorn.conf.py` starts the APScheduler jobs in the worker (one worker, by design). Before 2026-10-28 the scheduler never ran in production, so the site served the launch-day seed file.
- **Sources:** WrestlingAttitude year pages (2025 uses the paragraph layout, 2026 the h3 + table layout; `scraper.parse_page` handles both) and Wrestlenomics article URLs (`/articles/YYYY/`). `URLS` in `backend/scraper.py` needs a 2027 entry in January 2027 or 2027 data will not appear. Give it an `EXPECTED_SHOWS` entry listing only the shows that already have 2027 rows, then widen it; listing all six at once fails the whole source until every show has aired once (Raw's numbers lag about 8 days).
- **Deferred findings:** `CARRY_FORWARD.md`, ranked. The top item replaces the fewer-entries guard with a merge by date.
- **ROH (YouTube) is switched off** in `backend/youtube_scraper.py`: its uploads are clips and matches, not episodes.
- **Seed data:** `backend/data/ratings.json` is the deploy seed (the container disk is ephemeral). It was regenerated from a clean scrape on 2026-10-28; the original seed was contaminated.
- **SEO:** post drafts and an on-page fix list in `docs/seo/` (drafts, not published).
- `WRESTLING-RATINGS.md` is the original spec; `wrestling-ratings.jsx` is the original reference component.

## Development Commands

```bash
# Tests
python -m pytest -q tests

# Backend (dev server; starts the scheduler, which scrapes the live sources and writes backend/data/)
cd backend && pip install -r ../requirements.txt && python app.py

# Production-equivalent run (needs frontend/dist built). It scrapes the live sources and
# rewrites backend/data/ratings.json, the tracked deploy seed, so run it from a copy
# unless you mean to regenerate the seed
gunicorn --config backend/gunicorn.conf.py --bind 127.0.0.1:8080 --chdir backend app:app

# Frontend (dev with Vite, proxies API to Flask)
cd frontend && npm install && npm run dev

# Frontend build
cd frontend && npm run build

# Deploy: Railway auto-deploys from main, so merging a PR deploys (needs Todd's approval)
```

## Architecture

- **Flask backend** serves the API (`/api/ratings`, `/api/health`), SEO routes (`/sitemap.xml`, `/robots.txt`), and the static Vite-built React app
- **Nielsen scraper** (`scraper.py`) parses WrestlingAttitude.com pages for TV ratings data. In the paragraph layout (2025 page) viewer numbers use European-style comma as decimal separator ("1,175" = 1.175M); the table layout (2026 page) uses a period ("1.175 M"). `parse_viewer_number` handles both. Table columns are found by header text. A page that fails to load, or any show in `EXPECTED_SHOWS` for that year with no valid entries, raises `ScrapeError`; every `URLS` year needs an `EXPECTED_SHOWS` entry
- **Wrestlenomics scraper** (`scraper_wrestlenomics.py`) is the backup source, parsed from article URL slugs. The URL year is the publication year, so `air_date` moves a date that would land in the future back one year (late-December shows written up in January). Zero parsed entries raises `ScrapeError`
- **Alerts:** `scheduler.run_full_scrape` sends a Slack alert (`SLACK_WEBHOOK_URL`) when either source goes from not-failed to failed, once per outage. The backup alone cannot refresh the chart (the fewer-entries guard keeps the primary's longer lists), so a WrestlingAttitude failure freezes the site
- **`lastUpdated`** (the site's "Last updated" and the sitemap `lastmod`) moves only when stored data changes
- **YouTube scraper** (`youtube_scraper.py`) uses YouTube Data API v3. NWA was removed in March 2026 and ROH is switched off (`DISABLED_CHANNELS`), so it currently scrapes nothing
- **APScheduler** (started from `gunicorn.conf.py`) runs the two-source scrape every 6 hours and YouTube every 12 hours, both on one thread, first run at boot
- **Data store** is `backend/data/ratings.json` - never overwrite with less data than currently exists
- **Frontend** is a Recharts-based SPA with metric toggle (viewers/key demo), time range filters (3M/6M/1Y/ALL), and show toggles. Polls `/api/ratings` every 10 minutes

## Key Constraints

- No em dashes anywhere in the codebase or UI text
- SEO text content in React must render on initial load (no lazy loading) - critical for Google indexing
- Nielsen methodology changed Sep 26, 2025 - mark with reference line on chart
- TNA iMPACT data only exists from Jan 2026 onward
- SmackDown entries sometimes have "(on SyFy)" appended - strip during parsing
- Dark green color theme: page bg `#070f0b`, accent `#4ade80`, card bg `#0c1812`

## Environment Variables

- `YOUTUBE_API_KEY` - YouTube Data API v3 key (optional, set in Railway)
