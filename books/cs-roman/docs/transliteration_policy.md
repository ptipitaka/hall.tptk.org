# นโยบายผลปริวรรตและข้อความโรมันฉบับพิมพ์

เอกสารนี้กำหนด **ชั้นข้อมูล** และ **สิ่งที่ห้ามแก้ด้วยมือ** เมื่อปรับปรุงผลปริวรรต (ไทยจากโรมัน) หรือข้อความโรมันที่สะท้อนฉบับพิมพ์  
คู่มืองานประจำยังอยู่ที่ [`playbook.md`](playbook.md) · สัญญา JSON อยู่ที่ [`SCHEMA.md`](../SCHEMA.md)

## บริบท

ผลจากการถอด PDF และการปริวรรตจะถูกปรับปรุงอยู่เรื่อย ๆ  
**ห้ามแก้ผลที่เก็บใน `segments.json` โดยตรง** เพื่อแก้ตัวสะกด วรรคตอน หรือข้อความโรมันฉบับพิมพ์ — แม้จะเห็นผิดใน `output/` หรือ `volumes/…/data/segments.json`

การแก้แบบนั้นจะหายเมื่อ re-extract, sync จาก `output/`, หรือคนอื่นรัน pipeline — และทำให้กฎฉบับพิมพ์ไม่สอดคล้องกันทั้ง 40 เล่ม

## ชั้นข้อมูล (อ่านก่อนแก้)

| ชั้น | ไฟล์ | เข้า git | หมายความ |
| --- | --- | --- | --- |
| ถอดจาก PDF | `output/<id>.segments.json` | ไม่ | staging หลัง extract; `build.ps1` คัดลอกทับ `volumes/` ถ้ามี |
| เนื้อหาถอด (git) | `volumes/<id>/data/segments.json` | ใช่ | extract-normalized — **ไม่ใช่** ฉบับพิมพ์สุดท้าย |
| จังหวะพิมพ์ | `volumes/<id>/data/layout.json` | ใช่ | ระยะหน้า / บังคับขึ้นหน้า — ไม่ใช่ตัวสะกด |
| กฎฉบับพิมพ์ | `shared/transforms.json` | ใช่ | แก้โรมัน / อรรถ / ตัวหนาผิด — ใช้ตอน **generate TeX** |
| เลขข้อ (identity) | `shared/item_corrections.json` | ใช่ | พิมพ์ผิดที่เลข Tipiṭaka — extract / fixup / generate เขียน `item` ให้ถูก |
| ผลส่งมอบ | `volumes/<id>/out/*.pdf`, `tex/body.*.generated.tex` | ไม่ (PDF) | สร้างจาก segments + layout + transforms |

กฎใน `transforms.json` **ไม่ถูก bake** เข้า `segments.json` — แก้กฎแล้ว generate ใหม่จึงเห็นใน PDF  
รายละเอียด: [`SCHEMA.md`](../SCHEMA.md) § Content file และ § Transforms file

## แก้ที่ไหน (กรณีโรมัน / ปริวรรต / อรรถ)

| อาการ | แก้ที่ | ห้ามแก้ที่ |
| --- | --- | --- |
| โรมันผิดเทียบฉบับพิมพ์ | `shared/transforms.json` (`replace`) | `output/`, `volumes/…/segments.json` |
| คงคำพิมพ์ + อรรถ ` – ม.พ.ป.` | `shared/transforms.json` (`annotate`) | เหมือนข้างบน |
| ตัวหนาผิด (ไม่ใช่สะกด) | `shared/transforms.json` (`unbold`) | `segments.json` `runs` ด้วยมือ |
| discourse dash / วรรคตอนโรมัน (เช่น `uddiseyyātha.` → `uddiseyyātha–`) | `shared/transforms.json` + `when.loci` ถ้าไม่ผิดทุกที่ | แก้ท้าย `value` ใน segment |
| ไทยจากโรมันผิด **เพราะโรมันผิด** | แก้โรมันที่ `transforms.json` แล้ว generate | แก้ `script: thai` ใน segments ด้วยมือ |
| สมาสขึ้นบรรทัด | `shared/sandhi_breaks_overrides.json` | segments |
| ถอด PDF ผิดซ้ำทุกครั้ง | extract + test → `pipeline.ps1` | patch ทีละจุดใน segments |
| โครงสร้าง JSON เก่า / bug extract ที่แก้แล้ว | `fixup_*.py` + [`fixup_manifest.json`](../scripts/fixup_manifest.json) | one-off ใน segments เป็นทางหลัก |
| เลขข้อพิมพ์ผิด (สลับหลัก ฯลฯ) | `shared/item_corrections.json` แล้ว extract/fixup | แก้ฟิลด์ `item` ด้วยมือ |
| เนื้อเชิงอรรถฉบับพิมพ์ (`notes` / `symbol_notes`) | ไม่ใช้ `transforms.json` — คงตามที่ถอด | แก้ด้วยมือใน segments เพื่อให้ตรงแคตตาล็อก |

**กฎทอง:** ถ้าปัญหาคือ «ข้อความในฉบับพิมพ์ควรเป็นอะไร» → `transforms.json` เท่านั้น  
ถ้าปัญหาคือ «เลขข้อ Tipiṭaka ควรเป็นอะไร» → `item_corrections.json` เท่านั้น

## ห้ามเด็ดขาด (publication / ปริวรรต)

- แก้ `books/cs-roman/output/*.segments.json` เพื่อแก้โรมัน / ไทย / วรรคตอนฉบับพิมพ์
- แก้ `books/cs-roman/volumes/<id>/data/segments.json` ด้วยมือเพื่อจุดประสงค์เดียวกัน
- แก้ `text[].value` หรือ `runs` ใน segment เพื่อ «แก้ปริวรรต» หรือ «แก้โรมันฉบับพิมพ์»
- แก้ PDF หรือ `body.*.generated.tex` โดยตรง (แก้ macro ที่ `shared/style/`)

**ยกเว้น** งาน fixup ที่ลงทะเบียนใน manifest (โครงสร้าง extract / hyphen / header — ไม่ใช่กฎฉบับพิมพ์รายคำ) หรืองานจังหวะที่ `layout.json`

## ขั้นตอนเมื่อพบคำผิด (เอเจนต์ / มนุษย์)

1. จำแนก: โรมันฉบับพิมพ์ / อรรถ / ตัวหนาผิด → **transforms**
2. ค้นก่อนแก้ (Docker จากรากรีโป):

   ```powershell
   docker compose exec -T web python books/cs-roman/scripts/scan_transform_hits.py --match <คำหรือรูปแบบ>
   docker compose exec -T web python books/cs-roman/scripts/scan_transform_hits.py --rule-id <id>  # หลังเพิ่มกฎ
   ```

3. ถ้าคำเดียวกันถูกที่อื่น ผิดเฉพาะบางหน้า → ใส่ `when.loci` (`volume` บังคับ; `page` / `order` ถ้าจำเป็น)
4. เพิ่มหรือแก้กฎใน `shared/transforms.json` (`replace` / `annotate` / `unbold`)
5. ทดสอบ: `.\books\cs-roman\scripts\run_tests.ps1 -Module test_cs_roman_transforms`
6. สร้าง PDF เล่มที่โดน: `cd books/cs-roman` แล้ว `.\build.ps1 -Volume <id> -Mode printing`

`segments.json` อาจยังแสดงข้อความเดิม — **PDF หลัง generate ต้องถูก** นั่นคือเกณฑ์รับงาน

## ตัวอย่าง

**ผิด:** แก้บรรทัดใน `output/01Vin01.segments.json` เปลี่ยน `uddiseyyātha.` เป็น `uddiseyyātha–`

**ถูก:** กฎใน `transforms.json`:

```json
{
  "id": "roman-uddiseyyatha-discourse-dash-01vin01-187",
  "when": {
    "match": "uddiseyyātha.",
    "loci": [{"volume": "01Vin01", "page": 187, "order": 1200}]
  },
  "do": {
    "replace": {
      "with": "uddiseyyātha–",
      "remark": "Discourse dash before sikkhāpada; period mis-extract at 01Vin01 p187"
    }
  }
}
```

ใช้ en-dash `–` (U+2013) ตามมาตรฐานเล่ม — TeX แปลงเป็น `\csromandash` (ดู `shared/style/book-macros.tex`)

## ทำไม `output/` ไม่ใช่ที่แก้

- `output/` เป็น **staging หลังถอด** ไม่เข้า git
- `build.ps1` คัดลอก `output/` → `volumes/` เมื่อมีไฟล์ staging — การแก้มือใน `output/` อาจถูกทับหรือทับ git copy โดยไม่ตั้งใจ
- กฎฉบับพิมพ์ต้องอยู่ **หนึ่งแคตตาล็อก** ใน `shared/transforms.json` ไม่กระจายใน 40 ไฟล์ segments

## อ้างอิง

- [`playbook.md`](playbook.md) — ตารางอาการ / คำสั่ง
- [`SCHEMA.md`](../SCHEMA.md) — สัญญา segments vs transforms
- [`fixup_process.md`](fixup_process.md) — ซ่อม artifact JSON (ไม่ใช่กฎฉบับพิมพ์รายคำ)
- `.cursor/skills/cs-roman/SKILL.md` — เอเจนต์ CS Roman
