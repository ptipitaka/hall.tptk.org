#!/usr/bin/env python3
"""Retag hang-band / deep-column embedded gāthā on stored segments JSON.

Re-runs ``tag_gatha_by_geometry`` + stanza grouping for printed-line prose
that the extractor previously left as ``prose`` (e.g. wak_line udāna quotes
in the hang band). Does not re-extract text from the PDF.

Preserves ``order`` of the first line in each folded run (no global
renumber) so ``page_breaks_reading_mode.before_orders`` stay valid.

  python books/cs-roman/scripts/fixup_gatha_geometry.py --volume 02Vin02
  python books/cs-roman/scripts/fixup_gatha_geometry.py --all
  python books/cs-roman/scripts/fixup_gatha_geometry.py --volume 02Vin02 --dry-run
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import fitz
except ImportError:  # pragma: no cover
    print("PyMuPDF (pymupdf) is required", file=sys.stderr)
    raise

from paths import BOOKS, OUTPUT_DIR, REPO, ensure_import_paths

ensure_import_paths()
from cs_roman_hanging import segment_roman_text  # noqa: E402
from cs_roman_segments import load_document, save_content  # noqa: E402
from extract_cs_roman_pdf import (  # noqa: E402
    Segment,
    _consume_printed_gatha_lines,
    _segment_to_json,
    tag_gatha_by_geometry,
)


def _volume_ids() -> list[str]:
    vols = BOOKS / "volumes"
    if not vols.is_dir():
        return []
    return sorted(
        p.name
        for p in vols.iterdir()
        if p.is_dir() and (p / "data" / "segments.json").is_file()
    )


def _resolve_pdf(volume_id: str, doc_data: dict, override: Path | None) -> Path | None:
    if override is not None and override.is_file():
        return override
    source = doc_data.get("source") or ""
    if source:
        cand = REPO / source
        if cand.is_file():
            return cand
    alt = BOOKS / "volumes" / volume_id / "source" / f"{volume_id}.pdf"
    if alt.is_file():
        return alt
    src = BOOKS / "source" / f"{volume_id}.pdf"
    if src.is_file():
        return src
    return None


def _json_to_segment(d: dict, *, content_start: int) -> Segment:
    roman = segment_roman_text(d) or ""
    page = int(d.get("page") or 0)
    pdf_page = d.get("pdf_page")
    if not isinstance(pdf_page, int) or pdf_page < 1:
        pdf_page = content_start + page - 1 if page > 0 else None
    flags = list(d.get("flags") or [])
    notes = list(d.get("notes") or [])
    symbol_notes = dict(d.get("symbol_notes") or {})
    return Segment(
        page=page,
        order=int(d.get("order") or 0),
        item=d.get("item"),
        segment_type=str(d.get("segment_type") or "prose"),
        text=roman,
        pdf_page=pdf_page,
        flags=flags,
        notes=notes,
        symbol_notes=symbol_notes,
        needs_review=bool(d.get("needs_review")),
        review_reasons=list(d.get("review_reasons") or []),
        section_no=d.get("section_no"),
        source_layout=d.get("source_layout"),
        bats=d.get("bats"),
    )


def _overlay_line_text_onto_waks(
    stanza_payload: dict, source_dicts: list[dict]
) -> None:
    """For wak_line folds, copy bilingual line ``text`` onto each วรรค."""
    if stanza_payload.get("source_layout") != "wak_line":
        return
    flat: list[dict] = []
    for bat in stanza_payload.get("bats") or []:
        for wak in bat.get("waks") or []:
            flat.append(wak)
    if len(flat) != len(source_dicts):
        return
    for wak, src in zip(flat, source_dicts):
        text = src.get("text")
        if isinstance(text, list) and text:
            wak["text"] = text


def _source_lines_for_stanza(payload: dict) -> int:
    """How many printed-line source segments this folded บท consumed."""
    bats = payload.get("bats") or []
    if payload.get("source_layout") == "wak_line":
        return sum(len(b.get("waks") or []) for b in bats)
    return len(bats)


def _roman_preview(payload: dict) -> str:
    bats = payload.get("bats") or []
    if not bats:
        return ""
    w0 = (bats[0].get("waks") or [{}])[0]
    t0 = w0.get("text")
    if isinstance(t0, list):
        for e in t0:
            if isinstance(e, dict) and e.get("script") == "roman":
                return str(e.get("value") or "")[:50]
    if isinstance(t0, str):
        return t0[:50]
    return ""


def fixup_volume(
    volume_id: str,
    *,
    pdf: Path | None = None,
    dry_run: bool = False,
    sync_output: bool = True,
) -> int:
    vol = BOOKS / "volumes" / volume_id
    segments_path = vol / "data" / "segments.json"
    if not segments_path.is_file():
        print(f"Missing {segments_path}", file=sys.stderr)
        return 1

    doc_data = load_document(segments_path)
    content_start = int(doc_data.get("content_start_pdf_page") or 0)
    if content_start < 1:
        print(f"{volume_id}: content_start_pdf_page missing/invalid", file=sys.stderr)
        return 1

    pdf_path = _resolve_pdf(volume_id, doc_data, pdf)
    if pdf_path is None:
        print(f"Missing source PDF for {volume_id}", file=sys.stderr)
        return 1

    json_segs = [dict(s) for s in (doc_data.get("segments") or []) if isinstance(s, dict)]
    work = [_json_to_segment(s, content_start=content_start) for s in json_segs]
    before_kinds = [s.segment_type for s in work]

    pdf_doc = fitz.open(pdf_path)
    tagged = tag_gatha_by_geometry(pdf_doc, work, content_start=content_start)

    out: list[dict] = []
    folded_stanzas = 0
    folded_lines = 0
    i = 0
    n = len(work)
    while i < n:
        cur = work[i]
        newly = (
            before_kinds[i] == "prose"
            and _base_is_gatha(cur.segment_type)
            and cur.bats is None
        )
        if not newly:
            out.append(json_segs[i])
            i += 1
            continue

        j = i + 1
        while (
            j < n
            and before_kinds[j] == "prose"
            and _base_is_gatha(work[j].segment_type)
            and work[j].bats is None
        ):
            j += 1

        run = work[i:j]
        source_dicts = json_segs[i:j]
        stanzas = _consume_printed_gatha_lines(run)
        first_order = int(source_dicts[0].get("order") or run[0].order)
        line_cursor = 0
        for offset, stanza in enumerate(stanzas):
            stanza.order = first_order + offset
            payload = _segment_to_json(stanza)
            n_src = _source_lines_for_stanza(payload)
            chunk = source_dicts[line_cursor : line_cursor + n_src]
            line_cursor += n_src
            _overlay_line_text_onto_waks(payload, chunk)
            if chunk:
                payload["page"] = chunk[0].get("page")
            payload["order"] = stanza.order
            if not payload.get("needs_review"):
                payload.pop("needs_review", None)
                payload.pop("review_reasons", None)
            preview = _roman_preview(payload)
            last_o = chunk[-1].get("order") if chunk else "?"
            print(
                f"  fold p{payload.get('page')} o{payload.get('order')}"
                f" (lines …{last_o}): "
                f"{len(chunk)} lines -> {payload.get('source_layout')} | {preview}"
            )
            out.append(payload)
            folded_stanzas += 1
        folded_lines += len(source_dicts)
        i = j

    print(
        f"{volume_id}: geometry_tagged_lines={tagged} "
        f"folded_lines={folded_lines} stanzas={folded_stanzas} "
        f"segments {len(json_segs)} -> {len(out)}"
    )

    if dry_run:
        return 0

    doc_data["segments"] = out
    save_content(segments_path, doc_data, normalize=True)
    print(f"Wrote {segments_path}")

    if sync_output:
        out_path = OUTPUT_DIR / f"{volume_id}.segments.json"
        if out_path.is_file():
            save_content(out_path, doc_data, normalize=True)
            print(f"Wrote {out_path}")
    return 0


def _base_is_gatha(kind: str) -> bool:
    return kind == "gatha" or kind == "gatha_continuation"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--volume", help="e.g. 02Vin02")
    parser.add_argument("--all", action="store_true", help="All volumes with segments")
    parser.add_argument(
        "--pdf",
        type=Path,
        default=None,
        help="Override source PDF (single --volume only)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report changes without writing segments.json",
    )
    parser.add_argument(
        "--no-sync-output",
        action="store_true",
        help="Do not also write books/cs-roman/output/<id>.segments.json",
    )
    args = parser.parse_args(argv)

    if bool(args.volume) == bool(args.all):
        print("Specify exactly one of --volume or --all", file=sys.stderr)
        return 2

    ids = [args.volume] if args.volume else _volume_ids()
    if not ids:
        print("No volumes found", file=sys.stderr)
        return 1

    rc = 0
    for vid in ids:
        rc = max(
            rc,
            fixup_volume(
                vid,
                pdf=args.pdf if args.volume else None,
                dry_run=args.dry_run,
                sync_output=not args.no_sync_output,
            ),
        )
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
