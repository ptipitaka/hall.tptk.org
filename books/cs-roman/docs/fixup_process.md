# กระบวนการ Fixup CS Roman

เอกสารอ้างอิงเดียวของเหตุการณ์ซ่อม segments/layout หลัง extract  
งานประจำ (แก้ที่ไหน / คำสั่งค้นคำ): [`playbook.md`](playbook.md)  
**Registry:** [`scripts/fixup_manifest.json`](../scripts/fixup_manifest.json)  
**Runner:** `scripts/run_cs_roman_fixups.py` · **Gate:** `scripts/scan_fixup_residuals.py`

เมื่อปรับกระบวนการ / เพิ่ม–ลบ–เปลี่ยน fixup **ต้องอัปเดตเอกสารนี้และ manifest คู่กันเสมอ** (กฎ `.cursor/rules/cs-roman-fixup-docs-sync.mdc`)

---

## ภาพรวม

```
extract (optional)
  → run_cs_roman_fixups.py --pipeline   # ซ่อมตามลำดับใน manifest
  → scan_fixup_residuals.py --strict     # ล้มถ้ายังค้าง (gate=strict)
  → headings → prepare → build PDF
  → post-PDF audits (scan_*)              # คนละชั้น ไม่ใช่ JSON fixup
```

ลำดับใน manifest มีความหมาย: peel (closer / gāthā / header) มาก่อน แล้วจึง `unbound_footnote_callouts` เพราะ peel อาจเผยเลข callout ที่ติดคำ ถ้า rebound ก่อน peel ประตู `--strict` จะเจอ residual หลัง peel (เช่น 03Vin03)

Entrypoint: `books/cs-roman/pipeline.ps1` (มี `-SkipFixups` / `-SkipFixupGate`)

---

## ชั้นงาน (ห้ามปน)

| ชั้น | ทำอะไร | บังคับด้วย |
|------|--------|------------|
| **A. Extract normalize** | กันเกิดซ้ำใน `extract_cs_roman_pdf.py` | test + SCHEMA |
| **B. JSON fixup** | ซ่อม artifact เดิม (`--volume` / `--all` / `--dry-run`) | manifest + pipeline + `--strict` |
| **C. Post-PDF audit** | คุณภาพหน้าหลัง build | `scan_*` ใน manifest `post_pdf_audits` |

---

## ฟิลด์ manifest (fixups)

| ฟิลด์ | ความหมาย |
|--------|----------|
| `id` | รหัสคงที่ |
| `script` | สคริปต์ใต้ `scripts/` |
| `case` | ชื่อกรณีอ้างอิงในเอกสารนี้ |
| `pipeline` | `true` = รันใน `--pipeline` / `pipeline.ps1` |
| `gate` | `strict` ล้มถ้า residual>0 · `warn` รายงาน · `off` ไม่ตรวจ |
| `scope` | `all` (`--all`) หรือ `per_volume` (วนทุกเล่ม) |
| `requires_pdf` | ต้องมี source PDF |
| `follow_ups` | id ที่ควรรันต่อ (บันทึกใน manifest; runner รันตามลำดับ pipeline) |

---

## กรณี JSON fixup (ครบตาม manifest)

| case | อาการ | สคริปต์ |
|------|--------|---------|
| `unbound_footnote_callout` | เลข callout ติดคำ / `{{n0}}` ชนกันหลังพับ gāthā | `fixup_unbound_footnote_callouts` (PDF) |
| `footnote_callout` | callout หลุด / folio ขโมยเลขหมายเหตุ | `fixup_orphan_footnote_callouts` |
| `printable_dash` | U+23AF วาดไม่ได้ | `fixup_printable_dashes` |
| `midword_hyphen` | ยัติภังค์กลางคำ editorial ใน Roman | `fixup_solid_midword_hyphens` |
| `glued_section_closer` | closer ติดท้ายประโยค | `fixup_glued_section_closers` |
| `glued_cakka_closer` | `Khaṇḍacakkaṃ.` closer ติดท้าย prose (ไม่ใช่สูตร niṭṭhitaṃ) | `fixup_glued_cakka_closers` |
| `closer_level_cache` | ยังไม่มี/ผิด `closer_level` | `fixup_closer_levels` |
| `glued_parenthetical` | วงเล็บขยายติดท้ายวรรค | `fixup_glued_parentheticals` |
| `tassuddana_label` | exact `ตสฺสุทฺทานํ` เป็น `title`/`\titlehead` | `fixup_tassuddana_labels` |
| `idam_center_label` | `Idaṃ` เป็น heading ผิด | `fixup_idam_center_labels` |
| `false_heading` | title ปลอม (speech-intro / weak) | `fixup_false_heading_guesses` |
| `ordinal_section_closer` | closer ลำดับ + `section_rule` | `fixup_ordinal_section_closers` |
| `false_gatha_prose` | ร้อยแก้วปนในก้อน gāthā | `fixup_false_gatha_prose` |
| `glued_gatha_nama_colophon` | ป้าย `Name nāma.` ติดท้ายกลอน | `fixup_glued_gatha_nama_colophons` |
| `orphan_bat_gatha_hanging` | คาถาเลขข้อถูกเก็บเป็น hanging / หรือแยก prose+gāthā 1-bat → โปรโมตเป็น `gatha` (bat/wak) คง `item` | `fixup_orphan_bat_gatha_hanging` |
| `glued_gatha_title` | ป้าย uddāna ติดกลอน | `fixup_glued_gatha_titles` → แล้วรันมือ `gatha_geometry` + `center_layout` |
| `gatha_geometry` | จัด bats หลัง peel ชื่อกลอน (ต้อง PDF; ไม่ใน pipeline อัตโนมัติ) | `fixup_gatha_geometry` |
| `center_layout` | คืน `source_layout: center` (ต้อง PDF; คู่กับ geometry) | `fixup_center_layout` |
| `glued_gatha_bat` | บรรทัดกลอนติดกันจาก PDF join | `fixup_glued_gatha_bat_lines` |
| `mixed_gatha_layout` | mixed / wak_line ผิด | `fixup_mixed_gatha_layout` |
| `glued_uddesa_heading` | uddesa ติด prose | `fixup_glued_uddesa_headings` |
| `false_pa_hyphen` | `-pa-` ผิด | `fixup_false_pa_hyphen_joins` |
| `glued_running_header` | running header ติดเนื้อ | `fixup_glued_running_headers` |
| `page_start_continuation` | ขึ้นหน้าใหม่ไม่ใช่ continuation | `fixup_page_start_continuation` |
| `edition_layout_rhythm` | `par_skip` / `gatha_stanza_skip` ใน layout | `fixup_edition_layout_rhythm` |
| `midword_bold_split` | ตัวหนาขาดกลางคำหลังต่อยัติภังค์ (เหลือ `a`/`อ`) | `fixup_midword_bold_splits` |
| `item_correction` | เลขข้อพิมพ์ผิด (เช่น สลับหลัก 238→283) ตาม `shared/item_corrections.json` | `fixup_item_corrections` |
| `nitthitam_false_bold` | bold ปลอมบน closer (มือ/รายเล่ม) | `fixup_nitthitam_false_bold` |
| `bold_bbox` | bold จาก bbox PDF (มือ) | `fixup_bold_bbox` |

กรณีที่ **ยังไม่มีสคริปต์** (อย่า retag แบบ ad-hoc โดยไม่มีทางเข้า manifest): เช่น `Tassuddānaṃ.` มีจุดท้าย, ชื่อบทติด `Tassuddānaṃ` — ออกแบบ peel + ทดสอบ + เพิ่มใน manifest ก่อน

---

## กรณี post-PDF audit

| case | สคริปต์ |
|------|---------|
| `orphan_note_audit` | `scan_orphan_notes.py` |
| `closer_level_audit` | `scan_closer_levels.py` |
| `margin_overflow_audit` | `scan_margin_overflow.py` |
| `orphan_heading_audit` | `scan_orphan_headings.py` |
| `widow_stub_audit` | `scan_widow_stubs.py` |
| `sandhi_gap_audit` | `scan_sandhi_break_gaps.py` |

ชั้นนี้ไม่ผ่าน `--strict` ของ JSON residual (คนละเกณฑ์หลัง build)

---

## คำสั่งที่ใช้บ่อย

```powershell
# จาก repo root (Docker)
docker compose exec -T web python books/cs-roman/scripts/run_cs_roman_fixups.py --pipeline
docker compose exec -T web python books/cs-roman/scripts/scan_fixup_residuals.py --strict

# เล่มเดียว
docker compose exec -T web python books/cs-roman/scripts/run_cs_roman_fixups.py --pipeline --volume 13Sam02
docker compose exec -T web python books/cs-roman/scripts/scan_fixup_residuals.py --strict --volume 13Sam02

# dry-run ทั้งคลัง (ไม่เขียน)
docker compose exec -T web python books/cs-roman/scripts/run_cs_roman_fixups.py --pipeline --dry-run
```

ผ่าน pipeline:

```powershell
cd books/cs-roman
.\pipeline.ps1 -SkipExtract          # ยังรัน fixup + gate
.\pipeline.ps1 -SkipFixups           # ข้ามซ่อม (ไม่แนะนำ)
.\pipeline.ps1 -SkipFixupGate        # ข้ามประตู residual
```

---

## เมื่อมีเหตุการณ์ fixup ใหม่ (เช็กลิสต์)

1. แก้ต้นเหตุใน extract/generate ถ้าทำซ้ำได้ + regression test  
2. เขียน `fixup_*.py` (`--volume` / `--all` / `--dry-run`) พิมพ์ยอดท้ายแบบที่ `parse_residual_count` อ่านได้  
3. เพิ่มรายการใน `fixup_manifest.json` (`pipeline` / `gate` / `case`)  
4. อัปเดตตารางกรณีในเอกสารนี้  
5. ผูกแล้วโดยอัตโนมัติผ่าน `--pipeline` — **ห้าม** hardcode บล็อกใหม่ใน `pipeline.ps1`  
6. รัน `scan_fixup_residuals.py --strict` ให้ผ่านหลัง apply  

---

## ห้าม

- แก้ JSON/PDF ทีละจุดแล้วจบโดยไม่มีสคริปต์ซ้ำได้  
- เพิ่ม fixup ในแชท/scratch แล้วไม่ใส่ manifest  
- เปลี่ยนลำดับ/ความหมาย gate โดยไม่อัปเดตเอกสารนี้  
- ใช้ `-SkipFixupGate` เป็นทางปกติเมื่อทราบว่ายังมี residual  
