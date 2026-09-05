"""Seed reference catalog snippets (classifications, segment kinds)."""

from __future__ import annotations

from django.core.management.base import BaseCommand

from snippets.models import (
    CanonicalSection,
    Classification,
    ContentLanguage,
    ContentScript,
    Country,
    SegmentKind,
    Tradition,
)
from snippets.seed import create_translated_rows, seed_translation_key
from website.sacred_content_locales import LOCALE_CONTENT

CLASSIFICATION_SLUGS = {
    "TP": "tipitaka",
    "AK": "atthakatha",
    "TK": "tika",
    "AN": "annya",
}

# Segment kind ``code`` mirrors the extract pipeline ``segment_type`` 1:1
# (see books/cs-roman/SCHEMA.md "segment_type vocabulary"). The extract uses
# Pali diacritics in `segment_type`; we keep them in `code` so import maps
# directly, and store the ASCII slug in `slug`.
SEGMENT_KINDS = (
    {
        "code": "piṭaka",
        "slug": "pitaka",
        "names": {"en": "Piṭaka", "th": "ปิฏก"},
    },
    {
        "code": "gambhīra",
        "slug": "gambhira",
        "names": {"en": "Gambhīra (book)", "th": "คัมภีร์"},
    },
    {
        "code": "namakkāraṃ",
        "slug": "namakkaram",
        "names": {"en": "Namakkāraṃ", "th": "นมการ"},
    },
    {
        "code": "chapter",
        "slug": "chapter",
        "names": {"en": "Chapter", "th": "บท"},
    },
    {
        "code": "title",
        "slug": "title",
        "names": {"en": "Title", "th": "ชื่อเรื่อง"},
    },
    {
        "code": "niṭṭhitaṃ",
        "slug": "nitthitam",
        "names": {"en": "Niṭṭhitaṃ", "th": "นิฏฺฐิตํ"},
    },
    {
        "code": "tassuddānaṃ",
        "slug": "tassuddanam",
        "names": {"en": "Tassuddānaṃ", "th": "ตัสสุทฺทานํ"},
    },
    {
        "code": "prose",
        "slug": "prose",
        "names": {"en": "Prose", "th": "ข้อความ"},
    },
    {
        "code": "prose_continuation",
        "slug": "prose-continuation",
        "names": {"en": "Prose continuation", "th": "ข้อความต่อเนื่อง"},
    },
    {
        "code": "gatha",
        "slug": "gatha",
        "names": {"en": "Gāthā", "th": "คาถา"},
    },
    {
        "code": "gatha_continuation",
        "slug": "gatha-continuation",
        "names": {"en": "Gāthā continuation", "th": "คาถาต่อเนื่อง"},
    },
    {
        "code": "note",
        "slug": "note",
        "names": {"en": "Note (orphan footnote)", "th": "เชิงอรรถลอย"},
    },
)

COUNTRIES = (
    {
        "code": "th",
        "slug": "thailand",
        "localized": {
            "en": {"name": "Thailand", "description": ""},
            "th": {"name": "ประเทศไทย", "description": ""},
        },
    },
    {
        "code": "mm",
        "slug": "myanmar",
        "localized": {
            "en": {"name": "Myanmar", "description": ""},
            "th": {"name": "เมียนมา", "description": ""},
        },
    },
    {
        "code": "lk",
        "slug": "sri-lanka",
        "localized": {
            "en": {"name": "Sri Lanka", "description": ""},
            "th": {"name": "ศรีลังกา", "description": ""},
        },
    },
    {
        "code": "in",
        "slug": "india",
        "localized": {
            "en": {"name": "India", "description": ""},
            "th": {"name": "อินเดีย", "description": ""},
        },
    },
    {
        "code": "kh",
        "slug": "cambodia",
        "localized": {
            "en": {"name": "Cambodia", "description": ""},
            "th": {"name": "กัมพูชา", "description": ""},
        },
    },
    {
        "code": "la",
        "slug": "laos",
        "localized": {
            "en": {"name": "Laos", "description": ""},
            "th": {"name": "ลาว", "description": ""},
        },
    },
    {
        "code": "gb",
        "slug": "united-kingdom",
        "localized": {
            "en": {"name": "United Kingdom", "description": ""},
            "th": {"name": "สหราชอาณาจักร", "description": ""},
        },
    },
    {
        "code": "jp",
        "slug": "japan",
        "localized": {
            "en": {"name": "Japan", "description": ""},
            "th": {"name": "ญี่ปุ่น", "description": ""},
        },
    },
    {
        "code": "tw",
        "slug": "taiwan",
        "localized": {
            "en": {"name": "Taiwan", "description": ""},
            "th": {"name": "ไต้หวัน", "description": ""},
        },
    },
    {
        "code": "vn",
        "slug": "vietnam",
        "localized": {
            "en": {"name": "Vietnam", "description": ""},
            "th": {"name": "เวียดนาม", "description": ""},
        },
    },
    {
        "code": "cn",
        "slug": "china",
        "localized": {
            "en": {"name": "China", "description": ""},
            "th": {"name": "จีน", "description": ""},
        },
    },
    {
        "code": "tib",
        "slug": "tibet",
        "localized": {
            "en": {"name": "Tibet", "description": ""},
            "th": {"name": "ทิเบต", "description": ""},
        },
    },
)

TRADITIONS = (
    {
        "code": "theravada",
        "slug": "theravada",
        "localized": {
            "en": {
                "name": "Theravāda",
                "description": "Southern Buddhist tradition centred on the Pali canon.",
            },
            "th": {
                "name": "เถรวาท",
                "description": "นิกายพุทธศาสนาภาคใต้ มุ่งเน้นพระไตรปิฎกบาลี",
            },
        },
    },
    {
        "code": "mahayana",
        "slug": "mahayana",
        "localized": {
            "en": {
                "name": "Mahāyāna",
                "description": "Northern and East Asian Buddhist tradition of the Great Vehicle.",
            },
            "th": {
                "name": "มหายาน",
                "description": "นิกายพุทธศาสนามหายานในเอเชียเหนือและตะวันออก",
            },
        },
    },
    {
        "code": "vajrayana",
        "slug": "vajrayana",
        "localized": {
            "en": {
                "name": "Vajrayāna",
                "description": "Tantric Buddhist tradition of the Diamond Vehicle.",
            },
            "th": {
                "name": "วัชรยาน",
                "description": "นิกายพุทธศาสนาวัชรยานหรือตันตระ",
            },
        },
    },
)


def _empty_localized(names: dict[str, str]) -> dict[str, dict[str, str]]:
    return {
        locale: {"name": names[locale], "description": ""}
        for locale in ("en", "th")
    }


CONTENT_LANGUAGE_SPECS = (
    {"code": "pali", "slug": "pali", "names": {"en": "Pāli", "th": "บาลี"}},
    {"code": "thai", "slug": "thai", "names": {"en": "Thai", "th": "ไทย"}},
    {
        "code": "sinhala",
        "slug": "sinhala",
        "names": {"en": "Sinhala", "th": "สิงหล"},
    },
    {"code": "khmer", "slug": "khmer", "names": {"en": "Khmer", "th": "เขมร"}},
    {
        "code": "vietnamese",
        "slug": "vietnamese",
        "names": {"en": "Vietnamese", "th": "เวียดนาม"},
    },
    {
        "code": "japanese",
        "slug": "japanese",
        "names": {"en": "Japanese", "th": "ญี่ปุ่น"},
    },
    {"code": "english", "slug": "english", "names": {"en": "English", "th": "อังกฤษ"}},
    {"code": "chinese", "slug": "chinese", "names": {"en": "Chinese", "th": "จีน"}},
    {"code": "lanna", "slug": "lanna", "names": {"en": "Lanna", "th": "ล้านนา"}},
    {"code": "tibetan", "slug": "tibetan", "names": {"en": "Tibetan", "th": "ทิเบต"}},
    {
        "code": "myanmar",
        "slug": "myanmar",
        "names": {"en": "Myanmar", "th": "เมียนมา"},
    },
    {"code": "lao", "slug": "lao", "names": {"en": "Lao", "th": "ลาว"}},
)

# Tipiṭaka tree: piṭaka → nikāya (codes are cref building blocks).
CANONICAL_SECTION_SPECS = (
    {
        "code": "vin",
        "kind": CanonicalSection.Kind.PITAKA,
        "parent": None,
        "names": {"en": "Vinayapiṭaka", "th": "วินยปิฏก"},
    },
    {
        "code": "sut",
        "kind": CanonicalSection.Kind.PITAKA,
        "parent": None,
        "names": {"en": "Suttantapiṭaka", "th": "สุตฺตนฺตปิฏก"},
    },
    {
        "code": "dn",
        "kind": CanonicalSection.Kind.NIKAYA,
        "parent": "sut",
        "names": {"en": "Dīghanikāya", "th": "ทีฆนิกาย"},
    },
    {
        "code": "mn",
        "kind": CanonicalSection.Kind.NIKAYA,
        "parent": "sut",
        "names": {"en": "Majjhimanikāya", "th": "มชฺฌิมนิกาย"},
    },
    {
        "code": "sn",
        "kind": CanonicalSection.Kind.NIKAYA,
        "parent": "sut",
        "names": {"en": "Saṃyuttanikāya", "th": "สํยุตฺตนิกาย"},
    },
    {
        "code": "an",
        "kind": CanonicalSection.Kind.NIKAYA,
        "parent": "sut",
        "names": {"en": "Aṅguttaranikāya", "th": "องฺคุตฺตรนิกาย"},
    },
    {
        "code": "kn",
        "kind": CanonicalSection.Kind.NIKAYA,
        "parent": "sut",
        "names": {"en": "Khuddakanikāya", "th": "ขุทฺทกนิกาย"},
    },
    {
        "code": "abh",
        "kind": CanonicalSection.Kind.PITAKA,
        "parent": None,
        "names": {"en": "Abhidhammapiṭaka", "th": "อภิธมฺมปิฏก"},
    },
)

CONTENT_SCRIPT_SPECS = (
    {"code": "thai", "slug": "thai", "names": {"en": "Thai", "th": "ไทย"}},
    {
        "code": "sinhala",
        "slug": "sinhala",
        "names": {"en": "Sinhala", "th": "สิงหล"},
    },
    {
        "code": "myanmar",
        "slug": "myanmar",
        "names": {"en": "Myanmar", "th": "พม่า"},
    },
    {
        "code": "devanagari",
        "slug": "devanagari",
        "names": {"en": "Devanagari", "th": "เทวนาครี"},
    },
    {
        "code": "tai-yai",
        "slug": "tai-yai",
        "names": {"en": "Tai Yai", "th": "ไทใหญ่"},
    },
    {"code": "khmer", "slug": "khmer", "names": {"en": "Khmer", "th": "ขอม"}},
    {"code": "roman", "slug": "roman", "names": {"en": "Roman", "th": "โรมัน"}},
    {
        "code": "vietnamese",
        "slug": "vietnamese",
        "names": {"en": "Vietnamese", "th": "เวียดนาม"},
    },
    {
        "code": "lao-tham",
        "slug": "lao-tham",
        "names": {"en": "Lao Tham", "th": "ธัมม์ลาว"},
    },
    {
        "code": "lanna-tham",
        "slug": "lanna-tham",
        "names": {"en": "Lanna Tham", "th": "ธํมม์ล้านนา"},
    },
    {
        "code": "japanese",
        "slug": "japanese",
        "names": {"en": "Japanese", "th": "ญี่ปุ่น"},
    },
    {"code": "chinese", "slug": "chinese", "names": {"en": "Chinese", "th": "จีน"}},
    {"code": "tibetan", "slug": "tibetan", "names": {"en": "Tibetan", "th": "ทิเบต"}},
)


def _ordered_content_languages() -> list[dict]:
    pali = [spec for spec in CONTENT_LANGUAGE_SPECS if spec["code"] == "pali"]
    others = sorted(
        (spec for spec in CONTENT_LANGUAGE_SPECS if spec["code"] != "pali"),
        key=lambda spec: spec["names"]["en"].casefold(),
    )
    return pali + others


def _ordered_content_scripts() -> list[dict]:
    return sorted(CONTENT_SCRIPT_SPECS, key=lambda spec: spec["names"]["en"].casefold())


def seed_classifications() -> int:
    count = 0
    for entry in LOCALE_CONTENT["en"]["classification_entries"]:
        siglum = entry["siglum"]
        slug = CLASSIFICATION_SLUGS[siglum]
        localized = {}
        for language_code in LOCALE_CONTENT:
            match = next(
                item
                for item in LOCALE_CONTENT[language_code]["classification_entries"]
                if item["siglum"] == siglum
            )
            localized[language_code] = {
                "title": match["title"],
                "description": match["description"],
            }
        create_translated_rows(
            Classification,
            translation_key=seed_translation_key("classification", slug),
            shared={"siglum": siglum, "slug": slug, "sort_order": count},
            localized=localized,
        )
        count += 1
    return count


def seed_segment_kinds() -> int:
    for index, spec in enumerate(SEGMENT_KINDS):
        localized = {
            locale: {"name": spec["names"][locale], "description": "", "sort_order": index}
            for locale in ("en", "th")
        }
        create_translated_rows(
            SegmentKind,
            translation_key=seed_translation_key("segment-kind", spec["code"]),
            shared={"code": spec["code"], "slug": spec["slug"], "sort_order": index},
            localized=localized,
        )
    return len(SEGMENT_KINDS)


def seed_traditions() -> int:
    for index, spec in enumerate(TRADITIONS):
        localized = {
            code: {**values, "sort_order": index}
            for code, values in spec["localized"].items()
        }
        create_translated_rows(
            Tradition,
            translation_key=seed_translation_key("tradition", spec["code"]),
            shared={"code": spec["code"], "slug": spec["slug"], "sort_order": index},
            localized=localized,
        )
    return len(TRADITIONS)


def seed_countries() -> int:
    for index, spec in enumerate(COUNTRIES):
        localized = {
            code: {**values, "sort_order": index}
            for code, values in spec["localized"].items()
        }
        create_translated_rows(
            Country,
            translation_key=seed_translation_key("country", spec["code"]),
            shared={"code": spec["code"], "slug": spec["slug"], "sort_order": index},
            localized=localized,
        )
    return len(COUNTRIES)


def seed_content_languages() -> int:
    for index, spec in enumerate(_ordered_content_languages()):
        localized = {
            locale: {**values, "sort_order": index}
            for locale, values in _empty_localized(spec["names"]).items()
        }
        create_translated_rows(
            ContentLanguage,
            translation_key=seed_translation_key("content-language", spec["code"]),
            shared={"code": spec["code"], "slug": spec["slug"], "sort_order": index},
            localized=localized,
        )
    return len(CONTENT_LANGUAGE_SPECS)


def seed_content_scripts() -> int:
    for index, spec in enumerate(_ordered_content_scripts()):
        localized = {
            locale: {**values, "sort_order": index}
            for locale, values in _empty_localized(spec["names"]).items()
        }
        create_translated_rows(
            ContentScript,
            translation_key=seed_translation_key("content-script", spec["code"]),
            shared={"code": spec["code"], "slug": spec["slug"], "sort_order": index},
            localized=localized,
        )
    return len(CONTENT_SCRIPT_SPECS)


def seed_canonical_sections() -> int:
    """Seed piṭaka/nikāya tree; parents first so child FKs resolve per locale."""
    by_code: dict[str, dict[str, CanonicalSection]] = {}
    for index, spec in enumerate(CANONICAL_SECTION_SPECS):
        parent_code = spec["parent"]
        localized = {}
        for locale in ("en", "th"):
            parent = None
            if parent_code:
                parent = by_code[parent_code][locale]
            localized[locale] = {
                "name": spec["names"][locale],
                "description": "",
                "sort_order": index,
                "parent": parent,
            }
        rows = create_translated_rows(
            CanonicalSection,
            translation_key=seed_translation_key("canonical-section", spec["code"]),
            shared={
                "code": spec["code"],
                "slug": spec["code"],
                "kind": spec["kind"],
            },
            localized=localized,
        )
        by_code[spec["code"]] = rows
    return len(CANONICAL_SECTION_SPECS)


class Command(BaseCommand):
    help = (
        "Seed Classification, Tradition, Country, ContentLanguage, ContentScript, "
        "SegmentKind, and CanonicalSection reference snippets (en/th)."
    )

    def handle(self, *args, **options):
        classification_count = seed_classifications()
        tradition_count = seed_traditions()
        country_count = seed_countries()
        content_language_count = seed_content_languages()
        content_script_count = seed_content_scripts()
        segment_kind_count = seed_segment_kinds()
        canonical_section_count = seed_canonical_sections()
        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {classification_count} classification(s), "
                f"{tradition_count} tradition(s), "
                f"{country_count} countries, "
                f"{content_language_count} content language(s), "
                f"{content_script_count} content script(s), "
                f"{segment_kind_count} segment kind(s), and "
                f"{canonical_section_count} canonical section(s)."
            )
        )
