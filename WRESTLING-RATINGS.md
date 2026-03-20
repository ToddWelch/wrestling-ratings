# Pro Wrestling TV Ratings Tracker

## Project Overview

A standalone Flask + React single-page application that displays interactive historical TV ratings charts for all major professional wrestling shows. Features Nielsen TV ratings with total viewers and key demo toggles, a separate streaming views section for Netflix/YouTube-based shows, time range zooming, show toggles, and strong SEO for Google discoverability.

**Deploy target:** New Railway project at `wrestlingratings.welchproductsllc.com`

## Architecture

```
wrestling-ratings/
  backend/
    app.py              # Flask app, serves API + SSR HTML shell + static React build
    scraper.py          # Scrapes WrestlingAttitude.com for Nielsen data
    youtube_scraper.py  # YouTube Data API for ROH/NWA episode view counts
    scheduler.py        # APScheduler cron jobs
    seo.py              # Generates sitemap.xml, robots.txt, structured data
    data/
      ratings.json      # Current ratings data store
  frontend/
    src/
      App.jsx           # Main chart component (based on artifact)
      index.jsx         # Entry point
      index.css         # Global styles
    public/
      index.html        # SEO-optimized HTML shell (meta tags, OG, JSON-LD)
    package.json
    vite.config.js
  Dockerfile
  requirements.txt
  railway.toml
  .gitignore
  README.md
```

## Shows Tracked

### Tier 1: Nielsen TV Ratings (primary chart)

All use the same Y-axis. Toggle between Total Viewers (millions) and Key Demo (P18-49 rating).

| Show | ID | Color | Network | Day | Data Source |
|------|----|-------|---------|-----|-------------|
| WWE SmackDown | smackdown | #3B82F6 (blue) | USA/SyFy | Friday | WrestlingAttitude |
| WWE NXT | nxt | #F59E0B (yellow) | CW | Tuesday | WrestlingAttitude |
| AEW Dynamite | dynamite | #EF4444 (red) | TBS | Wednesday | WrestlingAttitude |
| AEW Collision | collision | #EC4899 (pink) | TNT | Saturday | WrestlingAttitude |
| TNA iMPACT | tna | #10B981 (green) | AMC | Thursday | WrestlingAttitude |

### Tier 2: Streaming/Digital Views (separate chart section)

Different metrics. Clearly labeled as not comparable to Nielsen.

| Show | ID | Color | Platform | Metric | Data Source |
|------|----|-------|----------|--------|-------------|
| WWE Raw | raw | #8B5CF6 (purple) | Netflix | Global Views (M) | WrestlingAttitude (Netflix data) |
| ROH Wrestling | roh | #F97316 (orange) | HonorClub/YouTube | YouTube Views (K) | YouTube Data API |
| NWA Powerrr | nwa | #06B6D4 (cyan) | Roku Channel/YouTube | YouTube Views (K) | YouTube Data API |

### Data Notes

- **Nielsen methodology change:** On Sep 26, 2025, Nielsen switched to "Big Data + Panel" measurement. Wrestling was disproportionately affected. A January 2026 adjustment partially reversed declines. Mark this date with a reference line on the chart.
- **WWE Raw:** Moved to Netflix Jan 2025. Uses Netflix's global views metric (total hours viewed / runtime). Not Nielsen.
- **ROH:** Primary platform is HonorClub (paid, Thursdays). YouTube episodes post Fridays. Track YouTube view counts.
- **NWA Powerrr:** Moved to Roku Channel Jul 2025. No public Roku viewership. Track YouTube clips/episodes when posted.
- **TNA iMPACT:** Only has Nielsen data from Jan 2026 onward (AMC debut).

## Frontend Design

### Chart Library

Use **Recharts** (already available in the artifact environment, install via npm for the Vite project).

### Layout (top to bottom)

**1. Header**
- Title: "Pro Wrestling TV Ratings Tracker" (h1)
- Subtitle: "WEEKLY VIEWERSHIP FOR WWE, AEW, TNA, ROH, AND NWA . UPDATED EVERY WEEK . NIELSEN + STREAMING"
- Metric toggle: VIEWERS / KEY DEMO 18-49
- Time range buttons: 3M, 6M, 1Y, ALL (default: 1Y)
- Show toggle buttons with colored dots (Nielsen shows)

**2. Nielsen TV Ratings Chart**
- Section heading: "Nielsen TV Ratings" (h2)
- Subheading shows current metric: "TOTAL VIEWERS (MILLIONS)" or "18-49 KEY DEMO RATING"
- Recharts LineChart, responsive, ~340px height
- One line per active show, colored per config
- X-axis: dates, formatted "Mon 'YY"
- Y-axis: 0-2.0M for viewers, 0-0.60 for demo
- Reference line at Sep 26, 2025 labeled "Nielsen Change"
- Tooltip: dark card showing date + all active show values
- Lines use connectNulls={false} so gaps appear naturally when data is missing

**3. Streaming & Digital Views Chart**
- Section heading: "Streaming & Digital Views" (h2)
- Disclaimer: "DIFFERENT METRICS: NOT COMPARABLE TO NIELSEN"
- Streaming show toggle buttons (Raw, ROH, NWA)
- Recharts LineChart, ~220px height
- Y-axis: 0-5.0M for Raw (Netflix), separate scale consideration for YouTube views
- Data source notes box explaining each show's platform and measurement

**4. SEO Content Section**
- "About Pro Wrestling TV Ratings" (h2) with ~5 paragraphs of keyword-rich descriptive text
- Show schedule grid: 8 cards showing show name, day, network, time
- This content is critical for Google indexing

**5. Footer**
- Data source attribution
- Site URL

### Color Palette

Same dark green theme as the US Open Cup bracket:
- Page background: #070f0b
- Header gradient: #0e2118 to #070f0b
- Card/panel background: #0c1812
- Border: #1a3a2a, #162a20
- Primary accent: #4ade80
- Muted text: #3e6e4e, #2e5e3e, #1e3e2e
- Typography: system-ui sans-serif body, monospace for data/labels

### Interactivity

- Metric toggle switches Y-axis and data keys between total viewers and key demo
- Time range filters data to last 3M/6M/1Y/ALL
- Show toggles add/remove lines from chart
- Hover tooltip with exact values
- All state is client-side (no URL routing needed)

### Auto-refresh

- Poll `/api/ratings` every 10 minutes
- Compare `lastUpdated` timestamp; update charts if newer data available

## Backend Details

### Flask App (`app.py`)

- `GET /` serves the React app with SEO-optimized HTML shell
- `GET /api/ratings` returns the full ratings JSON
- `GET /api/health` health check
- `GET /sitemap.xml` dynamically generated sitemap
- `GET /robots.txt` allows all crawlers
- On startup, run initial scrape if ratings.json is empty or stale

### Nielsen Scraper (`scraper.py`)

**Target URLs:**
- `https://www.wrestlingattitude.com/p/2026-wwe-aew-viewership-and-key-demo-ratings.html`
- `https://www.wrestlingattitude.com/p/2025-wwe-aew-viewership-and-key-demo-ratings.html`

**Parsing strategy:**

The pages have plain text in a consistent format per show section:

```
**WWE SmackDown (Million Viewers):**
Jan 2: 1,175 – 0.28 key demo rating
Jan 9: 0,990 – 0.26 key demo rating
```

Steps:
1. Use `requests` + `BeautifulSoup` to fetch page
2. Find each show section by its bold header text
3. Parse each line with regex: `(\w+ \d+): (\d+[,.]?\d*) . (\d+\.\d+) key demo rating`
4. The viewer number uses European-style comma as decimal separator on this site (e.g., "1,175" = 1.175 million). Parse accordingly: replace comma with period, convert to float.
5. Handle edge cases: "(on SyFy)" notes, "NO DATA" entries, links in text
6. Build structured data per show per date

**Important parsing notes:**
- SmackDown entries sometimes have "(on SyFy)" appended. Strip this.
- Some weeks show "NO DATA". Skip these.
- TNA iMPACT data only starts Jan 2026.
- The date format is "Mon DD" within the context of the year page being scraped. Combine with the year from the URL.

### YouTube Scraper (`youtube_scraper.py`)

Use the YouTube Data API v3 (free tier, 10,000 quota units/day).

**ROH Channel:** Search for recent uploads matching "ROH" or "Ring of Honor" episode pattern. Pull `viewCount` and `publishedAt`.

**NWA Channel:** Search for uploads matching "NWA Powerrr" or "POWERRR". Note: since Jul 2025 move to Roku, full episodes may not be on YouTube. Track whatever is posted.

**API flow:**
1. Use `playlistItems.list` on the channel's "uploads" playlist to get recent videos
2. Filter by title pattern for actual episode content (not clips/promos)
3. Use `videos.list` to get `viewCount` for each
4. Store date + view count per episode

**YouTube API key:** Store as `YOUTUBE_API_KEY` environment variable in Railway.

If no YouTube API key is configured, skip YouTube scraping gracefully and show "Data unavailable" for ROH/NWA.

### Scheduler (`scheduler.py`)

APScheduler (BackgroundScheduler) integrated into Flask:
- **Nielsen scrape:** Every 6 hours (data updates weekly, no need to hammer the source)
- **YouTube scrape:** Every 12 hours
- Log each run with timestamp and change status

### Data Store (`ratings.json`)

```json
{
  "lastUpdated": "2026-03-20T14:30:00Z",
  "scrapeStatus": {
    "nielsen": "ok",
    "youtube": "ok"
  },
  "nielsen": {
    "smackdown": [
      { "date": "2025-03-21", "viewers": 1.459, "demo": 0.39 }
    ],
    "nxt": [],
    "dynamite": [],
    "collision": [],
    "tna": []
  },
  "streaming": {
    "raw": [
      { "date": "2025-03-17", "viewers": 3.1 }
    ],
    "roh": [
      { "date": "2025-04-04", "views": 85000 }
    ],
    "nwa": []
  }
}
```

The frontend transforms this into the flat array format Recharts expects (one object per date with all show values).

### Error Handling

- Scrape failures: log warning, keep existing data
- Never overwrite with empty/corrupted data
- Compare new data length vs existing before writing
- `scrapeStatus` per source: "ok", "stale", "error", "no_api_key"

## SEO Strategy (CRITICAL)

This site needs to rank for queries like "wrestling TV ratings", "SmackDown ratings this week", "AEW Dynamite viewership 2026", etc.

### HTML Shell (`index.html`)

The Vite-built React app loads inside a server-rendered HTML shell that contains:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Pro Wrestling TV Ratings Tracker 2026 | WWE, AEW, TNA, ROH, NWA Weekly Viewership</title>
  <meta name="description" content="Track weekly TV ratings for WWE SmackDown, NXT, AEW Dynamite, Collision, TNA iMPACT, WWE Raw on Netflix, ROH, and NWA Powerrr. Interactive charts with total viewers and 18-49 key demo ratings updated every week.">
  <meta name="keywords" content="wrestling TV ratings, WWE ratings, AEW ratings, SmackDown viewership, Dynamite ratings, NXT ratings, TNA iMPACT ratings, wrestling viewership 2026, key demo wrestling, pro wrestling ratings tracker">
  <link rel="canonical" href="https://wrestlingratings.welchproductsllc.com/">

  <!-- Open Graph -->
  <meta property="og:title" content="Pro Wrestling TV Ratings Tracker 2026">
  <meta property="og:description" content="Interactive weekly TV ratings charts for WWE, AEW, TNA, ROH, and NWA. Total viewers and key demo data updated every week.">
  <meta property="og:type" content="website">
  <meta property="og:url" content="https://wrestlingratings.welchproductsllc.com/">
  <meta property="og:image" content="https://wrestlingratings.welchproductsllc.com/og-image.png">

  <!-- Twitter Card -->
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="Pro Wrestling TV Ratings Tracker 2026">
  <meta name="twitter:description" content="Weekly TV ratings for WWE, AEW, TNA, ROH, NWA with interactive charts.">

  <!-- JSON-LD Structured Data -->
  <script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@type": "WebApplication",
    "name": "Pro Wrestling TV Ratings Tracker",
    "description": "Interactive weekly television ratings tracker for professional wrestling shows including WWE SmackDown, NXT, AEW Dynamite, Collision, TNA iMPACT, WWE Raw, ROH, and NWA Powerrr.",
    "url": "https://wrestlingratings.welchproductsllc.com/",
    "applicationCategory": "Sports",
    "operatingSystem": "Web",
    "offers": {
      "@type": "Offer",
      "price": "0"
    }
  }
  </script>

  <!-- Favicon -->
  <link rel="icon" type="image/svg+xml" href="/favicon.svg">
</head>
<body>
  <div id="root"></div>
  <script type="module" src="/src/index.jsx"></script>
</body>
</html>
```

### Server-Side Considerations

Flask should serve the HTML shell with the meta tags already present (not client-rendered). This ensures Google's crawler sees the SEO content immediately.

Two approaches (pick the simpler one for v1):
1. **Simple:** Flask serves the static Vite build. The SEO text content in the React app is visible in the DOM on first render (no lazy loading of the text sections). Google's JS renderer will pick it up.
2. **Better (v2):** Flask injects a `<noscript>` section with the key SEO text content directly in the HTML, so even without JS execution, Google sees the descriptive text.

For v1, approach #1 is fine since the SEO text section in the React component renders immediately (no data fetch needed for it).

### sitemap.xml

Flask endpoint that returns:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://wrestlingratings.welchproductsllc.com/</loc>
    <lastmod>2026-03-20</lastmod>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
  </url>
</urlset>
```

The `<lastmod>` should be dynamically set from `ratings.json`'s `lastUpdated` field.

### robots.txt

```
User-agent: *
Allow: /
Sitemap: https://wrestlingratings.welchproductsllc.com/sitemap.xml
```

### Additional SEO

- Generate a simple OG image (static PNG with the site title and a mini chart graphic, can be made with Python PIL or just a designed static image)
- Ensure fast page load (the Vite build is already optimized, but keep the bundle small)
- Use semantic HTML in React: `<h1>`, `<h2>`, `<article>`, `<section>`, `<footer>` tags
- The "About" section and show schedule grid provide crawlable keyword-rich text
- Add `<meta name="robots" content="index, follow">`
- After deploy, submit sitemap to Google Search Console

## Deployment

### Dockerfile

```dockerfile
FROM node:20-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./backend/
COPY --from=frontend-build /app/frontend/dist ./frontend/dist
EXPOSE 8080
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--chdir", "backend", "app:app"]
```

### requirements.txt

```
flask==3.1.0
requests==2.32.3
beautifulsoup4==4.13.3
apscheduler==3.11.0
gunicorn==23.0.0
google-api-python-client==2.166.0
```

### railway.toml

```toml
[build]
dockerfilePath = "Dockerfile"

[deploy]
healthcheckPath = "/api/health"
healthcheckTimeout = 10
```

### Environment Variables (Railway)

- `YOUTUBE_API_KEY` - YouTube Data API v3 key (optional; YouTube scraping skipped if not set)

### Custom Domain

1. Railway project settings: add `wrestlingratings.welchproductsllc.com`
2. DNS: CNAME to Railway-provided domain
3. SSL handled automatically

## Initial Data

Seed ratings.json with data from the WrestlingAttitude scrape. The scraper will keep it updated.

The artifact (.jsx file) contains sample data that demonstrates the format. The scraper should produce this same structure from the live pages.

Key data ranges available:
- SmackDown: Full 2025 + 2026 Q1
- NXT: 2025 through Sep, then 2026 Q1
- Dynamite: 2026 Q1 only (AEW data on WrestlingAttitude starts Jan 2026)
- Collision: 2026 Q1 only
- TNA iMPACT: Jan 2026 onward (AMC debut)
- Raw (Netflix): Full 2025 + 2026 Q1
- ROH/NWA YouTube: to be populated by YouTube scraper

Note: WrestlingAttitude's 2025 page has AEW Dynamite and Collision data for all of 2025 as well. The scraper should parse those sections from the 2025 page. The sample data in the artifact only has partial data because I was working from a truncated scrape.

## Development Workflow

1. Clone repo, `cd wrestling-ratings`
2. Backend: `cd backend && pip install -r ../requirements.txt && python app.py`
3. Frontend: `cd frontend && npm install && npm run dev` (proxy API to Flask in vite.config.js)
4. Build: `cd frontend && npm run build`
5. Deploy: `git push` (Railway auto-deploys from main)

## Key Reminders

- No em dashes anywhere in the codebase or UI text
- Test the WrestlingAttitude scraper against both live 2025 and 2026 pages before deploying
- The European-style comma in viewer numbers (e.g., "1,175" = 1.175M) must be parsed correctly
- Never overwrite ratings.json with less data than it currently has
- Flask serves both the API, SEO routes (sitemap, robots), and the static React build
- The artifact (.jsx file) is the working reference implementation for the frontend
- YouTube API key is optional; the site works without it (ROH/NWA sections show "no data")
- SEO text content in the React component must render on initial load (no lazy loading)
- Submit sitemap to Google Search Console after first deploy
