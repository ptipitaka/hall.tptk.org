"""Download and extract Digital Pāḷi Dictionary SQLite (dpd.db) for local use.

Usage:
  python books/cs-roman/scripts/fetch_dpd_db.py
  python books/cs-roman/scripts/fetch_dpd_db.py --tag v0.4.20260728
"""

from __future__ import annotations

import argparse
import json
import ssl
import tarfile
import urllib.error
import urllib.request
from pathlib import Path

from paths import BOOKS

VENDOR = BOOKS / "vendor" / "dpd"
DEFAULT_TAG = "v0.4.20260728"
ASSET_NAME = "dpd.db.tar.xz"
API_LATEST = "https://api.github.com/repos/digitalpalidictionary/dpd-db/releases/latest"
API_TAG = (
    "https://api.github.com/repos/digitalpalidictionary/dpd-db/releases/tags/{tag}"
)


def _ssl_context() -> ssl.SSLContext:
    """Prefer system certs; fall back to unverified if local certs are stale."""
    try:
        ctx = ssl.create_default_context()
        # Probe by creating the context only; download will raise if needed.
        return ctx
    except ssl.SSLError:
        return ssl._create_unverified_context()


def _urlopen(url: str, timeout: int = 120):
    ctx = _ssl_context()
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "hall.tptk.org-cs-roman/1.0"},
    )
    try:
        return urllib.request.urlopen(req, timeout=timeout, context=ctx)
    except urllib.error.URLError:
        # Common on some Windows installs with expired local CA store.
        ctx = ssl._create_unverified_context()
        return urllib.request.urlopen(req, timeout=timeout, context=ctx)


def resolve_asset_url(tag: str | None) -> tuple[str, str]:
    """Return (tag, browser_download_url) for dpd.db.tar.xz."""
    if tag:
        meta_url = API_TAG.format(tag=tag)
    else:
        meta_url = API_LATEST
    with _urlopen(meta_url) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    resolved_tag = str(data.get("tag_name") or tag or "unknown")
    for asset in data.get("assets") or []:
        name = str(asset.get("name") or "")
        if name == ASSET_NAME or (
            name.startswith("dpd.db.tar.") and name.endswith((".xz", ".bz2", ".gz"))
        ):
            url = asset.get("browser_download_url")
            if url:
                return resolved_tag, str(url)
    raise RuntimeError(
        f"No dpd.db archive asset found in release {resolved_tag}"
    )


def fetch_and_extract(*, tag: str | None, force: bool) -> Path:
    VENDOR.mkdir(parents=True, exist_ok=True)
    db_path = VENDOR / "dpd.db"
    if db_path.is_file() and not force:
        print(f"already present: {db_path} ({db_path.stat().st_size} bytes)")
        return db_path

    resolved_tag, url = resolve_asset_url(tag)
    archive_name = url.rsplit("/", 1)[-1]
    archive_path = VENDOR / archive_name
    print(f"downloading {resolved_tag} → {archive_path}")
    with _urlopen(url, timeout=600) as resp:
        archive_path.write_bytes(resp.read())
    print(f"wrote {archive_path.stat().st_size} bytes")

    mode = "r:xz"
    if archive_name.endswith(".bz2"):
        mode = "r:bz2"
    elif archive_name.endswith(".gz"):
        mode = "r:gz"
    print(f"extracting {archive_path} …")
    with tarfile.open(archive_path, mode) as tar:
        tar.extractall(VENDOR)
    if not db_path.is_file():
        raise RuntimeError(f"extract finished but missing {db_path}")
    # Quick sanity: lookup table exists.
    import sqlite3

    con = sqlite3.connect(f"file:{db_path.resolve().as_posix()}?mode=ro", uri=True)
    try:
        n = con.execute(
            "SELECT COUNT(*) FROM lookup WHERE deconstructor != ''"
        ).fetchone()[0]
    finally:
        con.close()
    print(f"ok: {db_path} ({db_path.stat().st_size} bytes); "
          f"deconstructor rows ≈ {n}")
    meta = {
        "tag": resolved_tag,
        "asset": archive_name,
        "url": url,
        "deconstructor_rows": n,
    }
    (VENDOR / "SOURCE.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return db_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tag",
        default=DEFAULT_TAG,
        help=f"GitHub release tag (default: {DEFAULT_TAG})",
    )
    parser.add_argument(
        "--latest",
        action="store_true",
        help="use the latest GitHub release instead of --tag",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="re-download even when dpd.db already exists",
    )
    args = parser.parse_args()
    tag = None if args.latest else args.tag
    fetch_and_extract(tag=tag, force=args.force)


if __name__ == "__main__":
    main()
