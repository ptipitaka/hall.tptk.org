#!/usr/bin/env python3
"""Audit fixup residuals from ``fixup_manifest.json`` (dry-run gate).

  python books/cs-roman/scripts/scan_fixup_residuals.py
  python books/cs-roman/scripts/scan_fixup_residuals.py --strict
  python books/cs-roman/scripts/scan_fixup_residuals.py --strict --volume 13Sam02
  python books/cs-roman/scripts/scan_fixup_residuals.py --include-warn

Exit 1 under ``--strict`` when any ``gate: strict`` fixup still has residual > 0
or when residual count cannot be parsed.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from typing import Any

from paths import REPO, ensure_import_paths
from fixup_manifest_lib import (  # noqa: E402
    gated_fixups,
    list_volume_ids,
    load_manifest,
    parse_residual_count,
    script_argv,
)

ensure_import_paths()


def _capture(argv: list[str]) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, *argv],
        cwd=str(REPO),
        check=False,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    return int(proc.returncode), out


def _jobs(
    entries: list[dict[str, Any]], *, volume: str | None
) -> list[tuple[dict[str, Any], str | None]]:
    jobs: list[tuple[dict[str, Any], str | None]] = []
    for entry in entries:
        scope = str(entry.get("scope") or "all")
        if scope == "per_volume" and not volume:
            for vid in list_volume_ids():
                jobs.append((entry, vid))
        else:
            jobs.append((entry, volume))
    return jobs


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--volume", help="Limit to one volume id")
    ap.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 if any strict-gated residual > 0 (or unparsable)",
    )
    ap.add_argument(
        "--include-warn",
        action="store_true",
        help="Also dry-run gate=warn entries (report only; never fail alone)",
    )
    ap.add_argument(
        "--id",
        action="append",
        default=[],
        help="Limit to fixup id (repeatable)",
    )
    args = ap.parse_args(argv)

    manifest = load_manifest()
    levels = {"strict"}
    if args.include_warn:
        levels.add("warn")
    entries = gated_fixups(manifest, levels=levels)
    if args.id:
        want = set(args.id)
        entries = [e for e in entries if e.get("id") in want]
        missing = want - {e.get("id") for e in entries}
        if missing:
            print(f"Unknown or ungated id(s): {sorted(missing)}", file=sys.stderr)
            return 1

    # Skip PDF-heavy warn entries unless explicitly included via --id —
    # full --include-warn on glued_running_headers / page_start is slow.
    if args.include_warn and not args.id:
        entries = [
            e
            for e in entries
            if str(e.get("gate")) == "strict"
            or not e.get("requires_pdf")
        ]

    rows: list[tuple[str, str | None, int | None, str]] = []
    for entry, vol in _jobs(entries, volume=args.volume):
        cmd = script_argv(entry, volume=vol, dry_run=True)
        rc, out = _capture(cmd)
        count = parse_residual_count(out)
        status = "ok"
        if rc != 0:
            status = f"exit:{rc}"
        elif count is None:
            status = "unparsed"
        elif count > 0:
            status = f"residual:{count}"
        label = entry["id"] if vol is None else f"{entry['id']}@{vol}"
        print(f"{label}: {status}")
        rows.append((str(entry["id"]), vol, count, status))

    strict_fail = 0
    warn_n = 0
    by_id = {e["id"]: e for e in entries}
    for fid, _vol, count, status in rows:
        gate = str(by_id[fid].get("gate") or "off")
        if gate != "strict":
            if count and count > 0:
                warn_n += 1
            continue
        if status.startswith("exit:") or status == "unparsed":
            strict_fail += 1
        elif count is not None and count > 0:
            strict_fail += 1

    print(
        f"Summary: {len(rows)} job(s); "
        f"strict_failures={strict_fail}; warn_residuals={warn_n}"
    )
    if args.strict and strict_fail:
        print(
            "Strict gate failed — run: "
            "python books/cs-roman/scripts/run_cs_roman_fixups.py --pipeline",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
