"""
Shared volume list for Syāmaraṭṭhassa / Dayyaraṭṭha Pāli editions
(pali2538 / pali2556 / pali2560 / pali2549) from tipitaka-catalog
``_body-mmr-pali.tex``.
"""

from __future__ import annotations

# Editions that share this 45-volume set (Syāmaraṭṭha printings + Dayyaraṭṭha).
# (collection_code, edition_code) — edition codes may repeat across collections.
MMR_PALI_EDITIONS = (
    ("sy", "pali2538"),
    ("sy", "pali2556"),
    ("sy", "pali2560"),
    ("dr", "pali2549"),
)
MMR_PALI_EDITION_CODES = tuple(code for _coll, code in MMR_PALI_EDITIONS)

# Each entry: volume_index (1–45), section code, titles en/th.
# Titles follow the Pāli names in _body-mmr-pali.tex (Thai script / Roman).
MMR_PALI_VOLUMES: list[dict] = [
    {
        "index": 1,
        "section": "vin",
        "title": {
            "en": "Vinayapiṭake Mahāvibhaṅgassa [paṭhamo bhāgo]",
            "th": "วินยปิฏเก มหาวิภงฺคสฺส [ปฐโม ภาโค]",
        },
    },
    {
        "index": 2,
        "section": "vin",
        "title": {
            "en": "Vinayapiṭake Mahāvibhaṅgassa [dutiyo bhāgo]",
            "th": "วินยปิฏเก มหาวิภงฺคสฺส [ทุติโย ภาโค]",
        },
    },
    {
        "index": 3,
        "section": "vin",
        "title": {
            "en": "Vinayapiṭake Bhikkhunīvibhaṅgo",
            "th": "วินยปิฏเก ภิกฺขุนีวิภงฺโค",
        },
    },
    {
        "index": 4,
        "section": "vin",
        "title": {
            "en": "Vinayapiṭake Mahāvaggassa [paṭhamo bhāgo]",
            "th": "วินยปิฏเก มหาวคฺคสฺส [ปฐโม ภาโค]",
        },
    },
    {
        "index": 5,
        "section": "vin",
        "title": {
            "en": "Vinayapiṭake Mahāvaggassa [dutiyo bhāgo]",
            "th": "วินยปิฏเก มหาวคฺคสฺส [ทุติโย ภาโค]",
        },
    },
    {
        "index": 6,
        "section": "vin",
        "title": {
            "en": "Vinayapiṭake Cullavaggassa [paṭhamo bhāgo]",
            "th": "วินยปิฏเก จุลฺลวคฺคสฺส [ปฐโม ภาโค]",
        },
    },
    {
        "index": 7,
        "section": "vin",
        "title": {
            "en": "Vinayapiṭake Cullavaggassa [dutiyo bhāgo]",
            "th": "วินยปิฏเก จุลฺลวคฺคสฺส [ทุติโย ภาโค]",
        },
    },
    {
        "index": 8,
        "section": "vin",
        "title": {
            "en": "Vinayapiṭake Parivāro",
            "th": "วินยปิฏเก ปริวาโร",
        },
    },
    {
        "index": 9,
        "section": "dn",
        "title": {
            "en": "Suttantapiṭake Dīghanikāyassa Sīlakkhandhavaggo",
            "th": "สุตฺตนฺตปิฏเก ทีฆนิกายสฺส สีลกฺขนฺธวคฺโค",
        },
    },
    {
        "index": 10,
        "section": "dn",
        "title": {
            "en": "Suttantapiṭake Dīghanikāyassa Mahāvaggo",
            "th": "สุตฺตนฺตปิฏเก ทีฆนิกายสฺส มหาวคฺโค",
        },
    },
    {
        "index": 11,
        "section": "dn",
        "title": {
            "en": "Suttantapiṭake Dīghanikāyassa Pāṭikavaggo",
            "th": "สุตฺตนฺตปิฏเก ทีฆนิกายสฺส ปาฏิกวคฺโค",
        },
    },
    {
        "index": 12,
        "section": "mn",
        "title": {
            "en": "Suttantapiṭake Majjhimanikāyassa Mūlapaṇṇāsakaṃ",
            "th": "สุตฺตนฺตปิฏเก มชฺฌิมนิกายสฺส มูลปณฺณาสกํ",
        },
    },
    {
        "index": 13,
        "section": "mn",
        "title": {
            "en": "Suttantapiṭake Majjhimanikāyassa Majjhimapaṇṇāsakaṃ",
            "th": "สุตฺตนฺตปิฏเก มชฺฌิมนิกายสฺส มชฺฌิมปณฺณาสกํ",
        },
    },
    {
        "index": 14,
        "section": "mn",
        "title": {
            "en": "Suttantapiṭake Majjhimanikāyassa Uparipaṇṇāsakaṃ",
            "th": "สุตฺตนฺตปิฏเก มชฺฌิมนิกายสฺส อุปริปณฺณาสกํ",
        },
    },
    {
        "index": 15,
        "section": "sn",
        "title": {
            "en": "Suttantapiṭake Saṃyuttanikāyassa Sagāthavaggo",
            "th": "สุตฺตนฺตปิฏเก สํยุตฺตนิกายสฺส สคาถวคฺโค",
        },
    },
    {
        "index": 16,
        "section": "sn",
        "title": {
            "en": "Suttantapiṭake Saṃyuttanikāyassa Nidānavaggo",
            "th": "สุตฺตนฺตปิฏเก สํยุตฺตนิกายสฺส นิทานวคฺโค",
        },
    },
    {
        "index": 17,
        "section": "sn",
        "title": {
            "en": "Suttantapiṭake Saṃyuttanikāyassa Khandhavāravaggo",
            "th": "สุตฺตนฺตปิฏเก สํยุตฺตนิกายสฺส ขนฺธวารวคฺโค",
        },
    },
    {
        "index": 18,
        "section": "sn",
        "title": {
            "en": "Suttantapiṭake Saṃyuttanikāyassa Saḷāyatanavaggo",
            "th": "สุตฺตนฺตปิฏเก สํยุตฺตนิกายสฺส สฬายตนวคฺโค",
        },
    },
    {
        "index": 19,
        "section": "sn",
        "title": {
            "en": "Suttantapiṭake Saṃyuttanikāyassa Mahāvāravaggo",
            "th": "สุตฺตนฺตปิฏเก สํยุตฺตนิกายสฺส มหาวารวคฺโค",
        },
    },
    {
        "index": 20,
        "section": "an",
        "title": {
            "en": "Suttantapiṭake Aṅguttaranikāyassa [paṭhamo bhāgo]",
            "th": "สุตฺตนฺตปิฏเก องฺคุตฺตรนิกายสฺส [ปฐโม ภาโค]",
        },
    },
    {
        "index": 21,
        "section": "an",
        "title": {
            "en": "Suttantapiṭake Aṅguttaranikāyassa [dutiyo bhāgo]",
            "th": "สุตฺตนฺตปิฏเก องฺคุตฺตรนิกายสฺส [ทุติโย ภาโค]",
        },
    },
    {
        "index": 22,
        "section": "an",
        "title": {
            "en": "Suttantapiṭake Aṅguttaranikāyassa [tatiyo bhāgo]",
            "th": "สุตฺตนฺตปิฏเก องฺคุตฺตรนิกายสฺส [ตติโย ภาโค]",
        },
    },
    {
        "index": 23,
        "section": "an",
        "title": {
            "en": "Suttantapiṭake Aṅguttaranikāyassa [catuttho bhāgo]",
            "th": "สุตฺตนฺตปิฏเก องฺคุตฺตรนิกายสฺส [จตุตฺโถ ภาโค]",
        },
    },
    {
        "index": 24,
        "section": "an",
        "title": {
            "en": "Suttantapiṭake Aṅguttaranikāyassa [pañcamo bhāgo]",
            "th": "สุตฺตนฺตปิฏเก องฺคุตฺตรนิกายสฺส [ปญฺจโม ภาโค]",
        },
    },
    {
        "index": 25,
        "section": "kn",
        "title": {
            "en": (
                "Suttantapiṭake Khuddakanikāyassa "
                "Khuddakapāṭha-Dhammapadagāthā-Udāna-Itivuttaka-Suttanipātā"
            ),
            "th": (
                "สุตฺตนฺตปิฏเก ขุทฺทกนิกายสฺส "
                "ขุทฺทกปาฐ-ธมฺมปทคาถา-อุทาน-อิติวุตฺตก-สุตฺตนิปาตา"
            ),
        },
    },
    {
        "index": 26,
        "section": "kn",
        "title": {
            "en": (
                "Suttantapiṭake Khuddakanikāyassa "
                "Vimānavatthu-Petavatthu-Theragāthā-Therīgāthā"
            ),
            "th": (
                "สุตฺตนฺตปิฏเก ขุทฺทกนิกายสฺส "
                "วิมานวตฺถุ-เปตวตฺถุ-เถรคาถา-เถรีคาถา"
            ),
        },
    },
    {
        "index": 27,
        "section": "kn",
        "title": {
            "en": (
                "Suttantapiṭake Khuddakanikāyassa Jātakaṃ [paṭhamo bhāgo] "
                "(eka-cattālīsanipātajātakaṃ)"
            ),
            "th": (
                "สุตฺตนฺตปิฏเก ขุทฺทกนิกายสฺส ชาดกํ [ปฐโม ภาโค] "
                "(เอก-จตฺตาลีสนิปาตชาดกํ)"
            ),
        },
    },
    {
        "index": 28,
        "section": "kn",
        "title": {
            "en": (
                "Suttantapiṭake Khuddakanikāyassa Jātakaṃ [dutiyo bhāgo] "
                "(paññāsa-mahānipātajātakaṃ)"
            ),
            "th": (
                "สุตฺตนฺตปิฏเก ขุทฺทกนิกายสฺส ชาดกํ [ทุติโย ภาโค] "
                "(ปญฺญาส-มหานิปาตชาดกํ)"
            ),
        },
    },
    {
        "index": 29,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭake Khuddakanikāyassa Mahāniddeso",
            "th": "สุตฺตนฺตปิฏเก ขุทฺทกนิกายสฺส มหานิทฺเทโส",
        },
    },
    {
        "index": 30,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭake Khuddakanikāyassa Cūḷaniddeso",
            "th": "สุตฺตนฺตปิฏเก ขุทฺทกนิกายสฺส จูฬนิทฺเทโส",
        },
    },
    {
        "index": 31,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭake Khuddakanikāyassa Paṭisambhidāmaggo",
            "th": "สุตฺตนฺตปิฏเก ขุทฺทกนิกายสฺส ปฏิสมฺภิทามคฺโค",
        },
    },
    {
        "index": 32,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭake Khuddakanikāyassa Apadānassa [paṭhamo bhāgo]",
            "th": "สุตฺตนฺตปิฏเก ขุทฺทกนิกายสฺส อปทานสฺส [ปฐโม ภาโค]",
        },
    },
    {
        "index": 33,
        "section": "kn",
        "title": {
            "en": (
                "Suttantapiṭake Khuddakanikāyassa Apadānassa [dutiyo bhāgo] "
                "Buddhavamso Cariyāpiṭakaṃ"
            ),
            "th": (
                "สุตฺตนฺตปิฏเก ขุทฺทกนิกายสฺส อปทานสฺส [ทุติโย ภาโค] "
                "พุทฺธวํโส จริยาปิฏกํ"
            ),
        },
    },
    {
        "index": 34,
        "section": "abh",
        "title": {
            "en": "Abhidhammapiṭake Dhammasaṅgaṇī",
            "th": "อภิธมฺมปิฏเก ธมฺมสงฺคณิ",
        },
    },
    {
        "index": 35,
        "section": "abh",
        "title": {
            "en": "Abhidhammapiṭake Vibhaṅgo",
            "th": "อภิธมฺมปิฏเก วิภงฺโค",
        },
    },
    {
        "index": 36,
        "section": "abh",
        "title": {
            "en": "Abhidhammapiṭake Dhātukathā ceva Puggalapaññatti ca",
            "th": "อภิธมฺมปิฏเก ธาตุกถา เจว ปุคฺคลปญฺญตฺติ จ",
        },
    },
    {
        "index": 37,
        "section": "abh",
        "title": {
            "en": "Abhidhammapiṭake Kathāvatthu",
            "th": "อภิธมฺมปิฏเก กถาวตฺถุ",
        },
    },
    {
        "index": 38,
        "section": "abh",
        "title": {
            "en": "Abhidhammapiṭake Yamakaṃ [paṭhamo bhāgo]",
            "th": "อภิธมฺมปิฏเก ยมกํ [ปฐโม ภาโค]",
        },
    },
    {
        "index": 39,
        "section": "abh",
        "title": {
            "en": "Abhidhammapiṭake Yamakaṃ [dutiyo bhāgo]",
            "th": "อภิธมฺมปิฏเก ยมกํ [ทุติโย ภาโค]",
        },
    },
    {
        "index": 40,
        "section": "abh",
        "title": {
            "en": "Abhidhammapiṭake Paṭṭhānaṃ [paṭhamo bhāgo]",
            "th": "อภิธมฺมปิฏเก ปฏฐานํ [ปฐโม ภาโค]",
        },
    },
    {
        "index": 41,
        "section": "abh",
        "title": {
            "en": "Abhidhammapiṭake Paṭṭhānaṃ [dutiyo bhāgo]",
            "th": "อภิธมฺมปิฏเก ปฏฐานํ [ทุติโย ภาโค]",
        },
    },
    {
        "index": 42,
        "section": "abh",
        "title": {
            "en": "Abhidhammapiṭake Paṭṭhānaṃ [tatiyo bhāgo]",
            "th": "อภิธมฺมปิฏเก ปฏฐานํ [ตติโย ภาโค]",
        },
    },
    {
        "index": 43,
        "section": "abh",
        "title": {
            "en": "Abhidhammapiṭake Paṭṭhānaṃ [catuttho bhāgo]",
            "th": "อภิธมฺมปิฏเก ปฏฐานํ [จตุตฺโถ ภาโค]",
        },
    },
    {
        "index": 44,
        "section": "abh",
        "title": {
            "en": "Abhidhammapiṭake Paṭṭhānaṃ [pañcamo bhāgo]",
            "th": "อภิธมฺมปิฏเก ปฏฐานํ [ปญฺจโม ภาโค]",
        },
    },
    {
        "index": 45,
        "section": "abh",
        "title": {
            "en": "Abhidhammapiṭake Paṭṭhānaṃ [chaṭṭhamo bhāgo]",
            "th": "อภิธมฺมปิฏเก ปฏฐานํ [ฉฏฐโม ภาโค]",
        },
    },
]


def volume_code(index: int) -> str:
    return f"vol-{index:02d}"


def thai_digits(n: int) -> str:
    return "".join("๐๑๒๓๔๕๖๗๘๙"[int(ch)] for ch in str(n))
