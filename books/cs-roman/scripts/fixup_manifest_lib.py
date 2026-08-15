"""Load/validate CS Roman fixup manifest and parse residual counts."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from paths import BOOKS, SCRIPTS_DIR, VOLUMES_DIR

MANIFEST_PATH = SCRIPTS_DIR / "fixup_manifest.json"
PROCESS_DOC = BOOKS / "docs" / "fixup_process.md"

_GATES = frozenset({"strict", "warn", "off"})
_SCOPES = frozenset({"all", "per_volume"})

# Last-line / footer patterns used by fixup scripts (--dry-run).
_RESIDUAL_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"total:\s*peeled=(\d+)\s+cleared_center=(\d+)\s+fixed_item=(\d+)\s+"
        r"dropped_titles=(\d+)\s+cont\+=(\d+)",
        re.I,
    ),
    re.compile(
        r":\s*demoted=\d+\s+upgraded=\d+\s+changed=(\d+)\s*$",
        re.I | re.M,
    ),
    re.compile(r"^(\d+)/\d+\s+file\(s\)", re.I | re.M),
    re.compile(r"Done:\s*(\d+)", re.I),
    re.compile(r"Done\s*\((\d+)\s+", re.I),
    re.compile(r"total segments touched:\s*(\d+)", re.I),
    re.compile(r"total repaired:\s*(\d+)", re.I),
    re.compile(r"total replaced:\s*(\d+)", re.I),
    re.compile(r"total bound:\s*(\d+)", re.I),
    re.compile(r"^total:\s*(\d+)\s*$", re.I | re.M),
    re.compile(r"Total peeled headings:\s*(\d+)", re.I),
    re.compile(r"Total repaired joins:\s*(\d+)", re.I),
)


def load_manifest(path: Path | None = None) -> dict[str, Any]:
    p = path or MANIFEST_PATH
    data = json.loads(p.read_text(encoding="utf-8"))
    validate_manifest(data, path=p)
    return data


def validate_manifest(data: dict[str, Any], *, path: Path | None = None) -> None:
    if int(data.get("version") or 0) < 1:
        raise ValueError(f"{path}: manifest version must be >= 1")
    fixups = data.get("fixups")
    if not isinstance(fixups, list) or not fixups:
        raise ValueError(f"{path}: fixups must be a non-empty list")
    seen: set[str] = set()
    ids = {str(f.get("id")) for f in fixups if isinstance(f, dict)}
    for entry in fixups:
        if not isinstance(entry, dict):
            raise ValueError(f"{path}: fixup entry must be object")
        fid = str(entry.get("id") or "").strip()
        if not fid:
            raise ValueError(f"{path}: fixup missing id")
        if fid in seen:
            raise ValueError(f"{path}: duplicate fixup id {fid!r}")
        seen.add(fid)
        script = str(entry.get("script") or "").strip()
        if not script.endswith(".py"):
            raise ValueError(f"{path}: {fid}: script must be a .py file")
        if not (SCRIPTS_DIR / script).is_file():
            raise ValueError(f"{path}: {fid}: missing script {script}")
        gate = str(entry.get("gate") or "off")
        if gate not in _GATES:
            raise ValueError(f"{path}: {fid}: gate must be one of {sorted(_GATES)}")
        scope = str(entry.get("scope") or "all")
        if scope not in _SCOPES:
            raise ValueError(f"{path}: {fid}: scope must be one of {sorted(_SCOPES)}")
        for fu in entry.get("follow_ups") or []:
            if str(fu) not in ids:
                raise ValueError(f"{path}: {fid}: unknown follow_up {fu!r}")
    audits = data.get("post_pdf_audits") or []
    if not isinstance(audits, list):
        raise ValueError(f"{path}: post_pdf_audits must be a list")
    for entry in audits:
        if not isinstance(entry, dict):
            raise ValueError(f"{path}: audit entry must be object")
        script = str(entry.get("script") or "")
        if script and not (SCRIPTS_DIR / script).is_file():
            raise ValueError(f"{path}: audit missing script {script}")


def pipeline_fixups(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    return [f for f in manifest["fixups"] if f.get("pipeline")]


def gated_fixups(
    manifest: dict[str, Any], *, levels: set[str] | None = None
) -> list[dict[str, Any]]:
    want = levels or {"strict"}
    return [f for f in manifest["fixups"] if str(f.get("gate") or "off") in want]


def list_volume_ids() -> list[str]:
    out: list[str] = []
    if not VOLUMES_DIR.is_dir():
        return out
    for p in sorted(VOLUMES_DIR.iterdir()):
        if p.name.startswith("_"):
            continue
        if (p / "data" / "segments.json").is_file():
            out.append(p.name)
    return out


def parse_residual_count(stdout: str) -> int | None:
    """Return residual change count from fixup script stdout, or None if unknown."""
    text = stdout or ""
    # Prefer multi-metric totals (sum components).
    for pat in _RESIDUAL_PATTERNS[:2]:
        matches = list(pat.finditer(text))
        if matches:
            m = matches[-1]
            return sum(int(g) for g in m.groups())
    for pat in _RESIDUAL_PATTERNS[2:]:
        matches = list(pat.finditer(text))
        if matches:
            return int(matches[-1].group(1))
    return None


def script_argv(
    entry: dict[str, Any],
    *,
    volume: str | None,
    dry_run: bool,
) -> list[str]:
    """Build argv (script path relative to repo) for one fixup invocation."""
    script = str(entry["script"])
    rel = f"books/cs-roman/scripts/{script}"
    argv = [rel]
    scope = str(entry.get("scope") or "all")
    if scope == "per_volume":
        if not volume:
            raise ValueError(f"{entry['id']}: per_volume scope requires --volume")
        argv.extend(["--volume", volume])
    elif volume:
        argv.extend(["--volume", volume])
    else:
        argv.append("--all")
    if dry_run:
        argv.append("--dry-run")
    return argv
