#!/usr/bin/env python3
"""Typed load/save/normalize for cs-roman segments + layout JSON (schema_version 1).

Content and print config are separate files:

  books/cs-roman/output/<id>.segments.json   # extract staging (gitignored)
  books/cs-roman/output/<id>.layout.json
  books/cs-roman/volumes/<id>/data/segments.json  # git copy
  books/cs-roman/volumes/<id>/data/layout.json     # hand-edit print rhythm here

  python books/cs-roman/scripts/cs_roman_segments.py normalize books/cs-roman/output/01Vin01.segments.json
  python books/cs-roman/scripts/cs_roman_segments.py normalize --all
  python books/cs-roman/scripts/cs_roman_segments.py validate books/cs-roman/output/01Vin01.segments.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from cs_roman_text import CLOSER_LEVELS

SCHEMA_VERSION = 1

_CONTENT_KEEP = frozenset({"schema_version", "segments"})
_LAYOUT_KEEP = frozenset(
    {
        "schema_version",
        "source",
        "content_start_pdf_page",
        "content_end_printed_page",
        "back_matter_start_printed_page",
        "layout",
        "page_layout_reading_mode",
        "page_breaks_reading_mode",
    }
)
# Merged in-memory document (content ∪ layout).
_DOC_KEEP = _CONTENT_KEEP | _LAYOUT_KEEP

# Hand-authored section notes in layout.json (valid JSON; keys start with "//").
_DOC_COMMENT_PREFIX = "//"
_LAYOUT_DOC_COMMENT_ORDER = (
    "//",
    "//layout",
    "//page_layout_reading_mode",
    "//page_breaks_reading_mode",
)

# Body-rhythm edition defaults (absolute values). Normalize always emits a
# full ``layout`` object with these keys. At generate time these overwrite
# preamble.tex fallbacks via \\csromanlayoutapply; ``word_space`` is absolute
# fontspec WordSpace units scaled against the font-load WordSpace in
# preamble.tex (see generate_cs_roman_tex.PREAMBLE_WORD_SPACE).
# Reading-mode per-page overrides: page_layout_reading_mode.
DEFAULT_LAYOUT: dict[str, float | int | str] = {
    "word_space": 3.5,
    "line_space": 1.5,
    "par_indent": "21.6pt",
    # Extra air between prose paragraphs (added on top of baselineskip).
    "par_skip": "8pt",
    # Extra air between gāthā บท — same JSON value as par_skip; TeX adds
    # 0.3\\baselineskip so the optical gap matches prose inter-paragraph air.
    "gatha_stanza_skip": "8pt",
    "gatha_indent": "65pt",
    "emergency_stretch": "2.5em",
}

_LAYOUT_KEYS = frozenset(DEFAULT_LAYOUT)
_LAYOUT_MULTIPLIER_KEYS = frozenset({"word_space", "line_space"})
_LAYOUT_DIMENSION_KEYS = _LAYOUT_KEYS - _LAYOUT_MULTIPLIER_KEYS
_PAGE_ENTRY_META_KEYS = frozenset({"segments"})
_SEGMENT_OVERRIDE_KEYS = frozenset({"word_space"})
_DIMENSION_RE = re.compile(
    r"^[+]?\d+(?:\.\d+)?(?:pt|bp|em|ex|mm|cm|in|sp|dd|cc|nd|nc)$"
)

_SEGMENT_TYPES = frozenset(
    {
        "prose",
        "prose_continuation",
        "verse",
        "verse_continuation",
        "gatha",
        "gatha_continuation",
        "piṭaka",
        "gambhīra",
        "namakkāraṃ",
        "chapter",
        "title",
        "tassuddānaṃ",
        "niṭṭhitaṃ",
        "note",
        "subhead",
        "centered",
    }
)

_HEADING_KINDS = frozenset(
    {"nik", "boo", "cha", "h1", "h2", "h3", "h4", "h5", "h6"}
)
_SOURCE_LAYOUTS = frozenset(
    {"bat_line", "wak_line", "mixed", "hanging", "center"}
)
_NOTE_MARKER_RE = re.compile(r"\{\{n(\d+)\}\}")


def layout_path_for(segments_path: Path) -> Path:
    """Sibling layout.json path for a segments.json path."""
    name = segments_path.name
    if name.endswith(".segments.json"):
        return segments_path.with_name(
            name[: -len(".segments.json")] + ".layout.json"
        )
    if name == "segments.json":
        return segments_path.with_name("layout.json")
    return segments_path.with_name(segments_path.stem + ".layout.json")


def is_doc_comment_key(key: object) -> bool:
    """True for layout documentation keys (``//``, ``//layout``, …)."""
    return isinstance(key, str) and key.startswith(_DOC_COMMENT_PREFIX)


# Signature of UTF-8 Thai misread as windows-874 / cp1252 then re-saved as UTF-8
# (e.g. PowerShell ``Get-Content`` without ``-Encoding utf8`` on Thai Windows).
_MOJIBAKE_MARKERS = (
    "\u20ac",  # EURO SIGN — often from UTF-8 lead byte 0x80 via cp1252/cp874
    "\u0081",
    "\u008d",
    "\u008f",
    "\u0090",
    "\u009d",
    "\u0099",  # C1 controls left from mis-decoded UTF-8 continuation bytes
)


def doc_comment_encoding_errors(data: dict[str, Any]) -> list[str]:
    """Flag ``//…`` notes that look like UTF-8 mojibake (not content bugs)."""
    errors: list[str] = []
    for key, value in doc_comment_entries(data).items():
        texts = value if isinstance(value, list) else [value]
        for text in texts:
            if not isinstance(text, str):
                continue
            if any(marker in text for marker in _MOJIBAKE_MARKERS):
                errors.append(
                    f"{key}: looks like UTF-8 mojibake in doc comment "
                    "(do not edit JSON via PowerShell Get-Content without "
                    "-Encoding utf8; use Python pathlib UTF-8 I/O)"
                )
                break
            if len(text) > 800:
                errors.append(
                    f"{key}: doc comment suspiciously long ({len(text)} chars); "
                    "possible multi-round encoding corruption"
                )
                break
    return errors


def doc_comment_entries(data: dict[str, Any]) -> dict[str, Any]:
    """Return ``//…`` documentation entries from a layout/document dict."""
    return {k: v for k, v in data.items() if is_doc_comment_key(k)}


def volume_id_from_layout_source(source: object) -> str | None:
    """Folder id from layout ``source`` path (``…/01Vin01.pdf``)."""
    if not isinstance(source, str) or not source.strip():
        return None
    stem = Path(source.replace("\\", "/")).name
    if stem.lower().endswith(".pdf"):
        stem = stem[: -len(".pdf")]
    return stem or None


def layout_git_origin_lines(volume_id: str) -> list[str]:
    """Comment lines that name the git copy as the hand-edit target."""
    return [
        (
            "ไฟล์ที่เก็บใน git (แก้จังหวะพิมพ์ที่นี่): "
            f"books/cs-roman/volumes/{volume_id}/data/layout.json"
        ),
        (
            "output/<id>.layout.json เป็นของชั่วคราวหลังถอด PDF — "
            "ถ้ามีไฟล์ใน output แล้ว sync จะทับสำเนานี้"
        ),
    ]


def rewrite_layout_origin_comments(data: dict[str, Any]) -> dict[str, Any]:
    """Point ``//`` notes at the git layout copy, not gitignored output/."""
    volume_id = volume_id_from_layout_source(data.get("source"))
    if not volume_id:
        return data
    comments = data.get("//")
    if not isinstance(comments, list):
        return data
    lines = [str(item) for item in comments]
    if any("ไฟล์ที่เก็บใน git (แก้จังหวะพิมพ์ที่นี่):" in line for line in lines):
        return data
    if not any(line.startswith("ไฟล์ต้นทาง (แก้ที่นี่):") for line in lines):
        return data
    new_origin = layout_git_origin_lines(volume_id)
    out_lines: list[str] = []
    replaced = False
    for line in lines:
        if line.startswith("ไฟล์ต้นทาง (แก้ที่นี่):") or line.startswith(
            "ไฟล์ที่เก็บใน git (แก้จังหวะพิมพ์ที่นี่):"
        ):
            if not replaced:
                out_lines.extend(new_origin)
                replaced = True
            continue
        if line.startswith("sync คัดลอกมาที่") or line.startswith(
            "output/<id>.layout.json เป็นของชั่วคราว"
        ):
            continue
        out_lines.append(line)
    if not replaced:
        insert_at = 1 if out_lines else 0
        out_lines[insert_at:insert_at] = new_origin
    if out_lines == lines:
        return data
    updated = dict(data)
    updated["//"] = out_lines
    return updated


def _emit_doc_comments(
    out: dict[str, Any],
    comments: dict[str, Any],
    *,
    keys: tuple[str, ...] | None = None,
) -> None:
    """Insert selected documentation keys into ``out`` (skip missing)."""
    if keys is None:
        keys = tuple(comments)
    for key in keys:
        if key in comments:
            out[key] = comments[key]


def runs_have_bold(runs: Any) -> bool:
    if not isinstance(runs, list):
        return False
    return any(isinstance(r, dict) and r.get("bold") for r in runs)


def compact_script_entry(entry: dict[str, Any]) -> dict[str, Any]:
    """Keep script/value; keep runs only when at least one run is bold."""
    out: dict[str, Any] = {
        "script": entry.get("script"),
        "value": entry.get("value") or "",
    }
    runs = entry.get("runs")
    if runs_have_bold(runs):
        out["runs"] = [
            {"value": str(r.get("value") or ""), "bold": bool(r.get("bold"))}
            for r in runs
            if isinstance(r, dict)
        ]
    return out


def compact_text_field(text: Any) -> Any:
    if not isinstance(text, list):
        return text
    return [
        compact_script_entry(e) if isinstance(e, dict) else e for e in text
    ]


def compact_bats(bats: Any) -> list[dict[str, Any]] | None:
    """Drop bat/wak/role numbers; keep waks[].text only."""
    if not isinstance(bats, list) or not bats:
        return None
    out: list[dict[str, Any]] = []
    for bat in bats:
        if not isinstance(bat, dict):
            continue
        waks_out: list[dict[str, Any]] = []
        for wak in bat.get("waks") or []:
            if not isinstance(wak, dict):
                continue
            waks_out.append({"text": compact_text_field(wak.get("text"))})
        out.append({"waks": waks_out})
    return out or None


def compact_hanging_lines(lines: Any) -> list[Any] | None:
    if not isinstance(lines, list) or not lines:
        return None
    return [compact_text_field(line) for line in lines]


def compact_segment(seg: dict[str, Any]) -> dict[str, Any]:
    """Normalize one segment to schema v1 compact form (no print overrides)."""
    out: dict[str, Any] = {
        "page": seg.get("page"),
        "order": seg.get("order"),
        "segment_type": seg.get("segment_type") or "prose",
    }
    if seg.get("item") is not None:
        out["item"] = seg.get("item")
    if seg.get("section_no") is not None:
        out["section_no"] = seg.get("section_no")

    kind = out["segment_type"]
    if kind in {"gatha", "gatha_continuation"}:
        bats = compact_bats(seg.get("bats"))
        if bats is not None:
            out["bats"] = bats
        layout = seg.get("source_layout")
        if layout in _SOURCE_LAYOUTS:
            out["source_layout"] = layout
    else:
        if "text" in seg:
            out["text"] = compact_text_field(seg.get("text"))
        layout = seg.get("source_layout")
        if layout == "hanging":
            out["source_layout"] = "hanging"
            hl = compact_hanging_lines(seg.get("hanging_lines"))
            if hl is not None:
                out["hanging_lines"] = hl
        elif layout == "center":
            out["source_layout"] = "center"

    flags = [f for f in (seg.get("flags") or []) if f]
    if flags:
        out["flags"] = flags

    notes = list(seg.get("notes") or [])
    if notes:
        out["notes"] = notes

    symbol_notes = seg.get("symbol_notes") or {}
    if isinstance(symbol_notes, dict) and symbol_notes:
        out["symbol_notes"] = dict(symbol_notes)

    if seg.get("needs_review"):
        out["needs_review"] = True
        reasons = list(seg.get("review_reasons") or [])
        if reasons:
            out["review_reasons"] = reasons
    elif seg.get("review_reasons"):
        # Keep reasons even if flag cleared inconsistently.
        out["review_reasons"] = list(seg["review_reasons"])

    heading_kind = seg.get("heading_kind")
    if heading_kind:
        out["heading_kind"] = heading_kind
    closer_level = seg.get("closer_level")
    if closer_level in CLOSER_LEVELS:
        out["closer_level"] = closer_level
    if seg.get("in_toc"):
        out["in_toc"] = True

    return out


def _coerce_word_space(raw: Any) -> float | int | None:
    """fontspec WordSpace multiplier; omit when unset/invalid."""
    return _coerce_positive_number(raw)


def _coerce_positive_number(raw: Any) -> float | int | None:
    """Positive int/float; omit when unset/invalid."""
    if raw is None or raw is False:
        return None
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int):
        return raw if raw > 0 else None
    if isinstance(raw, float):
        if raw <= 0 or raw != raw:  # NaN
            return None
        return int(raw) if raw == int(raw) else raw
    if isinstance(raw, str) and raw.strip():
        try:
            return _coerce_positive_number(float(raw))
        except ValueError:
            return None
    return None


def _coerce_dimension(raw: Any) -> str | None:
    """TeX dimension string (e.g. 6.3pt, 2.5em); omit when unset/invalid."""
    if raw is None or raw is False or isinstance(raw, bool):
        return None
    if isinstance(raw, (int, float)):
        if raw <= 0 or (isinstance(raw, float) and raw != raw):
            return None
        n = int(raw) if float(raw) == int(raw) else raw
        return f"{n}pt"
    if isinstance(raw, str):
        s = raw.strip().replace(" ", "")
        if not s:
            return None
        if _DIMENSION_RE.match(s):
            return s
        try:
            return _coerce_dimension(float(s))
        except ValueError:
            return None
    return None


def _coerce_layout_value(key: str, raw: Any) -> float | int | str | None:
    if key in _LAYOUT_MULTIPLIER_KEYS:
        return _coerce_positive_number(raw)
    if key in _LAYOUT_DIMENSION_KEYS:
        return _coerce_dimension(raw)
    return None


def coerce_layout_patch(raw: Any) -> dict[str, float | int | str] | None:
    """Sparse layout object (known keys only); None if empty/invalid container."""
    if not isinstance(raw, dict):
        return None
    out: dict[str, float | int | str] = {}
    for key in DEFAULT_LAYOUT:
        if key not in raw or raw[key] is None:
            continue
        value = _coerce_layout_value(key, raw[key])
        if value is not None:
            out[key] = value
    return out or None


def merge_layout(base: dict[str, Any] | None, patch: dict[str, Any] | None) -> dict[str, float | int | str]:
    """Full layout: DEFAULT_LAYOUT ← base ← patch (layout keys only)."""
    out: dict[str, float | int | str] = dict(DEFAULT_LAYOUT)
    for src in (base, patch):
        if not isinstance(src, dict):
            continue
        for key in DEFAULT_LAYOUT:
            if key not in src or src[key] is None:
                continue
            value = _coerce_layout_value(key, src[key])
            if value is not None:
                out[key] = value
    return out


def coerce_segment_override(raw: Any) -> dict[str, float | int] | None:
    """Sparse per-segment print override (currently word_space only)."""
    if not isinstance(raw, dict):
        return None
    out: dict[str, float | int] = {}
    ws = _coerce_word_space(raw.get("word_space"))
    if ws is not None:
        out["word_space"] = ws
    return out or None


def coerce_page_segments(raw: Any) -> dict[str, dict[str, float | int]] | None:
    """Map 1-based page-local segment index → override; omit when empty."""
    if not isinstance(raw, dict) or not raw:
        return None
    out: dict[str, dict[str, float | int]] = {}
    for idx_key, patch in raw.items():
        try:
            idx = int(idx_key)
        except (TypeError, ValueError):
            continue
        if idx < 1:
            continue
        coerced = coerce_segment_override(patch)
        if coerced:
            out[str(idx)] = coerced
    if not out:
        return None
    return dict(sorted(out.items(), key=lambda kv: int(kv[0])))


def coerce_page_entry(raw: Any) -> dict[str, Any] | None:
    """One page_layout value: layout keys + optional segments map."""
    if not isinstance(raw, dict):
        return None
    out: dict[str, Any] = {}
    layout_patch = coerce_layout_patch(
        {k: v for k, v in raw.items() if k not in _PAGE_ENTRY_META_KEYS}
    )
    if layout_patch:
        out.update(layout_patch)
    segments = coerce_page_segments(raw.get("segments"))
    if segments is not None:
        out["segments"] = segments
    return out or None


def layout_keys_only(page_entry: dict[str, Any] | None) -> dict[str, float | int | str]:
    """Strip meta keys (e.g. segments) from a page_layout entry."""
    if not isinstance(page_entry, dict):
        return {}
    return {
        k: v
        for k, v in page_entry.items()
        if k in _LAYOUT_KEYS and v is not None
    }


def coerce_page_layout(
    raw: Any, *, keep_empty: bool = False
) -> dict[str, dict[str, Any]] | None:
    """Map printed page → page entry; omit when empty unless ``keep_empty``."""
    if not isinstance(raw, dict):
        return None
    if not raw:
        return {} if keep_empty else None
    out: dict[str, dict[str, Any]] = {}
    for page_key, patch in raw.items():
        try:
            page = int(page_key)
        except (TypeError, ValueError):
            continue
        if page < 1:
            continue
        coerced = coerce_page_entry(patch)
        if coerced:
            out[str(page)] = coerced
    if not out:
        return {} if keep_empty else None
    return dict(sorted(out.items(), key=lambda kv: int(kv[0])))


def coerce_page_breaks_reading(raw: Any) -> dict[str, list[int]] | None:
    """Normalize ``page_breaks_reading_mode`` to ``{before_orders: [int, …]}``.

    Omit when absent/empty. Deduplicates and sorts ``before_orders``.
    """
    if raw is None:
        return None
    if not isinstance(raw, dict):
        return None
    raw_orders = raw.get("before_orders")
    if raw_orders is None:
        return None
    if not isinstance(raw_orders, list):
        return None
    orders: list[int] = []
    seen: set[int] = set()
    for item in raw_orders:
        try:
            order = int(item)
        except (TypeError, ValueError):
            continue
        if order < 1 or order in seen:
            continue
        seen.add(order)
        orders.append(order)
    if not orders:
        return None
    return {"before_orders": sorted(orders)}


def migrate_segment_word_space(data: dict[str, Any]) -> dict[str, Any]:
    """Drop legacy segment ``word_space`` and removed ``page_layout``.

    Per-page sync overrides (``page_layout`` / segment word_space) are no longer
    supported; reading uses ``page_layout_reading_mode`` only.
    """
    segments = [s for s in (data.get("segments") or []) if isinstance(s, dict)]
    has_seg_ws = any(s.get("word_space") is not None for s in segments)
    has_page_layout = data.get("page_layout") is not None
    if not has_seg_ws and not has_page_layout:
        return data

    data = dict(data)
    if has_seg_ws:
        data["segments"] = [
            {k: v for k, v in s.items() if k != "word_space"}
            if isinstance(s, dict)
            else s
            for s in (data.get("segments") or [])
        ]
    data.pop("page_layout", None)
    return data


def normalize_content(data: dict[str, Any]) -> dict[str, Any]:
    """Content file: schema_version + compact segments only."""
    segments = [
        compact_segment(s) if isinstance(s, dict) else s
        for s in (data.get("segments") or [])
    ]
    return {"schema_version": SCHEMA_VERSION, "segments": segments}


def normalize_layout(data: dict[str, Any]) -> dict[str, Any]:
    """Layout file: source/bounds + layout + reading page overrides/breaks."""
    data = rewrite_layout_origin_comments(data)
    comments = doc_comment_entries(data)
    out: dict[str, Any] = {"schema_version": SCHEMA_VERSION}
    _emit_doc_comments(out, comments, keys=("//",))
    if data.get("source") is not None:
        out["source"] = data["source"]
    for key in (
        "content_start_pdf_page",
        "content_end_printed_page",
        "back_matter_start_printed_page",
    ):
        if key in data and data[key] is not None:
            out[key] = data[key]
    _emit_doc_comments(out, comments, keys=("//layout",))
    out["layout"] = merge_layout(data.get("layout"), None)
    _emit_doc_comments(out, comments, keys=("//page_layout_reading_mode",))
    # Keep empty {} when present so the reading-mode slot stays visible in file.
    if "page_layout_reading_mode" in data and data.get(
        "page_layout_reading_mode"
    ) is not None:
        reading = coerce_page_layout(
            data.get("page_layout_reading_mode"), keep_empty=True
        )
        if reading is not None:
            out["page_layout_reading_mode"] = reading
    _emit_doc_comments(out, comments, keys=("//page_breaks_reading_mode",))
    breaks = coerce_page_breaks_reading(data.get("page_breaks_reading_mode"))
    if breaks is not None:
        out["page_breaks_reading_mode"] = breaks
    for key, value in comments.items():
        if key not in out:
            out[key] = value
    return out


def normalize_document(data: dict[str, Any]) -> dict[str, Any]:
    """Merged in-memory document (content + layout). Migrates legacy fields."""
    data = migrate_segment_word_space(data)
    content = normalize_content(data)
    layout = normalize_layout(data)
    return merge_documents(content, layout)


def split_document(data: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return (content_doc, layout_doc) after normalize/migrate."""
    merged = normalize_document(data)
    return normalize_content(merged), normalize_layout(merged)


def merge_documents(
    content: dict[str, Any] | None,
    layout: dict[str, Any] | None,
) -> dict[str, Any]:
    """Merge content + layout files into one in-memory document."""
    out: dict[str, Any] = {"schema_version": SCHEMA_VERSION}
    if isinstance(layout, dict):
        for key in _LAYOUT_KEEP:
            if key == "schema_version":
                continue
            if key in layout and layout[key] is not None:
                out[key] = layout[key]
        for key, value in doc_comment_entries(layout).items():
            out[key] = value
    if isinstance(content, dict) and "segments" in content:
        out["segments"] = content["segments"]
    elif isinstance(layout, dict) and "segments" in layout:
        # Legacy combined file loaded as "layout" side — keep segments.
        out["segments"] = layout["segments"]
    else:
        out["segments"] = []
    if "layout" not in out:
        out["layout"] = dict(DEFAULT_LAYOUT)
    return out


def dumps(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def load(path: Path) -> dict[str, Any]:
    """Load a single JSON file (no sibling merge)."""
    return json.loads(path.read_text(encoding="utf-8"))


def load_document(segments_path: Path, layout_path: Path | None = None) -> dict[str, Any]:
    """Load segments (+ sibling layout when present) into a merged document.

    Supports legacy combined ``*.segments.json`` that still embeds layout keys.
    """
    segments_path = Path(segments_path)
    content = load(segments_path)
    layout_file = Path(layout_path) if layout_path is not None else layout_path_for(
        segments_path
    )
    layout: dict[str, Any] | None = None
    if layout_file.is_file():
        layout = load(layout_file)
    elif any(k in content for k in _LAYOUT_KEEP - {"schema_version"}):
        # Legacy combined file.
        layout = content
    return normalize_document(merge_documents(content, layout))


def save_content(path: Path, data: dict[str, Any], *, normalize: bool = True) -> None:
    payload = normalize_content(data) if normalize else data
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dumps(payload), encoding="utf-8")


def save_layout(path: Path, data: dict[str, Any], *, normalize: bool = True) -> None:
    payload = normalize_layout(data) if normalize else data
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dumps(payload), encoding="utf-8")


def save_document(
    segments_path: Path,
    data: dict[str, Any],
    *,
    layout_path: Path | None = None,
    normalize: bool = True,
) -> None:
    """Write split content + layout files."""
    segments_path = Path(segments_path)
    layout_file = Path(layout_path) if layout_path is not None else layout_path_for(
        segments_path
    )
    if normalize:
        content, layout = split_document(data)
    else:
        content, layout = normalize_content(data), normalize_layout(data)
    save_content(segments_path, content, normalize=False)
    save_layout(layout_file, layout, normalize=False)


def save(path: Path, data: dict[str, Any], *, normalize: bool = True) -> None:
    """Save to ``path``.

    - ``*.segments.json`` / ``segments.json`` → content file; also writes/updates
      sibling layout when ``data`` carries layout keys or the sibling already exists
      and ``data`` includes bounds/layout fields.
    - ``*.layout.json`` / ``layout.json`` → layout file only.
    - Other paths → legacy single-file merged document (tests).
    """
    path = Path(path)
    name = path.name
    if name.endswith(".layout.json") or name == "layout.json":
        save_layout(path, data, normalize=normalize)
        return
    if name.endswith(".segments.json") or name == "segments.json":
        layout_file = layout_path_for(path)
        has_layout_fields = any(
            k in data and data[k] is not None
            for k in _LAYOUT_KEEP - {"schema_version"}
        )
        if has_layout_fields or layout_file.is_file():
            if layout_file.is_file() and not has_layout_fields:
                # Content-only update: preserve existing layout file.
                save_content(path, data, normalize=normalize)
                return
            if layout_file.is_file() and has_layout_fields:
                # Merge bounds/layout updates onto existing print tuning.
                existing = load(layout_file)
                merged = merge_documents(data, existing)
                # Prefer incoming layout keys when present.
                for key in _LAYOUT_KEEP - {"schema_version"}:
                    if key in data and data[key] is not None:
                        merged[key] = data[key]
                if "segments" in data:
                    merged["segments"] = data["segments"]
                save_document(path, merged, layout_path=layout_file, normalize=normalize)
                return
            save_document(path, data, layout_path=layout_file, normalize=normalize)
            return
        save_content(path, data, normalize=normalize)
        return

    payload = normalize_document(data) if normalize else data
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dumps(payload), encoding="utf-8")


def normalize_file(path: Path) -> dict[str, Any]:
    """Load combined or split inputs, rewrite split files; return stats."""
    path = Path(path)
    before = path.stat().st_size
    layout_file = layout_path_for(path)
    layout_before = layout_file.stat().st_size if layout_file.is_file() else 0

    if path.name.endswith(".layout.json") or path.name == "layout.json":
        # Normalize layout alone; leave segments untouched.
        data = load(path)
        save_layout(path, data, normalize=True)
        after = path.stat().st_size
        return {
            "path": str(path).replace("\\", "/"),
            "segments": 0,
            "bytes_before": before,
            "bytes_after": after,
            "schema_version": SCHEMA_VERSION,
            "layout_path": str(path).replace("\\", "/"),
        }

    doc = load_document(path)
    save_document(path, doc, layout_path=layout_file, normalize=True)
    after = path.stat().st_size
    layout_after = layout_file.stat().st_size if layout_file.is_file() else 0
    return {
        "path": str(path).replace("\\", "/"),
        "segments": len(doc.get("segments") or []),
        "bytes_before": before + layout_before,
        "bytes_after": after + layout_after,
        "schema_version": SCHEMA_VERSION,
        "layout_path": str(layout_file).replace("\\", "/"),
    }


# --- accessors (defaults for omitted empty fields) ---


def seg_flags(seg: dict[str, Any]) -> list[str]:
    return list(seg.get("flags") or [])


def seg_notes(seg: dict[str, Any]) -> list[str]:
    return list(seg.get("notes") or [])


def seg_symbol_notes(seg: dict[str, Any]) -> dict[str, str]:
    raw = seg.get("symbol_notes") or {}
    return dict(raw) if isinstance(raw, dict) else {}


def seg_needs_review(seg: dict[str, Any]) -> bool:
    return bool(seg.get("needs_review"))


def seg_review_reasons(seg: dict[str, Any]) -> list[str]:
    return list(seg.get("review_reasons") or [])


def page_local_index(data: dict[str, Any], seg: dict[str, Any]) -> int | None:
    """1-based index of ``seg`` among segments on the same printed page."""
    page = seg.get("page")
    order = seg.get("order")
    if not isinstance(page, int):
        return None
    page_segs = [
        s
        for s in (data.get("segments") or [])
        if isinstance(s, dict) and s.get("page") == page
    ]
    page_segs.sort(key=lambda s: int(s.get("order") or 0))
    for i, s in enumerate(page_segs, 1):
        if s.get("order") == order:
            return i
    return None


def seg_word_space(
    data: dict[str, Any] | None,
    seg: dict[str, Any] | None = None,
) -> float | int | None:
    """Legacy segment ``word_space`` only (no sync page_layout overrides).

    Backward-compatible call shapes:
      seg_word_space(doc, seg)
      seg_word_space(seg)  # legacy: only seg.get("word_space")
    """
    if seg is None:
        # Legacy: first arg is the segment dict.
        if isinstance(data, dict):
            return _coerce_word_space(data.get("word_space"))
        return None
    return _coerce_word_space(seg.get("word_space"))


def doc_layout(data: dict[str, Any]) -> dict[str, float | int | str]:
    """Full volume layout (defaults merged)."""
    return merge_layout(data.get("layout"), None)


def doc_page_layout_reading(data: dict[str, Any]) -> dict[int, dict[str, Any]]:
    """Reading-mode physical page → page entry (layout keys only; no segments)."""
    raw = coerce_page_layout(data.get("page_layout_reading_mode")) or {}
    return {int(page): dict(patch) for page, patch in raw.items()}


def doc_reading_break_before_orders(data: dict[str, Any]) -> set[int]:
    """Segment ``order`` values that force ``\\clearpage`` in reading mode."""
    coerced = coerce_page_breaks_reading(data.get("page_breaks_reading_mode"))
    if not coerced:
        return set()
    return set(coerced["before_orders"])


def effective_layout(
    data: dict[str, Any],
    page: int | None = None,
    *,
    reading: bool = False,
) -> dict[str, float | int | str]:
    """Volume layout, optionally merged with reading per-page overrides.

    Sync (``reading=False``) always uses volume ``layout`` only.
    Reading uses ``page_layout_reading_mode`` (physical reading page).
    """
    base = doc_layout(data)
    if not reading or page is None:
        return base
    entry = doc_page_layout_reading(data).get(int(page))
    patch = layout_keys_only(entry)
    if not patch:
        return base
    return merge_layout(base, patch)


def effective_word_space(
    data: dict[str, Any],
    seg: dict[str, Any],
    *,
    page: int | None = None,
) -> float | int:
    """Segment override → page → volume layout (always a positive number)."""
    seg_ws = seg_word_space(data, seg)
    if seg_ws is not None:
        return seg_ws
    page_no = int(page if page is not None else seg.get("page") or 0)
    layout = effective_layout(data, page_no if page_no > 0 else None)
    ws = _coerce_positive_number(layout.get("word_space"))
    return ws if ws is not None else DEFAULT_LAYOUT["word_space"]


def _validate_layout_object(
    raw: Any, *, prefix: str, errors: list[str], allow_partial: bool
) -> None:
    if raw is None:
        return
    if not isinstance(raw, dict):
        errors.append(f"{prefix}: need object")
        return
    unknown = sorted(set(raw) - _LAYOUT_KEYS)
    if unknown:
        errors.append(f"{prefix}: unknown keys: {', '.join(unknown)}")
    if not allow_partial:
        missing = sorted(_LAYOUT_KEYS - set(raw))
        if missing:
            errors.append(f"{prefix}: missing keys: {', '.join(missing)}")
    for key in _LAYOUT_KEYS:
        if key not in raw or raw[key] is None:
            continue
        if _coerce_layout_value(key, raw[key]) is None:
            kind = (
                "positive number (multiplier)"
                if key in _LAYOUT_MULTIPLIER_KEYS
                else "positive TeX dimension (e.g. 6.3pt)"
            )
            errors.append(f"{prefix}.{key}: need {kind}, got {raw[key]!r}")


def _validate_page_entry(
    raw: Any,
    *,
    prefix: str,
    errors: list[str],
    page: int,
    segments: list[Any],
) -> None:
    if raw is None:
        return
    if not isinstance(raw, dict):
        errors.append(f"{prefix}: need object")
        return
    unknown = sorted(set(raw) - _LAYOUT_KEYS - _PAGE_ENTRY_META_KEYS)
    if unknown:
        errors.append(f"{prefix}: unknown keys: {', '.join(unknown)}")
    _validate_layout_object(
        {k: v for k, v in raw.items() if k in _LAYOUT_KEYS},
        prefix=prefix,
        errors=errors,
        allow_partial=True,
    )
    seg_map = raw.get("segments")
    if seg_map is None:
        return
    if not isinstance(seg_map, dict):
        errors.append(f"{prefix}.segments: need object keyed by page-local index")
        return
    page_count = sum(
        1
        for s in segments
        if isinstance(s, dict) and s.get("page") == page
    )
    for idx_key, patch in seg_map.items():
        try:
            idx = int(idx_key)
        except (TypeError, ValueError):
            errors.append(f"{prefix}.segments: invalid index {idx_key!r}")
            continue
        if idx < 1:
            errors.append(f"{prefix}.segments: index must be >= 1, got {idx_key!r}")
            continue
        if page_count and idx > page_count:
            errors.append(
                f"{prefix}.segments.{idx}: index out of range "
                f"(page {page} has {page_count} segments)"
            )
        if not isinstance(patch, dict):
            errors.append(f"{prefix}.segments.{idx}: need object")
            continue
        unknown_seg = sorted(set(patch) - _SEGMENT_OVERRIDE_KEYS)
        if unknown_seg:
            errors.append(
                f"{prefix}.segments.{idx}: unknown keys: {', '.join(unknown_seg)}"
            )
        if "word_space" in patch and patch.get("word_space") is not None:
            if _coerce_word_space(patch.get("word_space")) is None:
                errors.append(
                    f"{prefix}.segments.{idx}.word_space: need positive number, "
                    f"got {patch.get('word_space')!r}"
                )


def validate_document(data: dict[str, Any]) -> list[str]:
    """Return list of human-readable validation errors (empty = ok)."""
    errors: list[str] = []
    version = data.get("schema_version")
    if version != SCHEMA_VERSION:
        errors.append(f"schema_version: expected {SCHEMA_VERSION}, got {version!r}")
    if "segments" not in data or not isinstance(data["segments"], list):
        errors.append("segments: missing or not a list")
        return errors
    if "source" not in data:
        errors.append("source: missing")
    if "content_start_pdf_page" not in data:
        errors.append("content_start_pdf_page: missing")

    unknown_doc = sorted(
        k
        for k in set(data) - _DOC_KEEP
        if not is_doc_comment_key(k) and k != "page_layout"
    )
    if unknown_doc:
        errors.append(f"unexpected document keys: {', '.join(unknown_doc)}")
    if "page_layout" in data and data.get("page_layout") is not None:
        errors.append(
            "page_layout: removed; use page_layout_reading_mode for reading "
            "per-page overrides (sync uses volume layout only)"
        )
    for key, value in doc_comment_entries(data).items():
        if isinstance(value, str):
            continue
        if isinstance(value, list) and all(isinstance(x, str) for x in value):
            continue
        errors.append(
            f"{key}: need string or list of strings (layout documentation)"
        )
    errors.extend(doc_comment_encoding_errors(data))

    if "layout" in data and data.get("layout") is not None:
        _validate_layout_object(
            data.get("layout"), prefix="layout", errors=errors, allow_partial=True
        )
    if (
        "page_layout_reading_mode" in data
        and data.get("page_layout_reading_mode") is not None
    ):
        raw_reading = data.get("page_layout_reading_mode")
        if not isinstance(raw_reading, dict):
            errors.append(
                "page_layout_reading_mode: need object keyed by physical page"
            )
        else:
            for page_key, patch in raw_reading.items():
                try:
                    page = int(page_key)
                except (TypeError, ValueError):
                    errors.append(
                        f"page_layout_reading_mode: invalid page key {page_key!r}"
                    )
                    continue
                if page < 1:
                    errors.append(
                        "page_layout_reading_mode: page must be >= 1, "
                        f"got {page_key!r}"
                    )
                    continue
                if isinstance(patch, dict) and "segments" in patch:
                    errors.append(
                        f"page_layout_reading_mode.{page}.segments: "
                        "not supported (reading mode has no page-local "
                        "segment index)"
                    )
                    layout_only = {
                        k: v for k, v in patch.items() if k != "segments"
                    }
                else:
                    layout_only = patch
                _validate_page_entry(
                    layout_only,
                    prefix=f"page_layout_reading_mode.{page}",
                    errors=errors,
                    page=page,
                    segments=[],
                )
    if (
        "page_breaks_reading_mode" in data
        and data.get("page_breaks_reading_mode") is not None
    ):
        raw_breaks = data.get("page_breaks_reading_mode")
        if not isinstance(raw_breaks, dict):
            errors.append(
                "page_breaks_reading_mode: need object with before_orders"
            )
        else:
            unknown = set(raw_breaks) - {"before_orders"}
            for key in sorted(unknown):
                errors.append(
                    f"page_breaks_reading_mode: unknown key {key!r}"
                )
            raw_orders = raw_breaks.get("before_orders")
            if "before_orders" not in raw_breaks:
                errors.append(
                    "page_breaks_reading_mode: need before_orders list"
                )
            elif not isinstance(raw_orders, list):
                errors.append(
                    "page_breaks_reading_mode.before_orders: need list of int"
                )
            else:
                for j, item in enumerate(raw_orders):
                    try:
                        order = int(item)
                    except (TypeError, ValueError):
                        errors.append(
                            "page_breaks_reading_mode.before_orders"
                            f"[{j}]: need int, got {item!r}"
                        )
                        continue
                    if order < 1:
                        errors.append(
                            "page_breaks_reading_mode.before_orders"
                            f"[{j}]: must be >= 1, got {order}"
                        )

    for i, seg in enumerate(data["segments"]):
        if not isinstance(seg, dict):
            errors.append(f"segments[{i}]: not an object")
            continue
        prefix = f"segments[{i}]"
        if not isinstance(seg.get("page"), int):
            errors.append(f"{prefix}.page: need int")
        if not isinstance(seg.get("order"), int):
            errors.append(f"{prefix}.order: need int")
        st = seg.get("segment_type")
        if st not in _SEGMENT_TYPES:
            errors.append(f"{prefix}.segment_type: unknown {st!r}")
        hk = seg.get("heading_kind")
        if hk is not None and hk not in _HEADING_KINDS:
            errors.append(f"{prefix}.heading_kind: unknown {hk!r}")
        layout = seg.get("source_layout")
        if layout is not None and layout not in _SOURCE_LAYOUTS:
            errors.append(f"{prefix}.source_layout: unknown {layout!r}")
        closer_level = seg.get("closer_level")
        if closer_level is not None and closer_level not in CLOSER_LEVELS:
            errors.append(f"{prefix}.closer_level: unknown {closer_level!r}")
        if "word_space" in seg:
            errors.append(
                f"{prefix}.word_space: not stored on segments; "
                f"use layout / page_layout_reading_mode"
            )
        if "pdf_page" in seg:
            errors.append(f"{prefix}.pdf_page: must not be stored in v1")
        notes = seg_notes(seg)
        for field_name in ("text",):
            text = seg.get(field_name)
            if isinstance(text, list):
                for entry in text:
                    if isinstance(entry, dict):
                        _check_markers(entry.get("value") or "", notes, errors, prefix)
                        for run in entry.get("runs") or []:
                            if isinstance(run, dict):
                                _check_markers(
                                    run.get("value") or "", notes, errors, prefix
                                )
        for bat in seg.get("bats") or []:
            if not isinstance(bat, dict):
                continue
            if "bat" in bat:
                errors.append(f"{prefix}.bats[].bat: must not be stored in v1")
            for wak in bat.get("waks") or []:
                if not isinstance(wak, dict):
                    continue
                if "wak" in wak or "role" in wak:
                    errors.append(
                        f"{prefix}.bats[].waks: wak/role must not be stored in v1"
                    )
                wt = wak.get("text")
                if isinstance(wt, list):
                    for entry in wt:
                        if isinstance(entry, dict):
                            _check_markers(
                                entry.get("value") or "", notes, errors, prefix
                            )
    return errors


def _check_markers(
    value: str, notes: list[str], errors: list[str], prefix: str
) -> None:
    for m in _NOTE_MARKER_RE.finditer(value):
        idx = int(m.group(1))
        if idx < 0 or idx >= len(notes):
            errors.append(f"{prefix}: marker {{{{n{idx}}}}} out of range for notes")


def _default_json_dir() -> Path:
    from paths import OUTPUT_DIR

    return OUTPUT_DIR


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_norm = sub.add_parser(
        "normalize",
        help="Rewrite to split schema v1 (segments.json + layout.json)",
    )
    p_norm.add_argument("paths", nargs="*", type=Path)
    p_norm.add_argument(
        "--all",
        action="store_true",
        help="Normalize every *.segments.json under books/cs-roman/output",
    )
    p_norm.add_argument(
        "--dir",
        type=Path,
        default=_default_json_dir(),
        help="Directory for --all (default: books/cs-roman/output)",
    )

    p_val = sub.add_parser("validate", help="Validate schema v1 constraints")
    p_val.add_argument("paths", nargs="+", type=Path)

    args = parser.parse_args(argv)

    if args.cmd == "normalize":
        paths: list[Path] = list(args.paths)
        if args.all:
            paths.extend(sorted(args.dir.glob("*.segments.json")))
        if not paths:
            print("No paths given (use files or --all)", file=sys.stderr)
            return 1
        total_before = 0
        total_after = 0
        for path in paths:
            if not path.is_file():
                print(f"Missing: {path}", file=sys.stderr)
                return 1
            stats = normalize_file(path)
            total_before += stats["bytes_before"]
            total_after += stats["bytes_after"]
            pct = (
                100.0 * (1 - stats["bytes_after"] / stats["bytes_before"])
                if stats["bytes_before"]
                else 0.0
            )
            layout_note = ""
            if stats.get("layout_path"):
                layout_note = f" + {Path(stats['layout_path']).name}"
            print(
                f"{path.name}{layout_note}: {stats['segments']} segments, "
                f"{stats['bytes_before']} -> {stats['bytes_after']} bytes "
                f"({pct:.1f}% smaller)"
            )
        if len(paths) > 1:
            pct = 100.0 * (1 - total_after / total_before) if total_before else 0.0
            print(
                f"Total: {total_before} -> {total_after} bytes ({pct:.1f}% smaller)"
            )
        return 0

    if args.cmd == "validate":
        failed = 0
        for path in args.paths:
            if path.name.endswith(".layout.json") or path.name == "layout.json":
                # Validate layout structure with empty segments (skip index range).
                layout = load(path)
                data = merge_documents({"schema_version": SCHEMA_VERSION, "segments": []}, layout)
                # Soft-validate: missing segments list ok for layout-only; inject.
                errors = [
                    e
                    for e in validate_document(data)
                    if not e.startswith("segments:")
                    and "source: missing" not in e
                    and "content_start_pdf_page: missing" not in e
                ]
                # Re-run targeted checks when source/bounds present.
                if layout.get("source") is None:
                    errors.append("source: missing")
                if layout.get("content_start_pdf_page") is None:
                    errors.append("content_start_pdf_page: missing")
            else:
                data = load_document(path)
                errors = validate_document(data)
            if errors:
                failed += 1
                print(f"FAIL {path}:")
                for err in errors[:40]:
                    print(f"  - {err}")
                if len(errors) > 40:
                    print(f"  … +{len(errors) - 40} more")
            else:
                n = len(data.get("segments") or [])
                print(f"OK {path} ({n} segments)")
        return 1 if failed else 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
