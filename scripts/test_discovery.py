"""Regression coverage for accidental discovery and search-access regressions."""
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import shutil
import unittest
from build_discovery import ROOT, render
from check_live import html_issues


class DiscoveryChecks(unittest.TestCase):
    def test_every_guide_is_in_html_json_and_text_map(self):
        outputs = render(ROOT)
        entries = json.loads(outputs['guides.json'])['guides']
        self.assertGreaterEqual(len(entries), 36)
        for entry in entries:
            self.assertIn(entry['url'], outputs['sitemap-content.html'])
            self.assertIn(entry['url'], outputs['llms.txt'])

    def test_missing_homepage_listing_cannot_silently_drop_guide(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            shutil.copytree(ROOT, root, dirs_exist_ok=True, ignore=shutil.ignore_patterns('.git', '__pycache__'))
            path = root / 'index.html'
            path.write_text(path.read_text().replace('class="bp-guide-title"', 'class="removed-guide-title"', 1))
            with self.assertRaises(ValueError):
                render(root)

    def test_live_check_rejects_soft_404_and_snippet_blocks(self):
        url = 'https://bestpicksreviews.com/'
        good = '<html><head><link rel="canonical" href="' + url + '"></head><body><h1>BestPicks</h1></body></html>'
        self.assertEqual(html_issues(url, 200, {}, good), [])
        self.assertTrue(html_issues(url, 200, {}, '<html><h1>Not found</h1></html>'))
        self.assertTrue(html_issues(url, 200, {'x-robots-tag': 'noindex'}, good))
        self.assertTrue(html_issues(url, 200, {'x-robots-tag': 'max-snippet:0'}, good))
        self.assertTrue(html_issues(url, 410, {}, good))


if __name__ == '__main__':
    unittest.main()
