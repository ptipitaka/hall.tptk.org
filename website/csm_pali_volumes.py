"""
Shared volume list for Chaṭṭha Saṅgīti (Myanmar) Tipiṭaka editions
from tipitaka-catalog ``_body-chatta-myanmar.tex`` (40 volumes).
"""

from __future__ import annotations

# (collection_code, edition_code) pairs that share this 40-volume set.
CSM_PALI_EDITIONS = (
    ("ch", "pali2552ro"),
    ("ch", "pali2500"),
    ("ch", "pali2565"),
    ("cht", "pali2543"),
)

# Backward-compatible flat codes (unique within this set today).
CSM_PALI_EDITION_CODES = tuple(code for _coll, code in CSM_PALI_EDITIONS)

# Each entry: volume_index (1–40), section code, titles en/th.
# Titles follow the Pāli names in _body-chatta-myanmar.tex (Thai script / Roman).
# Split volumes (12–13, 15–17) combine both cover parts with " / ".
CSM_PALI_VOLUMES: list[dict] = [
    {
        "index": 1,
        "section": "vin",
        "title": {
            "en": "Pārājikapāḷi",
            "th": "ปาราชิกปาฬิ",
        },
    },
    {
        "index": 2,
        "section": "vin",
        "title": {
            "en": "Pācittiyapāḷi",
            "th": "ปาจิตฺติยปาฬิ",
        },
    },
    {
        "index": 3,
        "section": "vin",
        "title": {
            "en": "Mahāvaggapāḷi",
            "th": "มหาวคฺคปาฬิ",
        },
    },
    {
        "index": 4,
        "section": "vin",
        "title": {
            "en": "Cūḷavaggapāḷi",
            "th": "จูฬวคฺคปาฬิ",
        },
    },
    {
        "index": 5,
        "section": "vin",
        "title": {
            "en": "Parivārapāḷi",
            "th": "ปริวารปาฬิ",
        },
    },
    {
        "index": 6,
        "section": "dn",
        "title": {
            "en": "Sīlakkhandhavaggapāḷi",
            "th": "สีลกฺขนฺธวคฺคปาฬิ",
        },
    },
    {
        "index": 7,
        "section": "dn",
        "title": {
            "en": "Mahāvaggapāḷi",
            "th": "มหาวคฺคปาฬิ",
        },
    },
    {
        "index": 8,
        "section": "dn",
        "title": {
            "en": "Pāthikavaggapāḷi",
            "th": "ปาถิกวคฺคปาฬิ",
        },
    },
    {
        "index": 9,
        "section": "mn",
        "title": {
            "en": "Mūlapaṇṇāsapāḷi",
            "th": "มูลปณฺณาสปาฬิ",
        },
    },
    {
        "index": 10,
        "section": "mn",
        "title": {
            "en": "Majjhimapaṇṇāsapāḷi",
            "th": "มชฺฌิมปณฺณาสปาฬิ",
        },
    },
    {
        "index": 11,
        "section": "mn",
        "title": {
            "en": "Uparipaṇṇāsapāḷi",
            "th": "อุปริปณฺณาสปาฬิ",
        },
    },
    {
        "index": 12,
        "section": "sn",
        "title": {
            "en": "Sagāthāvagga / Nidānavaggasaṃyuttapāḷi",
            "th": "สคาถาวคฺค / นิทานวคฺคสํยุตฺตปาฬิ",
        },
    },
    {
        "index": 13,
        "section": "sn",
        "title": {
            "en": "Khandhavagga / Saḷāyatanavaggasaṃyuttapāḷi",
            "th": "ขนฺธวคฺค / สฬายตนวคฺคสํยุตฺตปาฬิ",
        },
    },
    {
        "index": 14,
        "section": "sn",
        "title": {
            "en": "Mahāvaggasaṃyuttapāḷi",
            "th": "มหาวคฺคสํยุตฺตปาฬิ",
        },
    },
    {
        "index": 15,
        "section": "an",
        "title": {
            "en": "Ekaka Duka Tika / Catukkanipātapāḷi",
            "th": "เอกก ทุก ติก / จตุกฺกนิปาตปาฬิ",
        },
    },
    {
        "index": 16,
        "section": "an",
        "title": {
            "en": "Pañcaka Chakka / Sattakanipātapāḷi",
            "th": "ปญฺจก ฉกฺก / สตฺตกนิปาตปาฬิ",
        },
    },
    {
        "index": 17,
        "section": "an",
        "title": {
            "en": "Aṭṭhaka Navaka Dasaka / Ekādasakanipātapāḷi",
            "th": "อฏฺฐก นวก ทสก / เอกาทสกนิปาตปาฬิ",
        },
    },
    {
        "index": 18,
        "section": "kn",
        "title": {
            "en": "Khuddakapāṭha Dhammapada Udāna Itivuttaka Suttanipātapāḷi",
            "th": "ขุทฺทกปาฐ ธมฺมปท อุทาน อิติวุตฺตก สุตฺตนิปาตปาฬิ",
        },
    },
    {
        "index": 19,
        "section": "kn",
        "title": {
            "en": "Vimānavatthu Petavatthu Theragāthā Therīgāthāpāḷi",
            "th": "วิมานวตฺถุ เปตวตฺถุ เถรคาถา เถรีคาถาปาฬิ",
        },
    },
    {
        "index": 20,
        "section": "kn",
        "title": {
            "en": "Apadānapāḷi — paṭhamo bhāgo",
            "th": "อปทานปาฬิ — ปฐโม ภาโค",
        },
    },
    {
        "index": 21,
        "section": "kn",
        "title": {
            "en": "Apadānapāḷi — dutiyo bhāgo; Buddhavamsapāḷi; Cariyāpiṭakapāḷi",
            "th": "อปทานปาฬิ — ทุติโย ภาโค พุทฺธวํสปาฬิ จริยาปิฏกปาฬิ",
        },
    },
    {
        "index": 22,
        "section": "kn",
        "title": {
            "en": "Jātakapāḷi — paṭhamo bhāgo",
            "th": "ชาตกปาฬิ — ปฐโม ภาโค",
        },
    },
    {
        "index": 23,
        "section": "kn",
        "title": {
            "en": "Jātakapāḷi — dutiyo bhāgo",
            "th": "ชาตกปาฬิ — ทุติโย ภาโค",
        },
    },
    {
        "index": 24,
        "section": "kn",
        "title": {
            "en": "Mahāniddesapāḷi",
            "th": "มหานิทฺเทสปาฬิ",
        },
    },
    {
        "index": 25,
        "section": "kn",
        "title": {
            "en": "Cūḷaniddesapāḷi",
            "th": "จูฬนิทฺเทสปาฬิ",
        },
    },
    {
        "index": 26,
        "section": "kn",
        "title": {
            "en": "Paṭisambhidāmaggapāḷi",
            "th": "ปฏิสมฺภิทามคฺคปาฬิ",
        },
    },
    {
        "index": 27,
        "section": "kn",
        "title": {
            "en": "Netti Peṭakopadesapāḷi",
            "th": "เนตฺติ เปฏโกปเทสปาฬิ",
        },
    },
    {
        "index": 28,
        "section": "kn",
        "title": {
            "en": "Milindapañhapāḷi",
            "th": "มิลินฺทปญฺหปาฬิ",
        },
    },
    {
        "index": 29,
        "section": "abh",
        "title": {
            "en": "Dhammasaṅgaṇīpāḷi",
            "th": "ธมฺมสงฺคณีปาฬิ",
        },
    },
    {
        "index": 30,
        "section": "abh",
        "title": {
            "en": "Vibhaṅgapāḷi",
            "th": "วิภงฺคปาฬิ",
        },
    },
    {
        "index": 31,
        "section": "abh",
        "title": {
            "en": "Dhātukathā Puggalapaññattipāḷi",
            "th": "ธาตุกถา ปุคฺคลปญฺญตฺติปาฬิ",
        },
    },
    {
        "index": 32,
        "section": "abh",
        "title": {
            "en": "Kathāvatthupāḷi",
            "th": "กถาวตฺถุปาฬิ",
        },
    },
    {
        "index": 33,
        "section": "abh",
        "title": {
            "en": "Yamakapāḷi — paṭhamo bhāgo",
            "th": "ยมกปาฬิ — ปฐโม ภาโค",
        },
    },
    {
        "index": 34,
        "section": "abh",
        "title": {
            "en": "Yamakapāḷi — dutiyo bhāgo",
            "th": "ยมกปาฬิ — ทุติโย ภาโค",
        },
    },
    {
        "index": 35,
        "section": "abh",
        "title": {
            "en": "Yamakapāḷi — tatiyo bhāgo",
            "th": "ยมกปาฬิ — ตติโย ภาโค",
        },
    },
    {
        "index": 36,
        "section": "abh",
        "title": {
            "en": "Paṭṭhānapāḷi — paṭhamo bhāgo",
            "th": "ปฏฺฐานปาฬิ — ปฐโม ภาโค",
        },
    },
    {
        "index": 37,
        "section": "abh",
        "title": {
            "en": "Paṭṭhānapāḷi — dutiyo bhāgo",
            "th": "ปฏฺฐานปาฬิ — ทุติโย ภาโค",
        },
    },
    {
        "index": 38,
        "section": "abh",
        "title": {
            "en": "Paṭṭhānapāḷi — tatiyo bhāgo",
            "th": "ปฏฺฐานปาฬิ — ตติโย ภาโค",
        },
    },
    {
        "index": 39,
        "section": "abh",
        "title": {
            "en": "Paṭṭhānapāḷi — catuttho bhāgo",
            "th": "ปฏฺฐานปาฬิ — จตุตฺโถ ภาโค",
        },
    },
    {
        "index": 40,
        "section": "abh",
        "title": {
            "en": "Paṭṭhānapāḷi — pañcamo bhāgo",
            "th": "ปฏฺฐานปาฬิ — ปญฺจโม ภาโค",
        },
    },
]


def volume_code(index: int) -> str:
    return f"vol-{index:02d}"


def thai_digits(n: int) -> str:
    return "".join("๐๑๒๓๔๕๖๗๘๙"[int(ch)] for ch in str(n))
