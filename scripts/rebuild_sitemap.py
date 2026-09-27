#!/usr/bin/env python3
"""Rebuild sitemap.xml from actual indexable canonical HTML, without network access."""
from pathlib import Path
from site_inventory import inventory, render_sitemap, sitemap_urls

root = Path(__file__).resolve().parents[1]
pages = inventory(root)
content = render_sitemap(pages)
destination = root / "sitemap.xml"
destination.write_text(content, encoding="utf-8")
print(f"Rebuilt sitemap.xml: {len(sitemap_urls(pages))} canonical URLs; no fabricated lastmod dates.")
