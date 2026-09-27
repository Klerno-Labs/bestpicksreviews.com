#!/usr/bin/env python3
"""Offline release checks. Exits nonzero for a broken page or silent content removal."""
from pathlib import Path
import sys
from site_inventory import validate_site

root = Path(__file__).resolve().parents[1]
result = validate_site(root)
for warning in result.warnings:
    print(f"WARN: {warning}")
for error in result.errors:
    print(f"ERROR: {error}")
print(f"Checked {result.page_count} HTML pages, {result.review_count} reviews, {result.redirect_count} redirect mappings, {result.indexable_count} indexable URLs; {len(result.errors)} errors, {len(result.warnings)} warnings.")
sys.exit(bool(result.errors))
