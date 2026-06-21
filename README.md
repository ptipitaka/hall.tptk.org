# hall.tptk.org

Digital twin ของเนื้อหาสแกนในหนังสือพระไตรปิฎก — Wagtail multi-page site พร้อม Vue islands สำหรับตรวจทาน Edition และ Master TOC

## Repository

Public repo สำหรับพัฒนาระบบใหม่แทน `tipitakahall.org` (Omeka) และ `sacred-app`

## เอกสาร

- [คู่มือการพัฒนา](docs/development_guide.md)
- [Checklist ทีละขั้น](docs/step_by_step.md)
- [Migrate Discussion](docs/migrate_discussion.md)

## เริ่มต้น (เมื่อ scaffold พร้อม)

```bash
git clone https://github.com/ptipitaka/hall.tptk.org.git
cd hall.tptk.org
cp .env.example .env
docker compose up --build
```

ตอนนี้โปรเจกอยู่ระหว่างจัดทำ docs และ scaffold — ดู [step_by_step.md](docs/step_by_step.md) สำหรับลำดับงาน
