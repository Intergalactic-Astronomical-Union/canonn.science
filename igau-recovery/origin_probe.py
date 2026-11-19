#!/usr/bin/env python3
"""Recover *verified binary candidates* from original Canonn media endpoints.

Bounded, opt-in, hard-coded research targets. Nothing is published, and
archive/HTTP leads are not counted as recovered media without signature checks.
Original attribution and re-use rights must be reviewed before an upstream PR.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

HOST_CDN = "cdn-5f3c0a05c1ac180394b62f3c.closte.com"
TARGETS = [
    {
        "key": "odysseus-our-new-eden-1",
        "expected": "ogg",
        "filename": "Odysseus-Our-New-Eden-1-5.ogg",
        "paths": ["/wp-content/uploads/2017/05/Odysseus-Our-New-Eden-1-5.ogg"],
        "hosts": ["canonn.science", HOST_CDN, "science.canonn.tech"],
        "article": "generation-ship-odysseus",
    },
    {
        "key": "guardian-robolobster-001-a",
        "expected": "jpeg",
        "filename": "ancient_medium_001-A.jpeg",
        "paths": ["/wp-content/uploads/2026/06/ancient_medium_001-A.jpeg"],
        "hosts": ["canonn.science", HOST_CDN, "science.canonn.tech"],
        "article": "guardian-structure",
    },
    {
        "key": "historical-lore-thargoid-photo",
        "expected": "jpeg",
        "filename": "Active_Thargoid_Site-small-1024x576.jpg",
        "paths": ["/wp-content/uploads/2017/04/Active_Thargoid_Site-small-1024x576.jpg"],
        "hosts": ["canonn.science", HOST_CDN],
        "article": "lore",
    },
]
MAX_ASSET_BYTES = 24 * 1024 * 1024
REQUEST_DELAY_SECONDS = 3.2
REQUEST_TIMEOUT_SECONDS = 15
USER_AGENT = "IGAU-Canonn-archive-research/1.0 (public historical-source verification)"


def media_signature(data: bytes, expected: str) -> bool:
    if expected == "jpeg":
        return data.startswith(b"\xff\xd8\xff") and data.endswith(b"\xff\xd9")
    if expected == "png":
        return data.startswith(b"\x89PNG\r\n\x1a\n")
    if expected == "ogg":
        return data.startswith(b"OggS")
    if expected == "mp3":
        return data.startswith(b"ID3") or data[:2] == b"\xff\xfb"
    return False


def fetch_bytes(url: str) -> tuple[bytes, str, str]:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        final_url = response.geturl()
        host = (urlparse(final_url).hostname or "").lower()
        allowed = {"canonn.science", HOST_CDN, "science.canonn.tech", "web.archive.org"}
        if host not in allowed:
            raise ValueError(f"Disallowed redirect hostname: {host}")
        mimetype = response.headers.get("Content-Type", "")
        data = response.read(MAX_ASSET_BYTES + 1)
    if len(data) > MAX_ASSET_BYTES:
        raise ValueError("File too large for bounded recovery attempt")
    return data, mimetype, final_url


def snapshot_url(original_url: str) -> tuple[str, str]:
    api = "https://archive.org/wayback/available?" + urlencode({"url": original_url})
    req = Request(api, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        result = json.loads(response.read(250_000))
    near = result.get("archived_snapshots", {}).get("closest", {})
    if not near.get("available") or str(near.get("status")) != "200":
        return "", "no_snapshot_reported_by_api"
    url = str(near.get("url", ""))
    if (urlparse(url).hostname or "").lower() != "web.archive.org":
        return "", "invalid_archive_host"
    # Request the original media bytes (avoid injecting Wayback HTML toolbar).
    url = re.sub(r"/web/(\d{14})/", r"/web/\1id_/", url, count=1)
    if "id_/" not in url:
        return "", "unrecognized_snapshot_format"
    return url, "candidate_unverified"


def run(out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    acquired = out / "media-candidates"
    acquired.mkdir(exist_ok=True)
    manifest = []
    requests_sent = 0
    found = set()

    def polite_delay():
        if requests_sent:
            time.sleep(REQUEST_DELAY_SECONDS)

    for item in TARGETS:
        for host in item["hosts"]:
            url = "https://" + host + item["paths"][0]
            entry = {"article": item["article"], "key": item["key"],
                     "original_url": url, "expected": item["expected"],
                     "direct_status": "not_attempted",
                     "archive_status": "not_attempted",
                     "direct_mimetype": "", "snapshot": "",
                     "source_url": "", "sha256": "", "local_file": "",
                     "bytes": 0}
            # Direct historical WordPress/CDN source.
            try:
                polite_delay()
                requests_sent += 1
                data, mimetype, final_url = fetch_bytes(url)
                entry["direct_mimetype"] = mimetype
                if media_signature(data, item["expected"]):
                    entry["direct_status"] = "valid_original_media_bytes"
                    entry["source_url"] = final_url
                    entry["sha256"] = hashlib.sha256(data).hexdigest()
                    entry["bytes"] = len(data)
                    if item["key"] not in found:
                        filename = item["key"] + "." + item["filename"].rsplit(".", 1)[-1]
                        (acquired / filename).write_bytes(data)
                        entry["local_file"] = "media-candidates/" + filename
                        found.add(item["key"])
                else:
                    entry["direct_status"] = "not_valid_media_signature"
            except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
                entry["direct_status"] = type(exc).__name__ + ": " + str(exc)[:140]

            # Check archive for each historical URL (not the newer /assets/media URL).
            try:
                polite_delay()
                requests_sent += 1
                snapshot, status = snapshot_url(url)
                entry["archive_status"], entry["snapshot"] = status, snapshot
                if snapshot and item["key"] not in found:
                    polite_delay()
                    requests_sent += 1
                    data, mimetype, final_url = fetch_bytes(snapshot)
                    if media_signature(data, item["expected"]):
                        entry["archive_status"] = "verified_archive_media_bytes"
                        entry["source_url"] = final_url
                        entry["sha256"] = hashlib.sha256(data).hexdigest()
                        entry["bytes"] = len(data)
                        filename = item["key"] + "." + item["filename"].rsplit(".", 1)[-1]
                        (acquired / filename).write_bytes(data)
                        entry["local_file"] = "media-candidates/" + filename
                        found.add(item["key"])
                    else:
                        entry["archive_status"] = "snapshot_not_valid_media_signature"
            except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
                entry["archive_status"] = type(exc).__name__ + ": " + str(exc)[:140]
            manifest.append(entry)

    summary = {"targets": len(TARGETS), "historical_urls_checked": len(manifest),
               "http_requests": requests_sent,
               "verified_binary_assets": len(found),
               "verified_asset_keys": sorted(found)}
    (out / "manifest.json").write_text(
        json.dumps({"summary": summary, "attempts": manifest}, indent=2)
        + "\n", encoding="utf-8")
    (out / "summary.md").write_text(
        "# IGAU historical original-media probe\n\n"
        "No media is approved for upstream use by this scan. Confirm content, "
        "authorship and permissions before redistribution.\n\n"
        + "\n".join(f"- {k}: {v}" for k, v in summary.items())
        + "\n\nSee manifest.json for exact historical source URLs and outcomes.\n",
        encoding="utf-8",
    )
    return summary


if __name__ == "__main__":
    result = run(Path("origin-research-results"))
    print(json.dumps(result, indent=2))
