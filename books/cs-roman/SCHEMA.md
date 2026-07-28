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
`layout` / `page_layout` / `page_layout_reading_mode` tuning. Transform rules are **not** baked into
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
| `page_layout` | no | Sparse per-page overrides for sync mode (source printed page); omit when empty |
| `page_layout_reading_mode` | no | Sparse per-page overrides for reading mode (physical PDF page / `\thepage`); empty `{}` kept when present; no `segments` |

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
| `section_no` | no | Outline number printed before a heading (e.g. `1` in `1. Pārājikakaṇḍa`); omit when unnumbered; **not** Tipiṭaka `item` |
| `segment_type` | yes | Structural kind (see below) |
| `text` | conditional | Multi-script body (absent on gāthā); heading titles stay bare (no leading outline `N.` prefix) |
| `notes` | no | Numbered footnote bodies (Roman); omit if empty |

### Compound outline titles (Vinaya)

Some CS Roman headings encode **two outline layers in one line**, e.g.
printed `1. Cīvaravagga 2. Udositasikkhāpada`:

| Stored field | Example | Role |
|--------------|---------|------|
| `section_no` | `1` | Parent outline number (vagga / major unit) |
| `text` | `Cīvaravagga 2. Udositasikkhāpada` | Parent name + embedded child number + child title |

TeX prefixes `section_no` via `with_section_no` → `1. จีวรวคฺค 2. อุโทสิตสิกฺขาปท`.
Do **not** put the leading outline `1.` inside `text`. The embedded child
number (`2.`) stays in `text`.

Keep **one body segment** (combined titles are intentional for readability).
The separate `*.matika.json` outline still lists parent and child as two rows;
TeX emits two `\csromantocmark` lines at that segment’s anchor (not the
compound string as a single TOC title). `heading_kind` on the segment is the
deeper (child) level for body macros.

### Mātikā outline file (`*.matika.json`)

Written by `assign_cs_roman_heading_levels.py` from the printed Mātikā.
Canonical: `output/<id>.matika.json`; sync copy: `volumes/<id>/data/matika.json`.

| Field | Role |
|-------|------|
| `title` | Bare outline title (no leading `N.`; same convention as body `text`) |
| `section_no` | Outline number when the Mātikā row is numbered; omit when unnumbered |
| `page` | Printed page when the row has leaders; else `null` |
| `kind` | `boo` \| `cha` \| `h1`…`h6` (TOC + heading skeleton) |
| `matched_order` | Body segment `order` when matched; else `null` |

TOC policy: prefer marks from this file (matched_order → segment anchor;
unmatched rows with `page` → first segment on that page). Body headings that
do not match the Mātikā keep optional `heading_kind` for typography but
`in_toc: false` (except edition title stack `nik` / `boo`).

When a short heading is glued to the pātimokkha uddesa sentence
(`Ime kho… uddesaṃ āgacchanti.`), extract/fixup **peels** them into a
heading segment + a following centered `prose` segment.
| `symbol_notes` | no | `{"*":…}` / `{"+":…}`; omit if empty |
| `flags` | no | e.g. `section_rule`; omit if empty |
| `needs_review` | no | Present only when `true` |
| `review_reasons` | no | Omit if empty |
| `heading_kind` | no | `nik` \| `boo` \| `cha` \| `h1`…`h6` — body typography level; assigned from the printed Mātikā skeleton when matched |
| `in_toc` | no | Body heading matched the Mātikā outline (cache). Memoir TOC is driven by `*.matika.json` when present (body-anchored, structure-expanded); falls back to this flag otherwise |
| `source_layout` | no | `bat_line` \| `wak_line` \| `hanging` \| `center` |
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
- Bold comes from CS Roman PDF fake-bold at **extract** time. `enrich_cs_roman_thai.py`
  (`--force` / spacing normalize) **preserves** remappable `runs`; it does not
  re-detect bold from the PDF. If runs are lost, re-extract the volume.

### Inline markers (in `value` / run values)

| Marker | Meaning |
|--------|---------|
| `{{nN}}` | Numbered footnote → `notes[N]` |
| `{{*}}` / `{{+}}` | Apparatus → `symbol_notes` |
| `{{sp1}}` | 0.5em gap after visible stop on **body** only (`prose` / `gatha` / …); pot-ma-gyi `. .` → `{{sp1}}{{sp1}}` (1.0em); ordinary `. next` → `.{{sp1}} next`. Not used on titles, chapters, closers, or footnote bodies (outline / catalog dots stay word-spaced). |
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
- **1 บทครึ่ง** (3 บาท / 6 วรรค): one segment with three `bats` (no inter-stanza
  gap in TeX). Legacy extracts may still split as full บท + irregular half;
  the generator joins that pair without `\\[\gathastanzaskip]`.

### Hanging prose

`source_layout: "hanging"`: `text` is the head line; `hanging_lines` is a list of
multi-script line entries (same shape as `text`).

### Centered labels

`source_layout: "center"`: first printed line is a short centered label (PDF
geometry: midpoint ≈ page center, width ≲ 0.55×page), **or** a short segment
(≲80 characters / ≲2 sentences) sandwiched between two already-centered
neighbors (e.g. `Evaṃ ekekaṃ…kattabbaṃ.` between `Baddhacakkaṃ.` and
`Idaṃ saṃkhittaṃ.`). Set at extract / geometry fixup; does not change
`segment_type`. TeX emits `\csromancenter` (body size, prose leading — not the
airy `\nitthitam` closer band) for centered prose and plain title labels; true
section closers (`niṭṭhitaṃ`, samattaṃ formulas) still use `\nitthitam`. Bold
titles, titles with `section_no`, and `heading_kind` keep their heading macros.

### `segment_type` vocabulary

| Type | Role |
|------|------|
| `prose` | Body paragraph |
| `prose_continuation` | Same unit continued on next printed page |
| `piṭaka` / `gambhīra` / `namakkāraṃ` / `chapter` / `title` / `niṭṭhitaṃ` | Structural |
| `gatha` | One stanza |
| `note` | Orphan / unattached footnote |

`heading_kind` (when set) overrides visual macros in TeX over `segment_type`.
Under a vagga stack, Mātikā assignment typically uses `h1` = vagga, `h2` =
sikkhāpada / rule, `h3` = vatthu / paññatti / vibhaṅga.

| Kind | Role | TeX |
|------|------|-----|
| `nik` | piṭaka | `\pitaka` |
| `boo` | book / gambhīra | `\gambhira` |
| `cha` | major chapter (e.g. kaṇḍa) | `\chapterhead` (same page) or `\chapterheadpage` (new sheet: odd/recto, plain, top pad) |
| `h1`…`h6` | generic section headers under `cha` (large → small) | `\csromanheader{n}` |

Former `tit` / `sub` map to `h1` / `h2`.

## Unit model

- One segment is anchored to one printed page.
- An itemless body block under the current `item` is stored as `prose`
  (same or later page). Sentence punctuation (`…ti`, fullstop) does **not**
  decide continuation — a new paragraph under the same item may start on
  the next page.
- Geometry upgrades a flush-left page-start to `{kind}_continuation`
  (usually `prose_continuation`). An indented page-start stays `prose`.
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
`page_layout` / `page_layout_reading_mode` (sync segments overrides; reading layout keys only), gāthā `bats`, hanging
fields, and optional `transforms.json`. It ignores document stats and review
flags.

### Document layout config

Print tuning lives in **`layout.json`**:

1. **`layout`** — volume defaults (every supported key; normalize fills gaps)
2. **`page_layout`** — overwrite any subset of those keys for specific **source printed pages** (sync mode; same numbers as ฉ.N)
3. **`page_layout[page].segments[n]`** — per-segment print overrides on that sync page
4. **`page_layout_reading_mode`** — same layout keys for **physical reading-PDF pages** (`\thepage` / running head); not folio ฉ.N; **no `segments`**

Edition defaults (from 01Vin01 tuning) live in `DEFAULT_LAYOUT` /
`shared/style/preamble.tex`. Volumes inherit them; use `page_layout` /
`page_layout_reading_mode` only when a page must differ.

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
  },
  "page_layout_reading_mode": {
    "100": { "line_space": 1.2 }
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

**Precedence (sync):** built-in defaults → `layout` → `page_layout[page]` (layout keys)
→ `page_layout[page].segments[n]` (interword only).

**Precedence (reading):** built-in defaults → `layout` → `page_layout_reading_mode[page]`
(layout keys). Sync `page_layout` is ignored in reading mode.

`n` is the **1-based index among segments on that printed page** (sorted by
`order`), not the global `order` field. This stays stable when other pages
gain/lose segments. Reading mode has no page-local segment index, so
`page_layout_reading_mode` must not include `segments`.

`page_layout` / `page_layout_reading_mode` may override **every** `layout` key.
The nested `segments` map (sync only) is meta and is **not** passed to
`\csromanlayoutapply`. Page format / geometry is not in this object (shared
`pagegeometry.tex` / `pagegeometry-reading.tex` only).

Sync generator emits `\csromanlayoutapply` at body start and whenever the
effective layout changes at a `\csromanpage` boundary. Reading generator emits
volume `\csromanlayoutapply`, then `\csromanreadingpagelayoutvolume` /
`\csromanreadingpagelayoutdef{N}` / `\csromanreadingpagelayoutenable`; TeX
re-applies when `\value{page}` changes at paragraph begin.

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
