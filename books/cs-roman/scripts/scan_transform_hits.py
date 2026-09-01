#!/usr/bin/env python3
"""Show where a token or catalog rule hits CS Roman volumes (stdout).

  python books/cs-roman/scripts/scan_transform_hits.py --match dighamaddhānaṃ
  python books/cs-roman/scripts/scan_transform_hits.py --rule-id roman-dighamaddhana-long-i
  python books/cs-roman/scripts/scan_transform_hits.py --catalog
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from paths import OUTPUT_DIR, VOLUMES_DIR, ensure_import_paths

ensure_import_paths()

from cs_roman_text import roman_value_from_text_field  # noqa: E402
from cs_roman_transforms import (  # noqa: E402
    TransformRule,
    iter_match_hits,
    load_shared_transforms,
    rule_matches,
)


@dataclass(frozen=True)
class SurfaceHit:
    volume: str
    page: int
    order: int
    segment_type: str
    start: int
    matched: str
    snippet: str
    applying: tuple[str, ...]


def iter_roman_blobs(seg: dict[str, Any]) -> Iterator[str]:
    """Yield Roman surfaces the catalog may change (body, hanging, gāthā).

    Edition ``notes`` / ``symbol_notes`` are out of scope for
    ``transforms.json`` and are not scanned.
    """
    body = roman_value_from_text_field(seg.get("text"))
    if body:
        yield body
    for line in seg.get("hanging_lines") or []:
        hanging = roman_value_from_text_field(line)
        if hanging:
            yield hanging
    for bat in seg.get("bats") or []:
        if not isinstance(bat, dict):
            continue
        for wak in bat.get("waks") or []:
            if not isinstance(wak, dict):
                continue
            wak_text = roman_value_from_text_field(wak.get("text"))
            if wak_text:
                yield wak_text


def snippet_around(text: str, start: int, length: int, *, radius: int = 36) -> str:
    a = max(0, start - radius)
    b = min(len(text), start + length + radius)
    prefix = "…" if a else ""
    suffix = "…" if b < len(text) else ""
    return prefix + text[a:b].replace("\n", " ") + suffix


def applying_rule_ids(
    text: str,
    *,
    page: int,
    order: int,
    segment_type: str,
    volume_id: str,
    rules: Sequence[TransformRule],
) -> tuple[str, ...]:
    ids: list[str] = []
    for rule in rules:
        if rule_matches(
            rule,
            text,
            page=page,
            order=order,
            segment_type=segment_type,
            volume_id=volume_id,
        ):
            ids.append(rule.id)
    return tuple(ids)


def hits_in_segment(
    seg: dict[str, Any],
    *,
    volume_id: str,
    needle: str,
    substring: bool,
    rules: Sequence[TransformRule],
) -> Iterator[SurfaceHit]:
    page = int(seg.get("page") or 0)
    order = int(seg.get("order") or 0)
    segment_type = str(seg.get("segment_type") or "prose")
    seen: set[tuple[int, int]] = set()
    for blob in iter_roman_blobs(seg):
        for start, length in iter_match_hits(blob, needle, substring=substring):
            key = (id(blob), start)
            if key in seen:
                continue
            seen.add(key)
            yield SurfaceHit(
                volume=volume_id,
                page=page,
                order=order,
                segment_type=segment_type,
                start=start,
                matched=blob[start : start + length],
                snippet=snippet_around(blob, start, length),
                applying=applying_rule_ids(
                    blob,
                    page=page,
                    order=order,
                    segment_type=segment_type,
                    volume_id=volume_id,
                    rules=rules,
                ),
            )


def volume_segment_paths(*, volume: str | None) -> list[tuple[str, Path]]:
    """Prefer git copies under volumes/; skip names starting with _."""
    out: list[tuple[str, Path]] = []
    if volume:
        vol_path = VOLUMES_DIR / volume / "data" / "segments.json"
        if vol_path.is_file():
            return [(volume, vol_path)]
        alt = OUTPUT_DIR / f"{volume}.segments.json"
        if alt.is_file():
            return [(volume, alt)]
        return []
    if VOLUMES_DIR.is_dir():
        for p in sorted(VOLUMES_DIR.iterdir()):
            if p.name.startswith("_"):
                continue
            seg = p / "data" / "segments.json"
            if seg.is_file():
                out.append((p.name, seg))
    if out:
        return out
    if OUTPUT_DIR.is_dir():
        for seg in sorted(OUTPUT_DIR.glob("*.segments.json")):
            stem = seg.name[: -len(".segments.json")]
            if stem.startswith("_"):
                continue
            out.append((stem, seg))
    return out


def load_segments(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    segs = data.get("segments") or []
    return [s for s in segs if isinstance(s, dict)]


def collect_hits(
    *,
    needle: str,
    substring: bool,
    rules: Sequence[TransformRule],
    volume: str | None,
) -> list[SurfaceHit]:
    hits: list[SurfaceHit] = []
    for volume_id, path in volume_segment_paths(volume=volume):
        for seg in load_segments(path):
            hits.extend(
                hits_in_segment(
                    seg,
                    volume_id=volume_id,
                    needle=needle,
                    substring=substring,
                    rules=rules,
                )
            )
    return hits


def format_hit(hit: SurfaceHit) -> str:
    rules = ",".join(hit.applying) if hit.applying else "-"
    return (
        f"{hit.volume}\tp={hit.page}\to={hit.order}\t{hit.segment_type}\t"
        f"{hit.matched}\trules={rules}\n"
        f"  {hit.snippet}"
    )


def print_hits(hits: Sequence[SurfaceHit], *, limit: int) -> None:
    shown = hits[:limit]
    for hit in shown:
        print(format_hit(hit))
    print(f"hits={len(hits)} shown={len(shown)}")
    volumes = sorted({h.volume for h in hits})
    print(f"volumes={len(volumes)} {','.join(volumes)}")


def print_catalog(rules: Sequence[TransformRule], *, volume: str | None) -> None:
    print("id\taction\tmatch\thits\tvolumes")
    for rule in rules:
        if not rule.enabled:
            continue
        hits = collect_hits(
            needle=rule.match,
            substring=False,
            rules=[rule],
            volume=volume,
        )
        applying = [h for h in hits if rule.id in h.applying]
        vols = sorted({h.volume for h in applying})
        print(
            f"{rule.id}\t{rule.action}\t{rule.match}\t"
            f"{len(applying)}\t{len(vols)}"
        )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument(
        "--match",
        help="Surface pattern (exact word, or +affix like +bandhiṃ)",
    )
    g.add_argument("--rule-id", help="Catalog rule id in shared/transforms.json")
    g.add_argument(
        "--catalog",
        action="store_true",
        help="One summary line per enabled catalog rule",
    )
    ap.add_argument("--volume", help="Folder id (e.g. 01Vin01)")
    ap.add_argument(
        "--limit",
        type=int,
        default=80,
        help="Max hit lines to print (default 80)",
    )
    ap.add_argument(
        "--substring",
        action="store_true",
        help="With --match: raw substring; do not parse + or require word bounds",
    )
    args = ap.parse_args(argv)

    try:
        rules = load_shared_transforms()
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 2

    if args.catalog:
        print_catalog(rules, volume=args.volume)
        return 0

    if args.rule_id:
        rule = next((r for r in rules if r.id == args.rule_id), None)
        if rule is None:
            print(f"unknown rule id: {args.rule_id}", file=sys.stderr)
            return 2
        hits = collect_hits(
            needle=rule.match,
            substring=False,
            rules=[rule],
            volume=args.volume,
        )
        applying = [h for h in hits if rule.id in h.applying]
        skipped = len(hits) - len(applying)
        print_hits(applying, limit=max(0, args.limit))
        if skipped:
            print(f"surface_not_applied={skipped} (loci/type filter)")
        return 0

    try:
        hits = collect_hits(
            needle=args.match,
            substring=args.substring,
            rules=rules,
            volume=args.volume,
        )
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2
    print_hits(hits, limit=max(0, args.limit))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
