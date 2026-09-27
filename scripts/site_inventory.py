"""Offline inventory shared by sitemap generation and release validation."""
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit
import json
import re
import xml.etree.ElementTree as ET

ORIGIN = "https://bestpicksreviews.com"
SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
SKIP_DIRS = {".git", ".github", "node_modules", "scripts", "audit"}


def page_url(path: str) -> str:
    if path == "index.html":
        return ORIGIN + "/"
    if path.endswith("/index.html"):
        return ORIGIN + "/" + path[:-10]
    return ORIGIN + "/" + path


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.full_document = False
        self.canonicals = []
        self.robots = []
        self.refreshes = []
        self.links = []
        self.references = []
        self.scripts = []
        self.stylesheets = []
        self.ids = set()
        self._script = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "html":
            self.full_document = True
        if attrs.get("id"):
            self.ids.add(attrs["id"])
        if tag == "a" and attrs.get("name"):
            self.ids.add(attrs["name"])
        if tag == "meta" and attrs.get("name", "").lower() in {"robots", "googlebot"}:
            self.robots.append(attrs.get("content", "").lower())
        if tag == "meta" and attrs.get("http-equiv", "").lower() == "refresh":
            self.refreshes.append(attrs.get("content", ""))
        if tag == "link" and "canonical" in attrs.get("rel", "").lower().split():
            self.canonicals.append(attrs.get("href", ""))
        if tag == "link" and "stylesheet" in attrs.get("rel", "").lower().split():
            self.stylesheets.append(attrs.get("href", ""))
        if tag == "a" and "href" in attrs:
            self.links.append(attrs["href"] or "")
        for attribute in ("href", "src"):
            if attrs.get(attribute):
                self.references.append((tag, attribute, attrs[attribute]))
        if tag == "script":
            self._script = {"attrs": attrs, "text": ""}
            self.scripts.append(self._script)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_data(self, data):
        if self._script is not None:
            self._script["text"] += data

    def handle_endtag(self, tag):
        if tag == "script":
            self._script = None


@dataclass
class Page:
    path: str
    html: str
    parsed: PageParser

    @property
    def url(self):
        return page_url(self.path)

    @property
    def noindex(self):
        return any(
            "noindex" in value or "none" in value.replace(",", " ").split()
            for value in self.parsed.robots
        )

    @property
    def indexable(self):
        return self.parsed.full_document and self.path != "404.html" and not self.noindex and not self.parsed.refreshes


def inventory(root: Path) -> list[Page]:
    pages = []
    for file in sorted(root.rglob("*.html")):
        relative = file.relative_to(root)
        if any(part in SKIP_DIRS for part in relative.parts):
            continue
        html = file.read_text(encoding="utf-8")
        parsed = PageParser()
        parsed.feed(html)
        parsed.close()
        pages.append(Page(relative.as_posix(), html, parsed))
    return pages


def sitemap_urls(pages: list[Page]) -> list[str]:
    """Fail rather than silently excluding an indexable page with bad metadata."""
    urls = []
    for page in pages:
        if not page.indexable:
            continue
        if page.parsed.canonicals != [page.url]:
            raise ValueError(f"{page.path}: expected exactly one self-canonical {page.url}")
        urls.append(page.url)
    return sorted(urls)


def render_sitemap(pages: list[Page]) -> str:
    ET.register_namespace("", SITEMAP_NS)
    root = ET.Element(f"{{{SITEMAP_NS}}}urlset")
    for url in sitemap_urls(pages):
        entry = ET.SubElement(root, f"{{{SITEMAP_NS}}}url")
        ET.SubElement(entry, f"{{{SITEMAP_NS}}}loc").text = url
    ET.indent(root, space="  ")
    # No lastmod: generation time is not evidence of an editorial change.
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode") + "\n"


def local_reference(value: str, base: str):
    """Return an internal URL, without fetching it; all other schemes are ignored."""
    try:
        resolved = urlsplit(urljoin(base, value))
    except ValueError:
        return None
    if resolved.scheme not in {"http", "https"}:
        return None
    if resolved.hostname not in {"bestpicksreviews.com", "www.bestpicksreviews.com"}:
        return None
    return resolved


def target_file(url) -> str:
    path = unquote(url.path).lstrip("/")
    if not path or path.endswith("/"):
        path += "index.html"
    return path


def schema_objects(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from schema_objects(child)
    elif isinstance(value, list):
        for child in value:
            yield from schema_objects(child)


@dataclass
class Validation:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    page_count: int = 0
    indexable_count: int = 0
    review_count: int = 0
    redirect_count: int = 0


def validate_site(root: Path) -> Validation:
    result = Validation()
    pages = inventory(root)
    by_path = {p.path: p for p in pages}
    result.page_count = sum(p.parsed.full_document for p in pages)
    result.indexable_count = sum(p.indexable for p in pages)
    result.review_count = sum(p.path.startswith("best-") and p.path.endswith("/index.html") for p in pages)
    manifest_file = root / "scripts/review-baseline.json"
    try:
        manifest = json.loads(manifest_file.read_text())
        required = manifest["requiredReviewPaths"]
        if not isinstance(required, list) or not all(isinstance(path, str) for path in required) or len(required) < 36 or len(set(required)) != len(required):
            raise ValueError("baseline must retain at least 36 unique reviewed paths")
    except (OSError, ValueError, KeyError, TypeError) as error:
        result.errors.append(f"review baseline invalid: {error}")
        required = []

    try:
        redirects = json.loads((root / "redirects.json").read_text()) if (root / "redirects.json").exists() else {}
        if not isinstance(redirects, dict):
            raise ValueError("redirects.json must map source paths to target paths")
        result.redirect_count = len(redirects)
        for source, destination in redirects.items():
            if not isinstance(source, str) or not isinstance(destination, str):
                raise ValueError("redirect source and destination must be strings")
            source_url = local_reference(source, ORIGIN)
            target_url = local_reference(destination, ORIGIN)
            if not source_url or not target_url or not source.startswith("/") or not destination.startswith("/"):
                result.errors.append(f"invalid redirect mapping: {source} -> {destination}")
                continue
            stub = by_path.get(target_file(source_url))
            target = by_path.get(target_file(target_url))
            if not stub or len(stub.parsed.refreshes) != 1:
                result.errors.append(f"redirect stub missing or invalid: {source}")
                continue
            if stub.noindex:
                result.errors.append(f"redirect stub must not contradict its redirect with noindex: {source}")
            match = re.fullmatch(r"0\s*;\s*url\s*=\s*(.+?)\s*", stub.parsed.refreshes[0], re.I)
            refresh_target = match.group(1).strip("\"'") if match else None
            if not refresh_target or urljoin(stub.url, refresh_target) != urljoin(ORIGIN, destination):
                result.errors.append(f"redirect must instantly resolve to its mapped target: {source}")
            if destination in redirects or not target or not target.indexable or target.parsed.canonicals != [target.url]:
                result.errors.append(f"redirect destination absent, noncanonical, noindex or chained: {source} -> {destination}")
            if stub.parsed.canonicals != [urljoin(ORIGIN, destination)]:
                result.errors.append(f"redirect canonical differs from its target: {source}")
    except (OSError, ValueError, TypeError) as error:
        result.errors.append(f"redirect manifest invalid: {error}")
        redirects = {}

    home = by_path.get("index.html")
    home_links = set()
    if home:
        for href in home.parsed.links:
            url = local_reference(href, home.url)
            if url:
                home_links.add(target_file(url))
    else:
        result.errors.append("index.html is missing")

    for path in required:
        url = local_reference(path, ORIGIN)
        if not url or url.query or url.fragment or not path.startswith("/best-") or not path.endswith("/"):
            result.errors.append(f"invalid baseline review path: {path}")
            continue
        file = target_file(url)
        page = by_path.get(file)
        if page is None:
            result.errors.append(f"required review removed: {path}")
        elif not page.indexable:
            result.errors.append(f"required review is no longer indexable: {path}")
        if file not in home_links:
            result.errors.append(f"homepage does not link to required review: {path}")

    for page in pages:
        if not page.parsed.full_document:
            continue  # Keep verification files; do not turn them into content pages.
        is_redirect = bool(page.parsed.refreshes)
        if is_redirect and urlsplit(page.url).path not in redirects:
            result.errors.append(f"{page.path}: redirect is not recorded in redirects.json")
        if not is_redirect and page.path != "404.html" and page.parsed.canonicals != [page.url]:
            result.errors.append(f"{page.path}: requires one self-canonical {page.url}")
        if page.path == "404.html" and not page.noindex:
            result.errors.append("404.html must not be indexable")

        shared = [s for s in page.parsed.scripts if local_reference(s["attrs"].get("src", ""), page.url)
                  and target_file(local_reference(s["attrs"].get("src", ""), page.url)) == "assets/analytics.js"]
        if not is_redirect and len(shared) != 1:
            result.errors.append(f"{page.path}: expected one shared analytics script; found {len(shared)}")
        if is_redirect and shared:
            result.errors.append(f"{page.path}: redirect stubs must not collect analytics")
        consent_styles = [href for href in page.parsed.stylesheets
                          if local_reference(href, page.url)
                          and target_file(local_reference(href, page.url)) == "assets/recovery.css"]
        if shared and not consent_styles:
            result.errors.append(f"{page.path}: shared analytics requires the consent stylesheet /assets/recovery.css")
        for script in page.parsed.scripts:
            attrs = script["attrs"]
            if "googletagmanager.com" in attrs.get("src", "") or "google-analytics.com" in attrs.get("src", ""):
                result.errors.append(f"{page.path}: direct analytics loader bypasses consent")
            if attrs.get("type", "").lower() == "application/ld+json":
                try:
                    schema = json.loads(script["text"])
                    for item in schema_objects(schema):
                        types = item.get("@type", [])
                        types = types if isinstance(types, list) else [types]
                        if any(value in ("Product", "https://schema.org/Product", "http://schema.org/Product") for value in types):
                            result.errors.append(f"{page.path}: unsupported Product markup requires an explicit evidence review; use Article markup for research guides")
                        if "aggregateRating" in item or "AggregateRating" in str(item.get("@type", "")):
                            result.errors.append(f"{page.path}: unsupported aggregateRating must be removed or explicitly reviewed")
                except (ValueError, TypeError) as error:
                    result.errors.append(f"{page.path}: invalid JSON-LD: {error}")
            elif any(marker in script["text"] for marker in ("googletagmanager.com", "google-analytics.com")) or re.search(r"\bgtag\s*\(", script["text"]):
                result.errors.append(f"{page.path}: inline analytics bypasses the shared consent script")

        for tag, attribute, value in page.parsed.references:
            url = local_reference(value, page.url)
            if url is None:
                continue
            file = target_file(url)
            target = (root / file).resolve()
            if not target.is_relative_to(root.resolve()) or not target.is_file():
                result.errors.append(f"{page.path}: broken internal {tag}[{attribute}] {value}")
                continue
            if url.fragment and file in by_path and unquote(url.fragment) not in by_path[file].parsed.ids:
                result.warnings.append(f"{page.path}: fragment not found in source: {value}")

    try:
        expected = set(sitemap_urls(pages))
        xml = ET.fromstring((root / "sitemap.xml").read_text())
        if xml.tag != f"{{{SITEMAP_NS}}}urlset":
            raise ValueError("sitemap must be a namespaced urlset")
        actual = [node.text or "" for node in xml.findall(f"{{{SITEMAP_NS}}}url/{{{SITEMAP_NS}}}loc")]
        if len(actual) != len(set(actual)):
            result.errors.append("sitemap contains duplicate URLs")
        for url in sorted(expected - set(actual)):
            result.errors.append(f"indexable canonical URL missing from sitemap: {url}")
        for url in sorted(set(actual) - expected):
            result.errors.append(f"sitemap URL is absent, noindex or noncanonical: {url}")
    except (OSError, ValueError, ET.ParseError) as error:
        result.errors.append(f"sitemap validation failed: {error}")

    result.errors = sorted(set(result.errors))
    result.warnings = sorted(set(result.warnings))
    return result
