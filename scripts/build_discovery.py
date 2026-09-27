#!/usr/bin/env python3
"""Build human and machine directories from the visible homepage guide library."""
from html import escape, unescape
from pathlib import Path
import argparse
import json
import re
from site_inventory import ORIGIN, inventory
from version_assets import version_html

ROOT = Path(__file__).resolve().parents[1]


def clean(value):
    return ' '.join(unescape(re.sub(r'<[^>]+>', '', value)).split())


def catalogue(root):
    home = (root / 'index.html').read_text()
    entries, categories = [], []
    for category_id, body in re.findall(r'<section class="bp-category" id="([^"]+)"[^>]*>(.*?)</section>', home, re.S):
        category = clean(re.search(r'<h3[^>]*>(.*?)</h3>', body, re.S).group(1))
        categories.append((category_id, category))
        for href, title in re.findall(r'<a href="([^"]+)"><span class="bp-guide-title">(.*?)</span>', body, re.S):
            entries.append({'title': clean(title), 'url': ORIGIN + href, 'category': category, 'categoryId': category_id})
    actual = {p.url for p in inventory(root) if p.indexable and p.path.startswith('best-')}
    listed = [entry['url'] for entry in entries]
    if not actual or len(listed) != len(set(listed)) or set(listed) != actual:
        raise ValueError('Homepage guide library must list every current guide exactly once before generating discovery files')
    return home, entries, categories


def render(root):
    home, entries, categories = catalogue(root)
    header = re.search(r'<header class="bp-header">.*?</header>', home, re.S).group()
    footer = re.search(r'<footer class="bp-footer">.*?</footer>', home, re.S).group()
    directory = re.search(r'<section class="bp-container bp-directory".*?</section></section>', home, re.S).group()
    directory = directory.replace('<h2 id="directory-heading">What are you looking for?</h2>', '<h2 id="directory-heading">Browse every buying guide</h2>')
    directory = re.sub(r'href="/#(audio|home|saunas|dog-gear|skincare|all-guides)"', r'href="#\1"', directory)
    schema = {'@context': 'https://schema.org', '@type': 'CollectionPage', 'name': 'BestPicks buying guide directory', 'url': ORIGIN + '/sitemap-content.html', 'mainEntity': {'@type': 'ItemList', 'numberOfItems': len(entries), 'itemListElement': [{'@type': 'ListItem', 'position': i + 1, 'name': e['title'], 'url': e['url']} for i, e in enumerate(entries)]}}
    category_links = ' '.join(f'<a class="bp-topic" href="#{key}">{escape(name)}</a>' for key, name in categories)
    schema_json = json.dumps(schema, ensure_ascii=False).replace('<', '\\u003c')
    html = f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Browse Product Buying Guides | BestPicks Reviews</title>
<meta name="description" content="Find BestPicks buying guides by product, category or use. Browse audio, home and office, dog gear, sauna and skincare research with evidence limitations.">
<meta name="robots" content="index,follow,max-image-preview:large">
<link rel="canonical" href="{ORIGIN}/sitemap-content.html"><link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="/assets/home.css"><link rel="stylesheet" href="/assets/recovery.css">
<link rel="alternate" type="application/json" href="/guides.json" title="Guide directory as JSON">
<script src="/assets/home.js" defer></script><script src="/assets/analytics.js" defer></script>
<script type="application/ld+json">{schema_json}</script>
</head><body class="bp-home"><a class="bp-skip" href="#main">Skip to content</a>
<div class="bp-disclosure"><div class="bp-container">We may earn a commission when you buy through our links. <a href="/disclosure.html">How affiliate links work ↗</a></div></div>
{header}<main id="main">
<section class="bp-container bp-directory-intro"><p class="bp-eyebrow">The complete guide library</p><h1>Find a clearer answer<br>before you buy.</h1><p>Search by product or choose a category. These are research-based buying guides: each explains its sources, shopping considerations and evidence limitations.</p><nav aria-label="Browse categories">{category_links}</nav><p><a href="/methodology.html">How we research</a> · <a href="/contact.html">Suggest a correction</a></p></section>
{directory}
</main>{footer}</body></html>
'''
    data = {'name': 'BestPicks Reviews guide directory', 'home': ORIGIN + '/', 'directory': ORIGIN + '/sitemap-content.html', 'methodology': ORIGIN + '/methodology.html', 'disclosure': ORIGIN + '/disclosure.html', 'evidenceNote': 'Research-based buying guides. Read each page for its evidence, sources and limitations. Inclusion is not proof of hands-on testing or an endorsement of every product. Merchant prices and availability can change.', 'guides': entries}
    llms = '# BestPicks Reviews\n\n> Research-based product buying guides. Each guide states its evidence and limitations. Inclusion does not establish hands-on testing. Some links earn affiliate commissions.\n\n## Browse and understand the site\n'
    for title, path in [('Guide directory', '/sitemap-content.html'), ('Guide directory as JSON', '/guides.json'), ('XML sitemap', '/sitemap.xml'), ('About', '/about.html'), ('Research methodology', '/methodology.html'), ('Affiliate disclosure', '/disclosure.html'), ('Corrections and contact', '/contact.html')]:
        llms += f'- [{title}]({ORIGIN}{path})\n'
    for key, category in categories:
        llms += f'\n## {category}\n'
        llms += ''.join(f'- [{e["title"]}]({e["url"]})\n' for e in entries if e['categoryId'] == key)
    return {'sitemap-content.html': version_html(html, root), 'guides.json': json.dumps(data, indent=2, ensure_ascii=False) + '\n', 'llms.txt': llms}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    stale = []
    for name, contents in render(ROOT).items():
        path = ROOT / name
        if args.check:
            if not path.exists() or path.read_text() != contents:
                stale.append(name)
        else:
            path.write_text(contents)
    if stale:
        raise SystemExit('Discovery files are stale: ' + ', '.join(stale) + '. Run python3 scripts/build_discovery.py')
    print('Discovery directory, JSON catalogue and llms.txt are current.')
