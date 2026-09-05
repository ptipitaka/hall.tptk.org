# การซิงก์ข้อมูลพัฒนา (DB + media) ผ่าน DigitalOcean Spaces

โปรเจกต์นี้แยกการซิงก์เป็นสองสายชัดเจน:

| อย่าง | ไหลผ่าน | ทิศทางที่ใช้จริง |
|---|---|---|
| **โค้ด** (`.py`, `.sh`, templates, config) | **git** (commit → push → pull) | local ↔ GitHub ↔ cloud |
| **ข้อมูล** (Postgres DB + ไฟล์ media) | **DigitalOcean Spaces** (สคริปต์ใน `scripts/`) | เครื่องที่มีข้อมูล → Spaces → เครื่องอื่น |

ข้อมูล **ไม่เก็บใน git** (DB/media อยู่ใน `.gitignore`) เพราะเป็นไฟล์ไบนารีก้อนใหญ่/มีข้อมูลส่วนบุคคล และ GitHub ปฏิเสธไฟล์เดียวเกิน 100 MB (ไฟล์ media ปัจจุบัน ~196 MB) จึงย้ายผ่าน object storage แทน

## ข้อกำหนดก่อนใช้งาน

- Docker Compose stack ต้องรันอยู่ (`db` + `web`) — ดู `.cursor/rules/docker-dev-workflow`
- ตั้งค่า Spaces keys ไว้อย่างใดอย่างหนึ่ง:
  - ใส่ใน `.env` ที่ repo root (สคริปต์โหลด `.env` ให้อัตโนมัติ), หรือ
  - export เป็น environment variables / ใส่ใน Cursor **Secrets** (บน Cloud Agent)

```
AWS_ACCESS_KEY_ID=...            # Spaces Access Key (20 ตัวอักษร)
AWS_SECRET_ACCESS_KEY=...        # Spaces Secret Key (43 ตัวอักษร)
AWS_S3_ENDPOINT_URL=https://<region>.digitaloceanspaces.com
# ตัวเลือก: SPACES_BUCKET (ค่าเริ่มต้น sacred), SPACES_PREFIX (ค่าเริ่มต้น archive)
```

> Spaces Access Key ต่างจาก DigitalOcean Personal Access Token (`dop_v1_...`) —
> สร้างจากเมนู **Spaces Object Storage → Access Keys** และคัดลอก Secret ทันทีที่สร้าง

## คำสั่ง

ใช้ `make` (ถ้ามี) หรือเรียก `bash scripts/sync.sh` ตรง ๆ ผลลัพธ์เหมือนกัน:

| งาน | ผ่าน make | ผ่าน bash |
|---|---|---|
| อัป DB + media ขึ้น Spaces | `make sync-up` | `bash scripts/sync.sh up` |
| ดึง DB + media ลงมา restore | `make sync-down` | `bash scripts/sync.sh down` |
| เฉพาะ DB ขึ้น / ลง | `make db-up` / `make db-down` | `bash scripts/sync.sh db-up` / `db-down` |
| เฉพาะ media ขึ้น / ลง | `make media-up` / `make media-down` | `bash scripts/sync.sh media-up` / `media-down` |

## รูปแบบการใช้งานที่แนะนำ

- **local คือต้นฉบับของข้อมูล** — แก้/เพิ่มเนื้อหาที่ local แล้ว `make sync-up`
- **cloud เป็นปลายทาง** — บน Cloud Agent รัน `make sync-down` เพื่อได้ข้อมูลชุดเดียวกัน
- อย่าแก้ข้อมูลทั้งสองฝั่งพร้อมกันแล้วหวังให้รวมกันเอง — เลือกทิศทางเดียวต่อครั้ง

## รายละเอียดเบื้องหลัง

สคริปต์รันเครื่องมือผ่านคอนเทนเนอร์ (ไม่ต้องลง `pg_dump`/`aws`/`boto3` บนเครื่อง host)
และเลือก `docker` หรือ `sudo docker` ให้เองอัตโนมัติ (รองรับทั้ง Docker Desktop และ VM ซ้อนของ Cloud Agent)

Object ที่ใช้บน Spaces (ภายใต้ `s3://<bucket>/<prefix>/`):

| ไฟล์ | เนื้อหา |
|---|---|
| `hall-<timestamp>.dump`, `hall-latest.dump` | Postgres custom-format dump (metadata + ข้อมูลทั้งหมด) |
| `hall-media-<timestamp>.tar.gz`, `hall-media-latest.tar.gz` | โฟลเดอร์ `media/` (originals + renditions) |

สคริปต์ที่เกี่ยวข้อง: `scripts/sync.sh`, `scripts/db/*.sh`, `scripts/media/*.sh`, `scripts/db/s3_transfer.py`
