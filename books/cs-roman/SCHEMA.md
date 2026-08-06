# CS-roman segments + layout + transforms JSON schema

`schema_version`: **1**

Three file roles:

| Role | Meaning | Canonical | Volume sync |
|------|---------|-----------|-------------|
| Content | Extract-normalized text (after format-contract rules only) | `output/<id>.segments.json` | `volumes/<id>/data/segments.json` |
| Print | Spacing / bounds | `output/<id>.layout.json` | `volumes/<id>/data/layout.json` |
| Publication rules | Conditional string transforms for the book | `shared/transforms.json` + optional `output/<id>.transforms.json` | `volumes/<id>/data/transforms.json` (volume file only) |

Consumers load segments + layout (via `load_document`) into one in-memory
document. TeX generate also loads transform rules (shared then volume) and
ensures `shared/sandhi_breaks.json` (DPD sandhi soft hyphens for long tokens —
layout-only; not stored in segments; auto-built from `vendor/dpd/dpd.db` when
the cache is missing) merged with curated
`shared/sandhi_breaks_overrides.json` (overrides win). See
`research/sandhi_soft_breaks.md`.
Re-extract rewrites content (+ bounds in layout) but **preserves** existing
`layout` / `page_layout_reading_mode` / `page_breaks_reading_mode` tuning
(and `//…` documentation keys). Transform rules are **not** baked into
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
section-rule underscores, solid editorial mid-word hyphens
`na-upanissaye` → Roman `naupanissaye` / Thai `นอุปนิสฺสเย` — Thai is
converted part-wise at the hyphen then joined, while peyyāla `-pa-` is kept,
etc.) are applied at extract; conditional / per-volume string fixes live in
`transforms.json` and run at TeX generate. Repair older segments with
`scripts/fixup_solid_midword_hyphens.py`.

## Layout file (`*.layout.json`)

| Field | Required | Role |
|-------|----------|------|
| `schema_version` | yes | Integer; currently `1` |
| `source` | yes | Repo-relative path to source PDF (`books/cs-roman/source/<id>.pdf`) |
| `content_start_pdf_page` | yes | 1-based PDF page = printed page 1 |
| `content_end_printed_page` | no | Last printed body page kept |
| `back_matter_start_printed_page` | no | First index / back-matter printed page |
| `layout` | no* | Volume body-rhythm defaults (see below); normalize always fills all keys; sync uses this only |
| `page_layout_reading_mode` | no | Sparse per-page overrides for reading mode (physical PDF page / `\thepage`); empty `{}` kept when present; no `segments` |
| `page_breaks_reading_mode` | no | Forced page breaks in reading mode by segment `order`; omit when empty |
| `//…` | no | Hand-authored documentation (string or string list). Keys start with `//`. Ignored by TeX; preserved by normalize / re-extract. Edit only via UTF-8-safe I/O (not PowerShell `Get-Content` without `-Encoding utf8`); validate rejects mojibake markers |

`page_layout` (sync per-page overrides) is **removed**. Validate rejects it if present.

\*Absent `layout` is valid before normalize; consumers treat missing keys as
`DEFAULT_LAYOUT` in `scripts/cs_roman_segments.py` (matches TeX preamble).

Extract/heading **stats and reports** are not stored in these files:
use CLI output, `output/manifest.json`, and `*.heading-report.json`.

## Transforms file (`transforms.json`)

Publication string rules applied when generating TeX (see
`scripts/cs_roman_transforms.py` + `generate_cs_roman_tex.py`).
`schema_version` **2**.

| Path | Role |
|------|------|
| `shared/transforms.json` | Edition-wide rules (always loaded first) |
| `output/<id>.transforms.json` | Optional per-volume rules — edit here |
| `volumes/<id>/data/transforms.json` | Sync copy of the volume file (if present) |

Absent volume file is fine. Sync copies from `output/` when present and
**removes** a stale volume copy when the canonical file is gone.

Exactly one action per rule:

| Action | When | Body text | PDF footnote |
|--------|------|-----------|--------------|
| `annotate` (default for new editorial notes) | Burmese/source reading is wrong; keep Roman as printed | Unchanged (`when.match`) | Yes — `footnote` |
| `replace` | Burmese is correct; Roman is wrong | `when.match` → `with` | No (`remark` is editor-only) |

`when.match` is the **full** edition surface token (literal substring, not a
regex). Optional `soft_breaks` parts must concatenate to the surface form that
remains after the rule (`match` for annotate, `with` for replace) and merge into
the sandhi break map at generate (they are not written to
`sandhi_breaks_overrides.json`).

```json
{
  "schema_version": 2,
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
          "with": "Bhagavā",
          "remark": "Roman typo; Burmese has Bhagavā"
        }
      }
    },
    {
      "id": "01vin01-p280-cira-civara",
      "enabled": true,
      "when": {
        "pages": [280],
        "orders": [1854],
        "segment_types": ["prose"],
        "match": "cīrapiṇḍapātasenāsanagilānappaccayabhesajjaparikkhārā"
      },
      "do": {
        "annotate": {
          "footnote": "cīra- pāṭho, cīvara- ม.พ.ป.",
          "soft_breaks": [
            "cīra",
            "piṇḍapāta",
            "senāsana",
            "gilānappaccaya",
            "bhesajja",
            "parikkhārā"
          ]
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
| `when` | AND filters: required literal `match` (full token); optional `pages`, `orders`, `segment_types` |
| `do.annotate` | Keep `match`; required `footnote` (Roman note body); optional `soft_breaks` |
| `do.replace` | Required `with`; optional `remark` (not rendered); optional `soft_breaks` |
| `do.annotate.footnote` | Editorial numbered note. At generate: callout `{{nN}}` is appended after each hit (after existing segment notes); body goes through `note_to_thai`. Runs on body/gāthā Roman **before** Thai transliteration and sandhi soft breaks. Not injected when transforming note bodies themselves. |

**Order:** shared file order, then volume file order. Matching rules are applied
to Roman text (body, notes, gāthā, hanging lines); Thai for the PDF is
re-derived via `roman_to_thai` when the Roman string changes (annotate always
changes Roman by adding `{{nN}}`). Stored Thai in `segments.json` is left
unchanged.

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
| `notes` | no | Numbered footnote bodies (Roman); omit if empty. PDF U+23AF (HORIZONTAL LINE EXTENSION) is normalized to en-dash U+2013 at extract; Thai is derived at generate via `note_to_thai`. |

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

Running-head policy: **verso** from piṭaka / nikāya / pāḷi macros;
**recto** from standard TeX marks set by body heading macros only
(`\chapterhead*` → `\markboth` / cha; `\csromanheader{1}` → h1;
`\csromanheader{2}` → h2 joined into `\rightmark`). Display trial:
`cha` + `h1` + `h2` (omit empty), separated by `\csromanheadsep`.
Mātikā rows (including unmatched “ghost” titles) drive TOC / bookmarks
only — they do **not** set recto marks. Levels h3…h6 do not touch marks.

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
- Bold comes from CS Roman PDF fake-bold at **extract** time: stroke overlays
  (`get_texttrace` type 1) are matched to body-line **bboxes**, then the span
  string is located only inside that line’s window in the segment text (so a
  bold lemma does not paint later plain repeats). `enrich_cs_roman_thai.py`
  (`--force` / spacing normalize) **preserves** remappable `runs`; it does not
  re-detect bold from the PDF. If runs are wrong or lost, re-extract or run
  `scripts/fixup_bold_bbox.py`.

### Inline markers (in `value` / run values)

| Marker | Meaning |
|--------|---------|
| `{{nN}}` | Numbered footnote → `notes[N]`. Extract binds glued (`word1`) and spaced (`word 1`) callouts; spaced `1.` outline numbers are not callouts. Orphans left from older extracts: `scripts/fixup_orphan_footnote_callouts.py`. |
| `{{*}}` / `{{+}}` | Apparatus → `symbol_notes` (also mid-paragraph spaced ` * ` / ` + ` callouts) |
| `{{[]}}` | Bracket apparatus (``[  ] …`` note, e.g. Syāma omission) → `symbol_notes["[]"]` |
| `{{()}}` | Empty-paren apparatus (``(  ) …`` note, e.g. *katthaci natthi*) → `symbol_notes["()"]`. Hosts on the first **non-folio** body `(`. Numbered footnotes whose body starts with `( )` stay numbered (`{{nN}}`), never steal onto `(150)`. |
| `{{sp1}}` | Sentence-stop spacer on **body** only (`prose` / `gatha` / …) → TeX `\csromanspacer` (default `0em` in `book-macros.tex`); pot-ma-gyi `. .` → `{{sp1}}{{sp1}}` (2× spacer); ordinary `. next` → `.{{sp1}} next`. Not used on titles, chapters, closers, or footnote bodies (outline / catalog dots stay word-spaced). |
| `{{sp3}}` | Legacy alias of `{{sp1}}` (migrated on enrich) |

Notes stay Roman in JSON; TeX transliterates at emit time.

**Line breaks (generate):** paragraph/folio ranges like `(12-13)` /
`(12- 13)` / `(55-56)` (optional spaces around `-`) are emitted as
`\mbox{(12-13)}` with spaces around `-` collapsed, so TeX neither breaks
after the hyphen nor opens a wide `\spaceskip` gap. Single markers `(14)`
are unchanged. Stored JSON may still have `(12- 13)`.

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
- **bat_line TeX:** each บาท emits `\csromangathabat{left}{right}` so the right
  วรรค (after the comma) shares a column; left-column width is the max left
  วรรค within that consecutive gāthā กลุ่ม (`\csromangathasetleft` /
  `\csromangathameasuregroup`). Gap between the two วรรค is `\csromangathabatgap`
  (**20pt** clear space after the left column; not printing-scaled).
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

When a section closer immediately follows body prose (`prose` /
`prose_continuation`), the generator emits one TeX unit
(`\prosewithcloser` / `\prosewithcloserruled`, or `proseitem*` /
`prosecont*` variants) so the closer cannot orphan alone at a page head.
Standalone closers (no prose predecessor) still use `\nitthitam`.

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
| `cha` | major chapter (e.g. kaṇḍa) | `\chapterhead` (same page) or `\chapterheadpage` / `\chapterheadpageread` (new sheet: odd/recto, plain, top pad). Reading mode may insert a blank verso via `\csromanensureoddpage`; that verso is `plain` (no running head) — all volumes. |
| `h1`…`h6` | generic section headers under `cha` (large → small) | `\csromanheader{n}` |

Former `tit` / `sub` map to `h1` / `h2`.

Running heads (all modes, `shared/style/book-macros.tex`): verso/even =
`ปิฎก นิกาย ปาฬิ` (only parts present); recto/odd = TeX `\leftmark` /
`\rightmark` from body `cha` / `h1` / `h2` (not from Mātikā). `\csromanrunhead`
uses a fixed `\spaceskip=0.33em` (not body `word_space`) so `N. Title` stays
tight; joined fields use `\csromanheadsep` (`1em`).
Suttanta volumes (no `piṭaka` segment) get `\setcsromanpitaka{สุตฺตนฺตปิฏก}`
+ the opening `title` as nikāya injected at generate
(`opening_running_head_lines`); Vinaya / Abhidhamma volumes set their own
piṭaka from the `piṭaka` segment's `\pitaka`.

## Unit model

- One segment is anchored to one printed page.
- An itemless body block under the current `item` is stored as `prose`
  (same or later page). Sentence punctuation (`…ti`, fullstop) does **not**
  decide continuation — a new paragraph under the same item may start on
  the next page.
- Geometry upgrades a flush-left page-start to `{kind}_continuation`
  (usually `prose_continuation`). An indented page-start stays `prose`.
- Footnotes stay on the segment where the callout appears.
- In TeX output, each footnote mark and its body must share the same
  physical page (`shared/style/footnotes.tex`: `\insert` natural note box,
  `\@makecol` repacks sealed boxes only; audit with
  `scripts/scan_footnote_page_mismatch.py`, regression
  `scripts/test_footnote_mark_page_sync.py`).
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
`page_layout_reading_mode` (reading layout keys only; **printing ignores**),
`page_breaks_reading_mode` (reading/printing `\clearpage` before listed `order`s), gāthā `bats`, hanging
fields, and optional `transforms.json`. It ignores document stats and review
flags.

### Document layout config

Print tuning lives in **`layout.json`**:

1. **`layout`** — volume defaults (every supported key; normalize fills gaps). **Sync and printing modes use this only** (printing has no per-page map).
2. **`page_layout_reading_mode`** — same layout keys for **physical reading-PDF pages** (`\thepage` / running head); not folio ฉ.N; **no `segments`**. Printing omits this map (reflow changes physical page numbers).
3. **`page_breaks_reading_mode`** — force `\clearpage` **before** listed segment `order`s in reading and printing modes (orphan headings / keep-with-next); sync ignores this
4. **`//…` documentation keys** — optional notes. Prefer `"//"`, `"//layout"`, `"//page_layout_reading_mode"`, `"//page_breaks_reading_mode"`. See `output/01Vin01.layout.json`.

Edition defaults live in `DEFAULT_LAYOUT` (`scripts/cs_roman_segments.py`) and
each volume’s `layout.json`. `shared/style/preamble.tex` holds matching TeX
fallbacks; **`layout` / `DEFAULT_LAYOUT` overwrite those at generate time**
(`\csromanlayoutapply`). For `word_space`, preamble `WordSpace` is only the
font-load baseline — the generator scales `\spaceskip` so the absolute
`layout.word_space` wins (do not couple the Python baseline to
`DEFAULT_LAYOUT`). Use `page_layout_reading_mode` only when a reading page
must differ.

```json
{
  "layout": {
    "word_space": 3.5,
    "line_space": 1.5,
    "par_indent": "21.6pt",
    "par_skip": "5pt",
    "gatha_stanza_skip": "30pt",
    "gatha_indent": "65pt",
    "emergency_stretch": "2.5em"
  },
  "page_layout_reading_mode": {
    "100": { "line_space": 1.2 }
  },
  "page_breaks_reading_mode": {
    "before_orders": [483]
  }
}
```

| Key | Kind | TeX |
|-----|------|-----|
| `word_space` | positive number | absolute interword (fontspec `WordSpace` units); overwrites preamble via `\spaceskip` = `(target / preamble WordSpace) × fontdimen` |
| `line_space` | positive number | `\linespread` |
| `par_indent` | dimension | `\tipitakahang` / `\parindent` |
| `par_skip` | dimension | `\tipitakaparskip` / `\parskip` (plus/minus glue fixed in TeX) |
| `gatha_stanza_skip` | dimension | `\gathastanzaskip` — target **baseline-to-baseline** gap between บท (default `30pt`: body leading ≈20pt plus clear stanza air; matches 01Vin01 printing). TeX uses `\vskip{\gathastanzaskip-0.62\baselineskip}` with `\nointerlineskip`, floored so a too-small value cannot smash บท together. |
| `gatha_indent` | dimension | `\gathaindent` |
| `emergency_stretch` | dimension | `\emergencystretch` |

**Precedence (sync):** built-in defaults → `layout` (no per-page map).

**Precedence (reading):** built-in defaults → `layout` → `page_layout_reading_mode[page]`
(layout keys).

**Precedence (printing):** built-in defaults → `layout` only (same continuous
flow as reading; no `page_layout_reading_mode`). Geometry is
`pagegeometry-printing.tex` (165 × 230 mm; linear scale \(s = 165\,\mathrm{mm}/499\,\mathrm{bp}\)).

`page_breaks_reading_mode.before_orders` inserts `\clearpage` before those
global segment `order` values (first segment of the block you want to start
a page — e.g. an orphaned heading) in reading and printing bodies.

`page_layout_reading_mode` may override **every** `layout` key and must not
include `segments`. Page format / geometry is not in this object (shared
`pagegeometry.tex` / `pagegeometry-reading.tex` / `pagegeometry-printing.tex`).

Sync generator emits volume `\csromanlayoutapply` at body start.
Reading generator emits volume `\csromanlayoutapply`, then
`\csromanreadingpagelayoutvolume` / `\csromanreadingpagelayoutdef{N}` /
`\csromanreadingpagelayoutenable`; TeX re-applies when `\value{page}` changes
at paragraph begin. Printing generator emits volume `\csromanlayoutapply` only
(plus the same continuous/folio body as reading). Forced breaks from
`page_breaks_reading_mode` are emitted as `\clearpage` in reading and printing
bodies only.
