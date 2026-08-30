#!/usr/bin/env python3
"""Report stale knowledge metadata and broken official evidence sources."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
MAX_AGE_DAYS = {"versioned": 365, "time-sensitive": 180}


def source_status(url: str, timeout: int) -> tuple[bool | None, str]:
    request = Request(url, headers={"User-Agent": "evm-audit-skills-knowledge-health/1"}, method="HEAD")
    try:
        with urlopen(request, timeout=timeout) as response:
            return 200 <= response.status < 400, f"HTTP {response.status}"
    except HTTPError as error:
        if error.code in {403, 405}:
            request = Request(url, headers={"User-Agent": "evm-audit-skills-knowledge-health/1"})
            try:
                with urlopen(request, timeout=timeout) as response:
                    return 200 <= response.status < 400, f"HTTP {response.status}"
            except (HTTPError, URLError, TimeoutError, OSError) as retry_error:
                if "CERTIFICATE_VERIFY_FAILED" in str(retry_error) or "certificate verify failed" in str(retry_error).lower():
                    return None, "TLS certificate verification unavailable in this runner"
                if isinstance(retry_error, HTTPError):
                    if retry_error.code in {404, 410}:
                        return False, f"HTTP {retry_error.code}"
                    return None, f"transient HTTP {retry_error.code}"
                if isinstance(retry_error, (URLError, TimeoutError, OSError)):
                    return None, f"network check unavailable: {retry_error}"
                return False, str(retry_error)
        if error.code in {404, 410}:
            return False, f"HTTP {error.code}"
        if error.code == 429 or 500 <= error.code < 600:
            return None, f"transient HTTP {error.code}"
        return None, f"unclassified HTTP {error.code}"
    except (URLError, TimeoutError, OSError) as error:
        return None, f"network check unavailable: {error}"


def knowledge_health(
    root: Path,
    *,
    today: date,
    check_links: bool,
    timeout: int,
) -> dict[str, Any]:
    registry = json.loads((root / "data" / "canonical-checks.json").read_text(encoding="utf-8"))
    findings: list[dict[str, Any]] = []
    skipped_sources: list[dict[str, str]] = []
    for check in registry.get("checks", []):
        freshness = check.get("freshness")
        if freshness not in MAX_AGE_DAYS:
            continue
        verified_at = check.get("verified_at")
        if not verified_at:
            findings.append(
                {
                    "kind": "unverified-freshness",
                    "severity": "error" if freshness == "time-sensitive" else "advisory",
                    "canonical_id": check.get("canonical_id"),
                    "message": f"{freshness} knowledge has no verified_at date",
                }
            )
            continue
        try:
            age = (today - date.fromisoformat(verified_at)).days
        except (TypeError, ValueError):
            findings.append(
                {
                    "kind": "invalid-freshness-date",
                    "severity": "error",
                    "canonical_id": check.get("canonical_id"),
                    "message": f"invalid verified_at={verified_at!r}",
                }
            )
            continue
        if age > MAX_AGE_DAYS[freshness]:
            findings.append(
                {
                    "kind": "stale-knowledge",
                    "severity": "error",
                    "canonical_id": check.get("canonical_id"),
                    "message": f"verified {age} days ago; limit is {MAX_AGE_DAYS[freshness]}",
                }
            )

    checked_urls = 0
    if check_links:
        for source_key, source in sorted(registry.get("source_catalog", {}).items()):
            if source.get("kind") != "official":
                continue
            checked_urls += 1
            ok, detail = source_status(str(source.get("url", "")), timeout)
            if ok is False:
                findings.append(
                    {
                        "kind": "broken-official-source",
                        "severity": "error",
                        "source_key": source_key,
                        "url": source.get("url"),
                        "message": detail,
                    }
                )
            elif ok is None:
                skipped_sources.append({"source_key": source_key, "url": str(source.get("url", "")), "message": detail})

    error_count = sum(finding["severity"] == "error" for finding in findings)
    return {
        "schema_version": 1,
        "checked_at": today.isoformat(),
        "registry_schema_version": registry.get("schema_version"),
        "canonical_checks": len(registry.get("checks", [])),
        "official_urls_checked": checked_urls,
        "official_urls_skipped": skipped_sources,
        "finding_count": len(findings),
        "error_count": error_count,
        "advisory_count": len(findings) - error_count,
        "findings": findings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--today", type=date.fromisoformat, default=date.today(), help="ISO date for deterministic testing")
    parser.add_argument("--check-links", action="store_true")
    parser.add_argument("--timeout", type=int, default=15)
    parser.add_argument("--output-json", type=Path)
    args = parser.parse_args(argv)

    try:
        report = knowledge_health(
            args.root.resolve(),
            today=args.today,
            check_links=args.check_links,
            timeout=args.timeout,
        )
        rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        if args.output_json:
            args.output_json.write_text(rendered, encoding="utf-8")
        for finding in report["findings"]:
            subject = finding.get("canonical_id") or finding.get("source_key")
            print(f"{finding['severity']}\t{finding['kind']}\t{subject}\t{finding['message']}")
        print(
            f"canonical_checks={report['canonical_checks']} official_urls_checked={report['official_urls_checked']} "
            f"official_urls_skipped={len(report['official_urls_skipped'])} errors={report['error_count']} advisories={report['advisory_count']}"
        )
        return 1 if report["error_count"] else 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
