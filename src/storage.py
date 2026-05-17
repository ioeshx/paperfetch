from __future__ import annotations

from pathlib import Path

from models import FetchResult, PaperRecord
from models import DownloadFailure, FetchResult, PaperRecord
from utils import ensure_directory, render_markdown_paper_list, write_json


def save_results(
    papers: list[PaperRecord],
    markdown_path: str,
    json_path: str,
    failures: list[DownloadFailure] | None = None,
    failures_path: str = "download_failures.json",
) -> FetchResult:
    markdown_file = Path(markdown_path)
    json_file = Path(json_path)
    failures_file = Path(failures_path)

    if markdown_file.parent != Path("."):
        ensure_directory(markdown_file.parent)
    if json_file.parent != Path("."):
        ensure_directory(json_file.parent)
    if failures_file.parent != Path("."):
        ensure_directory(failures_file.parent)

    markdown_file.write_text(render_markdown_paper_list(papers), encoding="utf-8")
    write_json(json_file, papers)
    failures = failures or []
    write_json(failures_file, failures)
    return FetchResult(
        papers=papers,
        failures=failures,
        markdown_list_path=str(markdown_file),
        json_path=str(json_file),
        failures_path=str(failures_file),
    )
