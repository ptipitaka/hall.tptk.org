"""
Tipiṭaka catalog tree data (Collections + Editions) from plan/tp-list.md
and tipitaka-catalog editionplate cover keys.
"""

from __future__ import annotations

# Cover keys map to website/data/covers/<key>.jpg (copied from tipitaka-catalog).

PUBLISHERS: dict[str, dict[str, str]] = {
    "mahamakut": {
        "en": "Mahamakut Buddhist University, Thailand",
        "th": "มหาวิทยาลัยมหามกุฏราชวิทยาลัย ประเทศไทย",
    },
    "mahachula": {
        "en": "Mahachulalongkornrajavidyalaya University, Thailand",
        "th": "มหาจุฬาลงกรณราชวิทยาลัย ประเทศไทย",
    },
    "sangha_onab": {
        "en": "Supreme Sangha Council / National Office of Buddhism, Thailand",
        "th": "มหาเถรสมาคม / สำนักงานพระพุทธศาสนาแห่งชาติ ประเทศไทย",
    },
    "wat_ram_poeng": {
        "en": "Wat Ram Poeng (Tapodaram), Chiang Mai, Thailand",
        "th": "วัดร่ำเปิง (ตโปทาราม) จ.เชียงใหม่ ประเทศไทย",
    },
    "dhammabhakdi": {
        "en": "S. Dhammabhakdi Publishing, Thailand",
        "th": "สำนักงาน ลูก ส. ธรรมภักดี ประเทศไทย",
    },
    "sri_lanka_gov": {
        "en": "Government of Sri Lanka",
        "th": "ศูนย์วัฒนธรรมชาวพุทธ ประเทศลังกา",
    },
    "myanmar_dora": {
        "en": "Department of Religious Affairs, Myanmar",
        "th": "กรมการศาสนา ประเทศเมียนมา",
    },
    "buddhasasana_society_mm": {
        "en": "Buddhasāsana Society, Myanmar",
        "th": "สมาคมพุทธศาสนา ประเทศเมียนมา",
    },
    "cbbef": {
        "en": "Corporate Body of the Buddha Educational Foundation, Taiwan",
        "th": "มูลนิธิการศึกษาพระพุทธศาสนาประเทศไต้หวัน",
    },
    "nalanda": {
        "en": "Nav Nalanda Mahavihara, India",
        "th": "สถาบันนวนาลันทามหาวิหาร ประเทศอินเดีย",
    },
    "buddhist_institute_kh": {
        "en": "Buddhist Institute, Cambodia",
        "th": "สถาบันพุทธศาสนบัณฑิตย์ ประเทศกัมพูชา",
    },
    "lao_buddhist": {
        "en": "Lao Buddhist Fellowship Organization, Laos",
        "th": "องค์การพุทธศาสนาสัมพันธ์ลาว ประเทศลาว",
    },
    "pts": {
        "en": "Pali Text Society, United Kingdom",
        "th": "สมาคมปาลีปกรณ์ สหราชอาณาจักร",
    },
    "daizo": {
        "en": "Daizō Shuppan, Japan",
        "th": "大蔵出版 (Daizō Shuppan) ประเทศญี่ปุ่น",
    },
    "yuanheng": {
        "en": "Yuanheng Temple (元亨寺), Taiwan",
        "th": "วัดหยวนเหิง (元亨寺) ไต้หวัน",
    },
    "vietnam_bri": {
        "en": "Vietnam Buddhist Research Institute",
        "th": "สถาบันวิจัยพุทธศาสน์แห่งเวียดนาม ประเทศเวียดนาม",
    },
    "tai_sangha": {
        "en": "Sangha Association for Tai Tipitaka Translation, Panglong, Myanmar",
        "th": "คณะสงฆ์เพื่อการแปลพระไตรปิฎกไต ประเทศเมียนมา",
    },
    "china_bookstore": {
        "en": "China Bookstore (中国书店), China",
        "th": "China Bookstore (中国书店 · จงกั๋ว ชูเตี้ยน) ประเทศจีน",
    },
    "palace_museum": {
        "en": "Palace Museum Press, China",
        "th": "สำนักพิมพ์พระราชวังต้องห้าม ประเทศจีน",
    },
}

# Place-of-publication labels (edition may set "place" key, else country default).
PLACES: dict[str, dict[str, str]] = {
    "bangkok": {
        "en": "Bangkok, Thailand",
        "th": "กรุงเทพฯ ประเทศไทย",
    },
    "chiang_mai": {
        "en": "Chiang Mai, Thailand",
        "th": "เชียงใหม่ ประเทศไทย",
    },
    "colombo": {
        "en": "Colombo, Sri Lanka",
        "th": "โคลัมโบ ประเทศศรีลังกา",
    },
    "yangon": {
        "en": "Yangon, Myanmar",
        "th": "ย่างกุ้ง ประเทศเมียนมา",
    },
    "panglong": {
        "en": "Panglong, Shan State, Myanmar",
        "th": "ปางโหลง รัฐฉาน ประเทศเมียนมา",
    },
    "taipei": {
        "en": "Taipei, Taiwan",
        "th": "ไทเป ไต้หวัน",
    },
    "kaohsiung": {
        "en": "Kaohsiung, Taiwan",
        "th": "เกาสง ไต้หวัน",
    },
    "nalanda": {
        "en": "Nalanda, Bihar, India",
        "th": "นาลันทา รัฐพิหาร ประเทศอินเดีย",
    },
    "phnom_penh": {
        "en": "Phnom Penh, Cambodia",
        "th": "พนมเปญ ประเทศกัมพูชา",
    },
    "vientiane": {
        "en": "Vientiane, Laos",
        "th": "เวียงจันทน์ ประเทศลาว",
    },
    "oxford": {
        "en": "Oxford, United Kingdom",
        "th": "ออกซ์ฟอร์ด สหราชอาณาจักร",
    },
    "tokyo": {
        "en": "Tokyo, Japan",
        "th": "โตเกียว ประเทศญี่ปุ่น",
    },
    "ho_chi_minh": {
        "en": "Ho Chi Minh City, Vietnam",
        "th": "นครโฮจิมินห์ ประเทศเวียดนาม",
    },
    "beijing": {
        "en": "Beijing, China",
        "th": "ปักกิ่ง ประเทศจีน",
    },
}

# Default place key by Collection.country code when edition has no "place".
COUNTRY_DEFAULT_PLACE: dict[str, str] = {
    "th": "bangkok",
    "lk": "colombo",
    "mm": "yangon",
    "tw": "taipei",
    "in": "nalanda",
    "kh": "phnom_penh",
    "la": "vientiane",
    "gb": "oxford",
    "jp": "tokyo",
    "vn": "ho_chi_minh",
    "cn": "beijing",
    "tib": "beijing",
}


def thai_digits(value: str | int) -> str:
    return "".join(
        "๐๑๒๓๔๕๖๗๘๙"[int(ch)] if ch.isdigit() else ch for ch in str(value)
    )


def localized_text(value, lang: str) -> str:
    if isinstance(value, dict):
        return (value.get(lang) or value.get("en") or "").strip()
    if value is None:
        return ""
    return str(value)


def edition_publication_fields(
    spec: dict, lang: str, *, country: str = ""
) -> dict[str, str]:
    """Resolve publisher / year / print / place for a UI locale."""
    publisher = localized_text(spec.get("publisher", ""), lang)
    place = localized_text(spec.get("place_of_publication", ""), lang)
    if not place:
        place_key = spec.get("place") or COUNTRY_DEFAULT_PLACE.get(country, "")
        place = localized_text(PLACES.get(place_key, ""), lang)
    year = localized_text(spec.get("published_year", ""), lang)
    print_number = localized_text(spec.get("print_number", ""), lang)
    if lang == "th":
        if year:
            year = thai_digits(year)
        if print_number:
            print_number = thai_digits(print_number)
    return {
        "publisher": publisher,
        "place_of_publication": place,
        "published_year": year,
        "print_number": print_number,
    }


COLLECTIONS: list[dict] = [
    {
        "code": "sy",
        "sort": 10,
        "tradition": "theravada",
        "country": "th",
        "cover": "mmr-pali",
        "title": {
            "en": "Syāmaraṭṭhassa tepiṭakaṃ",
            "th": "สยามรัฐเตปิฎกํ",
        },
        "body": {
            "en": (
                "The Syāmaraṭṭhassa tepiṭakaṃ is a 45-volume Pāli Tipiṭaka in Thai "
                "script. King Rama VII ordered its completion and printing in B.E. 2471 "
                "(1928), finishing the royal project begun under King Rama V."
            ),
            "th": (
                "สยามรัฐเตปิฎกํ เป็นพระไตรปิฎกภาษาบาลีอักษรไทย ๔๕ เล่ม "
                "พระบาทสมเด็จพระปกเกล้าเจ้าอยู่หัวทรงมีพระบรมราชโองการให้จัดพิมพ์ให้เสร็จในปี "
                "พ.ศ. ๒๔๗๑ สืบต่องานที่เริ่มในรัชกาลที่ ๕"
            ),
        },
        "editions": [
            {
                "code": "pali2538",
                "sort": 10,
                "cover": "mmr-pali",
                "role": "source",
                "languages": ["pali"],
                "scripts": ["thai"],
                "volume_set_count": 45,
                "publisher": PUBLISHERS["mahamakut"],
                "published_year": "2538",
                "print_number": "4",
                "title": {
                    "en": "Syāmaraṭṭhassa tepiṭakaṃ (4th printing)",
                    "th": "สฺยามรฏฺฐสฺส เตปิฏกํ (พิมพ์ครั้งที่ ๔)",
                },
                "description": {
                    "en": "Pāli Tipiṭaka in Thai script, 45 volumes; 4th printing, B.E. 2538.",
                    "th": "พระไตรปิฎกบาลีอักษรไทย ๔๕ เล่ม พิมพ์ครั้งที่ ๔ พ.ศ. ๒๕๓๘",
                },
            },
            {
                "code": "pali2556",
                "sort": 20,
                "cover": "mmr-pali",
                "role": "source",
                "languages": ["pali"],
                "scripts": ["thai"],
                "volume_set_count": 45,
                "publisher": PUBLISHERS["mahamakut"],
                "published_year": "2556",
                "print_number": "7",
                "title": {
                    "en": "Syāmaraṭṭhassa tepiṭakaṃ (7th printing)",
                    "th": "สฺยามรฏฺฐสฺส เตปิฏกํ (พิมพ์ครั้งที่ ๗)",
                },
                "description": {
                    "en": "Pāli Tipiṭaka in Thai script, 45 volumes; 7th printing, B.E. 2556.",
                    "th": "พระไตรปิฎกบาลีอักษรไทย ๔๕ เล่ม พิมพ์ครั้งที่ ๗ พ.ศ. ๒๕๕๖",
                },
            },
            {
                "code": "pali2560",
                "sort": 30,
                "cover": "mmr-pali",
                "role": "source",
                "languages": ["pali"],
                "scripts": ["thai"],
                "volume_set_count": 45,
                "publisher": PUBLISHERS["mahamakut"],
                "published_year": "2560",
                "print_number": "8",
                "title": {
                    "en": "Syāmaraṭṭhassa tepiṭakaṃ (8th printing)",
                    "th": "สฺยามรฏฺฐสฺส เตปิฏกํ (พิมพ์ครั้งที่ ๘)",
                },
                "description": {
                    "en": "Pāli Tipiṭaka in Thai script, 45 volumes; 8th printing, B.E. 2560.",
                    "th": "พระไตรปิฎกบาลีอักษรไทย ๔๕ เล่ม พิมพ์ครั้งที่ ๘ พ.ศ. ๒๕๖๐",
                },
            },
            {
                "code": "th2525",
                "sort": 40,
                "cover": "mmr-attha-91",
                "role": "translation",
                "languages": ["thai"],
                "scripts": ["thai"],
                "volume_set_count": 91,
                "publisher": PUBLISHERS["mahamakut"],
                "published_year": "2525",
                "print_number": "1",
                "title": {
                    "en": "Tipiṭaka & Commentaries (Chakri bicentenary, B.E. 2525)",
                    "th": "พระไตรปิฎกและอรรถกถาภาษาไทย (ครบ ๒๐๐ ปี ราชวงศ์จักรี)",
                },
                "description": {
                    "en": (
                        "Thai Tipiṭaka with commentaries, 91 volumes; Chakri bicentenary set "
                        "(B.E. 2525)."
                    ),
                    "th": "ชุด ๙๑ เล่มเนื่องในวโรกาสครบ ๒๐๐ ปีแห่งราชวงศ์จักรี พ.ศ. ๒๕๒๕",
                },
            },
            {
                "code": "th2552",
                "sort": 50,
                "cover": "mmr-attha-91",
                "role": "translation",
                "languages": ["thai"],
                "scripts": ["thai"],
                "volume_set_count": 91,
                "publisher": PUBLISHERS["mahamakut"],
                "published_year": "2552",
                "print_number": "3",
                "title": {
                    "en": "Tipiṭaka & Commentaries (3rd printing, B.E. 2552)",
                    "th": "พระไตรปิฎกและอรรถกถาภาษาไทย (พิมพ์ครั้งที่ ๓ พ.ศ. ๒๕๕๒)",
                },
                "description": {
                    "en": "Thai Tipiṭaka with commentaries, 91 volumes; 3rd printing, B.E. 2552.",
                    "th": "พระไตรปิฎกและอรรถกถาแปลไทย ๙๑ เล่ม พิมพ์ครั้งที่ ๓ พ.ศ. ๒๕๕๒",
                },
            },
            {
                "code": "th2559",
                "sort": 60,
                "cover": "mmr-thai",
                "role": "translation",
                "source_edition": "pali2560",
                "languages": ["thai"],
                "scripts": ["thai"],
                "volume_set_count": 45,
                "publisher": PUBLISHERS["mahamakut"],
                "published_year": "2559",
                "print_number": "1",
                "title": {
                    "en": "Thai Tipiṭaka: Siamratth Edition",
                    "th": "พระไตรปิฎกภาษาไทย ฉบับสยามรัฐ",
                },
                "description": {
                    "en": (
                        "Thai translation of the Syāmaraṭṭha Pāli Tipiṭaka, 45 volumes (B.E. "
                        "2559)."
                    ),
                    "th": "ฉบับแปลไทยจากสฺยามรฏฺฐสฺส เตปิฏกํ ๔๕ เล่ม พ.ศ. ๒๕๕๙",
                },
            },
        ],
    },
    {
        "code": "mc",
        "sort": 20,
        "tradition": "theravada",
        "country": "th",
        "cover": "mch-pali",
        "title": {
            "en": "Mahācuḷātepiṭakaṃ",
            "th": "มหาจุฬาเตปิฎกํ",
        },
        "body": {
            "en": (
                "The Mahācuḷātepiṭakaṃ of Mahachulalongkornrajavidyalaya University (B.E. "
                "2506) is a 45-volume Pāli Tipiṭaka in Thai script, prepared in honour of "
                "King Rama V, with cross-references to major parallel editions."
            ),
            "th": (
                "มหาจุฬาเตปิฎกํ ของมหาจุฬาลงกรณราชวิทยาลัย (พ.ศ. ๒๕๐๖) "
                "เป็นพระไตรปิฎกบาลีอักษรไทย ๔๕ เล่ม เพื่อเฉลิมพระเกียรติรัชกาลที่ ๕ "
                "มีการอ้างอิงข้ามฉบับสยามรัฐ ฉัฏฐสังคีติ พุทธชยันตี และ PTS"
            ),
        },
        "editions": [
            {
                "code": "pali2506",
                "sort": 10,
                "cover": "mch-pali",
                "role": "source",
                "languages": ["pali"],
                "scripts": ["thai"],
                "volume_set_count": 45,
                "publisher": PUBLISHERS["mahachula"],
                "published_year": "2506",
                "print_number": "1",
                "title": {
                    "en": "Mahācuḷātepiṭakaṃ",
                    "th": "มหาจุฬาเตปิฏกํ",
                },
                "description": {
                    "en": "Pāli Tipiṭaka in Thai script, 45 volumes (1st printing, B.E. 2506).",
                    "th": "พระไตรปิฎกบาลีอักษรไทย ๔๕ เล่ม พิมพ์ครั้งที่ ๑ พ.ศ. ๒๕๐๖",
                },
            },
            {
                "code": "th2539",
                "sort": 20,
                "cover": "mch-thai",
                "role": "translation",
                "source_edition": "pali2506",
                "languages": ["thai"],
                "scripts": ["thai"],
                "volume_set_count": 45,
                "publisher": PUBLISHERS["mahachula"],
                "published_year": "2539",
                "print_number": "1",
                "title": {
                    "en": "Thai Tipiṭaka: MCU Edition",
                    "th": "พระไตรปิฏกภาษาไทย ฉบับมหาจุฬาลงกรณราชวิทยาลัย",
                },
                "description": {
                    "en": "Thai translation of the Mahācuḷātepiṭakaṃ, 45 volumes (B.E. 2539).",
                    "th": "ฉบับแปลไทยจากมหาจุฬาเตปิฏกํ ๔๕ เล่ม พ.ศ. ๒๕๓๙",
                },
            },
        ],
    },
    {
        "code": "dr",
        "sort": 30,
        "tradition": "theravada",
        "country": "th",
        "cover": "dr-pali",
        "title": {
            "en": "Dayyaraṭṭhassa tepiṭakaṃ",
            "th": "ทยฺยรฏฺฐสฺส เตปิฏกํ",
        },
        "body": {
            "en": (
                "The Dayyaraṭṭhassa tepiṭakaṃ is the Thai State Pāli Tipiṭaka in Thai "
                "script (45 volumes, B.E. 2549), issued under the Supreme Sangha Council "
                "and the National Office of Buddhism, with a companion Thai translation "
                "(Royal Jubilee)."
            ),
            "th": (
                "ทยฺยรฏฺฐสฺส เตปิฏกํ เป็นพระไตรปิฎกบาลีอักษรไทยฉบับสังคายนา "
                "ในพระบรมราชูปถัมภ์ ๔๕ เล่ม (พ.ศ. ๒๕๔๙) ของมหาเถรสมาคม "
                "และสำนักงานพระพุทธศาสนาแห่งชาติ พร้อมฉบับแปลไทยเฉลิมพระเกียรติ"
            ),
        },
        "editions": [
            {
                "code": "pali2549",
                "sort": 10,
                "cover": "dr-pali",
                "role": "source",
                "languages": ["pali"],
                "scripts": ["thai"],
                "volume_set_count": 45,
                "publisher": PUBLISHERS["sangha_onab"],
                "published_year": "2549",
                "print_number": "1",
                "title": {
                    "en": "Dayyaraṭṭhassa tepiṭakaṃ",
                    "th": "ทยฺยรฏฺฐสฺส เตปิฏกํ",
                },
                "description": {
                    "en": "Thai State Pāli Tipiṭaka in Thai script, 45 volumes (B.E. 2549).",
                    "th": "พระไตรปิฎกบาลีอักษรไทยฉบับรัฐ ๔๕ เล่ม พ.ศ. ๒๕๔๙",
                },
            },
            {
                "code": "th2549",
                "sort": 20,
                "cover": "dr-thai",
                "role": "translation",
                "source_edition": "pali2549",
                "languages": ["thai"],
                "scripts": ["thai"],
                "volume_set_count": 45,
                "publisher": PUBLISHERS["sangha_onab"],
                "published_year": "2549",
                "print_number": "1",
                "title": {
                    "en": "Thai Tipiṭaka: Royal Jubilee Edition",
                    "th": "พระไตรปิฎกภาษาไทย ฉบับเฉลิมพระเกียรติ ฯ",
                },
                "description": {
                    "en": (
                        "Thai translation honouring King Bhumibol Adulyadej, 45 volumes (B.E. "
                        "2549)."
                    ),
                    "th": "ฉบับแปลไทยเฉลิมพระเกียรติพระบาทสมเด็จพระเจ้าอยู่หัว ๔๕ เล่ม พ.ศ. ๒๕๔๙",
                },
            },
        ],
    },
    {
        "code": "lan",
        "sort": 40,
        "tradition": "theravada",
        "country": "th",
        "cover": "lan",
        "title": {
            "en": "Lanna Tipiṭaka (Wat Ram Poeng)",
            "th": "พระไตรปิฎกภาษาล้านนา ฉบับวัดร่ำเปิง",
        },
        "body": {
            "en": (
                "An 80-volume Lanna-script Tipiṭaka from Wat Ram Poeng (Tapodārāma), "
                "Chiang Mai, preserving Northern Thai manuscript tradition linked to the "
                "Lanna councils."
            ),
            "th": (
                "พระไตรปิฎกอักษรล้านนา ๘๐ เล่ม จากวัดร่ำเปิง (ตโปทาราม) จ.เชียงใหม่ "
                "อนุรักษ์ประเพณีคัมภีร์ล้านนาจากสายสังคายนาในอดีต"
            ),
        },
        "editions": [
            {
                "code": "lanna2556",
                "former_codes": ["lanna"],
                "sort": 10,
                "cover": "lan",
                "role": "translation",
                "languages": ["lanna"],
                "scripts": ["lanna-tham"],
                "volume_set_count": 80,
                "publisher": PUBLISHERS["wat_ram_poeng"],
                "place": "chiang_mai",
                "published_year": "2556",
                "print_number": "2",
                "title": {
                    "en": "Lanna Tipiṭaka: Wat Ram Poeng",
                    "th": "พระไตรปิฎกภาษาล้านนา ฉบับวัดร่ำเปิง",
                },
                "description": {
                    "en": (
                        "Lanna Tipiṭaka in Lanna Tham script, 80 volumes (2nd printing, B.E. "
                        "2556)."
                    ),
                    "th": "พระไตรปิฎกอักษรธัมม์ล้านนา ๘๐ เล่ม พิมพ์ครั้งที่ ๒ พ.ศ. ๒๕๕๖",
                },
            },
        ],
    },
    {
        "code": "sdb",
        "sort": 50,
        "tradition": "theravada",
        "country": "th",
        "cover": "sdb",
        "title": {
            "en": "Maha-Vitthara-Naya Tipiṭaka (5,000 sections)",
            "th": "พระไตรปิฎกภาษาไทย ฉบับมหาวิตถารนัย ๕๐๐๐ กัณฑ์",
        },
        "body": {
            "en": (
                "A 100-volume Thai presentation of the Tipiṭaka in the "
                "“Maha-Vitthara-Naya” style (about 5,000 sections), compiled with "
                "commentary material by Ajahn Pui Saengchai and published by S. "
                "Dhammabhakdi—not a word-for-word translation alone."
            ),
            "th": (
                "พระไตรปิฎกไทยแนวมหาวิตถารนัย ๕๐๐๐ กัณฑ์ ๑๐๐ เล่ม "
                "เรียบเรียงพร้อมอรรถกถาโดยอาจารย์ปุ้ย แสงฉาย จัดพิมพ์โดย ส. ธรรมภักดี "
                "มิใช่เพียงงานแปลตรงตัว"
            ),
        },
        "editions": [
            {
                "code": "th2528",
                "former_codes": ["th100"],
                "sort": 10,
                "cover": "sdb",
                "role": "translation",
                "languages": ["thai"],
                "scripts": ["thai"],
                "volume_set_count": 100,
                "publisher": PUBLISHERS["dhammabhakdi"],
                "published_year": "2528",
                "print_number": "1",
                "title": {
                    "en": "Maha-Vitthara-Naya Tipiṭaka",
                    "th": "พระไตรปิฎก มหาวิตถารนัย ๕๐๐๐ กัณฑ์",
                },
                "description": {
                    "en": "Thai Tipiṭaka with expanded commentary style, 100 volumes.",
                    "th": "พระไตรปิฎกไทยแนวมหาวิตถารนัย ๑๐๐ เล่ม",
                },
            },
        ],
    },
    {
        "code": "bj",
        "sort": 60,
        "tradition": "theravada",
        "country": "lk",
        "cover": "slk",
        "title": {
            "en": "Buddha Jayanti Tripitaka Granthamālā",
            "th": "พุทฺธชยนฺติ ตฺริปิฏก คฺรนฺถมาลา",
        },
        "body": {
            "en": (
                "The Buddha Jayanti Tipiṭaka is Sri Lanka’s mid-20th-century Pāli edition "
                "in Sinhala script (52 volume sets / 57 books), published by the "
                "government to mark 2,500 years of Buddhism."
            ),
            "th": (
                "พุทธชยันตีติปิฎก เป็นพระไตรปิฎกบาลีอักษรสิงหลของศรีลังกา "
                "๕๒ เล่มชุด (๕๗ เล่ม) จัดพิมพ์โดยรัฐบาลเนื่องในวาระ ๒๕๐๐ ปีแห่งพุทธศาสนา"
            ),
        },
        "editions": [
            {
                "code": "pali2499",
                "former_codes": ["pali-sinhala"],
                "sort": 10,
                "cover": "slk",
                "role": "source",
                "languages": ["pali", "sinhala"],
                "scripts": ["sinhala"],
                "volume_set_count": 52,
                "physical_volume_count": 57,
                "publisher": PUBLISHERS["sri_lanka_gov"],
                "published_year": "2499-2533",
                "print_number": "1",
                "title": {
                    "en": "Buddha Jayanti Tripitaka Granthamālā",
                    "th": "พุทฺธชยนฺติ ตฺริปิฏก คฺรนฺถมาลา",
                },
                "description": {
                    "en": (
                        "Pāli Tipiṭaka in Sinhala script; Buddha Jayanti edition (B.E. "
                        "2499–2533)."
                    ),
                    "th": "พระไตรปิฎกบาลีอักษรสิงหล ฉบับพุทธชยันตี พ.ศ. ๒๔๙๙–๒๕๓๓",
                },
            },
        ],
    },
    {
        "code": "ch",
        "former_codes": ["cs", "csm"],
        "sort": 70,
        "tradition": "theravada",
        "country": "mm",
        "cover": "mym",
        "title": {
            "en": "Chaṭṭha Saṅgīti Piṭaka (Myanmar DORA)",
            "th": "ฉฏฺฐสงฺคีติ ปิฏก (กรมการศาสนาเมียนมา)",
        },
        "body": {
            "en": (
                "The Sixth Buddhist Council (Chaṭṭha Saṅgīti) Pāli Tipiṭaka from Myanmar: "
                "Myanmar-script sets published by the Department of Religious Affairs "
                "(B.E. 2500–2556 and 2565), and a Roman-script 40-volume set (B.E. 2552 / "
                "2008) issued by the Buddhasāsana Society."
            ),
            "th": (
                "พระไตรปิฎกบาลีฉัฏฐสังคีติจากเมียนมา: ชุดอักษรพม่าของกรมการศาสนา "
                "(พ.ศ. ๒๕๐๐–๒๕๕๖ และ ๒๕๖๕) และชุดอักษรโรมัน ๔๐ เล่ม "
                "(พ.ศ. ๒๕๕๒ / ค.ศ. 2008) ของสมาคมพุทธศาสนา"
            ),
        },
        "editions": [
            {
                "code": "pali2500",
                "former_codes": ["myanmar-1"],
                "sort": 10,
                "cover": "mym",
                "role": "source",
                "languages": ["pali"],
                "scripts": ["myanmar"],
                "volume_set_count": 40,
                "publisher": PUBLISHERS["myanmar_dora"],
                "published_year": "2500-2556",
                "print_number": "1",
                "title": {
                    "en": "Chaṭṭha Saṅgīti Piṭaka",
                    "th": "ฉฏฺฐสงฺคีติ ปิฏก",
                },
                "description": {
                    "en": (
                        "Sixth Council Pāli Tipiṭaka in Myanmar script, 40 volumes (B.E. "
                        "2500–2556)."
                    ),
                    "th": "ฉัฏฐสังคีติบาลีอักษรพม่า ๔๐ เล่ม พ.ศ. ๒๕๐๐–๒๕๕๖",
                },
            },
            {
                "code": "pali2565",
                "former_codes": ["myanmar-2"],
                "sort": 20,
                "cover": "mym",
                "role": "source",
                "languages": ["pali"],
                "scripts": ["myanmar"],
                "volume_set_count": 40,
                "publisher": PUBLISHERS["myanmar_dora"],
                "published_year": "2565",
                "print_number": "1",
                "title": {
                    "en": "Chaṭṭha Saṅgīti Piṭaka",
                    "th": "ฉฏฺฐสงฺคีติ ปิฏก",
                },
                "description": {
                    "en": (
                        "Sixth Council Pāli Tipiṭaka in Myanmar script, 40 volumes (B.E. 2565 "
                        "set)."
                    ),
                    "th": "ฉัฏฐสังคีติบาลีอักษรพม่า ๔๐ เล่ม ชุด พ.ศ. ๒๕๖๕",
                },
            },
            {
                "code": "pali2552ro",
                "former_codes": ["pali2552", "cts-roman", "pali-2552"],
                "sort": 30,
                "cover": "cts-roman",
                "role": "source",
                "languages": ["pali"],
                "scripts": ["roman"],
                "volume_set_count": 40,
                "publisher": PUBLISHERS["buddhasasana_society_mm"],
                "published_year": "2552",
                "print_number": "1",
                "title": {
                    "en": "Chaṭṭha Saṅgīti Piṭaka (Roman)",
                    "th": "ฉฏฺฐสงฺคีติ ปิฏก (อักษรโรมัน)",
                },
                "description": {
                    "en": (
                        "Sixth Council Pāli Tipiṭaka in Roman script, 40 volumes "
                        "(Buddhasāsana Society, B.E. 2552 / 2008)."
                    ),
                    "th": (
                        "ฉัฏฐสังคีติบาลีอักษรโรมัน ๔๐ เล่ม "
                        "(สมาคมพุทธศาสนา พ.ศ. ๒๕๕๒ / ค.ศ. 2008)"
                    ),
                },
            },
        ],
    },
    {
        "code": "cht",
        "former_codes": ["cst"],
        "sort": 80,
        "tradition": "theravada",
        "country": "mm",
        "cover": "vri",
        "title": {
            "en": "Chaṭṭha Saṅgīti Piṭaka (Taiwan CBBEF)",
            "th": "ฉฏฺฐสงฺคีติ ปิฏก (มูลนิธิการศึกษาพระพุทธศาสนา ประเทศไต้หวัน)",
        },
        "body": {
            "en": (
                "A Myanmar-script Chaṭṭha Saṅgīti Tipiṭaka reprint (40 volumes) "
                "distributed by the Corporate Body of the Buddha Educational Foundation "
                "(Taiwan), based on the Sixth Council text."
            ),
            "th": (
                "พระไตรปิฎกฉัฏฐสังคีติอักษรพม่า ๔๐ เล่ม ที่มูลนิธิการศึกษาพระพุทธศาสนา "
                "ประเทศไต้หวันจัดพิมพ์/แจกเป็นธรรมทาน อิงข้อความสังคายนาครั้งที่ ๖"
            ),
        },
        "editions": [
            {
                "code": "pali2543",
                "former_codes": ["myanmar-tw"],
                "sort": 10,
                "cover": "vri",
                "role": "source",
                "languages": ["pali"],
                "scripts": ["myanmar"],
                "volume_set_count": 40,
                "publisher": PUBLISHERS["cbbef"],
                "place": "taipei",
                "published_year": "2543",
                "print_number": "1",
                "title": {
                    "en": "Chaṭṭha Saṅgīti Piṭaka (Taiwan)",
                    "th": "ฉฏฺฐสงฺคีติ ปิฏก (มูลนิธิการศึกษาพระพุทธศาสนา ประเทศไต้หวัน)",
                },
                "description": {
                    "en": (
                        "Sixth Council Pāli Tipiṭaka in Myanmar script, Taiwan CBBEF set (B.E. "
                        "2543)."
                    ),
                    "th": "ฉัฏฐสังคีติบาลีอักษรพม่า ชุดมูลนิธิไต้หวัน พ.ศ. ๒๕๔๓",
                },
            },
        ],
    },
    {
        "code": "nld",
        "sort": 125,
        "tradition": "theravada",
        "country": "in",
        "cover": "nld",
        "title": {
            "en": "Nālandā Devanāgarī Pāli Granthamālā",
            "th": "นาลนฺทา เทวนาครี ปาลิ คฺรนฺถมาลา",
        },
        "body": {
            "en": (
                "The Nālandā Devanāgarī Tipiṭaka presents the Pāli Canon in Devanāgarī "
                "script (41 volumes), published by Nav Nālandā Mahāvihāra in India for "
                "Indic readership."
            ),
            "th": (
                "นาลันทาเทวนาครีเป็นพระไตรปิฎกบาลีอักษรเทวนาครี ๔๑ เล่ม "
                "จัดพิมพ์โดยสถาบันนวนาลันทามหาวิหาร ประเทศอินเดีย"
            ),
        },
        "editions": [
            {
                "code": "pali2560",
                "former_codes": ["pali-deva"],
                "sort": 10,
                "cover": "nld",
                "role": "source",
                "languages": ["pali"],
                "scripts": ["devanagari"],
                "volume_set_count": 41,
                "publisher": PUBLISHERS["nalanda"],
                "published_year": "2560",
                "print_number": "2",
                "title": {
                    "en": "Nālandā Devanāgarī Pāli Tipiṭaka",
                    "th": "นาลนฺทา เทวนาครี ปาลิ คฺรนฺถมาลา",
                },
                "description": {
                    "en": "Pāli Tipiṭaka in Devanāgarī script, 41 volumes (reprint B.E. 2560).",
                    "th": "พระไตรปิฎกบาลีอักษรเทวนาครี ๔๑ เล่ม พิมพ์ซ้ำ พ.ศ. ๒๕๖๐",
                },
            },
        ],
    },
    {
        "code": "kmr",
        "sort": 110,
        "tradition": "theravada",
        "country": "kh",
        "cover": "kmr",
        "title": {
            "en": "Khmer Tipiṭaka (Buddhist Institute)",
            "th": "พระไตรปิฎกบาลี และแปลภาษาเขมร ฉบับพุทธศาสนบัณฑิต",
        },
        "body": {
            "en": (
                "The Cambodian Tipiṭaka of the Buddhist Institute pairs Pāli with Khmer "
                "translation in Khmer script across 110 volumes (published c. B.E. "
                "2472–2512)."
            ),
            "th": (
                "พระไตรปิฎกฉบับสถาบันพุทธศาสนบัณฑิตกัมพูชา เป็นบาลีคู่แปลเขมร "
                "อักษรขอม/เขมร ๑๑๐ เล่ม (ราว พ.ศ. ๒๔๗๒–๒๕๑๒)"
            ),
        },
        "editions": [
            {
                "code": "pali2472",
                "former_codes": ["pali-khmer"],
                "sort": 10,
                "cover": "kmr",
                "role": "source",
                "languages": ["pali", "khmer"],
                "scripts": ["khmer"],
                "volume_set_count": 110,
                "publisher": PUBLISHERS["buddhist_institute_kh"],
                "published_year": "2472-2512",
                "print_number": "1",
                "title": {
                    "en": "Pāli–Khmer Tipiṭaka (Buddhist Institute)",
                    "th": "พระไตรปิฎกบาลี และแปลภาษาเขมร ฉบับพุทธศาสนบัณฑิต",
                },
                "description": {
                    "en": "Pāli with Khmer translation, 110 volumes (Buddhist Institute).",
                    "th": "บาลีคู่แปลเขมร ๑๑๐ เล่ม ฉบับพุทธศาสนบัณฑิต",
                },
            },
        ],
    },
    {
        "code": "lao",
        "sort": 100,
        "tradition": "theravada",
        "country": "la",
        "cover": "lao",
        "title": {
            "en": "Lāvaratthe tepiṭakaṃ",
            "th": "ลาวรัถเถ เตปิฏกํ",
        },
        "body": {
            "en": (
                "The Lao State Tipiṭaka is a 45-volume Pāli edition in Lao Tham script, "
                "issued by the Lao Sangha for use in Laos."
            ),
            "th": (
                "ลาวรัถเถเตปิฏกํ เป็นพระไตรปิฎกบาลีอักษรธัมม์ลาว ๔๕ เล่ม "
                "จัดพิมพ์โดยคณะสงฆ์ลาว สำหรับใช้ในประเทศลาว"
            ),
        },
        "editions": [
            {
                "code": "pali2556",
                "former_codes": ["pali-lao"],
                "sort": 10,
                "cover": "lao",
                "role": "source",
                "languages": ["pali"],
                "scripts": ["lao-tham"],
                "volume_set_count": 45,
                "publisher": PUBLISHERS["lao_buddhist"],
                "published_year": "2556",
                "print_number": "1",
                "title": {
                    "en": "Lāvaratthe tepiṭakaṃ",
                    "th": "ลาวรัถเถ เตปิฏกํ",
                },
                "description": {
                    "en": "Pāli Tipiṭaka in Lao Tham script, 45 volumes.",
                    "th": "พระไตรปิฎกบาลีอักษรธัมม์ลาว ๔๕ เล่ม",
                },
            },
        ],
    },
    {
        "code": "pts",
        "sort": 120,
        "tradition": "theravada",
        "country": "gb",
        "cover": "pts-pali",
        "title": {
            "en": "Pali Text Society Tipiṭaka",
            "th": "พระไตรปิฎกฉบับสมาคมปาลีปกรณ์",
        },
        "body": {
            "en": (
                "The Pali Text Society (PTS) edition is the standard Roman-script Pāli "
                "Tipiṭaka for international scholarship (57 volumes), with a companion "
                "English translation series."
            ),
            "th": (
                "ฉบับสมาคมปาลีปกรณ์ (PTS) เป็นพระไตรปิฎกบาลีอักษรโรมันมาตรฐานสำหรับงานวิชาการ "
                "๕๗ เล่ม พร้อมชุดแปลภาษาอังกฤษคู่กัน"
            ),
        },
        "editions": [
            {
                "code": "pali2424",
                "former_codes": ["pali-roman"],
                "sort": 10,
                "cover": "pts-pali",
                "role": "source",
                "languages": ["pali"],
                "scripts": ["roman"],
                "volume_set_count": 57,
                "publisher": PUBLISHERS["pts"],
                "published_year": "2424-2541",
                "title": {
                    "en": "Pāli Tipiṭaka (PTS)",
                    "th": "พระไตรปิฎกบาลี ฉบับสมาคมปาลีปกรณ์",
                },
                "description": {
                    "en": "Pāli Tipiṭaka in Roman script, 57 volumes (PTS).",
                    "th": "พระไตรปิฎกบาลีอักษรโรมัน ๕๗ เล่ม (PTS)",
                },
            },
            {
                "code": "en2438",
                "former_codes": ["en"],
                "sort": 20,
                "cover": "pts-english",
                "role": "translation",
                "source_edition": "pali2424",
                "languages": ["english"],
                "scripts": ["roman"],
                "volume_set_count": 57,
                "physical_volume_count": 42,
                "publisher": PUBLISHERS["pts"],
                "published_year": "2438-2540",
                "title": {
                    "en": "English Tipiṭaka (PTS)",
                    "th": "พระไตรปิฎกภาษาอังกฤษ ฉบับสมาคมบาลีปกรณ์",
                },
                "description": {
                    "en": (
                        "English Tipiṭaka translations (PTS), listed against the 57 Pāli "
                        "catalog slots (about 42 published volumes; unpublished slots marked)."
                    ),
                    "th": (
                        "ชุดแปลอังกฤษของสมาคมปาลีปกรณ์ จัดรายการเทียบช่องบาลี ๕๗ ช่อง "
                        "(พิมพ์จริงราว ๔๒ เล่ม; ช่องที่ยังไม่มีแปลระบุไว้)"
                    ),
                },
            },
        ],
    },
    {
        "code": "ndz",
        "sort": 130,
        "tradition": "theravada",
        "country": "jp",
        "cover": "ndz",
        "title": {
            "en": "Nanden Daizōkyō",
            "th": "พระไตรปิฎกภาษาญี่ปุ่น ฉบับนันเดนไดโซเคียว",
        },
        "body": {
            "en": (
                "The Nanden Daizōkyō (南伝大蔵経) is the classic Japanese translation of the "
                "Theravāda Tipiṭaka (about 65 sets / 70 volumes), published by Daizō "
                "Shuppan."
            ),
            "th": (
                "นันเดนไดโซเคียว (南伝大蔵経) เป็นชุดแปลญี่ปุ่นคลาสสิกของพระไตรปิฎกเถรวาท ราว "
                "๖๕ เล่มชุด (๗๐ เล่ม) สำนักพิมพ์大蔵出版"
            ),
        },
        "editions": [
            {
                "code": "ja2544",
                "former_codes": ["ja"],
                "sort": 10,
                "cover": "ndz",
                "role": "translation",
                "languages": ["japanese"],
                "scripts": ["japanese"],
                "volume_set_count": 65,
                "physical_volume_count": 70,
                "publisher": PUBLISHERS["daizo"],
                "place": "tokyo",
                "published_year": "2544",
                "print_number": "1",
                "title": {
                    "en": "Nanden Daizōkyō",
                    "th": "นันเดน ไดโซเคียว",
                },
                "description": {
                    "en": (
                        "Japanese Theravāda Tipiṭaka translation (Nanden Daizōkyō), "
                        "65 sets / 70 volumes (B.E. 2544)."
                    ),
                    "th": (
                        "พระไตรปิฎกเถรวาทแปลญี่ปุ่น ฉบับนันเดนไดโซเคียว "
                        "๖๕ เล่มชุด / ๗๐ เล่ม พ.ศ. ๒๕๔๔"
                    ),
                },
            },
        ],
    },
    {
        "code": "ych",
        "sort": 140,
        "tradition": "theravada",
        "country": "tw",
        "cover": "ych",
        "title": {
            "en": "Chinese Tipiṭaka: Nanchuan (Yuanheng)",
            "th": "พระไตรปิฎกภาษาจีน ฉบับหนานฉวน",
        },
        "body": {
            "en": (
                "The Nanchuan (南传) Chinese Tipiṭaka from Yuanheng Temple, Taiwan, is a "
                "Chinese translation of the Theravāda Canon (about 70 sets / 71 volumes), "
                "drawing on the Japanese Nanden Daizōkyō tradition."
            ),
            "th": (
                "หนานฉวน (南传大藏经) จากวัดหยวนเหิง ไต้หวัน เป็นคำแปลจีนของพระไตรปิฎกเถรวาท "
                "ราว ๗๐ เล่มชุด (๗๑ เล่ม) อิงสายนันเดนไดโซเคียว"
            ),
        },
        "editions": [
            {
                "code": "zh2533",
                "former_codes": ["zh"],
                "sort": 10,
                "cover": "ych",
                "role": "translation",
                "languages": ["chinese"],
                "scripts": ["chinese"],
                "volume_set_count": 70,
                "physical_volume_count": 71,
                "publisher": PUBLISHERS["yuanheng"],
                "place": "kaohsiung",
                "published_year": "2533-2541",
                "print_number": "1",
                "title": {
                    "en": "Chinese Tipiṭaka: Nanchuan",
                    "th": "พระไตรปิฎกภาษาจีน ฉบับหนานฉวน",
                },
                "description": {
                    "en": (
                        "Chinese Theravāda Tipiṭaka translation from Yuanheng Temple "
                        "(70 sets / 71 volumes)."
                    ),
                    "th": "แปลจีนพระไตรปิฎกเถรวาท ฉบับวัดหยวนเหิง ๗๐ เล่มชุด / ๗๑ เล่ม",
                },
            },
        ],
    },
    {
        "code": "vnm",
        "sort": 150,
        "tradition": "theravada",
        "country": "vn",
        "cover": "vnm",
        "title": {
            "en": "Vietnamese Tipiṭaka (Theravāda Sutta)",
            "th": "พระไตรปิฎกภาษาเวียดนาม ฉบับนิกายเถรวาท",
        },
        "body": {
            "en": (
                "A Vietnamese Theravāda translation focused on the Sutta Piṭaka (13 "
                "volumes), produced by Vietnam’s Buddhist research institute (translation "
                "lineage of Thích Minh Châu)."
            ),
            "th": (
                "ฉบับแปลเวียดนามนิกายเถรวาท หมวดสุตตันตปิฎก ๑๓ เล่ม "
                "โดยสถาบันวิจัยพุทธศาสน์แห่งเวียดนาม (สายแปลของ Thích Minh Châu)"
            ),
        },
        "editions": [
            {
                "code": "vi2563",
                "former_codes": ["vi"],
                "sort": 10,
                "cover": "vnm",
                "role": "translation",
                "languages": ["vietnamese"],
                "scripts": ["vietnamese"],
                "volume_set_count": 13,
                "publisher": PUBLISHERS["vietnam_bri"],
                "published_year": "2563",
                "print_number": "2",
                "title": {
                    "en": "Vietnamese Tipiṭaka: Sutta Piṭaka",
                    "th": "พระไตรปิฎกภาษาเวียดนาม หมวดสุตตันตปิฎก",
                },
                "description": {
                    "en": (
                        "Vietnamese Theravāda Sutta translation, 13 volumes (2nd printing, B.E. "
                        "2563)."
                    ),
                    "th": "แปลสุตตันตปิฎกภาษาเวียดนาม ๑๓ เล่ม พิมพ์ครั้งที่ ๒ พ.ศ. ๒๕๖๓",
                },
            },
        ],
    },
    {
        "code": "tai",
        "sort": 85,
        "tradition": "theravada",
        "country": "mm",
        "cover": "tai",
        "title": {
            "en": "Tai Tipiṭaka",
            "th": "ไต ติปิฏก",
        },
        "body": {
            "en": (
                "A Pāli Tipiṭaka in Tai/Shan (Tai Yai) script from Panglong, Shan State "
                "(5 volumes, B.E. 2567), prepared by the Sangha Association for Tai "
                "Tipitaka Translation."
            ),
            "th": (
                "พระไตรปิฎกบาลีอักษรไทใหญ่จากเมืองปางโหลง รัฐฉาน ๕ เล่ม (พ.ศ. ๒๕๖๗) "
                "โดยคณะสงฆ์เพื่อการแปลพระไตรปิฎกไต"
            ),
        },
        "editions": [
            {
                "code": "pali2567",
                "former_codes": ["pali-tai"],
                "sort": 10,
                "cover": "tai",
                "role": "source",
                "languages": ["pali"],
                "scripts": ["tai-yai"],
                "volume_set_count": 5,
                "publisher": PUBLISHERS["tai_sangha"],
                "place": "panglong",
                "published_year": "2567",
                "print_number": "1",
                "title": {
                    "en": "Tai Tipiṭaka",
                    "th": "ไต ติปิฏก",
                },
                "description": {
                    "en": "Pāli Tipiṭaka in Tai Yai script, 5 volumes (B.E. 2567).",
                    "th": "พระไตรปิฎกบาลีอักษรไทใหญ่ ๕ เล่ม พ.ศ. ๒๕๖๗",
                },
            },
        ],
    },
    {
        "code": "hwn",
        "sort": 170,
        "tradition": "mahayana",
        "country": "cn",
        "cover": "hwn",
        "title": {
            "en": "Hongwu Nanzang",
            "th": "พระไตรปิฎกภาษาจีน ฉบับหงอู่หนานจั้ง",
        },
        "body": {
            "en": (
                "The Hongwu Southern Canon (洪武南藏) is a major Chinese Buddhist canon of "
                "the early Ming period, here in a modern China Bookstore reprint "
                "(hundreds of volumes in classical Chinese)."
            ),
            "th": (
                "หงอู่หนานจั้ง (洪武南藏) เป็นพระไตรปิฎกจีนสายมหายานสมัยต้นราชวงศ์หมิง "
                "ฉบับพิมพ์ซ้ำโดย China Bookstore อักษรจีนโบราณ จำนวนหลายร้อยเล่ม"
            ),
        },
        "editions": [
            {
                "code": "zh2564",
                "former_codes": ["zh-hongwu"],
                "sort": 10,
                "cover": "hwn",
                "role": "source",
                "languages": ["chinese"],
                "scripts": ["chinese"],
                "volume_set_count": 242,
                "publisher": PUBLISHERS["china_bookstore"],
                "published_year": "2564",
                "print_number": "1",
                "title": {
                    "en": "Hongwu Nanzang",
                    "th": "พระไตรปิฎกภาษาจีน ฉบับหงอู่หนานจั้ง",
                },
                "description": {
                    "en": "Ming Hongwu Southern Canon reprint in Chinese (242 volumes).",
                    "th": "หงอู่หนานจั้ง ฉบับพิมพ์ซ้ำภาษาจีน ๒๔๒ เล่ม",
                },
            },
        ],
    },
    {
        "code": "qll",
        "sort": 180,
        "tradition": "mahayana",
        "country": "cn",
        "cover": "qll",
        "title": {
            "en": "Qianlong Canon",
            "th": "พระไตรปิฎกภาษาจีน ฉบับเฉียนหลง",
        },
        "body": {
            "en": (
                "The Qianlong Canon (乾隆大藏经 / Dragon Canon) is the Qing imperial Chinese "
                "Buddhist canon; the hall holds a China Bookstore edition in 168 volumes."
            ),
            "th": (
                "เฉียนหลงต้าจั้งจิง (乾隆大藏经) เป็นพระไตรปิฎกจีนสมัยราชวงศ์ชิง ฉบับ China "
                "Bookstore ที่หอเก็บรักษา ๑๖๘ เล่ม"
            ),
        },
        "editions": [
            {
                "code": "zh2550",
                "former_codes": ["zh-qianlong"],
                "sort": 10,
                "cover": "qll",
                "role": "source",
                "languages": ["chinese"],
                "scripts": ["chinese"],
                "volume_set_count": 168,
                "publisher": PUBLISHERS["china_bookstore"],
                "published_year": "2550",
                "print_number": "1",
                "title": {
                    "en": "Qianlong Canon",
                    "th": "พระไตรปิฎกภาษาจีน ฉบับเฉียนหลง",
                },
                "description": {
                    "en": "Qing Qianlong Chinese Buddhist canon, 168 volumes.",
                    "th": "เฉียนหลงต้าจั้งจิง ๑๖๘ เล่ม",
                },
            },
        ],
    },
    {
        "code": "tib",
        "sort": 190,
        "tradition": "vajrayana",
        "country": "tib",
        "cover": "tib",
        "title": {
            "en": "Tibetan Tipiṭaka: Peking Edition",
            "th": "พระไตรปิฎกภาษาทิเบต ฉบับปักกิ่ง",
        },
        "body": {
            "en": (
                "The Peking (Beijing) Tibetan Canon reprint from the Palace Museum Press "
                "presents the Tibetan Kangyur/Tengyur tradition in about 150 sets (153 "
                "bound volumes)."
            ),
            "th": (
                "พระไตรปิฎกทิเบตฉบับปักกิ่งจากสำนักพิมพ์พระราชวังต้องห้าม ราว ๑๕๐ เล่มชุด "
                "(๑๕๓ เล่ม) ในสายคัมภีร์ทิเบต"
            ),
        },
        "editions": [
            {
                "code": "tib2563",
                "former_codes": ["tib-peking"],
                "sort": 10,
                "cover": "tib",
                "role": "source",
                "languages": ["tibetan"],
                "scripts": ["tibetan"],
                "volume_set_count": 150,
                "physical_volume_count": 153,
                "publisher": PUBLISHERS["palace_museum"],
                "published_year": "2563",
                "print_number": "1",
                "title": {
                    "en": "Tibetan Tipiṭaka: Peking Edition",
                    "th": "พระไตรปิฎกภาษาทิเบต ฉบับปักกิ่ง",
                },
                "description": {
                    "en": (
                        "Tibetan Buddhist canon, Peking edition reprint (150 sets / 153 volumes)."
                    ),
                    "th": "พระไตรปิฎกทิเบตฉบับปักกิ่ง ๑๕๐ เล่มชุด (๑๕๓ เล่ม)",
                },
            },
        ],
    },
]
