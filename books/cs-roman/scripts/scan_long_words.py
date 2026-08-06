"""Scan cs-roman volumes for long Roman tokens; emit Thai list via pali_script."""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path

from paths import BOOKS, VOLUMES_DIR, ensure_import_paths

ensure_import_paths()

from pali_script import Script, convert  # noqa: E402

ROOT = BOOKS
RESEARCH = BOOKS / "research"
VOLUMES = VOLUMES_DIR

MARKER_RE = re.compile(r"\{\{(?:n\d+|\*|sp1|sp3|\+)\}\}")
# Letters (incl. Pāli diacritics) with optional internal hyphens from PDF wraps.
TOKEN_RE = re.compile(r"[^\W\d_]+(?:-[^\W\d_]+)*", re.UNICODE)


def roman_letter_len(word: str) -> int:
    return len(word.replace("-", ""))


def thai_display_len(word: str) -> int:
    """Count Thai glyphs that take horizontal space.

    Skips nonspacing marks (Mn): above/below vowels such as ิ ี ุ ู,
    plus ฺ / ํ and other stacked marks. Also skips PDF-wrap ``-``.
    Spacing letters (พยัญชนะ, สระหน้า เแโใไ, า, อ, …) are counted.
    """
    n = 0
    for ch in word:
        if ch == "-":
            continue
        if unicodedata.category(ch) == "Mn":
            continue
        n += 1
    return n


def roman_to_thai(word: str) -> str:
    """Transliterate Roman token to Thai; keep literal ``-`` from PDF wraps."""
    pieces: list[str] = []
    buf: list[str] = []
    for ch in word:
        if ch == "-":
            if buf:
                pieces.append(convert("".join(buf), Script.ROMAN, Script.THAI))
                buf = []
            pieces.append("-")
        else:
            buf.append(ch)
    if buf:
        pieces.append(convert("".join(buf), Script.ROMAN, Script.THAI))
    return "".join(pieces)


def roman_strings(seg: dict) -> list[str]:
    out: list[str] = []
    for item in seg.get("text") or []:
        if isinstance(item, dict) and item.get("script") == "roman":
            val = item.get("value")
            if isinstance(val, str) and val:
                out.append(val)
    for note in seg.get("notes") or []:
        if isinstance(note, str) and note:
            out.append(note)
        elif isinstance(note, dict):
            val = note.get("value")
            if isinstance(val, str) and val:
                out.append(val)
    for _sym, body in (seg.get("symbol_notes") or {}).items():
        if isinstance(body, str) and body:
            out.append(body)
    for line in seg.get("hanging_lines") or []:
        if isinstance(line, str) and line:
            out.append(line)
        elif isinstance(line, dict):
            val = line.get("value")
            if isinstance(val, str) and val:
                out.append(val)
    for bat in seg.get("bats") or []:
        if isinstance(bat, str) and bat:
            out.append(bat)
        elif isinstance(bat, dict):
            for wak in bat.get("waks") or bat.get("lines") or []:
                if isinstance(wak, str) and wak:
                    out.append(wak)
                elif isinstance(wak, dict):
                    val = wak.get("value")
                    if isinstance(val, str) and val:
                        out.append(val)
    return out


def scan_roman_words(min_len: int) -> set[str]:
    """Unique Roman tokens with letter length ``>= min_len`` (candidate pool)."""
    words: set[str] = set()
    for seg_path in sorted(VOLUMES.glob("*/data/segments.json")):
        data = json.loads(seg_path.read_text(encoding="utf-8"))
        for seg in data.get("segments") or []:
            for raw in roman_strings(seg):
                cleaned = MARKER_RE.sub(" ", raw)
                for match in TOKEN_RE.finditer(cleaned):
                    word = match.group(0)
                    if roman_letter_len(word) >= min_len:
                        words.add(word)
    return words


def write_thai_tsv(
    roman_words: set[str], out_tsv: Path, min_len: int
) -> list[tuple[int, str]]:
    """Transliterate; keep Thai forms with display length ``>= min_len``; sort asc."""
    thai_words = {roman_to_thai(w) for w in roman_words}
    rows = sorted(
        ((n, w) for w in thai_words if (n := thai_display_len(w)) >= min_len),
        key=lambda r: (r[0], r[1]),
    )
    lines = ["length\tword"] + [f"{n}\t{w}" for n, w in rows]
    out_tsv.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--min-len",
        type=int,
        default=20,
        help=(
            "keep Thai tokens whose display length >= this "
            "(excludes above/below marks ิีฺุูํ…; default: 20)"
        ),
    )
    parser.add_argument(
        "--tsv",
        type=Path,
        default=None,
        help="output TSV path (default: research/research_long_words_ge{N}.tsv)",
    )
    args = parser.parse_args()
    out_tsv = args.tsv or (RESEARCH / f"research_long_words_ge{args.min_len}.tsv")

    roman_words = scan_roman_words(args.min_len)
    rows = write_thai_tsv(roman_words, out_tsv, args.min_len)
    print(
        f"roman_candidates={len(roman_words)} "
        f"thai_kept={len(rows)} (thai_display_len>={args.min_len})"
    )
    print(f"wrote {out_tsv}")
    if rows:
        print(f"length range: {rows[0][0]} .. {rows[-1][0]}")
        print("--- shortest 5 ---")
        for n, w in rows[:5]:
            print(f"{n:3d}  {w}")
        print("--- longest 5 ---")
        for n, w in rows[-5:]:
            print(f"{n:3d}  {w}")


if __name__ == "__main__":
    main()
