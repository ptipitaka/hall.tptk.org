# Sandhi soft breaks (DPD)

สถานะ 2026-08-02 — ตัดคำสนธิ/สมาสตามความหมายเพื่อขึ้นบรรทัดใน PDF

## สิ่งที่ทำแล้ว

- แหล่งจุดตัด: `lookup.deconstructor` (+ fallback `dpd_headwords.construction`) จาก DPD SQLite ท้องถิ่น
- แคช: [`shared/sandhi_breaks.json`](../shared/sandhi_breaks.json) — Roman → ชิ้นผิวที่ตัดได้
- Override curated: [`shared/sandhi_breaks_overrides.json`](../shared/sandhi_breaks_overrides.json) — คำที่ DPD/align ให้จุดตัดไม่ได้; ชิ้นผิวต้องต่อกันได้ตรงคีย์; ทับแคช DPD; rebuild แคชไม่เขียนทับไฟล์นี้
- Generate: ฉีด `{{sb}}` → TeX `\-` อัตโนมัติทุก mode (ไม่แก้ `segments.json`)
- เกณฑ์รอบแรก: `thai_display_len >= 15`
- คง `hyphenrules=nohyphenation` — ตัดเฉพาะจุดที่ inject
- `ensure_sandhi_break_cache()` — ถ้าแคชหายแต่มี `vendor/dpd/dpd.db` จะสร้างแคชตอน generate แล้วรวม overrides

## วิธีใช้

ทำงานอัตโนมัติตอน generate ทุก mode (`sync` / `reading` / `printing`) ผ่าน
`build.ps1`, `batch_prepare_volumes.py`, หรือเรียก `generate_cs_roman_tex.py`
โดยตรง — ไม่ต้องใส่ flag พิเศษ

```powershell
cd books/cs-roman
.\build.ps1 -Volume 01Vin01 -Mode sync
.\build.ps1 -Volume 01Vin01 -Mode reading
.\build.ps1 -Volume 01Vin01 -Mode printing
```

ถ้ายังไม่มี `shared/sandhi_breaks.json` แต่มี `vendor/dpd/dpd.db` อยู่แล้ว
generate จะสร้างแคชให้เองครั้งแรก

```powershell
# ครั้งแรกเท่านั้น (DB ~2GB) — ถ้ายังไม่มี dpd.db
python scripts/fetch_dpd_db.py
# บังคับสร้าง/รีเฟรชแคชทั้งคลัง
python scripts/build_sandhi_break_cache.py --all
# ปิด soft break ชั่วคราว
python scripts/generate_cs_roman_tex.py --volume 01Vin01 --mode printing --no-sandhi-breaks
```

## Coverage (สแกนคลัง 40 เล่ม)

| รายการ | จำนวน |
|--------|------:|
| Roman tokens ทั้งหมด | 145172 |
| ยาว `thai_display_len >= 15` | 5436 |
| มี soft-break ในแคช | 2683 |
| ไม่มี / align ไม่ผ่าน | 2753 |

ประมาณ **49%** ของคำยาวได้จุดตัดจาก DPD ที่ align กับรูปผิวได้

รายการคำที่ยังไม่มีในแคช (สำหรับเตรียม overrides): [`research/sandhi_breaks_missing.tsv`](../research/sandhi_breaks_missing.tsv) — สร้างด้วย `python scripts/scan_sandhi_break_gaps.py`

## เมื่อ DPD/align ให้จุดตัดไม่ได้

1. ยืนยันว่า `thai_display_len >= 15` ผ่าน แต่ไม่มีในแคช หรือ align ไม่ผ่าน
2. แยกชิ้นผิว Roman ที่ต่อกันได้ตรงรูปฉบับ **และ** แปลงไทยเป็น prefix สะอาดได้ (อย่าตัดค้างพินทุ เช่น `gat|u`)
3. ใส่ใน `shared/sandhi_breaks_overrides.json` แล้ว generate ใหม่ — อย่า patch TeX/segments
4. เก็บ regression ใน `test_cs_roman_sandhi_breaks.py` เมื่อเป็นเคสที่เคยพลาด

ตัวอย่าง (สะกดฉบับ `นาน` ซ้อน; จุดสนธิ `gata`+`ubhato` → `gatubhato`
ตัดที่ `gat|u` ไม่ได้ในไทยเพราะเหลือพินทุ — ตัดหลัง `ubhato` แทน):

```json
"tiracchānanagatubhatobyañjanakassa": [
  "tiracchānanagatubhato",
  "byañjanakassa"
]
```

## ขอบเขตที่ไม่ทำในรอบนี้

- ไม่เปิดตัดพยางค์จาก `hyph-pi.tex`
- ไม่แสดงจุดตัดบนจอตลอดเวลา
- ไม่รัน Go deconstructor ของ DPD ใน pipeline
- ไม่ดาวน์โหลด `dpd.db` อัตโนมัติตอน build (ใหญ่เกิน; ใช้แคชที่ commit หรือ fetch ครั้งเดียว)
