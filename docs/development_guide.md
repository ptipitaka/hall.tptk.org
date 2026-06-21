# คู่มือการพัฒนา — [hall.tptk.org](http://hall.tptk.org)

**ประเภทเอกสาร:** Development Guide  
**สถานะ:** กำลังจัดทำ — เติมรายละเอียดทีละหัวข้อ  
**อัปเดตล่าสุด:** 2026-06-21

---

## 1. เกี่ยวกับเอกสารนี้

เอกสารนี้เป็นคู่มือปฏิบัติสำหรับการพัฒนาโปรเจกต `hall.tptk.org` รวบรวมขั้นตอน การตั้งค่า และมาตรฐานที่ทีมยึดถือร่วมกันในการลงมือทำงานจริง

**วัตถุประสงค์**

- ให้ผู้พัฒนาเริ่มงานได้อย่างถูกต้องและสม่ำเสมอ
- กำหนดแนวทางและ convention ที่ใช้ร่วมกันทั้งทีม

**ขอบเขต (เอกสารนี้ครอบคลุม)**

- การเตรียมความพร้อมและการตั้งค่าสภาพแวดล้อมพัฒนา
- ขั้นตอนการทำงาน มาตรฐานโค้ด การทดสอบ และการ deploy

**Checklist ทีละขั้น:** [step_by_step.md](./step_by_step.md) — ทำตาม phase 0–6 พร้อม checkbox

**นอกขอบเขต (ไม่ครอบคลุม)**

- เหตุผลและที่มาของการปรับสถาปัตยกรรม — ดู [migrate_discussion.md](./migrate_discussion.md)
- การตัดสินใจเชิงสถาปัตยกรรมที่ยังไม่สรุป — รอ migration plan ที่ ratify แยกต่างหาก
- รายละเอียดเชิงลึกจากระบบเดิม (OCR, editorial workflow แบบ sacred-app) — ดู `sacred-app/docs/`

**ผู้อ่านเป้าหมาย:** ผู้พัฒนาและผู้ที่ต้องตั้งค่าหรือดูแลโปรเจกต

**การบำรุงรักษา:** ปรับปรุงเมื่อ convention หรือขั้นตอนเปลี่ยน หากขัดกับ migration plan ที่ ratify แล้ว ให้ยึด migration plan เป็นหลัก

---

## 2. สรุปประเด็นก่อนเริ่มงาน

มติทีมสำหรับระบบใหม่ `hall.tptk.org` บริบทระบบเดิมดู [migrate_discussion.md](./migrate_discussion.md)

### มติหลัก


| หัวข้อ          | สรุป                                                                                                      |
| --------------- | --------------------------------------------------------------------------------------------------------- |
| **เป้าหมาย**    | digital twin ของเนื้อหาสแกนในหนังสือ — เตรียมข้อมูลและตรวจทาน (ไม่เน้น editorial workflow แบบ sacred-app) |
| **แพลตฟอร์ม**   | Wagtail multi-page — site สาธารณะและ admin เป็นที่ทำงานเดียว                                              |
| **Vue**         | ตรวจทาน Edition (archive) และ Master TOC — ไม่เป็น SPA ทั้ง site                                          |
| **OCR**         | ไม่อยู่ใน scope                                                                                           |
| **โมเดลข้อมูล** | ออกแบบใหม่ทั้งหมด — อาจอ้างอิงแนวทางเดิม ไม่ copy schema                                                  |
| **ผลลัพธ์**     | Wagtail site ระบบเดียวเมื่อเสร็จสมบูรณ์ — ไม่พึ่ง backend แยกคงค้าง                                       |
| **Revision**    | segment ข้อความ — ระบบ revision แยก · ส่วนอื่น — Wagtail Page revision ปกติ                               |


**นอก scope:** รับสแกน รัน OCR และตรวจทานผล · SPA ทั้ง site · FastAPI/sacred-app คู่ขนานถาวร · bulk data ใน Snippet inline · HTMX

### โครงสร้างและเทคโนโลยี


| หัวข้อ            | มติ                                                                               |
| ----------------- | --------------------------------------------------------------------------------- |
| **Repo**          | [ptipitaka/hall.tptk.org](https://github.com/ptipitaka/hall.tptk.org) — public · Django + Wagtail + frontend ใน repo เดียว |
| **PostgreSQL**    | บน Droplet เดียวกับ Django — ไม่ใช้ Managed PostgreSQL                            |
| **Auth**          | Django auth + Wagtail groups/permissions                                          |
| **Frontend**      | หน้า interactive ใช้ Vue · ที่เหลือ Django template                               |
| **Media**         | สแกน/PDF: path ใน Spaces + metadata ใน `archive/` · ไม่อัปโหลดสแกนผ่าน Wagtail admin |
| **Deploy**        | Droplet all-in-one · `git push` → **GitHub Actions** → SSH deploy · ไม่มี staging · **ตั้ง Droplet + Actions ภายหลัง** (พัฒนา local ก่อน) |
| **Backup**        | `pg_dump` รายวัน → DigitalOcean Spaces                                            |
| **Import ข้อมูล** | Django management commands / scripts ใน repo                                      |


### โมเดลหลัก (draft)

ออกแบบใหม่ทั้งหมด — อ้างอิงแนวทาง Omeka / sacred-app ไม่ copy schema


| ชั้น             | รายการ                                                          | Revision                         |
| ---------------- | --------------------------------------------------------------- | -------------------------------- |
| **Snippet**      | Corpus, Edition, Script                                         | Wagtail `RevisionMixin`          |
| **Model**        | Segment (ข้อความ)                                               | SegmentRevision (แยกจาก Wagtail) |
| **Wagtail Page** | หน้าแรก, Corpus browse, Archive/Edition (Vue), Master TOC (Vue) | Wagtail built-in                 |


Segment จำนวนมาก — เก็บในตารางแยก ไม่ inline ใน Snippet

### แหล่งข้อมูลและลำดับ import

หลายแหล่ง — import ผ่าน management commands ตามลำดับ:


| ลำดับ | แหล่ง                              | เนื้อหา                                     |
| ----- | ---------------------------------- | ------------------------------------------- |
| 1     | `tipitakahall.org/catalog/*.csv`   | metadata catalog (Corpus, Edition ฯลฯ)      |
| 2     | export จาก sacred-app (PostgreSQL) | segment ข้อความ (ถ้ามีข้อมูลเดิมให้ย้าย)    |
| 3     | ไฟล์สแกน/PDF จากระบบเดิม         | วางใน Spaces ตาม path convention · บันทึก path ใน `archive/` |


ข้อมูลใหม่หลัง go-live — สร้างและแก้ใน Wagtail admin เป็นหลัก

### Redirect URL เก่า

- **จาก:** `tipitakahall.org` (Omeka) → **ไป:** `hall.tptk.org`
- **ก่อน go-live:** จัดทำ URL map (corpus / edition / volume ฯลฯ) และตั้ง redirect ใน Nginx หรือ Wagtail
- **ชั่วคราวก่อน map ครบ:** redirect หน้าแรก + หน้า catalog หลัก — หน้าที่ไม่มี map แสดง 404 ชัดเจน

แผนละเอียด ratify แล้วยึด `migration_plan.md` (เมื่อจัดทำ)

### สิ่งที่ต้องมี

- อ่าน migrate discussion และทราบช่วงงานที่กำลังทำ
- Git · Python 3.11+ · Node.js (หน้า Vue) · PostgreSQL
- สิทธิ์ repo, dev/staging และ credentials ตามงาน

### Definition of Ready

- [ ] Scope ชัด (in / out) สอดคล้องมติด้านบน
- [ ] ข้อค้างของช่วงงานปิดแล้ว หรือบันทึก defer
- [ ] มี acceptance criteria 1–3 ข้อ
- [ ] ทราบแหล่งข้อมูลและไม่กระทบ production โดยไม่ตั้งใจ

---

## 3. ตั้งค่าสภาพแวดล้อม

พัฒนาบนเครื่อง local ด้วย **Docker Compose** ให้ใกล้เคียง production (PostgreSQL บน container เดียวกับแอป)

### เครื่องมือที่ต้องมี

- Git
- Docker Desktop (Windows)
- Node.js 20+ (build หน้า Vue บน local ถ้าต้องการ)

### เริ่มต้น

```bash
git clone https://github.com/ptipitaka/hall.tptk.org.git
cd hall.tptk.org
cp .env.example .env          # แก้ค่าตามด้านล่าง — ไม่ commit .env
docker compose up --build
```

เปิด `http://localhost:8000` · Wagtail admin ตาม URL ที่ตั้งใน `.env`

### ตัวแปรสภาพแวดล้อม (`.env`)

สร้าง `.env.example` ใน repo ตามหมวดนี้ — **dev ใช้ local media ไม่ต้องตั้ง Spaces**


| หมวด                | ตัวแปร (ตัวอย่าง)                                                                              | dev                          | production                  |
| ------------------- | ---------------------------------------------------------------------------------------------- | ---------------------------- | --------------------------- |
| Django              | `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `DJANGO_SETTINGS_MODULE`                               | `DEBUG=True`                 | `DEBUG=False`               |
| Database            | `DATABASE_URL` หรือ `POSTGRES_`*                                                               | ชี้ container `db`           | ชี้ PostgreSQL บน Droplet   |
| Wagtail             | `WAGTAILADMIN_BASE_URL`                                                                        | `http://localhost:8000`      | `https://hall.tptk.org`     |
| Media               | `USE_SPACES` หรือ settings แยก env                                                             | `False` — `MEDIA_ROOT` local | `True` — ดู Spaces ด้านล่าง |
| Spaces              | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_STORAGE_BUCKET_NAME`, `AWS_S3_ENDPOINT_URL` | ไม่ใช้                       | ใช่ — จาก DO Control Panel  |
| Deploy (บน Droplet) | `SSH_HOST`, ใช้ใน GitHub Secrets ไม่ใส่ใน `.env` ของ repo                                      | —                            | GitHub Actions              |


**Spaces endpoint ตัวอย่าง:** `https://<region>.digitaloceanspaces.com` (เช่น `sgp1`)

### คำสั่งที่ใช้บ่อย (local)

```bash
docker compose up              # รัน dev
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py test
docker compose down
```

Frontend (เมื่อมี Vue entries):

```bash
cd frontend && npm install && npm run build   # หรือ npm run dev สำหรับ hot reload
```

---

## 4. โครงสร้างโปรเจก

โครงเป้าหมายของ repo — สอดคล้อง §2 (Wagtail เดียว, Vue 2 หน้า, ไม่มี backend แยก)

### โฟลเดอร์หลัก

```
hall.tptk.org/
├── docs/                          # เอกสาร (คู่มือนี้)
├── .github/workflows/             # GitHub Actions (deploy)
├── docker-compose.yml             # local + production บน Droplet
├── .env.example
├── manage.py
├── hall/                          # Django project
│   ├── settings/
│   │   ├── base.py
│   │   ├── dev.py
│   │   └── production.py
│   ├── urls.py
│   └── wsgi.py
├── home/                          # Wagtail — หน้าแรก (HomePage)
├── snippets/                      # Wagtail Snippet models
├── archive/                       # Item (ie: set, bookVolume), Segment, SegmentRevision
├── templates/                     # Django / Wagtail templates
├── static/                        # CSS/JS หลัง collectstatic (ไม่ใช่ PDF สแกน)
├── media/                         # dev เท่านั้น — ภาพ/PDF อัปโหลด (gitignore)
├── frontend/                      # Vue islands (Vite multi-entry)
│   ├── edition/                   # Vue — ตรวจทาน Edition (archive view)
│   ├── master/                    # Master TOC
│   └── vite.config.ts
└── scripts/                       # import / backup ช่วยเหลือ (ถ้าไม่ใส่ใน management)
```

### หน้าที่แต่ละส่วน


| ส่วน                 | หน้าที่                                                                                            |
| -------------------- | -------------------------------------------------------------------------------------------------- |
| `hall/settings/`     | config แยก dev / production · Spaces ใน production                                                 |
| `home/`              | `HomePage` และ routing หน้าแรก                                                                     |
| `snippets/`          | Snippet: Corpus, Edition, Script · Page: Corpus browse · management commands import CSV            |
| `archive/`           | Segment + SegmentRevision · Page: Archive/Edition (Vue), Master TOC (Vue) · view/API สำหรับตรวจทาน |
| `templates/`         | layout สาธารณะ · template mount `<div id="…-app">` สำหรับ Vue                                      |
| `frontend/`          | build `edition.js`, `master.js` → `static/dist/`                                                   |
| `docker-compose.yml` | services: `web`, `db` (PostgreSQL), `nginx` (production)                                           |


### Vue islands


| Page (ใน `archive/`) | Vite entry                 | mount ใน template |
| -------------------- | -------------------------- | ----------------- |
| Archive / Edition    | `frontend/edition/main.ts` | `edition.js`      |
| Master TOC           | `frontend/master/main.ts`  | `master.js`       |


หน้าอื่นใช้ Django template — ไม่มี Vue Router ครอบทั้ง site

### ภาพสแกนและ PDF

**ไม่อัปโหลดหน้าสแกนผ่าน Wagtail admin** — วางไฟล์ใน storage ตาม path ที่กำหนด · แถวใน `archive/` เก็บ `bookCode`, `pageNo` (หรือ path) แล้วชี้ URL ไป Spaces

| สภาพแวดล้อม | ที่เก็บไฟล์ | path ตัวอย่าง |
|-------------|------------|---------------|
| **production** | DigitalOcean Spaces | `archive/{bookCode}/{pageNo}.jpg` |
| **local dev** | โฟลเดอร์ `media/` (gitignore) | `media/archive/{bookCode}/{pageNo}.jpg` |

```
Spaces (หรือ media/ ใน dev)
└── archive/
    └── {bookCode}/
        ├── 001.jpg
        ├── 002.jpg
        └── ...
```

| ชั้น | หน้าที่ |
|------|--------|
| **ไฟล์** | script / `s3cmd` / DO CLI วางไฟล์เข้า Spaces — ไม่ผ่าน Wagtail `Image` |
| **DB (`archive/`)** | `bookCode`, `pageNo`, segment ฯลฯ · สร้าง URL จาก convention หรือเก็บ `scan_path` |
| **แอป / Vue** | อ่าน metadata จาก DB → แสดงภาพจาก URL Spaces |

**Wagtail media** (ถ้าใช้) — เฉพาะ asset หน้าเว็บทั่วไป (โลโก้ ฯลฯ) ไม่ใช่หน้าสแกนจำนวนมาก

**แยกจาก `static/`** — `static/` = CSS, `edition.js` · สแกนอยู่ใต้ `archive/…` ใน Spaces

import: bulk วางไฟล์ + บันทึก path ใน DB ผ่าน management command

### สิ่งที่ไม่มีใน repo

- FastAPI / sacred-app runtime
- HTMX
- Wagtail `Image` ต่อหน้าสแกน · ไฟล์สแกนบน disk Droplet ใน production

เมื่อ scaffold โปรเจกต ให้จัดโครงตามนี้ — แยก `snippets/` (metadata) กับ `archive/` (segment, ตรวจทาน, Vue) คงไว้

---

## 5. ขั้นตอนการพัฒนา

Workflow ทีม — อ้างอิง §2 (DoR) · §3 (local) · §8 (`main` merge แล้ว deploy อัตโนมัติ)

### Git และ branch

| แนวทาง | รายละเอียด |
|--------|------------|
| **branch หลัก** | `main` — production deploy จาก branch นี้ |
| **งานใหม่** | branch จาก `main` — ชื่อสั้น เช่น `feat/archive-models`, `fix/scan-url` |
| **merge** | ผ่าน PR (หรือ review คู่ก่อน merge ถ้าทีมเล็ก) — ไม่ push ตรง `main` งานใหญ่โดยไม่ review |

### ก่อนเริ่ม task

1. ตรวจ §2 Definition of Ready
2. ระบุ scope สั้น ๆ (in / out) และ acceptance 1–3 ข้อ
3. ทราบว่าแตะ app ไหน (`snippets/`, `archive/`, `frontend/`) ตาม §4

### ระหว่างพัฒนา

| ลำดับ | แนวทาง |
|-------|--------|
| 1 | model / migration ก่อน template หรือ Vue |
| 2 | หน้า Wagtail + URL ก่อน mount Vue island |
| 3 | API หรือ view ที่ Vue ใช้ — นิยามก่อนหรือคู่กับ frontend ใน PR เดียว |
| 4 | สแกน — วางไฟล์ตาม path §4 · ไม่ผ่าน Wagtail admin |
| 5 | commit เล็ก ตาม logical unit (model · template · frontend · import script) |

ทดสอบ local: `docker compose` · `migrate` · `test` · build frontend ถ้าแตะ Vue

### Pull request

PR ควรมี:

- คำอธิบายสั้น — ทำอะไร ทำไม
- acceptance criteria ที่ reviewer ตรวจได้
- migration ใหม่ (ถ้ามี) — รัน migrate บน DB ว่างได้
- ไม่มี `.env`, secrets, ไฟล์สแกนขนาดใหญ่

Reviewer ตรวจ: สอดคล้อง §2 · โครง §4 · ไม่ inline bulk data ใน Snippet

### Checklist ก่อน merge

- [ ] `docker compose exec web python manage.py test` ผ่าน (หรือ test ที่เกี่ยวข้อง)
- [ ] `migrate` รันผ่าน DB ว่าง
- [ ] แตะ Vue แล้ว build frontend สำเร็จ
- [ ] ไม่ commit secrets / สแกน / PDF
- [ ] อัปเดต docs ถ้าเปลี่ยน convention หรือโครงสร้าง

### ลำดับ implement แนะนำ (ภาพรวม)

ไม่ใช่ phase แยกระบบ — สร้างระบบใหม่ทีละชั้น:

| ลำดับ | งาน |
|-------|-----|
| 1 | scaffold Wagtail + Docker Compose + settings แยก env |
| 2 | `snippets/` — Snippet models · หน้า browse · import CSV |
| 3 | `archive/` — Item, Segment, SegmentRevision |
| 4 | import segment · วางสแกนใน Spaces + บันทึก path |
| 5 | Vue — Edition (archive) · Master TOC |
| 6 | deploy pipeline · go-live (redirect, URL map) |

ยืดหยุ่นได้ — แต่ **metadata ก่อน segment ก่อน Vue ก่อน go-live**

---

## 6. มาตรฐานและ convention

### ชื่อไฟล์และโฟลเดอร์

| ประเภท | แนวทาง |
|--------|--------|
| โฟลเดอร์ / ไฟล์ใน repo | ภาษาอังกฤษ — `snake_case` (Python) · `kebab-case` หรือ `snake_case` (Vue/TS ตามที่ตั้งใน tooling) |
| เอกสารใน `docs/` | ชื่อไฟล์อังกฤษ · เนื้อหาไทยได้ |
| Django apps | `home`, `snippets`, `archive` — ตาม §4 |
| migration | ชื่ออัตโนมัติของ Django — ไม่แก้ migration ที่ merge แล้ว |

### ภาษาในโค้ดและเอกสาร

| ส่วน | ภาษา |
|------|------|
| โค้ด (ชื่อ, comment สั้น) | อังกฤษ |
| docstring / commit / PR | อังกฤษ (แนะนำ) |
| เอกสาร `docs/` | ไทย · ศัพท์เทคนิคอังกฤษเมื่อจำเป็น |
| UI สาธารณะ | ตามผลิตภัณฑ์ (ไทย) — กำหนดเมื่อมีหน้าเว็บ |

### Git commit

รูปแบบสั้น: `<type>: <สรุป>` — อังกฤษ

| type | ใช้เมื่อ |
|------|----------|
| `feat` | ฟีเจอร์ใหม่ |
| `fix` | แก้บั๊ก |
| `docs` | เอกสารเท่านั้น |
| `refactor` | ปรับโครงสร้าง ไม่เปลี่ยน behaviour |
| `test` | เพิ่มหรือแก้ test |
| `chore` | tooling, deps, CI |

ตัวอย่าง: `feat: add Segment model` · `docs: update development guide §6`

### Wagtail / Django

- Snippet metadata — `RevisionMixin` + `DraftStateMixin` ตาม §2
- Segment / สแกนจำนวนมาก — model ใน `archive/` ไม่ inline ใน Snippet
- สแกน — path ใน Spaces ตาม §4 ไม่อัปโหลดผ่าน Wagtail admin
- settings — แยก `base` / `dev` / `production` · secrets จาก env เท่านั้น
- migration — review ก่อน merge · ขข้อมูล seed ผ่าน management command ไม่ใส่ใน migration

### Vue / frontend

- Vue 3 + Composition API
- Vite multi-entry — `edition`, `master` แยก bundle
- mount บน Wagtail template — ไม่ SPA ทั้ง site
- API เรียก Django view/endpoint ใน `archive/` — ไม่แยก FastAPI

### Import และ path สแกน

- path convention: `archive/{bookCode}/{pageNo}.jpg` (prod Spaces · dev `media/archive/…`)
- import ผ่าน management command — ไม่ commit ไฟล์สแกนใน repo
- backup DB — prefix `backups/` ใน Spaces แยกจาก `archive/`

---

## 7. การทดสอบ

### ทดสอบอะไร

| ชั้น | เน้น |
|------|------|
| **Models** | Snippet create · Segment + SegmentRevision · FK / constraint |
| **Views / API** | archive endpoints ที่ Vue ใช้ · URL สแกนจาก `bookCode` / `pageNo` |
| **Templates** | หน้า browse render · mount point Vue |
| **Import commands** | CSV ชุดเล็ก → จำนวน record ถูก · path สแกนสอดคล้อง convention |
| **Frontend** | logic สำคัญใน component (ถ้ามี) — build ผ่าน Vite |

ไม่บังคับ coverage สูงในช่วงแรก — แต่ต้องมี test สำหรับ model และ import ที่จะใช้ production

### คำสั่งรัน test (local)

```bash
docker compose exec web python manage.py test
docker compose exec web python manage.py test archive
docker compose exec web python manage.py test snippets
```

Frontend (เมื่อมี):

```bash
cd frontend && npm run test        # ถ้าตั้ง Vitest ฯลฯ
cd frontend && npm run build       # smoke — build ต้องผ่านก่อน merge
```

### ขั้นต่ำก่อน merge (ร่วมกับ §5)

- [ ] `manage.py test` ผ่าน — อย่างน้อย test ของ app ที่ PR แตะ
- [ ] `migrate` บน DB ว่างสำเร็จ
- [ ] แตะ Vue → `npm run build` ผ่าน
- [ ] แตะ import → ทดสอบด้วย sample ขนาดเล็ก

CI (GitHub Actions) — รัน test ก่อน deploy ตาม §8 เมื่อตั้ง workflow แล้ว

---

## 8. การ deploy

**สภาพแวดล้อม:** local (Docker Compose) → **production** โดยตรง — ไม่มี staging

**ลำดับตอนนี้:** พัฒนาและทดสอบบน local · push โค้ดไป [github.com/ptipitaka/hall.tptk.org](https://github.com/ptipitaka/hall.tptk.org) · **ยังไม่ตั้ง Droplet หรือ GitHub Actions** — ทำใน Phase 6 ก่อน go-live (ดู [step_by_step.md](./step_by_step.md))

### โครงสร้าง production


| ส่วน                       | ที่อยู่                                 |
| -------------------------- | --------------------------------------- |
| Wagtail + Gunicorn + Nginx | Droplet เดียว                           |
| PostgreSQL                 | Droplet เดียว                           |
| Media / PDF                | Spaces — path `archive/{bookCode}/{pageNo}` · metadata ใน `archive/` |
| โค้ด                       | GitHub → deploy ผ่าน GitHub Actions     |


### Workflow deploy

1. พัฒนาและทดสอบบน local (`docker compose`)
2. `git push` ไป GitHub (branch หลักที่กำหนด เช่น `main`)
3. **GitHub Actions** รัน test (ถ้ามี) แล้ว SSH เข้า Droplet
4. บน Droplet: `git pull` · `docker compose pull/build` · `migrate` · `collectstatic` · restart containers

ตั้ง **GitHub Secrets:** `SSH_HOST`, `SSH_USER`, `SSH_PRIVATE_KEY` (และ path deploy ถ้าต้องการ)

### Droplet เริ่มต้น

- ขนาดแนะนำ production เล็ก: **4 GB RAM**
- ติดตั้ง Docker + Docker Compose
- เปิด firewall: 22 (SSH), 80/443 (web) — ปิด PostgreSQL จากภายนอก
- SSL: Let's Encrypt (Certbot หรือ reverse proxy ใน compose)

### Backup PostgreSQL

- **รายวัน:** `pg_dump` ผ่าน cron บน Droplet
- อัปโหลดไฟล์ backup ไป **Spaces** (bucket แยกหรือ prefix `backups/` — ไม่ปนกับ media สาธารณะ)
- ทดสอบ restore เป็นระยะ

### หลัง deploy

- [ ] `migrate` สำเร็จ
- [ ] หน้าเว็บและ Wagtail admin เข้าได้
- [ ] หน้าตรวจทานแสดงสแกนจาก URL Spaces ตาม `bookCode` / `pageNo`
- [ ] backup รันและมีไฟล์ใน Spaces

---

## 9. อ้างอิง

- [step_by_step.md](./step_by_step.md) — checklist ทีละขั้น (phase 0–6)
- [migrate_discussion.md](./migrate_discussion.md) — บริบทและมติ migration

