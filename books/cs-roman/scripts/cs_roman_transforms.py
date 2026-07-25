"""Publication transform rules for cs-roman (schema_version 1).

Declarative string rules applied at TeX generate time (not baked into
segments.json). Format-contract normalizations (pot-ma-gyi, ``-pa-``,
section-rule underscores) stay hardcoded in ``cs_roman_text``.

  books/cs-roman/shared/transforms.json           # edition-wide
  books/cs-roman/output/<id>.transforms.json      # per-volume (canonical)
  books/cs-roman/volumes/<id>/data/transforms.json  # sync copy
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from paths import BOOKS, OUTPUT_DIR, VOLUMES_DIR

SCHEMA_VERSION = 1

SHARED_TRANSFORMS_PATH = BOOKS / "shared" / "transforms.json"


@dataclass(frozen=True)
class TransformRule:
    """One ordered replace rule with optional segment filters."""

    id: str
    enabled: bool
    pattern: re.Pattern[str]
    replacement: str
    pages: frozenset[int] | None = None
    orders: frozenset[int] | None = None
    segment_types: frozenset[str] | None = None
    match: re.Pattern[str] | None = None


def shared_transforms_path() -> Path:
    return SHARED_TRANSFORMS_PATH


def output_transforms_path(volume_id: str) -> Path:
    return OUTPUT_DIR / f"{volume_id}.transforms.json"


def volume_transforms_path(volume_id: str) -> Path:
    return VOLUMES_DIR / volume_id / "data" / "transforms.json"


def _compile_flags(flags: str) -> int:
    value = 0
    for ch in flags or "":
        if ch == "i":
            value |= re.IGNORECASE
        elif ch == "m":
            value |= re.MULTILINE
        elif ch == "s":
            value |= re.DOTALL
        elif ch in {" ", "\t"}:
            continue
        else:
            raise ValueError(f"Unsupported regex flag {ch!r} (use i, m, s)")
    return value


def _int_set(raw: Any, *, field: str) -> frozenset[int] | None:
    if raw is None:
        return None
    if not isinstance(raw, list):
        raise ValueError(f"when.{field} must be a list of integers")
    out: set[int] = set()
    for item in raw:
        if not isinstance(item, int) or isinstance(item, bool):
            raise ValueError(f"when.{field} entries must be integers")
        out.add(item)
    return frozenset(out)


def _str_set(raw: Any, *, field: str) -> frozenset[str] | None:
    if raw is None:
        return None
    if not isinstance(raw, list):
        raise ValueError(f"when.{field} must be a list of strings")
    out: set[str] = set()
    for item in raw:
        if not isinstance(item, str) or not item:
            raise ValueError(f"when.{field} entries must be non-empty strings")
        out.add(item)
    return frozenset(out)


def parse_transforms_document(data: Any, *, source: str) -> list[TransformRule]:
    """Parse a transforms.json object into ordered rules."""
    if not isinstance(data, dict):
        raise ValueError(f"{source}: root must be an object")
    version = data.get("schema_version")
    if version != SCHEMA_VERSION:
        raise ValueError(
            f"{source}: unsupported schema_version {version!r} "
            f"(expected {SCHEMA_VERSION})"
        )
    raw_rules = data.get("rules")
    if raw_rules is None:
        return []
    if not isinstance(raw_rules, list):
        raise ValueError(f"{source}: rules must be a list")

    rules: list[TransformRule] = []
    seen_ids: set[str] = set()
    for i, raw in enumerate(raw_rules):
        loc = f"{source}: rules[{i}]"
        if not isinstance(raw, dict):
            raise ValueError(f"{loc}: must be an object")
        rule_id = raw.get("id")
        if not isinstance(rule_id, str) or not rule_id.strip():
            raise ValueError(f"{loc}: id must be a non-empty string")
        rule_id = rule_id.strip()
        if rule_id in seen_ids:
            raise ValueError(f"{loc}: duplicate id {rule_id!r}")
        seen_ids.add(rule_id)

        enabled = raw.get("enabled", True)
        if not isinstance(enabled, bool):
            raise ValueError(f"{loc}: enabled must be a boolean")

        when = raw.get("when") or {}
        if not isinstance(when, dict):
            raise ValueError(f"{loc}: when must be an object")

        do = raw.get("do")
        if not isinstance(do, dict) or "replace" not in do:
            raise ValueError(f"{loc}: do.replace is required")
        if set(do) - {"replace"}:
            unknown = ", ".join(sorted(set(do) - {"replace"}))
            raise ValueError(f"{loc}: unsupported do keys: {unknown}")
        repl = do["replace"]
        if not isinstance(repl, dict):
            raise ValueError(f"{loc}: do.replace must be an object")
        pattern = repl.get("pattern")
        replacement = repl.get("with")
        if not isinstance(pattern, str) or pattern == "":
            raise ValueError(f"{loc}: do.replace.pattern must be a non-empty string")
        if not isinstance(replacement, str):
            raise ValueError(f"{loc}: do.replace.with must be a string")
        flag_str = repl.get("flags") or ""
        if not isinstance(flag_str, str):
            raise ValueError(f"{loc}: do.replace.flags must be a string")

        match_raw = when.get("match")
        match_re: re.Pattern[str] | None = None
        if match_raw is not None:
            if not isinstance(match_raw, str) or match_raw == "":
                raise ValueError(f"{loc}: when.match must be a non-empty string")
            match_re = re.compile(match_raw)

        try:
            compiled = re.compile(pattern, _compile_flags(flag_str))
        except re.error as exc:
            raise ValueError(f"{loc}: invalid pattern: {exc}") from exc

        rules.append(
            TransformRule(
                id=rule_id,
                enabled=enabled,
                pattern=compiled,
                replacement=replacement,
                pages=_int_set(when.get("pages"), field="pages"),
                orders=_int_set(when.get("orders"), field="orders"),
                segment_types=_str_set(
                    when.get("segment_types"), field="segment_types"
                ),
                match=match_re,
            )
        )
    return rules


def load_transforms_file(path: Path) -> list[TransformRule]:
    """Load rules from one JSON file; missing file → empty list."""
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return parse_transforms_document(data, source=str(path))


def load_volume_transforms(
    volume_id: str,
    *,
    shared_path: Path | None = None,
    volume_path: Path | None = None,
) -> list[TransformRule]:
    """Load shared rules then per-volume rules (volume path after sync)."""
    shared = load_transforms_file(shared_path or shared_transforms_path())
    volume = load_transforms_file(volume_path or volume_transforms_path(volume_id))
    return [*shared, *volume]


def rule_matches(
    rule: TransformRule,
    text: str,
    *,
    page: int,
    order: int,
    segment_type: str,
) -> bool:
    if not rule.enabled:
        return False
    if rule.pages is not None and page not in rule.pages:
        return False
    if rule.orders is not None and order not in rule.orders:
        return False
    if rule.segment_types is not None and segment_type not in rule.segment_types:
        return False
    if rule.match is not None and rule.match.search(text) is None:
        return False
    return True


def apply_transforms(
    text: str,
    rules: list[TransformRule],
    *,
    page: int,
    order: int,
    segment_type: str,
) -> str:
    """Apply matching rules in order to ``text``; return possibly new string."""
    if not text or not rules:
        return text
    out = text
    for rule in rules:
        if not rule_matches(
            rule, out, page=page, order=order, segment_type=segment_type
        ):
            continue
        out = rule.pattern.sub(rule.replacement, out)
    return out


def segment_context(seg: dict[str, Any]) -> tuple[int, int, str]:
    """``(page, order, segment_type)`` for rule matching."""
    return (
        int(seg.get("page") or 0),
        int(seg.get("order") or 0),
        str(seg.get("segment_type") or "prose"),
    )
