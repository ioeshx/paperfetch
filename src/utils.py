from __future__ import annotations

import json
import re
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any


INVALID_FILENAME_CHARS = r'<>:"/\\|?*'


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def ensure_directory(path: str | Path) -> Path:
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def slugify_filename(text: str) -> str:
    cleaned = text.strip()
    cleaned = re.sub(rf"[{re.escape(INVALID_FILENAME_CHARS)}]", "_", cleaned)
    cleaned = re.sub(r"\s+", "_", cleaned)
    cleaned = re.sub(r"_+", "_", cleaned)
    cleaned = cleaned.strip("._ ")
    return cleaned or "paper"


def paper_filename(paper_id: str, title: str, extension: str = ".pdf") -> str:
    safe_id = slugify_filename(paper_id)
    safe_title = slugify_filename(title)
    return f"{safe_id}_{safe_title}{extension}"


def render_markdown_paper_list(papers: list[Any]) -> str:
    lines: list[str] = []
    for index, paper in enumerate(papers, start=1):
        title = getattr(paper, "title", "") or "Untitled"
        abstract = getattr(paper, "abstract", "") or ""
        lines.append(f"{index}. {title}")
        lines.append(f"   {abstract}")
    return "\n".join(lines).rstrip() + ("\n" if lines else "")


def write_json(path: str | Path, data: Any) -> None:
    serializable = data
    if is_dataclass(data):
        serializable = asdict(data)
    elif isinstance(data, list):
        serializable = [asdict(item) if is_dataclass(item) else item for item in data]
    Path(path).write_text(
        json.dumps(serializable, ensure_ascii=False, indent=2, default=_json_default),
        encoding="utf-8",
    )


def _json_default(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if is_dataclass(value):
        return asdict(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")
