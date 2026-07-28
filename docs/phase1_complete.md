# Phase 1 — สรุปสิ่งที่ส่งมอบแล้ว

**ประเภทเอกสาร:** Phase Completion Summary  
**สถานะ:** ปิด Phase 1 (2026-07-21)  
**ขอบเขต:** สรุปสิ่งที่มีในระบบ **ตอนนี้** — ไม่ใช่แผนงานถัดไป

> เอกสารนี้ **นิยาม Phase 1 ใหม่ตามของจริงใน repo**  
> Checklist เดิมใน [`archive/step_by_step.md`](./archive/step_by_step.md) (อัปเดต 2026-06-21) ยังอิงแผน Snippet Corpus/Edition + CSV จาก Omeka ซึ่ง**ถูกแทนที่แล้ว**ด้วย Page tree ตาม [`archive/data_model_design.md`](./archive/data_model_design.md)  
> ใช้เอกสารนี้เป็นจุดอ้างอิง “จบ Phase 1” ก่อนหารือ Phase ถัดไป

---

## 1. นิยาม Phase 1 (ที่ปิดแล้ว)

**เป้าหมายที่ถือว่าสำเร็จใน Phase นี้**

สร้าง **เว็บไซต์ + catalog metadata** ที่รันบน local (Docker) ได้ครบชั้นแสดงผลสาธารณะ:

- โครงสร้าง Wagtail / Django พร้อม Docker Compose + PostgreSQL
- หน้า Home / Sacred content (en–th)
- ต้นไม้ catalog: **CatalogIndex → Collection → Edition → Volume**
- vocabulary snippets ที่ catalog อ้างถึง
- i18n หน้าเว็บ **en / th**
- แอปเสริม **Patidina** (ปฏิทิน)
- **scaffold** ชั้น archive + จุด mount Vue (ยังไม่มีข้อมูล / ยังไม่ทำงานจริง)

**นอกขอบเขต Phase 1 (ยังไม่ทำ / ยังไม่ปิด)**

| หัวข้อ | สถานะสั้น |
|--------|-----------|
| ข้อมูลสแกน (`ScanFolio`) + วางไฟล์ใน `media/` / Spaces | ยังไม่มี |
| ข้อความถอด (`Segment` / `SegmentRevision`) + import | ยังไม่มี |
| Citation data (`ReferenceAlias`) | โมเดลมี · ข้อมูลว่าง |
| Vue island ตรวจทาน Edition / Master TOC | stub เท่านั้น |
| ออกแบบ UI หน้า Volume / folio viewer ลงรายละเอียด | ยังไม่ทำ |
| Deploy production (Droplet, Actions, Spaces ใน Django) | defer |

ลำดับความสำคัญระยะยาวที่ยังยึดจากมติทีม: **metadata → segment/scan → Vue → go-live**  
Phase 1 = ปิดชั้น **metadata (catalog) + โครงไซต์**

---

## 2. สแต็กและสภาพแวดล้อม

| รายการ | ค่าปัจจุบัน |
|--------|-------------|
| Repo | [ptipitaka/hall.tptk.org](https://github.com/ptipitaka/hall.tptk.org) |
| Django / Wagtail | Django 5.2 · Wagtail 7.x · CodeRed CMS (CRX) |
| i18n | wagtail-localize — locales **en**, **th** |
| DB | PostgreSQL ใน Docker Compose (`db`) — ไม่ publish ไป host |
| Dev server | `http://localhost:8000` (`web` container) |
| Media สแกน | `USE_SPACES=False` · ใช้ `media/` local (ยังไม่มีไฟล์สแกนจริงใน path archive) |
| Spaces bucket | สร้างแล้ว (`sacred` / `sgp1`) — **ยังไม่ผูก Django ใน Phase นี้** |

คำสั่งหลัก: `docker compose exec web python manage.py …` (ดู `.cursor/rules/docker-dev-workflow.mdc`)

---

## 3. แอปและบทบาท

| App | บทบาทใน Phase 1 |
|-----|------------------|
| `hall/` | project settings, root URLs |
| `website/` | Home/Sacred pages, **catalog Page types**, Visual Design shells, seed/populate |
| `snippets/` | controlled vocabulary (ไม่ใช่ Corpus/Edition Snippet แบบแผนเก่า) |
| `archive/` | โมเดล Scan/Segment + URL `/cite/` — **scaffold เท่านั้น (ข้อมูล 0)** |
| `patidina/` | ปฏิทินพุทธไทย (Wagtail page + widgets) |
| `frontend/` | Vite + Vue entries `edition` / `master` — **placeholder** |
| `scripts/` | เครื่องมือ extract/cover (เช่น volume titles จาก TeX, CTS/CS Roman covers) |

---

## 4. Catalog ที่ส่งมอบแล้ว

### 4.1 โครงสร้าง Page (FRBR)

```
CatalogIndexPage          /buddhist-scriptures/
└── CollectionPage        Work (ชุดคัมภีร์)
    └── EditionPage       Expression (ฉบับ / ภาษา / อักษร)
        └── VolumePage    Item (เล่ม) + RoutablePageMixin → /f/{sequence}/
```

สเปกฟิลด์และมติ: [`archive/data_model_design.md`](./archive/data_model_design.md)

### 4.2 ตัวเลขใน DB (ณ วันที่ปิด Phase — local)

| ชนิด | จำนวน (โดยประมาณ) |
|------|-------------------|
| CatalogIndexPage | 2 (en + th) |
| CollectionPage | 38 |
| EditionPage | 58 |
| VolumePage | ~2 798 |
| CanonicalSection | 16 |
| Classification / Tradition / Country | มีข้อมูล seed |
| ContentLanguage / ContentScript / SegmentKind | มีข้อมูล seed |

URL ตัวอย่างที่ตอบ HTTP 200:

- `/buddhist-scriptures/`
- `/buddhist-scriptures/cs/`
- `/buddhist-scriptures/cs/pali2552/`
- `/buddhist-scriptures/cs/pali2552/vol-01/`

### 4.3 ความสามารถ catalog ที่ใช้ได้แล้ว

- แสดงรายการ Collection / Edition / Volume ตามต้นไม้
- metadata ฉบับ (ภาษา, อักษร, publication defaults) + override ระดับเล่ม
- Visual Design shells (default / cover / notitle / blank) ร่วมกับเนื้อหาเฉพาะ type
- Scroll background บนหน้า catalog
- Breadcrumb ตามลำดับ Catalog → Collection → Edition → Volume
- ข้อมูล volume จากโมดูล Python + management commands (ไม่ใช่ InlinePanel bulk)

### 4.4 Management commands ที่เกี่ยวข้อง (catalog)

| คำสั่ง | หน้าที่โดยย่อ |
|--------|----------------|
| `bootstrap_site` | ตั้งต้นไซต์ |
| `populate_tipitaka_catalog` | สร้าง/อัปเดต Collection + Edition จาก `tipitaka_catalog_data` |
| `populate_catalog_volumes` | Volume จาก `catalog_volume_sets` |
| `populate_csm_pali_volumes` / `populate_mmr_pali_volumes` | ชุดเล่ม CS / SY–DR |
| `seed_catalog_translations` / `seed_locale_navbars` / `seed_sacred_*` | i18n / เนื้อหา Sacred / navbar |

แหล่งข้อมูลชื่อเล่ม: `website/catalog_volume_sets.py`, `csm_pali_volumes.py`, `mmr_pali_volumes.py`  
(สกัดจาก tipitaka-catalog TeX ผ่าน `scripts/extract_catalog_volumes.py` → scratch ที่ `scripts/output/`)

---

## 5. Snippets (vocabulary)

ไม่มี Snippet ชื่อ Corpus / Edition / Script ตามแผนเก่าใน `step_by_step` Phase 2 แล้ว

คงไว้และใช้งาน:

- `Classification`, `Tradition`, `Country`
- `ContentLanguage`, `ContentScript`
- `SegmentKind`
- `CanonicalSection` (ปิฏก → นิกาย แบบ tree · FK จาก Volume)

---

## 6. Archive — มีโครง ไม่มี workload

| องค์ประกอบ | สถานะ Phase 1 |
|------------|----------------|
| `ScanFolio`, `Segment`, `SegmentRevision`, `ReferenceAlias` | โมเดล + migrations มี |
| `/cite/{cref}/`, `/cite/{collection}/{edition}/{cref}/`, alias `scheme:value` | route + template stub |
| แถวใน DB | **0 ทั้งตาราง** |
| REST API สำหรับ Vue | ยังไม่มี |
| import สแกน / segment | ยังไม่มี |
| `books/cs-roman/source/` | PDF ต้นทาง CS Roman (gitignore `*.pdf`) — ไม่ใช่ข้อมูล ScanFolio |

หน้า Volume มี `#edition-app` เป็นจุดจอง Vue (Phase ถัดไป) — ยังไม่วาด viewer

---

## 7. Frontend (Vue)

| Entry | สถานะ |
|-------|--------|
| `frontend/edition/main.ts` | placeholder: “Edition island — Phase 5” |
| `frontend/master/main.ts` | placeholder: “Master TOC island — Phase 5” |
| build → `static/dist/` | โครง Vite มี · ยังไม่ใช่ผลิตภัณฑ์จริง |

มติเดิมยังใช้ได้: **Vue เป็น islands เท่านั้น** — ไม่ SPA ทั้งไซต์

---

## 8. Patidina

ส่งมอบในรอบ Phase 1 (นอก checklist เก่า แต่ใช้งานบนไซต์แล้ว):

- `PatidinaPage` (en + th) ที่ `/patidina/` · `/th/patidina/`
- sub-routes ปฏิทินรายเดือน / อุโบสถ
- วันสำคัญจันทรคติ / สุริยคติ ใน admin
- UI server-rendered (Django template) — ไม่ใช้ HTMX/Vue สำหรับ patidina

---

## 9. เอกสารที่เกี่ยวข้อง (หลังปิด Phase 1)

| เอกสาร | ใช้ทำอะไรต่อไป |
|--------|----------------|
| **เอกสารนี้** | จุดอ้างอิง “มีอะไรแล้ว” |
| [`archive/data_model_design.md`](./archive/data_model_design.md) | สเปก catalog + archive ที่โค้ดยึด |
| [`archive/development_guide.md`](./archive/development_guide.md) | convention / Docker / Spaces — **§โมเดลหลักยังเขียนแบบเก่า ต้องอัปเดตในรอบเอกสารถัดไป** |
| [`archive/step_by_step.md`](./archive/step_by_step.md) | checklist เก่า — **อย่าใช้ Phase 2–5 ตามตัวอักษรโดยไม่อ่านเอกสารนี้ก่อน** |
| [`archive/migrate_discussion.md`](./archive/migrate_discussion.md) | บริบทหารือ migrate เท่านั้น |

---

## 10. Definition of Done — Phase 1

ถือว่าปิด Phase 1 เมื่อครบทุกข้อต่อไปนี้ (ณ 2026-07-21):

- [x] รัน local ด้วย Docker ได้ · หน้าแรกและ admin เข้าได้
- [x] Catalog Page tree มีข้อมูลและ browse ได้ (en/th)
- [x] Volume pages มี URL และ metadata พื้นฐาน (ยังไม่ต้องมีสแกน)
- [x] Vocabulary snippets + CanonicalSection ใช้งานกับ catalog ได้
- [x] Archive models + `/cite/` scaffold พร้อม แต่ยังไม่มีข้อมูลจริง
- [x] Patidina ใช้งานได้บนไซต์
- [x] มีเอกสารสรุปปิด Phase (เอกสารนี้)

---

## 11. สิ่งที่จะหารือใน Phase ถัดไป

**Goal 1 นำร่อง (`ch/pali2552ro`):** ภาพสแกนจาก Spaces ใช้งานได้แล้ว  
→ [`goal1_pilot_pali2552ro.md`](./goal1_pilot_pali2552ro.md)

หัวข้อถัดไป (ยังไม่ล็อกลำดับละเอียด):

1. ขยาย import สแกนไปฉบับอื่นใต้ `tipitaka/`
2. Segment / citation / Vue edition island
3. อัปเดตคู่มือพัฒนา + checklist ใน `docs/` ให้ตรงของจริง — เอกสารเก่าอยู่ที่ `docs/archive/`
4. Deploy (เมื่อพร้อม go-live)

---

**สรุปหนึ่งบรรทัด:** Phase 1 ส่งมอบ **ไซต์ + catalog metadata ที่ browse ได้ครบชั้นถึงเล่ม** พร้อม scaffold archive/Vue/Patidina — ยังไม่ใช่ digital twin ที่มีภาพสแกนและข้อความถอดจริง
