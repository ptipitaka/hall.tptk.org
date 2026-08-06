#!/usr/bin/env python3
"""Scaffold, sync, and generate TeX for every cs-roman volume.

Creates volumes/<id>/tex/main.tex and main.printing.tex;
copies segments.json + layout.json (+ matika/transforms when present); and
writes body.generated.tex / body.printing.generated.tex. Does not run latexmk
(use build.ps1 / batch_build).

Example:
  python books/cs-roman/scripts/batch_prepare_volumes.py
  python books/cs-roman/scripts/batch_prepare_volumes.py --volume 01Vin01
  python books/cs-roman/scripts/batch_prepare_volumes.py --mode printing
  python books/cs-roman/scripts/batch_prepare_volumes.py --mode both
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from paths import BOOKS, OUTPUT_DIR, ensure_import_paths

ensure_import_paths()

JSON_DIR = OUTPUT_DIR

from generate_cs_roman_tex import generate  # noqa: E402
from sync_volume_data import sync_volume  # noqa: E402

_GENERATE_MODES = ("sync", "printing")

_MAIN_TEX = """\
% !TeX program = lualatex
% !TeX root = main.tex
% CS Roman Thai Tipiṭaka text — {volume_id}
\\documentclass[11pt,twoside,openany]{{memoir}}

\\input{{shared/style/preamble}}

\\begin{{document}}
% Front: Mātikā from segments with in_toc (page numbers = body printed pages).
\\pagestyle{{plain}}
\\pagenumbering{{roman}}
% babel-thai may reset \\contentsname — set immediately before use.
\\renewcommand{{\\contentsname}}{{มาติกา}}
\\tableofcontents*
% Body must open on a recto (right-hand / odd) page.
\\cleardoublepage
% Body resets arabic page 1 at Namo / content start (see body.generated).
\\pagenumbering{{arabic}}
\\pagestyle{{plain}}
\\input{{volumes/{volume_id}/tex/body.generated}}
\\end{{document}}
"""

_MAIN_PRINTING_TEX = """\
% !TeX program = lualatex
% !TeX root = main.printing.tex
% CS Roman Thai Tipiṭaka — {volume_id} (printing: reading flow at 165×230 mm)
\\documentclass[11pt,twoside,openany]{{memoir}}

% Trim 165×230 mm; lengths scaled from reading by 165mm/499bp.
\\def\\csromanuseprintinggeometry{{1}}
\\input{{shared/style/preamble}}

\\begin{{document}}
% Front: Mātikā from segments with in_toc (page numbers = physical body pages).
\\pagestyle{{plain}}
\\pagenumbering{{roman}}
% babel-thai may reset \\contentsname — set immediately before use.
\\renewcommand{{\\contentsname}}{{มาติกา}}
\\tableofcontents*
% Body must open on a recto (right-hand / odd) page.
\\cleardoublepage
\\pagenumbering{{arabic}}
\\pagestyle{{plain}}
\\input{{volumes/{volume_id}/tex/body.printing.generated}}
\\end{{document}}
"""


def ensure_main_tex(volume_id: str) -> Path:
    tex_dir = BOOKS / "volumes" / volume_id / "tex"
    tex_dir.mkdir(parents=True, exist_ok=True)
    main = tex_dir / "main.tex"
    main.write_text(_MAIN_TEX.format(volume_id=volume_id), encoding="utf-8")
    return main


def ensure_main_printing_tex(volume_id: str) -> Path:
    tex_dir = BOOKS / "volumes" / volume_id / "tex"
    tex_dir.mkdir(parents=True, exist_ok=True)
    main = tex_dir / "main.printing.tex"
    main.write_text(_MAIN_PRINTING_TEX.format(volume_id=volume_id), encoding="utf-8")
    return main


def volume_ids_from_json() -> list[str]:
    return sorted(
        p.name.replace(".segments.json", "")
        for p in JSON_DIR.glob("*.segments.json")
    )


def _modes_from_arg(mode: str) -> tuple[str, ...]:
    if mode == "both":
        return _GENERATE_MODES
    if mode in _GENERATE_MODES:
        return (mode,)
    raise ValueError(
        f"mode must be sync, printing, or both; got {mode!r}"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--volume",
        action="append",
        dest="volumes",
        help="Process only this volume id (repeatable). Default: all JSON volumes.",
    )
    parser.add_argument(
        "--mode",
        choices=("sync", "printing", "both"),
        default="both",
        help=(
            "Which body TeX to generate (default: both = sync+printing)."
        ),
    )
    parser.add_argument(
        "--copy-pdf",
        action="store_true",
        help="Copy PDF instead of hardlinking when syncing",
    )
    args = parser.parse_args(argv)

    volumes = args.volumes or volume_ids_from_json()
    if not volumes:
        print(f"No volumes found under {JSON_DIR}", file=sys.stderr)
        return 1

    modes = _modes_from_arg(args.mode)
    ok = 0
    failures: list[str] = []
    for volume_id in volumes:
        try:
            ensure_main_tex(volume_id)
            ensure_main_printing_tex(volume_id)
            sync_volume(volume_id, copy_pdf=args.copy_pdf)
            outs: list[str] = []
            for mode in modes:
                out = generate(volume_id, mode=mode)
                outs.append(str(out))
            print(f"OK {volume_id} -> {', '.join(outs)}")
            ok += 1
        except Exception as exc:  # noqa: BLE001 — batch continues
            print(f"FAIL {volume_id}: {exc}", file=sys.stderr)
            failures.append(volume_id)

    print(f"Done: {ok} ok, {len(failures)} failed")
    if failures:
        print("Failed:", ", ".join(failures), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
