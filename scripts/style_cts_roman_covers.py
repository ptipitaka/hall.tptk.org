"""
Turn CTS Roman Tipiṭaka title pages into maroon/gold book-cover images.

Input:  website/data/covers/cts-roman-raw/<stem>.jpg  (PDF page 1 renders)
Output: website/data/covers/cts-roman/<NN>-<stem>.jpg
        website/data/covers/cts-roman.jpg  (vol. 01 edition cover)
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "website" / "data" / "covers" / "cts-roman-raw"
OUT_DIR = ROOT / "website" / "data" / "covers" / "cts-roman"
EDITION_COVER = ROOT / "website" / "data" / "covers" / "cts-roman.jpg"

OUT_W, OUT_H = 1320, 1900

BG_RGB = np.array([92, 18, 22], dtype=np.float32)
GOLD_RGB = np.array([212, 175, 85], dtype=np.float32)
GOLD_HI = np.array([236, 210, 130], dtype=np.float32)
FRAME_RGB = (198, 160, 72)


def _leather_texture(w: int, h: int, seed: int = 42) -> np.ndarray:
    rng = np.random.default_rng(seed)
    noise = rng.normal(0.0, 1.0, (h, w)).astype(np.float32)
    tex = Image.fromarray(
        ((noise - noise.min()) / (np.ptp(noise) + 1e-6) * 255).astype(np.uint8), "L"
    )
    tex = tex.filter(ImageFilter.GaussianBlur(radius=1.2))
    fine = Image.fromarray((rng.random((h, w)) * 255).astype(np.uint8), "L").filter(
        ImageFilter.GaussianBlur(radius=0.4)
    )
    mixed = Image.blend(tex, fine, 0.35)
    arr = np.asarray(mixed, dtype=np.float32) / 255.0
    return (arr - 0.5) * 0.14


def _vignette(w: int, h: int, strength: float = 0.22) -> np.ndarray:
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    cx, cy = (w - 1) / 2.0, (h - 1) / 2.0
    rx, ry = w * 0.65, h * 0.65
    d = np.sqrt(((xs - cx) / rx) ** 2 + ((ys - cy) / ry) ** 2)
    return np.clip(1.0 - strength * np.clip(d - 0.55, 0, None) ** 1.4, 0.78, 1.0)


def _maroon_board(w: int, h: int, seed: int) -> Image.Image:
    tex = _leather_texture(w, h, seed=seed)
    vig = _vignette(w, h)[..., None]
    bg = (BG_RGB + tex[..., None] * 255.0 * 0.35) * vig
    return Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8), "RGB")


def _colorize_title_page(page: Image.Image) -> Image.Image:
    """Map black-on-white title page → gold ink on maroon (RGBA)."""
    rgb = np.asarray(page.convert("RGB"), dtype=np.float32)
    lum = 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]
    # Paper is near-white; ink is dark. Ignore mid-tones from JPEG noise.
    ink = np.clip((220.0 - lum) / 200.0, 0.0, 1.0)
    ink = np.where(ink < 0.08, 0.0, ink)
    ink = np.power(ink, 0.9)
    ink_img = Image.fromarray((ink * 255).astype(np.uint8), "L").filter(
        ImageFilter.GaussianBlur(radius=0.3)
    )
    ink = np.asarray(ink_img, dtype=np.float32) / 255.0

    gold = GOLD_RGB[None, None, :] * (0.85 + 0.30 * ink[..., None])
    gold = gold + (GOLD_HI - GOLD_RGB)[None, None, :] * (ink[..., None] ** 2) * 0.4
    # Transparent where paper was (composited onto leather board).
    rgba = np.zeros((page.height, page.width, 4), dtype=np.float32)
    rgba[..., :3] = gold
    rgba[..., 3] = ink * 255.0
    return Image.fromarray(np.clip(rgba, 0, 255).astype(np.uint8), "RGBA")


def style_cover(src: Path, dst: Path) -> None:
    page = Image.open(src).convert("RGB")
    gray = ImageOps.invert(ImageOps.grayscale(page))
    bbox = gray.getbbox()
    if bbox:
        pad = int(min(page.size) * 0.07)
        l, t, r, b = bbox
        page = page.crop(
            (
                max(0, l - pad),
                max(0, t - pad),
                min(page.width, r + pad),
                min(page.height, b + pad),
            )
        )

    page.thumbnail((int(OUT_W * 0.86), int(OUT_H * 0.90)), Image.Resampling.LANCZOS)
    foil = _colorize_title_page(page)

    cover = _maroon_board(OUT_W, OUT_H, seed=hash(src.name) % 10_000)
    ox = (OUT_W - foil.width) // 2
    oy = (OUT_H - foil.height) // 2
    cover = cover.convert("RGBA")
    cover.alpha_composite(foil, (ox, oy))
    cover = cover.convert("RGB")

    draw = ImageDraw.Draw(cover)
    margin = 38
    for inset, width in ((0, 3), (10, 1)):
        m = margin + inset
        draw.rectangle(
            [m, m, OUT_W - 1 - m, OUT_H - 1 - m],
            outline=FRAME_RGB,
            width=width,
        )

    shade = Image.new("L", (OUT_W, OUT_H), 0)
    sdraw = ImageDraw.Draw(shade)
    for i, a in enumerate(range(50, 0, -3)):
        sdraw.rectangle([0, 0, 16 + i, OUT_H], fill=a)
    shade = shade.filter(ImageFilter.GaussianBlur(radius=6))
    cover = Image.composite(
        ImageEnhance.Brightness(cover).enhance(0.84),
        cover,
        shade,
    )

    cover = ImageEnhance.Contrast(cover).enhance(1.05)
    cover = ImageEnhance.Color(cover).enhance(1.06)
    dst.parent.mkdir(parents=True, exist_ok=True)
    cover.save(dst, "JPEG", quality=92, optimize=True)


def main() -> None:
    files = sorted(
        p for p in RAW_DIR.glob("*.jpg") if not re.search(r"-p\d+\.jpg$", p.name)
    )
    if not files:
        raise SystemExit(f"No raw pages in {RAW_DIR}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for path in files:
        m = re.match(r"^(\d+)", path.stem)
        if not m:
            continue
        nn = int(m.group(1))
        out = OUT_DIR / f"{nn:02d}-{path.stem}.jpg"
        style_cover(path, out)
        written.append(out)
        print(f"  {path.name} -> {out.name}")

    first = next(p for p in written if p.name.startswith("01-"))
    Image.open(first).save(EDITION_COVER, "JPEG", quality=92, optimize=True)
    print(f"Edition cover: {EDITION_COVER.name} ({len(written)} volumes)")


if __name__ == "__main__":
    main()
