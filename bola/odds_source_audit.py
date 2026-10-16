"""Probe public odds URLs without credentials and record transport evidence."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile


DEFAULT_URLS = (
    "https://1xbet.com",
    "https://1xbet.com/id",
    "https://1xbx.site",
    "https://1xlite-118654.top/id",
)
STATUS_LINE = re.compile(r"^HTTP/\S+\s+(\d{3})(?:\s+.*)?$")


def _status_chain(headers: bytes) -> list[int]:
    statuses = []
    for line in headers.decode("iso-8859-1", errors="replace").splitlines():
        match = STATUS_LINE.match(line.strip())
        if match:
            statuses.append(int(match[1]))
    return statuses


def probe(url: str, timeout: int = 20) -> dict:
    """Fetch a URL through the configured network path, never sending credentials."""
    checked_at = datetime.now(timezone.utc).isoformat()
    with tempfile.NamedTemporaryFile() as header_file, tempfile.NamedTemporaryFile() as body_file:
        command = ["curl", "--http1.1", "--max-time", str(timeout), "--connect-timeout", "10",
                   "--silent", "--show-error", "--location", "--dump-header", header_file.name,
                   "--output", body_file.name,
                   "--write-out", "%{http_code}\t%{url_effective}\t%{content_type}\t%{size_download}", url]
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        summary = completed.stdout.strip().split("\t")
        body = body_file.read()
        headers = header_file.read()
    status_chain = _status_chain(headers)
    http_code = int(summary[0]) if summary and summary[0].isdigit() else 0
    result = {
        "url": url, "checked_at": checked_at, "curl_exit_code": completed.returncode,
        "http_code": http_code, "effective_url": summary[1] if len(summary) > 1 else url,
        "content_type": summary[2] if len(summary) > 2 else "",
        "size_bytes": len(body), "status_chain": status_chain,
        "body_sha256": hashlib.sha256(body).hexdigest() if body else None,
        "odds_observed": False,
        "transport_error": completed.stderr.strip() or None,
        "interpretation": "No machine-readable odds quote was observed.",
    }
    if http_code == 403 or 403 in status_chain:
        result["interpretation"] = "Access denied (HTTP 403); no odds quote was used."
    elif completed.returncode != 0:
        result["interpretation"] = "Transport failed before a usable odds page; no quote was used."
    elif http_code >= 400:
        result["interpretation"] = f"HTTP {http_code}; no odds quote was used."
    return result


def audit(urls: list[str], timeout: int = 20) -> dict:
    if not urls:
        raise ValueError("At least one URL is required")
    results = [probe(url, timeout) for url in urls]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "urls_requested": urls, "quotes_observed": sum(item["odds_observed"] for item in results),
        "results": results,
        "limitations": [
            "The probe uses public unauthenticated HTTP requests and does not log in.",
            "An access response is not an odds quote and cannot satisfy a timestamped-market gate.",
            "A page body, if returned, is not parsed as a quote without match, market, three prices, and capture time.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", action="append", dest="urls", default=[])
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.urls or list(DEFAULT_URLS), args.timeout)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"urls": len(result["results"]), "quotes_observed": result["quotes_observed"]}, indent=2))


if __name__ == "__main__":
    main()
