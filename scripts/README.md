# Offline publishing checks

Run these from the repository root; they use Python 3.11+ and Node 22+ with no package install and no remote requests:

```sh
python3 scripts/rebuild_sitemap.py
python3 scripts/validate.py
python3 -m unittest discover -s scripts -p 'test_*.py'
node --test scripts/analytics.test.mjs
```

The sitemap is built from real HTML files that declare exactly one self-canonical and are indexable. It omits the 404, verification files and noindex pages. It deliberately omits `lastmod`; regenerating a sitemap is not an editorial update. Do not reintroduce blanket date refreshes.

`review-baseline.json` preserves the 36 review URLs present before this recovery. Validation fails if any disappears, becomes noindex or loses its homepage link. New reviews are included automatically in sitemap checks; add them to the baseline after review. Retiring a baseline URL requires an explicit editorial and redirect decision, followed by an intentional baseline revision. Do not shrink this list to make a failing build pass.

Research guides use Article markup. Product rich-result markup requires a separate evidence review and a deliberate validator update; do not add invented offers or ratings merely to satisfy a rich-result requirement.

Guides do not need an affiliate link to pass. A verified manufacturer reference is appropriate when a valid commission-earning destination has not been confirmed.

Validation also checks local links/assets, canonicals, sitemap coverage, JSON-LD, unsupported Product nodes (including nested Article subjects), unsupported aggregate ratings and one shared analytics loader per complete HTML document. Pages with that loader must also link `/assets/recovery.css` as a stylesheet so the consent controls remain visible and usable; a preload alone is insufficient. Fragment references warn because some sections may be created at runtime. External product images, merchants, affiliate redirects, live Google indexing and commission status require separate authenticated/live checks; a passing offline run does not verify those systems.

Legacy aliases in `redirects.json` are checked separately: each source must have one immediate meta refresh and a canonical pointing to an existing, indexable destination, without redirect chains. Alias stubs are excluded from the sitemap and do not collect analytics. Their HTML redirects support the current static hosting setup; move the same mapping to server-side permanent redirects when the hosting platform supports them.

The analytics tests use a small in-memory DOM and fake Google transport to exercise consent and event handling without collecting analytics. GitHub Actions runs the same checks on pushes and pull requests. Branch protection must separately require the validation job if merges should be blocked automatically.
