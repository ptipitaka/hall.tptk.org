#!/usr/bin/env python3
"""Run CS Roman fixups from ``fixup_manifest.json``.

Canonical registry: ``books/cs-roman/scripts/fixup_manifest.json``.
Process doc: ``books/cs-roman/docs/fixup_process.md``.

  python books/cs-roman/scripts/run_cs_roman_fixups.py --pipeline
  python books/cs-roman/scripts/run_cs_roman_fixups.py --pipeline --volume 13Sam02
  python books/cs-roman/scripts/run_cs_roman_fixups.py --id tassuddana_labels --all
  python books/cs-roman/scripts/run_cs_roman_fixups.py --pipeline --dry-run
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from typing import Any

from paths import REPO, ensure_import_paths
from fixup_manifest_lib import (  # noqa: E402
    list_volume_ids,
    load_manifest,
    pipeline_fixups,
    script_argv,
)

ensure_import_paths()


def _run(argv: list[str], *, dry_run: bool) -> int:
    print(f"+ python {' '.join(argv)}" + ("  [dry-run]" if dry_run else ""))
    proc = subprocess.run(
        [sys.executable, *argv],
        cwd=str(REPO),
        check=False,
    )
    return int(proc.returncode)


def _expand_entries(
    entries: list[dict[str, Any]],
    *,
    volume: str | None,
) -> list[tuple[dict[str, Any], str | None]]:
    """Expand per_volume entries into one job per volume when --all."""
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
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument(
        "--pipeline",
        action="store_true",
        help="Run all fixups with pipeline=true (manifest order)",
    )
    g.add_argument("--id", help="Run a single fixup id from the manifest")
    ap.add_argument("--volume", help="Limit to one volume id")
    ap.add_argument(
        "--all",
        action="store_true",
        help="With --id: run corpus-wide (--all / every volume)",
    )
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    if args.id and not (args.volume or args.all):
        ap.error("--id requires --volume or --all")
    if args.pipeline and args.all:
        # --pipeline already means corpus unless --volume is set
        pass

    manifest = load_manifest()
    if args.pipeline:
        entries = pipeline_fixups(manifest)
    else:
        entries = [f for f in manifest["fixups"] if f.get("id") == args.id]
        if not entries:
            print(f"Unknown fixup id: {args.id}", file=sys.stderr)
            return 1

    volume = args.volume
    jobs = _expand_entries(entries, volume=volume)
    failures = 0
    for entry, vol in jobs:
        try:
            cmd = script_argv(entry, volume=vol, dry_run=args.dry_run)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            failures += 1
            continue
        rc = _run(cmd, dry_run=args.dry_run)
        if rc != 0:
            print(f"FAIL {entry['id']} (exit {rc})", file=sys.stderr)
            failures += 1
    if failures:
        print(f"Done with {failures} failure(s)", file=sys.stderr)
        return 1
    print(f"Done: {len(jobs)} fixup job(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
