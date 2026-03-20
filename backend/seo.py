import json
from pathlib import Path
from flask import Response


def register_seo_routes(app, ratings_file):

    @app.route("/sitemap.xml")
    def sitemap():
        lastmod = "2026-03-20"
        if Path(ratings_file).exists():
            with open(ratings_file) as f:
                data = json.load(f)
            updated = data.get("lastUpdated")
            if updated:
                lastmod = updated[:10]

        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://wrestlingratings.welchcommercesystems.com/</loc>
    <lastmod>{lastmod}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
  </url>
</urlset>"""
        return Response(xml, mimetype="application/xml")

    @app.route("/robots.txt")
    def robots():
        txt = """User-agent: *
Allow: /
Sitemap: https://wrestlingratings.welchcommercesystems.com/sitemap.xml"""
        return Response(txt, mimetype="text/plain")
