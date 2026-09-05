# Goal 1 Pilot — `ch/pali2552ro` (ภาพสแกน)

**ประเภทเอกสาร:** Implementation Plan  
**สถานะ:** นำร่องใช้งานได้ (2026-07-21)  
**อ้างอิงสถานะระบบ:** [`phase1_complete.md`](./phase1_complete.md)

---

## มติที่ล็อก

| ข้อ | มติ |
|-----|-----|
| ฉบับนำร่อง | `ch` / `pali2552ro` |
| เนื้อหา | ภาพสแกนเท่านั้น |
| CDN | `https://sacred.tipitakahall.org` |
| Prefix | `tipitaka/` |
| Path ไฟล์ | `tipitaka/ch/pali2552ro/{volume_index}/{sequence}.png` |
| Catalog slug | **`vol-01` … `vol-40`** |
| เชื่อมสแกน | `VolumePage.volume_index` |
| Manifest | ไม่ใช้ `book-viewer.json` |

ตัวอย่าง:  
ไฟล์ `https://sacred.tipitakahall.org/tipitaka/ch/pali2552ro/1/1.png`  
หน้า `/buddhist-scriptures/ch/pali2552ro/vol-01/f/1/`

---

## ความคืบหน้า

| Phase | สถานะ |
|-------|--------|
| A สำรวจ path | ✅ |
| B ScanFolio URL / settings | ✅ |
| C Import ทั้ง 40 เล่ม | ✅ · รายการหน้าควรเป็นชุดเดียวต่อเล่ม (locale หลัก) · แถวซ้ำ en/th เดิมเป็นมรดกนำเข้าเก่า |
| D หน้าเปิดอ่านขั้นต่ำ | ✅ |
| E ปิด pilot docs | ✅ |

### ตรวจบน local

- http://localhost:8000/buddhist-scriptures/ch/pali2552ro/vol-01/f/1/
- http://localhost:8000/th/buddhist-scriptures/ch/pali2552ro/vol-01/f/1/

### คำสั่ง

```bash
docker compose exec web python manage.py import_scan_folios \
  --all --rediscover --count-only

docker compose exec web python manage.py generate_scan_folios \
  --all --replace --dry-run

docker compose exec web python manage.py generate_scan_folios \
  --all --replace
```

`import_scan_folios --all --rediscover --count-only` นับไฟล์บน CDN แล้วบันทึก `VolumePage.scan_folio_count` ที่ locale หลัก

`generate_scan_folios --all --replace` ลบแถวซ้ำทุก locale แล้วสร้าง `1..N` บนหน้าเล่ม locale หลัก หน้าแปลอ่านชุดเดียวกัน

### Settings ที่เกี่ยวข้อง

`SCAN_BASE_URL` · `SCAN_PREFIX` · `SCAN_FILE_EXT` · `SCAN_USE_REMOTE`  
(ดู `.env.example` / `hall/settings/base.py`)
