# IGAU recovery research (fork only)

This directory contains **read-only discovery tooling** maintained by the Intergalactic Astronomical Union. It is not intended for an upstream PR to Canonn. Recovered content may eventually be proposed through the normal Canonn process, **one verified article at a time**.

## What runs

- `audit.py` reads `content/articles/<slug>/{article.json,body.html,body.md}`.
- It identifies **missing repository files**, **legacy media URLs that need checking**, and **external Imgur references requiring review**.
- Git-tracked file paths are used as the authoritative existence index. GitHub Actions can therefore use a sparse checkout and avoid downloading all media blobs.
- It produces `candidates.csv`, `summary.json`, and `summary.md` as an Actions artifact.
- Optional Wayback availability lookups are **leads**, not proof the archived file is the correct asset.
- The scheduled workflow runs offline. Manually dispatched runs may perform a small number of rate-limited Wayback lookups.
- No issue, PR, article change, commit, or image replacement is automatically generated.

## Run locally

```sh
python3 -m unittest discover -s igau-recovery/tests -v
python3 igau-recovery/audit.py --repo . --out recovery-results
# Optional: at most 12 Wayback availability requests, >=4 seconds apart
python3 igau-recovery/audit.py --repo . --out recovery-results --wayback-limit 12 --delay 4
```

The workflow's run summary shows aggregate counts; download its `canonn-recovery-inventory` artifact for individual URLs. Output is deliberately **not committed** to Canonn's source tree.

## Strict acceptance gate before suggesting any upstream change

1. **Confirm the defect still exists** in the latest upstream `main` version, not merely in an old migration report.
2. **Locate the exact original or an approved equivalent**. Record the original article URL, asset URL, Wayback timestamp if applicable, and provenance/attribution; check reuse rights. Never invent an image or swap a similar-looking screenshot.
3. **Validate the media**: real image/audio file, content type, dimensions or duration, correct article/caption, and a working local link after rebuilding. Check whether a higher-quality version already exists elsewhere in the repo.
4. **Keep the upstream patch minimal**: one article (or a genuinely coherent small group), only files under its `content/articles/<slug>/` directory. Do not add the audit workflow or tooling upstream.
5. **Run their checks**: `npm run content:check` and `npm run content:guard -- --slug <slug>`. Review any guard warnings and get maintainer approval.
6. **Prepare a provenance-backed commit** with exact before/after and only confirmed files. A separate commit per independent fix lets Canonn cherry-pick or reject it.
7. **Human review before any upstream PR**. Aim for **1–3 independently validated fixes** per PR. Never automatically open issues or PRs from a scanner report.

## Starting research queue (unverified, not a change request)

- `guardian-structure`: 15 legacy references to monolith-bank/pylon diagrams in the article. Compare with Canonn's own historically credited Guardian layout galleries before choosing any replacement.
- `generation-ship-odysseus`: five legacy OGG audio URLs. Locate authentic source recordings before considering edits.
- `voyager-2`: existing Canonn issue [#49](https://github.com/canonn-science/canonn.science/issues/49) reports inaccessible external Imgur album; coordinate with that issue rather than duplicating it.

These are **candidates**, not verified recoveries. In particular, a URL at `/assets/media/...` is not necessarily HTTP 404 until tested.

## Scoping and upstream separation

Run the tooling only in the IGAU fork. An upstream PR should contain **only recovered article folders and their media**, no new scheduled jobs or repository-wide source changes. A fork-internal PR for this tool is appropriate. Do not merge it upstream.

Sources: [Canonn README](https://github.com/canonn-science/canonn.science/blob/main/README.md), [content authoring guide](https://github.com/canonn-science/canonn.science/blob/main/docs/ADDING-ARTICLES.md), [existing migration audit](https://github.com/canonn-science/canonn.science/blob/main/tools/migration-report.json).
