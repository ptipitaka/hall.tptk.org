# Data Model Design — Catalog (Pages) + Archive (Scan/Segment)

> **ประเภทเอกสาร:** Design Spec (ratified-pending) — ใช้เป็นจุดอ้างอิงสำหรับการ implement
> **สถานะ:** Draft สำหรับทบทวน · ออกแบบ field พร้อมระบุ **บังคับ/ไม่บังคับ**
> **อัปเดตล่าสุด:** 2026-09-04 (Scan folios ใน Digital archive: กรอง Collection → Edition → Book, จำค่ากรอง, กระโดดเลขหน้า, เปิดภาพสแกนหรือแจ้งว่าไม่มี)
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
| `scan_folio_count` | PositiveIntegerField | – | จำนวนหน้าสแกนที่ประกาศของเล่ม · บันทึกที่ locale หลัก · `generate_scan_folios` สร้างแถว `1..N` จากค่านี้ |
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
| `volume` | FK → VolumePage | ✓ | หน้าเล่ม **locale หลัก** เท่านั้น — หนึ่งภาพหนึ่งแถว หน้าแปลอ่านชุดเดียวกัน |
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
- จำนวนหน้าประกาศที่ `VolumePage.scan_folio_count` แล้ว `generate_scan_folios` สร้างแถว `1..N` — ไม่ใช้การไล่ไฟล์ CDN เป็นทางสร้างรายการ
- หน้าเล่มทุก locale ใช้ `scan_folios_for(volume)` ไม่กรอง `volume=self` ตรง ๆ

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

> มติ (ล็อก 2026-09-03): **ไม่มีระบบหน่วยอ้างอิงข้ามฉบับ (`cref`)** แล้ว
> และ **ไม่มี `text` สตริงเดียว** — เนื้อหาเป็น payload ตามรูป extract
> (`text[]` หลายอักษร + `runs`, `bats`, `notes`, `symbol_notes`, …)
> โมเดลออกแบบให้รับไฟล์ถอดจริง (`books/cs-roman/output/*.segments.json`) ได้ตรง ๆ

### 5.1 Segment — หนึ่งแถวต่อหนึ่งหน่วยของไฟล์ถอด

หนึ่งแถว = **หนึ่งหน่วยบนหน้าพิมพ์หนึ่งหน้า** (ตรง `segment` ใน `*.segments.json`)
ย่อหน้าที่ไหลไปหน้าถัดไปเป็นแถว `prose_continuation` คนละแถว — ไม่มี `folio_end` คร่อมหน้า

| field | ชนิด | บังคับ | หมายเหตุ |
| --- | --- | :---: | --- |
| `volume` | FK → VolumePage | ✓ | ขอบเขตหลัก (PROTECT); ผูกเล่ม locale หลักเหมือน `ScanFolio` |
| `folio` | FK → ScanFolio | – | ภาพสแกนที่หน่วยนี้อยู่ ว่างได้ตอน draft import |
| `order` | IntegerField | ✓ | ลำดับอ่านในเล่ม **unique** (`UniqueConstraint(volume, order)`) — ตรง `order` ของ extract |
| `kind` | FK → SegmentKind | ✓ | `code` ตรง `segment_type` ของ extract 1:1 (§5.3) |
| `item` | IntegerField (index) | – | เลขข้อฉบับพิมพ์ (Tipiṭaka `item`) ว่างสำหรับ heading/gāthā |
| `section_no` | IntegerField | – | เลขโครงหัวข้อที่พิมพ์ (เช่น `1` ใน `1. Pārājikakaṇḍa`) — คนละชั้นกับ `item` |
| `content` | JSONField (default `{}`) | – | **ต้นฉบับ** — payload รูป extract: `text[]`, `bats`, `hanging_lines`, `notes`, `symbol_notes`, `flags`, `heading_kind`, `in_toc`, `source_layout`, `closer_level`, `needs_review`, `review_reasons` |
| `plain_roman` | TextField | – | โรมันแบนสำหรับค้น/ลิสต์ — สร้างจาก `content` **ไม่ใช่ต้นฉบับ** |
| `plain_thai` | TextField | – | ไทยแบนสำหรับค้น/ลิสต์ — สร้างจาก `content` **ไม่ใช่ต้นฉบับ** |
| `region` | JSONField | – | bbox normalized `{x,y,w,h}` (0–1) ผูกกับ segment นี้ — ออกแบบการใช้งานภายหลัง |
| `status` | CharField choices | ✓ (default `draft`) | `draft` / `review` / `published` |
| `created_at` / `updated_at` | DateTimeField | ✓ (auto) | housekeeping |

> **ไม่มี** `cref` / `cref_end` / `structural_ref` / `parent` / `folio_end` /
> `citation_key` / `source_note` / `region_note` ในโมเดลนี้แล้ว (ถอดออกตามมติ)
> `structural_ref` แยกเป็น `item` + `section_no` ที่เป็นคอลัมน์ชัด
> อัตลักษณ์หน่วยในเล่มคือ `order` (ใช้กับ `?seg={order}` บนหน้า folio)

**Constraints / Index**

- `UniqueConstraint(volume, order)` — อัตลักษณ์เดียวกับ extract
- index `(volume, order)`, index `item`, index `kind`
- ไม่มี index `cref` แล้ว (ไม่มีระบบ cref)

**หัวใจการทำงาน**

- `content` เป็นที่เก็บต้นฉบับรูป extract — ฟอร์มเจ้าหน้าที่ (เมนู Digital archive ที่จะสร้าง) แก้โครงนี้ทีละหน้า
- `plain_roman` / `plain_thai` คือข้อความแบนสำหรับค้น/ลิสต์เท่านั้น ไม่ใช่แหล่งความจริง
- `region` ผูก bbox กับ segment นี้ — การใช้งานบน viewer ออกแบบภายหลัง
- `folio` + `region` บังคับเมื่อจะเลื่อนเป็น `review`/`published` (`clean()`) — draft จาก import ว่างได้

### 5.2 SegmentRevision — snapshot ทั้ง payload

ประวัติแยกจาก Wagtail (segment มี workflow เฉพาะ — รองรับ four-eyes ตาม `migrate_discussion.md`)

| field | ชนิด | บังคับ | หมายเหตุ |
| --- | --- | :---: | --- |
| `segment` | FK → Segment | ✓ | (CASCADE) |
| `content` | JSONField | – | snapshot payload (ตาม segment) |
| `kind` | FK → SegmentKind | ✓ | snapshot |
| `item` | IntegerField | – | snapshot |
| `section_no` | IntegerField | – | snapshot |
| `region` | JSONField | – | snapshot |
| `status` | CharField choices | ✓ (default `draft`) | snapshot |
| `created_by` | FK → User | – | ผู้แก้ |
| `created_at` | DateTimeField | ✓ (auto) | |
| `change_note` | CharField | – | สรุปการแก้ |
| `is_current` | BooleanField | ✓ (default False) | รุ่นที่ใช้แสดง |

> revision ของ **metadata เล่ม/ฉบับ** ใช้ Wagtail Page revision; revision ของ **ข้อความ segment** ใช้ตารางนี้ — แยกชั้นชัดเจน
> snapshot ทั้ง `content` + คอลัมน์สาระ ไม่ใช่แค่ `text` เดิม

### 5.3 SegmentKind — `code` ตรง `segment_type` ของ extract

`snippets.SegmentKind.code` ตั้งให้ตรงกับ `segment_type` ของ extract 1:1
(ดู `books/cs-roman/SCHEMA.md` "segment_type vocabulary") เพื่อ import แมปตรง:

| `code` | หมายเหตุ |
| --- | --- |
| `piṭaka` / `gambhīra` / `namakkāraṃ` / `chapter` / `title` / `niṭṭhitaṃ` / `tassuddānaṃ` | โครงสร้าง |
| `prose` / `prose_continuation` | ข้อความร้อย |
| `gatha` / `gatha_continuation` | คาถา |
| `note` | เชิงอรรถลอย |

> `heading_kind` (nik/boo/cha/h1…h6) และ `source_layout` (center/bat_line/wak_line/hanging)
> **ไม่ใช่ kind** — อยู่ใน `content` ของ segment ไม่ใช่ `SegmentKind`
> seed เดิมที่มี `centered` / `prose-indented` / `prose-plain` เป็น kind ถอดออกแล้ว

---

## 6. URL อ้างอิงถาวร (Citation URLs)

> มติ (ล็อก 2026-09-03): **ไม่มีระบบ `cref` ข้ามฉบับและ `/cite/` route แล้ว**
> `archive.ReferenceAlias` และ view/url/template ของ cite ถูกถอดออก

URL ที่เหลือสำหรับอ้างอิงคือ **folio viewer ใต้ Volume** (RoutablePageMixin):

| ประเภท | รูปแบบ | ทำหน้าที่ |
| --- | --- | --- |
| Folio viewer | `/{volume-path}/f/{sequence}/` | เปิด viewer ที่หน้านั้น |
| Segment ในหน้า | `/{volume-path}/f/{sequence}/?seg={order}` | เลื่อนไป segment ตาม `order` |

- อัตลักษณ์ segment คือ `order` ในเล่ม (unique) — ไม่มี `citation_key` แยก
- ไม่มี `/cite/{cref}/` หรือ `/cite/{scheme}:{value}/` อีก
- หากภายหลังต้องการอ้างอิงข้ามฉบับ จะออกแบบเป็นชั้นใหม่ ไม่ใช่ `cref` บน `Segment`

---

## 7. (ถอดออก — Canonical Reference System)

> ระบบ `cref` / `ReferenceAlias` และการเทียบเคียงข้ามฉบับที่ขับด้วย `cref`
> ถูกถอดออกตามมติ 2026-09-03 ส่วนนี้เก็บไว้เป็นประวัติเท่านั้น
> หากจะกลับมาทำอ้างอิงข้ามฉบับ ให้ออกแบบเป็นชั้นแยกใหม่ ไม่ใช่คอลัมน์บน `Segment`

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
| Segment | หลายแสน/Edition | pagination ในหน้า list ของ Wagtail admin · ไม่โหลดทั้งเล่มครั้งเดียว · index `(volume, order)` / `item` / `kind` |

**กฎเหล็ก:** ห้าม `InlinePanel` ScanFolio/Segment บน VolumePage — หน้า Page explorer จะต้องไม่โหลด
หลักหมื่น–แสนแถว แก้ผ่าน **เมนู Digital archive ใน Wagtail admin** เท่านั้น (standalone list + filter +
paginate, รายละเอียดใน §10) Wagtail admin ใช้ metadata (Collection/Edition/Volume) และ trigger import ตามปกติ

---

## 10. การทำงานคู่ ScanFolio ↔ Segment (transcription)

> มติ (ล็อก 2026-09-03): เจ้าหน้าที่ทำงานผ่าน **Wagtail admin (เมนู "Digital archive")**
> ไม่ใช้ Vue island + REST API ดังที่เคยร่างไว้ การเปลี่ยนนี้อยู่ในระดับข้อกำหนดทางเทคนิค (§๑๒ นโยบาย)
> ไม่ขัดนโยบาย/ยุทธศาสตร์ — ยุทธศาสตร์ §๕.๔ และแผนงานระยะ ๕ กำหนดให้ต้องมีเครื่องมือเจ้าหน้าที่
> สำหรับรับเข้า/ตรวจทานอยู่แล้ว

```
Wagtail admin → เมนู "Digital archive" (SnippetViewSetGroup, archive/wagtail_hooks.py)
   ├── Scan folios (ScanFolio)        list + paginate
   │     · กรองแบบ cascade: Collection → Edition → Book (VolumePage) · จำค่ากรองใน session
   │     · ยังไม่แสดงรายการจนกว่าจะเลือก Book — เลือกชั้นแม่แล้วโหลดตัวเลือกชั้นลูกทันที (options JSON)
   │     · เรียงตามเลขหน้า (sequence) น้อย→มากเป็นค่าเริ่มต้น หรือมาก→น้อย
   │     · ระบุเลขหน้า (page_no หรือ sequence) เพื่อกระโดดไปแถวนั้นโดยตรง
   │     · คลิก folio → หน้า inspect: มีภาพเมื่อ status=present · ไม่มีแล้วบอกว่าไม่มี
   │     · สร้างแถวด้วย management command (import/generate) ไม่ใช่มือ
   └── Segments (รอบถัดไป)           list + filter (volume/kind/status) + paginate
         · แก้ content (payload extract) + kind + item + section_no
         · folio + region บังคับก่อนเลื่อนเป็น review/published (clean())
         · ทุก save สร้าง SegmentRevision (audit / four-eyes)
```

- ผู้บันทึกคลิก folio ในรายการแล้วเปิดภาพสแกน (หรือข้อความว่าไม่มีภาพ) — เครื่องมือถอด Segment ต่อภาพจะตามมาในรอบถัดไป
- ระบบ region viewer (bbox) ยังเป็นแบบออกแบบไว้ (`region` field มีอยู่) จะเชื่อมเข้า admin ภายหลัง
- ไม่มี Vue island และไม่มี REST API สาธารณะใน `archive/` (เอา `/cite/` ออกแล้วใน §๖)

---

## 11. สรุปการตัดสินใจ (locked) และที่ยังเปิด

### ตัดสินใจแล้ว

- Collection = **พระไตรปิฎกทั้งชุด** (Work) · Edition = ภาษา/อักษร · Volume = **Page**
- ภาษา/อักษรอยู่ที่ **Edition เท่านั้น** — Collection ไม่มี `content_languages`
- ScanFolio = model + path (ไม่ใช่ Image/Page) · ScanFolioPage = ไม่ทำ
- URL folio ผ่าน RoutablePageMixin (`/{volume-path}/f/{sequence}/`) — ไม่มี `/cite/` route และไม่มี `cref` (ถอดออกตามมติ 2026-09-03, ดู §๖–§๗)
- Segment + SegmentRevision ใน `archive/` · **region บังคับก่อน publish**
- เครื่องมือเจ้าหน้าที่ = **Wagtail admin (เมนู "Digital archive")** ไม่ใช่ Vue island (มติ 2026-09-03, ดู §๙–§๑๐)
- มี `CatalogIndexPage`
- ปิฏก/นิกาย = snippet `CanonicalSection` (controlled vocabulary แบบ tree) FK จาก VolumePage — ไม่ใช้ free tag, ไม่เพิ่มชั้น Page
- ยังไม่เพิ่ม `taggit` ในชั้นนี้ (เก็บไว้พิจารณาภายหลังสำหรับ subject tags)
- **identifier ใช้ `code` ชื่อเดียวทั่วระบบ** (เลิก siglum/work_key/book_code) · unique ภายใต้ parent · reference = composite
- **`slug` default = slugify(code)** สำหรับ catalog pages (หน้าเว็บทั่วไปคง slug จาก title)
- `edition_role` แยกจาก `code` (code = URL/สื่อ user · role = logic)
- **scan path เป็น hierarchical** `archive/{collection.code}/{edition.code}/{volume.code}/{sequence}.jpg` (แก้ convention เดิม — ต้องอัปเดต `development_guide.md`)
- publisher/place_of_publication/published_year/print_number/isbn_number = **Edition (default) + Volume (override)** · ชื่อ field ครั้งที่พิมพ์ = `print_number`

### ยังเปิด (จัดทำเมื่อเริ่ม import จริง)

- ระบบอ้างอิงข้ามฉบับ — หากจะทำ ออกแบบเป็นชั้นใหม่ ไม่ใช่ `cref` บน `Segment` (ดู §๗)
- ตาราง Master TOC แบบเต็ม (cross-edition mapping ขั้นสูง)
- รายละเอียด workflow four-eyes/lock (สืบจาก sacred-app)
- region viewer (bbox) บนหน้า edit Segment ใน Wagtail admin
- การรองรับ IIIF เต็มรูปแบบ

---

## 12. ขั้นตอน implement (ลำดับแนะนำ)

1. `snippets/` — เพิ่ม snippet `CanonicalSection` (tree) + ลงทะเบียน admin
2. `website/models.py` — เพิ่ม 4 page types + `parent_page_types`/`subpage_types`
3. `archive/models.py` — `ScanFolio`, `Segment`, `SegmentRevision`, `ReferenceAlias`
4. RoutablePageMixin + view `/cite/...` + resolver `ReferenceAlias`
5. management command: import metadata → Page tree, import segment/scan, import alias
6. ลบ catalog snippets + `CatalogGroup`
7. Wagtail admin (เมนู "Digital archive" ใน `archive/wagtail_hooks.py`) สำหรับ ScanFolio/Segment

> หมายเหตุ: เอกสารนี้เป็น **design reference** — สอดคล้องกับ `development_guide.md` (§โครงสร้าง, §ภาพสแกน)
> และ `migrate_discussion.md` (§4 โมเดล/revision) เมื่อ implement ให้ยึดเอกสารนี้เป็นสเปกหลักของชั้น catalog/archive
