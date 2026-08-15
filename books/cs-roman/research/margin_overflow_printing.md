# ข้อความล้นขอบ — โหมด printing

คำที่ขอบขวาเลยกรอบตัวอักษรไป **มากกว่าประมาณ 2 ความกว้างตัวอักษร** ของคำนั้น ไม่นับเครื่องหมายเลขหน้า (`ฉ.N`)

สแกนแล้ว 40 เล่ม; พบ 6 จุด เรียงตามความยาวตัวอักษร (ยาวสุดก่อน)

**สถานะ 2026-08-09:** หลัง inject-time stem compose (ขยาย head/tail + typography guard) และ curated overrides สำหรับรูปยาวที่เหลือ — จากสแกนทั้งคลังครั้งก่อน **43 → 6** จุด รายการที่เหลือส่วนใหญ่อยู่นอกขอบเขต sandhi cache (ไทยฉบับ ≠ รูป solid จาก `roman→thai`, ข้อมูล extract เพี้ยน หรือเศษสั้นกว่า `min_fragment_len=3`)

| volume | หน้า PDF | ฉบับ (`ฉ.N`) | PDF | text |
|--------|--------:|-------------:|-----|------|
| 28Khu11 | 418 | ฉ.336 | [`28Khu11.printing.pdf`](../volumes/28Khu11/out/28Khu11.printing.pdf) | คหณาปคตอุรุวิสฏวิตฺถตมหนฺตฏฺเฐน. |
| 25Khu08 | 278 | ฉ.222 | [`25Khu08.printing.pdf`](../volumes/25Khu08/out/25Khu08.printing.pdf) | qอํสมกสวาตาตปสรีสปสมฺผสฺเสน |
| 36Abhi08 | 537 | ฉ.436 | [`36Abhi08.printing.pdf`](../volumes/36Abhi08/out/36Abhi08.printing.pdf) | อนฺอุปาทินฺนุปาทานิยสฺส |
| 36Abhi08 | 8 | — (ต้นเล่ม) | [`36Abhi08.printing.pdf`](../volumes/36Abhi08/out/36Abhi08.printing.pdf) | ตํสมฺปยุตฺตกานญฺจ |
| 25Khu08 | 190 | ฉ.151 | [`25Khu08.printing.pdf`](../volumes/25Khu08/out/25Khu08.printing.pdf) | วิคตโลมหํโสติปิ |
| 36Abhi08 | 15 | ฉ.8 | [`36Abhi08.printing.pdf`](../volumes/36Abhi08/out/36Abhi08.printing.pdf) | ตํสมุฏฺฐานานญฺจ |

> **หน้า PDF** = หน้าที่เปิดใน viewer (1-based)  
> **ฉบับ (`ฉ.N`)** = เลขหน้าฉบับเดิมบนหน้าเดียวกัน (ถ้ามี)

## หมายเหตุ residual

| text | ตำแหน่ง | PDF | เหตุที่ยังเปิดอยู่ |
|------|---------|-----|---------------------|
| คหณาปคตอุรุ… | 28Khu11 หน้า 418 / ฉ.336 | [`28Khu11.printing.pdf`](../volumes/28Khu11/out/28Khu11.printing.pdf) | มี override สำหรับ Roman `gahaṇāpagatauru…` แล้ว แต่ convert/slices ได้ `…ปคตฺเอารุ…` ส่วนไทยฉบับเป็น `…ปคตอุรุ…` — inject จึงแทนที่ไม่ได้ |
| qอํสมกส… | 25Khu08 หน้า 278 / ฉ.222 | [`25Khu08.printing.pdf`](../volumes/25Khu08/out/25Khu08.printing.pdf) | ตัว `q` นำหน้าเป็นข้อมูล extract/segment เพี้ยน ไม่ใช่เพราะขาด sandhi key |
| อนฺอุปาทินฺนุ… | 36Abhi08 หน้า 537 / ฉ.436 | [`36Abhi08.printing.pdf`](../volumes/36Abhi08/out/36Abhi08.printing.pdf) | เศษนอกสั้น ไม่ผ่าน `min_fragment_len=3` จึงเหลือ `\-` น้อยหรือไม่มี |
| ตํสมฺปยุตฺตกานญฺจ | 36Abhi08 หน้า 8 | [`36Abhi08.printing.pdf`](../volumes/36Abhi08/out/36Abhi08.printing.pdf) | เช่นกัน (`ตํ`, `ñca`) |
| ตํสมุฏฺฐานานญฺจ | 36Abhi08 หน้า 15 / ฉ.8 | [`36Abhi08.printing.pdf`](../volumes/36Abhi08/out/36Abhi08.printing.pdf) | เช่นกัน |
| วิคตโลมหํโสติปิ | 25Khu08 หน้า 190 / ฉ.151 | [`25Khu08.printing.pdf`](../volumes/25Khu08/out/25Khu08.printing.pdf) | อยู่ในบริบทวัดบรรทัดคาถา; ส่วนท้าย `tipi` ถูกตัดทิ้งด้วยเกณฑ์ความยาวเศษ |

สแกนใหม่: `python books/cs-roman/scripts/scan_margin_overflow.py --mode printing`
