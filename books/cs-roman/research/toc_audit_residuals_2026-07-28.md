# TOC residuals after pipeline fixes (2026-07-28)

Draft notes while the full rebuild/audit runs. Update after
`audit_cs_roman_toc.py` completes on the rebuilt set.

## Fixes shipped in this pass

1. **parse_matika** — multi-page lists (`21-30-38`, `... 21-30-38`);
   filter `…pāḷi …bhāga` running headers.
2. **matching** — earliest `boo` match; skip duplicate unpaged titles;
   fold `ḷ/l`, `ṇ/n` in `normalize_title`.
3. **MatikaTocPlanner** — hypertarget anchors; structural inherit;
   targeted inversion remap; deferred `\csromantocmarkat` /
   `\csromantocmarkref` + raw `\bookmark`.
4. **chapterheadpage** — no extra `\clearpage` / odd-page bump after
   `\csromanpage` (sync folio preserved).
5. **reading** — emit `ฉ.N` when a segment carries TOC marks.

## Sample results (post-fix, before full-batch finish)

| Volume | sync | reading notes |
|---|---|---|
| 01Vin01 | PASS (244/244) | folio mismatches only |
| 05Vin05 | 4× +1 page offs (complete list) | folio mismatches |
| 06Di01 | PASS | folio mismatches |
| 22Khu05 | 5× +1 page offs (complete list) | folio mismatches |
| 38Abhi10 | PASS (was 30 missing) | folio mismatches |

## Expected remaining manual / hard cases

- Sync **+1** folio where heading sits at a page turn and layout still
  ships the mark onto the next sheet (not fixed by chapterheadpage alone).
- Reading **folio context** when a destination page has no `ฉ.N` yet
  (partially mitigated; some heads may still lack markers).
- Body headings missing from extract → unmatched Mātikā rows with no
  inheritable child.
- Paṭṭhāna multi-page entries anchored on the **first** page only.
- Duplicate generic titles (Paññatti, Uddānagāthā, …) with wrong fuzzy
  latch if page gate cannot decide.

## Re-audit command

```powershell
cd books/cs-roman
python scripts/audit_cs_roman_toc.py `
  --output-json research/toc_audit_2026-07-28_post.json `
  --output-md research/toc_audit_2026-07-28_post.md
```
