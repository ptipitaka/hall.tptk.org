"""
Extract page 1 from each CTS Roman PDF into website/data/covers/cts-roman-raw/.

Requires Ghostscript (gswin64c) on PATH or at the default Windows install path.
Then run: python scripts/style_cts_roman_covers.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PDF_DIR = ROOT / "archive" / "resourses" / "cs-roman"
RAW_DIR = ROOT / "website" / "data" / "covers" / "cts-roman-raw"

GS_CANDIDATES = [
    "gswin64c",
    "gs",
    r"C:\Program Files\gs\gs10.05.1\bin\gswin64c.exe",
]


def find_gs() -> str:
    for name in GS_CANDIDATES:
        which = shutil.which(name)
        if which:
            return which
        if Path(name).is_file():
            return name
    raise SystemExit("Ghostscript not found (gswin64c / gs).")


def main() -> None:
    gs = find_gs()
    pdfs = sorted(PDF_DIR.glob("*.pdf"))
    if not pdfs:
        raise SystemExit(f"No PDFs in {PDF_DIR}")
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for i, pdf in enumerate(pdfs, 1):
        out = RAW_DIR / f"{pdf.stem}.jpg"
        cmd = [
            gs,
            "-dSAFER",
            "-dBATCH",
            "-dNOPAUSE",
            "-dQUIET",
            "-sDEVICE=jpeg",
            "-dJPEGQ=92",
            "-r200",
            "-dFirstPage=1",
            "-dLastPage=1",
            f"-sOutputFile={out}",
            str(pdf),
        ]
        subprocess.run(cmd, check=True)
        print(f"  [{i}/{len(pdfs)}] {pdf.name}", file=sys.stderr)
    print(f"Wrote {len(pdfs)} pages to {RAW_DIR}")


if __name__ == "__main__":
    main()
