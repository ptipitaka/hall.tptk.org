"""Publication transform rules for cs-roman (schema_version 2).

Declarative string rules applied at TeX generate time (not baked into
segments.json). Format-contract normalizations (pot-ma-gyi, ``-pa-``,
section-rule underscores) stay hardcoded in ``cs_roman_text``.

  books/cs-roman/shared/transforms.json           # edition-wide
  books/cs-roman/output/<id>.transforms.json      # per-volume (canonical)
  books/cs-roman/volumes/<id>/data/transforms.json  # sync copy

Actions (exactly one per rule):

- ``annotate`` — keep edition ``when.match``, inject numbered footnote
  (Burmese/source reading wrong; do not silently “fix” the Roman).
- ``replace`` — substitute ``with`` for ``when.match``, no PDF footnote
  (Roman wrong vs Burmese; ``remark`` is editor documentation only).

Optional ``soft_breaks`` on either action merges into the sandhi break map
at generate (keyed by the surface form present after the rule).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from paths import BOOKS, OUTPUT_DIR, VOLUMES_DIR

SCHEMA_VERSION = 2

SHARED_TRANSFORMS_PATH = BOOKS / "shared" / "transforms.json"

TransformAction = Literal["annotate", "replace"]


@dataclass(frozen=True)
class TransformRule:
    """One ordered annotate or replace rule with optional segment filters."""

    id: str
    enabled: bool
    action: TransformAction
    match: str
    pages: frozenset[int] | None = None
    orders: frozenset[int] | None = None
    segment_types: frozenset[str] | None = None
    footnote: str | None = None
    replacement: str | None = None
    remark: str | None = None
    soft_breaks: tuple[str, ...] | None = None


def shared_transforms_path() -> Path:
    return SHARED_TRANSFORMS_PATH


def output_transforms_path(volume_id: str) -> Path:
    return OUTPUT_DIR / f"{volume_id}.transforms.json"


def volume_transforms_path(volume_id: str) -> Path:
    return VOLUMES_DIR / volume_id / "data" / "transforms.json"


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


def _parse_soft_breaks(
    raw: Any,
    *,
    surface: str,
    loc: str,
    field: str,
) -> tuple[str, ...] | None:
    if raw is None:
        return None
    if not isinstance(raw, list) or len(raw) < 2:
        raise ValueError(f"{loc}: {field} must be a list of at least 2 strings")
    parts: list[str] = []
    for item in raw:
        if not isinstance(item, str) or not item:
            raise ValueError(f"{loc}: {field} entries must be non-empty strings")
        parts.append(item)
    if "".join(parts) != surface:
        raise ValueError(
            f"{loc}: {field} parts must concatenate to {surface!r} "
            f"(got {''.join(parts)!r})"
        )
    return tuple(parts)


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
        match_raw = when.get("match")
        if not isinstance(match_raw, str) or match_raw == "":
            raise ValueError(f"{loc}: when.match must be a non-empty string")
        match = match_raw

        do = raw.get("do")
        if not isinstance(do, dict):
            raise ValueError(f"{loc}: do must be an object")
        actions = set(do) & {"annotate", "replace"}
        if len(actions) != 1:
            raise ValueError(
                f"{loc}: do must contain exactly one of annotate, replace"
            )
        unknown_do = set(do) - {"annotate", "replace"}
        if unknown_do:
            unknown = ", ".join(sorted(unknown_do))
            raise ValueError(f"{loc}: unsupported do keys: {unknown}")

        footnote: str | None = None
        replacement: str | None = None
        remark: str | None = None
        soft_breaks: tuple[str, ...] | None = None

        if "annotate" in do:
            action: TransformAction = "annotate"
            ann = do["annotate"]
            if not isinstance(ann, dict):
                raise ValueError(f"{loc}: do.annotate must be an object")
            allowed = {"footnote", "soft_breaks"}
            if set(ann) - allowed:
                unknown = ", ".join(sorted(set(ann) - allowed))
                raise ValueError(f"{loc}: unsupported do.annotate keys: {unknown}")
            footnote_raw = ann.get("footnote")
            if not isinstance(footnote_raw, str) or footnote_raw == "":
                raise ValueError(
                    f"{loc}: do.annotate.footnote must be a non-empty string"
                )
            footnote = footnote_raw
            soft_breaks = _parse_soft_breaks(
                ann.get("soft_breaks"),
                surface=match,
                loc=loc,
                field="do.annotate.soft_breaks",
            )
        else:
            action = "replace"
            repl = do["replace"]
            if not isinstance(repl, dict):
                raise ValueError(f"{loc}: do.replace must be an object")
            allowed = {"with", "remark", "soft_breaks"}
            if set(repl) - allowed:
                unknown = ", ".join(sorted(set(repl) - allowed))
                raise ValueError(f"{loc}: unsupported do.replace keys: {unknown}")
            with_raw = repl.get("with")
            if not isinstance(with_raw, str) or with_raw == "":
                raise ValueError(f"{loc}: do.replace.with must be a non-empty string")
            replacement = with_raw
            remark_raw = repl.get("remark")
            if remark_raw is not None:
                if not isinstance(remark_raw, str):
                    raise ValueError(f"{loc}: do.replace.remark must be a string")
                remark = remark_raw
            soft_breaks = _parse_soft_breaks(
                repl.get("soft_breaks"),
                surface=replacement,
                loc=loc,
                field="do.replace.soft_breaks",
            )

        rules.append(
            TransformRule(
                id=rule_id,
                enabled=enabled,
                action=action,
                match=match,
                pages=_int_set(when.get("pages"), field="pages"),
                orders=_int_set(when.get("orders"), field="orders"),
                segment_types=_str_set(
                    when.get("segment_types"), field="segment_types"
                ),
                footnote=footnote,
                replacement=replacement,
                remark=remark,
                soft_breaks=soft_breaks,
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


def collect_transform_soft_breaks(
    rules: list[TransformRule],
) -> dict[str, list[str]]:
    """Roman surface → soft-break parts from enabled rules (later wins)."""
    out: dict[str, list[str]] = {}
    for rule in rules:
        if not rule.enabled or not rule.soft_breaks:
            continue
        if rule.action == "annotate":
            key = rule.match
        else:
            assert rule.replacement is not None
            key = rule.replacement
        out[key] = list(rule.soft_breaks)
    return out


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
    if rule.match not in text:
        return False
    return True


def _literal_sub(
    text: str,
    needle: str,
    *,
    replacer,
) -> str:
    """Replace every non-overlapping occurrence of ``needle`` via ``replacer``."""
    if not needle or needle not in text:
        return text
    parts: list[str] = []
    start = 0
    while True:
        idx = text.find(needle, start)
        if idx < 0:
            parts.append(text[start:])
            break
        parts.append(text[start:idx])
        parts.append(replacer(needle))
        start = idx + len(needle)
    return "".join(parts)


def apply_transforms(
    text: str,
    rules: list[TransformRule],
    *,
    page: int,
    order: int,
    segment_type: str,
    note_base_index: int = 0,
    emit_footnotes: bool = True,
) -> tuple[str, list[str]]:
    """Apply matching rules in order; return ``(text, extra_note_bodies)``.

    ``annotate`` keeps ``match`` and (when ``emit_footnotes``) appends
    ``{{nN}}`` after each hit, collecting footnote bodies.

    ``replace`` substitutes ``with`` for ``match`` and never emits notes
    (``remark`` is ignored at generate).

    When ``emit_footnotes`` is false (e.g. transforming note bodies),
    annotate leaves text unchanged; replace still applies.
    """
    if not text or not rules:
        return text, []
    out = text
    extra: list[str] = []
    for rule in rules:
        if not rule_matches(
            rule, out, page=page, order=order, segment_type=segment_type
        ):
            continue
        if rule.action == "replace":
            assert rule.replacement is not None
            out = out.replace(rule.match, rule.replacement)
            continue
        # annotate
        if not emit_footnotes:
            continue
        footnote_body = rule.footnote
        assert footnote_body is not None

        def _annotate_hit(
            matched: str,
            *,
            _body: str = footnote_body,
        ) -> str:
            idx = note_base_index + len(extra)
            extra.append(_body)
            return f"{matched}{{{{n{idx}}}}}"

        out = _literal_sub(out, rule.match, replacer=_annotate_hit)
    return out, extra


def segment_context(seg: dict[str, Any]) -> tuple[int, int, str]:
    """``(page, order, segment_type)`` for rule matching."""
    return (
        int(seg.get("page") or 0),
        int(seg.get("order") or 0),
        str(seg.get("segment_type") or "prose"),
    )
