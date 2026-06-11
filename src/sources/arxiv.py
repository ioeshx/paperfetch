from __future__ import annotations

import time
from datetime import date, datetime, time as dt_time, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import quote_plus
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

from downloader import BROWSER_USER_AGENT, download_file
from models import PaperRecord, QuerySpec
from utils import ensure_directory, paper_filename


ARXIV_API_URL = "http://export.arxiv.org/api/query"
ARXIV_REQUEST_TIMEOUT = 30
ARXIV_MAX_RETRIES = 3
ARXIV_RETRY_DELAY_SECONDS = 3.0
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}


def build_search_query(spec: QuerySpec) -> str:
    clauses: list[str] = []
    if spec.query:
        clauses.append(f'all:"{_escape_query_phrase(spec.query)}"+AND+cat:{spec.source}')
    if spec.subject:
        clauses.append(f"cat:{spec.subject}")
    if spec.from_date or spec.to_date:
        clauses.append(f"submittedDate:{_format_submitted_date_range(spec.from_date, spec.to_date)}")
    return " AND ".join(clauses) if clauses else "all:electron"


def fetch_arxiv_papers(spec: QuerySpec) -> list[PaperRecord]:
    search_query = build_search_query(spec)
    url = (
        f"{ARXIV_API_URL}?search_query={quote_plus(search_query)}"
        f"&start=0&max_results={spec.limit}"
        f"&sortBy={quote_plus(spec.sort_by)}&sortOrder={quote_plus(spec.sort_order)}"
    )
    print("url:", url)
    xml_bytes = _fetch_arxiv_feed(url)

    root = ET.fromstring(xml_bytes)
    papers: list[PaperRecord] = []
    for entry in root.findall("atom:entry", ATOM_NS):
        paper = parse_entry(entry)
        if spec.from_date and paper.published_at and paper.published_at.date() < spec.from_date:
            continue
        if spec.to_date and paper.published_at and paper.published_at.date() > spec.to_date:
            continue
        papers.append(paper)
    return papers


def parse_entry(entry: ET.Element) -> PaperRecord:
    paper_id = _text(entry, "atom:id")
    arxiv_id = paper_id.rsplit("/", 1)[-1]
    title = _text(entry, "atom:title").replace("\n", " ").strip()
    abstract = _text(entry, "atom:summary").replace("\n", " ").strip()
    authors = [author.findtext("atom:name", default="", namespaces=ATOM_NS).strip() for author in entry.findall("atom:author", ATOM_NS)]
    published_at = _parse_atom_datetime(_text(entry, "atom:published"))
    updated_at = _parse_atom_datetime(_text(entry, "atom:updated"))
    subjects = [category.attrib.get("term", "") for category in entry.findall("atom:category", ATOM_NS) if category.attrib.get("term")]
    pdf_url = _find_pdf_url(entry) or f"https://arxiv.org/pdf/{arxiv_id}.pdf"
    return PaperRecord(
        source="arxiv",
        paper_id=arxiv_id,
        title=title,
        abstract=abstract,
        authors=authors,
        published_at=published_at,
        updated_at=updated_at,
        subjects=subjects,
        url=paper_id,
        pdf_url=pdf_url,
        extra={"raw": {"id": paper_id, "subjects": subjects}},
    )


def download_arxiv_pdf(paper: PaperRecord, output_dir: str) -> str:
    destination_dir = ensure_directory(output_dir)
    destination = destination_dir / paper_filename(paper.paper_id, paper.title)
    download_file(paper.pdf_url, destination)
    return str(destination)


def _fetch_arxiv_feed(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": BROWSER_USER_AGENT, "Accept": "application/atom+xml"})
    last_error: Exception | None = None

    for attempt in range(1, ARXIV_MAX_RETRIES + 1):
        try:
            print(f"Fetching arXiv feed (attempt {attempt}/{ARXIV_MAX_RETRIES})...")
            with urlopen(request, timeout=ARXIV_REQUEST_TIMEOUT) as response:
                return response.read()
        except HTTPError as exc:
            last_error = exc
            if exc.code not in (429, 500, 502, 503, 504):
                break
        except (TimeoutError, URLError) as exc:
            last_error = exc

        if attempt < ARXIV_MAX_RETRIES:
            time.sleep(ARXIV_RETRY_DELAY_SECONDS * attempt)

    raise RuntimeError(f"arXiv API request failed after {ARXIV_MAX_RETRIES} attempts: {last_error}") from last_error


def _text(entry: ET.Element, path: str) -> str:
    value = entry.findtext(path, default="", namespaces=ATOM_NS)
    return value or ""


def _parse_atom_datetime(value: str) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized).astimezone(timezone.utc)


def _find_pdf_url(entry: ET.Element) -> str:
    for link in entry.findall("atom:link", ATOM_NS):
        if link.attrib.get("title") == "pdf" or link.attrib.get("type") == "application/pdf":
            return link.attrib.get("href", "")
    return ""


def _format_submitted_date_range(from_date: date | None, to_date: date | None) -> str:
    start_date = from_date or date(1970, 1, 1)
    end_date = to_date or date.today()
    start_dt = datetime.combine(start_date, dt_time.min, tzinfo=timezone.utc)
    end_dt = datetime.combine(end_date, dt_time(23, 59), tzinfo=timezone.utc)
    return f"[{start_dt:%Y%m%d%H%M} TO {end_dt:%Y%m%d%H%M}]"


def _escape_query_phrase(value: str) -> str:
    return value.replace('"', r'\"').strip()
