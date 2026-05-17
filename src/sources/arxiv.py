from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import quote_plus
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

from downloader import BROWSER_USER_AGENT, download_file
from models import PaperRecord, QuerySpec
from utils import ensure_directory, paper_filename


ARXIV_API_URL = "https://export.arxiv.org/api/query"
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}


def build_search_query(spec: QuerySpec) -> str:
    clauses: list[str] = []
    if spec.query:
        clauses.append(f"all:{spec.query}")
    if spec.subject:
        clauses.append(f"cat:{spec.subject}")
    return " AND ".join(clauses) if clauses else "all:electron"


def fetch_arxiv_papers(spec: QuerySpec) -> list[PaperRecord]:
    search_query = build_search_query(spec)
    url = (
        f"{ARXIV_API_URL}?search_query={quote_plus(search_query)}"
        f"&start=0&max_results={spec.limit}"
        f"&sortBy={quote_plus(spec.sort_by)}&sortOrder={quote_plus(spec.sort_order)}"
    )
    request = Request(url, headers={"User-Agent": BROWSER_USER_AGENT})
    with urlopen(request, timeout=30) as response:
        xml_bytes = response.read()

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
