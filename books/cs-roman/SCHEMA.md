# CS-roman segments + layout + transforms JSON schema

`schema_version`: **1**

Three file roles:

| Role | Meaning | Canonical | Volume sync |
|------|---------|-----------|-------------|
| Content | Extract-normalized text (after format-contract rules only) | `output/<id>.segments.json` | `volumes/<id>/data/segments.json` |
| Print | Spacing / bounds | `output/<id>.layout.json` | `volumes/<id>/data/layout.json` |
| Publication rules | Conditional string transforms for the book | `shared/transforms.json` + optional `output/<id>.transforms.json` | `volumes/<id>/data/transforms.json` (volume file only) |

Consumers load segments + layout (via `load_document`) into one in-memory
document. TeX generate also loads transform rules (shared then volume).
Re-extract rewrites content (+ bounds in layout) but **preserves** existing
`layout` / `page_layout` tuning. Transform rules are **not** baked into
`segments.json`; edit rules and rebuild to see them in the PDF.

Format prose that used to be duplicated in every volume file
(`text_format`, `unit_model`, `heading_model`, `note_style`, encoding notes)
is documented here instead.

## Content file (`*.segments.json`)

| Field | Required | Role |
|-------|----------|------|
| `schema_version` | yes | Integer; currently `1` |
| `segments` | yes | Ordered list of segment objects |

No print overrides or publication transforms belong here.
`segments.json` is **extract-normalized**, not necessarily publication-final:
format-contract rules (`. .` → `{{sp1}}{{sp1}}`, `. next` → `.{{sp1}} next`,
section-rule underscores, etc.) are
applied at extract; conditional / per-volume string fixes live in
`transforms.json` and run at TeX generate.

## Layout file (`*.layout.json`)

| Field | Required | Role |
|-------|----------|------|
| `schema_version` | yes | Integer; currently `1` |
| `source` | yes | Repo-relative path to source PDF (`books/cs-roman/source/<id>.pdf`) |
| `content_start_pdf_page` | yes | 1-based PDF page = printed page 1 |
| `content_end_printed_page` | no | Last printed body page kept |
| `back_matter_start_printed_page` | no | First index / back-matter printed page |
| `layout` | no* | Volume body-rhythm defaults (see below); normalize always fills all keys |
| `page_layout` | no | Sparse per-page overrides; omit when empty |

\*Absent `layout` is valid before normalize; consumers treat missing keys as
`DEFAULT_LAYOUT` in `scripts/cs_roman_segments.py` (matches TeX preamble).

Extract/heading **stats and reports** are not stored in these files:
use CLI output, `output/manifest.json`, and `*.heading-report.json`.

## Transforms file (`transforms.json`)

Publication string rules applied when generating TeX (see
`scripts/cs_roman_transforms.py` + `generate_cs_roman_tex.py`).

| Path | Role |
|------|------|
| `shared/transforms.json` | Edition-wide rules (always loaded first) |
| `output/<id>.transforms.json` | Optional per-volume rules — edit here |
| `volumes/<id>/data/transforms.json` | Sync copy of the volume file (if present) |

Absent volume file is fine. Sync copies from `output/` when present and
**removes** a stale volume copy when the canonical file is gone.

```json
{
  "schema_version": 1,
  "rules": [
    {
      "id": "01vin01-page12-bhagavaa",
      "enabled": true,
      "when": {
        "pages": [12],
        "orders": [3],
        "segment_types": ["prose"],
        "match": "Bhagavaa"
      },
      "do": {
        "replace": {
          "pattern": "Bhagavaa",
          "with": "Bhagavā",
          "flags": ""
        }
      }
    }
  ]
}
```

| Field | Role |
|-------|------|
| `id` | Stable unique id within the file (for tests / disable) |
| `enabled` | Default `true`; `false` skips the rule |
| `when` | Optional AND filters: `pages`, `orders`, `segment_types`, `match` (regex on the string being transformed) |
| `do.replace` | `pattern` + `with`; optional `flags` (`i` / `m` / `s`) |

**Order:** shared file order, then volume file order. Each matching rule’s
`pattern` is applied to Roman text (body, notes, gāthā, hanging lines); Thai
for the PDF is re-derived via `roman_to_thai` when the Roman string changes.
Stored Thai in `segments.json` is left unchanged.

Format-contract rules that define markers / flags stay in Python
(`cs_roman_text.py`), not in this file: pot-ma-gyi, `-pa-` → ฯเปฯ, trailing
`___` → `section_rule`.

## Segment object

| Field | Required | Role |
|-------|----------|------|
| `page` | yes | Printed page number |
| `order` | yes | Reading order in the volume |
| `item` | no | Tipiṭaka item number; `null`/absent for headings & gāthā |
| `segment_type` | yes | Structural kind (see below) |
| `text` | conditional | Multi-script body (absent on gāthā) |
| `notes` | no | Numbered footnote bodies (Roman); omit if empty |
| `symbol_notes` | no | `{"*":…}` / `{"+":…}`; omit if empty |
| `flags` | no | e.g. `section_rule`; omit if empty |
| `needs_review` | no | Present only when `true` |
| `review_reasons` | no | Omit if empty |
| `heading_kind` | no | `nik` \| `boo` \| `cha` \| `h1`…`h6` |
| `in_toc` | no | Include in Mātikā / memoir TOC |
| `source_layout` | no | `bat_line` \| `wak_line` \| `hanging` |
| `bats` | gāthā | Nested stanza (see below) |
| `hanging_lines` | hanging | Body lines under hanging head |

**Not stored (v1):** `pdf_page`, `bats[].bat`, `waks[].wak`, `waks[].role`,
segment-level `word_space` (print overrides live in `layout.json`).

### `text` / script entries

```json
[
  {"script": "roman", "value": "…", "runs": [{"value": "…", "bold": true}]},
  {"script": "thai", "value": "…", "runs": [{"value": "…", "bold": true}]}
]
```

- Script codes align with `ContentScript` (`roman`, `thai`).
- Thai is IAST→Thai via `pali_script`; inline markers are preserved.
- `runs` are present **only when at least one run is bold**.
  Otherwise consumers use `value` alone.
- `join(runs[].value)` equals `value` when `runs` exist.

### Inline markers (in `value` / run values)

| Marker | Meaning |
|--------|---------|
| `{{nN}}` | Numbered footnote → `notes[N]` |
| `{{*}}` / `{{+}}` | Apparatus → `symbol_notes` |
| `{{sp1}}` | 1em gap after visible stop; pot-ma-gyi `. .` → `{{sp1}}{{sp1}}`; ordinary `. next` → `.{{sp1}} next` |
| `{{sp3}}` | Legacy alias of `{{sp1}}` (migrated on enrich) |

Notes stay Roman in JSON; TeX transliterates at emit time.

### Gāthā (`segment_type`: `gatha`)

No top-level `text`. One segment = one บท:

```json
{
  "segment_type": "gatha",
  "source_layout": "bat_line",
  "bats": [
    {"waks": [{"text": [/* multi-script */]}, {"text": […]}]},
    {"waks": [{"text": […]}, {"text": […]}]}
  ]
}
```

- `source_layout`: `bat_line` (2 printed lines/บท) or `wak_line` (4 lines/บท).
- Wak order within each bat is fixed; roles (sadap/rap/rong/song) are implied by position.

### Hanging prose

`source_layout: "hanging"`: `text` is the head line; `hanging_lines` is a list of
multi-script line entries (same shape as `text`).

### `segment_type` vocabulary

| Type | Role |
|------|------|
| `prose` | Body paragraph |
| `prose_continuation` | Same unit continued on next printed page |
| `piṭaka` / `gambhīra` / `namakkāraṃ` / `chapter` / `title` / `niṭṭhitaṃ` | Structural |
| `gatha` | One stanza |
| `note` | Orphan / unattached footnote |

`heading_kind` (when set) overrides visual macros in TeX over `segment_type`.

| Kind | Role | TeX |
|------|------|-----|
| `nik` | piṭaka | `\pitaka` |
| `boo` | book / gambhīra | `\gambhira` |
| `cha` | major chapter (e.g. kaṇḍa) | `\chapterhead` |
| `h1`…`h6` | generic section headers under `cha` (large → small) | `\csromanheader{n}` |

Former `tit` / `sub` map to `h1` / `h2`.

## Unit model

- One segment is anchored to one printed page.
- An unfinished unit on the next page becomes `{kind}_continuation`
  (in practice almost always `prose_continuation`).
- A new paragraph under the same `item` is `prose` (not continuation).
- Footnotes stay on the segment where the callout appears.
- Mid-word page breaks finish the word on the earlier segment.

## Consumers

| Consumer | Path |
|----------|------|
| Extract | `scripts/extract_cs_roman_pdf.py` |
| Headings | `scripts/assign_cs_roman_heading_levels.py` |
| Typed I/O | `scripts/cs_roman_segments.py` |
| Transforms | `scripts/cs_roman_transforms.py` |
| TeX body | `scripts/generate_cs_roman_tex.py` |

TeX reads Thai `text` / `runs` (or re-derives Thai after publication
transforms on Roman), markers, `heading_kind` / `in_toc`, `layout` /
`page_layout` (including per-segment overrides), gāthā `bats`, hanging
fields, and optional `transforms.json`. It ignores document stats and review
flags.

### Document layout config

Print tuning lives in **`layout.json`**:

1. **`layout`** — volume defaults (every supported key; normalize fills gaps)
2. **`page_layout`** — overwrite any subset of those keys for specific printed pages
3. **`page_layout[page].segments[n]`** — per-segment print overrides on that page

Edition defaults (from 01Vin01 tuning) live in `DEFAULT_LAYOUT` /
`shared/style/preamble.tex`. Volumes inherit them; use `page_layout` only
when a printed page must differ.

```json
{
  "layout": {
    "word_space": 1.6,
    "line_space": 1.5,
    "par_indent": "21.6pt",
    "par_skip": "5pt",
    "gatha_stanza_skip": "6.3pt",
    "gatha_indent": "65pt",
    "emergency_stretch": "2.5em"
  },
  "page_layout": {
    "157": { "line_space": 1.15 },
    "174": { "line_space": 1.00 }
  }
}
```

| Key | Kind | TeX |
|-----|------|-----|
| `word_space` | positive number | interword (`WordSpace` / `\spaceskip`) |
| `line_space` | positive number | `\linespread` |
| `par_indent` | dimension | `\tipitakahang` / `\parindent` |
| `par_skip` | dimension | `\tipitakaparskip` / `\parskip` (plus/minus glue fixed in TeX) |
| `gatha_stanza_skip` | dimension | `\gathastanzaskip` |
| `gatha_indent` | dimension | `\gathaindent` |
| `emergency_stretch` | dimension | `\emergencystretch` |

**Precedence:** built-in defaults → `layout` → `page_layout[page]` (layout keys)
→ `page_layout[page].segments[n]` (interword only).

`n` is the **1-based index among segments on that printed page** (sorted by
`order`), not the global `order` field. This stays stable when other pages
gain/lose segments.

`page_layout` may override **every** `layout` key. The nested `segments` map is
meta and is **not** passed to `\csromanlayoutapply`. Page format / geometry is
not in this object (shared `pagegeometry.tex` only).

Generator emits `\csromanlayoutapply` at body start and whenever the effective
layout changes at a page boundary.

### Per-segment word spacing

To tighten (or widen) **one** segment without changing the page/volume, put the
override under that page’s `segments` map:

```json
"page_layout": {
  "322": {
    "segments": {
      "5": { "word_space": 1.6 }
    }
  }
}
```

TeX wraps that segment with `\csromanwordspacebegin` /
`\csromanwordspaceend` when the value differs from the effective page
`word_space`. Omit the entry to keep page/volume layout. Values must be
positive numbers. Build validation fails if `n` is out of range for that page.
