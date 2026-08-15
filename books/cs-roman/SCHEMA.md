# CS-roman segments + layout + transforms JSON schema

`schema_version`: **1**

Three file roles:

| Role | Meaning | Canonical | Volume sync |
|------|---------|-----------|-------------|
| Content | Extract-normalized text (after format-contract rules only) | `output/<id>.segments.json` | `volumes/<id>/data/segments.json` |
| Print | Spacing / bounds | `output/<id>.layout.json` | `volumes/<id>/data/layout.json` |
| Publication rules | Conditional string transforms for the book | `shared/transforms.json` | not synced |

Consumers load segments + layout (via `load_document`) into one in-memory
document. TeX generate also loads transform rules from
`shared/transforms.json` and
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

Repair of older/mistagged segment JSON is governed by
[`docs/fixup_process.md`](docs/fixup_process.md) and
`scripts/fixup_manifest.json` (pipeline + residual gate) — not ad-hoc edits.

## Content file (`*.segments.json`)

| Field | Required | Role |
|-------|----------|------|
| `schema_version` | yes | Integer; currently `1` |
| `segments` | yes | Ordered list of segment objects |

No print overrides or publication transforms belong here.
`segments.json` is **extract-normalized**, not necessarily publication-final:
format-contract rules (`. .` → `. ` ordinary full stop,
section-rule underscores, solid editorial mid-word hyphens
`na-upanissaye` → Roman `naupanissaye` / Thai `นอุปนิสฺสเย` — Thai is
converted part-wise at the hyphen then joined, while peyyāla `-pa-` is kept,
etc.) are applied at extract; publication string fixes live in
`shared/transforms.json` and run at TeX generate. Repair older segments with
`scripts/fixup_solid_midword_hyphens.py`. Legacy `{{sp1}}` / `{{sp3}}`
sentence-spacer markers are stripped on normalize (retired; TeX no longer
emits `\csromanspacer` from them).

**Running headers:** extract scans page-top labels across the whole body (not
only the first dozen pages). Labels of the form `Name (folio)` /
`N. Name (folio)` (Majjhima-style) are accepted from a single page-top
sighting — short suttas may span fewer than three pages. When the PDF omits a
blank line after `10. Subhasutta` / folio / `Potaliyasutta (54)`, extract peels
that furniture from the multi-line block so it is not item-parsed into the body
or tagged `source_layout=center`. Isolated `Name (folio)` blocks are dropped as
furniture; chapter opens without a folio paren (`10. Subhasutta`,
`Potaliyasutta`) are kept.

Continuation pages (common in Saṃyutta) reprint a centered `N. Title` with the
**edition page number on the outer margin** (เลขหน้าฉบับริมนอก). Blank lines
between them used to leave the title as a false body heading. Extract peels
that page-top cluster when it contains both a detected header and an edition
page number and the next line is not a child title; real opens
(`12. Vacchagottasaṃyutta` then `1. Rūpa-…`) are kept. Repair older artifacts
with `scripts/fixup_glued_running_headers.py` (also drops leftover folio-title
segments, continuation-page running-header title repeats, and re-runs
page-start continuation) and/or `scripts/fixup_page_start_continuation.py`.

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

## Transforms file (`shared/transforms.json`)

Publication string rules applied when generating TeX (see
`scripts/cs_roman_transforms.py` + `generate_cs_roman_tex.py`).
`schema_version` **2**. One edition catalog — no per-volume transform files.

| Path | Role |
|------|------|
| `shared/transforms.json` | Sole catalog; generate loads this for every volume |

Prefer a unique `when.match` so the same typo is fixed wherever it appears.
Optional `volumes` / `pages` / `orders` / `segment_types` are AND filters on the
volume **currently being generated**. Printed `pages` / `orders` collide across
books — pin `volumes` (folder id, e.g. `01Vin01`) when the same surface string
is wrong in one book and correct in another. Record known loci in
`replace.remark` or a test, not as a default pin.

Exactly one action per rule:

| Action | When | Body text | PDF footnote |
|--------|------|-----------|--------------|
| `annotate` (default for new editorial notes) | Burmese/source reading is wrong; keep Roman as printed | Unchanged (`when.match`) | Yes — `footnote` |
| `replace` | Burmese is correct; Roman is wrong | `when.match` → `with` | No (`remark` is editor-only) |

`when.match` is the **full** edition surface token (literal substring, not a
regex). Matching is **case-insensitive** (`str.casefold`) so catalog entries
may use Roman capitalisation while still hitting lowercase surface in segments;
`annotate` keeps the edition substring as printed. Catalog rules in
`shared/transforms.json` always set `when.token` to
`true` (letter boundaries: `bandhiṃ` does not hit `bandhiṃsu` / `anubandhiṃ`).
Match the complete word or phrase as printed, not a stem (`kukuccaṃ` not
`kukucc`). The parser still defaults `token` to `false` for tests. Optional
`volumes` (volume folder ids) plus `pages` / `orders` when the same surface
token is correct in one locus and wrong in another. Optional `soft_breaks` parts must
concatenate to the surface form that remains after the rule (`match` for
annotate, `with` for replace) and merge into the sandhi break map at generate
(they are not written to `sandhi_breaks_overrides.json`).

```json
{
  "schema_version": 2,
  "rules": [
    {
      "id": "01vin01-page12-bhagavaa",
      "enabled": true,
      "when": {
        "volumes": ["01Vin01"],
        "pages": [12],
        "orders": [3],
        "segment_types": ["prose"],
        "match": "Bhagavaa",
        "token": true
      },
      "do": {
        "replace": {
          "with": "Bhagavā",
          "remark": "Roman typo; Burmese has Bhagavā"
        }
      }
    },
    {
      "id": "roman-cira-civara-patho",
      "enabled": true,
      "when": {
        "match": "cīrapiṇḍapātasenāsanagilānappaccayabhesajjaparikkhārā",
        "token": true
      },
      "do": {
        "annotate": {
          "footnote": "cīra- pāṭho, cīvara- – ม.พ.ป.",
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
| `when` | AND filters: required literal `match`; optional `volumes`, `pages`, `orders`, `segment_types`; optional `token` |
| `when.volumes` | Volume folder ids (`01Vin01`, …). Generate drops the rule for other books. Use with `pages` when page numbers collide |
| `when.token` | Catalog `replace` / `annotate`: always `true`. Letter boundaries so `bandhiṃ` does not hit `bandhiṃsu` / `anubandhiṃ` (`taṃ yeva` does not hit `santaṃ yeva`). Parser default for tests is `false`. Catalog `unbold` of glued quote-iti (`”ti`) uses `false` because `”` is not a letter-run |
| `do.annotate` | Keep `match`; required `footnote` (Roman note body + siglum); optional `soft_breaks` |
| `do.replace` | Required `with`; optional `remark` (not rendered); optional `soft_breaks` |
| `do.unbold` | Keep `match`; clear bold on that span in `runs` (Roman stroke/weight wrong vs Burmese). Optional `skip` (non-negative int, smaller than `match`) leaves a prefix bold — e.g. `skip: 1` on `”ti` keeps `”`. Optional `remark`. Does not change the Roman string |
| `do.annotate.footnote` | Editorial numbered note. Convention: Pali lemma / tag, then **` – ม.พ.ป.`** (en-dash + มูลนิธิพระไตรปิฎกเพื่อประชาชน) so the note is distinct from edition apparatus (`สี`, `สฺยา`, …). Example: `tesaṃyeva niggahītasandhi – ม.พ.ป.` → Thai `เตสํเยว นิคฺคหีตสนฺธิ – ม.พ.ป.` At generate: callout `{{nN}}` is appended after each hit (after existing segment notes); body goes through `note_to_thai`, then TeX `\csromansharedfootnote{id}{…}` (identical bodies share one mark per page after ≥2 latex runs; see `footnotes.tex`). Runs on body/gāthā Roman **before** Thai transliteration and sandhi soft breaks. Not injected when transforming note bodies themselves. |

**Order:** file order in `shared/transforms.json`. Matching rules are applied
to Roman text (body, notes, gāthā, hanging lines); Thai for the PDF is
re-derived via `roman_to_thai` when the Roman string changes (annotate always
changes Roman by adding `{{nN}}`). Stored Thai in `segments.json` is left
unchanged. Stored bold `runs` are remapped through the same edit
(`remap_runs_through_edit`: inserted characters inherit bold from the
preceding kept character; inline markers stay unbold) then Thai runs via
`transliterate_runs`. Do not patch `segments.json` `runs` by hand for a
publication replace or unbold — generate remaps lemma bold (e.g. `Haneyyuṃvā` + `ti`
→ `Haneyyuṃ vā` + `ti`) and applies `unbold` to stored runs when the string
is unchanged. Runs drop only when they cannot be aligned.

Generate compiles a letter-run index (`compile_transforms` in
`cs_roman_transforms.py`) so apply is O(tokens in the segment), not
O(rules × segments). The JSON schema is unchanged; file order remains the
apply contract. Do not write hit positions back into this catalog.

Format-contract rules that define markers / flags stay in Python
(`cs_roman_text.py`), not in this file: pot-ma-gyi, `-pa-` → ฯเปฯ, trailing
`___` → `section_rule`. Roman-wrong bold (e.g. closing iti after `”`) is
catalog `do.unbold`, not a hardcoded peel.

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
Compound body titles (`1. ปตฺตวคฺค 8. อฏฺฐมสิกฺขาปท`) split into separate
mark fields at generate; footnote / symbol-footnote bodies are stripped
before that split so edition refs like `3. …` inside `\footnote{…}` do
not tear braces. `\csroman@setheadfield` also gobbles footnotes when
writing marks. Mātikā rows (including unmatched “ghost” titles) drive
TOC / bookmarks only — they do **not** set recto marks. Levels h3…h6 do
not touch marks.

When a short heading is glued to the pātimokkha uddesa sentence
(`Ime kho… uddesaṃ āgacchanti.`), extract/fixup **peels** them into a
heading segment + a following centered `prose` segment.
| `symbol_notes` | no | `{"*":…}` / `{"+":…}`; omit if empty |
| `flags` | no | e.g. `section_rule`; omit if empty |
| `needs_review` | no | Present only when `true` |
| `review_reasons` | no | Omit if empty |
| `heading_kind` | no | `nik` \| `boo` \| `cha` \| `h1`…`h6` — body typography level; assigned from the printed Mātikā skeleton when matched |
| `closer_level` | no | Structural unit closed by a section-closer formula (`pāḷi`, `ordinal_vagga`, `sikkhāpada`, …, `unknown`); optional cache — generate re-derives from text via `classify_section_closer` |
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
  bold lemma does not paint later plain repeats). When the Roman edition
  stroke is wrong vs Burmese, catalog `do.unbold` in `shared/transforms.json`
  (applied at generate; not baked into JSON). `enrich_cs_roman_thai.py`
  (`--force` / spacing normalize) **preserves** remappable `runs`; it does not
  re-detect bold from the PDF. If runs are wrong or lost, re-extract or run
  `scripts/fixup_bold_bbox.py`.

### Inline markers (in `value` / run values)

| Marker | Meaning |
|--------|---------|
| `{{nN}}` | Numbered footnote → `notes[N]`. Extract binds glued (`word1`) and spaced (`word 1`) callouts; spaced `1.` outline numbers are not callouts. Folding printed gāthā lines remaps per-line `{{n0}}` into a single notes list. Older JSON (literal digits / collided markers): `scripts/fixup_unbound_footnote_callouts.py` then `scripts/fixup_orphan_footnote_callouts.py`. |
| `{{*}}` / `{{+}}` | Apparatus → `symbol_notes` (also mid-paragraph spaced ` * ` / ` + ` callouts) |
| `{{[]}}` | Bracket apparatus (``[  ] …`` note, e.g. Syāma omission) → `symbol_notes["[]"]`. Body keeps the editorial `[…]` span; TeX emits `\csromansymbolfoottext{[ ]}{…}` (footnote label only — no second superscript `[ ]` next to the opener). |
| `{{()}}` | Empty-paren apparatus (``(  ) …`` note, e.g. *katthaci natthi*) → `symbol_notes["()"]`. Hosts on the first **non-folio** body `(`. Numbered footnotes whose body starts with `( )` stay numbered (`{{nN}}`), never steal onto `(150)`. Same bodyless foot-text emit as `{{[]}}`. |
| `{{sp1}}` | **Retired.** Legacy sentence-stop spacer; normalize strips to ordinary `. ` / word space. Not emitted in new extracts; TeX drops any leftover marker (no `\csromanspacer`). |
| `{{sp3}}` | **Retired.** Legacy alias of `{{sp1}}` (stripped on normalize). |

Notes stay Roman in JSON; TeX transliterates at emit time.

**Line breaks (generate):** paragraph/folio ranges like `(12-13)` /
`(12- 13)` / `(55-56)` (optional spaces around `-`) are emitted as
`\mbox{(12-13)}` with spaces around `-` collapsed, so TeX neither breaks
after the hyphen nor opens a wide `\spaceskip` gap. Dual comma refs
`(4, 24)` / `(4,24)` become `\mbox{(4, 24)}` (normalize to one space after
`,`) so TeX does not break after the comma. Single markers `(14)` are
unchanged. Stored JSON may still have `(12- 13)` or `(4,24)`.

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

- `source_layout`: `bat_line` (2 printed lines/บท), `wak_line` (4 lines/บท),
  or `mixed` (Roman CS shape: some บาท as ``วรรค, วรรค.``, long วรรค as one
  line each — typically 3 printed lines/บท).
- Wak order within each bat is fixed; roles (sadap/rap/rong/song) are implied by position.
- **Mixed print → `mixed`:** when CS prints some บาท as ``วรรค, วรรค.`` and
  others as one long วรรค per line, extract keeps all four วรรค and sets
  `source_layout: mixed`. TeX emits `\csromangathabat` only for comma-left
  บาท; stop-left บาท become two single lines (never pair two long วรรค into
  one bat column — that overflowed / stretched `\csromangathabatgap`).
  Audit marker `mixed_gatha_layout` may appear without `needs_review`.
  Repair: `fixup_mixed_gatha_layout.py` (comma+stop lefts → `mixed`;
  stop-left only → `wak_line`).
- **bat_line TeX:** each บาท emits `\csromangathabat{left}{right}` so the right
  วรรค (after the comma) shares a column; left-column width is the max left
  วรรค within that consecutive gāthā กลุ่ม (`\csromangathasetleft` /
  `\csromangathameasuregroup`). Gap between the two วรรค is `\csromangathabatgap`
  (**20pt** clear space after the left column; not printing-scaled). Measure
  payloads omit footnote *bodies* but keep `\textsuperscript{…}` callout
  proxies so page/left widths match body marks (otherwise a bat line can wrap
  mid-วรรค).
- **Overflow → one วรรค/line:** before emitting a กลุ่ม, generate measures each
  candidate bat pair (Sarabun advances + layout `word_space`) against the mode
  text block. If `leftcol + gap + right` would overflow, that บาท is emitted as
  two single lines (same as mixed stop-left), and `leftcol` is recomputed from
  pairs that still fit — so one long บาท does not inflate the column for shorter
  neighbours. No JSON change; regenerate TeX/PDF only.
  (`cs_roman_gatha_fit.py` / `measure_gatha_group_stack_keys`).
- **wak_line TeX:** each วรรค is one printed line; the บท is wrapped in
  `\csromangathawak{...}` so the block is centered inside the shared optical
  page box (lines stay left-aligned in a wak-width box). `\csromangathawakwidth`
  is the max wak line on the page (`\csromangathameasurewak`), so every wak บท
  on that page shares one center axis even when bat_line and wak_line alternate
  in the same กลุ่ม.
- **mixed TeX:** same optical กลุ่ม as bat_line (no `\csromangathawak`); printed
  lines are a mix of `\csromangathabat{…}{…}` and single-วรรค lines (stop-left
  บาท and fit-overflow บาท).
- **1 บทครึ่ง** (3 บาท / 6 วรรค): one segment with three `bats` (no inter-stanza
  gap in TeX). Legacy extracts may still split as full บท + irregular half;
  the generator joins that pair without `\\[\gathastanzaskip]` **only when both
  halves share the same `source_layout`** (never merge wak_line + bat_line).
  Extract appends a leftover บาท only when it is **bat_line** verse (not wak
  pairs / speech-intro / narrative). Repair stored JSON with
  `fixup_false_gatha_prose.py`.
- **Block-joined verse lines:** when the PDF text layer omits a blank line
  between consecutive gāthā printed lines, `_split_blocks` joins them into one
  paragraph (`A, B.{{sp1}} C…`). Fold expands those joins
  (`expand_glued_gatha_printed_lines`) before bat/wak split and before
  length-based prose demotion, so the right วรรค does not absorb the next
  printed line. Repair stored JSON with `fixup_glued_gatha_bat_lines.py`
  (also after extract in `pipeline.ps1`).
- **Section-rule tail on last บาท:** extract glues decorative `_____` onto the
  previous body line. Fold peels that tail (`split_trailing_section_rule`)
  **before** `_is_bat_printed_line` / comma-split and records `section_rule`,
  so `A, B. _____` still becomes two วรรค (not one irregular วรรค). The same
  fixup re-folds stored บาท that stayed as a single `A, B.` วรรค.

### Hanging prose

`source_layout: "hanging"`: `text` is the head line; `hanging_lines` is a list of
multi-script line entries (same shape as `text`).

Numbered KN/SN bat verses often print as first-indent head (~84 pt) + near-hang
body (~97–116 pt). Extract should fold those as ``gatha`` with ``item`` (not
hanging): hang merge skips bat+bat groups; geometry may seed first-indent
numbered bats and keep ``item`` on the บท. TeX uses ``\csromangathaitembat`` /
``\csromangathacontbat`` so the label sits outside the shared left-วรรค column
and วรรค 2/4 still align. The item number stays in the fixed ``\proseitem``
column (``\tipitakahang`` from text left; not ``\parindent``, which
``\raggedright`` zeros inside the stanza box); optical centering may indent the verse
body without dragging the number inward (same for wak ``\csromangathaitemline``).
Measure macros omit item labels so page/wak width is body-only. Older JSON that
stored them as hanging (or as bat-shaped ``prose`` + irregular 1-bat ``gatha``)
is repaired by `scripts/fixup_orphan_bat_gatha_hanging.py`. The same merge also
applies when the leftover บาท is clean ``bat_line`` with no ``item`` (e.g. after
peeling a trailing ``Name nāma.`` colophon).

### Centered labels

`source_layout: "center"`: first printed line is a short centered label (PDF
geometry: midpoint ≈ page center, width ≲ 0.55×page), **or** a short segment
(≲80 characters / ≲2 sentences) sandwiched between two already-centered
neighbors (e.g. `Evaṃ ekekaṃ…kattabbaṃ.` between `Baddhacakkaṃ.` and
`Idaṃ saṃkhittaṃ.`). Set at extract / geometry fixup; does not change
`segment_type`. TeX emits `\csromancenter` (body size, prose leading — not the
airy `\nitthitam` closer band) for centered prose and plain title labels; true
section closers (`niṭṭhitaṃ`, samattaṃ / samatto formulas, and ordinal category
closers such as `ปริมณฺฑลวคฺโค ปฐโม.` / `…vaggo paṭhamo.`) still use `\nitthitam`.
Bold titles, titles with `section_no`, and `heading_kind` keep their heading macros
except when the body matches a section-closer formula (closer wins) or a plain
`Idaṃ …` / `อิทํ …` centered label (assigner clears `heading_kind`; generate
emits `\csromancenter` even if mistagged; older JSON:
`scripts/fixup_idam_center_labels.py`). Gap before a center run is
optical prose paragraph air (`\csroman@closergap` =
`\tipitakaparskip+0.3\baselineskip`, same compensation as gāthā inter-บท);
after a closer band the deferred closer bottom air is that gap (symmetric
with the top) — TeX suppresses an extra `\parskip` on the following prose
block (`\csromanapplyclosergap`), and generate does not stack another
`\tipitakaparskip` before a following center label.
Consecutive center lines share prose leading (1.2× baselineskip), not an
extra parskip between each line.

**PDF line match:** geometry tags the segment's first body line via a prefix
gate, then picks the **longest shared normalized prefix** among candidates on
that page so co-page labels with a shared opening (e.g. 01Vin01 p.157
`Vatthuvisārakassa ekamūlakassa khaṇḍacakkaṃ…` vs `…baddhacakkaṃ.`) do not
steal each other's `x0`/`width`. Re-tag stored JSON with
`scripts/fixup_center_layout.py`.

**Heading cues (extract basics):** a body heading should look like a label —
typically **bold** and **centered** in the CS PDF — and should align with the
printed Mātikā when levels matter. A trailing en/em dash (`–` / `—`) means
speech or verse lead-in (`…abhāsi–`, `…paṭicodetha–`), **not** a title; extract
keeps those as prose. Short uppercase guesses (`weak_heading_heuristic`) are
kept as `title` only when center geometry confirms them; otherwise they are
demoted. Older mistags: `scripts/fixup_false_heading_guesses.py`.

**Glued closer after verse/prose stop:** when a section-closer formula follows a
sentence stop on the same printed line as the last gāthā วรรค (or prose)
— e.g. `…จาติ. มูลปณฺณาสโก สมตฺโต.` — extract peels the trailer into a
`niṭṭhitaṃ` segment so TeX uses the centered closer band instead of
overstretching `\csromangathabat`. Gendered endings include Thai `สมตฺโต` /
`นิฏฺฐิโต` (leading vowel โ) and Roman `samatto` / `niṭṭhito`, not only
`สมตฺตํ` / `นิฏฺฐิตํ`. Older JSON: `scripts/fixup_glued_section_closers.py`.

**Closer structural level (`closer_level`):** optional cache of what unit the
formula closes, from longest-rightmost lexical cues on the closer string
(`classify_section_closer` in `cs_roman_text.py`) — e.g. `pāḷi`,
`saṃyutta_pāḷi`, `khandhaka`, `ordinal_vagga`, `sikkhāpada`, `kathā`,
`analytic`, `unknown`. Generate always re-derives from text (JSON is audit /
enrich only). Visual TeX uses three tiers via `closer_tier(level)`:

| Tier | Levels (examples) | TeX |
|------|-------------------|-----|
| `major` | `*pāḷi`, `nikāya`, `khandhaka`, `kaṇḍa`, `paṇṇāsaka`, `nipāta` | `\nitthitammajor` (+ruled / withcloser*) — normalsize + bfseries + larger air |
| `mid` | `ordinal_vagga`, `vagga`, `saṃyutta` | `\nitthitammid` (+ruled / withcloser*) |
| `leaf` | `sikkhāpada`, `sutta`, `kathā`, `bhāṇavāra`, `vatthu`, `pārājika_unit`, `peyyāla`, `analytic`, `unknown` | `\nitthitam` (current default band) |

Never enlarge closer type beyond `\normalsize`. Unmatched formulas stay
`unknown` → leaf (safe across volumes). Enrich stored JSON:
`scripts/fixup_closer_levels.py`. Corpus audit: `scripts/scan_closer_levels.py`.

**Two-line category closer:** rare print form where a bare nominative
category label (`โสตาปตฺติวคฺโค.`) sits on its own centered line, then the
next line is the end-formula (`อฏฺฐารสเวยฺยากรณํ นิฏฺฐิตํ.`). Together they
close the open vagga (mid tier) — not a leaf closer plus a center label.
Generate merges them via `join_two_line_category_closer` /
`take_two_line_category_closer` into one `\nitthitammid{label\\trailer}`.

**Glued expansion parenthetical:** when a long centered note
`(Appamādavaggo … vitthāretabbo.)` follows a verse/prose stop with only a
single newline in the PDF text layer, extract splits before normalize and/or
peels the trailer into centered `prose` (`source_layout: center`). Short
editorial refs `(12-13)` / `(150)` are not peeled. Older JSON:
`scripts/fixup_glued_parentheticals.py`.

**Glued section `nāma.` colophon:** short centered end-labels after a finished
pabba/kaṇḍa (etc.) — `Maddīpabbaṃ nāma.` / `มทฺทีปพฺพํ นาม.` — must not fold
as a leftover gāthā วรรค. Extract recognizes them via
`is_section_nama_colophon` and emits centered `prose`. Narrative verse that
merely ends in lowercase `… nāma.` is left alone. Older JSON:
`scripts/fixup_glued_gatha_nama_colophons.py`.

**`tassuddānaṃ`:** exact label `Tassuddānaṃ` / `ตสฺสุทฺทานํ` is a recitation
topic-summary cue (what heads were just covered in chanting) — not a heading
and not `niṭṭhitaṃ`. TeX always emits `\csromancenter` (including when bold).
Never treated as a running header (it recurs mid-volume at page tops after
summary verses). Gap before following content (usually `gatha`) is one
paragraph air from the gāthā group top (`\addvspace{\tipitakaparskip}`) — do
not stack an extra half-`\baselineskip`. Older `title` mistags:
`scripts/fixup_tassuddana_labels.py`.

**Ordinal category closers:** an open category head uses the stem noun
(`1. ปริมณฺฑลวคฺค`); after its children finish, the same name closes in
nominative plus an ordinal matching `section_no` (`ปริมณฺฑลวคฺโค ปฐโม.`).
Recognized via category markers in `cs_roman_text.py`
(`ORDINAL_SECTION_CLOSER_MARKERS_*`, starting with `วคฺโค` / `vaggo` —
extend when new families are confirmed). Not headings: assigner clears
`heading_kind`; generate emits `\nitthitammidruled` (mid tier + end rule).

These closers **always** carry `section_rule` in our edition. CS sometimes
omits the underscore rule when the closer sits on a page foot that already
has a footnote separator (pagination, not structure); our page breaks differ,
so generate / `fixup_ordinal_section_closers.py` restore the conventional
end rule even when the source flag is absent.

When a section closer immediately follows body prose (`prose` /
`prose_continuation`) or a gāthā กลุ่ม (`gatha` / `gatha_continuation`), the
generator emits one TeX unit (`\prosewithcloser*` / mid / major variants,
`proseitem*` / `prosecont*` variants, or `\csromangathagroupwithcloser*` /
mid / major) so the closer cannot orphan alone at a
page head. Standalone closers (no prose/gāthā predecessor) still use
`\nitthitam` / `\nitthitammid` / `\nitthitammajor` by tier.
Consecutive closers (e.g. prose+closer then two more `\nitthitam*`) share
one inter-line gap = max of the two tiers' air (same deferred-bottom
contract as leaf `\csroman@closerband` / `\csromanflushcloserbottom` in
`book-macros.tex`). A following heading merges closer bottom with its
before-skip via `\addvspace` (max, not sum).

### `segment_type` vocabulary

| Type | Role |
|------|------|
| `prose` | Body paragraph |
| `prose_continuation` | Same unit continued on next printed page |
| `piṭaka` / `gambhīra` / `namakkāraṃ` / `chapter` / `title` / `niṭṭhitaṃ` | Structural |
| `tassuddānaṃ` | Recitation topic-summary label (`Tassuddānaṃ` / `ตสฺสุทฺทานํ`) — not a TOC heading and not an end-formula; following mnemonic summary verses stay `gatha` |
| `gatha` | One stanza |
| `note` | Orphan / unattached footnote |

`heading_kind` (when set) overrides visual macros in TeX over `segment_type`.
Under a vagga stack, Mātikā assignment typically uses `h1` = vagga, `h2` =
sikkhāpada / rule, `h3` = vatthu / paññatti / vibhaṅga.

| Kind | Role | TeX |
|------|------|-----|
| `nik` | piṭaka | `\pitaka` |
| `boo` | book / gambhīra | `\gambhira`. Printing/reading: a *subsequent* distinct pāḷi (after the volume’s first) is preceded by `\csromanpalirecto` (clearpage + `\csromanensureoddpage`) so the open stack starts on a recto; nikāya prelude reprinted before that gambhīra moves with it. Exact gambhīra text repeats (source running-head furniture) are skipped at generate; repair with `fixup_glued_running_headers.py`. |
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
  Matching PDF lines ignores mid-line sentence leftovers after a stop
  (CS pot-ma-gyi `word. . Next…` on a flush wrap line) so they cannot steal
  geometry from a later indented paragraph that starts with the same words.
  Repair stored JSON: `fixup_page_start_continuation.py` (also in the
  fixup pipeline).
- Footnotes stay on the segment where the callout appears.
- In TeX output, each footnote mark and its body must share the same
  physical page (`shared/style/footnotes.tex`: `\insert` natural note box,
  `\@makecol` repacks sealed boxes onto a fixed 3-column grid; audit with
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
fields. It ignores document stats and review
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
must differ. To re-apply edition `par_skip` / `gatha_stanza_skip` on stored
layout files: `python scripts/fixup_edition_layout_rhythm.py --all`.

```json
{
  "layout": {
    "word_space": 3.5,
    "line_space": 1.5,
    "par_indent": "21.6pt",
    "par_skip": "8pt",
    "gatha_stanza_skip": "8pt",
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
| `word_space` | positive number | absolute interword for **body** (fontspec `WordSpace` units); overwrites preamble via `\spaceskip` = `(target / preamble WordSpace) × fontdimen` of the current face. Footnotes clear `\spaceskip` after `\footnotesize` so TeX uses the face's natural interword glue (not this key). |
| `line_space` | positive number | `\linespread` |
| `par_indent` | dimension | `\tipitakahang` / `\parindent` |
| `par_skip` | dimension | `\tipitakaparskip` / `\parskip` (plus/minus glue fixed in TeX); edition default `8pt`. This is **extra** air on top of `\baselineskip` packing — visible paragraph gap ≈ open leading + `par_skip`. |
| `gatha_stanza_skip` | dimension | `\gathastanzaskip` — **extra** air between บท (default `8pt`, keep equal to `par_skip`). Multi-line stanza `\vtop`s cannot use `\baselineskip` packing, so TeX inserts `\vskip\gathastanzaskip+0.3\baselineskip` with `\nointerlineskip` (the `0.3\baselineskip` term restores open leading that prose gets from interline glue; tuned on 01Vin01 printing). |
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
Primary keep-with-next for `h1`…`h6` / chapter titles lives in
`shared/style/book-macros.tex` (`\csromanheaderbody` / `\csromanchapterheadbody`:
`\Needspace` for title + ≥2 body lines, then `\nobreak` after the title).
Consecutive structural titles (`cha` / `h1`…`h6`) use a tight
`\csromanheaderstackskip` (~14pt scaled) so a saṃyutta→vagga→sutta stack
matches ordinary book practice and source CS Roman inter-title ink gaps
(~17pt); after prose the level before-skip ladder applies (more above than
below, without an extra `\baselineskip`). `\csromanclearheaderstack` runs at
the start of prose / gāthā / center / closer / section-rule so the next title
gets a normal section break.
Use `before_orders` only for residual orphans after that contract.

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
