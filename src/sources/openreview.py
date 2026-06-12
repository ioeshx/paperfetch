from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from downloader import download_file
from models import PaperRecord, QuerySpec
from utils import ensure_directory, paper_filename


OPENREVIEW_API_BASE_URL = "https://api2.openreview.net"
OPENREVIEW_BASE_URL = "https://api.openreview.net"
OPENREVIEW_USERNAME_ENV = "OPENREVIEW_USERNAME"
OPENREVIEW_PASSWORD_ENV = "OPENREVIEW_PASSWORD"


def fetch_openreview_papers(spec: QuerySpec) -> list[PaperRecord]:
    client = _get_client()
    notes = _get_notes(client, spec)
    papers: list[PaperRecord] = []

    for note in notes:
        paper = parse_note(note)
        if spec.query and not _matches_query(paper, spec.query):
            continue
        if spec.from_date and paper.published_at and paper.published_at.date() < spec.from_date:
            continue
        if spec.to_date and paper.published_at and paper.published_at.date() > spec.to_date:
            continue
        papers.append(paper)

    return papers


def parse_note(note: Any) -> PaperRecord:
    content = _get_note_content(note)
    paper_id = str(_get_note_field(note, "id") or _get_note_field(note, "forum") or _get_note_field(note, "number") or "openreview-note")
    title = _extract_content_value(content, "title")
    abstract = _extract_content_value(content, "abstract")
    authors = _extract_authors(content)
    published_at = _parse_openreview_time(_get_note_field(note, "cdate") or _get_note_field(note, "tcdate"))
    updated_at = _parse_openreview_time(_get_note_field(note, "mdate"))
    pdf_url = _extract_pdf_url(content)
    invitation = _get_note_field(note, "invitation")
    subjects = [str(invitation)] if invitation else []
    return PaperRecord(
        source="openreview",
        paper_id=paper_id,
        title=title or "Untitled",
        abstract=abstract,
        authors=authors,
        published_at=published_at,
        updated_at=updated_at,
        subjects=subjects,
        url=str(_get_note_field(note, "forum") or _get_note_field(note, "id") or ""),
        pdf_url=pdf_url,
        extra={"raw": _note_to_dict(note)},
    )


def download_openreview_pdf(paper: PaperRecord, output_dir: str) -> str:
    if not paper.pdf_url:
        return ""
    destination_dir = ensure_directory(output_dir)
    destination = destination_dir / paper_filename(paper.paper_id, paper.title)
    download_file(paper.pdf_url, destination)
    return str(destination)


def _get_client():
    try:
        import openreview
    except ImportError as exc:
        raise RuntimeError(
            "openreview-py is required for OpenReview fetching. Install it with `python -m pip install openreview-py` or `python -m pip install -e .`."
        ) from exc

    username, password = _get_openreview_credentials()

    # api v2
    return openreview.api.OpenReviewClient(
        baseurl=OPENREVIEW_API_BASE_URL,
        username=username,
        password=password,
    )


def _get_openreview_credentials() -> tuple[str | None, str | None]:
    username = (os.getenv(OPENREVIEW_USERNAME_ENV) or "").strip()
    password = (os.getenv(OPENREVIEW_PASSWORD_ENV) or "").strip()

    if bool(username) != bool(password):
        raise RuntimeError(
            f"Please set both {OPENREVIEW_USERNAME_ENV} and {OPENREVIEW_PASSWORD_ENV}, or set neither for anonymous access."
        )

    if not username:
        return None, None

    return username, password


def _get_notes(client: Any, spec: QuerySpec) -> list[Any]:
    if spec.invitation:
        return client.get_all_notes(invitation=spec.invitation)
    if spec.venue:
        return client.get_all_notes(invitation=f"{spec.venue}/-/Submission")
    if spec.query:
        return client.search_notes(spec.query, 
                                   content="all", 
                                   limit=max(1, spec.limit),
                                #    content="", # Specifies whether to look in all the content, authors, or keywords. Valid inputs: ‘all’, ‘authors’, ‘keywords’
                                #    group="all", # Specifies under which Group to look. E.g. ‘all’, ‘ICLR’, ‘UAI’, etc.
                                #    source="" # Whether to look in papers, replies or all
                                   )   
    return client.get_all_notes(limit=max(1, spec.limit))


def _matches_query(paper: PaperRecord, query: str) -> bool:
    haystack = f"{paper.title}\n{paper.abstract}".lower()
    tokens = [token.lower() for token in query.split() if token.strip()]
    return all(token in haystack for token in tokens)


def _extract_content_value(content: dict[str, Any], key: str) -> str:
    value = content.get(key, "")
    if isinstance(value, dict):
        return str(value.get("value") or value.get("text") or "")
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return str(value or "")


def _extract_authors(content: dict[str, Any]) -> list[str]:
    authors_value = content.get("authors", [])
    if isinstance(authors_value, list):
        return [str(author) for author in authors_value]
    if isinstance(authors_value, dict):
        return [str(authors_value.get("value", ""))]
    if authors_value:
        return [str(authors_value)]
    return []


def _extract_pdf_url(content: dict[str, Any]) -> str:
    pdf_value = content.get("pdf", "")
    if isinstance(pdf_value, dict):
        pdf_url = str(pdf_value.get("value") or pdf_value.get("url") or "")
    else:
        pdf_url = str(pdf_value or "")

    if pdf_url.startswith("/"):
        return f"{OPENREVIEW_BASE_URL}{pdf_url}"
    return pdf_url


def _parse_openreview_time(value: Any) -> datetime | None:
    if value is None:
        return None
    try:
        timestamp = int(value)
    except (TypeError, ValueError):
        return None
    return datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc)


def _get_note_content(note: Any) -> dict[str, Any]:
    if isinstance(note, dict):
        return note.get("content", {}) or {}
    return getattr(note, "content", {}) or {}


def _get_note_field(note: Any, field_name: str) -> Any:
    if isinstance(note, dict):
        return note.get(field_name)
    return getattr(note, field_name, None)


def _note_to_dict(note: Any) -> dict[str, Any]:
    if isinstance(note, dict):
        return note
    if hasattr(note, "to_json"):
        return note.to_json()
    if hasattr(note, "__dict__"):
        return dict(note.__dict__)
    return {"value": str(note)}
