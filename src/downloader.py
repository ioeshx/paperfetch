from __future__ import annotations

from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen
import time


BROWSER_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"


def download_file(
    url: str,
    destination: str | Path,
    timeout: int = 30,
    retries: int = 3,
    retry_delay: float = 1.0,
) -> Path:
    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)

    request = Request(url, headers={"User-Agent": BROWSER_USER_AGENT})
    last_error: Exception | None = None
    attempt_count = max(1, retries)

    for attempt in range(1, attempt_count + 1):
        try:
            with urlopen(request, timeout=timeout) as response:
                target.write_bytes(response.read())
            return target
        except (HTTPError, URLError, TimeoutError) as exc:
            last_error = exc
            if attempt < attempt_count:
                time.sleep(retry_delay * attempt)

    raise RuntimeError(f"failed to download {url} after {attempt_count} attempts: {last_error}") from last_error


def guess_filename_from_url(url: str, fallback: str) -> str:
    parsed = urlparse(url)
    name = Path(parsed.path).name
    return name or fallback
