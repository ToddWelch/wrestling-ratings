# "How This Website Works" Section - Design Layout

Reusable layout pattern for a technical showcase section on Welch Commerce Systems projects. Styling (colors, fonts, sizes) should inherit from the host site's design system.

## Structure

### Section Container

- Full-width section with top border divider
- Consistent padding with the rest of the page
- Same background as other content sections

### Heading

- Section title: "How This Website Works"

### Feature Cards Grid

- Responsive CSS Grid: `repeat(auto-fill, minmax(280px, 1fr))`
- Gap between cards for breathing room
- Each card is a panel/card component matching the site's card style

**Card structure:**
1. **Title** - Short all-caps label in monospace (accent color)
2. **Body** - Detailed paragraph describing the feature (3-5 sentences)

**Standard cards (adapt content per project):**

| Card | What to cover |
|------|--------------|
| ARCHITECTURE | Stack overview: backend, frontend, bundler, data store format. Mention that it runs as a single process if applicable. |
| LIVE DATA PIPELINE | How data is collected, how many sources, redundancy strategy, scrape frequency, frontend polling interval. List sources as Primary/Backup/Fallback. Always mention the safety net (never overwrite with fewer entries). |
| DATA RECONCILIATION | How multiple sources are compared. Tolerance thresholds, consensus logic (2-of-3 agreement), gap filling strategy. |
| CHART RENDERING (or equivalent) | Chart/visualization library, axis behavior (time-scaled, categorical), data grouping logic, label formatting per zoom level. |
| INTERACTION | All user controls: toggles, filters, zoom, pan, hover tooltips. Describe what each control does. |
| DEPLOYMENT | Containerization (multi-stage Docker build), hosting platform, CI/CD (auto-deploy from main), health checks, SEO strategy (SSR shell, meta tags, JSON-LD, sitemap). |

### Tech Stack Badges

- Horizontal flex row, wrapping allowed
- One badge per technology, using the site's badge/tag style
- Include version numbers for key technologies (e.g., "Python 3.11", "React 18")
- Example: Python 3.11, Flask, Gunicorn, APScheduler, BeautifulSoup, React 18, Vite, Recharts, Docker, Railway

### Open Source Line

- Below the badges, a single text line
- "Open Source" label in bold/secondary color
- "The full source code is available at [github.com/user/repo]."
- Link styled as the site's standard link (underline, secondary color)

## Responsive Behavior

- Cards reflow from 2-3 columns on desktop to single column on mobile
- Tech badges wrap naturally
- Open source line is full-width text

## Usage

This section sits between the main content area and the site footer. It serves as a portfolio/showcase element demonstrating the technical depth of the project. Adapt the card content to match the specific project's architecture. Keep the same card categories across all Welch Commerce projects for consistency.
