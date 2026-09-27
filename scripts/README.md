# Offline publishing checks

Run these from the repository root; they use Python 3.11+ and Node 22+ with no package install and no remote requests:

```sh
python3 scripts/rebuild_sitemap.py
python3 scripts/build_discovery.py
python3 scripts/validate.py
python3 scripts/build_discovery.py --check
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

## Discovery and ongoing delivery

The visible homepage library is the source for the human directory, `guides.json` and `llms.txt`. `build_discovery.py` refuses to omit or duplicate a guide. Add a new guide to that library with a neutral, descriptive title and category, regenerate discovery and sitemap files, then validate. The human directory works without JavaScript; search is progressive enhancement. A JSON directory and llms.txt are optional conveniences, not Google ranking factors or guaranteed AI citation mechanisms.

Every guide should have a visible evidence statement, source links, honest author attribution, stable section anchors, related guides, ordinary merchant links with clear affiliate labels and accurate Article markup. Keep factual review dates; navigation changes do not justify changing editorial dates. Do not create pages for every keyword variation.

After a Pages deployment, run `python3 scripts/check_live.py --output /tmp/bestpicks-live-health.json`. It checks canonical HTML, redirects, index/snippet permissions, structured data, robots, discovery files and diagnostic search-agent responses. It never follows affiliate links. These synthetic requests do not prove access from a provider's actual IP addresses. Review Cloudflare crawl logs separately when real access is uncertain.

The `Daily live site health` workflow runs daily at 13:17 UTC and can be dispatched manually. It needs no account analytics credentials. Results remain GitHub artifacts for 30 days; failed runs use the account's existing GitHub Actions notification preferences. Scheduled runs may be delayed by GitHub and schedules on inactive public repositories may be disabled; the editorial operator must verify recent successful runs.

Editorial operations and private metrics are maintained outside this public repository in the owner's workspace audit directory. Never commit account exports, session details, API keys, private advertiser terms or financial reports here.
