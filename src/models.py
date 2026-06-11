from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Optional


@dataclass(slots=True)
class QuerySpec:
    source: str = "all"
    query: str = ""
    subject: str = ""
    venue: str = ""
    invitation: str = ""
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    limit: int = 20
    sort_by: str = "submittedDate"  # sortBy: value in [relevance, lastUpdatedDate, submittedDate]
    sort_order: str = "descending"  # sortOrder value in [ascending, descending]
    download: bool = True
    output_dir: str = "downloads"
    markdown_path: str = "papers.md"
    json_path: str = "papers.json"

    failures_path: str = "download_failures.json"

# 

@dataclass(slots=True)
class PaperRecord:
    source: str
    paper_id: str
    title: str
    abstract: str
    authors: list[str] = field(default_factory=list)
    published_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    subjects: list[str] = field(default_factory=list)
    url: str = ""
    pdf_url: str = ""
    local_pdf_path: str = ""
    local_markdown_path: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

@dataclass(slots=True)
class DownloadFailure:
    source: str
    paper_id: str
    title: str
    url: str
    error: str
    attempts: int


@dataclass(slots=True)
class FetchResult:
    papers: list[PaperRecord]
    failures: list[DownloadFailure] = field(default_factory=list)
    markdown_list_path: str = ""
    json_path: str = ""
    failures_path: str = ""
    errors: list[str] = field(default_factory=list)
