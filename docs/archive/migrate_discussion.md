# Migrate Discussion — SACRED / Tipitaka Hall

> **หมายเหตุสำคัญ**
>
> เอกสารนี้เป็น **Migrate Discussion** เท่านั้น — บันทึกผลการ **หารือ / อภิปราย** เกี่ยวกับการ **ย้าย/ปรับสถาปัตยกรรม** จาก `sacred-app` + `tipitakahall.org` (Omeka) ไปแนวทางใหม่  
> เอกสารนี้ **ไม่ใช่** แผน migration ที่ ratify แล้ว และ **ไม่ใช่** คู่มือในการพัฒนา (development guide)  
> ก่อนเริ่ม migrate จริง ต้องทบทวน ตัดสินใจ และจัดทำ migration plan / architecture spec ที่ approved แยกต่างหาก

**ประเภทเอกสาร:** Migrate Discussion (ไม่ใช่ migration plan ที่ bind)  
**สถานะ:** Discussion only  
**อัปเดตล่าสุด:** 2025-06-20  
**ขอบเขตโปรเจกต:** `sacred-app`, `tipitakahall.org` → เป้าหมาย `hall.tptk.org` (proposal)

---

## 1. บริบทและปัญหา (ทำไมถึงคุยเรื่อง migrate)

### เป้าหมาย (SACRED)

1. **ความบริสุทธิ์ของข้อมูล** — พระไตรปิฎกหลายฉบับ (CH, SY, MC, BJ), ตรวจทาน, audit trail
2. **อ้างอิงข้ามฉบับ** — Master TOC, mapping, citation ร่วม
3. **ตรวจสอบอัจฉริยะ** — OCR verify/ingest, transliteration 4 script, ต่อยอด NLP/AI

### สถานะโปรเจกตปัจจุบัน (ก่อน migrate)

| โปรเจกต | Stack | จุดแข็ง | จุดอ่อน |
|---------|-------|---------|---------|
| **sacred-app** | FastAPI + Vue 3 + PostgreSQL | OCR, segment editorial, branch/revision, TOC | ไม่มี admin ที่ใช้สะดวก (SQLAdmin ดิบ); งานกระจาย Vue + scripts |
| **tipitakahall.org** | Omeka S (PHP) | catalog Corpus → Edition → Volume | ช้า, custom หนัก, stack เก่า, หาคนสานต่อยาก |

### Pain หลักที่ทำให้พิจารณา migrate

- ทีม IT **2 คน** — stack หลายชั้น (FastAPI + Vue + SQLAdmin + Omeka) ดูแลยาก
- **ไม่มี admin รวมศูนท์** — `/admin` (SQLAdmin) แยก auth จาก user ในระบบ; segment แก้เป็น JSONB ดิบ
- งานวิชาการ (OCR/editorial) กับงาน catalog (Omeka) **แยกระบบ**

---

## 2. ทางเลือกที่พิจารณาแล้ว (มุมมองจากการหารือ migrate)

| ทางเลือก | เหตุผลที่ไม่น่าจะเลือกเป็นหลัก |
|----------|--------------------------------|
| **Omeka S ต่อ** | เหมาะ catalog แต่ไม่รองรับ segment/OCR/editorial; ช้า; PHP niche |
| **Rewrite ทั้งก้อนเป็น Plone** | ZODB/learning curve สูง; ไม่ fit โมเดล segment PostgreSQL |
| **Rewrite ทั้งก้อนเป็น Nuxt full-stack** | ต้อง rewrite backend OCR; ยังเป็น SPA ทั้ง site |
| **ทิ้ง sacred-app ใช้ Wagtail อย่างเดียว** | OCR/editorial/segment branch ต้องสร้างใหม่ทั้งก้อน |
| **Vue SPA ทั้ง site ต่อไป** | ไม่แก้ admin; ไม่แทน Omeka; bundle/SEO หน้าสาธารณะ |

---

## 3. แนวทาง migrate ที่หารือ (ยังไม่ใช่มติสุดท้าย)

### หลักการ (proposal)

- **Wagtail เป็น host หลัก** — pages, navigation, SEO, catalog, admin, workflow/revision ของ metadata
- **ไม่ใช่ SPA ทั้ง site** — เปลี่ยนหน้าหลัก = Wagtail multi-page (HTML)
- **Vue เฉพาะจุด (islands)** — Archive, Edition editor, Master TOC; mount บน Wagtail Page
- **Segment + OCR อยู่ PostgreSQL + API** — ไม่ยัด segment หลายแสนแถวเป็น inline ใน Snippet
- **ค่อย ๆ ปิด Omeka** — catalog ย้ายเข้า Wagtail
- **เก็บ sacred-app backend (FastAPI) ช่วงเปลี่ยนผ่าน** — OCR, editorial, segment API

### ภาพรวมหลัง migrate (proposal)

```
┌─────────────────────────────────────────────────────────┐
│  Wagtail (Django) — site หลัก  @ hall.tptk.org           │
│  • Pages: หน้าแรก, corpus, about, …                      │
│  • Snippets: Edition, Corpus, Script (RevisionMixin)     │
│  • Admin: user/workflow/revision สำเร็จรูป               │
│  • หน้าง่าย: HTML หรือ HTMX (+ Alpine ถ้าต้องการ)        │
│  • หน้าหนัก: template + <div id="…-app"> → Vue island   │
└───────────────────────────┬─────────────────────────────┘
                            │ REST / proxy
┌───────────────────────────▼─────────────────────────────┐
│  FastAPI (sacred-app backend) — ช่วงเปลี่ยนผ่าน          │
│  • tipitaka_segments, OCR, editorial, TOC mapping        │
│  • PostgreSQL (+ JSONB, GIN index)                       │
└─────────────────────────────────────────────────────────┘

tipitakahall.org (Omeka) → retire เมื่อ catalog migrate เสร็จ (ถ้ามีมติ)
```

### Vue islands (ไม่ใช่ SPA)

| Wagtail Page (ตัวอย่าง) | Vue entry | หน้าที่ |
|-------------------------|-----------|--------|
| `ArchivePage` | `archive.js` | OCR verify, dual-view สแกน |
| `EditionPage` | `edition.js` | segment editorial |
| `MasterPage` | `master.js` | Master TOC |

- Build ด้วย Vite — **แยก entry ต่อหน้า** โหลด JS เฉพาะ page ที่ต้องการ
- Reuse components จาก `sacred-app/frontend` ได้
- ภายใน island อาจมี Vue Router ย่อย (tab) — ไม่ถือว่า SPA ทั้ง site

### Frontend แบ่งหน้าที่ (proposal)

| ชั้น | เทคโนโลยี | ใช้เมื่อ |
|------|-----------|---------|
| Wagtail templates | Django + (HTMX + Alpine) | catalog browse, ฟอร์มง่าย, static content |
| Vue islands | Vue 3 + Vite | Archive, Edition, TOC |
| Wagtail admin | built-in | metadata, snippet, workflow |

---

## 4. โมเดลข้อมูลและ Revision (จากการหารือ migrate)

### อย่ายัด segment เป็น inline ใน Snippet เดียว

- Segment ทั้งฉบับ = **หลายแสนแถว** → inline + ParentalKey ทำให้ admin/revision พัง
- **Snippet (Edition metadata)** — ขนาดเล็ก → `RevisionMixin` + `DraftStateMixin` (+ workflow ถ้าต้องการ)
- **Segment** — ตาราง `tipitaka_segments` แยก → revision ต่อแถว (custom `SegmentRevision` ใน sacred-app หรือ django-reversion ถ้าแค่ rollback)

### กลยุทธ์ revision (proposal)

| Model | วิธี revision |
|-------|----------------|
| Wagtail Page | Wagtail built-in |
| Snippet (Edition, Corpus, …) | `RevisionMixin` + `DraftStateMixin` |
| Segment, OCR config | django-reversion หรือ **SegmentRevision (sacred-app)** สำหรับ four-eyes/branch |
| Git deploy stamp | ไม่ใช้ django-revision (erikvw) — คนละเรื่องกับ content revision |

### สิ่งที่ Wagtail/django-reversion น่าจะไม่แทน sacred-app

- Branch/version control (main + custom branch)
- Four-eyes review (reviewer ≠ last editor)
- Pessimistic lock 15 นาที
- OCR verify/ingest pipeline
- Master TOC cross-edition mapping แบบเต็ม

---

## 5. Auth (หัวข้อ migrate ที่ยังต้องหารือต่อ)

| ระบบ | ปัจจุบัน | แนวทางที่หารือ (ยังไม่ ratify) |
|------|----------|--------------------------------|
| SQLAdmin `/admin` | ADMIN_USERNAME/PASSWORD (env) | **เลิกใช้** หรือรวมกับ Wagtail admin |
| API + Vue | JWT + User ใน PostgreSQL | **คงไว้** สำหรับ islands |
| Wagtail | Django auth | **รวม user** หรือ SSO กับ API — ตัดสินใน Phase B |

---

## 6. แผน Migration (ร่างจาก Migrate Discussion — ไม่ใช่ roadmap ที่ bind)

### Phase A — โครง Wagtail + เอกสาร

- [ ] สร้างโปรเจกต Wagtail ที่ `hall.tptk.org`
- [ ] Snippet: Corpus, Edition, Script
- [ ] Pages: หน้าแรก, corpus browse (HTML/HTMX)
- [ ] import catalog จาก `tipitakahall.org/catalog/*.csv`

### Phase B — Vue islands + API

- [ ] `ArchivePage`, `EditionPage` + Vite entries
- [ ] proxy `/api/` → FastAPI (sacred-app)
- [ ] auth ร่วม Wagtail ↔ JWT

### Phase C — retire Omeka

- [ ] redirect URL เก่า
- [ ] PDF/metadata จาก Wagtail + Spaces

### Phase D — รวม backend (ถ้าต้องการ)

- [ ] ย้าย OCR/editorial เป็น Django apps ใน Wagtail หรือเก็บ FastAPI เป็น microservice

---

## 7. สิ่งที่ยังไม่ตัดสินใจ (Open)

- [ ] repo เดียว (monorepo) vs แยก `hall.tptk.org` + `sacred-app`
- [ ] รวม PostgreSQL instance เดียวหรือแยก DB ช่วงเปลี่ยนผ่าน
- [ ] ย้าย user table ไป Django หรือ sync
- [ ] HTMX ใช้หน้าไหนบ้าง (catalog browse แน่ ๆ — รายละเอียด template)
- [ ] ratify แนวทาง migrate ใน §3 เป็น migration plan อย่างเป็นทางการหรือไม่

---

## 8. อ้างอิงใน repo

| เอกสาร/โค้ด | path |
|-------------|------|
| วิสัยทัศน์ SACRED | `sacred-app/docs/SACRED_PROJECT.md` |
| Editorial system | `sacred-app/docs/design/EDITORIAL_SYSTEM.md` |
| Permissions | `sacred-app/docs/design/PERMISSIONS_AND_ROLES.md` |
| SQLAdmin (ชั่วคราว) | `sacred-app/backend/admin/setup.py` |
| Omeka blueprint | `tipitakahall.org/docs/sacred-site-blueprint.md` |
| Catalog CSV | `tipitakahall.org/catalog/` |

---

## 9. สรุป Migrate Discussion (ไม่ใช่มติ migrate)

จากการอภิปราย มี **proposal** ว่าอาจ migrate ไปใช้ Wagtail เป็น site + admin + catalog แบบ multi-page (ไม่ SPA); ฝัง Vue เฉพาะหน้า Archive/Edition/TOC; เก็บ segment/OCR บน PostgreSQL ผ่าน FastAPI (sacred-app) ช่วงเปลี่ยนผ่าน; และอาจ retire Omeka เมื่อ catalog migrate เสร็จ — **โดยไม่ rewrite OCR/editorial ทั้งก้อน**

ข้อเสนอนี้ **ยังต้องทบทวนและ approve โดยทีม** ก่อนจัดทำ migration plan และเริ่ม implement
