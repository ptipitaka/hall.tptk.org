"""
Enrich cs-roman segment JSON: ``text`` string → multi-script list.

  [{ "script": "roman", "value": "..." }, { "script": "thai", "value": "..." }]

Bold ``runs`` are preserved across ``--force`` / spacing normalize when spans
can be remapped. If bold cannot be remapped, enrich warns (does not invent
bold). Restoring lost bold requires re-extract from the CS Roman PDF.

Example:
  docker compose exec -T web python books/cs-roman/scripts/enrich_cs_roman_thai.py
  docker compose exec -T web python books/cs-roman/scripts/enrich_cs_roman_thai.py \\
      books/cs-roman/output/01Vin01.segments.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from paths import OUTPUT_DIR, ensure_import_paths

ensure_import_paths()
from cs_roman_segments import save as save_segments  # noqa: E402
from cs_roman_text import (  # noqa: E402
    SECTION_RULE_FLAG,
    ensure_script_text,
    needs_solid_midword_hyphen_strip,
    needs_spacing_normalize,
    uses_sentence_spacer,
)

DEFAULT_DIR = OUTPUT_DIR


def enrich_document(data: dict, *, force: bool = False) -> tuple[dict, int, int]:
    """Return (updated doc, segments converted, bold_lost count)."""
    data = dict(data)
    converted = 0
    bold_lost = 0
    segments = []
    for seg in data.get("segments") or []:
        seg = dict(seg)
        before = seg.get("text")
        already = (
            isinstance(before, list)
            and any(isinstance(e, dict) and e.get("script") == "thai" for e in before)
        )
        normalize_spacing = uses_sentence_spacer(
            str(seg.get("segment_type") or "")
        )
        had_rule = False
        if before is not None:
            entries, text_rule, lost = ensure_script_text(
                before, force=force, normalize_spacing=normalize_spacing
            )
            had_rule = had_rule or text_rule
            if lost:
                bold_lost += 1
            seg["text"] = entries
            if force or not already or text_rule:
                converted += 1
        hanging = seg.get("hanging_lines")
        if isinstance(hanging, list) and hanging:
            hl_out: list = []
            for hl in hanging:
                hl_entries, hl_rule, hl_lost = ensure_script_text(
                    hl, force=force, normalize_spacing=normalize_spacing
                )
                had_rule = had_rule or hl_rule
                if hl_lost:
                    bold_lost += 1
                hl_out.append(hl_entries)
            seg["hanging_lines"] = hl_out
        bats = seg.get("bats")
        if isinstance(bats, list) and bats:
            bats_out: list = []
            for bat in bats:
                if not isinstance(bat, dict):
                    bats_out.append(bat)
                    continue
                bat = dict(bat)
                waks_out: list = []
                for wak in bat.get("waks") or []:
                    if not isinstance(wak, dict):
                        waks_out.append(wak)
                        continue
                    wak = dict(wak)
                    wak_text = wak.get("text")
                    if wak_text is None:
                        waks_out.append(wak)
                        continue
                    wak_entries, wak_rule, wak_lost = ensure_script_text(
                        wak_text,
                        force=force,
                        normalize_spacing=normalize_spacing,
                    )
                    had_rule = had_rule or wak_rule
                    if wak_lost:
                        bold_lost += 1
                    wak["text"] = wak_entries
                    waks_out.append(wak)
                bat["waks"] = waks_out
                bats_out.append(bat)
            seg["bats"] = bats_out
        # Preserve an existing section_rule flag: after extract/serialize the
        # trailing ``_____`` is already stripped into the flag, so a later
        # enrich/--force pass would otherwise clear it (had_rule=False).
        had_flag = SECTION_RULE_FLAG in (seg.get("flags") or [])
        flags = [f for f in (seg.get("flags") or []) if f != SECTION_RULE_FLAG]
        if had_rule or had_flag:
            flags.append(SECTION_RULE_FLAG)
        seg["flags"] = flags
        if before is None and (force or had_rule):
            converted += 1
        segments.append(seg)
    data["segments"] = segments
    return data, converted, bold_lost


def enrich_file(path: Path, *, force: bool = False) -> tuple[int, int, int]:
    """Return (converted, total, bold_lost)."""
    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    segs = data.get("segments") or []
    already = bool(
        segs
        and isinstance(segs[0].get("text"), list)
        and any(
            isinstance(e, dict) and e.get("script") == "thai"
            for e in segs[0]["text"]
        )
    )
    # Still rewrite when spacing or solid mid-word hyphens need normalize.
    needs_normalize = needs_spacing_normalize(raw) or needs_solid_midword_hyphen_strip(
        raw
    )
    if not force and already and not needs_normalize:
        return 0, len(segs), 0

    data, converted, bold_lost = enrich_document(
        data, force=force or needs_normalize
    )
    save_segments(path, data, normalize=True)
    return converted, len(data["segments"]), bold_lost


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="JSON file(s) or directory (default: books/cs-roman/output)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Re-transliterate even if thai entries already exist "
            "(preserves bold runs when remappable; warn if lost)"
        ),
    )
    args = parser.parse_args(argv)

    targets: list[Path] = []
    paths = args.paths or [DEFAULT_DIR]
    for p in paths:
        if p.is_dir():
            targets.extend(sorted(p.glob("*.segments.json")))
        elif p.is_file():
            targets.append(p)
        else:
            print(f"Skip missing: {p}", file=sys.stderr)

    if not targets:
        print("No segment JSON files found.", file=sys.stderr)
        return 1

    for path in targets:
        converted, total, bold_lost = enrich_file(path, force=args.force)
        print(f"{path.name}: {converted}/{total} segments -> multi-script text")
        if bold_lost:
            print(
                f"WARNING: {path.name}: bold runs lost on {bold_lost} text field(s); "
                "re-extract from PDF to restore",
                file=sys.stderr,
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
