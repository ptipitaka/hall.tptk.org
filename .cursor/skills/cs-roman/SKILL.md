---
name: cs-roman
description: >-
  Leads CS Roman book repair when the user reports a page problem. Use when
  they mention a CS Roman volume, folio, typo, footnote, heading, gāthā,
  printing PDF, transforms.json, layout.json, segments, fixup, extract, or
  sandhi. Drive the playbook loop; reply in short Thai.
---

# CS Roman

The user reports defects. You lead the repair. Read
[`books/cs-roman/docs/playbook.md`](books/cs-roman/docs/playbook.md) and
[`books/cs-roman/docs/transliteration_policy.md`](books/cs-roman/docs/transliteration_policy.md)
once, then act. Do not treat README as the playbook. Do not wait for the user
to name files or commands.

## When the user reports a problem

They may send only a volume, page, and what looks wrong. That is enough.

1. Classify with the playbook table (spelling / item number / extract / old JSON / layout / TeX / sandhi).
2. If spelling: run `scan_transform_hits.py --match …` before editing. Pin `when.loci` when the same string is correct elsewhere.
3. Edit the right layer. **Never** hand-edit `output/` or `volumes/…/data/segments.json`
   for publication Roman, punctuation, transliteration, editorial notes, or
   item numbers — only `shared/transforms.json` or `shared/item_corrections.json`
   (see transliteration_policy.md).
4. Run the matching test module (`run_tests.ps1 -Module …`), not the whole suite by default.
5. Rebuild only the volumes that the scan showed (`build.ps1 -Volume … -Mode printing` on the host for catalog/TeX).
6. Stop. Tell them what to check.

Ask a question only if volume **and** what is wrong are both missing. Do not ask which file to edit.

## Reply style (Thai)

- Short complete sentences. Lead with the decision or the result.
- One screen: what was wrong, what you changed, which pages to inspect.
- No README archaeology, no jargon, no long options lists.
- Do not narrate tool calls. Do not dump hit logs; summarize counts.

Example: `คำนี้โผล่ 3 เล่ม ผิดเฉพาะ 01Vin01 จึงจำกัดเล่ม ตรวจ PDF หน้า 54`

## Where to edit

- Spelling / editorial note / false bold → `shared/transforms.json` (generate-time)
- Printed item-number typo → `shared/item_corrections.json` (extract / fixup / generate)
- Recurring extract bug → extract + test, then `pipeline.ps1 -Volume …`
- Old JSON → `fixup_*.py` in `fixup_manifest.json` ([`docs/fixup_process.md`](books/cs-roman/docs/fixup_process.md))
- Page rhythm → `volumes/<id>/data/layout.json` (git copy)
- TeX macros → `shared/style/`, not `body.*.generated.tex`
- Sandhi exceptions → `shared/sandhi_breaks_overrides.json`

## Files

- Git copy: `volumes/<id>/data/` (content JSON is extract-normalized — not publication-final)
- Extract staging: `output/` (gitignored). **Not** where to fix Roman/transliteration; `build.ps1` may copy staging onto volumes
- Website catalog `ch/pali2552ro` `vol-01` = folder `01Vin01`. Do not import to archive in ordinary book work

## Transforms

- `replace` = Roman wrong; `annotate` = keep printed token + footnote ending ` – ม.พ.ป.`; `unbold` = weight only
- Catalog never rewrites edition `notes` / `symbol_notes` (apparatus as extracted)
- Catalog `when.match` is an exact whole word; `+` at start/end marks affixes (`+bandhiṃ`, `bandhiṃ+`, `+bandhiṃ+`)
- Prefer unique `when.match`. Same token mixed right/wrong: one rule with `when.loci` (`volume` required; `page` / `order` optional). Several volumes are several locus entries
- Do not add a long per-rule test method unless locking a non-hit

Scratch: `tmp/` (annotate HTML: `tmp/cs-roman/`) or `scripts/scratch/`. Not `research/_*.txt` as a normal step. JSON: UTF-8 editor/Python, never PowerShell `Get-Content` without `-Encoding utf8`.
