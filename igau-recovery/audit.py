#!/usr/bin/env python3
"""Read-only audit of Canonn article media paths; no third-party dependencies."""
import argparse
import csv
import json
import re
import subprocess
import time
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, unquote, urlparse, urlencode
from urllib.request import Request, urlopen

FIELDS = ["slug", "title", "section", "source_file", "attribute", "url",
          "classification", "possible_local_variant", "archive_target",
          "wayback_status", "wayback_snapshot", "search_url"]


class AssetLinks(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.refs = []

    def handle_starttag(self, tag, attributes):
        self.collect(tag, attributes)

    def handle_startendtag(self, tag, attributes):
        self.collect(tag, attributes)

    def collect(self, tag, attributes):
        attrs = dict(attributes)
        for key in ("src", "poster", "data-src", "href"):
            if attrs.get(key) and (key != "href" or tag == "a"):
                self.refs.append((key, attrs[key]))
        for key in ("srcset", "data-srcset"):
            if attrs.get(key):
                for part in attrs[key].split(","):
                    words = part.strip().split()
                    if words:
                        self.refs.append((key, words[0]))


def normalize_name(name):
    stem = Path(unquote(name)).stem.lower()
    return re.sub(r"-(?:\d+x\d+|scaled)$", "", stem)


def git_file_index(root):
    """Get tracked media paths without checking out gigabytes of image blobs.

    This supports actions/checkout with --filter=blob:none and sparse checkout.
    In a non-git export, return None and inspect the filesystem instead.
    """
    try:
        p = subprocess.run(
            ["git", "-C", str(root), "ls-tree", "-r", "--name-only",
             "HEAD", "--", "content/articles", "content/shared-media"],
            check=True, text=True, capture_output=True,
        )
        return set(p.stdout.splitlines())
    except (OSError, subprocess.CalledProcessError):
        return None


def audit(repo):
    root = repo.resolve()
    content = root / "content"
    git_files = git_file_index(root)
    articles = content / "articles"
    if not articles.is_dir():
        raise ValueError(f"Missing article directory: {articles}")
    rows = []
    examined = 0
    for folder in sorted(articles.iterdir()):
        metadata_file = folder / "article.json"
        if not metadata_file.is_file():
            continue
        examined += 1
        metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
        links = []
        for filename in ("body.html", "body.md"):
            file = folder / filename
            if not file.is_file():
                continue
            body = file.read_text(encoding="utf-8")
            parser = AssetLinks()
            parser.feed(body)
            links.extend((filename, attr, url) for attr, url in parser.refs)
            if filename.endswith(".md"):
                links.extend((filename, "markdown", m.group(1))
                             for m in re.finditer(r"!?\[[^\]]*\]\(([^)\s]+)", body))
        if metadata.get("banner"):
            links.append(("article.json", "banner", metadata["banner"]))
        available = {}
        media_dir = folder / "media"
        if git_files is not None:
            prefix = f"content/articles/{folder.name}/media/"
            for path in git_files:
                if path.startswith(prefix):
                    available.setdefault(normalize_name(Path(path).name), []).append(path)
        elif media_dir.is_dir():
            for file in media_dir.rglob("*"):
                if file.is_file():
                    available.setdefault(normalize_name(file.name), []).append(
                        file.relative_to(root).as_posix())
        seen = set()
        for filename, attr, url in links:
            url = url.strip()
            if not url or url.startswith(("#", "javascript:", "data:")):
                continue
            parsed = urlparse(url)
            host = (parsed.hostname or "").lower()
            path = unquote(parsed.path)
            classification, target = "", None
            if host in ("imgur.com", "www.imgur.com", "i.imgur.com", "m.imgur.com"):
                classification = "external_imgur_review"
            elif path.startswith(("/assets/media/", "/wp-content/uploads/")):
                classification = "legacy_media_url_review"
            elif not parsed.scheme and not parsed.netloc and path.startswith("media/"):
                target = folder / path
            elif not parsed.scheme and not parsed.netloc and path.startswith("shared-media/"):
                target = content / path
            if target is not None:
                resolved = target.resolve()
                if not resolved.is_relative_to(content):
                    classification = "unsafe_local_path"
                elif (resolved.relative_to(root).as_posix() not in git_files
                      if git_files is not None else not resolved.is_file()):
                    classification = "missing_local_file"
            if not classification:
                continue
            key = (filename, attr, url, classification)
            if key in seen:
                continue
            seen.add(key)
            possible = sorted(available.get(normalize_name(Path(path).name), []))[:3]
            original = ""
            if path.startswith(("/assets/media/", "/wp-content/uploads/")):
                original = "https://canonn.science" + quote(path, safe="/")
            name = Path(path).name
            rows.append({
                "slug": folder.name, "title": metadata.get("title", folder.name),
                "section": metadata.get("section", ""),
                "source_file": filename, "attribute": attr, "url": url,
                "classification": classification,
                "possible_local_variant": " | ".join(possible),
                "archive_target": original, "wayback_status": "not_checked",
                "wayback_snapshot": "",
                "search_url": "https://www.google.com/search?" + urlencode({
                    "q": f'"{name}" "Elite Dangerous"'}) if name else "",
            })
    order = {"missing_local_file": 0, "unsafe_local_path": 0,
             "legacy_media_url_review": 1, "external_imgur_review": 2}
    rows.sort(key=lambda r: (order[r["classification"]], r["slug"],
                             r["url"], r["source_file"]))
    return examined, rows


def wayback(rows, limit, delay):
    checked, probes = {}, 0
    for row in rows:
        target = row["archive_target"]
        if not target:
            continue
        if target in checked:
            status, snapshot = checked[target]
        elif probes < limit:
            if probes:
                time.sleep(delay)
            probes += 1
            url = "https://archive.org/wayback/available?" + urlencode({"url": target})
            try:
                req = Request(url, headers={"User-Agent":
                    "IGAU-Canonn-archive-audit/1.0 (read-only research)"})
                with urlopen(req, timeout=15) as response:
                    data = json.loads(response.read(200000))
                nearest = data.get("archived_snapshots", {}).get("closest", {})
                if nearest.get("available") and str(nearest.get("status")) == "200":
                    status, snapshot = "unverified_snapshot_lead", nearest.get("url", "")
                else:
                    status, snapshot = "no_snapshot_reported_by_api", ""
            except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
                status, snapshot = "probe_error:" + type(exc).__name__, ""
            checked[target] = status, snapshot
        else:
            continue
        row["wayback_status"], row["wayback_snapshot"] = status, snapshot
    return probes


def save(out, count, rows, probes):
    out.mkdir(parents=True, exist_ok=True)
    with (out / "candidates.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    groups = dict(sorted(Counter(r["classification"] for r in rows).items()))
    affected = Counter(r["slug"] for r in rows)
    summary = {"articles_scanned": count, "findings": len(rows),
               "affected_articles": len(affected), "by_classification": groups,
               "wayback_targets_probed": probes,
               "unverified_wayback_leads": sum(
                   r["wayback_status"] == "unverified_snapshot_lead" for r in rows)}
    (out / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = ["# Canonn recovery audit", "",
             "This is a read-only inventory, not a list of confirmed HTTP 404s.",
             "Legacy URLs can redirect; filename variants and archive snapshots",
             "must be visually verified before publication.", "",
             f"Articles scanned: {count}. Findings: {len(rows)} across {len(affected)} articles.",
             f"Wayback targets probed: {probes}.", "",
             "| Classification | References |", "|---|---:|"]
    lines += [f"| {k} | {v} |" for k, v in groups.items()]
    lines += ["", "## Highest-count articles", "",
              "| Slug | Findings |", "|---|---:|"]
    lines += [f"| {slug} | {n} |" for slug, n in
              sorted(affected.items(), key=lambda item: (-item[1], item[0]))[:30]]
    lines += ["", "Full paths, source links, and archive leads are in candidates.csv.", ""]
    (out / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--out", type=Path, default=Path("recovery-results"))
    parser.add_argument("--wayback-limit", type=int, default=0)
    parser.add_argument("--delay", type=float, default=4)
    args = parser.parse_args()
    if args.wayback_limit < 0 or args.delay < 3:
        parser.error("wayback-limit must be >= 0 and delay at least 3 seconds")
    count, rows = audit(args.repo)
    probes = wayback(rows, args.wayback_limit, args.delay) if args.wayback_limit else 0
    print(json.dumps(save(args.out, count, rows, probes), indent=2))


if __name__ == "__main__":
    main()
