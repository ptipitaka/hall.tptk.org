# hall.tptk.org

Digital twin ของเนื้อหาสแกนในหนังสือพระไตรปิฎก — Wagtail multi-page site พร้อม Vue islands สำหรับตรวจทาน Edition และ Master TOC

## Repository

Public repo สำหรับพัฒนาระบบใหม่แทน `tipitakahall.org` (Omeka) และ `sacred-app`

## เอกสาร

- [คู่มือการพัฒนา](docs/development_guide.md)
- [Checklist ทีละขั้น](docs/step_by_step.md)
- [Migrate Discussion](docs/migrate_discussion.md)

## เริ่มต้น (local)

```bash
git clone https://github.com/ptipitaka/hall.tptk.org.git
cd hall.tptk.org
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

## คำสั่งที่ใช้บ่อย

```bash
docker compose up              # รัน dev
docker compose exec web python manage.py migrate
docker compose exec web python manage.py test
docker compose down
```

Frontend (Vue islands — Phase 5):

```bash
cd frontend && npm install && npm run build
```

## โครงสร้างหลัก

- `hall/` — Django project + settings (`dev` / `production`)
- `home/` — Wagtail `HomePage`
- `snippets/` — catalog metadata (Phase 2)
- `archive/` — segment + ตรวจทาน (Phase 3+)
- `frontend/` — Vite multi-entry (`edition`, `master`)
