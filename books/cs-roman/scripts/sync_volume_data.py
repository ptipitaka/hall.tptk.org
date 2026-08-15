#!/usr/bin/env python3
"""Sync PDF + segments/layout JSON into books/cs-roman/volumes/<id>/."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

from paths import BOOKS, OUTPUT_DIR, SOURCE_DIR

PDF_DIR = SOURCE_DIR
JSON_DIR = OUTPUT_DIR


def _same_file(a: Path, b: Path) -> bool:
    try:
        return os.path.samefile(a, b)
    except OSError:
        return False


def _ensure_pdf(pdf_src: Path, pdf_dst: Path, *, copy_pdf: bool) -> None:
    if pdf_dst.exists() or pdf_dst.is_symlink():
        if not copy_pdf and _same_file(pdf_src, pdf_dst):
            return
        try:
            pdf_dst.unlink()
        except OSError:
            # Docker/Windows bind mounts can refuse unlinking an existing hardlink.
            # Fall back to leaving the destination when it already matches source.
            if _same_file(pdf_src, pdf_dst) or (
                pdf_dst.is_file() and pdf_dst.stat().st_size == pdf_src.stat().st_size
            ):
                return
            raise
    if copy_pdf:
        shutil.copy2(pdf_src, pdf_dst)
        return
    try:
        pdf_dst.hardlink_to(pdf_src)
    except OSError:
        shutil.copy2(pdf_src, pdf_dst)


def sync_volume(volume_id: str, *, copy_pdf: bool = False) -> Path:
    vol = BOOKS / "volumes" / volume_id
    source = vol / "source"
    data = vol / "data"
    tex = vol / "tex"
    out = vol / "out"
    for d in (source, data, tex, out):
        d.mkdir(parents=True, exist_ok=True)

    pdf_src = PDF_DIR / f"{volume_id}.pdf"
    pdf_dst = source / f"{volume_id}.pdf"
    if not pdf_src.is_file():
        raise FileNotFoundError(f"Missing PDF: {pdf_src}")
    _ensure_pdf(pdf_src, pdf_dst, copy_pdf=copy_pdf)

    json_src = JSON_DIR / f"{volume_id}.segments.json"
    json_dst = data / "segments.json"
    if not json_src.is_file():
        raise FileNotFoundError(f"Missing segments JSON: {json_src}")
    _copy_replace(json_src, json_dst)

    layout_src = JSON_DIR / f"{volume_id}.layout.json"
    layout_dst = data / "layout.json"
    if layout_src.is_file():
        _copy_replace(layout_src, layout_dst)
    elif layout_dst.is_file():
        # Keep an existing volume layout if canonical output has not been split yet.
        pass
    else:
        raise FileNotFoundError(f"Missing layout JSON: {layout_src}")

    sync_optional_json(
        JSON_DIR / f"{volume_id}.matika.json",
        data / "matika.json",
    )
    stale_transforms = data / "transforms.json"
    if stale_transforms.is_file():
        stale_transforms.unlink()
    return vol


def _copy_replace(src: Path, dst: Path) -> None:
    """Copy ``src`` → ``dst``, tolerating Windows bind-mount replace quirks."""
    try:
        shutil.copy2(src, dst)
        return
    except OSError:
        pass
    tmp = dst.with_suffix(dst.suffix + ".tmp")
    try:
        shutil.copy2(src, tmp)
        tmp.replace(dst)
    finally:
        if tmp.is_file():
            try:
                tmp.unlink()
            except OSError:
                pass


def sync_optional_json(src: Path, dst: Path) -> None:
    """Copy optional JSON, or remove a stale volume copy."""
    if src.is_file():
        shutil.copy2(src, dst)
    elif dst.is_file():
        dst.unlink()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--volume", default="01Vin01")
    parser.add_argument(
        "--copy-pdf",
        action="store_true",
        help="Copy PDF instead of hardlinking",
    )
    args = parser.parse_args(argv)
    vol = sync_volume(args.volume, copy_pdf=args.copy_pdf)
    print(f"Synced -> {vol}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
