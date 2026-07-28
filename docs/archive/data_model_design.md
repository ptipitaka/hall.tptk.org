# Data Model Design — Catalog (Pages) + Archive (Scan/Segment)

> **ประเภทเอกสาร:** Design Spec (ratified-pending) — ใช้เป็นจุดอ้างอิงสำหรับการ implement
> **สถานะ:** Draft สำหรับทบทวน · ออกแบบ field พร้อมระบุ **บังคับ/ไม่บังคับ**
> **อัปเดตล่าสุด:** 2026-06-25 (rev. publication defaults ครบชุด, M2M ภาษา/อักษร, catalog extent)
> **ขอบเขต:** โครงข้อมูลหลักของ `hall.tptk.org` — แทนที่ catalog snippets เดิมด้วย Wagtail Page tree + ตารางข้อมูลใน `archive/`

---

## 1. หลักการและกรอบคิด (FRBR)

ออกแบบตามโมเดลบรรณานุกรมสากล **FRBR** ซึ่งเข้ากับโครงพระไตรปิฎกอย่างเป็นธรรมชาติ
และช่วยตัดสินใจเรื่อง "ภาษาอยู่ชั้นไหน" ได้อย่างมีหลักการ

| FRBR | โมเดลในระบบเรา | คืออะไร | มีภาษา/อักษร? |
| --- | --- | --- | --- |
| **Work** (งานนามธรรม) | `CollectionPage` | **พระไตรปิฎกทั้งชุด** (เช่น "พระไตรปิฎกบาลี") | ❌ ไม่มี |
| **Expression** (การแสดงออก) | `EditionPage` | ฉบับหนึ่ง ในภาษา+อักษรหนึ่ง (มหาจุฬาฯ / ภาคแปลไทย / PTS) | ✅ มี |
| **Item / Manifestation** | `VolumePage` | เล่ม/ภาคของฉบับนั้น | สืบจาก Edition |

**ข้อสรุปเชิงหลักการ**

- ภาษา (`content_language`) และอักษร (`content_script`) เป็นคุณสมบัติของ **Edition เท่านั้น**
- `CollectionPage` คือ Work ที่อยู่เหนือภาษา จึง **ไม่มี** `content_languages`
- มหาจุฬาเตปิฏกํ กับ ภาคแปลไทย = **1 CollectionPage + หลาย EditionPage** (Work เดียว แสดงต่างภาษา)
- แยกเป็น 2 Collection ก็ต่อเมื่อเป็นคนละ Work จริง (เช่น ติปิฏก vs อฏฺฐกถา/ฏีกา → ต่าง `classification`)

### "ภาษา" สองความหมาย (อย่าสับสน)

| สิ่ง | ความหมาย | ตัวอย่าง | เก็บที่ไหน |
| --- | --- | --- | --- |
| **Page locale** (Wagtail) | ภาษาของ **UI / metadata** ที่แสดงผลหน้าเว็บ | en / th | Wagtail (wagtail-localize) จัดการเอง |
| **content_language** | ภาษาของ **ตัวข้อความคัมภีร์** | Pāli, Thai, Sanskrit | FK บน `EditionPage` |

สองแกนนี้ตั้งฉากกัน — EditionPage "มหาจุฬาฯ" (content_language = Pāli) มีหน้า metadata locale ไทย/อังกฤษได้พร้อมกัน

---

## 2. โครงสร้างรวม

```
website/models.py  (Wagtail Pages — tree, revision, i18n, SEO)
────────────────────────────────────────────────────────────
CatalogIndexPage                       หน้ารวมคลัง (browse hub)
└── CollectionPage      Work           พระไตรปิฎกทั้งชุด
    └── EditionPage     Expression     ฉบับ/ภาษา/อักษร
        └── VolumePage  Item           เล่ม/ภาค  + RoutablePageMixin (folio URL)

archive/models.py  (ตารางข้อมูลจำนวนมาก — ไม่ใช่ Page, ไม่ revision แบบ Wagtail)
────────────────────────────────────────────────────────────
ScanFolio          ภาพสแกน (path-based, ไม่ใช่ Wagtail Image)
Segment            ข้อความถอด + anchor ไปภาพ
SegmentRevision    ประวัติการแก้ segment (audit / four-eyes)
ReferenceAlias     แผนที่อ้างอิงเดิม (PTS/VRI/…) → cref ของเรา

snippets/  (คงไว้ — vocabulary)
────────────────────────────────────────────────────────────
Classification, Tradition, Country, ContentLanguage, ContentScript, SegmentKind
CanonicalSection   (ใหม่) โครงสร้างคัมภีร์แบบ tree: ปิฏก→นิกาย→…
```

**เหตุผลแยก app**

- Page tree (Collection/Edition/Volume) มีจำนวนหลักร้อย–พัน → เหมาะกับ Wagtail explorer/revision
- ScanFolio/Segment มีหลักหมื่น–แสนแถว → lifecycle และ revision ต่างกันโดยสิ้นเชิง ไม่ควรอยู่ใน Page tree
- สอดคล้องมติเดิมใน `development_guide.md` และ `migrate_discussion.md` ("ไม่ inline segment", "ไม่อัปโหลดสแกนผ่าน Wagtail admin")

---

## 3. Page Models (`website/models.py`)

> คอลัมน์ **บังคับ**: ✓ = required (NOT NULL / blank=False) · – = optional (null/blank)
> ฟิลด์ `title`, `slug` เป็นของ Wagtail Page อยู่แล้ว (บังคับโดย Wagtail)

### 3.0 หลักการตั้งรหัส — `code` / `slug` / `title`

ระบบ identifier มี **3 บทบาทเท่านั้น** ใช้ชื่อเดียวกันทั้งระบบ:

| บทบาท | field | คุณสมบัติ |
| --- | --- | --- |
| ชื่อมนุษย์อ่าน | `title` (Page) / `name` (snippet) | แปลภาษาได้ |
| **รหัสคงที่** | **`code`** | ไม่แปลภาษา · ตั้งครั้งเดียว ไม่แก้พล่อย · ใช้ใน path/citation/import/`cref` |
| URL | `slug` (Page built-in) | แก้/แปลได้ |

**กติกา**

1. ใช้ `code` เป็นชื่อเดียวสำหรับ "รหัสคงที่" ทุก model — เลิกใช้ `siglum`, `work_key`, `book_code`
2. **`code` unique ภายใต้ parent** (sibling scope) ไม่ต้อง unique ทั้งโลก
   - reference เต็มเป็น composite จึง unique เสมอ: `{collection.code}/{edition.code}/{volume.code}`
   - บังคับด้วย `UniqueConstraint(parent, code)`
3. **catalog pages (Collection/Edition/Volume): `slug` default = `slugify(code)`** (override ได้)
   - ได้ URL ASCII คงที่ อ้างอิงได้ เช่น `/catalog/pali-tipitaka/pali-2e/vol-01/`
   - หน้าเว็บทั่วไป (WebPage/Article) คง default เดิม (slug จาก title)
4. ลำดับความสำคัญในการอ้างอิง: **Collection.code → Edition.code → Volume.code**

### 3.1 CatalogIndexPage

หน้ารวมคลัง — ทำให้การแสดงผลหน้า browse เป็นระบบ และปรับตามข้อมูลที่เปลี่ยนได้

| field | ชนิด | บังคับ | หมายเหตุ |
| --- | --- | :---: | --- |
| `intro` | RichTextField | – | คำนำ/คำอธิบายคลัง |
| `body` | StreamField | – | บล็อกแนะนำ/ไฮไลต์ (ใช้ของ website เดิมได้) |

```python
subpage_types  = ["website.CollectionPage"]
parent_page_types = ["website.WebPage", "home.HomePage"]   # ปรับตาม site tree จริง
max_count = None
```

### 3.2 CollectionPage — *Work (ทั้งชุด, ไม่มีภาษา)*

| field | ชนิด | บังคับ | หมายเหตุ |
| --- | --- | :---: | --- |
| `code` | CharField | ✓ | รหัสคงที่ของ Work — **first priority ในการอ้างอิง** (เช่น `pali-tipitaka`) · `slug` default = slugify(code) |
| `description` | RichTextField | – | คำอธิบายชุดคัมภีร์ |
| `classification` | FK → Classification | – | ระดับชุด: ติปิฏก / อฏฺฐกถา / ฏีกา |
| `tradition` | FK → Tradition | – | นิกาย/สายจารีต |
| `country` | FK → Country | – | **ประเทศของชุดคัมภีร์** (ไม่ใช่ที่พิมพ์) · label: ประเทศ / Country · เช่น ฉฏฺฐสงฺคีติ พิมพ์ใต้หวันก็ยังเป็นพม่า |
| `sort_order` | IntegerField | ✓ (default 0) | จัดลำดับในหน้า index |
| ~~`content_languages`~~ | — | — | **ตัดออก** — ภาษาอยู่ที่ Edition |

> `code` unique ในกลุ่ม Collection (siblings ใต้ CatalogIndexPage)

```python
subpage_types  = ["website.EditionPage"]
parent_page_types = ["website.CatalogIndexPage"]
```

### 3.3 EditionPage — *Expression (จุดกำหนดภาษา/อักษร)*

| field | ชนิด | บังคับ | หมายเหตุ |
| --- | --- | :---: | --- |
| `code` | CharField | ✓ | รหัสฉบับ user-friendly เช่น `pali-2e`, `thai-translation`, `pts` · `slug` default = slugify(code) |
| `content_languages` | M2M → ContentLanguage | ✓ | **ภาษาของข้อความ** — ฉบับเดียวอาจมีหลายภาษา |
| `content_scripts` | M2M → ContentScript | ✓ | อักษรที่ใช้ — ฉบับเดียวอาจมีหลายระบบ |
| `edition_role` | CharField choices | ✓ | `source` / `translation` / `transliteration` / `commentary` / `digital` — **field แยกจาก code** (ใช้ใน logic/filter/badge) |
| `source_edition` | FK → self | – | ฉบับต้นทาง (กรณีแปล/ปริวรรต) |
| `volume_set_count` | PositiveIntegerField | – | จำนวนชุดเล่มตาม catalog (ระดับฉบับ — ไม่ override ต่อเล่ม) |
| `physical_volume_count` | PositiveIntegerField | – | จำนวนเล่มผูกจริงเมื่อไม่เท่ากับชุดเล่ม (ว่าง = เท่ากับ `volume_set_count`) |
| `publisher` | CharField | – | **ค่า default ของฉบับ** — Volume override ได้ (ดู §3.4) |
| `place_of_publication` | CharField | – | **default** สถานที่พิมพ์ — Volume override ได้ |
| `published_year` | CharField | – | **default** ของฉบับ (string รองรับ พ.ศ./ค.ศ./ช่วงปี) — Volume override ได้ |
| `print_number` | CharField | – | **default** ครั้งที่พิมพ์ของฉบับ — Volume override ได้ |
| `isbn_number` | CharField | – | **default** ISBN-10/13 — Volume override ได้ |
| `description` | RichTextField | – | |
| `catalog_sort_order` | IntegerField | ✓ (default 0) | ลำดับเรียงใน admin/catalog UI |

> - `code` unique ภายใน Collection (siblings) → `pali-2e` ใช้ซ้ำต่าง Collection ได้
> - `code` กับ `edition_role` **แยกกัน**: code ไว้สื่อ user/URL · role ไว้ทำ logic (อย่า parse role จาก code)
> - **Publication defaults** (`publisher`, `place_of_publication`, `published_year`, `print_number`, `isbn_number`) ที่ Edition = **ค่า default** ของทั้งฉบับ
>   ถ้า Volume กรอกค่าเดียวกันนี้ = override เฉพาะเล่ม (รองรับฉบับที่ทยอยพิมพ์/บางเล่มปรับปรุง)
> - `volume_set_count` / `physical_volume_count` เป็นข้อมูลระดับฉบับ (Catalog extent) — ไม่มี override ต่อ Volume

```python
subpage_types  = ["website.VolumePage"]
parent_page_types = ["website.CollectionPage"]
```

### 3.4 VolumePage — *Item (container ของ folio + segment)*

> ตามที่ตกลง: **Volume เป็น Page** (รับภาระประสิทธิภาพได้ดีกว่า inline)

| field | ชนิด | บังคับ | หมายเหตุ |
| --- | --- | :---: | --- |
| `code` | CharField | ✓ | รหัสเล่ม เช่น `vol-01` · เป็นส่วนของ scan path + citation · `slug` default = slugify(code) |
| `volume_index` | IntegerField | ✓ | ลำดับเรียงจริงในฉบับ (มีเสมอ แม้ไม่มีเลขเล่ม) |
| `number` | CharField | – | เลขเล่มที่แสดง เช่น "๑" — **ไม่บังคับ** (บางฉบับใช้ชื่อเล่มแทน) |
| `part_label` | CharField | – | ภาค/ตอน เช่น "ภาค ๒" |
| `section` | FK → CanonicalSection | – | ปิฏก/นิกายที่เล่มนี้สังกัด (ดู §3.5) |
| `publisher` | CharField | – | **override** ของเล่ม (ว่าง = ใช้ค่า Edition) |
| `place_of_publication` | CharField | – | **override** สถานที่พิมพ์ของเล่ม (ว่าง = ใช้ค่า Edition) |
| `published_year` | CharField | – | **override** ปีพิมพ์ของเล่ม (ว่าง = ใช้ค่า Edition) |
| `print_number` | CharField | – | **override** ครั้งที่พิมพ์ของเล่ม (ว่าง = ใช้ค่า Edition) |
| `isbn_number` | CharField | – | **override** ISBN ของเล่ม (ว่าง = ใช้ค่า Edition) |
| `description` | RichTextField | – | |

> - `code` unique ภายใน Edition (siblings)
> - **กรณีไม่มีเลขเล่ม:** ใช้ `title` (ชื่อเล่ม) + `part_label` แสดงผล · ใช้ `volume_index` เรียงลำดับ · `number` ว่างได้ (UI fallback ไป `title`)
> - **ข้อมูลการพิมพ์** (`publisher`, `place_of_publication`, `published_year`, `print_number`, `isbn_number`): ปกติฉบับเดียวกันค่าเท่ากัน → กรอกที่ Edition พอ
>   เล่มที่ทยอยพิมพ์/ปรับปรุงต่างจากเล่มอื่น → กรอก override ที่ Volume เฉพาะเล่มนั้น
>   property helper เช่น `effective_publisher`, `effective_isbn_number` = Volume ถ้ามี ไม่งั้น fallback ไป Edition

```python
subpage_types  = []                         # ไม่มี Page ลูก
parent_page_types = ["website.EditionPage"]
# + RoutablePageMixin → URL ระดับ folio (ดู §6)
```

**การแบ่งปิฏก/นิกายภายในฉบับ** — เก็บเป็น FK ไป snippet `CanonicalSection` (controlled vocabulary แบบ tree)
ไม่ใช้ free tag และไม่เพิ่มชั้น Page คั่น เพื่อรักษาโครง Collection→Edition→Volume พร้อมได้ลำดับชั้น/i18n/`code`

### 3.5 CanonicalSection (snippet — `snippets/`)

> โครงสร้างคัมภีร์มาตรฐาน (ปิฏก → นิกาย → หมวด…) เป็น **controlled vocabulary แบบ tree**
> ใช้แพตเทิร์นเดียวกับ `Classification` ที่มีอยู่ (self-referential + `code` + TranslatableMixin)
> **ทำไมไม่ใช้ free tag:** ปิฏก/นิกายเป็นชุดค่าจำกัดและมีลำดับชั้น — ต้องการความถูกต้องของค่า,
> i18n, `code`, การเรียง และ query ที่แม่นเพื่อ "เทียบเคียง" ข้ามฉบับ ซึ่ง tag ให้ไม่ได้

| field | ชนิด | บังคับ | หมายเหตุ |
| --- | --- | :---: | --- |
| `code` | CharField | ✓ | รหัสสั้น เช่น `vin` `sut` `dn` `mn` — เป็น building block ของ `cref` (§7) |
| `slug` | SlugField | ✓ | default = slugify(code) |
| `parent` | FK → self | – | ปิฏก (root) → นิกาย (child) → หมวดย่อย |
| `kind` | CharField choices | – | `pitaka` / `nikaya` / `section` — ระดับของโหนด |
| `name` | CharField | ✓ | ชื่อ (translatable per locale) |
| `description` | TextField | – | |
| `sort_order` | IntegerField | ✓ (default 0) | |

- ใช้ `HallTranslatableMixin` + unique `(locale, code)` ตามแพตเทิร์น vocabulary เดิม
- `code` ของ section เป็น building block ของ `cref` → โครงสร้างกับ canonical ref สอดคล้องกัน

---

## 4. ScanFolio (`archive/models.py`)

### 4.1 มติ: ไม่ใช้ Wagtail Image, ไม่ใช่ Page

| ทางเลือก | ปัญหากับงานหลักหมื่น–แสนภาพ |
| --- | --- |
| Wagtail `Image` | ทุกภาพเป็น row + ระบบ rendition สร้างไฟล์ทวีคูณ · chooser ไม่เหมาะ bulk · ขัดมติเดิม |
| `ScanFolioPage` (Page ต่อ folio) | Page หลายหมื่น → explorer/tree พัง · revision ไม่จำเป็น |
| **ScanFolio (model) + path** ✅ | row เบา · upload ผ่าน script/s3cmd เข้า Spaces · ตรง convention เดิม |

URL ระดับ folio สำหรับแชร์/อ้างอิง → ใช้ `RoutablePageMixin` บน VolumePage + citation URL (§6)

### 4.2 Fields

| field | ชนิด | บังคับ | หมายเหตุ |
| --- | --- | :---: | --- |
| `volume` | FK → VolumePage | ✓ | สังกัดเล่ม (on_delete=PROTECT) |
| `sequence` | IntegerField | ✓ | ลำดับกายภาพในเล่ม (ใช้ path/nav/sort) |
| `page_no` | CharField | – | เลขหน้าที่พิมพ์จริง (อาจ "ก", "iv", "42") |
| `image_path` | CharField | – | override path เต็ม; ว่าง = derive จาก composite (ดู §4.2 URL) |
| `width` | IntegerField | – | px — สำหรับ viewer/zoom/พิกัด |
| `height` | IntegerField | – | px |
| `status` | CharField choices | ✓ (default `present`) | `present` / `missing` / `excluded` / `pending` |
| `checksum` | CharField | – | ตรวจ integrity หลัง bulk upload |
| `iiif_id` | CharField | – | (อนาคต) รองรับ IIIF Image API |

**Constraints / Index**

- `UniqueConstraint(volume, sequence)`
- index `(volume, sequence)` สำหรับ nav

**URL ภาพ = property (ไม่เก็บ URL เต็มใน DB)**

scan path เป็น **hierarchical** ตาม composite code → unique ทั้งระบบ และตรงกับโครง citation:

```python
# โครง: archive/{collection.code}/{edition.code}/{volume.code}/{sequence}.jpg
# dev:        /media/archive/pali-tipitaka/pali-2e/vol-01/001.jpg
# production:  https://sacred.sgp1.digitaloceanspaces.com/archive/pali-tipitaka/pali-2e/vol-01/001.jpg
```

- สลับ dev/prod ด้วย setting เดียว (`USE_SPACES`)
- **เปลี่ยนจาก convention เดิม** (`archive/{bookCode}/{pageNo}.jpg` แบบ flat) — อัปเดต `development_guide.md` + `step_by_step.md` แล้ว
  · import map legacy `bookCode` → path ใหม่ได้

### 4.3 มองไกล: IIIF (เผื่อไว้ ไม่ทำตอนนี้)

เป้าหมาย "เทียบเคียง/ตรวจสอบ/อ้างอิง" ตรงกับมาตรฐานวิชาการ **IIIF** (deep zoom, อ้างพิกัดภาพ, viewer เทียบหลายฉบับ)
ออกแบบ field เผื่อ (`iiif_id`, เก็บพิกัดแบบ normalized §5) เพื่อต่อยอดภายหลังโดยไม่ต้อง migrate

---

## 5. Segment + SegmentRevision (`archive/models.py`)

### 5.1 Segment

| field | ชนิด | บังคับ | หมายเหตุ |
| --- | --- | :---: | --- |
| `volume` | FK → VolumePage | ✓ | ขอบเขตหลัก (on_delete=PROTECT) |
| `order` | IntegerField | ✓ | ลำดับอ่านในเล่ม |
| `kind` | FK → SegmentKind | ✓ | heading / prose / gāthā / structural … |
| `text` | TextField | ✓ | ข้อความถอด |
| `cref` | CharField (index) | ✓ | **canonical reference** ของเรา (§7) — edition-independent |
| `cref_end` | CharField | – | กรณี segment คร่อมหลายหน่วย |
| `structural_ref` | CharField | – | เลขข้อ/ย่อหน้าที่พิมพ์ในฉบับนี้ (เช่น VRI para) |
| `parent` | FK → self | – | โครงสร้างย่อยในเล่ม (vagga→sutta→para) |
| **anchor → ภาพ** | | | |
| `folio` | FK → ScanFolio | ✓ | folio หลักที่ข้อความนี้อยู่ |
| `folio_end` | FK → ScanFolio | – | กรณีข้อความคร่อมหน้า |
| `region` | JSONField | ✓¹ | bbox normalized `{x,y,w,h}` (0–1) — overlay บนภาพ |
| `region_note` | CharField | – | คำอธิบายตำแหน่ง (เช่น "คอลัมน์ขวา") |
| **metadata** | | | |
| `status` | CharField choices | ✓ (default `draft`) | `draft` / `review` / `published` |
| `citation_key` | CharField | ✓ | ID คงที่สำหรับลิงก์ `?seg=` (unique-in-volume) |
| `source_note` | TextField | – | หมายเหตุวิชาการ |

> **¹ region บังคับทุก segment (ตามมติ)** แต่เพื่อรองรับ bulk import ข้อมูลเดิมที่ยังไม่มี bbox:
> - import เข้ามาเป็น `status=draft` ได้โดย `region` ยังว่างชั่วคราว
> - `clean()` **บังคับ `region`** เมื่อจะเลื่อนเป็น `status=review` หรือ `published`
> - ผลคือ **ทุก segment ที่ถูกเผยแพร่/ให้บริการ มี region เสมอ** ตามเจตนา (ตรวจเทียบภาพ↔ข้อความได้)

**Constraints / Index**

- `UniqueConstraint(volume, citation_key)`
- index `cref` (สำคัญมาก — ใช้ join cross-edition)
- index `(volume, order)`
- พิจารณา GIN index บน `text` ถ้าทำ full-text search

**หัวใจการทำงาน**

- `folio` + `region` → viewer วาดกรอบบนภาพตรงกับ segment text → ผู้ตรวจเทียบทันที
- `cref` → query segment เดียวกันข้ามหลาย Edition มาวางคู่กัน → "เทียบเคียง" โดยไม่ต้องมีตาราง mapping หนักตั้งแต่แรก

### 5.2 SegmentRevision

ประวัติแยกจาก Wagtail (segment มี workflow เฉพาะ — รองรับ four-eyes/branch ตาม `migrate_discussion.md`)

| field | ชนิด | บังคับ | หมายเหตุ |
| --- | --- | :---: | --- |
| `segment` | FK → Segment | ✓ | (on_delete=CASCADE) |
| `text` | TextField | ✓ | snapshot ข้อความ |
| `kind` | FK → SegmentKind | ✓ | snapshot |
| `cref` | CharField | ✓ | snapshot |
| `region` | JSONField | – | snapshot (ตาม segment) |
| `created_by` | FK → User | ✓ | ผู้แก้ |
| `created_at` | DateTimeField | ✓ (auto) | |
| `change_note` | CharField | – | สรุปการแก้ |
| `is_current` | BooleanField | ✓ (default False) | รุ่นที่ใช้แสดง |

> revision ของ **metadata เล่ม/ฉบับ** ใช้ Wagtail Page revision; revision ของ **ข้อความ segment** ใช้ตารางนี้ — แยกชั้นชัดเจน

---

## 6. URL อ้างอิงถาวร (Citation URLs)

> มติ: **ต้องมี URL อ้างอิงถาวรแยก** เพื่อการศึกษา/แชร์/อ้างอิงข้ามฉบับ

### 6.1 รูปแบบ URL

| ประเภท | รูปแบบ | ทำหน้าที่ |
| --- | --- | --- |
| Folio viewer (ใต้ Volume) | `/{volume-path}/f/{sequence}/` | เปิด viewer ที่หน้านั้น (RoutablePageMixin) |
| Segment ในหน้า | `/{volume-path}/f/{sequence}/?seg={citation_key}` | เลื่อนไป segment |
| **Citation ถาวร (edition-independent)** | `/cite/{cref}/` | แสดงตัวเลือก/เทียบทุก Edition ที่มี cref นี้ |
| Citation เจาะ Edition | `/cite/{collection.code}/{edition.code}/{cref}/` | ไปยัง segment ของฉบับนั้นตรง ๆ (composite เพราะ edition.code unique แค่ใน collection) |
| Legacy alias | `/cite/{scheme}:{value}/` | แปลงอ้างอิงเดิม → 302 → canonical |

- URL `/cite/...` **ไม่ผูกกับ slug ของ Page** → คงที่แม้ปรับโครง/เปลี่ยนชื่อหน้า
- `/cite/{cref}/` คือ "ที่อยู่ทางวิชาการ" ของข้อความ — เหมาะใส่ในงานวิจัย/อ้างอิง

### 6.2 ตัวอย่าง

```
/cite/sut.mn.1/                          → Mūlapariyāya across all editions (picker/compare)
/cite/pali-tipitaka/pali-2e/sut.mn.1/   → ฉบับ pali-2e ของ MN 1 ตรง ๆ
/cite/pts:M.i.1/                         → PTS Majjhima เล่ม i หน้า 1 → 302 → /cite/sut.mn.1/
```

---

## 7. Canonical Reference System (`cref`)

> มติ: **ศึกษาระบบเดิมของทุกสถาบัน แล้วสร้างของเราเองที่ดีกว่า** + แปลงอ้างอิงเก่ามาเข้าถึงข้อมูลเราได้

### 7.1 บทเรียนจากระบบเดิม

| ระบบ | รูปแบบ | จุดแข็ง | จุดอ่อน |
| --- | --- | --- | --- |
| **PTS** | `M i 1` (เล่ม/หน้า) | มาตรฐานวิชาการตะวันตก | ผูกกับเล่ม/หน้าของฉบับ PTS · หยาบ (ระดับหน้า) · ต่างฉบับเลขไม่ตรง |
| **VRI/CST** | เลขย่อหน้า (paragraph) | ละเอียดระดับ para · ดิจิทัล | ผูกกับฉบับฉัฏฐสังคีติ |
| **Thai (สยามรัฐ/มหาจุฬาฯ)** | เล่ม/ข้อ/หน้า | ใช้ในไทยแพร่หลาย | ผูกฉบับ · เลขข้อต่างฉบับไม่ตรง |
| **BJT (สิงหล)** | เล่ม/หน้า | parallel แปลสิงหล | ผูกฉบับ |
| **SuttaCentral (MST)** | `mn1:1.2` (โครงสร้าง+segment id) | **edition-independent** · ละเอียดระดับ segment · เทียบข้ามฉบับได้ | ต้อง map กับฉบับสิ่งพิมพ์ |

**ข้อสรุป:** ไม่มีระบบเดียวที่ใช้ได้ทุกฉบับ — ระบบที่ดีที่สุด (SuttaCentral) เป็นแบบ
**edition-independent + structural + segment-level** เราจะออกแบบ `cref` แนวนี้แต่ปรับให้เหมาะกับงานเรา

### 7.2 ออกแบบ `cref` ของเรา

**หลักการ**

1. **Edition-independent** — อ้างถึง "หน่วยตรรกะของ Work" ไม่ผูกเล่ม/หน้าของฉบับใด → segment ของหลายฉบับที่มี `cref` เดียวกัน = ข้อความคู่ขนาน → เทียบเคียงได้
2. **Hierarchical + URL-safe** — เป็น path จุดคั่น ใช้รหัสสั้นมาตรฐาน
3. **Segment-level** — ละเอียดถึงย่อหน้า/หน่วยย่อย
4. **Stable** — กำหนดครั้งเดียวคงที่ตลอด

**รูปแบบ**

```
{pitaka}.{division}.{book}.{section}.{unit}[.{sub}]
```

| ส่วน | ความหมาย | ตัวอย่างรหัส |
| --- | --- | --- |
| `pitaka` | ปิฏก | `vin` `sut` `abh` |
| `division` | นิกาย/หมวดใหญ่ | `dn` `mn` `sn` `an` `kn` (สำหรับ Sutta) |
| `book/section/unit` | หนังสือ/วรรค/สูตร/ข้อ | ตามโครงสร้างคัมภีร์ |

**ตัวอย่าง**

```
sut.mn.1            → Mūlapariyāya Sutta (MN 1)
sut.mn.1.2          → ย่อหน้า/section ที่ 2 ของ MN 1
sut.sn.22.150       → SN samyutta 22 sutta 150
vin.para.1          → Vinaya ย่อหน้า 1 (โครง Vinaya ใช้ schema ย่อยของตน)
abh.dhs.1           → Abhidhamma Dhammasaṅgaṇī หน่วย 1
```

> รายละเอียด schema ต่อปิฏก/นิกาย (รหัสและความลึกของ unit) จัดทำเป็นภาคผนวกแยกเมื่อเริ่ม import จริง
> โดยอ้าง mapping ของ SuttaCentral/VRI เป็นจุดตั้งต้น

### 7.3 ReferenceAlias — แปลงอ้างอิงเดิม → ของเรา

ตารางแยกสำหรับ resolve อ้างอิงเก่าทุกระบบมายัง `cref` (และ segment)

| field | ชนิด | บังคับ | หมายเหตุ |
| --- | --- | :---: | --- |
| `scheme` | CharField choices | ✓ | `pts` / `vri` / `thai_siam` / `mahachula` / `burmese_cs` / `sinhala_bjt` … |
| `value` | CharField | ✓ | สตริงอ้างอิง normalize แล้ว (เช่น `M.i.1`) |
| `cref` | CharField (index) | ✓ | ชี้หน่วยตรรกะของเรา |
| `edition` | FK → EditionPage | – | เมื่อ scheme ผูกฉบับเฉพาะ (เช่น เลขหน้าฉบับนั้น) |
| `note` | CharField | – | |

**Constraints**

- `UniqueConstraint(scheme, value, edition)`
- index `cref`

**การใช้งาน**

- `/cite/pts:M.i.1/` → ค้น `ReferenceAlias(scheme=pts, value=M.i.1)` → ได้ `cref` → 302 → `/cite/{cref}/`
- รองรับ "อ้างอิงแบบเก่าเพื่อเข้าถึงข้อมูลแบบใหม่ของเรา" ตามมติ
- หนึ่ง segment มีได้หลาย alias (PTS, VRI, Thai, …) → แสดงเป็น "อ้างอิงเทียบ" บนหน้า segment

---

## 8. ความสัมพันธ์กับ snippets เดิม

| เก็บไว้ (vocabulary) | ลบ/แทนที่ |
| --- | --- |
| `Classification` (FK จาก CollectionPage) | `snippets.models.catalog.Collection` |
| `Tradition` (FK จาก CollectionPage) | `snippets.models.catalog.Edition` |
| `ContentLanguage` (FK จาก EditionPage) | `snippets.models.catalog.Volume` |
| `ContentScript` (FK จาก EditionPage) | `CatalogGroup` ใน `snippets/wagtail_hooks.py` |
| `SegmentKind` (FK จาก Segment) | migration/seed ของ catalog snippets |
| `CanonicalSection` (ใหม่ · FK จาก VolumePage) | — |

> เมื่อย้ายเป็น Page tree แล้ว validator locale-sync (`validate_same_locale_fk` ใน `snippets/models/base.py`)
> สำหรับชั้น catalog ไม่จำเป็นอีก — Wagtail page locale จัดการ i18n ให้ใน tree

---

## 9. ประสิทธิภาพเมื่อ scale

| ชั้น | จำนวนประมาณ | กลยุทธ์ |
| --- | --- | --- |
| Collection/Edition/Volume Pages | ร้อย–พัน | Wagtail tree ปกติ + index |
| ScanFolio | หลักหมื่น–แสน/Collection | bulk import command · index DB · ไฟล์บน Spaces/CDN |
| Segment | หลายแสน/Edition | pagination ผ่าน API · ไม่โหลดทั้งเล่มครั้งเดียว · index `cref` |

**กฎเหล็ก:** ห้าม `InlinePanel` ScanFolio/Segment บน VolumePage — แก้ผ่าน **Vue island + API** เท่านั้น
Wagtail admin ใช้เฉพาะ metadata (Collection/Edition/Volume) และ trigger import

---

## 10. การทำงานคู่ ScanFolio ↔ Segment (transcription)

```
VolumePage template → #edition-app (Vue island)
   ┌───────────────┬────────────────────────┐
   │ ScanFolio     │ Segment editor          │
   │ viewer (ภาพ)  │ text + kind + cref      │
   │ + วาด region  │ + region (bbox)         │
   └───────┬───────┴───────────┬────────────┘
           │ REST API (archive/) │
           ▼                     ▼
       ScanFolio              Segment.save → SegmentRevision
       (Spaces URL)           (audit / four-eyes)
```

- ผู้บันทึกดูภาพ → ลากกรอบ (region) → พิมพ์ข้อความ → ผูก `cref`
- ทุก save สร้าง `SegmentRevision`
- ไม่ผ่าน Wagtail admin

---

## 11. สรุปการตัดสินใจ (locked) และที่ยังเปิด

### ตัดสินใจแล้ว

- Collection = **พระไตรปิฎกทั้งชุด** (Work) · Edition = ภาษา/อักษร · Volume = **Page**
- ภาษา/อักษรอยู่ที่ **Edition เท่านั้น** — Collection ไม่มี `content_languages`
- ScanFolio = model + path (ไม่ใช่ Image/Page) · ScanFolioPage = ไม่ทำ
- URL folio ผ่าน RoutablePageMixin + **citation URL ถาวรแยก** `/cite/...`
- Segment + SegmentRevision ใน `archive/` · **region บังคับก่อน publish**
- `cref` = canonical ref ของเรา (edition-independent) + `ReferenceAlias` แปลงระบบเก่า
- มี `CatalogIndexPage`
- ปิฏก/นิกาย = snippet `CanonicalSection` (controlled vocabulary แบบ tree) FK จาก VolumePage — ไม่ใช้ free tag, ไม่เพิ่มชั้น Page
- ยังไม่เพิ่ม `taggit` ในชั้นนี้ (เก็บไว้พิจารณาภายหลังสำหรับ subject tags)
- **identifier ใช้ `code` ชื่อเดียวทั่วระบบ** (เลิก siglum/work_key/book_code) · unique ภายใต้ parent · reference = composite
- **`slug` default = slugify(code)** สำหรับ catalog pages (หน้าเว็บทั่วไปคง slug จาก title)
- `edition_role` แยกจาก `code` (code = URL/สื่อ user · role = logic)
- **scan path เป็น hierarchical** `archive/{collection.code}/{edition.code}/{volume.code}/{sequence}.jpg` (แก้ convention เดิม — ต้องอัปเดต `development_guide.md`)
- publisher/place_of_publication/published_year/print_number/isbn_number = **Edition (default) + Volume (override)** · ชื่อ field ครั้งที่พิมพ์ = `print_number`

### ยังเปิด (จัดทำเมื่อเริ่ม import จริง)

- schema `cref` ละเอียดต่อปิฏก/นิกาย (ภาคผนวกแยก)
- ตาราง Master TOC แบบเต็ม (cross-edition mapping ขั้นสูง) — เริ่มจาก `cref` ก่อน
- รายละเอียด workflow four-eyes/lock (สืบจาก sacred-app)
- การรองรับ IIIF เต็มรูปแบบ

---

## 12. ขั้นตอน implement (ลำดับแนะนำ)

1. `snippets/` — เพิ่ม snippet `CanonicalSection` (tree) + ลงทะเบียน admin
2. `website/models.py` — เพิ่ม 4 page types + `parent_page_types`/`subpage_types`
3. `archive/models.py` — `ScanFolio`, `Segment`, `SegmentRevision`, `ReferenceAlias`
4. RoutablePageMixin + view `/cite/...` + resolver `ReferenceAlias`
5. management command: import metadata → Page tree, import segment/scan, import alias
6. ลบ catalog snippets + `CatalogGroup`
7. Vue island (edition) + REST API ใน `archive/`

> หมายเหตุ: เอกสารนี้เป็น **design reference** — สอดคล้องกับ `development_guide.md` (§โครงสร้าง, §ภาพสแกน)
> และ `migrate_discussion.md` (§4 โมเดล/revision) เมื่อ implement ให้ยึดเอกสารนี้เป็นสเปกหลักของชั้น catalog/archive
