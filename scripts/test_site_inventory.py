import json
from pathlib import Path
import tempfile
import unittest
from site_inventory import ORIGIN, inventory, render_sitemap, validate_site


class SiteSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "scripts").mkdir()
        (self.root / "assets").mkdir()
        (self.root / "assets/analytics.js").write_text("// stub")
        (self.root / "assets/recovery.css").write_text("/* consent styles */")
        self.reviews = [f"/best-example-{i}/" for i in range(36)]
        (self.root / "scripts/review-baseline.json").write_text(json.dumps({"requiredReviewPaths": self.reviews}))
        for path in self.reviews:
            self.page(path)
        self.page("/", "".join(f'<a href="{path}">Review</a>' for path in self.reviews))
        self.page("/privacy.html", noindex=True)
        self.page("/404.html", noindex=True)
        (self.root / "verification.html").write_text("verification-token")
        self.rebuild()

    def page(self, path, body="", noindex=False):
        file = self.root / (path.lstrip("/") + "index.html" if path.endswith("/") else path.lstrip("/"))
        file.parent.mkdir(parents=True, exist_ok=True)
        robots = '<meta name="robots" content="noindex, follow">' if noindex else ''
        file.write_text(f'<!doctype html><html><head>{robots}<link rel="canonical" href="{ORIGIN}{path}"><link rel="stylesheet" href="/assets/recovery.css"></head><body>{body}<script src="/assets/analytics.js" defer></script></body></html>')
        return file

    def rebuild(self):
        (self.root / "sitemap.xml").write_text(render_sitemap(inventory(self.root)))

    def test_valid_site_does_not_require_affiliate_links_and_excludes_noindex(self):
        self.assertEqual(validate_site(self.root).errors, [])
        sitemap = (self.root / "sitemap.xml").read_text()
        self.assertNotIn("lastmod", sitemap)
        for excluded in ["404.html", "privacy.html", "verification.html"]:
            self.assertNotIn(excluded, sitemap)

    def test_removed_review_fails_even_after_sitemap_is_regenerated(self):
        (self.root / "best-example-0/index.html").unlink()
        self.rebuild()
        errors = validate_site(self.root).errors
        self.assertTrue(any("required review removed" in error for error in errors))

    def test_consent_controls_require_their_stylesheet(self):
        file = self.root / "best-example-0/index.html"
        original = file.read_text()
        stylesheet = '<link rel="stylesheet" href="/assets/recovery.css">'
        for replacement in ("", '<link rel="preload" as="style" href="/assets/recovery.css">'):
            with self.subTest(replacement=replacement):
                file.write_text(original.replace(stylesheet, replacement))
                self.assertTrue(any("requires the consent stylesheet" in error for error in validate_site(self.root).errors))
        file.write_text(original)
        self.assertEqual(validate_site(self.root).errors, [])

    def test_unlinked_review_and_noindex_sitemap_entry_fail(self):
        self.page("/", "".join(f'<a href="{path}">Review</a>' for path in self.reviews[1:]))
        sitemap = self.root / "sitemap.xml"
        sitemap.write_text(sitemap.read_text().replace("</urlset>", f'<url><loc>{ORIGIN}/privacy.html</loc></url></urlset>'))
        errors = validate_site(self.root).errors
        self.assertTrue(any("homepage does not link" in error for error in errors))
        self.assertTrue(any("noindex or noncanonical" in error for error in errors))

    def test_broken_assets_invalid_schema_and_unproven_ratings_fail(self):
        self.page(self.reviews[0], '<img src="/missing.png"><script type="application/ld+json">{broken}</script><script type="application/ld+json">{"@type":"Product","aggregateRating":{"ratingValue":5}}</script>')
        errors = validate_site(self.root).errors
        self.assertTrue(any("broken internal" in error for error in errors))
        self.assertTrue(any("invalid JSON-LD" in error for error in errors))
        self.assertTrue(any("unsupported aggregateRating" in error for error in errors))

    def test_redirects_are_excluded_and_must_resolve_without_chains(self):
        source = "/review-best-example-0/"
        destination = self.reviews[0]
        directory = self.root / source.lstrip("/")
        directory.mkdir()
        (directory / "index.html").write_text(f'<html><head><meta http-equiv="refresh" content="0; url={destination}"><link rel="canonical" href="{ORIGIN}{destination}"></head><body><a href="{destination}">Continue</a></body></html>')
        (self.root / "redirects.json").write_text(json.dumps({source: destination}))
        self.rebuild()
        self.assertEqual(validate_site(self.root).errors, [])
        self.assertNotIn("review-best-example", (self.root / "sitemap.xml").read_text())
        stub = directory / "index.html"
        original = stub.read_text()
        stub.write_text(original.replace("<head>", '<head><meta name="robots" content="noindex">'))
        self.assertTrue(any("redirect stub must not contradict" in error for error in validate_site(self.root).errors))
        stub.write_text(original)
        self.page(destination, noindex=True)
        self.rebuild()
        self.assertTrue(any("redirect destination" in error for error in validate_site(self.root).errors))

    def test_redirect_chains_fail(self):
        mapping = {"/review-old/": "/review-new/", "/review-new/": self.reviews[0]}
        for source, destination in mapping.items():
            directory = self.root / source.lstrip("/")
            directory.mkdir()
            (directory / "index.html").write_text(f'<html><meta http-equiv="refresh" content="0; url={destination}"><link rel="canonical" href="{ORIGIN}{destination}"></html>')
        (self.root / "redirects.json").write_text(json.dumps(mapping))
        self.rebuild()
        self.assertTrue(any("chained" in error for error in validate_site(self.root).errors))

    def test_duplicate_sitemap_urls_fail(self):
        sitemap = self.root / "sitemap.xml"
        sitemap.write_text(sitemap.read_text().replace("</urlset>", f'<url><loc>{ORIGIN}/</loc></url></urlset>'))
        self.assertTrue(any("duplicate URLs" in error for error in validate_site(self.root).errors))


if __name__ == "__main__":
    unittest.main()
