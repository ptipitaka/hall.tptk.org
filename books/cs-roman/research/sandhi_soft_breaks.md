# Sandhi soft breaks (DPD)

สถานะ 2026-08-06 — ตัดคำสนธิ/สมาสตามความหมายเพื่อขึ้นบรรทัดใน PDF

## สิ่งที่ทำแล้ว

- แหล่งจุดตัด: `lookup.deconstructor` (+ fallback `dpd_headwords.compound_construction` แล้ว `construction`) จาก DPD SQLite ท้องถิ่น
  - `compound_construction`: แกะ `<b>…</b>` markup ที่ mark ส่วนท้าย (case ending) ของ part แรกที่สนธิกลืน — strip เฉพาะ `ṃ` เมื่อเป็น niggahita-doubling (`aṃ+p→app`) เก็บสระไว้; strip ทั้งหมดเมื่อเป็น case-ending drop (`āya`, `ena`, `assa`)
  - `construction`: ใช้ `parse_plus_parts` (strip `<b>` tags, `>` derivation markers, ขึ้นบรรทัดใหม่)
- กฎสนธิใน `align_parts` (`_candidate_ends`):
  - elision (`a+e/o→e/o`): part ลงท้ายด้วยสระ ผิวมีสระต่างชนิด → ตัดที่จุดนั้น
  - contraction (`a+a→ā`, `a+i→ā`, `a+u→o`): สองสระสั้นกลืนเป็นสระยาว/ทวิสระ → `_CONTRACTION_TO` map
  - long-vowel fusion (`ā+ā→ā`): ส่วนท้ายสระยาว → ให้ part ถัดไปเป็นเจ้าของ
  - same-vowel merge (`a+a→a`): สระเดียวกันกลืนเป็นตัวเดียว → part ยกสระให้ part ถัดไป
  - niggahita drop (`ṃ+C→…`): part ลงท้ายด้วย `ṃ` ผิวมีพยัญชนะ → ตัด `ṃ` ทิ้ง
  - niggahita consonant doubling (`aṃ+p→app`): ผิวมีพยัญชนะซ้อน → ข้ามตัวแรก
  - niggahita nasal assimilation (`ṃ+c→ñc`, `ṃ+k→ṅk`, `ṃ+t→nt`, `ṃ+p→mp`): ผิวมีนาสิก + พยัญชนะ → ข้ามนาสิก
  - last-vowel case-ending substitution (`...ga+o→...go`): `is_last` ยอมสระท้ายต่างจาก stem
- Fallback สำหรับคำที่ไม่มี `lookup` row: strip prefix `na/neva/no` แล้ว lookup ส่วนที่เหลือ; strip case ending แล้ว lookup `dpd_headwords.lemma_1`
- แคช: [`shared/sandhi_breaks.json`](../shared/sandhi_breaks.json) — Roman → ชิ้นผิวที่ตัดได้
- Override curated: [`shared/sandhi_breaks_overrides.json`](../shared/sandhi_breaks_overrides.json) — คำที่ DPD/align ให้จุดตัดไม่ได้; ชิ้นผิวต้องต่อกันได้ตรงคีย์; ทับแคช DPD; rebuild แคชไม่เขียนทับไฟล์นี้
- Generate: ฉีด `{{sb}}` → TeX `\-` อัตโนมัติทุก mode (ไม่แก้ `segments.json`)
- เกณฑ์รอบแรก: `thai_display_len >= 15`
- ตัวกรองความยาวชิ้น: ฉีดเฉพาะจุดตัดที่ทั้งสองด้านยาว `>= 3` Thai glyph (ดู `DEFAULT_MIN_FRAGMENT_LEN`) — จุดตัดที่ทิ้งเศษ 2 ตัว (เช่น `sippikasambukā|pi` → `ปิ`) ถูกทิ้ง ให้ TeX เลื่อนทั้งคำแทน
- คง `hyphenrules=nohyphenation` — ตัดเฉพาะจุดที่ inject
- `ensure_sandhi_break_cache()` — ถ้าแคชหายแต่มี `vendor/dpd/dpd.db` จะสร้างแคชตอน generate แล้วรวม overrides

## วิธีใช้

ทำงานอัตโนมัติตอน generate ทุก mode ผ่าน `build.ps1`, `batch_prepare_volumes.py`,
หรือเรียก `generate_cs_roman_tex.py` โดยตรง — ไม่ต้องใส่ flag พิเศษ

```powershell
cd books/cs-roman
.\build.ps1 -Volume 01Vin01 -Mode sync
.\build.ps1 -Volume 01Vin01 -Mode printing
```

```powershell
# ครั้งแรกเท่านั้น (DB ~2GB) — ถ้ายังไม่มี dpd.db
python scripts/fetch_dpd_db.py
# บังคับสร้าง/รีเฟรชแคชทั้งคลัง
python scripts/build_sandhi_break_cache.py --all
# ปิด soft break ชั่วคราว
python scripts/generate_cs_roman_tex.py --volume 01Vin01 --mode printing --no-sandhi-breaks
```

## Coverage (สแกนคลัง 40 เล่ม)

| รายการ | ก่อน (2026-08-02) | หลัง (2026-08-06) |
|--------|------:|------:|
| Roman tokens ทั้งหมด | 145172 | 145172 |
| ยาว `thai_display_len >= 15` | 5437 | 5437 |
| มี soft-break ในแคช DPD | 2683 | 4402 |
| Override curated | 7 | 26 |
| ไม่มี / align ไม่ผ่าน | 2753 | 1012 |
| **coverage** | **49%** | **81%** |

ประมาณ **81%** ของคำยาวได้จุดตัด (เพิ่มจาก 49%) จากการเพิ่มกฎสนธิใน aligner
และเปิดใช้ `compound_construction` เป็นแหล่งหลัก

รายการคำที่ยังไม่มีในแคช: [`research/sandhi_breaks_missing.tsv`](../research/sandhi_breaks_missing.tsv) — สร้างด้วย `python scripts/scan_sandhi_break_gaps.py`

## เมื่อ DPD/align ให้จุดตัดไม่ได้

1. ยืนยันว่า `thai_display_len >= 15` ผ่าน แต่ไม่มีในแคช หรือ align ไม่ผ่าน
2. แยกชิ้นผิว Roman ที่ต่อกันได้ตรงรูปฉบับ **และ** แปลงไทยเป็น prefix สะอาดได้ (อย่าตัดค้างพินทุ เช่น `gat|u`)
3. ใส่ใน `shared/sandhi_breaks_overrides.json` แล้ว generate ใหม่ — อย่า patch TeX/segments
4. เก็บ regression ใน `test_cs_roman_sandhi_breaks.py` เมื่อเป็นเคสที่เคยพลาด

## คิวตรวจสำหรับคำที่ขยายจากคำที่แยกได้

สำหรับคำที่ขาดซึ่งมี **ส่วนนำ/ส่วนท้ายตรงคีย์ที่มีในแคชอยู่แล้ว** (เช่น
`cīvarapiṇḍapātasenāsanagilānapaccayabhesajjaparikkhārānan` =
`...parikkhārā` (มีในแคช) + `nan`) ใช้สคริปต์สร้างคิวตรวจก่อนใส่ overrides
เพราะการเทียบสตริงยาวสุดอาจตัดผิดที่ขอบมอร์ฟีมทั้งที่ Thai-slice ผ่าน

```powershell
python books/cs-roman/scripts/scan_sandhi_partial_extensions.py
# -> books/cs-roman/research/sandhi_partial_extensions.tsv
```

คอลัมน์ `thai_slice_ok` แยก `yes` (ใส่ overrides ได้หลังตรวจ) จาก `no`
(เช่น `kaḷ|ambadāyaka…` ผ่านสตริงแต่ตัดผิดขอบ — ทิ้งไว้ให้คนดูแลกาย)

ทดสอบหลักการใน `test_cs_roman_sandhi_breaks.py::PartialExtensionTests`

ผลสำรวจความคุ้มครอก (สแกน 40 เล่ม 2026-08-06):

| ประเภท | จำนวน | หมายเหตุ |
|--------|-----:|--------|
| คำที่ขาดทั้งหมด | 1012 | — |
| ขยายด้านท้าย (prefix ตรงคีย์) | 28 | Thai-slice ผ่าน 28/28 |
| ขยายด้านหน้า (suffix ตรงคีย์) | 44 | Thai-slice ผ่าน 42/44 |
| ไม่มีส่วนซ้อนกับคีย์ใดในแคช | 938 (92.7%) | ส่วนใหญ่เป็นชื่อเชิงประกอบ (`Xpupphiyattheraapadāna`) ที่ DPD ไม่ index |

หลักการเทียบสตริงล้วน ๆ กับชุดชิ้นส่วน (morpheme) ทั้งหมดในแคช คุ้มครอกสูง
(~45% แยกได้ครบ) **แต่ความแม่นยำต่ำ** เพราะแคชเก็บ surface chunk หลังสนธิ ไม่ใช่
stem จึงเจอบังเอิญผิดตำแหน่ง (เช่น `nev|ācayagāmi`, `s|añña…`) — ห้ามใช้
auto-apply; ใช้เฉพาะคิวตรวจข้างต้น

## Compose จุดตัดภายในจาก stem + suffix (inject-time)

เมื่อแคชให้แยกหยาบ `[head, tail]`:

- ถ้า `breaks[head]` ≥ 2 ชิ้น → ลอง `inner_head[:-1] + [inner_head[-1] + tail]`
  (เช่น `ākāsānañcāyatana|samāpatti`)
- ถ้า `breaks[tail]` ≥ 2 ชิ้น → ลอง `[head] + inner_tail`
  (เช่น `na|nevavipākanavipākadhammadhammo`)

ยอมรับเฉพาะเมื่อ `thai_slices_from_roman_chunks` ผ่าน **และ** typography ดีขึ้น
(ชิ้นไทยยาวสุดเล็กลง หรือเท่าเดิมแต่มีจุดตัดที่ inject ได้มากขึ้น) — ถ้าขยายได้ทั้งสองด้าน
เลือกตัวที่ max chunk เล็กกว่า วนซ้ำได้ถ้าผลยังเป็น 2 ส่วน

- คำนวณตอน `inject_soft_breaks_in_thai` เท่านั้น — **ไม่** เขียนทับ `sandhi_breaks.json`
- override ใน `sandhi_breaks_overrides.json` ที่ merge แล้วเป็นจุดเริ่ม; ถ้า override
  เป็นหลายส่วนอยู่แล้ว compose เป็น no-op

ทดสอบ: `test_compose_refines_arupa_stem_plus_suffix`,
`test_compose_iterates_for_neva_ayatana_long_form`,
`test_compose_expands_known_tail_after_prefix`,
`test_compose_rejects_when_max_chunk_worsens`

## ขอบเขตที่ไม่ทำในรอบนี้

- ไม่เปิดตัดพยางค์จาก `hyph-pi.tex`
- ไม่แสดงจุดตัดบนจอตลอดเวลา
- ไม่รัน Go deconstructor ของ DPD ใน pipeline
- ไม่ดาวน์โหลด `dpd.db` อัตโนมัติตอน build (ใหญ่เกิน; ใช้แคชที่ commit หรือ fetch ครั้งเดียว)
