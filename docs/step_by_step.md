# Checklist ทีละขั้น — hall.tptk.org

**ประเภทเอกสาร:** Step-by-step Checklist  
**สถานะ:** กำลังจัดทำ — ทำตามลำดับ ข้ามขั้นเมื่อยังไม่พร้อม  
**อัปเดตล่าสุด:** 2026-06-21

---

## เกี่ยวกับเอกสารนี้

Checklist ปฏิบัติสำหรับสร้างระบบ `hall.tptk.org` ทีละขั้น — แต่ละขั้นมี checkbox ให้ติ๊กเมื่อเสร็จ

**อ่านก่อนเริ่ม**

- [คู่มือการพัฒนา](./development_guide.md) — convention, โครงสร้าง, deploy
- [Migrate Discussion](./migrate_discussion.md) — บริบทและมติ (อ้างอิง ไม่ใช่แผนที่ bind)

**Repository**

- Public: [github.com/ptipitaka/hall.tptk.org](https://github.com/ptipitaka/hall.tptk.org)
- Clone: `git clone https://github.com/ptipitaka/hall.tptk.org.git`

**หลักการ**

- ทำตามลำดับ phase — **metadata → segment → Vue → go-live**
- ขั้นย่อยใน phase เดียวกันทำคู่ขนานได้ถ้าไม่พึ่งขั้นก่อนหน้า
- ทุก PR ผ่าน checklist ก่อน merge ใน [§ PR ก่อน merge](#pr-ก่อน-merge)

**ลำดับความสำคัญตอนนี้**

- ทำ **Phase 0–5** บน local ก่อน — scaffold, models, import, Vue
- **Phase 6** (DigitalOcean Droplet, Spaces production, GitHub Actions deploy) — **ทำภายหลัง** เมื่อแอปพร้อม go-live
- ใน Phase 1–5 ยังไม่ต้องมี `.github/workflows/` หรือ Droplet — แค่ `git push` ไป `main` เพื่อเก็บโค้ดและ docs

---

## Phase 0 — เตรียมความพร้อม

### 0.1 ทำความเข้าใจ scope

- [x] อ่าน §2 ใน development guide — มติหลัก (Wagtail เดียว, Vue 2 หน้า, ไม่ OCR, ไม่ SPA)
- [x] ทราบสิ่งที่ **นอก scope** (OCR, SPA ทั้ง site, sacred-app คู่ขนานถาวร)
- [x] ทราบโมเดลหลัก: Snippet (Corpus, Edition, Script) · Segment + SegmentRevision · Wagtail Pages

### 0.2 Repository

- [x] สร้าง repo public — [ptipitaka/hall.tptk.org](https://github.com/ptipitaka/hall.tptk.org)
- [ ] clone หรือเชื่อม local กับ remote (`git remote add origin …` ถ้ายังไม่มี)
- [ ] push docs และ scaffold แรกไป `main` (เมื่อพร้อม)

### 0.3 เครื่องมือบนเครื่อง dev

- [ ] ติดตั้ง Git
- [ ] ติดตั้ง Docker Desktop (Windows)
- [ ] ติดตั้ง Node.js 20+ (สำหรับ build Vue)

### 0.4 Definition of Ready (ก่อนเริ่มแต่ละงาน)

- [ ] Scope ชัด (in / out) สอดคล้องมติ
- [ ] ข้อค้างของช่วงงานปิดแล้ว หรือบันทึก defer
- [ ] มี acceptance criteria 1–3 ข้อ
- [ ] ทราบแหล่งข้อมูลและไม่กระทบ production โดยไม่ตั้งใจ

---

## Phase 1 — Scaffold โปรเจก

เป้าหมาย: Wagtail + Docker Compose + settings แยก env — รัน local ได้

### 1.1 โครงสร้าง repo

- [ ] สร้างโครงตาม §4 ใน development guide
- [ ] `hall/settings/` — `base.py`, `dev.py`, `production.py`
- [ ] Django apps: `home/`, `snippets/`, `archive/`
- [ ] `frontend/` — โครง Vite multi-entry (ยังไม่ต้องมี component)
- [ ] `templates/`, `static/`, `scripts/` (ถ้าต้องการ)
- [ ] `.gitignore` — `media/`, `.env`, ไฟล์สแกน/PDF

### 1.2 Docker Compose

- [ ] `docker-compose.yml` — services `web`, `db` (PostgreSQL)
- [ ] `docker compose up --build` รันผ่าน
- [ ] เปิด `http://localhost:8000` ได้

### 1.3 ตัวแปรสภาพแวดล้อม

- [ ] สร้าง `.env.example` ตามหมวดใน development guide §3
- [ ] คัดลอกเป็น `.env` บน local (ไม่ commit)
- [ ] dev: `DEBUG=True`, `USE_SPACES=False`, `MEDIA_ROOT` local

### 1.4 Wagtail พื้นฐาน

- [ ] ติดตั้ง Wagtail และ dependencies
- [ ] `HomePage` ใน `home/`
- [ ] Wagtail admin เข้าได้
- [ ] `createsuperuser` สำเร็จ

### 1.5 ตรวจสอบ Phase 1

- [ ] `docker compose exec web python manage.py migrate` ผ่าน
- [ ] `docker compose exec web python manage.py test` ผ่าน (หรือมี test พื้นฐาน)
- [ ] ไม่มี secrets ใน repo

---

## Phase 2 — Snippets และ catalog

เป้าหมาย: metadata Corpus, Edition, Script · หน้า browse · import จาก CSV

### 2.1 Snippet models

- [ ] Model `Corpus` — `RevisionMixin` + `DraftStateMixin`
- [ ] Model `Edition`
- [ ] Model `Script`
- [ ] migration review และ merge
- [ ] ลงทะเบียน Snippet ใน Wagtail admin

### 2.2 หน้า Wagtail

- [ ] `HomePage` — หน้าแรกพื้นฐาน
- [ ] Page browse Corpus (หรือ catalog หลัก)
- [ ] URL routing ถูกต้อง

### 2.3 Import CSV

- [ ] management command import จาก `tipitakahall.org/catalog/*.csv`
- [ ] ลำดับ import: Corpus → Edition (ตาม dependency)
- [ ] ทดสอบด้วย sample CSV ขนาดเล็ก
- [ ] test: จำนวน record และ FK ถูกต้อง

### 2.4 ตรวจสอบ Phase 2

- [ ] browse หน้า catalog แสดงข้อมูลจาก import
- [ ] Wagtail admin แก้ Snippet ได้
- [ ] `manage.py test snippets` ผ่าน

---

## Phase 3 — Archive models

เป้าหมาย: Item, Segment, SegmentRevision — ยังไม่ต้องมี Vue

### 3.1 Models

- [ ] Model `Item` (หรือเทียบเท่า — set, bookVolume ตาม design)
- [ ] Model `Segment` — ข้อความ เก็บในตารางแยก
- [ ] Model `SegmentRevision` — revision แยกจาก Wagtail Page
- [ ] FK ไป Snippet (Edition ฯลฯ) ถูกต้อง
- [ ] migration review และ merge

### 3.2 Wagtail Pages (โครง)

- [ ] Page template สำหรับ Archive/Edition (mount point Vue ยังว่างได้)
- [ ] Page template สำหรับ Master TOC (mount point Vue ยังว่างได้)
- [ ] URL สำหรับ archive views

### 3.3 API / views พื้นฐาน

- [ ] endpoint หรือ view อ่าน Segment (สำหรับ Vue ใน Phase 5)
- [ ] URL สแกนจาก `bookCode` / `pageNo` ตาม convention §4

### 3.4 ตรวจสอบ Phase 3

- [ ] สร้าง Segment ผ่าน shell/admin หรือ import ทดสอบได้
- [ ] SegmentRevision บันทึกและอ่านได้
- [ ] `manage.py test archive` ผ่าน

---

## Phase 4 — Import ข้อมูลและสแกน

เป้าหมาย: ย้าย segment จาก sacred-app · วางไฟล์สแกน · บันทึก path ใน DB

### 4.1 Import segment

- [ ] management command import จาก export sacred-app (PostgreSQL)
- [ ] ลำดับ: หลัง import CSV (Phase 2) เสร็จ
- [ ] ทดสอบด้วย subset ขนาดเล็ก
- [ ] test: จำนวน segment และความสัมพันธ์ถูกต้อง

### 4.2 Path convention สแกน

- [ ] ยืนยัน convention: `archive/{bookCode}/{pageNo}.jpg`
- [ ] dev: `media/archive/{bookCode}/{pageNo}.jpg`
- [ ] production: Spaces `archive/{bookCode}/{pageNo}.jpg`

### 4.3 วางไฟล์สแกน

- [ ] วาง sample สแกนใน dev `media/archive/…`
- [ ] (production) วาง bulk ใน Spaces ผ่าน script/s3cmd — ไม่ผ่าน Wagtail admin
- [ ] management command บันทึก `bookCode`, `pageNo`, path ใน `archive/`

### 4.4 ตรวจสอบ Phase 4

- [ ] แอปสร้าง URL สแกนถูกต้อง (dev local media)
- [ ] ไม่ commit ไฟล์สแกน/PDF ใน repo
- [ ] test import command ผ่าน

---

## Phase 5 — Vue islands

เป้าหมาย: ตรวจทาน Edition (archive) และ Master TOC — ไม่ SPA ทั้ง site

### 5.1 Frontend setup

- [ ] Vite multi-entry: `frontend/edition/`, `frontend/master/`
- [ ] build ออก `static/dist/` — `edition.js`, `master.js`
- [ ] `npm install` และ `npm run build` ผ่าน

### 5.2 Edition (archive view)

- [ ] Vue 3 + Composition API
- [ ] mount บน Wagtail template `<div id="edition-app">`
- [ ] เรียก API/view จาก `archive/` — ไม่แยก FastAPI
- [ ] แสดง segment และภาพสแกนจาก URL

### 5.3 Master TOC

- [ ] mount `<div id="master-app">`
- [ ] แสดง TOC / mapping ตาม design
- [ ] เรียก backend ใน `archive/`

### 5.4 ตรวจสอบ Phase 5

- [ ] หน้าอื่นยังเป็น Django template — ไม่มี Vue Router ครอบทั้ง site
- [ ] `npm run build` ผ่านก่อน merge
- [ ] ทดสอบ manual: ตรวจทาน edition + master TOC บน local

---

## Phase 6 — Deploy และ go-live

> **Defer** — ทำภายหลังเมื่อ Phase 1–5 พร้อมและใกล้ go-live  
> ตอนนี้ยังไม่ต้องตั้ง Droplet, Spaces production, หรือ GitHub Actions

เป้าหมาย: production บน Droplet · pipeline อัตโนมัติ · redirect จาก Omeka

### 6.1 Droplet และ production config

- [ ] Droplet 4 GB RAM · Docker + Docker Compose
- [ ] firewall: 22, 80/443 — PostgreSQL ไม่เปิดภายนอก
- [ ] SSL (Let's Encrypt)
- [ ] `production.py` — `DEBUG=False`, Spaces เปิดใช้
- [ ] `docker-compose.yml` รองรับ production (nginx ถ้าต้องการ)

### 6.2 DigitalOcean Spaces

- [ ] bucket และ credentials จาก DO Control Panel
- [ ] ตั้ง `AWS_`* env บน production
- [ ] แยก prefix `backups/` จาก `archive/`

### 6.3 GitHub Actions

- [ ] workflow: test → SSH deploy
- [ ] Secrets: `SSH_HOST`, `SSH_USER`, `SSH_PRIVATE_KEY`
- [ ] บน Droplet: `git pull` · build · `migrate` · `collectstatic` · restart

### 6.4 Backup

- [ ] cron `pg_dump` รายวัน
- [ ] อัปโหลด backup ไป Spaces (`backups/`)
- [ ] ทดสอบ restore อย่างน้อยหนึ่งครั้ง

### 6.5 Redirect และ URL map

- [ ] จัดทำ URL map: `tipitakahall.org` → `hall.tptk.org`
- [ ] ตั้ง redirect ใน Nginx หรือ Wagtail
- [ ] ชั่วคราว: redirect หน้าแรก + catalog หลัก · หน้าไม่มี map → 404 ชัดเจน

### 6.6 ตรวจสอบ go-live

- [ ] `migrate` สำเร็จบน production
- [ ] หน้าเว็บและ Wagtail admin เข้าได้
- [ ] หน้าตรวจทานแสดงสแกนจาก Spaces
- [ ] backup รันและมีไฟล์ใน Spaces
- [ ] redirect จาก URL เก่าทำงาน (ตาม map)

---

## PR ก่อน merge

ใช้ทุก PR — ไม่ว่าอยู่ phase ไหน

- [ ] คำอธิบาย PR — ทำอะไร ทำไม · acceptance criteria
- [ ] `docker compose exec web python manage.py test` ผ่าน (อย่างน้อย app ที่แตะ)
- [ ] `migrate` รันผ่าน DB ว่าง
- [ ] แตะ Vue → `npm run build` สำเร็จ
- [ ] แตะ import → ทดสอบ sample ขนาดเล็ก
- [ ] ไม่ commit `.env`, secrets, สแกน, PDF
- [ ] อัปเดต docs ถ้าเปลี่ยน convention หรือโครงสร้าง

---

## สรุปลำดับ (ภาพรวม)


| Phase | งานหลัก                   | สถานะ |
| ----- | ------------------------- | ----- |
| 0     | เตรียมความพร้อม           | ⬜     |
| 1     | Scaffold Wagtail + Docker | ⬜     |
| 2     | Snippets + import CSV     | ⬜     |
| 3     | Archive models            | ⬜     |
| 4     | Import segment + สแกน     | ⬜     |
| 5     | Vue Edition + Master TOC  | ⬜     |
| 6     | Deploy + go-live (defer)  | ⬜     |


อัปเดตคอลัมน์ **สถานะ** เป็น ✅ เมื่อ phase นั้นเสร็จทั้งหมด

---

## อ้างอิง

- [development_guide.md](./development_guide.md)
- [migrate_discussion.md](./migrate_discussion.md)

