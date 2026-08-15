"""Publication transform rules for cs-roman (schema_version 2).

Declarative string rules applied at TeX generate time (not baked into
segments.json). Format-contract normalizations (pot-ma-gyi, ``-pa-``,
section-rule underscores) stay hardcoded in ``cs_roman_text``.

  books/cs-roman/shared/transforms.json           # sole catalog

Actions (exactly one per rule):

- ``annotate`` — keep edition ``when.match``, inject numbered footnote
  (Burmese/source reading wrong; do not silently “fix” the Roman).
- ``replace`` — substitute ``with`` for ``when.match``, no PDF footnote
  (Roman wrong vs Burmese; ``remark`` is editor documentation only).
- ``unbold`` — keep ``when.match``; clear bold on that span in ``runs``
  (Roman stroke/weight wrong vs Burmese). Optional ``skip`` leaves a
  prefix of the match bold (e.g. ``”`` in ``”ti``).

Catalog ``replace`` / ``annotate`` set ``when.token`` to ``true`` (letter
boundaries: ``bandhiṃ`` does not hit ``bandhiṃsu``). ``unbold`` of a glued
quote-iti uses ``token: false`` because ``”`` is not a letter-run.
The parser still defaults ``token`` to ``false`` for tests. Optional
``when.volumes`` pins a rule to volume folder ids (``01Vin01``); generate
drops it for other books. Optional ``soft_breaks`` on either action merges
into the sandhi break map at generate (keyed by the surface form present
after the rule).

Generate compiles a letter-run index (``compile_transforms``) so apply is
O(tokens in the segment), not O(rules × segments). File order is unchanged.

``when.match`` is compared case-insensitively (``str.casefold``) so catalog
entries can use the usual Roman capitalisation while still hitting lowercase
surface in segments. ``annotate`` keeps the edition substring as printed.
"""

from __future__ import annotations

import json
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from paths import BOOKS

from cs_roman_bold import unbold_ranges_in_runs

SCHEMA_VERSION = 2

SHARED_TRANSFORMS_PATH = BOOKS / "shared" / "transforms.json"

TransformAction = Literal["annotate", "replace", "unbold"]


@dataclass(frozen=True)
class TransformRule:
    """One ordered annotate or replace rule with optional segment filters."""

    id: str
    enabled: bool
    action: TransformAction
    match: str
    pages: frozenset[int] | None = None
    orders: frozenset[int] | None = None
    volumes: frozenset[str] | None = None
    segment_types: frozenset[str] | None = None
    token: bool = False
    footnote: str | None = None
    replacement: str | None = None
    remark: str | None = None
    soft_breaks: tuple[str, ...] | None = None
    unbold_skip: int = 0


def shared_transforms_path() -> Path:
    return SHARED_TRANSFORMS_PATH


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
        allowed_when = {
            "match",
            "pages",
            "orders",
            "volumes",
            "segment_types",
            "token",
        }
        unknown_when = set(when) - allowed_when
        if unknown_when:
            unknown = ", ".join(sorted(unknown_when))
            raise ValueError(f"{loc}: unsupported when keys: {unknown}")
        match_raw = when.get("match")
        if not isinstance(match_raw, str) or match_raw == "":
            raise ValueError(f"{loc}: when.match must be a non-empty string")
        match = match_raw
        token_raw = when.get("token", False)
        if not isinstance(token_raw, bool):
            raise ValueError(f"{loc}: when.token must be a boolean")
        token = token_raw

        do = raw.get("do")
        if not isinstance(do, dict):
            raise ValueError(f"{loc}: do must be an object")
        actions = set(do) & {"annotate", "replace", "unbold"}
        if len(actions) != 1:
            raise ValueError(
                f"{loc}: do must contain exactly one of annotate, replace, unbold"
            )
        unknown_do = set(do) - {"annotate", "replace", "unbold"}
        if unknown_do:
            unknown = ", ".join(sorted(unknown_do))
            raise ValueError(f"{loc}: unsupported do keys: {unknown}")

        footnote: str | None = None
        replacement: str | None = None
        remark: str | None = None
        soft_breaks: tuple[str, ...] | None = None
        unbold_skip = 0

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
        elif "unbold" in do:
            action = "unbold"
            spec = do["unbold"]
            if not isinstance(spec, dict):
                raise ValueError(f"{loc}: do.unbold must be an object")
            allowed = {"skip", "remark"}
            if set(spec) - allowed:
                unknown = ", ".join(sorted(set(spec) - allowed))
                raise ValueError(f"{loc}: unsupported do.unbold keys: {unknown}")
            skip_raw = spec.get("skip", 0)
            if not isinstance(skip_raw, int) or isinstance(skip_raw, bool) or skip_raw < 0:
                raise ValueError(f"{loc}: do.unbold.skip must be a non-negative integer")
            if skip_raw >= len(match):
                raise ValueError(
                    f"{loc}: do.unbold.skip must be smaller than when.match"
                )
            unbold_skip = skip_raw
            remark_raw = spec.get("remark")
            if remark_raw is not None:
                if not isinstance(remark_raw, str):
                    raise ValueError(f"{loc}: do.unbold.remark must be a string")
                remark = remark_raw
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
                volumes=_str_set(when.get("volumes"), field="volumes"),
                segment_types=_str_set(
                    when.get("segment_types"), field="segment_types"
                ),
                token=token,
                footnote=footnote,
                replacement=replacement,
                remark=remark,
                soft_breaks=soft_breaks,
                unbold_skip=unbold_skip,
            )
        )
    return rules


def load_transforms_file(path: Path) -> list[TransformRule]:
    """Load rules from one JSON file; missing file → empty list."""
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return parse_transforms_document(data, source=str(path))


def load_shared_transforms(*, path: Path | None = None) -> list[TransformRule]:
    """Load the edition catalog from ``shared/transforms.json``."""
    return load_transforms_file(path or shared_transforms_path())


def collect_transform_soft_breaks(
    rules: Sequence[TransformRule],
) -> dict[str, list[str]]:
    """Roman surface → soft-break parts from enabled rules (later wins)."""
    out: dict[str, list[str]] = {}
    for rule in rules:
        if not rule.enabled or not rule.soft_breaks:
            continue
        if rule.action == "annotate":
            key = rule.match
        elif rule.action == "replace":
            assert rule.replacement is not None
            key = rule.replacement
        else:
            continue
        out[key] = list(rule.soft_breaks)
    return out


def select_rules_for_volume(
    rules: Sequence[TransformRule], volume_id: str
) -> list[TransformRule]:
    """Drop rules pinned to other volume ids; unpinned rules stay."""
    return [
        rule
        for rule in rules
        if rule.volumes is None or volume_id in rule.volumes
    ]


@dataclass(frozen=True)
class _IndexedRule:
    index: int
    rule: TransformRule


@dataclass
class TransformProgram:
    """Compiled catalog: file-order rules plus letter-run indexes."""

    rules: list[TransformRule]
    by_run: dict[str, tuple[_IndexedRule, ...]] = field(default_factory=dict)
    by_first_run: dict[str, tuple[_IndexedRule, ...]] = field(default_factory=dict)
    other: tuple[_IndexedRule, ...] = ()

    def __iter__(self) -> Iterator[TransformRule]:
        return iter(self.rules)

    def __len__(self) -> int:
        return len(self.rules)

    def __getitem__(self, index: int) -> TransformRule:
        return self.rules[index]


def _index_key_run(run: str) -> str:
    """Letter-run key for the compiled index (case-insensitive)."""
    return run.casefold()


def _iter_letter_runs(text: str) -> Iterator[str]:
    """Yield maximal ``str.isalpha()`` runs (same boundaries as token match)."""
    i = 0
    n = len(text)
    while i < n:
        if text[i].isalpha():
            j = i + 1
            while j < n and text[j].isalpha():
                j += 1
            yield text[i:j]
            i = j
        else:
            i += 1


def _is_single_letter_run(text: str) -> bool:
    return bool(text) and all(ch.isalpha() for ch in text)


def _first_letter_run(text: str) -> str | None:
    return next(_iter_letter_runs(text), None)


def compile_transforms(rules: Sequence[TransformRule]) -> TransformProgram:
    """Build letter-run indexes; disabled rules stay in ``rules`` but not indexes."""
    rule_list = rules if isinstance(rules, list) else list(rules)
    by_run_map: dict[str, list[_IndexedRule]] = {}
    by_first_map: dict[str, list[_IndexedRule]] = {}
    other_list: list[_IndexedRule] = []
    for i, rule in enumerate(rule_list):
        if not rule.enabled:
            continue
        indexed = _IndexedRule(i, rule)
        if rule.token and _is_single_letter_run(rule.match):
            by_run_map.setdefault(_index_key_run(rule.match), []).append(indexed)
        elif rule.token:
            first = _first_letter_run(rule.match)
            if first is None:
                other_list.append(indexed)
            else:
                by_first_map.setdefault(_index_key_run(first), []).append(indexed)
        else:
            other_list.append(indexed)
    return TransformProgram(
        rules=rule_list,
        by_run={key: tuple(vals) for key, vals in by_run_map.items()},
        by_first_run={key: tuple(vals) for key, vals in by_first_map.items()},
        other=tuple(other_list),
    )


_compiled_cache: TransformProgram | None = None


def _as_program(
    rules: Sequence[TransformRule] | TransformProgram,
) -> TransformProgram:
    global _compiled_cache
    if isinstance(rules, TransformProgram):
        return rules
    if _compiled_cache is not None and _compiled_cache.rules is rules:
        return _compiled_cache
    prog = compile_transforms(rules)
    _compiled_cache = prog
    return prog


def _candidate_indexed(
    text: str,
    program: TransformProgram,
    min_index: int,
) -> list[_IndexedRule]:
    """Rules that might hit ``text``, in file order, from ``min_index`` onward."""
    seen: set[int] = set()
    out: list[_IndexedRule] = []

    def _take(items: Sequence[_IndexedRule]) -> None:
        for item in items:
            if item.index >= min_index and item.index not in seen:
                seen.add(item.index)
                out.append(item)

    seen_runs: set[str] = set()
    for run in _iter_letter_runs(text):
        if run in seen_runs:
            continue
        seen_runs.add(run)
        indexed = program.by_run.get(_index_key_run(run))
        if indexed:
            _take(indexed)
        first_hits = program.by_first_run.get(_index_key_run(run))
        if first_hits:
            _take(first_hits)
    if program.other:
        _take(program.other)
    out.sort(key=lambda item: item.index)
    return out


def rule_matches(
    rule: TransformRule,
    text: str,
    *,
    page: int,
    order: int,
    segment_type: str,
    volume_id: str | None = None,
) -> bool:
    if not rule.enabled:
        return False
    if (
        rule.volumes is not None
        and volume_id is not None
        and volume_id not in rule.volumes
    ):
        return False
    if rule.pages is not None and page not in rule.pages:
        return False
    if rule.orders is not None and order not in rule.orders:
        return False
    if rule.segment_types is not None and segment_type not in rule.segment_types:
        return False
    return _has_match(text, rule.match, token=rule.token)


def _token_bounded(text: str, start: int, length: int) -> bool:
    """True when ``text[start:start+length]`` is not inside a longer letter-run."""
    if start > 0 and text[start - 1].isalpha():
        return False
    end = start + length
    if end < len(text) and text[end].isalpha():
        return False
    return True


def _iter_match_indices(text: str, needle: str, *, token: bool):
    """Yield start indices of non-overlapping ``needle`` hits (case-insensitive)."""
    if not needle:
        return
    needle_fold = needle.casefold()
    needle_len = len(needle)
    start = 0
    text_len = len(text)
    while start <= text_len - needle_len:
        if text[start:start + needle_len].casefold() == needle_fold:
            if not token or _token_bounded(text, start, needle_len):
                yield start
                start += needle_len
            else:
                start += 1
        else:
            start += 1


def _has_match(text: str, needle: str, *, token: bool) -> bool:
    return next(_iter_match_indices(text, needle, token=token), None) is not None


def _literal_sub(
    text: str,
    needle: str,
    *,
    replacer,
    token: bool = False,
) -> str:
    """Replace every non-overlapping occurrence of ``needle`` via ``replacer``."""
    indices = list(_iter_match_indices(text, needle, token=token))
    if not indices:
        return text
    needle_len = len(needle)
    parts: list[str] = []
    last = 0
    for idx in indices:
        parts.append(text[last:idx])
        parts.append(replacer(text[idx:idx + needle_len]))
        last = idx + needle_len
    parts.append(text[last:])
    return "".join(parts)


def _apply_one_rule(
    text: str,
    rule: TransformRule,
    *,
    page: int,
    order: int,
    segment_type: str,
    volume_id: str | None,
    extra: list[str],
    note_base_index: int,
    emit_footnotes: bool,
) -> str:
    """Apply one rule; append annotate bodies to ``extra``. Returns new text."""
    if not rule_matches(
        rule,
        text,
        page=page,
        order=order,
        segment_type=segment_type,
        volume_id=volume_id,
    ):
        return text
    if rule.action == "unbold":
        return text
    if rule.action == "replace":
        assert rule.replacement is not None
        replacement = rule.replacement
        return _literal_sub(
            text,
            rule.match,
            replacer=lambda _matched, _with=replacement: _with,
            token=rule.token,
        )
    if not emit_footnotes:
        return text
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

    return _literal_sub(
        text, rule.match, replacer=_annotate_hit, token=rule.token
    )


def _apply_transforms_linear(
    text: str,
    rules: Sequence[TransformRule],
    *,
    page: int,
    order: int,
    segment_type: str,
    volume_id: str | None = None,
    note_base_index: int = 0,
    emit_footnotes: bool = True,
) -> tuple[str, list[str]]:
    """Apply every rule in order (no index). Used for equivalence tests."""
    out = text
    extra: list[str] = []
    for rule in rules:
        out = _apply_one_rule(
            out,
            rule,
            page=page,
            order=order,
            segment_type=segment_type,
            volume_id=volume_id,
            extra=extra,
            note_base_index=note_base_index,
            emit_footnotes=emit_footnotes,
        )
    return out, extra


def apply_transforms(
    text: str,
    rules: Sequence[TransformRule] | TransformProgram,
    *,
    page: int,
    order: int,
    segment_type: str,
    volume_id: str | None = None,
    note_base_index: int = 0,
    emit_footnotes: bool = True,
) -> tuple[str, list[str]]:
    """Apply matching rules in file order; return ``(text, extra_note_bodies)``.

    Uses a letter-run index so catalog size does not scan every rule per
    segment. After a mutation, later rules are re-indexed on the new text
    (replace/annotate chaining).

    ``annotate`` keeps ``match`` and (when ``emit_footnotes``) appends
    ``{{nN}}`` after each hit, collecting footnote bodies.

    ``replace`` substitutes ``with`` for ``match`` and never emits notes
    (``remark`` is ignored at generate).

    ``unbold`` does not change the string (applied to ``runs`` via
    ``apply_unbold_to_runs`` at generate).

    When ``emit_footnotes`` is false (e.g. transforming note bodies),
    annotate leaves text unchanged; replace still applies.
    """
    if not text or not rules:
        return text, []
    program = _as_program(rules)
    out = text
    extra: list[str] = []
    min_index = 0
    n = len(program.rules)
    while min_index < n:
        cands = _candidate_indexed(out, program, min_index)
        if not cands:
            break
        mutated = False
        for item in cands:
            before = out
            extra_before = len(extra)
            out = _apply_one_rule(
                out,
                item.rule,
                page=page,
                order=order,
                segment_type=segment_type,
                volume_id=volume_id,
                extra=extra,
                note_base_index=note_base_index,
                emit_footnotes=emit_footnotes,
            )
            if out != before or len(extra) != extra_before:
                min_index = item.index + 1
                mutated = True
                break
        if not mutated:
            break
    return out, extra


def apply_unbold_to_runs(
    text: str,
    runs: list[dict[str, Any]] | None,
    rules: Sequence[TransformRule] | TransformProgram,
    *,
    page: int,
    order: int,
    segment_type: str,
    volume_id: str | None = None,
) -> list[dict[str, Any]] | None:
    """Clear bold on ``unbold`` catalog hits; string ``text`` is unchanged."""
    if not text or not runs or not rules:
        return runs
    program = _as_program(rules)
    ranges: list[tuple[int, int]] = []
    for rule in program.rules:
        if rule.action != "unbold":
            continue
        if not rule_matches(
            rule,
            text,
            page=page,
            order=order,
            segment_type=segment_type,
            volume_id=volume_id,
        ):
            continue
        skip = rule.unbold_skip
        match_len = len(rule.match)
        for start in _iter_match_indices(text, rule.match, token=rule.token):
            a = start + skip
            b = start + match_len
            if a < b:
                ranges.append((a, b))
    if not ranges:
        return runs
    return unbold_ranges_in_runs(runs, ranges)


def segment_context(seg: dict[str, Any]) -> tuple[int, int, str]:
    """``(page, order, segment_type)`` for rule matching."""
    return (
        int(seg.get("page") or 0),
        int(seg.get("order") or 0),
        str(seg.get("segment_type") or "prose"),
    )
