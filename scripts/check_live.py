#!/usr/bin/env python3
"""Read-only delivery monitoring. Never visits merchant or affiliate destinations."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser
import argparse
import json
import re
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET
from site_inventory import ORIGIN, PageParser, inventory, sitemap_urls, schema_objects

ROOT = Path(__file__).resolve().parents[1]
SEARCH_AGENTS = ('Googlebot', 'bingbot', 'OAI-SearchBot', 'ChatGPT-User', 'PerplexityBot', 'Perplexity-User', 'Claude-SearchBot')


def fetch(url, agent='BestPicksHealthCheck/1.0 (+https://bestpicksreviews.com/contact.html)'):
    if urlsplit(url).netloc != 'bestpicksreviews.com':
        raise ValueError('Health checks are restricted to this website')
    with tempfile.TemporaryDirectory() as folder:
        headers, body = Path(folder) / 'headers', Path(folder) / 'body'
        result = subprocess.run(['curl', '--silent', '--show-error', '--max-time', '20', '--user-agent', agent, '--dump-header', str(headers), '--output', str(body), '--write-out', '%{http_code}', url], capture_output=True, text=True)
        if result.returncode:
            raise ValueError(result.stderr.strip())
        parsed = {}
        for line in headers.read_text().splitlines():
            if line.startswith('HTTP/'):
                parsed = {}
            elif ':' in line:
                key, value = line.split(':', 1)
                parsed[key.lower()] = parsed.get(key.lower(), '') + ' ' + value.strip()
        return int(result.stdout), {k: v.strip() for k, v in parsed.items()}, body.read_text(errors='replace')


def html_issues(url, status, headers, body):
    issues = []
    parsed = PageParser()
    parsed.feed(body)
    if status != 200:
        issues.append(f'HTTP {status}, expected 200')
    if not parsed.full_document or not re.search(r'<h1\b', body, re.I):
        issues.append('Missing readable HTML document or headline')
    if parsed.canonicals != [url]:
        issues.append('Canonical URL differs from requested page')
    if parsed.refreshes:
        issues.append('Unexpected HTML redirect')
    directives = parsed.robots + [headers.get('x-robots-tag', '').lower()]
    if any(re.search(r'\b(noindex|none|nosnippet)\b|max-snippet\s*:\s*0\b', value) for value in directives):
        issues.append('Indexing or snippets restricted')
    for script in parsed.scripts:
        if script['attrs'].get('type') == 'application/ld+json':
            try:
                for item in schema_objects(json.loads(script['text'])):
                    if 'aggregateRating' in item or item.get('@type') == 'Product':
                        issues.append('Unsupported product or ratings markup')
            except ValueError:
                issues.append('Invalid structured data')
    return issues


def check(url, target=None, agent=None):
    result = {'url': url, 'kind': 'redirect' if target else 'canonical'}
    if agent:
        result['probeUserAgent'] = agent
    for attempt in range(2):
        try:
            status, headers, body = fetch(url, agent) if agent else fetch(url)
            result['status'] = status
            issues = [] if not target else (['Missing exact permanent redirect'] if status != 301 or urljoin(url, headers.get('location', '')) != target else [])
            if not target:
                issues = html_issues(url, status, headers, body)
            result['issues'] = issues
        except (OSError, ValueError) as error:
            result['issues'] = [str(error)]
        if not result['issues']:
            break
        if attempt == 0:
            time.sleep(1)
    return result


def run():
    expected = set(sitemap_urls(inventory(ROOT)))
    aliases = json.loads((ROOT / 'redirects.json').read_text())
    jobs = [(url, None, None) for url in sorted(expected)]
    jobs += [(ORIGIN + path, ORIGIN + target, None) for path, target in aliases.items()]
    # Diagnostic user-agent probes are not proof of access from a provider's IPs.
    jobs += [(ORIGIN + path, None, agent) for path in ('/', '/sitemap-content.html', '/best-open-ear-headphones-for-running/') for agent in SEARCH_AGENTS]
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda job: check(*job), jobs))
    for path in ('/robots.txt', '/sitemap.xml', '/guides.json', '/llms.txt'):
        result = {'url': ORIGIN + path, 'kind': 'discovery', 'issues': []}
        for attempt in range(2):
            result['issues'] = []
            try:
                status, _, body = fetch(ORIGIN + path)
                result['status'] = status
                if status != 200:
                    raise ValueError(f'HTTP {status}, expected 200')
                if path == '/robots.txt':
                    robot = RobotFileParser()
                    robot.parse(body.splitlines())
                    for agent in SEARCH_AGENTS:
                        if not all(robot.can_fetch(agent, url) for url in expected):
                            result['issues'].append(f'{agent} blocked by robots.txt')
                elif path == '/sitemap.xml':
                    urls = [element.text for element in ET.fromstring(body).iter() if element.tag.endswith('}loc')]
                    if len(urls) != len(set(urls)) or set(urls) != expected:
                        result['issues'].append('Live sitemap differs from canonical inventory')
                elif path == '/guides.json':
                    guides = json.loads(body)['guides']
                    if {e['url'] for e in guides} != {u for u in expected if '/best-' in u}:
                        result['issues'].append('Guide catalogue differs from canonical inventory')
                elif body != (ROOT / 'llms.txt').read_text():
                    result['issues'].append('Published guide map differs from repository')
            except (OSError, ValueError, KeyError, TypeError, ET.ParseError) as error:
                result['issues'] = [str(error)]
            if not result['issues']:
                break
            if attempt == 0:
                time.sleep(1)
        results.append(result)
    return {'checkedAt': datetime.now(timezone.utc).isoformat(), 'limitations': 'Synthetic HTTP checks, not confirmation of real bot visits, indexing, AI citations, affiliate attribution or earnings.', 'passed': sum(not r['issues'] for r in results), 'total': len(results), 'results': results}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report = run()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(f"Live checks: {report['passed']}/{report['total']} passed")
    for result in report['results']:
        if result['issues']:
            print(result['url'] + ': ' + '; '.join(result['issues']))
    raise SystemExit(report['passed'] != report['total'])
