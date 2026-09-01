"""Canonical Tipiṭaka ``item`` remaps for printed number typos.

Extract stores the number printed in the Roman PDF. When that glyph is
wrong (digit transposition, etc.) the structured ``item`` field must still
be the Tipiṭaka identity — not the edition typo — so citation does not
collide with a real earlier item.

Catalog: ``books/cs-roman/shared/item_corrections.json``.
Applied at extract, JSON fixup, and TeX generate. Do not hand-edit
``segments.json`` ``item`` for this class of defect.

Each rule needs ``from``, ``to``, and ``loci``. A locus requires
``volume`` and at least ``page`` (``order`` optional; ``order`` requires
``page``). Matching starts at the locus, then follows subsequent segments
that still carry ``from`` (skipping itemless headings).
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from paths import BOOKS

SCHEMA_VERSION = 1

SHARED_ITEM_CORRECTIONS_PATH = BOOKS / "shared" / "item_corrections.json"


@dataclass(frozen=True)
class ItemCorrectionLocus:
    volume: str
    page: int
    order: int | None = None


@dataclass(frozen=True)
class ItemCorrectionRule:
    id: str
    enabled: bool
    from_item: int
    to_item: int
    loci: tuple[ItemCorrectionLocus, ...]
    remark: str = ""


def volume_id_from_segments_path(path: Path) -> str | None:
    """Volume folder id from a segments JSON path."""
    name = path.name
    if name.endswith(".segments.json"):
        stem = name[: -len(".segments.json")]
        return stem or None
    if name == "segments.json" and path.parent.name == "data":
        return path.parent.parent.name or None
    return None


def _as_int(value: Any, *, loc: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{loc}: must be an integer")
    return value


def _parse_locus(raw: Any, *, loc: str) -> ItemCorrectionLocus:
    if not isinstance(raw, dict):
        raise ValueError(f"{loc}: locus must be an object")
    volume = str(raw.get("volume") or "").strip()
    if not volume:
        raise ValueError(f"{loc}: volume is required")
    if "page" not in raw:
        raise ValueError(f"{loc}: page is required")
    page = _as_int(raw.get("page"), loc=f"{loc}.page")
    order: int | None = None
    if "order" in raw and raw.get("order") is not None:
        order = _as_int(raw.get("order"), loc=f"{loc}.order")
    unknown = set(raw) - {"volume", "page", "order"}
    if unknown:
        raise ValueError(f"{loc}: unsupported keys: {sorted(unknown)}")
    return ItemCorrectionLocus(volume=volume, page=page, order=order)


def load_item_corrections_file(
    path: Path | None = None,
) -> list[ItemCorrectionRule]:
    p = path or SHARED_ITEM_CORRECTIONS_PATH
    data = json.loads(p.read_text(encoding="utf-8"))
    if int(data.get("schema_version") or 0) != SCHEMA_VERSION:
        raise ValueError(f"{p}: schema_version must be {SCHEMA_VERSION}")
    raw_rules = data.get("rules")
    if not isinstance(raw_rules, list):
        raise ValueError(f"{p}: rules must be a list")
    seen: set[str] = set()
    out: list[ItemCorrectionRule] = []
    for i, raw in enumerate(raw_rules):
        loc = f"{p}: rules[{i}]"
        if not isinstance(raw, dict):
            raise ValueError(f"{loc}: rule must be an object")
        rid = str(raw.get("id") or "").strip()
        if not rid:
            raise ValueError(f"{loc}: id is required")
        if rid in seen:
            raise ValueError(f"{loc}: duplicate id {rid!r}")
        seen.add(rid)
        enabled = raw.get("enabled", True)
        if not isinstance(enabled, bool):
            raise ValueError(f"{loc}: enabled must be a boolean")
        from_item = _as_int(raw.get("from"), loc=f"{loc}.from")
        to_item = _as_int(raw.get("to"), loc=f"{loc}.to")
        if from_item == to_item:
            raise ValueError(f"{loc}: from and to must differ")
        raw_loci = raw.get("loci")
        if not isinstance(raw_loci, list) or not raw_loci:
            raise ValueError(f"{loc}: loci must be a non-empty list")
        loci = tuple(
            _parse_locus(entry, loc=f"{loc}.loci[{j}]")
            for j, entry in enumerate(raw_loci)
        )
        remark = raw.get("remark") or ""
        if remark is not None and not isinstance(remark, str):
            raise ValueError(f"{loc}: remark must be a string")
        unknown = set(raw) - {"id", "enabled", "from", "to", "loci", "remark"}
        if unknown:
            raise ValueError(f"{loc}: unsupported keys: {sorted(unknown)}")
        out.append(
            ItemCorrectionRule(
                id=rid,
                enabled=enabled,
                from_item=from_item,
                to_item=to_item,
                loci=loci,
                remark=str(remark or ""),
            )
        )
    return out


def load_shared_item_corrections() -> list[ItemCorrectionRule]:
    return load_item_corrections_file(SHARED_ITEM_CORRECTIONS_PATH)


def _locus_matches(
    locus: ItemCorrectionLocus,
    *,
    volume_id: str,
    page: int,
    order: int,
) -> bool:
    if locus.volume != volume_id:
        return False
    if locus.page != page:
        return False
    if locus.order is not None and locus.order != order:
        return False
    return True


def _matching_rule(
    rules: Sequence[ItemCorrectionRule],
    seg: dict[str, Any],
    *,
    volume_id: str,
) -> ItemCorrectionRule | None:
    item = seg.get("item")
    if not isinstance(item, int) or isinstance(item, bool):
        return None
    try:
        page = int(seg.get("page") or 0)
        order = int(seg.get("order") or 0)
    except (TypeError, ValueError):
        return None
    for rule in rules:
        if not rule.enabled or item != rule.from_item:
            continue
        if any(
            _locus_matches(loc, volume_id=volume_id, page=page, order=order)
            for loc in rule.loci
        ):
            return rule
    return None


def apply_item_corrections(
    segments: list[Any],
    volume_id: str,
    *,
    rules: Sequence[ItemCorrectionRule] | None = None,
) -> int:
    """Mutate ``item`` in place. Return how many segments changed."""
    if not volume_id or not segments:
        return 0
    catalog = list(rules) if rules is not None else load_shared_item_corrections()
    if not catalog:
        return 0
    changed = 0
    i = 0
    n = len(segments)
    while i < n:
        seg = segments[i]
        if not isinstance(seg, dict):
            i += 1
            continue
        rule = _matching_rule(catalog, seg, volume_id=volume_id)
        if rule is None:
            i += 1
            continue
        old = rule.from_item
        new = rule.to_item
        j = i
        while j < n:
            nxt = segments[j]
            if not isinstance(nxt, dict):
                j += 1
                continue
            item = nxt.get("item")
            if item is None:
                j += 1
                continue
            if item != old:
                break
            nxt["item"] = new
            changed += 1
            j += 1
        i = max(j, i + 1)
    return changed
