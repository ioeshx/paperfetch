# paperfetch

Fetch papers from arXiv and OpenReview, export metadata, download PDFs when available, and generate a Markdown paper list.

## TODO
- [x] arxiv (rate limit会导致429失败，过段时间重试)
- [ ] openreview （）


## ref
https://info.arxiv.org/help/api/basics.html

https://info.arxiv.org/help/api/user-manual.html

https://docs.openreview.net/reference/api-v2

https://github.com/openreview/openreview-py

https://zhuanlan.zhihu.com/p/679538991

## Usage

### 1. Run directly with Python

Use Python 3.10 or newer.

```bash
python src/cli.py \
	--source arxiv \
	--query "concept erasure" \
	--subject cs.AI \
	--from-date 2026-05-01 \
	--to-date 2026-05-17 \
	--limit 100 \
	--output-dir downloads/concept_erasure \
	--markdown-path outputs/concept_erasure.md \
	--json-path outputs/concept_erasure.json \
	--failures-path outputs/concept_erasure_failures.json
```

### 2. Output files

- `--source`: `all`, `arxiv`, or `openreview`
- `--query`: keyword search text
- `--subject`: arXiv subject such as `cs.AI` or `cs.CV`
- `--venue`: OpenReview venue prefix, such as `ICLR.cc/2025/Conference`
- `--invitation`: OpenReview invitation ID, used when you need a more exact filter
- `--from-date` and `--to-date`: ISO dates in `YYYY-MM-DD` format
- `--limit`: maximum number of results per source
- `--sort-by` and `--sort-order`: arXiv sorting controls
- `--no-download`: skip PDF downloads and only save metadata
- `--output-dir`: root directory for downloaded PDFs
- `--markdown-path`: output path for the Markdown paper list
- `--json-path`: output path for the metadata JSON
- `--failures-path`: output path for failed download records

By default this command writes:

- `papers.md`: a Markdown list in the form

```markdown
1. title 1
	abstract 1
2. title 2
	abstract 2
```

- `papers.json`: structured metadata for all fetched papers
- `download_failures.json`: failed download records with source, paper ID, title, URL, error, and attempt count
- `downloads/`: downloaded PDFs, split into `downloads/arxiv` and `downloads/openreview`

### 3. Notes

- arXiv PDFs are saved with the original arXiv ID plus the title, with spaces converted to underscores.
- Download failures do not stop the whole batch; they are recorded and written to the failures file.
- If a paper has no PDF URL, it is still included in the metadata and Markdown list.
- OpenReview fetching uses the official `openreview-py` client.
