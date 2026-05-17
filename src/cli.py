from __future__ import annotations

import argparse
from pathlib import Path

from models import DownloadFailure, PaperRecord, QuerySpec
from sources.arxiv import download_arxiv_pdf, fetch_arxiv_papers
from sources.openreview import download_openreview_pdf, fetch_openreview_papers
from storage import save_results
from utils import parse_date


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="paperfetch", description="Fetch arXiv and OpenReview papers")
    parser.add_argument("--source", choices=["all", "arxiv", "openreview"], default="all")
    parser.add_argument("--query", default="")
    parser.add_argument("--subject", default="")
    parser.add_argument("--venue", default="")
    parser.add_argument("--invitation", default="")
    parser.add_argument("--from-date", default="")
    parser.add_argument("--to-date", default="")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--sort-by", default="submittedDate")
    parser.add_argument("--sort-order", default="descending")
    parser.add_argument("--no-download", action="store_true")
    parser.add_argument("--output-dir", default="downloads")
    parser.add_argument("--markdown-path", default="papers.md")
    parser.add_argument("--json-path", default="papers.json")
    parser.add_argument("--failures-path", default="download_failures.json")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    spec = QuerySpec(
        source=args.source,
        query=args.query,
        subject=args.subject,
        venue=args.venue,
        invitation=args.invitation,
        from_date=parse_date(args.from_date),
        to_date=parse_date(args.to_date),
        limit=args.limit,
        sort_by=args.sort_by,
        sort_order=args.sort_order,
        download=not args.no_download,
        output_dir=args.output_dir,
        markdown_path=args.markdown_path,
        json_path=args.json_path,
        failures_path=args.failures_path,
    )

    papers: list[PaperRecord] = []
    if spec.source in ("all", "arxiv"):
        papers.extend(fetch_arxiv_papers(spec))
    if spec.source in ("all", "openreview"):
        papers.extend(fetch_openreview_papers(spec))

    failures: list[DownloadFailure] = []
    if spec.download:
        for paper in papers:
            if not paper.pdf_url:
                failures.append(
                    DownloadFailure(
                        source=paper.source,
                        paper_id=paper.paper_id,
                        title=paper.title,
                        url=paper.pdf_url,
                        error="missing pdf url",
                        attempts=0,
                    )
                )
                continue

            try:
                if paper.source == "arxiv":
                    paper.local_pdf_path = download_arxiv_pdf(paper, Path(spec.output_dir) / "arxiv")
                elif paper.source == "openreview":
                    paper.local_pdf_path = download_openreview_pdf(paper, Path(spec.output_dir) / "openreview")
            except RuntimeError as exc:
                failures.append(
                    DownloadFailure(
                        source=paper.source,
                        paper_id=paper.paper_id,
                        title=paper.title,
                        url=paper.pdf_url,
                        error=str(exc),
                        attempts=3,
                    )
                )

    result = save_results(
        papers,
        spec.markdown_path,
        spec.json_path,
        failures=failures,
        failures_path=spec.failures_path,
    )
    print(f"Fetched {len(papers)} papers")
    print(f"Markdown list: {spec.markdown_path}")
    print(f"JSON output: {spec.json_path}")
    print(f"Failures: {result.failures_path} ({len(failures)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
