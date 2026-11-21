"""corpus/urls.csv must stay well-formed, because cached essays are keyed by these URLs."""

import csv
from pathlib import Path

URLS = Path(__file__).resolve().parent.parent / "corpus" / "urls.csv"
HEADER = ["title", "author", "url", "license", "notes"]


def _rows() -> list[dict[str, str]]:
    with URLS.open(newline="") as f:
        return list(csv.DictReader(f))


def test_header_is_expected() -> None:
    with URLS.open(newline="") as f:
        assert next(csv.reader(f)) == HEADER


def test_every_row_has_title_and_https_url() -> None:
    for row in _rows():
        assert row["title"].strip(), row
        assert row["url"].startswith("https://"), row


def test_urls_are_unique() -> None:
    urls = [r["url"] for r in _rows()]
    assert len(urls) == len(set(urls))


def test_non_public_domain_rows_say_url_only() -> None:
    """Copyrighted text is never committed, so every row here must be marked URL only."""
    for row in _rows():
        assert "URL only" in row["license"], row
