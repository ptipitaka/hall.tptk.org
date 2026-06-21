# hall.tptk.org

Digital twin ของเนื้อหาสแกนในหนังสือพระไตรปิฎก — Wagtail CRX site พร้อม Vue islands สำหรับตรวจทาน Edition และ Master TOC

## Repository

Public repo สำหรับพัฒนาระบบใหม่แทน `tipitakahall.org` (Omeka) และ `sacred-app`

## Stack

- **Wagtail CRX 6.0** (`coderedcms`) — StreamField pages, navbar/footer, SEO
- **Wagtail 7.4** + **wagtail-localize** — หลายภาษา (en / th / zh)
- **Django 5.2** + PostgreSQL (Docker)

## เอกสาร

- [คู่มือการพัฒนา](docs/development_guide.md)
- [Checklist ทีละขั้น](docs/step_by_step.md)

## เริ่มต้น (local)

### Python virtual environment

```bash
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# macOS / Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

### Docker (แนะนำ)

```bash
cp .env.example .env
docker compose up --build
```

เปิด:

- Site: http://localhost:8000
- Wagtail admin: http://localhost:8000/admin/

สร้าง superuser (ครั้งแรก):

```bash
docker compose exec web python manage.py createsuperuser
```

## หลายภาษา (admin)

1. แก้ไขหน้า Home (locale **English**)
2. คลิก **Translate this page** → เลือก ไทย / 中文
3. แก้เนื้อหาแต่ละภาษาแยกกัน
4. สลับ locale ได้จากแผง **Status** ทางขวา

URL รองรับ prefix ภาษา: `/th/...`, `/zh/...` (ภาษาอังกฤษไม่มี prefix)

## คำสั่งที่ใช้บ่อย

```bash
docker compose up              # รัน dev
docker compose exec web python manage.py migrate
docker compose exec web python manage.py bootstrap_site
docker compose exec web python manage.py test
docker compose down -v       # ล้าง DB + media volumes (ติดตั้งใหม่)
```

Frontend (Vue islands — Phase 5):

```bash
cd frontend && npm install && npm run build
```

## โครงสร้างหลัก

- `hall/` — Django project + settings (`dev` / `production`)
- `website/` — Wagtail CRX page models (`WebPage`, `ArticlePage`, …)
- `snippets/` — catalog metadata (Phase 2)
- `archive/` — segment + ตรวจทาน (Phase 3+)
- `frontend/` — Vite multi-entry (`edition`, `master`)
