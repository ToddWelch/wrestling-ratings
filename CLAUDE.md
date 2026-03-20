# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Flask + React single-page application that displays interactive historical TV ratings charts for professional wrestling shows. Nielsen TV ratings (viewers + key demo) for 5 shows, plus a separate streaming/digital views section for Netflix/YouTube-based shows. Uses Recharts for charting.

**Deploy target:** Railway at `wrestlingratings.welchcommercesystems.com`

## Current State

The project is in early development. Currently contains:
- `WRESTLING-RATINGS.md` - Full project specification (architecture, data formats, scraping strategy, SEO plan, deployment config)
- `wrestling-ratings.jsx` - Reference React component with sample data, chart layout, and styling

The full project structure (backend/, frontend/, Dockerfile, etc.) has not been scaffolded yet. See `WRESTLING-RATINGS.md` for the target architecture.

## Development Commands (once scaffolded)

```bash
# Backend
cd backend && pip install -r ../requirements.txt && python app.py

# Frontend (dev with Vite, proxies API to Flask)
cd frontend && npm install && npm run dev

# Frontend build
cd frontend && npm run build

# Deploy (Railway auto-deploys from main)
git push
```

## Architecture

- **Flask backend** serves the API (`/api/ratings`, `/api/health`), SEO routes (`/sitemap.xml`, `/robots.txt`), and the static Vite-built React app
- **Nielsen scraper** (`scraper.py`) parses WrestlingAttitude.com pages for TV ratings data. Viewer numbers use European-style comma as decimal separator ("1,175" = 1.175M) - must parse by replacing comma with period
- **YouTube scraper** (`youtube_scraper.py`) uses YouTube Data API v3 for ROH/NWA view counts. Optional - works without `YOUTUBE_API_KEY`
- **APScheduler** runs Nielsen scrape every 6 hours, YouTube scrape every 12 hours
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
