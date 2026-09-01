# คู่มืองาน CS Roman

หน้าเดียวสำหรับงานประจำ สัญญาข้อมูลอยู่ที่ [`SCHEMA.md`](../SCHEMA.md) กระบวนการซ่อมอยู่ที่ [`fixup_process.md`](fixup_process.md)  
เป้าหมายและกระบวนการ (ประเด็นสื่อสาร): [`goals_and_process.md`](goals_and_process.md)  
**นโยบายผลปริวรรต / โรมันฉบับพิมพ์ (ห้ามแก้ segments โดยตรง):** [`transliteration_policy.md`](transliteration_policy.md)

## บทบาท

ผู้ใช้แจ้งสิ่งที่เห็นผิด (เล่ม หน้า อาการ)  
เอเจนต์เป็นฝ่ายจำแนก เลือกไฟล์ ค้นคำ แก้ ทดสอบ สร้าง PDF เล่มที่โดน แล้วสรุปสั้น ๆ ว่าให้ตรวจหน้าไหน

พอแจ้งปัญหา อย่างน้อยบอก **เล่ม** และ **อะไรผิด** หน้าหรือคำที่เห็นจะยิ่งเร็ว ไม่ต้องบอกว่าจะแก้ไฟล์ไหน

## กฎทอง: ผลปริวรรตและโรมันฉบับพิมพ์

งานปรับปรุงผลปริวรรตและข้อความโรมันเทียบฉบับพิมพ์จะทำต่อเนื่อง — **ห้ามแก้ผลใน `segments.json` โดยตรงเด็ดขาด** ไม่ว่าจะเห็นใน `output/` หรือ `volumes/…/data/segments.json`

| ต้องการแก้ | แก้ที่ |
| --- | --- |
| โรมัน / วรรคตอน / อรรถ / ตัวหนาผิด | [`shared/transforms.json`](../shared/transforms.json) |
| เลขข้อพิมพ์ผิด | [`shared/item_corrections.json`](../shared/item_corrections.json) |
| จังหวะหน้า | `volumes/<id>/data/layout.json` |
| ถอด PDF ผิดซ้ำ | extract + `pipeline.ps1` |
| โครงสร้าง JSON เก่า | fixup ใน manifest |

รายละเอียด ตัวอย่าง และสิ่งที่ห้าม: [`transliteration_policy.md`](transliteration_policy.md)

## แก้ที่ไหน

| อาการ | แก้ที่ | ตรวจ | สร้างใหม่ |
| --- | --- | --- | --- |
| โรมันผิด / พม่าผิด / ตัวหนาผิด | [`shared/transforms.json`](../shared/transforms.json) | `scan_transform_hits.py` แล้วทดสอบแคตตาล็อก | `generate` แล้วค่อย `latexmk` |
| เลขข้อพิมพ์ผิด (สลับหลัก ฯลฯ) | [`shared/item_corrections.json`](../shared/item_corrections.json) | ทดสอบแคตตาล็อก | extract/fixup แล้ว `generate` |
| PDF ต้นทางผิดซ้ำทุกครั้งที่ถอด | สคริปต์ extract + ทดสอบ | unittest ไฟล์นั้น | `.\pipeline.ps1 -Volume …` |
| JSON เก่าค้าง | `fixup_*.py` ใน manifest | `scan_fixup_residuals.py --strict` | pipeline แล้ว sync |
| จังหวะหน้า / บังคับขึ้นหน้า | `volumes/<id>/data/layout.json` | สายตา | generate + latexmk |
| มหภาค TeX | `shared/style/` | สายตา | latexmk (`-SkipGenerate` ถ้าไม่แตะ JSON) |
| สมาสขึ้นบรรทัดผิด | `shared/sandhi_breaks_overrides.json` | generate | generate |

ห้ามแก้ `output/` หรือ `volumes/…/data/segments.json` ด้วยมือเพื่อแก้ตัวสะกด วรรคตอน ปริวรรต โรมันฉบับพิมพ์ หรือเลขข้อ — ใช้ `transforms.json` / `item_corrections.json` (ดู [`transliteration_policy.md`](transliteration_policy.md))

`replace` = โรมันผิด, `annotate` = คงคำพิมพ์แล้วเชิงอรรถลงท้าย ` – ม.พ.ป.`, `unbold` = ตัวหนาผิดอย่างเดียว  
กฎไม่แตะเนื้อเชิงอรรถของฉบับพิมพ์ (`notes` / `symbol_notes`) — แค่ตัวบท คาถา และบรรทัดห้อย  
`when.match` ที่ไม่มี `+` คือทั้งคำ (`bandhiṃ` ไม่โดน `bandhiṃsu`) คำต่อท้ายหรือหน้าในคำเดียวกันใช้ `+` ที่ต้นหรือท้าย (`+bandhiṃ`, `bandhiṃ+`, `+bandhiṃ+`)  
ปักตำแหน่งที่ `when.loci` เท่านั้น แต่ละจุดมี `volume` และจะมี `page` / `order` ก็ได้ หลายเล่มใส่หลายจุดในกฎเดียว

## ไฟล์ไหนคือต้นทาง

- **เก็บใน git:** `volumes/<id>/data/` — แก้จังหวะพิมพ์ที่ `layout.json` ชุดนี้
- **ของชั่วคราวหลังถอด PDF:** `output/` (ไม่เข้า git) — `.\build.ps1` จะคัดลอกจาก `output/` ทับ `volumes/` ถ้ามีไฟล์ใน `output/`
- **กฎฉบับพิมพ์:** `shared/transforms.json` (ตัวสะกด) และ `shared/item_corrections.json` (เลขข้อ) — ไฟล์กลางทั้งฉบับ ไม่มีไฟล์รายเล่ม

โหมดที่ส่งมอบคือ `sync` (หน้าตรงต้นฉบับ) และ `printing` (165×230 มม.)  
`page_layout_reading_mode` และ `scripts/scratch/archive/reading-mode/` เป็นของเก่า อย่าเปิดเป็นงานปัจจุบัน

โฟลเดอร์ `01Vin01` คือเล่มที่ 1 ของฉบับเดียวกับที่เว็บเรียก `ch/pali2552ro` / `vol-01` (ชุด 40 เล่มใน `website/csm_pali_volumes.py`)  
`27khu10` คือเล่มที่ 27 — ตัว `k` พิมพ์เล็ก เป็นข้อยกเว้น อย่าเปลี่ยนชื่อโฟลเดอร์ในงานประจำ  
ยังไม่ย้ายข้อความขึ้นคลังเว็บ

## คำสั่งที่ใช้บ่อย

จากรากรีโป ถอด/ซ่อม/ทดสอบชุดใหญ่ใช้ Docker จากโฟลเดอร์ `books/cs-roman` สร้าง PDF ใช้โฮสต์

```powershell
# ค้นคำก่อนแก้ transforms.json
docker compose exec -T web python books/cs-roman/scripts/scan_transform_hits.py --match dighamaddhānaṃ
docker compose exec -T web python books/cs-roman/scripts/scan_transform_hits.py --rule-id roman-dighamaddhana-long-i
docker compose exec -T web python books/cs-roman/scripts/scan_transform_hits.py --catalog

# เล่มเดียว → PDF พิมพ์
cd books/cs-roman
.\build.ps1 -Volume 01Vin01 -Mode printing

# ถอด + ซ่อม + ประตู residual (Docker)
.\pipeline.ps1 -Volume 01Vin01

# ทดสอบ
cd <รากรีโป>
.\books\cs-roman\scripts\run_tests.ps1
.\books\cs-roman\scripts\run_tests.ps1 -Module test_cs_roman_transforms

# รายงานเชิงอรรถ annotate → tmp/cs-roman/annotate_<เล่ม>.html
python books/cs-roman/scripts/report_annotate.py --volume 01Vin01
```

`follow_ups` และ `post_pdf_audits` ใน manifest เป็นรายการมือ ไม่ได้รันเองหลังสร้าง PDF

## ที่วางของชั่วคราว

| ที่ | ใช้ทำอะไร |
| --- | --- |
| `tmp/` | โพรบทั้งรีโป ไม่เข้า git |
| `tmp/cs-roman/` | รายงาน annotate HTML และโพรบเล่ม ไม่เข้า git |
| `books/cs-roman/research/_*` | สแกนชั่วคราว ไม่เข้า git |
| `books/cs-roman/scripts/_*` | สคริปต์ครั้งเดียว ไม่เข้า git |
| `books/cs-roman/scripts/scratch/` | ของเก่า อย่าเปิด `archive/` |

อย่าใช้ไฟล์ `_` เป็นขั้นตอนปกติ — ใช้ `scan_transform_hits.py` หรือสคริปต์ใน pipeline

แก้ JSON ภาษาไทยด้วยเครื่องมือแก้ไขหรือ Python `encoding="utf-8"` ห้าม `Get-Content` โดยไม่ใส่ `-Encoding utf8`
