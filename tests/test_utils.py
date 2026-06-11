from datetime import date
from pathlib import Path

import pytest

import downloader
from models import QuerySpec
from sources.arxiv import build_search_query
from utils import paper_filename, render_markdown_paper_list, slugify_filename


def test_slugify_filename_replaces_spaces_and_invalid_chars():
    assert slugify_filename('A Title: With / Bad*Chars?') == 'A_Title_With_Bad_Chars'


def test_paper_filename_keeps_id_and_title():
    assert paper_filename('1234.5678v1', 'My Paper Title') == '1234.5678v1_My_Paper_Title.pdf'


def test_render_markdown_paper_list():
    class Paper:
        title = 'Paper One'
        abstract = 'Abstract One'

    assert render_markdown_paper_list([Paper()]) == '1. Paper One\n   Abstract One\n'


def test_download_file_retries(monkeypatch, tmp_path: Path):
    calls = {"count": 0}

    class DummyResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b"ok"

    def fake_urlopen(request, timeout=30):
        calls["count"] += 1
        if calls["count"] < 3:
            raise TimeoutError("temporary failure")
        return DummyResponse()

    monkeypatch.setattr(downloader, "urlopen", fake_urlopen)

    output = downloader.download_file("https://example.com/test.pdf", tmp_path / "test.pdf", retries=3, retry_delay=0)

    assert output.read_bytes() == b"ok"
    assert calls["count"] == 3


def test_arxiv_search_query_quotes_phrase_and_filters_dates():
    query = build_search_query(
        QuerySpec(
            query="concept erasure",
            subject="cs.AI",
            from_date=date(2026, 5, 1),
            to_date=date(2026, 5, 17),
        )
    )

    assert 'all:"concept erasure"' in query
    assert 'cat:cs.AI' in query
    assert 'submittedDate:[' in query

