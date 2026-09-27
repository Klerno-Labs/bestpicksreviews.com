#!/usr/bin/env python3
"""Give changed local CSS/JS new URLs so returning browsers receive the release."""
from hashlib import sha256
from html import escape, unescape
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit
import argparse
import re
from site_inventory import inventory

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = re.compile(r'''(?P<attr>\b(?:src|href))=(?P<quote>["'])(?P<url>(?:https://bestpicksreviews\.com)?/assets/[^"'?#]+\.(?:css|js))(?P<query>\?[^"']*)?(?P=quote)''')


def version_html(html, root):
    def replace(match):
        url = match['url']
        path = root / urlsplit(url).path.lstrip('/')
        if not path.is_file() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError('Missing or invalid local asset: ' + url)
        version = sha256(path.read_bytes()).hexdigest()[:12]
        query = [(k, v) for k, v in parse_qsl(unescape((match['query'] or '')[1:]), keep_blank_values=True) if k != 'v']
        query.append(('v', version))
        return match['attr'] + '=' + match['quote'] + escape(url + '?' + urlencode(query), quote=True) + match['quote']
    return REFERENCE.sub(replace, html)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    stale = []
    for page in inventory(ROOT):
        current = version_html(page.html, ROOT)
        if current != page.html:
            stale.append(page.path)
            if not args.check:
                (ROOT / page.path).write_text(current)
    if args.check and stale:
        raise SystemExit('Asset versions are stale in ' + ', '.join(stale) + '. Run python3 scripts/version_assets.py, then build_discovery.py.')
    print('Asset versions are current.' if args.check else f'Updated asset references in {len(stale)} files.')
