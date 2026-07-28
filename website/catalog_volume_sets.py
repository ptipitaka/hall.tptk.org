# -*- coding: utf-8 -*-
"""Tipiṭaka volume title lists extracted from tipitaka-catalog TeX.

Each list entry:
    {"index": int, "section": "vin"|"dn"|"mn"|"sn"|"an"|"kn"|"abh",
     "title": {"en": str, "th": str}}

Optional ``catalog_no`` (str): displayed volume number when it differs from
``index`` (e.g. PTS English splits ``33.(1)``).

Regenerate with: ``python scripts/extract_catalog_volumes.py``
(then move/merge into this module). Used by ``populate_catalog_volumes``.
"""
from __future__ import annotations


# === MCH_PALI_VOLUMES ===
# hall edition code(s): pali2506
# source: tipitaka-catalog/catalog/content/mch-pali-thai.tex
# count: 45
# Compare to MMR Pāli (mmr_pali_volumes): MCU uses -pāli locative forms (Mahāvibhaṅgapāli vs MMR Mahāvibhaṅgassa); Cūḷa vs Cullavagga; AN named nipātas vs MMR numbered bhāga; KN/Abhidhamma wording differs slightly; same 8+3+3+5+5+9+12 = 45 structure.
MCH_PALI_VOLUMES = [
    {
        "index": 1,
        "section": "vin",
        "title": {
            "en": "Vinayapiṭake Mahāvibhaṅgapāli [paṭhamabhāga]",
            "th": "วินยปิฏเก มหาวิภงฺคปาลิ [ปฐมภาค]",
        },
    },
    {
        "index": 2,
        "section": "vin",
        "title": {
            "en": "Vinayapiṭake Mahāvibhaṅgapāli [dutiyabhāga]",
            "th": "วินยปิฏเก มหาวิภงฺคปาลิ [ทุติยภาค]",
        },
    },
    {
        "index": 3,
        "section": "vin",
        "title": {
            "en": "Vinayapiṭake Bhikkhunīvibhaṅgapāli",
            "th": "วินยปิฏเก ภิกฺขุนีวิภงฺคปาลิ",
        },
    },
    {
        "index": 4,
        "section": "vin",
        "title": {
            "en": "Vinayapiṭake Mahāvaggapāli [paṭhamabhāga]",
            "th": "วินยปิฏเก มหาวคฺคปาลิ [ปฐมภาค]",
        },
    },
    {
        "index": 5,
        "section": "vin",
        "title": {
            "en": "Vinayapiṭake Mahāvaggapāli [dutiyabhāga]",
            "th": "วินยปิฏเก มหาวคฺคปาลิ [ทุติยภาค]",
        },
    },
    {
        "index": 6,
        "section": "vin",
        "title": {
            "en": "Vinayapiṭake Cūḷavaggapāli [paṭhamabhāga]",
            "th": "วินยปิฏเก จูฬวคฺคปาลิ [ปฐมภาค]",
        },
    },
    {
        "index": 7,
        "section": "vin",
        "title": {
            "en": "Vinayapiṭake Cūḷavaggapāli [dutiyabhāga]",
            "th": "วินยปิฏเก จูฬวคฺคปาลิ [ทุติยภาค]",
        },
    },
    {
        "index": 8,
        "section": "vin",
        "title": {
            "en": "Vinayapiṭake Parivārapāli",
            "th": "วินยปิฏเก ปริวารปาลิ",
        },
    },
    {
        "index": 9,
        "section": "dn",
        "title": {
            "en": "Suttantapiṭake Dīghanikāye Sīlakkhandhavaggapāli",
            "th": "สุตฺตนฺตปิฏเก ทีฆนิกาเย สีลกฺขนฺธวคฺคปาลิ",
        },
    },
    {
        "index": 10,
        "section": "dn",
        "title": {
            "en": "Suttantapiṭake Dīghanikāye Mahāvaggapāli",
            "th": "สุตฺตนฺตปิฏเก ทีฆนิกาเย มหาวคฺคปาลิ",
        },
    },
    {
        "index": 11,
        "section": "dn",
        "title": {
            "en": "Suttantapiṭake Dīghanikāye Pāṭikavaggapāli",
            "th": "สุตฺตนฺตปิฏเก ทีฆนิกาเย ปาฏิกวคฺคปาลิ",
        },
    },
    {
        "index": 12,
        "section": "mn",
        "title": {
            "en": "Suttantapiṭake Majjhimanikāye Mūlapaṇṇāsakapāli",
            "th": "สุตฺตนฺตปิฏเก มชฺฌิมนิกาเย มูลปณฺณาสกปาลิ",
        },
    },
    {
        "index": 13,
        "section": "mn",
        "title": {
            "en": "Suttantapiṭake Majjhimanikāye Majjhimapaṇṇāsakapāli",
            "th": "สุตฺตนฺตปิฏเก มชฺฌิมนิกาเย มชฺฌิมปณฺณาสกปาลิ",
        },
    },
    {
        "index": 14,
        "section": "mn",
        "title": {
            "en": "Suttantapiṭake Majjhimanikāye Uparipaṇṇāsakapāli",
            "th": "สุตฺตนฺตปิฏเก มชฺฌิมนิกาเย อุปริปณฺณาสกปาลิ",
        },
    },
    {
        "index": 15,
        "section": "sn",
        "title": {
            "en": "Suttantapiṭake Saṃyuttanikāye Sagāthavaggapāli",
            "th": "สุตฺตนฺตปิฏเก สํยุตฺตนิกาเย สคาถวคฺคปาลิ",
        },
    },
    {
        "index": 16,
        "section": "sn",
        "title": {
            "en": "Suttantapiṭake Saṃyuttanikāye Nidānavaggapāli",
            "th": "สุตฺตนฺตปิฏเก สํยุตฺตนิกาเย นิทานวคฺคปาลิ",
        },
    },
    {
        "index": 17,
        "section": "sn",
        "title": {
            "en": "Suttantapiṭake Saṃyuttanikāye Khandhavāravaggapāli",
            "th": "สุตฺตนฺตปิฏเก สํยุตฺตนิกาเย ขนฺธวารวคฺคปาลิ",
        },
    },
    {
        "index": 18,
        "section": "sn",
        "title": {
            "en": "Suttantapiṭake Saṃyuttanikāye Saḷāyatanavaggapāli",
            "th": "สุตฺตนฺตปิฏเก สํยุตฺตนิกาเย สฬายตนวคฺคปาลิ",
        },
    },
    {
        "index": 19,
        "section": "sn",
        "title": {
            "en": "Suttantapiṭake Saṃyuttanikāye Mahāvāravaggapāli",
            "th": "สุตฺตนฺตปิฏเก สํยุตฺตนิกาเย มหาวารวคฺคปาลิ",
        },
    },
    {
        "index": 20,
        "section": "an",
        "title": {
            "en": "Suttantapiṭake Aṅguttaranikāye Ekaka-Duka-Tikanipātapāli",
            "th": "สุตฺตนฺตปิฏเก องฺคุตฺตรนิกาเย เอกก-ทุก-ติกนิปาตปาลิ",
        },
    },
    {
        "index": 21,
        "section": "an",
        "title": {
            "en": "Suttantapiṭake Aṅguttaranikāye Catukkanipātapāli",
            "th": "สุตฺตนฺตปิฏเก องฺคุตฺตรนิกาเย จตุกฺกนิปาตปาลิ",
        },
    },
    {
        "index": 22,
        "section": "an",
        "title": {
            "en": "Suttantapiṭake Aṅguttaranikāye Pañcaka-Chakkanipātapāli",
            "th": "สุตฺตนฺตปิฏเก องฺคุตฺตรนิกาเย ปญฺจก-ฉกฺกนิปาตปาลิ",
        },
    },
    {
        "index": 23,
        "section": "an",
        "title": {
            "en": "Suttantapiṭake Aṅguttaranikāye Sattaka-Aṭṭhaka-Navakanipātapāli",
            "th": "สุตฺตนฺตปิฏเก องฺคุตฺตรนิกาเย สตฺตก-อฏฺฐก-นวกนิปาตปาลิ",
        },
    },
    {
        "index": 24,
        "section": "an",
        "title": {
            "en": "Suttantapiṭake Aṅguttaranikāye Dasaka-Ekādasakanipātapāli",
            "th": "สุตฺตนฺตปิฏเก องฺคุตฺตรนิกาเย ทสก-เอกาทสกนิปาตปาลิ",
        },
    },
    {
        "index": 25,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭake Khuddakanikāye Khuddakapāṭha-Dhammapada-Udāna-Itivuttaka-Suttanipātapāli",
            "th": "สุตฺตนฺตปิฏเก ขุทฺทกนิกาเย ขุทฺทกปาฐ-ธมฺมปท-อุทาน-อิติวุตฺตก-สุตฺตนิปาตปาลิ",
        },
    },
    {
        "index": 26,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭake Khuddakanikāye Vimānavatthu-Petavatthu-Theragāthā-Therīgāthāpāli",
            "th": "สุตฺตนฺตปิฏเก ขุทฺทกนิกาเย วิมานวตฺถุ-เปตวตฺถุ-เถรคาถา-เถรีคาถาปาลิ",
        },
    },
    {
        "index": 27,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭake Khuddakanikāye Jātakapāli [paṭhamabhāga]",
            "th": "สุตฺตนฺตปิฏเก ขุทฺทกนิกาเย ชาตกปาลิ [ปฐมภาค]",
        },
    },
    {
        "index": 28,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭake Khuddakanikāye Jātakapāli [dutiyabhāga]",
            "th": "สุตฺตนฺตปิฏเก ขุทฺทกนิกาเย ชาตกปาลิ [ทุติยภาค]",
        },
    },
    {
        "index": 29,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭake Khuddakanikāye Mahāniddesapāli",
            "th": "สุตฺตนฺตปิฏเก ขุทฺทกนิกาเย มหานิทฺเทสปาลิ",
        },
    },
    {
        "index": 30,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭake Khuddakanikāye Cūḷaniddesapāli",
            "th": "สุตฺตนฺตปิฏเก ขุทฺทกนิกาเย จูฬนิทฺเทสปาลิ",
        },
    },
    {
        "index": 31,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭake Khuddakanikāye Paṭisambhidāmaggapāli",
            "th": "สุตฺตนฺตปิฏเก ขุทฺทกนิกาเย ปฏิสมฺภิทามคฺคปาลิ",
        },
    },
    {
        "index": 32,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭake Khuddakanikāye Apadānapāli [paṭhamabhāga]",
            "th": "สุตฺตนฺตปิฏเก ขุทฺทกนิกาเย อปทานปาลิ [ปฐมภาค]",
        },
    },
    {
        "index": 33,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭake Khuddakanikāye Apadānapāli [dutiyabhāga]-Buddhavamsa-Cariyāpiṭaka",
            "th": "สุตฺตนฺตปิฏเก ขุทฺทกนิกาเย อปทานปาลิ [ทุติยภาค]-พุทฺธวํส-จริยาปิฏก",
        },
    },
    {
        "index": 34,
        "section": "abh",
        "title": {
            "en": "Abhidhammapiṭake Dhammasaṅgaṇipāli",
            "th": "อภิธมฺมปิฏเก ธมฺมสงฺคณิปาลิ",
        },
    },
    {
        "index": 35,
        "section": "abh",
        "title": {
            "en": "Abhidhammapiṭake Vibhaṅgapāli",
            "th": "อภิธมฺมปิฏเก วิภงฺคปาลิ",
        },
    },
    {
        "index": 36,
        "section": "abh",
        "title": {
            "en": "Abhidhammapiṭaka Dhātukathā Puggalapaññatti",
            "th": "อภิธมฺมปิฏก ธาตุกถา ปุคฺคลปญฺญตฺติ",
        },
    },
    {
        "index": 37,
        "section": "abh",
        "title": {
            "en": "Abhidhammapiṭake Kathāvatthupāli",
            "th": "อภิธมฺมปิฏเก กถาวตฺถุปาลิ",
        },
    },
    {
        "index": 38,
        "section": "abh",
        "title": {
            "en": "Abhidhammapiṭake Yamakapāli [paṭhamabhāga]",
            "th": "อภิธมฺมปิฏเก ยมกปาลิ [ปฐมภาค]",
        },
    },
    {
        "index": 39,
        "section": "abh",
        "title": {
            "en": "Abhidhammapiṭake Yamakapāli [dutiyabhāga]",
            "th": "อภิธมฺมปิฏเก ยมกปาลิ [ทุติยภาค]",
        },
    },
    {
        "index": 40,
        "section": "abh",
        "title": {
            "en": "Abhidhammapiṭake Paṭṭhānapāli [paṭhamabhāga]",
            "th": "อภิธมฺมปิฏเก ปฏฺฐานปาลิ [ปฐมภาค]",
        },
    },
    {
        "index": 41,
        "section": "abh",
        "title": {
            "en": "Abhidhammapiṭake Paṭṭhānapāli [dutiyabhāga]",
            "th": "อภิธมฺมปิฏเก ปฏฺฐานปาลิ [ทุติยภาค]",
        },
    },
    {
        "index": 42,
        "section": "abh",
        "title": {
            "en": "Abhidhammapiṭake Paṭṭhānapāli [tatiyabhāga]",
            "th": "อภิธมฺมปิฏเก ปฏฺฐานปาลิ [ตติยภาค]",
        },
    },
    {
        "index": 43,
        "section": "abh",
        "title": {
            "en": "Abhidhammapiṭake Paṭṭhānapāli [catutthabhāga]",
            "th": "อภิธมฺมปิฏเก ปฏฺฐานปาลิ [จตุตฺถภาค]",
        },
    },
    {
        "index": 44,
        "section": "abh",
        "title": {
            "en": "Abhidhammapiṭake Dukatikapaṭṭhānapāli [pañcamabhāga]",
            "th": "อภิธมฺมปิฏเก ทุกติกปฏฺฐานปาลิ [ปญจมภาค]",
        },
    },
    {
        "index": 45,
        "section": "abh",
        "title": {
            "en": "Abhidhammapiṭake Paṭṭhānapāli [chaṭṭhabhāga]",
            "th": "อภิธมฺมปิฏเก ปฏฺฐานปาลิ [ฉฏฺฐภาค]",
        },
    },
]

# === MMR_THAI_VOLUMES ===
# hall edition code(s): th2559
# source: tipitaka-catalog/catalog/content/mmr-thai.tex
# count: 45
MMR_THAI_VOLUMES = [
    {
        "index": 1,
        "section": "vin",
        "title": {
            "en": "Mahāvibhaṅga, Part 1",
            "th": "มหาวิภังค์ ภาค 1",
        },
    },
    {
        "index": 2,
        "section": "vin",
        "title": {
            "en": "Mahāvibhaṅga, Part 2",
            "th": "มหาวิภังค์ ภาค 2",
        },
    },
    {
        "index": 3,
        "section": "vin",
        "title": {
            "en": "Bhikkhunīvibhaṅga",
            "th": "ภิกขุนีวิภังค์",
        },
    },
    {
        "index": 4,
        "section": "vin",
        "title": {
            "en": "Mahāvagga, Part 1",
            "th": "มหาวรรค ภาค 1",
        },
    },
    {
        "index": 5,
        "section": "vin",
        "title": {
            "en": "Mahāvagga, Part 2",
            "th": "มหาวรรค ภาค 2",
        },
    },
    {
        "index": 6,
        "section": "vin",
        "title": {
            "en": "Cullavagga, Part 1",
            "th": "จุลลวรรค ภาค 1",
        },
    },
    {
        "index": 7,
        "section": "vin",
        "title": {
            "en": "Cullavagga, Part 2",
            "th": "จุลลวรรค ภาค 2",
        },
    },
    {
        "index": 8,
        "section": "vin",
        "title": {
            "en": "Parivāra",
            "th": "ปริวาร",
        },
    },
    {
        "index": 9,
        "section": "dn",
        "title": {
            "en": "Sīlakkhandhavagga",
            "th": "สีลขันธวรรค",
        },
    },
    {
        "index": 10,
        "section": "dn",
        "title": {
            "en": "Mahāvagga",
            "th": "มหาวรรค",
        },
    },
    {
        "index": 11,
        "section": "dn",
        "title": {
            "en": "Pāṭikavagga",
            "th": "ปาฏิกวรรค",
        },
    },
    {
        "index": 12,
        "section": "mn",
        "title": {
            "en": "Mūlapaṇṇāsaka",
            "th": "มูลปัณณาสก์",
        },
    },
    {
        "index": 13,
        "section": "mn",
        "title": {
            "en": "Majjhimapaṇṇāsaka",
            "th": "มัชฌิมปัณณาสก์",
        },
    },
    {
        "index": 14,
        "section": "mn",
        "title": {
            "en": "Uparipaṇṇāsaka",
            "th": "อุปริปัณณาสก์",
        },
    },
    {
        "index": 15,
        "section": "sn",
        "title": {
            "en": "Sagāthāvagga",
            "th": "สคาถาวรรค",
        },
    },
    {
        "index": 16,
        "section": "sn",
        "title": {
            "en": "Nidānavagga",
            "th": "นิทานวรรค",
        },
    },
    {
        "index": 17,
        "section": "sn",
        "title": {
            "en": "Khandhavāravagga",
            "th": "ขันธวารวรรค",
        },
    },
    {
        "index": 18,
        "section": "sn",
        "title": {
            "en": "Saḷāyatanavagga",
            "th": "สฬายตนวรรค",
        },
    },
    {
        "index": 19,
        "section": "sn",
        "title": {
            "en": "Mahāvāravagga",
            "th": "มหาวารวรรค",
        },
    },
    {
        "index": 20,
        "section": "an",
        "title": {
            "en": "Aṅguttaranikāya, Part 1",
            "th": "องคุตตรนิกาย ภาค 1",
        },
    },
    {
        "index": 21,
        "section": "an",
        "title": {
            "en": "Aṅguttaranikāya, Part 2",
            "th": "องคุตตรนิกาย ภาค 2",
        },
    },
    {
        "index": 22,
        "section": "an",
        "title": {
            "en": "Aṅguttaranikāya, Part 3",
            "th": "องคุตตรนิกาย ภาค 3",
        },
    },
    {
        "index": 23,
        "section": "an",
        "title": {
            "en": "Aṅguttaranikāya, Part 4",
            "th": "องคุตตรนิกาย ภาค 4",
        },
    },
    {
        "index": 24,
        "section": "an",
        "title": {
            "en": "Aṅguttaranikāya, Part 5",
            "th": "องคุตตรนิกาย ภาค 5",
        },
    },
    {
        "index": 25,
        "section": "kn",
        "title": {
            "en": "Khuddakapāṭha–Dhammapada–Udāna–Itivuttaka–Suttanipāta",
            "th": "ขุททกปาฐะ-ธรรมบท-อุทาน-อิติวุตตกะ-สุตตนิบาต",
        },
    },
    {
        "index": 26,
        "section": "kn",
        "title": {
            "en": "Vimānavatthu–Petavatthu–Theragāthā–Therīgāthā",
            "th": "วิมานวัตถุ-เปตวัตถุ-เถรคาถา-เถรีคาถา",
        },
    },
    {
        "index": 27,
        "section": "kn",
        "title": {
            "en": "Jātaka, Part 1 — Eka–Cattālīsa Nipāta",
            "th": "ชาดก ภาค 1 — เอก-จัตตาฬีสนิบาตชาดก",
        },
    },
    {
        "index": 28,
        "section": "kn",
        "title": {
            "en": "Jātaka, Part 2 — Paññāsa–Mahā Nipāta",
            "th": "ชาดก ภาค 2 — ปัญญาส-มหานิบาตชาดก",
        },
    },
    {
        "index": 29,
        "section": "kn",
        "title": {
            "en": "Mahāniddesa",
            "th": "มหานิเทส",
        },
    },
    {
        "index": 30,
        "section": "kn",
        "title": {
            "en": "Cūḷaniddesa",
            "th": "จูฬนิเทส",
        },
    },
    {
        "index": 31,
        "section": "kn",
        "title": {
            "en": "Paṭisambhidāmagga",
            "th": "ปฏิสัมภิทามรรค",
        },
    },
    {
        "index": 32,
        "section": "kn",
        "title": {
            "en": "Apadāna, Part 1",
            "th": "อปทาน ภาค 1",
        },
    },
    {
        "index": 33,
        "section": "kn",
        "title": {
            "en": "Apadāna, Part 2 — Buddhavaṃsa–Cariyāpiṭaka",
            "th": "อปทาน ภาค 2 — พุทธวังสะ-จริยาปิฎก",
        },
    },
    {
        "index": 34,
        "section": "abh",
        "title": {
            "en": "Dhammasaṅgaṇī",
            "th": "ธัมมสังคณี",
        },
    },
    {
        "index": 35,
        "section": "abh",
        "title": {
            "en": "Vibhaṅga",
            "th": "วิภังค์",
        },
    },
    {
        "index": 36,
        "section": "abh",
        "title": {
            "en": "Dhātukathā and Puggalapaññatti",
            "th": "ธาตุกถา และ ปุคคลบัญญัติ",
        },
    },
    {
        "index": 37,
        "section": "abh",
        "title": {
            "en": "Kathāvatthu",
            "th": "กถาวัตถุ",
        },
    },
    {
        "index": 38,
        "section": "abh",
        "title": {
            "en": "Yamaka, Part 1",
            "th": "ยมก ภาค 1",
        },
    },
    {
        "index": 39,
        "section": "abh",
        "title": {
            "en": "Yamaka, Part 2",
            "th": "ยมก ภาค 2",
        },
    },
    {
        "index": 40,
        "section": "abh",
        "title": {
            "en": "Paṭṭhāna, Part 1",
            "th": "ปัฏฐาน ภาค 1",
        },
    },
    {
        "index": 41,
        "section": "abh",
        "title": {
            "en": "Paṭṭhāna, Part 2",
            "th": "ปัฏฐาน ภาค 2",
        },
    },
    {
        "index": 42,
        "section": "abh",
        "title": {
            "en": "Paṭṭhāna, Part 3",
            "th": "ปัฏฐาน ภาค 3",
        },
    },
    {
        "index": 43,
        "section": "abh",
        "title": {
            "en": "Paṭṭhāna, Part 4",
            "th": "ปัฏฐาน ภาค 4",
        },
    },
    {
        "index": 44,
        "section": "abh",
        "title": {
            "en": "Paṭṭhāna, Part 5",
            "th": "ปัฏฐาน ภาค 5",
        },
    },
    {
        "index": 45,
        "section": "abh",
        "title": {
            "en": "Paṭṭhāna, Part 6",
            "th": "ปัฏฐาน ภาค 6",
        },
    },
]

# === MCH_THAI_VOLUMES ===
# hall edition code(s): th2539
# source: tipitaka-catalog/catalog/content/mch-thai.tex
# count: 45
MCH_THAI_VOLUMES = [
    {
        "index": 1,
        "section": "vin",
        "title": {
            "en": "Mahāvibhaṅga, Part 1",
            "th": "วินัยปิฎก มหาวิภังค์ ภาค 1",
        },
    },
    {
        "index": 2,
        "section": "vin",
        "title": {
            "en": "Mahāvibhaṅga, Part 2",
            "th": "วินัยปิฎก มหาวิภังค์ ภาค 2",
        },
    },
    {
        "index": 3,
        "section": "vin",
        "title": {
            "en": "Bhikkhunīvibhaṅga",
            "th": "วินัยปิฎก ภิกขุนีวิภังค์",
        },
    },
    {
        "index": 4,
        "section": "vin",
        "title": {
            "en": "Mahāvagga, Part 1",
            "th": "วินัยปิฎก มหาวรรค ภาค 1",
        },
    },
    {
        "index": 5,
        "section": "vin",
        "title": {
            "en": "Mahāvagga, Part 2",
            "th": "วินัยปิฎก มหาวรรค ภาค 2",
        },
    },
    {
        "index": 6,
        "section": "vin",
        "title": {
            "en": "Cullavagga, Part 1",
            "th": "วินัยปิฎก จุลวรรค ภาค 1",
        },
    },
    {
        "index": 7,
        "section": "vin",
        "title": {
            "en": "Cullavagga, Part 2",
            "th": "วินัยปิฎก จุลวรรค ภาค 2",
        },
    },
    {
        "index": 8,
        "section": "vin",
        "title": {
            "en": "Parivāra",
            "th": "วินัยปิฎก ปริวาร",
        },
    },
    {
        "index": 9,
        "section": "dn",
        "title": {
            "en": "Sīlakkhandhavagga",
            "th": "สุตตันตปิฎก ทีฆนิกาย สีลขันธวรรค",
        },
    },
    {
        "index": 10,
        "section": "dn",
        "title": {
            "en": "Mahāvagga",
            "th": "สุตตันตปิฎก ทีฆนิกาย มหาวรรค",
        },
    },
    {
        "index": 11,
        "section": "dn",
        "title": {
            "en": "Pāṭikavagga",
            "th": "สุตตันตปิฎก ทีฆนิกาย ปาฏิกวรรค",
        },
    },
    {
        "index": 12,
        "section": "mn",
        "title": {
            "en": "Mūlapaṇṇāsaka",
            "th": "สุตตันตปิฎก มัชฌิมนิกาย มูลปัณณาสก์",
        },
    },
    {
        "index": 13,
        "section": "mn",
        "title": {
            "en": "Majjhimapaṇṇāsaka",
            "th": "สุตตันตปิฎก มัชฌิมนิกาย มัชฌิมปัณณาสก์",
        },
    },
    {
        "index": 14,
        "section": "mn",
        "title": {
            "en": "Uparipaṇṇāsaka",
            "th": "สุตตันตปิฎก มัชฌิมนิกาย อุปริปัณณาสก์",
        },
    },
    {
        "index": 15,
        "section": "sn",
        "title": {
            "en": "Sagāthavagga",
            "th": "สุตตันตปิฎก สังยุตตนิกาย สคาถวรรค",
        },
    },
    {
        "index": 16,
        "section": "sn",
        "title": {
            "en": "Nidānavagga",
            "th": "สุตตันตปิฎก สังยุตตนิกาย นิทานวรรค",
        },
    },
    {
        "index": 17,
        "section": "sn",
        "title": {
            "en": "Khandhavāravagga",
            "th": "สุตตันตปิฎก สังยุตตนิกาย ขันธวารวรรค",
        },
    },
    {
        "index": 18,
        "section": "sn",
        "title": {
            "en": "Saḷāyatanavagga",
            "th": "สุตตันตปิฎก สังยุตตนิกาย สฬายตนวรรค",
        },
    },
    {
        "index": 19,
        "section": "sn",
        "title": {
            "en": "Mahāvāravagga",
            "th": "สุตตันตปิฎก สังยุตตนิกาย มหาวารวรรค",
        },
    },
    {
        "index": 20,
        "section": "an",
        "title": {
            "en": "Ekaka–Duka–Tika Nipāta",
            "th": "สุตตันตปิฎก อังคุตตรนิกาย เอกก ทุก ติกนิบาต",
        },
    },
    {
        "index": 21,
        "section": "an",
        "title": {
            "en": "Catukka Nipāta",
            "th": "สุตตันตปิฎก อังคุตตรนิกาย จตุกกนิบาต",
        },
    },
    {
        "index": 22,
        "section": "an",
        "title": {
            "en": "Pañcaka–Chakka Nipāta",
            "th": "สุตตันตปิฎก อังคุตตรนิกาย ปัญจก ฉักกนิบาต",
        },
    },
    {
        "index": 23,
        "section": "an",
        "title": {
            "en": "Sattaka–Aṭṭhaka–Navaka Nipāta",
            "th": "สุตตันตปิฎก อังคุตตรนิกาย สัตตก อัฏฐก นวกนิบาต",
        },
    },
    {
        "index": 24,
        "section": "an",
        "title": {
            "en": "Dasaka–Ekādasaka Nipāta",
            "th": "สุตตันตปิฎก อังคุตตรนิกาย ทสก เอกาทสกนิบาต",
        },
    },
    {
        "index": 25,
        "section": "kn",
        "title": {
            "en": "Khuddakapāṭha–Dhammapada–Udāna–Itivuttaka–Suttanipāta",
            "th": "สุตตันตปิฎก ขุททกนิกาย ขุททกปาฐะ ธรรมบท อุทาน อิติวุตตกะ สุตตนิบาต",
        },
    },
    {
        "index": 26,
        "section": "kn",
        "title": {
            "en": "Vimānavatthu–Petavatthu–Theragāthā–Therīgāthā",
            "th": "สุตตันตปิฎก ขุททกนิกาย วิมาน เปตวัตถุ เถรคาถา เถรีคาถา",
        },
    },
    {
        "index": 27,
        "section": "kn",
        "title": {
            "en": "Jātaka, Part 1",
            "th": "สุตตันตปิฎก ขุททกนิกาย ชาดก ภาค 1",
        },
    },
    {
        "index": 28,
        "section": "kn",
        "title": {
            "en": "Jātaka, Part 2",
            "th": "สุตตันตปิฎก ขุททกนิกาย ชาดก ภาค 2",
        },
    },
    {
        "index": 29,
        "section": "kn",
        "title": {
            "en": "Mahāniddesa",
            "th": "สุตตันตปิฎก ขุททกนิกาย มหานิทเทส",
        },
    },
    {
        "index": 30,
        "section": "kn",
        "title": {
            "en": "Cūḷaniddesa",
            "th": "สุตตันตปิฎก ขุททกนิกาย จูฬนิทเทส",
        },
    },
    {
        "index": 31,
        "section": "kn",
        "title": {
            "en": "Paṭisambhidāmagga",
            "th": "สุตตันตปิฎก ขุททกนิกาย ปฏิสัมภิทามรรค",
        },
    },
    {
        "index": 32,
        "section": "kn",
        "title": {
            "en": "Apadāna, Part 1",
            "th": "สุตตันตปิฎก ขุททกนิกาย อปทาน ภาค 1",
        },
    },
    {
        "index": 33,
        "section": "kn",
        "title": {
            "en": "Apadāna, Part 2 — Buddhavaṃsa–Cariyāpiṭaka",
            "th": "สุตตันตปิฎก ขุททกนิกาย อปทาน ภาค 2 พุทธวงศ์ จริยาปิฎก",
        },
    },
    {
        "index": 34,
        "section": "abh",
        "title": {
            "en": "Dhammasaṅgaṇī",
            "th": "อภิธรรมปิฎก ธัมมสังคนี",
        },
    },
    {
        "index": 35,
        "section": "abh",
        "title": {
            "en": "Vibhaṅga",
            "th": "อภิธรรมปิฎก วิภังค์",
        },
    },
    {
        "index": 36,
        "section": "abh",
        "title": {
            "en": "Dhātukathā–Puggalapaññatti",
            "th": "อภิธรรมปิฎก ธาตุกถา ปุคคลบัญญัติ",
        },
    },
    {
        "index": 37,
        "section": "abh",
        "title": {
            "en": "Kathāvatthu",
            "th": "อภิธรรมปิฎก กถาวัตถุ",
        },
    },
    {
        "index": 38,
        "section": "abh",
        "title": {
            "en": "Yamaka, Part 1",
            "th": "อภิธรรมปิฎก ยมก ภาค 1",
        },
    },
    {
        "index": 39,
        "section": "abh",
        "title": {
            "en": "Yamaka, Part 2",
            "th": "อภิธรรมปิฎก ยมก ภาค 2",
        },
    },
    {
        "index": 40,
        "section": "abh",
        "title": {
            "en": "Paṭṭhāna, Part 1",
            "th": "อภิธรรมปิฎก ปัฏฐาน ภาค 1",
        },
    },
    {
        "index": 41,
        "section": "abh",
        "title": {
            "en": "Paṭṭhāna, Part 2",
            "th": "อภิธรรมปิฎก ปัฏฐาน ภาค 2",
        },
    },
    {
        "index": 42,
        "section": "abh",
        "title": {
            "en": "Paṭṭhāna, Part 3",
            "th": "อภิธรรมปิฎก ปัฏฐาน ภาค 3",
        },
    },
    {
        "index": 43,
        "section": "abh",
        "title": {
            "en": "Paṭṭhāna, Part 4",
            "th": "อภิธรรมปิฎก ปัฏฐาน ภาค 4",
        },
    },
    {
        "index": 44,
        "section": "abh",
        "title": {
            "en": "Paṭṭhāna, Part 5",
            "th": "อภิธรรมปิฎก ปัฏฐาน ภาค 5",
        },
    },
    {
        "index": 45,
        "section": "abh",
        "title": {
            "en": "Paṭṭhāna, Part 6",
            "th": "อภิธรรมปิฎก ปัฏฐาน ภาค 6",
        },
    },
]

# === CLPK_THAI_VOLUMES ===
# hall edition code(s): th2549
# source: tipitaka-catalog/catalog/content/clpk-thai.tex
# count: 45
CLPK_THAI_VOLUMES = [
    {
        "index": 1,
        "section": "vin",
        "title": {
            "en": "Mahāvibhaṅga, Part 1",
            "th": "มหาวิภังค์ ภาค 1",
        },
    },
    {
        "index": 2,
        "section": "vin",
        "title": {
            "en": "Mahāvibhaṅga, Part 2",
            "th": "มหาวิภังค์ ภาค 2",
        },
    },
    {
        "index": 3,
        "section": "vin",
        "title": {
            "en": "Bhikkhunīvibhaṅga",
            "th": "ภิกขุนีวิภังค์",
        },
    },
    {
        "index": 4,
        "section": "vin",
        "title": {
            "en": "Mahāvagga, Part 1",
            "th": "มหาวรรค ภาค 1",
        },
    },
    {
        "index": 5,
        "section": "vin",
        "title": {
            "en": "Mahāvagga, Part 2",
            "th": "มหาวรรค ภาค 2",
        },
    },
    {
        "index": 6,
        "section": "vin",
        "title": {
            "en": "Cullavagga, Part 1",
            "th": "จุลวรรค ภาค 1",
        },
    },
    {
        "index": 7,
        "section": "vin",
        "title": {
            "en": "Cullavagga, Part 2",
            "th": "จุลวรรค ภาค 2",
        },
    },
    {
        "index": 8,
        "section": "vin",
        "title": {
            "en": "Parivāra",
            "th": "ปริวาร",
        },
    },
    {
        "index": 9,
        "section": "dn",
        "title": {
            "en": "Sīlakkhandhavagga",
            "th": "สีลขันธวรรค",
        },
    },
    {
        "index": 10,
        "section": "dn",
        "title": {
            "en": "Mahāvagga",
            "th": "มหาวรรค",
        },
    },
    {
        "index": 11,
        "section": "dn",
        "title": {
            "en": "Pāṭikavagga",
            "th": "ปาฏิกวรรค",
        },
    },
    {
        "index": 12,
        "section": "mn",
        "title": {
            "en": "Mūlapaṇṇāsaka",
            "th": "มูลปัณณาสก์",
        },
    },
    {
        "index": 13,
        "section": "mn",
        "title": {
            "en": "Majjhimapaṇṇāsaka",
            "th": "มัชฌิมปัณณาสก์",
        },
    },
    {
        "index": 14,
        "section": "mn",
        "title": {
            "en": "Uparipaṇṇāsaka",
            "th": "อุปริปัณณาสก์",
        },
    },
    {
        "index": 15,
        "section": "sn",
        "title": {
            "en": "Sagāthavagga",
            "th": "สคาถวรรค",
        },
    },
    {
        "index": 16,
        "section": "sn",
        "title": {
            "en": "Nidānavagga",
            "th": "นิทานวรรค",
        },
    },
    {
        "index": 17,
        "section": "sn",
        "title": {
            "en": "Khandhavāravagga",
            "th": "ขันธวารวรรค",
        },
    },
    {
        "index": 18,
        "section": "sn",
        "title": {
            "en": "Saḷāyatanavagga",
            "th": "สฬายตนวรรค",
        },
    },
    {
        "index": 19,
        "section": "sn",
        "title": {
            "en": "Mahāvāravagga",
            "th": "มหาวารวรรค",
        },
    },
    {
        "index": 20,
        "section": "an",
        "title": {
            "en": "Ekaka–Duka–Tika Nipāta",
            "th": "เอก-ทุก-ติกนิบาต",
        },
    },
    {
        "index": 21,
        "section": "an",
        "title": {
            "en": "Catukka Nipāta",
            "th": "จตุกกนิบาต",
        },
    },
    {
        "index": 22,
        "section": "an",
        "title": {
            "en": "Pañcaka–Chakka Nipāta",
            "th": "ปัญจก-ฉักกนิบาต",
        },
    },
    {
        "index": 23,
        "section": "an",
        "title": {
            "en": "Sattaka–Aṭṭhaka–Navaka Nipāta",
            "th": "สัตตก-อัฏฐก-นวกนิบาต",
        },
    },
    {
        "index": 24,
        "section": "an",
        "title": {
            "en": "Dasaka–Ekādasaka Nipāta",
            "th": "ทสก-เอกาทสกนิบาต",
        },
    },
    {
        "index": 25,
        "section": "kn",
        "title": {
            "en": "Khuddakapāṭha–Dhammapada–Udāna–Itivuttaka–Suttanipāta",
            "th": "ขุททกปาฐ-ธรรมบท-อุทาน-อิติวุตตก-สุตตนิบาต",
        },
    },
    {
        "index": 26,
        "section": "kn",
        "title": {
            "en": "Vimānavatthu–Petavatthu–Theragāthā–Therīgāthā",
            "th": "วิมานวัตถุ-เปตวัตถุ-เถรคาถา-เถรีคาถา",
        },
    },
    {
        "index": 27,
        "section": "kn",
        "title": {
            "en": "Jātaka, Part 1",
            "th": "ชาดก ภาค 1",
        },
    },
    {
        "index": 28,
        "section": "kn",
        "title": {
            "en": "Jātaka, Part 2",
            "th": "ชาดก ภาค 2",
        },
    },
    {
        "index": 29,
        "section": "kn",
        "title": {
            "en": "Mahāniddesa",
            "th": "มหานิทเทส",
        },
    },
    {
        "index": 30,
        "section": "kn",
        "title": {
            "en": "Cūḷaniddesa",
            "th": "จูฬนิทเทส",
        },
    },
    {
        "index": 31,
        "section": "kn",
        "title": {
            "en": "Paṭisambhidāmagga",
            "th": "ปฏิสัมภิทามรรค",
        },
    },
    {
        "index": 32,
        "section": "kn",
        "title": {
            "en": "Apadāna, Part 1",
            "th": "อปทาน ภาค 1",
        },
    },
    {
        "index": 33,
        "section": "kn",
        "title": {
            "en": "Apadāna, Part 2 — Buddhavaṃsa–Cariyāpiṭaka",
            "th": "อปทาน ภาค 2-พุทธวงส์-จริยาปิฎก",
        },
    },
    {
        "index": 34,
        "section": "abh",
        "title": {
            "en": "Dhammasaṅgaṇī",
            "th": "ธัมมสังคณี",
        },
    },
    {
        "index": 35,
        "section": "abh",
        "title": {
            "en": "Vibhaṅga",
            "th": "วิภังค์",
        },
    },
    {
        "index": 36,
        "section": "abh",
        "title": {
            "en": "Dhātukathā–Puggalapaññatti",
            "th": "ธาตุกถา-ปุคคลบัญญัติ",
        },
    },
    {
        "index": 37,
        "section": "abh",
        "title": {
            "en": "Kathāvatthu",
            "th": "กถาวัตถุ",
        },
    },
    {
        "index": 38,
        "section": "abh",
        "title": {
            "en": "Yamaka, Part 1",
            "th": "ยมก ภาค 1",
        },
    },
    {
        "index": 39,
        "section": "abh",
        "title": {
            "en": "Yamaka, Part 2",
            "th": "ยมก ภาค 2",
        },
    },
    {
        "index": 40,
        "section": "abh",
        "title": {
            "en": "Paṭṭhāna, Part 1",
            "th": "ปัฏฐาน ภาค 1",
        },
    },
    {
        "index": 41,
        "section": "abh",
        "title": {
            "en": "Paṭṭhāna, Part 2",
            "th": "ปัฏฐาน ภาค 2",
        },
    },
    {
        "index": 42,
        "section": "abh",
        "title": {
            "en": "Paṭṭhāna, Part 3",
            "th": "ปัฏฐาน ภาค 3",
        },
    },
    {
        "index": 43,
        "section": "abh",
        "title": {
            "en": "Paṭṭhāna, Part 4",
            "th": "ปัฏฐาน ภาค 4",
        },
    },
    {
        "index": 44,
        "section": "abh",
        "title": {
            "en": "Paṭṭhāna, Part 5",
            "th": "ปัฏฐาน ภาค 5",
        },
    },
    {
        "index": 45,
        "section": "abh",
        "title": {
            "en": "Paṭṭhāna, Part 6",
            "th": "ปัฏฐาน ภาค 6",
        },
    },
]

# === MMR_91_VOLUMES ===
# hall edition code(s): th2525, th2552
# source: tipitaka-catalog/catalog/content/_body-mmr-91.tex
# count: 91
# Tipiṭaka+Aṭṭhakathā; ranges expanded to printed volume numbers 1–91.
MMR_91_VOLUMES = [
    {
        "index": 1,
        "section": "vin",
        "title": {
            "en": "Vinayapiṭaka Mahāvibhaṅga vol. 1 [สมันตปาสาทิกา ภาค 1] — printed vol. 1",
            "th": "พระวินัยปิฎก มหาวิภังค์ เล่ม 1 [สมันตปาสาทิกา ภาค 1] — พิมพ์เล่ม 1",
        },
    },
    {
        "index": 2,
        "section": "vin",
        "title": {
            "en": "Vinayapiṭaka Mahāvibhaṅga vol. 1 [สมันตปาสาทิกา ภาค 1] — printed vol. 2",
            "th": "พระวินัยปิฎก มหาวิภังค์ เล่ม 1 [สมันตปาสาทิกา ภาค 1] — พิมพ์เล่ม 2",
        },
    },
    {
        "index": 3,
        "section": "vin",
        "title": {
            "en": "Vinayapiṭaka Mahāvibhaṅga vol. 1 [สมันตปาสาทิกา ภาค 1] — printed vol. 3",
            "th": "พระวินัยปิฎก มหาวิภังค์ เล่ม 1 [สมันตปาสาทิกา ภาค 1] — พิมพ์เล่ม 3",
        },
    },
    {
        "index": 4,
        "section": "vin",
        "title": {
            "en": "Vinayapiṭaka Mahāvibhaṅga vol. 2 [สมันตปาสาทิกา ภาค 2]",
            "th": "พระวินัยปิฎก มหาวิภังค์ เล่ม 2 [สมันตปาสาทิกา ภาค 2]",
        },
    },
    {
        "index": 5,
        "section": "vin",
        "title": {
            "en": "Vinayapiṭaka Bhikkhunīvibhaṅga vol. 3 [สมันตปาสาทิกา ภาค 2]",
            "th": "พระวินัยปิฎก ภิกขุนีวิภังค์ เล่ม 3 [สมันตปาสาทิกา ภาค 2]",
        },
    },
    {
        "index": 6,
        "section": "vin",
        "title": {
            "en": "Vinayapiṭaka Mahāvagga vol. 4 part 1 [สมันตปาสาทิกา ภาค 3]",
            "th": "พระวินัยปิฎก มหาวรรค เล่ม 4 ภาค 1 [สมันตปาสาทิกา ภาค 3]",
        },
    },
    {
        "index": 7,
        "section": "vin",
        "title": {
            "en": "Vinayapiṭaka Mahāvagga vol. 5 part 2 [สมันตปาสาทิกา ภาค 3]",
            "th": "พระวินัยปิฎก มหาวรรค เล่ม 5 ภาค 2 [สมันตปาสาทิกา ภาค 3]",
        },
    },
    {
        "index": 8,
        "section": "vin",
        "title": {
            "en": "Vinayapiṭaka Cullavagga vol. 6 part 1 [สมันตปาสาทิกา ภาค 3]",
            "th": "พระวินัยปิฎก จุลวรรค เล่ม 6 ภาค 1 [สมันตปาสาทิกา ภาค 3]",
        },
    },
    {
        "index": 9,
        "section": "vin",
        "title": {
            "en": "Vinayapiṭaka Cullavagga vol. 7 part 2 [สมันตปาสาทิกา ภาค 3]",
            "th": "พระวินัยปิฎก จุลวรรค เล่ม 7 ภาค 2 [สมันตปาสาทิกา ภาค 3]",
        },
    },
    {
        "index": 10,
        "section": "vin",
        "title": {
            "en": "Vinayapiṭaka Parivāra vol. 8 [สมันตปาสาทิกา ภาค 3]",
            "th": "พระวินัยปิฎก ปริวาร เล่ม 8 [สมันตปาสาทิกา ภาค 3]",
        },
    },
    {
        "index": 11,
        "section": "dn",
        "title": {
            "en": "Suttantapiṭaka Dīghanikāya Sīlakkhandhavagga vol. 1 [สุมังคลวิลาสินี ภาค 1] — printed vol. 11",
            "th": "พระสุตตันตปิฎก ทีฆนิกาย สีลขันธวรรค เล่ม 1 [สุมังคลวิลาสินี ภาค 1] — พิมพ์เล่ม 11",
        },
    },
    {
        "index": 12,
        "section": "dn",
        "title": {
            "en": "Suttantapiṭaka Dīghanikāya Sīlakkhandhavagga vol. 1 [สุมังคลวิลาสินี ภาค 1] — printed vol. 12",
            "th": "พระสุตตันตปิฎก ทีฆนิกาย สีลขันธวรรค เล่ม 1 [สุมังคลวิลาสินี ภาค 1] — พิมพ์เล่ม 12",
        },
    },
    {
        "index": 13,
        "section": "dn",
        "title": {
            "en": "Suttantapiṭaka Dīghanikāya Mahāvagga vol. 2 [สุมังคลวิลาสินี ภาค 2] — printed vol. 13",
            "th": "พระสุตตันตปิฎก ทีฆนิกาย มหาวรรค เล่ม 2 [สุมังคลวิลาสินี ภาค 2] — พิมพ์เล่ม 13",
        },
    },
    {
        "index": 14,
        "section": "dn",
        "title": {
            "en": "Suttantapiṭaka Dīghanikāya Mahāvagga vol. 2 [สุมังคลวิลาสินี ภาค 2] — printed vol. 14",
            "th": "พระสุตตันตปิฎก ทีฆนิกาย มหาวรรค เล่ม 2 [สุมังคลวิลาสินี ภาค 2] — พิมพ์เล่ม 14",
        },
    },
    {
        "index": 15,
        "section": "dn",
        "title": {
            "en": "Suttantapiṭaka Dīghanikāya Pāṭikavagga vol. 3 [สุมังคลวิลาสินี ภาค 3] — printed vol. 15",
            "th": "พระสุตตันตปิฎก ทีฆนิกาย ปาฏิกวรรค เล่ม 3 [สุมังคลวิลาสินี ภาค 3] — พิมพ์เล่ม 15",
        },
    },
    {
        "index": 16,
        "section": "dn",
        "title": {
            "en": "Suttantapiṭaka Dīghanikāya Pāṭikavagga vol. 3 [สุมังคลวิลาสินี ภาค 3] — printed vol. 16",
            "th": "พระสุตตันตปิฎก ทีฆนิกาย ปาฏิกวรรค เล่ม 3 [สุมังคลวิลาสินี ภาค 3] — พิมพ์เล่ม 16",
        },
    },
    {
        "index": 17,
        "section": "mn",
        "title": {
            "en": "Suttantapiṭaka Majjhimanikāya Mūlapaṇṇāsaka vol. 1 [ปปัญจสูดนี ภาค 1] — printed vol. 17",
            "th": "พระสุตตันตปิฎก มัชฌิมนิกาย มูลปัณณาสก์ เล่ม 1 [ปปัญจสูดนี ภาค 1] — พิมพ์เล่ม 17",
        },
    },
    {
        "index": 18,
        "section": "mn",
        "title": {
            "en": "Suttantapiṭaka Majjhimanikāya Mūlapaṇṇāsaka vol. 1 [ปปัญจสูดนี ภาค 1] — printed vol. 18",
            "th": "พระสุตตันตปิฎก มัชฌิมนิกาย มูลปัณณาสก์ เล่ม 1 [ปปัญจสูดนี ภาค 1] — พิมพ์เล่ม 18",
        },
    },
    {
        "index": 19,
        "section": "mn",
        "title": {
            "en": "Suttantapiṭaka Majjhimanikāya Mūlapaṇṇāsaka vol. 1 [ปปัญจสูดนี ภาค 1] — printed vol. 19",
            "th": "พระสุตตันตปิฎก มัชฌิมนิกาย มูลปัณณาสก์ เล่ม 1 [ปปัญจสูดนี ภาค 1] — พิมพ์เล่ม 19",
        },
    },
    {
        "index": 20,
        "section": "mn",
        "title": {
            "en": "Suttantapiṭaka Majjhimanikāya Majjhimapaṇṇāsaka vol. 2 [ปปัญจสูดนี ภาค 2] — printed vol. 20",
            "th": "พระสุตตันตปิฎก มัชฌิมนิกาย มัชฌิมปัณณาสก์ เล่ม 2 [ปปัญจสูดนี ภาค 2] — พิมพ์เล่ม 20",
        },
    },
    {
        "index": 21,
        "section": "mn",
        "title": {
            "en": "Suttantapiṭaka Majjhimanikāya Majjhimapaṇṇāsaka vol. 2 [ปปัญจสูดนี ภาค 2] — printed vol. 21",
            "th": "พระสุตตันตปิฎก มัชฌิมนิกาย มัชฌิมปัณณาสก์ เล่ม 2 [ปปัญจสูดนี ภาค 2] — พิมพ์เล่ม 21",
        },
    },
    {
        "index": 22,
        "section": "mn",
        "title": {
            "en": "Suttantapiṭaka Majjhimanikāya Uparipaṇṇāsaka vol. 3 [ปปัญจสูดนี ภาค 3] — printed vol. 22",
            "th": "พระสุตตันตปิฎก มัชฌิมนิกาย อุปริปัณณาสก์ เล่ม 3 [ปปัญจสูดนี ภาค 3] — พิมพ์เล่ม 22",
        },
    },
    {
        "index": 23,
        "section": "mn",
        "title": {
            "en": "Suttantapiṭaka Majjhimanikāya Uparipaṇṇāsaka vol. 3 [ปปัญจสูดนี ภาค 3] — printed vol. 23",
            "th": "พระสุตตันตปิฎก มัชฌิมนิกาย อุปริปัณณาสก์ เล่ม 3 [ปปัญจสูดนี ภาค 3] — พิมพ์เล่ม 23",
        },
    },
    {
        "index": 24,
        "section": "sn",
        "title": {
            "en": "Suttantapiṭaka Saṃyuttanikāya Sagāthavagga vol. 1 [สารัตถปกาสินี ภาค 1] — printed vol. 24",
            "th": "พระสุตตันตปิฎก สังยุตตนิกาย สคาถวรรค เล่ม 1 [สารัตถปกาสินี ภาค 1] — พิมพ์เล่ม 24",
        },
    },
    {
        "index": 25,
        "section": "sn",
        "title": {
            "en": "Suttantapiṭaka Saṃyuttanikāya Sagāthavagga vol. 1 [สารัตถปกาสินี ภาค 1] — printed vol. 25",
            "th": "พระสุตตันตปิฎก สังยุตตนิกาย สคาถวรรค เล่ม 1 [สารัตถปกาสินี ภาค 1] — พิมพ์เล่ม 25",
        },
    },
    {
        "index": 26,
        "section": "sn",
        "title": {
            "en": "Suttantapiṭaka Saṃyuttanikāya Nidānavagga vol. 2 [สารัตถปกาสินี ภาค 2]",
            "th": "พระสุตตันตปิฎก สังยุตตนิกาย นิทานวรรค เล่ม 2 [สารัตถปกาสินี ภาค 2]",
        },
    },
    {
        "index": 27,
        "section": "sn",
        "title": {
            "en": "Suttantapiṭaka Saṃyuttanikāya Khandhavāravagga vol. 3 [สารัตถปกาสินี ภาค 2]",
            "th": "พระสุตตันตปิฎก สังยุตตนิกาย ขันธวารวรรค เล่ม 3 [สารัตถปกาสินี ภาค 2]",
        },
    },
    {
        "index": 28,
        "section": "sn",
        "title": {
            "en": "Suttantapiṭaka Saṃyuttanikāya Saḷāyatanavagga vol. 4 [สารัตถปกาสินี ภาค 3] — printed vol. 28",
            "th": "พระสุตตันตปิฎก สังยุตตนิกาย สฬายตนวรรค เล่ม 4 [สารัตถปกาสินี ภาค 3] — พิมพ์เล่ม 28",
        },
    },
    {
        "index": 29,
        "section": "sn",
        "title": {
            "en": "Suttantapiṭaka Saṃyuttanikāya Saḷāyatanavagga vol. 4 [สารัตถปกาสินี ภาค 3] — printed vol. 29",
            "th": "พระสุตตันตปิฎก สังยุตตนิกาย สฬายตนวรรค เล่ม 4 [สารัตถปกาสินี ภาค 3] — พิมพ์เล่ม 29",
        },
    },
    {
        "index": 30,
        "section": "sn",
        "title": {
            "en": "Suttantapiṭaka Saṃyuttanikāya Mahāvāravagga vol. 5 [สารัตถปกาสินี ภาค 3] — printed vol. 30",
            "th": "พระสุตตันตปิฎก สังยุตตนิกาย มหาวารวรรค เล่ม 5 [สารัตถปกาสินี ภาค 3] — พิมพ์เล่ม 30",
        },
    },
    {
        "index": 31,
        "section": "sn",
        "title": {
            "en": "Suttantapiṭaka Saṃyuttanikāya Mahāvāravagga vol. 5 [สารัตถปกาสินี ภาค 3] — printed vol. 31",
            "th": "พระสุตตันตปิฎก สังยุตตนิกาย มหาวารวรรค เล่ม 5 [สารัตถปกาสินี ภาค 3] — พิมพ์เล่ม 31",
        },
    },
    {
        "index": 32,
        "section": "an",
        "title": {
            "en": "Suttantapiṭaka Aṅguttaranikāya Eka Nipāta vol. 1 part 1 [มโนรถปูรณี ภาค 1]",
            "th": "พระสุตตันตปิฎก อังคุตรนิกาย เอกนิบาต เล่ม 1 ภาค 1 [มโนรถปูรณี ภาค 1]",
        },
    },
    {
        "index": 33,
        "section": "an",
        "title": {
            "en": "Suttantapiṭaka Aṅguttaranikāya Eka Nipāta-Duka Nipāta vol. 1 part 2 [มโนรถปูรณี ภาค 1]",
            "th": "พระสุตตันตปิฎก อังคุตรนิกาย เอกนิบาต-ทุกนิบาต เล่ม 1 ภาค 2 [มโนรถปูรณี ภาค 1]",
        },
    },
    {
        "index": 34,
        "section": "an",
        "title": {
            "en": "Suttantapiṭaka Aṅguttaranikāya Tika Nipāta vol. 1 part 3 [มโนรถปูรณี ภาค 2]",
            "th": "พระสุตตันตปิฎก อังคุตรนิกาย ติกนิบาต เล่ม 1 ภาค 3 [มโนรถปูรณี ภาค 2]",
        },
    },
    {
        "index": 35,
        "section": "an",
        "title": {
            "en": "Suttantapiṭaka Aṅguttaranikāya Catukka Nipāta vol. 2 [มโนรถปูรณี ภาค 2]",
            "th": "พระสุตตันตปิฎก อังคุตรนิกาย จตุกนิบาต เล่ม 2 [มโนรถปูรณี ภาค 2]",
        },
    },
    {
        "index": 36,
        "section": "an",
        "title": {
            "en": "Suttantapiṭaka Aṅguttaranikāya Pañcaka–Chakka Nipāta vol. 3 [มโนรถปูรณี ภาค 2]",
            "th": "พระสุตตันตปิฎก อังคุตรนิกาย ปัญจก-ฉักกนิบาต เล่ม 3 [มโนรถปูรณี ภาค 2]",
        },
    },
    {
        "index": 37,
        "section": "an",
        "title": {
            "en": "Suttantapiṭaka Aṅguttaranikāya Sattaka–Aṭṭhaka–Navaka Nipāta vol. 4 [มโนรถปูรณี ภาค 3]",
            "th": "พระสุตตันตปิฎก อังคุตรนิกาย สัตตก-อัฏฐก-นวกนิบาต เล่ม 4 [มโนรถปูรณี ภาค 3]",
        },
    },
    {
        "index": 38,
        "section": "an",
        "title": {
            "en": "Suttantapiṭaka Aṅguttaranikāya Dasaka–Ekādasaka Nipāta vol. 5 [มโนรถปูรณี ภาค 3]",
            "th": "พระสุตตันตปิฎก อังคุตรนิกาย ทสก--เอกาทสกนิบาต เล่ม 5 [มโนรถปูรณี ภาค 3]",
        },
    },
    {
        "index": 39,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭaka Khuddakanikāya Khuddakapāṭha vol. 1 part 1 [ปรมัตถโชติกา]",
            "th": "พระสุตตันตปิฎก ขุททกนิกาย ขุททกปาฐะ เล่ม 1 ภาค 1 [ปรมัตถโชติกา]",
        },
    },
    {
        "index": 40,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭaka Khuddakanikāya Dhammapada vol. 1 part 2 [ธัมมปทัฏฐกถา ภาค 1] — printed vol. 40",
            "th": "พระสุตตันตปิฎก ขุททกนิกาย คาถาธรรมบท เล่ม 1 ภาค 2 [ธัมมปทัฏฐกถา ภาค 1] — พิมพ์เล่ม 40",
        },
    },
    {
        "index": 41,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭaka Khuddakanikāya Dhammapada vol. 1 part 2 [ธัมมปทัฏฐกถา ภาค 1] — printed vol. 41",
            "th": "พระสุตตันตปิฎก ขุททกนิกาย คาถาธรรมบท เล่ม 1 ภาค 2 [ธัมมปทัฏฐกถา ภาค 1] — พิมพ์เล่ม 41",
        },
    },
    {
        "index": 42,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭaka Khuddakanikāya Dhammapada vol. 1 part 2 [ธัมมปทัฏฐกถา ภาค 2] — printed vol. 42",
            "th": "พระสุตตันตปิฎก ขุททกนิกาย คาถาธรรมบท เล่ม 1 ภาค 2 [ธัมมปทัฏฐกถา ภาค 2] — พิมพ์เล่ม 42",
        },
    },
    {
        "index": 43,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭaka Khuddakanikāya Dhammapada vol. 1 part 2 [ธัมมปทัฏฐกถา ภาค 2] — printed vol. 43",
            "th": "พระสุตตันตปิฎก ขุททกนิกาย คาถาธรรมบท เล่ม 1 ภาค 2 [ธัมมปทัฏฐกถา ภาค 2] — พิมพ์เล่ม 43",
        },
    },
    {
        "index": 44,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭaka Khuddakanikāya Udāna vol. 1 part 3 [ปรมัตถทีปนี]",
            "th": "พระสุตตันตปิฎก ขุททกนิกาย อุทาน เล่ม 1 ภาค 3 [ปรมัตถทีปนี]",
        },
    },
    {
        "index": 45,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭaka Khuddakanikāya Itivuttaka vol. 1 part 4 [ปรมัตถทีปนี]",
            "th": "พระสุตตันตปิฎก ขุททกนิกาย อิติวุตตก เล่ม 1 ภาค 4 [ปรมัตถทีปนี]",
        },
    },
    {
        "index": 46,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭaka Khuddakanikāya Suttanipāta vol. 1 part 5 [ปรมัตถโชติกา ภาค 1]",
            "th": "พระสุตตันตปิฎก ขุททกนิกาย สุตตนิบาต เล่ม 1 ภาค 5 [ปรมัตถโชติกา ภาค 1]",
        },
    },
    {
        "index": 47,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭaka Khuddakanikāya Suttanipāta vol. 1 part 6 [ปรมัตถโชติกา ภาค 2]",
            "th": "พระสุตตันตปิฎก ขุททกนิกาย สุตตนิบาต เล่ม 1 ภาค 6 [ปรมัตถโชติกา ภาค 2]",
        },
    },
    {
        "index": 48,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭaka Khuddakanikāya Vimānavatthu vol. 2 part 1 [ปรมัตถทีปนี]",
            "th": "พระสุตตันตปิฎก ขุททกนิกาย วิมานวัตถุ เล่ม 2 ภาค 1 [ปรมัตถทีปนี]",
        },
    },
    {
        "index": 49,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭaka Khuddakanikāya Petavatthu vol. 2 part 2 [ปรมัตถทีปนี]",
            "th": "พระสุตตันตปิฎก ขุททกนิกาย เปตวัตถุ เล่ม 2 ภาค 2 [ปรมัตถทีปนี]",
        },
    },
    {
        "index": 50,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭaka Khuddakanikāya Theragāthā vol. 2 part 3 [ปรมัตถทีปนี ภาค 1] — printed vol. 50",
            "th": "พระสุตตันตปิฎก ขุททกนิกาย เถรคาถา เล่ม 2 ภาค 3 [ปรมัตถทีปนี ภาค 1] — พิมพ์เล่ม 50",
        },
    },
    {
        "index": 51,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭaka Khuddakanikāya Theragāthā vol. 2 part 3 [ปรมัตถทีปนี ภาค 1] — printed vol. 51",
            "th": "พระสุตตันตปิฎก ขุททกนิกาย เถรคาถา เล่ม 2 ภาค 3 [ปรมัตถทีปนี ภาค 1] — พิมพ์เล่ม 51",
        },
    },
    {
        "index": 52,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭaka Khuddakanikāya Theragāthā vol. 2 part 3 [ปรมัตถทีปนี ภาค 2] — printed vol. 52",
            "th": "พระสุตตันตปิฎก ขุททกนิกาย เถรคาถา เล่ม 2 ภาค 3 [ปรมัตถทีปนี ภาค 2] — พิมพ์เล่ม 52",
        },
    },
    {
        "index": 53,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭaka Khuddakanikāya Theragāthā vol. 2 part 3 [ปรมัตถทีปนี ภาค 2] — printed vol. 53",
            "th": "พระสุตตันตปิฎก ขุททกนิกาย เถรคาถา เล่ม 2 ภาค 3 [ปรมัตถทีปนี ภาค 2] — พิมพ์เล่ม 53",
        },
    },
    {
        "index": 54,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭaka Khuddakanikāya Therīgāthā vol. 2 part 4 [ปรมัตถทีปนี]",
            "th": "พระสุตตันตปิฎก ขุททกนิกาย เถรีคาถา เล่ม 2 ภาค 4 [ปรมัตถทีปนี]",
        },
    },
    {
        "index": 55,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭaka Khuddakanikāya Jātaka vol. 3 part 1 [ชาตกัฏฐกถา ภาค 1]",
            "th": "พระสุตตันตปิฎก ขุททกนิกาย ชาดก เล่ม 3 ภาค 1 [ชาตกัฏฐกถา ภาค 1]",
        },
    },
    {
        "index": 56,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭaka Khuddakanikāya Jātaka vol. 3 part 2 [ชาตกัฏฐกถา ภาค 2]",
            "th": "พระสุตตันตปิฎก ขุททกนิกาย ชาดก เล่ม 3 ภาค 2 [ชาตกัฏฐกถา ภาค 2]",
        },
    },
    {
        "index": 57,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭaka Khuddakanikāya Jātaka vol. 3 part 3 [ชาตกัฏฐกถา ภาค 3]",
            "th": "พระสุตตันตปิฎก ขุททกนิกาย ชาดก เล่ม 3 ภาค 3 [ชาตกัฏฐกถา ภาค 3]",
        },
    },
    {
        "index": 58,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭaka Khuddakanikāya Jātaka vol. 3 part 4 [ชาตกัฏฐกถา ภาค 4]",
            "th": "พระสุตตันตปิฎก ขุททกนิกาย ชาดก เล่ม 3 ภาค 4 [ชาตกัฏฐกถา ภาค 4]",
        },
    },
    {
        "index": 59,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭaka Khuddakanikāya Jātaka vol. 3 part 5 [ชาตกัฏฐกถา ภาค 5]",
            "th": "พระสุตตันตปิฎก ขุททกนิกาย ชาดก เล่ม 3 ภาค 5 [ชาตกัฏฐกถา ภาค 5]",
        },
    },
    {
        "index": 60,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭaka Khuddakanikāya Jātaka vol. 3 part 6 [ชาตกัฏฐกถา ภาค 6]",
            "th": "พระสุตตันตปิฎก ขุททกนิกาย ชาดก เล่ม 3 ภาค 6 [ชาตกัฏฐกถา ภาค 6]",
        },
    },
    {
        "index": 61,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭaka Khuddakanikāya Jātaka vol. 3 part 7 [ชาตกัฏฐกถา ภาค 7]",
            "th": "พระสุตตันตปิฎก ขุททกนิกาย ชาดก เล่ม 3 ภาค 7 [ชาตกัฏฐกถา ภาค 7]",
        },
    },
    {
        "index": 62,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭaka Khuddakanikāya Jātaka vol. 4 part 1 [ชาตกัฏฐกถา ภาค 8]",
            "th": "พระสุตตันตปิฎก ขุททกนิกาย ชาดก เล่ม 4 ภาค 1 [ชาตกัฏฐกถา ภาค 8]",
        },
    },
    {
        "index": 63,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭaka Khuddakanikāya Jātaka vol. 4 part 2 [ชาตกัฏฐกถา ภาค 9]",
            "th": "พระสุตตันตปิฎก ขุททกนิกาย ชาดก เล่ม 4 ภาค 2 [ชาตกัฏฐกถา ภาค 9]",
        },
    },
    {
        "index": 64,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭaka Khuddakanikāya Jātaka vol. 4 part 3 [ชาตกัฏฐกถา ภาค 10]",
            "th": "พระสุตตันตปิฎก ขุททกนิกาย ชาดก เล่ม 4 ภาค 3 [ชาตกัฏฐกถา ภาค 10]",
        },
    },
    {
        "index": 65,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭaka Khuddakanikāya Mahāniddesa vol. 5 [สัทธัมมปัชโชติกา] — printed vol. 65",
            "th": "พระสุตตันตปิฎก ขุททกนิกาย มหานิเทส เล่ม 5 [สัทธัมมปัชโชติกา] — พิมพ์เล่ม 65",
        },
    },
    {
        "index": 66,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭaka Khuddakanikāya Mahāniddesa vol. 5 [สัทธัมมปัชโชติกา] — printed vol. 66",
            "th": "พระสุตตันตปิฎก ขุททกนิกาย มหานิเทส เล่ม 5 [สัทธัมมปัชโชติกา] — พิมพ์เล่ม 66",
        },
    },
    {
        "index": 67,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭaka Khuddakanikāya Cūḷaniddesa vol. 6 [สัทธัมมปัชโชติกา]",
            "th": "พระสุตตันตปิฎก ขุททกนิกาย จูฬนิเทส เล่ม 6 [สัทธัมมปัชโชติกา]",
        },
    },
    {
        "index": 68,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭaka Khuddakanikāya Paṭisambhidāmagga vol. 7 part 1 [สัทธัมมปกาสินี ภาค 1]",
            "th": "พระสุตตันตปิฎก ขุททกนิกาย ปฏิสัมภิทามรรค เล่ม 7 ภาค 1 [สัทธัมมปกาสินี ภาค 1]",
        },
    },
    {
        "index": 69,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭaka Khuddakanikāya Paṭisambhidāmagga vol. 7 part 2 [สัทธัมมปกาสินี ภาค 2]",
            "th": "พระสุตตันตปิฎก ขุททกนิกาย ปฏิสัมภิทามรรค เล่ม 7 ภาค 2 [สัทธัมมปกาสินี ภาค 2]",
        },
    },
    {
        "index": 70,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭaka Khuddakanikāya Apadāna vol. 8 [วิสุทธชนวิลาสินี ภาค 1] — printed vol. 70",
            "th": "พระสุตตันตปิฎก ขุททกนิกาย อปทาน เล่ม 8 [วิสุทธชนวิลาสินี ภาค 1] — พิมพ์เล่ม 70",
        },
    },
    {
        "index": 71,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭaka Khuddakanikāya Apadāna vol. 8 [วิสุทธชนวิลาสินี ภาค 1] — printed vol. 71",
            "th": "พระสุตตันตปิฎก ขุททกนิกาย อปทาน เล่ม 8 [วิสุทธชนวิลาสินี ภาค 1] — พิมพ์เล่ม 71",
        },
    },
    {
        "index": 72,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭaka Khuddakanikāya Apadāna vol. 9 part 1 [วิสุทธชนวิลาสินี ภาค 2]",
            "th": "พระสุตตันตปิฎก ขุททกนิกาย อปทาน เล่ม 9 ภาค 1 [วิสุทธชนวิลาสินี ภาค 2]",
        },
    },
    {
        "index": 73,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭaka Khuddakanikāya Buddhavaṃsa vol. 9 part 2 [มธุรัตถวิลาสินี]",
            "th": "พระสุตตันตปิฎก ขุททกนิกาย พุทธวงศ์ เล่ม 9 ภาค 2 [มธุรัตถวิลาสินี]",
        },
    },
    {
        "index": 74,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭaka Khuddakanikāya Cariyāpiṭaka vol. 9 part 3 [ปรมัตถทีปนี]",
            "th": "พระสุตตันตปิฎก ขุททกนิกาย จริยาปิฎก เล่ม 9 ภาค 3 [ปรมัตถทีปนี]",
        },
    },
    {
        "index": 75,
        "section": "abh",
        "title": {
            "en": "Abhidhammapiṭaka Dhammasaṅgaṇī vol. 1 [อัฏฐสาลินี] — printed vol. 75",
            "th": "พระอภิธรรมปิฎก ธรรมสังคณี เล่ม 1 [อัฏฐสาลินี] — พิมพ์เล่ม 75",
        },
    },
    {
        "index": 76,
        "section": "abh",
        "title": {
            "en": "Abhidhammapiṭaka Dhammasaṅgaṇī vol. 1 [อัฏฐสาลินี] — printed vol. 76",
            "th": "พระอภิธรรมปิฎก ธรรมสังคณี เล่ม 1 [อัฏฐสาลินี] — พิมพ์เล่ม 76",
        },
    },
    {
        "index": 77,
        "section": "abh",
        "title": {
            "en": "Abhidhammapiṭaka Vibhaṅga vol. 2 [สัมโมหวิโนทนี] — printed vol. 77",
            "th": "พระอภิธรรมปิฎก วิภังค์ เล่ม 2 [สัมโมหวิโนทนี] — พิมพ์เล่ม 77",
        },
    },
    {
        "index": 78,
        "section": "abh",
        "title": {
            "en": "Abhidhammapiṭaka Vibhaṅga vol. 2 [สัมโมหวิโนทนี] — printed vol. 78",
            "th": "พระอภิธรรมปิฎก วิภังค์ เล่ม 2 [สัมโมหวิโนทนี] — พิมพ์เล่ม 78",
        },
    },
    {
        "index": 79,
        "section": "abh",
        "title": {
            "en": "Abhidhammapiṭaka Dhātukathā–Puggalapaññatti vol. 3 [ปัญจปกรณ์]",
            "th": "พระอภิธรรมปิฎก ธาตุกถา--บุคคลบัญญัติ เล่ม 3 [ปัญจปกรณ์]",
        },
    },
    {
        "index": 80,
        "section": "abh",
        "title": {
            "en": "Abhidhammapiṭaka Kathāvatthu vol. 4 [ปัญจปกรณ์] — printed vol. 80",
            "th": "พระอภิธรรมปิฎก กถาวัตถุ เล่ม 4 [ปัญจปกรณ์] — พิมพ์เล่ม 80",
        },
    },
    {
        "index": 81,
        "section": "abh",
        "title": {
            "en": "Abhidhammapiṭaka Kathāvatthu vol. 4 [ปัญจปกรณ์] — printed vol. 81",
            "th": "พระอภิธรรมปิฎก กถาวัตถุ เล่ม 4 [ปัญจปกรณ์] — พิมพ์เล่ม 81",
        },
    },
    {
        "index": 82,
        "section": "abh",
        "title": {
            "en": "Abhidhammapiṭaka Yamaka vol. 5 part 1 [ปัญจปกรณ์] — printed vol. 82",
            "th": "พระอภิธรรมปิฎก ยมก เล่ม 5 ภาค 1 [ปัญจปกรณ์] — พิมพ์เล่ม 82",
        },
    },
    {
        "index": 83,
        "section": "abh",
        "title": {
            "en": "Abhidhammapiṭaka Yamaka vol. 5 part 1 [ปัญจปกรณ์] — printed vol. 83",
            "th": "พระอภิธรรมปิฎก ยมก เล่ม 5 ภาค 1 [ปัญจปกรณ์] — พิมพ์เล่ม 83",
        },
    },
    {
        "index": 84,
        "section": "abh",
        "title": {
            "en": "Abhidhammapiṭaka Yamaka vol. 6 part 2 [ปัญจปกรณ์]",
            "th": "พระอภิธรรมปิฎก ยมก เล่ม 6 ภาค 2 [ปัญจปกรณ์]",
        },
    },
    {
        "index": 85,
        "section": "abh",
        "title": {
            "en": "Abhidhammapiṭaka Paṭṭhāna vol. 7 [ปัญจปกรณ์] — printed vol. 85",
            "th": "พระอภิธรรมปิฎก ปัฏฐาน เล่ม 7 [ปัญจปกรณ์] — พิมพ์เล่ม 85",
        },
    },
    {
        "index": 86,
        "section": "abh",
        "title": {
            "en": "Abhidhammapiṭaka Paṭṭhāna vol. 7 [ปัญจปกรณ์] — printed vol. 86",
            "th": "พระอภิธรรมปิฎก ปัฏฐาน เล่ม 7 [ปัญจปกรณ์] — พิมพ์เล่ม 86",
        },
    },
    {
        "index": 87,
        "section": "abh",
        "title": {
            "en": "Abhidhammapiṭaka Paṭṭhāna vol. 7 [ปัญจปกรณ์] — printed vol. 87",
            "th": "พระอภิธรรมปิฎก ปัฏฐาน เล่ม 7 [ปัญจปกรณ์] — พิมพ์เล่ม 87",
        },
    },
    {
        "index": 88,
        "section": "abh",
        "title": {
            "en": "Abhidhammapiṭaka Paṭṭhāna vol. 7 [ปัญจปกรณ์] — printed vol. 88",
            "th": "พระอภิธรรมปิฎก ปัฏฐาน เล่ม 7 [ปัญจปกรณ์] — พิมพ์เล่ม 88",
        },
    },
    {
        "index": 89,
        "section": "abh",
        "title": {
            "en": "Abhidhammapiṭaka Paṭṭhāna vol. 7 [ปัญจปกรณ์] — printed vol. 89",
            "th": "พระอภิธรรมปิฎก ปัฏฐาน เล่ม 7 [ปัญจปกรณ์] — พิมพ์เล่ม 89",
        },
    },
    {
        "index": 90,
        "section": "abh",
        "title": {
            "en": "Abhidhammapiṭaka Paṭṭhāna vol. 7 [ปัญจปกรณ์] — printed vol. 90",
            "th": "พระอภิธรรมปิฎก ปัฏฐาน เล่ม 7 [ปัญจปกรณ์] — พิมพ์เล่ม 90",
        },
    },
    {
        "index": 91,
        "section": "abh",
        "title": {
            "en": "Abhidhammapiṭaka Paṭṭhāna vol. 7 [ปัญจปกรณ์] — printed vol. 91",
            "th": "พระอภิธรรมปิฎก ปัฏฐาน เล่ม 7 [ปัญจปกรณ์] — พิมพ์เล่ม 91",
        },
    },
]

# === LAO_PALI_VOLUMES ===
# hall edition code(s): lao/pali2556
# source: tipitaka-catalog/catalog/content/lao-pali-lao.tex
# count: 45
# Vinaya is 5 vols (Chaṭṭha-like), not 8; AN=6, KN=11, Abhidhamma Yamaka 3 + Paṭṭhāna 5.
LAO_PALI_VOLUMES = [
    {
        "index": 1,
        "section": "vin",
        "title": {
            "en": "Pārājikapāli",
            "th": "ปาราชิกปาลิ",
        },
    },
    {
        "index": 2,
        "section": "vin",
        "title": {
            "en": "Pācittiyapāli",
            "th": "ปาจิตฺติยปาลิ",
        },
    },
    {
        "index": 3,
        "section": "vin",
        "title": {
            "en": "Mahāvaggapāli",
            "th": "มหาวคฺคปาลิ",
        },
    },
    {
        "index": 4,
        "section": "vin",
        "title": {
            "en": "Cūḷavaggapāli",
            "th": "จูฬวคฺคปาลิ",
        },
    },
    {
        "index": 5,
        "section": "vin",
        "title": {
            "en": "Parivārapāli",
            "th": "ปริวารปาลิ",
        },
    },
    {
        "index": 6,
        "section": "dn",
        "title": {
            "en": "Sīlakkhandhavaggapāli",
            "th": "สีลกฺขนฺธวคฺคปาลิ",
        },
    },
    {
        "index": 7,
        "section": "dn",
        "title": {
            "en": "Mahāvaggapāli",
            "th": "มหาวคฺคปาลิ",
        },
    },
    {
        "index": 8,
        "section": "dn",
        "title": {
            "en": "Pāthikavaggapāli",
            "th": "ปาถิกวคฺคปาลิ",
        },
    },
    {
        "index": 9,
        "section": "mn",
        "title": {
            "en": "Mūlapaṇṇāsakapāli",
            "th": "มูลปณฺณาสกปาลิ",
        },
    },
    {
        "index": 10,
        "section": "mn",
        "title": {
            "en": "Majjhimapaṇṇāsakapāli",
            "th": "มชฺฌิมปณฺณาสกปาลิ",
        },
    },
    {
        "index": 11,
        "section": "mn",
        "title": {
            "en": "Uparipaṇṇāsakapāli",
            "th": "อุปริปณฺณาสกปาลิ",
        },
    },
    {
        "index": 12,
        "section": "sn",
        "title": {
            "en": "Sagāthāvaggasaṃyuttapāli",
            "th": "สคาถาวคฺคสํยุตฺตปาลิ",
        },
    },
    {
        "index": 13,
        "section": "sn",
        "title": {
            "en": "Nidānavaggasaṃyuttapāli",
            "th": "นิทานวคฺคสํยุตฺตปาลิ",
        },
    },
    {
        "index": 14,
        "section": "sn",
        "title": {
            "en": "Khandhavāravaggasaṃyuttapāli",
            "th": "ขนฺธวารวคฺคสํยุตฺตปาลิ",
        },
    },
    {
        "index": 15,
        "section": "sn",
        "title": {
            "en": "Saḷāyatanavaggasaṃyuttapāli",
            "th": "สฬายตนวคฺคสํยุตฺตปาลิ",
        },
    },
    {
        "index": 16,
        "section": "sn",
        "title": {
            "en": "Mahāvaggasaṃyuttapāli",
            "th": "มหาวคฺคสํยุตฺตปาลิ",
        },
    },
    {
        "index": 17,
        "section": "an",
        "title": {
            "en": "Ekaka-Duka-Tikanipātapāli",
            "th": "เอกก-ทุก-ติกนิปาตปาลิ",
        },
    },
    {
        "index": 18,
        "section": "an",
        "title": {
            "en": "Catukkanipātapāli",
            "th": "จตุกฺกนิปาตปาลิ",
        },
    },
    {
        "index": 19,
        "section": "an",
        "title": {
            "en": "Pañcakanipātapāli",
            "th": "ปญฺจกนิปาตปาลิ",
        },
    },
    {
        "index": 20,
        "section": "an",
        "title": {
            "en": "Chakka-Sattakanipātapāli",
            "th": "ฉกฺก-สตฺตกนิปาตปาลิ",
        },
    },
    {
        "index": 21,
        "section": "an",
        "title": {
            "en": "Aṭṭhaka-Navakanipātapāli",
            "th": "อฏฺฐก-นวกนิปาตปาลิ",
        },
    },
    {
        "index": 22,
        "section": "an",
        "title": {
            "en": "Dasaka-Ekādasakanipātapāli",
            "th": "ทสก-เอกาทสกนิปาตปาลิ",
        },
    },
    {
        "index": 23,
        "section": "kn",
        "title": {
            "en": "Khuddakapāṭha · Dhammapada · Udānapāli",
            "th": "ขุทฺทกปาฐ · ธมฺมปท · อุทานปาลิ",
        },
    },
    {
        "index": 24,
        "section": "kn",
        "title": {
            "en": "Itivuttaka · Suttanipātapāli",
            "th": "อิติวุตฺตก · สุตฺตนิปาตปาลิ",
        },
    },
    {
        "index": 25,
        "section": "kn",
        "title": {
            "en": "Vimānavatthu · Petavatthupāli",
            "th": "วิมานวตฺถุ · เปตวตฺถุปาลิ",
        },
    },
    {
        "index": 26,
        "section": "kn",
        "title": {
            "en": "Theragāthā · Therīgāthāpāli",
            "th": "เถรคาถา · เถรีคาถาปาลิ",
        },
    },
    {
        "index": 27,
        "section": "kn",
        "title": {
            "en": "Jātakapāli — paṭhamo bhāgo",
            "th": "ชาตกปาลิ -- ปฐโม ภาโค",
        },
    },
    {
        "index": 28,
        "section": "kn",
        "title": {
            "en": "Jātakapāli — dutiyo bhāgo",
            "th": "ชาตกปาลิ -- ทุติโย ภาโค",
        },
    },
    {
        "index": 29,
        "section": "kn",
        "title": {
            "en": "Mahāniddesapāli",
            "th": "มหานิทฺเทสปาลิ",
        },
    },
    {
        "index": 30,
        "section": "kn",
        "title": {
            "en": "Cūḷaniddesapāli",
            "th": "จูฬนิทฺเทสปาลิ",
        },
    },
    {
        "index": 31,
        "section": "kn",
        "title": {
            "en": "Paṭisambhidāmaggapāli",
            "th": "ปฏิสมฺภิทามคฺคปาลิ",
        },
    },
    {
        "index": 32,
        "section": "kn",
        "title": {
            "en": "Apadānapāli — paṭhamo bhāgo",
            "th": "อปทานปาลิ -- ปฐโม ภาโค",
        },
    },
    {
        "index": 33,
        "section": "kn",
        "title": {
            "en": "Apadānapāli — dutiyo bhāgo · Buddhavamsa · Cariyāpiṭakapāli",
            "th": "อปทานปาลิ -- ทุติโย ภาโค · พุทฺธวํส · จริยาปิฏกปาลิ",
        },
    },
    {
        "index": 34,
        "section": "abh",
        "title": {
            "en": "Dhammasaṅgaṇīpāli",
            "th": "ธมฺมสงฺคณีปาลิ",
        },
    },
    {
        "index": 35,
        "section": "abh",
        "title": {
            "en": "Vibhaṅgapāli",
            "th": "วิภงฺคปาลิ",
        },
    },
    {
        "index": 36,
        "section": "abh",
        "title": {
            "en": "Dhātukathā · Puggalapaññattipāli",
            "th": "ธาตุกถา · ปุคฺคลปญฺญตฺติปาลิ",
        },
    },
    {
        "index": 37,
        "section": "abh",
        "title": {
            "en": "Kathāvatthupāli",
            "th": "กถาวตฺถุปาลิ",
        },
    },
    {
        "index": 38,
        "section": "abh",
        "title": {
            "en": "Yamakapāli — paṭhamo bhāgo",
            "th": "ยมกปาลิ -- ปฐโม ภาโค",
        },
    },
    {
        "index": 39,
        "section": "abh",
        "title": {
            "en": "Yamakapāli — dutiyo bhāgo",
            "th": "ยมกปาลิ -- ทุติโย ภาโค",
        },
    },
    {
        "index": 40,
        "section": "abh",
        "title": {
            "en": "Yamakapāli — tatiyo bhāgo",
            "th": "ยมกปาลิ -- ตติโย ภาโค",
        },
    },
    {
        "index": 41,
        "section": "abh",
        "title": {
            "en": "Paṭṭhānapāli — paṭhamo bhāgo",
            "th": "ปฏฺฐานปาลิ -- ปฐโม ภาโค",
        },
    },
    {
        "index": 42,
        "section": "abh",
        "title": {
            "en": "Paṭṭhānapāli — dutiyo bhāgo",
            "th": "ปฏฺฐานปาลิ -- ทุติโย ภาโค",
        },
    },
    {
        "index": 43,
        "section": "abh",
        "title": {
            "en": "Paṭṭhānapāli — tatiyo bhāgo",
            "th": "ปฏฺฐานปาลิ -- ตติโย ภาโค",
        },
    },
    {
        "index": 44,
        "section": "abh",
        "title": {
            "en": "Paṭṭhānapāli — catuttho bhāgo",
            "th": "ปฏฺฐานปาลิ -- จตุตฺโถ ภาโค",
        },
    },
    {
        "index": 45,
        "section": "abh",
        "title": {
            "en": "Paṭṭhānapāli — pañcamo bhāgo",
            "th": "ปฏฺฐานปาลิ -- ปญฺจโม ภาโค",
        },
    },
]

# === NLD_PALI_VOLUMES ===
# hall edition code(s): nld/pali2560
# source: tipitaka-catalog/catalog/content/nld-pali-devanagari.tex
# count: 41
# 41 vols; en from IAST in generator script.
NLD_PALI_VOLUMES = [
    {
        "index": 1,
        "section": "vin",
        "title": {
            "en": "Mahāvaggapāli",
            "th": "มหาวคฺคปาลิ",
        },
    },
    {
        "index": 2,
        "section": "vin",
        "title": {
            "en": "Cūḷavaggapāli",
            "th": "จุลฺลวคฺคปาลิ",
        },
    },
    {
        "index": 3,
        "section": "vin",
        "title": {
            "en": "Pārājikapāli",
            "th": "ปาราชิกปาลิ · ภิกฺขุวิภงฺค",
        },
    },
    {
        "index": 4,
        "section": "vin",
        "title": {
            "en": "Pācittiyapāli",
            "th": "ปาจิตฺติยปาลิ · ภิกฺขุ-ภิกฺขุนีวิภงฺค",
        },
    },
    {
        "index": 5,
        "section": "vin",
        "title": {
            "en": "Parivārapāli",
            "th": "ปริวารปาลิ",
        },
    },
    {
        "index": 6,
        "section": "dn",
        "title": {
            "en": "Dīghanikāya Sīlakkhandhavagga",
            "th": "ทีฆนิกาย สีลกฺขนฺธวคฺค",
        },
    },
    {
        "index": 7,
        "section": "dn",
        "title": {
            "en": "Dīghanikāya Mahāvagga",
            "th": "ทีฆนิกาย มหาวคฺค",
        },
    },
    {
        "index": 8,
        "section": "dn",
        "title": {
            "en": "Dīghanikāya Pāṭhikavagga",
            "th": "ทีฆนิกาย ปาฏิกวคฺค",
        },
    },
    {
        "index": 9,
        "section": "mn",
        "title": {
            "en": "Majjhimanikāya Mūlapaṇṇāsaka",
            "th": "มชฺฌิมนิกาย มูลปณฺณาสก",
        },
    },
    {
        "index": 10,
        "section": "mn",
        "title": {
            "en": "Majjhimanikāya Majjhimapaṇṇāsaka",
            "th": "มชฺฌิมนิกาย มชฺฌิมปณฺณาสก",
        },
    },
    {
        "index": 11,
        "section": "mn",
        "title": {
            "en": "Majjhimanikāya Uparipaṇṇāsaka",
            "th": "มชฺฌิมนิกาย อุปริปณฺณาสก",
        },
    },
    {
        "index": 12,
        "section": "sn",
        "title": {
            "en": "Saṃyuttanikāya Sagāthāvagga",
            "th": "สํยุตฺตนิกาย สคาถาวคฺค",
        },
    },
    {
        "index": 13,
        "section": "sn",
        "title": {
            "en": "Saṃyuttanikāya Nidānavagga · Khandhavagga",
            "th": "นิทานวคฺค · ขนฺธวคฺค",
        },
    },
    {
        "index": 14,
        "section": "sn",
        "title": {
            "en": "Saṃyuttanikāya Saḷāyatanavagga",
            "th": "สฬายตนวคฺค",
        },
    },
    {
        "index": 15,
        "section": "sn",
        "title": {
            "en": "Saṃyuttanikāya Mahāvagga",
            "th": "สํยุตฺตนิกาย มหาวคฺค",
        },
    },
    {
        "index": 16,
        "section": "an",
        "title": {
            "en": "Aṅguttaranikāya Ekaka- Duka- Tikanipāta",
            "th": "เอกก-ทุก-ติกนิปาต",
        },
    },
    {
        "index": 17,
        "section": "an",
        "title": {
            "en": "Aṅguttaranikāya Catukka- Pañcakanipāta",
            "th": "จตุกฺก-ปญฺจกนิปาต",
        },
    },
    {
        "index": 18,
        "section": "an",
        "title": {
            "en": "Aṅguttaranikāya Chakka- Sattaka- Aṭhakanipāta",
            "th": "ฉกฺก-สตฺตก-อฏฺฐกนิปาต",
        },
    },
    {
        "index": 19,
        "section": "an",
        "title": {
            "en": "Aṅguttaranikāya Navaka- Dasaka- Ekādasakanipāta",
            "th": "นวก-ทสก-เอกาทสกนิปาต",
        },
    },
    {
        "index": 20,
        "section": "kn",
        "title": {
            "en": "Khuddakapāṭha · Dhammapada · Udāna · Itivuttaka · Suttanipāta",
            "th": "ขุทฺทกปาฐ · ธมฺมปท · อุทาน · อิติวุตฺตก · สุตฺตนิปาต",
        },
    },
    {
        "index": 21,
        "section": "kn",
        "title": {
            "en": "Vimānavatthu · Petavatthu · Theragāthā · Therīgāthā",
            "th": "วิมานวตฺถุ · เปตวตฺถุ · เถรคาถา · เถรีคาถา",
        },
    },
    {
        "index": 22,
        "section": "kn",
        "title": {
            "en": "Jātakapāli (paṭhamo Bhāgo)",
            "th": "ชาตกปาลิ -- ปฐโม ภาโค",
        },
    },
    {
        "index": 23,
        "section": "kn",
        "title": {
            "en": "Jātakapāli (dutiyo Bhāgo)",
            "th": "ชาตกปาลิ -- ทุติโย ภาโค",
        },
    },
    {
        "index": 24,
        "section": "kn",
        "title": {
            "en": "Mahāniddesa",
            "th": "มหานิทฺเทส",
        },
    },
    {
        "index": 25,
        "section": "kn",
        "title": {
            "en": "Cūlaniddesa",
            "th": "จุลฺลนิทฺเทส",
        },
    },
    {
        "index": 26,
        "section": "kn",
        "title": {
            "en": "Paṭisambhidāmagga",
            "th": "ปฏิสมฺภิทามคฺค",
        },
    },
    {
        "index": 27,
        "section": "kn",
        "title": {
            "en": "Apadānapāli (paṭhamo Bhāgo)",
            "th": "อปทานปาลิ -- ปฐโม ภาโค",
        },
    },
    {
        "index": 28,
        "section": "kn",
        "title": {
            "en": "Apadānapāli (dutiyo Bhāgo) · Buddhavaṃsa · Cariyāpiṭaka",
            "th": "อปทานปาลิ -- ทุติโย ภาโค · พุทฺธวํส · จริยาปิฏก",
        },
    },
    {
        "index": 29,
        "section": "abh",
        "title": {
            "en": "Dhammasaṅgaṇī",
            "th": "ธมฺมสงฺคณี",
        },
    },
    {
        "index": 30,
        "section": "abh",
        "title": {
            "en": "Vibhaṅga",
            "th": "วิภงฺค",
        },
    },
    {
        "index": 31,
        "section": "abh",
        "title": {
            "en": "Dhātukathā · Puggalapaññatti",
            "th": "ธาตุกถา · ปุคฺคลปญฺญตฺติ",
        },
    },
    {
        "index": 32,
        "section": "abh",
        "title": {
            "en": "Kathāvatthu (paṭhamo Bhāgo)",
            "th": "กถาวตฺถุ -- ปฐโม ภาโค",
        },
    },
    {
        "index": 33,
        "section": "abh",
        "title": {
            "en": "Kathāvatthu (dutiyo Bhāgo)",
            "th": "กถาวตฺถุ -- ทุติโย ภาโค",
        },
    },
    {
        "index": 34,
        "section": "abh",
        "title": {
            "en": "Yamaka (paṭhamo Bhāgo)",
            "th": "ยมก -- ปฐโม ภาโค",
        },
    },
    {
        "index": 35,
        "section": "abh",
        "title": {
            "en": "Yamaka (dutiyo Bhāgo)",
            "th": "ยมก -- ทุติโย ภาโค",
        },
    },
    {
        "index": 36,
        "section": "abh",
        "title": {
            "en": "Paṭṭhāna (paṭhamo Bhāgo)",
            "th": "ปฏฺฐาน -- ปฐโม ภาโค",
        },
    },
    {
        "index": 37,
        "section": "abh",
        "title": {
            "en": "Paṭṭhāna (dutiyo Bhāgo)",
            "th": "ปฏฺฐาน -- ทุติโย ภาโค",
        },
    },
    {
        "index": 38,
        "section": "abh",
        "title": {
            "en": "Paṭṭhāna (tatiyo Bhāgo)",
            "th": "ปฏฺฐาน -- ตติโย ภาโค",
        },
    },
    {
        "index": 39,
        "section": "abh",
        "title": {
            "en": "Paṭṭhāna (catuttho Bhāgo)",
            "th": "ปฏฺฐาน -- จตุตฺโถ ภาโค",
        },
    },
    {
        "index": 40,
        "section": "abh",
        "title": {
            "en": "Paṭṭhāna (pañcamo Bhāgo)",
            "th": "ปฏฺฐาน -- ปญฺจโม ภาโค",
        },
    },
    {
        "index": 41,
        "section": "abh",
        "title": {
            "en": "Paṭṭhāna (chaṭṭhamo Bhāgo)",
            "th": "ปฏฺฐาน -- ฉฏฺฐโม ภาโค",
        },
    },
]

# === SLK_PALI_VOLUMES ===
# hall edition code(s): bj/pali2499
# source: tipitaka-catalog/catalog/content/slk-pali-sinhala.tex
# count: 57
# 57 physical volumes (cover numbers 1–52 with splits). th = Thai-script Pāli from TeX.
SLK_PALI_VOLUMES = [
    {
        "index": 1,
        "section": "vin",
        "title": {
            "en": "Pārājikapāli",
            "th": "ปาราชิกปาลิ",
        },
    },
    {
        "index": 2,
        "section": "vin",
        "title": {
            "en": "Pācittiyapāli 1",
            "th": "ปาจิตฺติยปาลิ 1",
        },
    },
    {
        "index": 3,
        "section": "vin",
        "title": {
            "en": "Pācittiyapāli 2",
            "th": "ปาจิตฺติยปาลิ 2",
        },
    },
    {
        "index": 4,
        "section": "vin",
        "title": {
            "en": "Mahāvaggapāli 1",
            "th": "มหาวคฺคปาลิ 1",
        },
    },
    {
        "index": 5,
        "section": "vin",
        "title": {
            "en": "Mahāvaggapāli 2",
            "th": "มหาวคฺคปาลิ 2",
        },
    },
    {
        "index": 6,
        "section": "vin",
        "title": {
            "en": "Cullavaggapāli 1",
            "th": "จุลฺลวคฺคปาลิ 1",
        },
    },
    {
        "index": 7,
        "section": "vin",
        "title": {
            "en": "Cullavaggapāli 2",
            "th": "จุลฺลวคฺคปาลิ 2",
        },
    },
    {
        "index": 8,
        "section": "vin",
        "title": {
            "en": "Parivārapāli 1",
            "th": "ปริวารปาลิ 1",
        },
    },
    {
        "index": 9,
        "section": "vin",
        "title": {
            "en": "Parivārapāli 2",
            "th": "ปริวารปาลิ 2",
        },
    },
    {
        "index": 10,
        "section": "dn",
        "title": {
            "en": "Dīghanikāya 1",
            "th": "ทีฆนิกาย 1",
        },
    },
    {
        "index": 11,
        "section": "dn",
        "title": {
            "en": "Dīghanikāya 2",
            "th": "ทีฆนิกาย 2",
        },
    },
    {
        "index": 12,
        "section": "dn",
        "title": {
            "en": "Dīghanikāya 3",
            "th": "ทีฆนิกาย 3",
        },
    },
    {
        "index": 13,
        "section": "mn",
        "title": {
            "en": "Majjhimanikāya 1",
            "th": "มชฺฌิมนิกาย 1",
        },
    },
    {
        "index": 14,
        "section": "mn",
        "title": {
            "en": "Majjhimanikāya 2",
            "th": "มชฺฌิมนิกาย 2",
        },
    },
    {
        "index": 15,
        "section": "mn",
        "title": {
            "en": "Majjhimanikāya 3",
            "th": "มชฺฌิมนิกาย 3",
        },
    },
    {
        "index": 16,
        "section": "sn",
        "title": {
            "en": "Sṃyuttanikāya 1",
            "th": "สํยุตฺตนิกาย 1",
        },
    },
    {
        "index": 17,
        "section": "sn",
        "title": {
            "en": "Sṃyuttanikāya 2",
            "th": "สํยุตฺตนิกาย 2",
        },
    },
    {
        "index": 18,
        "section": "sn",
        "title": {
            "en": "Sṃyuttanikāya 3",
            "th": "สํยุตฺตนิกาย 3",
        },
    },
    {
        "index": 19,
        "section": "sn",
        "title": {
            "en": "Sṃyuttanikāya 4",
            "th": "สํยุตฺตนิกาย 4",
        },
    },
    {
        "index": 20,
        "section": "sn",
        "title": {
            "en": "Sṃyuttanikāya 5-1",
            "th": "สํยุตฺตนิกาย 5-1",
        },
    },
    {
        "index": 21,
        "section": "sn",
        "title": {
            "en": "Sṃyuttanikāya 5-2",
            "th": "สํยุตฺตนิกาย 5-2",
        },
    },
    {
        "index": 22,
        "section": "an",
        "title": {
            "en": "Aṅguttaranikāya 1",
            "th": "องฺคุตฺตรนิกาย 1",
        },
    },
    {
        "index": 23,
        "section": "an",
        "title": {
            "en": "Aṅguttaranikāya 2",
            "th": "องฺคุตฺตรนิกาย 2",
        },
    },
    {
        "index": 24,
        "section": "an",
        "title": {
            "en": "Aṅguttaranikāya 3",
            "th": "องฺคุตฺตรนิกาย 3",
        },
    },
    {
        "index": 25,
        "section": "an",
        "title": {
            "en": "Aṅguttaranikāya 4",
            "th": "องฺคุตฺตรนิกาย 4",
        },
    },
    {
        "index": 26,
        "section": "an",
        "title": {
            "en": "Aṅguttaranikāya 5",
            "th": "องฺคุตฺตรนิกาย 5",
        },
    },
    {
        "index": 27,
        "section": "an",
        "title": {
            "en": "Aṅguttaranikāya 6",
            "th": "องฺคุตฺตรนิกาย 6",
        },
    },
    {
        "index": 28,
        "section": "kn",
        "title": {
            "en": "Khuddakapāṭha-dhammapada-udāna-itivuttakapāli",
            "th": "ขุทฺทกปาฐ-ธมฺมปท-อุทาน-อิติวุตฺตกปาลิ",
        },
    },
    {
        "index": 29,
        "section": "kn",
        "title": {
            "en": "Suttanipātapāli",
            "th": "สุตฺตนิปาตปาลิ",
        },
    },
    {
        "index": 30,
        "section": "kn",
        "title": {
            "en": "Vimānavatthu-petavatthupāli",
            "th": "วิมานวตฺถุ-เปตวตฺถุปาลิ",
        },
    },
    {
        "index": 31,
        "section": "kn",
        "title": {
            "en": "Thera-therīgāthāpāli",
            "th": "เถร-เถรีคาถาปาลิ",
        },
    },
    {
        "index": 32,
        "section": "kn",
        "title": {
            "en": "Jātakapāli 1",
            "th": "ชาตกปาลิ 1",
        },
    },
    {
        "index": 33,
        "section": "kn",
        "title": {
            "en": "Jātakapāli 2",
            "th": "ชาตกปาลิ 2",
        },
    },
    {
        "index": 34,
        "section": "kn",
        "title": {
            "en": "Jātakapāli 3",
            "th": "ชาตกปาลิ 3",
        },
    },
    {
        "index": 35,
        "section": "kn",
        "title": {
            "en": "Mahāniddesapāli",
            "th": "มหานิทฺเทสปาลิ",
        },
    },
    {
        "index": 36,
        "section": "kn",
        "title": {
            "en": "Cūḷaniddesapāli",
            "th": "จูฬนิทฺเทสปาลิ",
        },
    },
    {
        "index": 37,
        "section": "kn",
        "title": {
            "en": "Paṭisambhidāmaggapāli 1",
            "th": "ปฏิสมฺภิทามคฺคปาลิ 1",
        },
    },
    {
        "index": 38,
        "section": "kn",
        "title": {
            "en": "Paṭisambhidāmaggapāli 2",
            "th": "ปฏิสมฺภิทามคฺคปาลิ 2",
        },
    },
    {
        "index": 39,
        "section": "kn",
        "title": {
            "en": "Apadānapāli 1",
            "th": "อปทานปาลิ 1",
        },
    },
    {
        "index": 40,
        "section": "kn",
        "title": {
            "en": "Apadānapāli 2-1",
            "th": "อปทานปาลิ 2-1",
        },
    },
    {
        "index": 41,
        "section": "kn",
        "title": {
            "en": "Apadānapāli 2-2",
            "th": "อปทานปาลิ 2-2",
        },
    },
    {
        "index": 42,
        "section": "kn",
        "title": {
            "en": "Buddhavṃsa-cariyāpiṭakapāli",
            "th": "พุทฺธวํส-จริยาปิฏกปาลิ",
        },
    },
    {
        "index": 43,
        "section": "kn",
        "title": {
            "en": "Nettippakaraṇapāli",
            "th": "เนตฺติปฺปกรณปาลิ",
        },
    },
    {
        "index": 44,
        "section": "kn",
        "title": {
            "en": "Peṭakopadesapāli",
            "th": "เปฏโกปเทสปาลิ",
        },
    },
    {
        "index": 45,
        "section": "abh",
        "title": {
            "en": "Dhammasaṅgaṇī",
            "th": "ธมฺมสงฺคณี",
        },
    },
    {
        "index": 46,
        "section": "abh",
        "title": {
            "en": "Vibhaṅga 1",
            "th": "วิภงฺค 1",
        },
    },
    {
        "index": 47,
        "section": "abh",
        "title": {
            "en": "Vibhaṅga 2",
            "th": "วิภงฺค 2",
        },
    },
    {
        "index": 48,
        "section": "abh",
        "title": {
            "en": "Kathāvatthu 1",
            "th": "กถาวตฺถุ 1",
        },
    },
    {
        "index": 49,
        "section": "abh",
        "title": {
            "en": "Kathāvatthu 2",
            "th": "กถาวตฺถุ 2",
        },
    },
    {
        "index": 50,
        "section": "abh",
        "title": {
            "en": "Kathāvatthu 3",
            "th": "กถาวตฺถุ 3",
        },
    },
    {
        "index": 51,
        "section": "abh",
        "title": {
            "en": "Dhātukathā-puggalapaññatti",
            "th": "ธาตุกถา-ปุคฺคลปญฺญตฺติ",
        },
    },
    {
        "index": 52,
        "section": "abh",
        "title": {
            "en": "Yamaka 1",
            "th": "ยมก 1",
        },
    },
    {
        "index": 53,
        "section": "abh",
        "title": {
            "en": "Yamaka 2-1",
            "th": "ยมก 2-1",
        },
    },
    {
        "index": 54,
        "section": "abh",
        "title": {
            "en": "Yamaka 2-2",
            "th": "ยมก 2-2",
        },
    },
    {
        "index": 55,
        "section": "abh",
        "title": {
            "en": "Paṭṭhāna 1",
            "th": "ปฏฺฐาน 1",
        },
    },
    {
        "index": 56,
        "section": "abh",
        "title": {
            "en": "Paṭṭhāna 2",
            "th": "ปฏฺฐาน 2",
        },
    },
    {
        "index": 57,
        "section": "abh",
        "title": {
            "en": "Paṭṭhāna 3",
            "th": "ปฏฺฐาน 3",
        },
    },
]

# === PTS_PALI_VOLUMES ===
# hall edition code(s): pts/pali2424
# source: tipitaka-catalog/catalog/content/pts-pali-roman.tex
# count: 52
# \catalogitem only → 52. Meta says 57 vols including Index; see PTS_PALI_VOLUMES_WITH_INDEX (57) for Index lines too.
PTS_PALI_VOLUMES = [
    {
        "index": 1,
        "section": "vin",
        "title": {
            "en": "Vol. I: Pārājika",
            "th": "เล่ม ๑: ปาราชิก",
        },
    },
    {
        "index": 2,
        "section": "vin",
        "title": {
            "en": "Vol. II: Pācittiya",
            "th": "เล่ม ๒: ปาจิตฺติย",
        },
    },
    {
        "index": 3,
        "section": "vin",
        "title": {
            "en": "Vol. III: Bhikkhunīvibhaṅga",
            "th": "เล่ม ๓: ภิกฺขุนีวิภงฺค",
        },
    },
    {
        "index": 4,
        "section": "vin",
        "title": {
            "en": "Vol. IV: Mahāvagga",
            "th": "เล่ม ๔: มหาวคฺค",
        },
    },
    {
        "index": 5,
        "section": "vin",
        "title": {
            "en": "Vol. V: Cūḷavagga",
            "th": "เล่ม ๕: จูฬวคฺค",
        },
    },
    {
        "index": 6,
        "section": "vin",
        "title": {
            "en": "Vol. VI: Parivāra / Index",
            "th": "เล่ม ๖: ปริวาร / ดัชนี",
        },
    },
    {
        "index": 7,
        "section": "dn",
        "title": {
            "en": "Vol. I: Sīlakkhandhavagga",
            "th": "เล่ม ๑: สีลกฺขนฺธวคฺค",
        },
    },
    {
        "index": 8,
        "section": "dn",
        "title": {
            "en": "Vol. II: Mahāvagga",
            "th": "เล่ม ๒: มหาวคฺค",
        },
    },
    {
        "index": 9,
        "section": "dn",
        "title": {
            "en": "Vol. III: Pāṭikavagga",
            "th": "เล่ม ๓: ปาฏิกวคฺค",
        },
    },
    {
        "index": 10,
        "section": "mn",
        "title": {
            "en": "Vol. I: Mūlapaṇṇāsaka",
            "th": "เล่ม ๑: มูลปณฺณาสก",
        },
    },
    {
        "index": 11,
        "section": "mn",
        "title": {
            "en": "Vol. II: Majjhimapaṇṇāsaka",
            "th": "เล่ม ๒: มชฺฌิมปณฺณาสก",
        },
    },
    {
        "index": 12,
        "section": "mn",
        "title": {
            "en": "Vol. III: Uparipaṇṇāsaka",
            "th": "เล่ม ๓: อุปริปณฺณาสก",
        },
    },
    {
        "index": 13,
        "section": "sn",
        "title": {
            "en": "Vol. I: Sagāthāvagga",
            "th": "เล่ม ๑: สคาถาวคฺค",
        },
    },
    {
        "index": 14,
        "section": "sn",
        "title": {
            "en": "Vol. II: Nidānavagga",
            "th": "เล่ม ๒: นิทานวคฺค",
        },
    },
    {
        "index": 15,
        "section": "sn",
        "title": {
            "en": "Vol. III: Khandhavagga",
            "th": "เล่ม ๓: ขนฺธวคฺค",
        },
    },
    {
        "index": 16,
        "section": "sn",
        "title": {
            "en": "Vol. IV: Saḷāyatanavagga",
            "th": "เล่ม ๔: สฬายตนวคฺค",
        },
    },
    {
        "index": 17,
        "section": "sn",
        "title": {
            "en": "Vol. V: Mahāvagga",
            "th": "เล่ม ๕: มหาวคฺค",
        },
    },
    {
        "index": 18,
        "section": "an",
        "title": {
            "en": "Vol. I: Ekaka–Tika Nipāta",
            "th": "เล่ม ๑: เอกก–ติก นิปาต",
        },
    },
    {
        "index": 19,
        "section": "an",
        "title": {
            "en": "Vol. II: Catukka Nipāta",
            "th": "เล่ม ๒: จตุกฺก นิปาต",
        },
    },
    {
        "index": 20,
        "section": "an",
        "title": {
            "en": "Vol. III: Pañcaka–Chakka Nipāta",
            "th": "เล่ม ๓: ปญฺจก–ฉกฺก นิปาต",
        },
    },
    {
        "index": 21,
        "section": "an",
        "title": {
            "en": "Vol. IV: Sattaka–Aṭṭhaka–Navaka Nipāta",
            "th": "เล่ม ๔: สตฺตก–อฏฺฐก–นวก นิปาต",
        },
    },
    {
        "index": 22,
        "section": "an",
        "title": {
            "en": "Vol. V: Dasaka–Ekādasaka Nipāta",
            "th": "เล่ม ๕: ทสก–เอกาทสก นิปาต",
        },
    },
    {
        "index": 23,
        "section": "kn",
        "title": {
            "en": "Khuddakapāṭha with Commentary",
            "th": "ขุทฺทกปาฐ พร้อมอรรถกถา",
        },
    },
    {
        "index": 24,
        "section": "kn",
        "title": {
            "en": "Dhammapada",
            "th": "ธมฺมปท",
        },
    },
    {
        "index": 25,
        "section": "kn",
        "title": {
            "en": "Dhammapada Commentary",
            "th": "อรรถกถาธมฺมปท",
        },
    },
    {
        "index": 26,
        "section": "kn",
        "title": {
            "en": "Udāna",
            "th": "อุทาน",
        },
    },
    {
        "index": 27,
        "section": "kn",
        "title": {
            "en": "Itivuttaka",
            "th": "อิติวุตฺตก",
        },
    },
    {
        "index": 28,
        "section": "kn",
        "title": {
            "en": "Suttanipāta",
            "th": "สุตฺตนิปาต",
        },
    },
    {
        "index": 29,
        "section": "kn",
        "title": {
            "en": "Vimānavatthu and Petavatthu",
            "th": "วิมานวตฺถุ และ เปตวตฺถุ",
        },
    },
    {
        "index": 30,
        "section": "kn",
        "title": {
            "en": "Theragāthā / Therīgāthā",
            "th": "เถรคาถา / เถรีคาถา",
        },
    },
    {
        "index": 31,
        "section": "kn",
        "title": {
            "en": "Jātaka with Commentary, Vol. I",
            "th": "ชาตก พร้อมอรรถกถา เล่ม ๑",
        },
    },
    {
        "index": 32,
        "section": "kn",
        "title": {
            "en": "Jātaka with Commentary, Vol. II",
            "th": "ชาตก พร้อมอรรถกถา เล่ม ๒",
        },
    },
    {
        "index": 33,
        "section": "kn",
        "title": {
            "en": "Jātaka with Commentary, Vol. III",
            "th": "ชาตก พร้อมอรรถกถา เล่ม ๓",
        },
    },
    {
        "index": 34,
        "section": "kn",
        "title": {
            "en": "Jātaka with Commentary, Vol. IV",
            "th": "ชาตก พร้อมอรรถกถา เล่ม ๔",
        },
    },
    {
        "index": 35,
        "section": "kn",
        "title": {
            "en": "Jātaka with Commentary, Vol. V",
            "th": "ชาตก พร้อมอรรถกถา เล่ม ๕",
        },
    },
    {
        "index": 36,
        "section": "kn",
        "title": {
            "en": "Jātaka with Commentary, Vol. VI",
            "th": "ชาตก พร้อมอรรถกถา เล่ม ๖",
        },
    },
    {
        "index": 37,
        "section": "kn",
        "title": {
            "en": "Jātaka with Commentary, Vol. VII — Indexes",
            "th": "ชาตก พร้อมอรรถกถา เล่ม ๗ — ดัชนี",
        },
    },
    {
        "index": 38,
        "section": "kn",
        "title": {
            "en": "Mahāniddesa",
            "th": "มหานิทฺเทส",
        },
    },
    {
        "index": 39,
        "section": "kn",
        "title": {
            "en": "Cūḷaniddesa",
            "th": "จูฬนิทฺเทส",
        },
    },
    {
        "index": 40,
        "section": "kn",
        "title": {
            "en": "Paṭisambhidāmagga, 2 Vols in one",
            "th": "ปฏิสมฺภิทามคฺค ๒ เล่มรวมเล่มเดียว",
        },
    },
    {
        "index": 41,
        "section": "kn",
        "title": {
            "en": "Apadāna, 2 Vols in one",
            "th": "อปทาน ๒ เล่มรวมเล่มเดียว",
        },
    },
    {
        "index": 42,
        "section": "kn",
        "title": {
            "en": "Buddhavaṃsa and Cariyāpiṭaka",
            "th": "พุทฺธวํส และ จริยาปิฏก",
        },
    },
    {
        "index": 43,
        "section": "abh",
        "title": {
            "en": "Dhammasaṅgaṇī",
            "th": "ธมฺมสงฺคณี",
        },
    },
    {
        "index": 44,
        "section": "abh",
        "title": {
            "en": "Vibhaṅga",
            "th": "วิภงฺค",
        },
    },
    {
        "index": 45,
        "section": "abh",
        "title": {
            "en": "Dhātukathā with Commentary",
            "th": "ธาตุกถา พร้อมอรรถกถา",
        },
    },
    {
        "index": 46,
        "section": "abh",
        "title": {
            "en": "Puggalapaññatti \\& Commentary, 2 Vols in one",
            "th": "ปุคฺคลปญฺญตฺติ และอรรถกถา ๒ เล่มรวมเล่มเดียว",
        },
    },
    {
        "index": 47,
        "section": "abh",
        "title": {
            "en": "Kathāvatthu, Vol. I",
            "th": "กถาวตฺถุ เล่ม ๑",
        },
    },
    {
        "index": 48,
        "section": "abh",
        "title": {
            "en": "Kathāvatthu, Vol. II / Index",
            "th": "กถาวตฺถุ เล่ม ๒ / ดัชนี",
        },
    },
    {
        "index": 49,
        "section": "abh",
        "title": {
            "en": "Yamaka, Vol. I",
            "th": "ยมก เล่ม ๑",
        },
    },
    {
        "index": 50,
        "section": "abh",
        "title": {
            "en": "Yamaka, Vol. II",
            "th": "ยมก เล่ม ๒",
        },
    },
    {
        "index": 51,
        "section": "abh",
        "title": {
            "en": "Paṭṭhāna, Dukapaṭṭhāna",
            "th": "ปฏฺฐาน ทุกปฏฺฐาน",
        },
    },
    {
        "index": 52,
        "section": "abh",
        "title": {
            "en": "Paṭṭhāna, Tikapaṭṭhāna with Commentary",
            "th": "ปฏฺฐาน ติกปฏฺฐาน พร้อมอรรถกถา",
        },
    },
]

# === PTS_PALI_VOLUMES_WITH_INDEX ===
# hall edition code(s): pts/pali2424
# source: tipitaka-catalog/catalog/content/pts-pali-roman.tex
# count: 57
# Includes bare \item Index entries (DN/MN/SN/AN/Niddesa indexes).
# title.th = Thai-script Pāli (ปริวรรต) + Thai structural wording for /th/ UI.
PTS_PALI_VOLUMES_WITH_INDEX = [
    {
        "index": 1,
        "section": "vin",
        "title": {
            "en": "Vol. I: Pārājika",
            "th": "เล่ม ๑: ปาราชิก",
        },
    },
    {
        "index": 2,
        "section": "vin",
        "title": {
            "en": "Vol. II: Pācittiya",
            "th": "เล่ม ๒: ปาจิตฺติย",
        },
    },
    {
        "index": 3,
        "section": "vin",
        "title": {
            "en": "Vol. III: Bhikkhunīvibhaṅga",
            "th": "เล่ม ๓: ภิกฺขุนีวิภงฺค",
        },
    },
    {
        "index": 4,
        "section": "vin",
        "title": {
            "en": "Vol. IV: Mahāvagga",
            "th": "เล่ม ๔: มหาวคฺค",
        },
    },
    {
        "index": 5,
        "section": "vin",
        "title": {
            "en": "Vol. V: Cūḷavagga",
            "th": "เล่ม ๕: จูฬวคฺค",
        },
    },
    {
        "index": 6,
        "section": "vin",
        "title": {
            "en": "Vol. VI: Parivāra / Index",
            "th": "เล่ม ๖: ปริวาร / ดัชนี",
        },
    },
    {
        "index": 7,
        "section": "dn",
        "title": {
            "en": "Vol. I: Sīlakkhandhavagga",
            "th": "เล่ม ๑: สีลกฺขนฺธวคฺค",
        },
    },
    {
        "index": 8,
        "section": "dn",
        "title": {
            "en": "Vol. II: Mahāvagga",
            "th": "เล่ม ๒: มหาวคฺค",
        },
    },
    {
        "index": 9,
        "section": "dn",
        "title": {
            "en": "Vol. III: Pāṭikavagga",
            "th": "เล่ม ๓: ปาฏิกวคฺค",
        },
    },
    {
        "index": 10,
        "section": "dn",
        "title": {
            "en": "Index",
            "th": "ดัชนี",
        },
    },
    {
        "index": 11,
        "section": "mn",
        "title": {
            "en": "Vol. I: Mūlapaṇṇāsaka",
            "th": "เล่ม ๑: มูลปณฺณาสก",
        },
    },
    {
        "index": 12,
        "section": "mn",
        "title": {
            "en": "Vol. II: Majjhimapaṇṇāsaka",
            "th": "เล่ม ๒: มชฺฌิมปณฺณาสก",
        },
    },
    {
        "index": 13,
        "section": "mn",
        "title": {
            "en": "Vol. III: Uparipaṇṇāsaka",
            "th": "เล่ม ๓: อุปริปณฺณาสก",
        },
    },
    {
        "index": 14,
        "section": "mn",
        "title": {
            "en": "Index",
            "th": "ดัชนี",
        },
    },
    {
        "index": 15,
        "section": "sn",
        "title": {
            "en": "Vol. I: Sagāthāvagga",
            "th": "เล่ม ๑: สคาถาวคฺค",
        },
    },
    {
        "index": 16,
        "section": "sn",
        "title": {
            "en": "Vol. II: Nidānavagga",
            "th": "เล่ม ๒: นิทานวคฺค",
        },
    },
    {
        "index": 17,
        "section": "sn",
        "title": {
            "en": "Vol. III: Khandhavagga",
            "th": "เล่ม ๓: ขนฺธวคฺค",
        },
    },
    {
        "index": 18,
        "section": "sn",
        "title": {
            "en": "Vol. IV: Saḷāyatanavagga",
            "th": "เล่ม ๔: สฬายตนวคฺค",
        },
    },
    {
        "index": 19,
        "section": "sn",
        "title": {
            "en": "Vol. V: Mahāvagga",
            "th": "เล่ม ๕: มหาวคฺค",
        },
    },
    {
        "index": 20,
        "section": "sn",
        "title": {
            "en": "Index",
            "th": "ดัชนี",
        },
    },
    {
        "index": 21,
        "section": "an",
        "title": {
            "en": "Vol. I: Ekaka–Tika Nipāta",
            "th": "เล่ม ๑: เอกก–ติก นิปาต",
        },
    },
    {
        "index": 22,
        "section": "an",
        "title": {
            "en": "Vol. II: Catukka Nipāta",
            "th": "เล่ม ๒: จตุกฺก นิปาต",
        },
    },
    {
        "index": 23,
        "section": "an",
        "title": {
            "en": "Vol. III: Pañcaka–Chakka Nipāta",
            "th": "เล่ม ๓: ปญฺจก–ฉกฺก นิปาต",
        },
    },
    {
        "index": 24,
        "section": "an",
        "title": {
            "en": "Vol. IV: Sattaka–Aṭṭhaka–Navaka Nipāta",
            "th": "เล่ม ๔: สตฺตก–อฏฺฐก–นวก นิปาต",
        },
    },
    {
        "index": 25,
        "section": "an",
        "title": {
            "en": "Vol. V: Dasaka–Ekādasaka Nipāta",
            "th": "เล่ม ๕: ทสก–เอกาทสก นิปาต",
        },
    },
    {
        "index": 26,
        "section": "an",
        "title": {
            "en": "Index",
            "th": "ดัชนี",
        },
    },
    {
        "index": 27,
        "section": "kn",
        "title": {
            "en": "Khuddakapāṭha with Commentary",
            "th": "ขุทฺทกปาฐ พร้อมอรรถกถา",
        },
    },
    {
        "index": 28,
        "section": "kn",
        "title": {
            "en": "Dhammapada",
            "th": "ธมฺมปท",
        },
    },
    {
        "index": 29,
        "section": "kn",
        "title": {
            "en": "Dhammapada Commentary",
            "th": "อรรถกถาธมฺมปท",
        },
    },
    {
        "index": 30,
        "section": "kn",
        "title": {
            "en": "Udāna",
            "th": "อุทาน",
        },
    },
    {
        "index": 31,
        "section": "kn",
        "title": {
            "en": "Itivuttaka",
            "th": "อิติวุตฺตก",
        },
    },
    {
        "index": 32,
        "section": "kn",
        "title": {
            "en": "Suttanipāta",
            "th": "สุตฺตนิปาต",
        },
    },
    {
        "index": 33,
        "section": "kn",
        "title": {
            "en": "Vimānavatthu and Petavatthu",
            "th": "วิมานวตฺถุ และ เปตวตฺถุ",
        },
    },
    {
        "index": 34,
        "section": "kn",
        "title": {
            "en": "Theragāthā / Therīgāthā",
            "th": "เถรคาถา / เถรีคาถา",
        },
    },
    {
        "index": 35,
        "section": "kn",
        "title": {
            "en": "Jātaka with Commentary, Vol. I",
            "th": "ชาตก พร้อมอรรถกถา เล่ม ๑",
        },
    },
    {
        "index": 36,
        "section": "kn",
        "title": {
            "en": "Jātaka with Commentary, Vol. II",
            "th": "ชาตก พร้อมอรรถกถา เล่ม ๒",
        },
    },
    {
        "index": 37,
        "section": "kn",
        "title": {
            "en": "Jātaka with Commentary, Vol. III",
            "th": "ชาตก พร้อมอรรถกถา เล่ม ๓",
        },
    },
    {
        "index": 38,
        "section": "kn",
        "title": {
            "en": "Jātaka with Commentary, Vol. IV",
            "th": "ชาตก พร้อมอรรถกถา เล่ม ๔",
        },
    },
    {
        "index": 39,
        "section": "kn",
        "title": {
            "en": "Jātaka with Commentary, Vol. V",
            "th": "ชาตก พร้อมอรรถกถา เล่ม ๕",
        },
    },
    {
        "index": 40,
        "section": "kn",
        "title": {
            "en": "Jātaka with Commentary, Vol. VI",
            "th": "ชาตก พร้อมอรรถกถา เล่ม ๖",
        },
    },
    {
        "index": 41,
        "section": "kn",
        "title": {
            "en": "Jātaka with Commentary, Vol. VII — Indexes",
            "th": "ชาตก พร้อมอรรถกถา เล่ม ๗ — ดัชนี",
        },
    },
    {
        "index": 42,
        "section": "kn",
        "title": {
            "en": "Mahāniddesa",
            "th": "มหานิทฺเทส",
        },
    },
    {
        "index": 43,
        "section": "kn",
        "title": {
            "en": "Cūḷaniddesa",
            "th": "จูฬนิทฺเทส",
        },
    },
    {
        "index": 44,
        "section": "kn",
        "title": {
            "en": "Index",
            "th": "ดัชนี",
        },
    },
    {
        "index": 45,
        "section": "kn",
        "title": {
            "en": "Paṭisambhidāmagga, 2 Vols in one",
            "th": "ปฏิสมฺภิทามคฺค ๒ เล่มรวมเล่มเดียว",
        },
    },
    {
        "index": 46,
        "section": "kn",
        "title": {
            "en": "Apadāna, 2 Vols in one",
            "th": "อปทาน ๒ เล่มรวมเล่มเดียว",
        },
    },
    {
        "index": 47,
        "section": "kn",
        "title": {
            "en": "Buddhavaṃsa and Cariyāpiṭaka",
            "th": "พุทฺธวํส และ จริยาปิฏก",
        },
    },
    {
        "index": 48,
        "section": "abh",
        "title": {
            "en": "Dhammasaṅgaṇī",
            "th": "ธมฺมสงฺคณี",
        },
    },
    {
        "index": 49,
        "section": "abh",
        "title": {
            "en": "Vibhaṅga",
            "th": "วิภงฺค",
        },
    },
    {
        "index": 50,
        "section": "abh",
        "title": {
            "en": "Dhātukathā with Commentary",
            "th": "ธาตุกถา พร้อมอรรถกถา",
        },
    },
    {
        "index": 51,
        "section": "abh",
        "title": {
            "en": "Puggalapaññatti \\& Commentary, 2 Vols in one",
            "th": "ปุคฺคลปญฺญตฺติ และอรรถกถา ๒ เล่มรวมเล่มเดียว",
        },
    },
    {
        "index": 52,
        "section": "abh",
        "title": {
            "en": "Kathāvatthu, Vol. I",
            "th": "กถาวตฺถุ เล่ม ๑",
        },
    },
    {
        "index": 53,
        "section": "abh",
        "title": {
            "en": "Kathāvatthu, Vol. II / Index",
            "th": "กถาวตฺถุ เล่ม ๒ / ดัชนี",
        },
    },
    {
        "index": 54,
        "section": "abh",
        "title": {
            "en": "Yamaka, Vol. I",
            "th": "ยมก เล่ม ๑",
        },
    },
    {
        "index": 55,
        "section": "abh",
        "title": {
            "en": "Yamaka, Vol. II",
            "th": "ยมก เล่ม ๒",
        },
    },
    {
        "index": 56,
        "section": "abh",
        "title": {
            "en": "Paṭṭhāna, Dukapaṭṭhāna",
            "th": "ปฏฺฐาน ทุกปฏฺฐาน",
        },
    },
    {
        "index": 57,
        "section": "abh",
        "title": {
            "en": "Paṭṭhāna, Tikapaṭṭhāna with Commentary",
            "th": "ปฏฺฐาน ติกปฏฺฐาน พร้อมอรรถกถา",
        },
    },
]

# === PTS_ENGLISH_VOLUMES ===
# hall edition code(s): pts/en2438
# source: tipitaka-catalog/catalog/content/pts-english.tex
# count: 59
# Concordance rows from \ptsrow / \ptsnone (Pali slot labels via catalog_no). title = '{pali} -- {english|Not Published}'. not_published rows are list-only (no VolumePage). Splits 33.(1)/33.(2) and 34.(1)/34.(2) are separate rows.
PTS_ENGLISH_VOLUMES = [
    {
        "index": 1,
        "section": "vin",
        "catalog_no": "1",
        "title": {
            "en": "Vol. I: Pārājika -- The Book of Discipline, Vol. I",
            "th": "เล่ม ๑: ปาราชิก -- The Book of Discipline, Vol. I",
        },
    },
    {
        "index": 2,
        "section": "vin",
        "catalog_no": "2",
        "title": {
            "en": "Vol. II: Pācittiya -- The Book of Discipline, Vol. II",
            "th": "เล่ม ๒: ปาจิตฺติย -- The Book of Discipline, Vol. II",
        },
    },
    {
        "index": 3,
        "section": "vin",
        "catalog_no": "3",
        "title": {
            "en": "Vol. III: Bhikkhunīvibhaṅga -- The Book of Discipline, Vol. III",
            "th": "เล่ม ๓: ภิกฺขุนีวิภงฺค -- The Book of Discipline, Vol. III",
        },
    },
    {
        "index": 4,
        "section": "vin",
        "catalog_no": "4",
        "title": {
            "en": "Vol. IV: Mahāvagga -- The Book of Discipline, Vol. IV",
            "th": "เล่ม ๔: มหาวคฺค -- The Book of Discipline, Vol. IV",
        },
    },
    {
        "index": 5,
        "section": "vin",
        "catalog_no": "5",
        "title": {
            "en": "Vol. V: Cūḷavagga -- The Book of Discipline, Vol. V",
            "th": "เล่ม ๕: จูฬวคฺค -- The Book of Discipline, Vol. V",
        },
    },
    {
        "index": 6,
        "section": "vin",
        "catalog_no": "6",
        "title": {
            "en": "Vol. VI: Parivāra / Index -- The Book of Discipline, Vol. VI",
            "th": "เล่ม ๖: ปริวาร / ดัชนี -- The Book of Discipline, Vol. VI",
        },
    },
    {
        "index": 7,
        "section": "dn",
        "catalog_no": "7",
        "title": {
            "en": "Vol. I: Sīlakkhandhavagga -- Dialogues of the Buddha, Vol. I",
            "th": "เล่ม ๑: สีลกฺขนฺธวคฺค -- Dialogues of the Buddha, Vol. I",
        },
    },
    {
        "index": 8,
        "section": "dn",
        "catalog_no": "8",
        "title": {
            "en": "Vol. II: Mahāvagga -- Dialogues of the Buddha, Vol. II",
            "th": "เล่ม ๒: มหาวคฺค -- Dialogues of the Buddha, Vol. II",
        },
    },
    {
        "index": 9,
        "section": "dn",
        "catalog_no": "9",
        "title": {
            "en": "Vol. III: Pāṭikavagga -- Dialogues of the Buddha, Vol. III",
            "th": "เล่ม ๓: ปาฏิกวคฺค -- Dialogues of the Buddha, Vol. III",
        },
    },
    {
        "index": 10,
        "section": "dn",
        "catalog_no": "10",
        "not_published": True,
        "title": {
            "en": "Index to the Dīgha-nikāya -- (Not Published)",
            "th": "ดัชนีทีฆนิกาย -- (ยังไม่ได้จัดพิมพ์)",
        },
    },
    {
        "index": 11,
        "section": "mn",
        "catalog_no": "11",
        "title": {
            "en": "Vol. I: Mūlapaṇṇāsaka -- Middle Length Sayings, Vol. I",
            "th": "เล่ม ๑: มูลปณฺณาสก -- Middle Length Sayings, Vol. I",
        },
    },
    {
        "index": 12,
        "section": "mn",
        "catalog_no": "12",
        "title": {
            "en": "Vol. II: Majjhimapaṇṇāsaka -- Middle Length Sayings, Vol. II",
            "th": "เล่ม ๒: มชฺฌิมปณฺณาสก -- Middle Length Sayings, Vol. II",
        },
    },
    {
        "index": 13,
        "section": "mn",
        "catalog_no": "13",
        "title": {
            "en": "Vol. III: Uparipaṇṇāsaka -- Middle Length Sayings, Vol. III",
            "th": "เล่ม ๓: อุปริปณฺณาสก -- Middle Length Sayings, Vol. III",
        },
    },
    {
        "index": 14,
        "section": "mn",
        "catalog_no": "14",
        "not_published": True,
        "title": {
            "en": "Index to the Majjhima-nikāya -- (Not Published)",
            "th": "ดัชนีมัชฌิมนิกาย -- (ยังไม่ได้จัดพิมพ์)",
        },
    },
    {
        "index": 15,
        "section": "sn",
        "catalog_no": "15",
        "title": {
            "en": "Vol. I: Sagāthāvagga -- Kindred Sayings, Vol. I",
            "th": "เล่ม ๑: สคาถาวคฺค -- Kindred Sayings, Vol. I",
        },
    },
    {
        "index": 16,
        "section": "sn",
        "catalog_no": "16",
        "title": {
            "en": "Vol. II: Nidānavagga -- Kindred Sayings, Vol. II",
            "th": "เล่ม ๒: นิทานวคฺค -- Kindred Sayings, Vol. II",
        },
    },
    {
        "index": 17,
        "section": "sn",
        "catalog_no": "17",
        "title": {
            "en": "Vol. III: Khandhavagga -- Kindred Sayings, Vol. III",
            "th": "เล่ม ๓: ขนฺธวคฺค -- Kindred Sayings, Vol. III",
        },
    },
    {
        "index": 18,
        "section": "sn",
        "catalog_no": "18",
        "title": {
            "en": "Vol. IV: Saḷāyatanavagga -- Kindred Sayings, Vol. IV",
            "th": "เล่ม ๔: สฬายตนวคฺค -- Kindred Sayings, Vol. IV",
        },
    },
    {
        "index": 19,
        "section": "sn",
        "catalog_no": "19",
        "title": {
            "en": "Vol. V: Mahāvagga -- Kindred Sayings, Vol. V",
            "th": "เล่ม ๕: มหาวคฺค -- Kindred Sayings, Vol. V",
        },
    },
    {
        "index": 20,
        "section": "sn",
        "catalog_no": "20",
        "not_published": True,
        "title": {
            "en": "Index to the Saṃyutta-nikāya -- (Not Published)",
            "th": "ดัชนีสังยุตตนิกาย -- (ยังไม่ได้จัดพิมพ์)",
        },
    },
    {
        "index": 21,
        "section": "an",
        "catalog_no": "21",
        "title": {
            "en": "Vol. I: Ekaka–Tika Nipāta -- Gradual Sayings, Vol. I",
            "th": "เล่ม ๑: เอกก–ติก นิปาต -- Gradual Sayings, Vol. I",
        },
    },
    {
        "index": 22,
        "section": "an",
        "catalog_no": "22",
        "title": {
            "en": "Vol. II: Catukka Nipāta -- Gradual Sayings, Vol. II",
            "th": "เล่ม ๒: จตุกฺก นิปาต -- Gradual Sayings, Vol. II",
        },
    },
    {
        "index": 23,
        "section": "an",
        "catalog_no": "23",
        "title": {
            "en": "Vol. III: Pañcaka–Chakka Nipāta -- Gradual Sayings, Vol. III",
            "th": "เล่ม ๓: ปญฺจก–ฉกฺก นิปาต -- Gradual Sayings, Vol. III",
        },
    },
    {
        "index": 24,
        "section": "an",
        "catalog_no": "24",
        "title": {
            "en": "Vol. IV: Sattaka–Aṭṭhaka–Navaka Nipāta -- Gradual Sayings, Vol. IV",
            "th": "เล่ม ๔: สตฺตก–อฏฺฐก–นวก นิปาต -- Gradual Sayings, Vol. IV",
        },
    },
    {
        "index": 25,
        "section": "an",
        "catalog_no": "25",
        "title": {
            "en": "Vol. V: Dasaka–Ekādasaka Nipāta -- Gradual Sayings, Vol. V",
            "th": "เล่ม ๕: ทสก–เอกาทสก นิปาต -- Gradual Sayings, Vol. V",
        },
    },
    {
        "index": 26,
        "section": "an",
        "catalog_no": "26",
        "not_published": True,
        "title": {
            "en": "Index to the Aṅguttara-nikāya -- (Not Published)",
            "th": "ดัชนีอังคุตตรนิกาย -- (ยังไม่ได้จัดพิมพ์)",
        },
    },
    {
        "index": 27,
        "section": "kn",
        "catalog_no": "27",
        "title": {
            "en": "Khuddakapāṭha with Commentary -- Minor Readings",
            "th": "ขุทฺทกปาฐ พร้อมอรรถกถา -- Minor Readings",
        },
    },
    {
        "index": 28,
        "section": "kn",
        "catalog_no": "28",
        "title": {
            "en": "Dhammapada -- Word of the Doctrine",
            "th": "ธมฺมปท -- Word of the Doctrine",
        },
    },
    {
        "index": 29,
        "section": "kn",
        "catalog_no": "29",
        "not_published": True,
        "title": {
            "en": "Dhammapada Commentary -- (Not Published)",
            "th": "อรรถกถาธมฺมปท -- (ยังไม่ได้จัดพิมพ์)",
        },
    },
    {
        "index": 30,
        "section": "kn",
        "catalog_no": "30",
        "title": {
            "en": "Udāna -- The Udāna and The Itivuttaka",
            "th": "อุทาน -- The Udāna and The Itivuttaka",
        },
    },
    {
        "index": 31,
        "section": "kn",
        "catalog_no": "31",
        "title": {
            "en": "Itivuttaka -- The Udāna and The Itivuttaka",
            "th": "อิติวุตฺตก -- The Udāna and The Itivuttaka",
        },
    },
    {
        "index": 32,
        "section": "kn",
        "catalog_no": "32",
        "title": {
            "en": "Suttanipāta -- The Group of Discourses",
            "th": "สุตฺตนิปาต -- The Group of Discourses",
        },
    },
    {
        "index": 33,
        "section": "kn",
        "catalog_no": "33.(1)",
        "title": {
            "en": "Vimānavatthu and Petavatthu -- Vimāna Stories",
            "th": "วิมานวตฺถุ และ เปตวตฺถุ -- Vimāna Stories",
        },
    },
    {
        "index": 34,
        "section": "kn",
        "catalog_no": "33.(2)",
        "title": {
            "en": "Vimānavatthu and Petavatthu -- Peta Stories",
            "th": "วิมานวตฺถุ และ เปตวตฺถุ -- Peta Stories",
        },
    },
    {
        "index": 35,
        "section": "kn",
        "catalog_no": "34.(1)",
        "title": {
            "en": "Theragāthā / Therīgāthā -- Elders' Verses, Vol. I",
            "th": "เถรคาถา / เถรีคาถา -- Elders' Verses, Vol. I",
        },
    },
    {
        "index": 36,
        "section": "kn",
        "catalog_no": "34.(2)",
        "title": {
            "en": "Theragāthā / Therīgāthā -- Elders' Verses, Vol. II",
            "th": "เถรคาถา / เถรีคาถา -- Elders' Verses, Vol. II",
        },
    },
    {
        "index": 37,
        "section": "kn",
        "catalog_no": "35",
        "title": {
            "en": "Jātaka with Commentary, Vol. I -- The Jātaka or Stories of the Buddha's Former Births, Vol. I",
            "th": "ชาตก พร้อมอรรถกถา เล่ม ๑ -- The Jātaka or Stories of the Buddha's Former Births, Vol. I",
        },
    },
    {
        "index": 38,
        "section": "kn",
        "catalog_no": "36",
        "title": {
            "en": "Jātaka with Commentary, Vol. II -- The Jātaka or Stories of the Buddha's Former Births, Vol. II",
            "th": "ชาตก พร้อมอรรถกถา เล่ม ๒ -- The Jātaka or Stories of the Buddha's Former Births, Vol. II",
        },
    },
    {
        "index": 39,
        "section": "kn",
        "catalog_no": "37",
        "title": {
            "en": "Jātaka with Commentary, Vol. III -- The Jātaka or Stories of the Buddha's Former Births, Vol. III",
            "th": "ชาตก พร้อมอรรถกถา เล่ม ๓ -- The Jātaka or Stories of the Buddha's Former Births, Vol. III",
        },
    },
    {
        "index": 40,
        "section": "kn",
        "catalog_no": "38",
        "title": {
            "en": "Jātaka with Commentary, Vol. IV -- The Jātaka or Stories of the Buddha's Former Births, Vol. IV",
            "th": "ชาตก พร้อมอรรถกถา เล่ม ๔ -- The Jātaka or Stories of the Buddha's Former Births, Vol. IV",
        },
    },
    {
        "index": 41,
        "section": "kn",
        "catalog_no": "39",
        "title": {
            "en": "Jātaka with Commentary, Vol. V -- The Jātaka or Stories of the Buddha's Former Births, Vol. V",
            "th": "ชาตก พร้อมอรรถกถา เล่ม ๕ -- The Jātaka or Stories of the Buddha's Former Births, Vol. V",
        },
    },
    {
        "index": 42,
        "section": "kn",
        "catalog_no": "40",
        "title": {
            "en": "Jātaka with Commentary, Vol. VI -- The Jātaka or Stories of the Buddha's Former Births, Vol. VI",
            "th": "ชาตก พร้อมอรรถกถา เล่ม ๖ -- The Jātaka or Stories of the Buddha's Former Births, Vol. VI",
        },
    },
    {
        "index": 43,
        "section": "kn",
        "catalog_no": "41",
        "not_published": True,
        "title": {
            "en": "Jātaka with Commentary, Vol. VII — Indexes -- (Not Published)",
            "th": "ชาตก พร้อมอรรถกถา เล่ม ๗ — ดัชนี -- (ยังไม่ได้จัดพิมพ์)",
        },
    },
    {
        "index": 44,
        "section": "kn",
        "catalog_no": "42",
        "not_published": True,
        "title": {
            "en": "Mahāniddesa -- (Not Published)",
            "th": "มหานิทฺเทส -- (ยังไม่ได้จัดพิมพ์)",
        },
    },
    {
        "index": 45,
        "section": "kn",
        "catalog_no": "43",
        "not_published": True,
        "title": {
            "en": "Cūḷaniddesa -- (Not Published)",
            "th": "จูฬนิทฺเทส -- (ยังไม่ได้จัดพิมพ์)",
        },
    },
    {
        "index": 46,
        "section": "kn",
        "catalog_no": "44",
        "not_published": True,
        "title": {
            "en": "Index to the Mahāniddesa -- (Not Published)",
            "th": "ดัชนีมหานิทเทส -- (ยังไม่ได้จัดพิมพ์)",
        },
    },
    {
        "index": 47,
        "section": "kn",
        "catalog_no": "45",
        "title": {
            "en": "Paṭisambhidāmagga, 2 Vols in one -- The Path of Discrimination",
            "th": "ปฏิสมฺภิทามคฺค ๒ เล่มรวมเล่มเดียว -- The Path of Discrimination",
        },
    },
    {
        "index": 48,
        "section": "kn",
        "catalog_no": "46",
        "not_published": True,
        "title": {
            "en": "Apadāna, 2 Vols in one -- (Not Published)",
            "th": "อปทาน ๒ เล่มรวมเล่มเดียว -- (ยังไม่ได้จัดพิมพ์)",
        },
    },
    {
        "index": 49,
        "section": "kn",
        "catalog_no": "47",
        "title": {
            "en": "Buddhavaṃsa and Cariyāpiṭaka -- Chronicle of Buddhas; Basket of Conduct",
            "th": "พุทฺธวํส และ จริยาปิฏก -- Chronicle of Buddhas; Basket of Conduct",
        },
    },
    {
        "index": 50,
        "section": "abh",
        "catalog_no": "48",
        "title": {
            "en": "Dhammasaṅgaṇī -- A Buddhist Manual of Psychological Ethics",
            "th": "ธมฺมสงฺคณี -- A Buddhist Manual of Psychological Ethics",
        },
    },
    {
        "index": 51,
        "section": "abh",
        "catalog_no": "49",
        "title": {
            "en": "Vibhaṅga -- The Book of Analysis",
            "th": "วิภงฺค -- The Book of Analysis",
        },
    },
    {
        "index": 52,
        "section": "abh",
        "catalog_no": "50",
        "title": {
            "en": "Dhātukathā with Commentary -- Discourse on Elements",
            "th": "ธาตุกถา พร้อมอรรถกถา -- Discourse on Elements",
        },
    },
    {
        "index": 53,
        "section": "abh",
        "catalog_no": "51",
        "title": {
            "en": "Puggalapaññatti & Commentary, 2 Vols in one -- A Designation of Human Types",
            "th": "ปุคฺคลปญฺญตฺติ และอรรถกถา ๒ เล่มรวมเล่มเดียว -- A Designation of Human Types",
        },
    },
    {
        "index": 54,
        "section": "abh",
        "catalog_no": "52",
        "title": {
            "en": "Kathāvatthu, Vol. I -- Points of Controversy",
            "th": "กถาวตฺถุ เล่ม ๑ -- Points of Controversy",
        },
    },
    {
        "index": 55,
        "section": "abh",
        "catalog_no": "53",
        "title": {
            "en": "Kathāvatthu, Vol. II / Index -- Points of Controversy",
            "th": "กถาวตฺถุ เล่ม ๒ / ดัชนี -- Points of Controversy",
        },
    },
    {
        "index": 56,
        "section": "abh",
        "catalog_no": "54",
        "not_published": True,
        "title": {
            "en": "Yamaka, Vol. I -- (Not Published)",
            "th": "ยมก เล่ม ๑ -- (ยังไม่ได้จัดพิมพ์)",
        },
    },
    {
        "index": 57,
        "section": "abh",
        "catalog_no": "55",
        "not_published": True,
        "title": {
            "en": "Yamaka, Vol. II -- (Not Published)",
            "th": "ยมก เล่ม ๒ -- (ยังไม่ได้จัดพิมพ์)",
        },
    },
    {
        "index": 58,
        "section": "abh",
        "catalog_no": "56",
        "title": {
            "en": "Paṭṭhāna, Dukapaṭṭhāna -- Conditional Relations, Vol. I",
            "th": "ปฏฺฐาน ทุกปฏฺฐาน -- Conditional Relations, Vol. I",
        },
    },
    {
        "index": 59,
        "section": "abh",
        "catalog_no": "57",
        "title": {
            "en": "Paṭṭhāna, Tikapaṭṭhāna with Commentary -- Conditional Relations, Vol. II",
            "th": "ปฏฺฐาน ติกปฏฺฐาน พร้อมอรรถกถา -- Conditional Relations, Vol. II",
        },
    },
]

# === TAI_PALI_VOLUMES ===
# hall edition code(s): tai/pali2567
# source: tipitaka-catalog/catalog/content/tai-pali-shan.tex
# count: 5
# Vinaya only (5).
TAI_PALI_VOLUMES = [
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
]

# === VNM_VIETNAMESE_VOLUMES ===
# hall edition code(s): vnm/vi2563
# source: tipitaka-catalog/catalog/content/vnm-vietnamese.tex
# count: 13
# Sutta only 13 vols; title.en = Vietnamese; title.th = Thai description from TeX.
VNM_VIETNAMESE_VOLUMES = [
    {
        "index": 1,
        "section": "dn",
        "title": {
            "en": "Kinh Trường Bộ",
            "th": "ทีฆนิกาย --- พระสูตรยาว 34 สูตร",
        },
    },
    {
        "index": 2,
        "section": "mn",
        "title": {
            "en": "Kinh Trung Bộ I",
            "th": "มัชฌิมนิกาย ภาค 1 --- สูตรที่ 1--76",
        },
    },
    {
        "index": 3,
        "section": "mn",
        "title": {
            "en": "Kinh Trung Bộ II",
            "th": "มัชฌิมนิกาย ภาค 2 --- สูตรที่ 77--152",
        },
    },
    {
        "index": 4,
        "section": "sn",
        "title": {
            "en": "Kinh Tương Ưng Bộ I",
            "th": "สังยุตตนิกาย ภาค 1",
        },
    },
    {
        "index": 5,
        "section": "sn",
        "title": {
            "en": "Kinh Tương Ưng Bộ II",
            "th": "สังยุตตนิกาย ภาค 2",
        },
    },
    {
        "index": 6,
        "section": "an",
        "title": {
            "en": "Kinh Tăng Chi Bộ I",
            "th": "อังคุตตรนิกาย ภาค 1 --- เอก--ปัญจกนิบาต",
        },
    },
    {
        "index": 7,
        "section": "an",
        "title": {
            "en": "Kinh Tăng Chi Bộ II",
            "th": "อังคุตตรนิกาย ภาค 2 --- ฉักก--เอกาทสกนิบาต",
        },
    },
    {
        "index": 8,
        "section": "kn",
        "title": {
            "en": "Kinh Tiểu Bộ I",
            "th": "ขุททกนิกาย ภาค 1 --- ขุททกปาฐะ, ธรรมบท, อุทาน, อิติวุตตกะ, สุตตนิบาต",
        },
    },
    {
        "index": 9,
        "section": "kn",
        "title": {
            "en": "Kinh Tiểu Bộ II",
            "th": "ขุททกนิกาย ภาค 2 --- วิมานวัตถุ, เปตวัตถุ, เถรคาถา, เถรีคาถา",
        },
    },
    {
        "index": 10,
        "section": "kn",
        "title": {
            "en": "Kinh Tiểu Bộ III",
            "th": "ขุททกนิกาย ภาค 3 --- ชาดก ภาค 1",
        },
    },
    {
        "index": 11,
        "section": "kn",
        "title": {
            "en": "Kinh Tiểu Bộ IV",
            "th": "ขุททกนิกาย ภาค 4 --- ชาดก ภาค 2",
        },
    },
    {
        "index": 12,
        "section": "kn",
        "title": {
            "en": "Kinh Tiểu Bộ V",
            "th": "ขุททกนิกาย ภาค 5 --- ชาดก ภาค 3",
        },
    },
    {
        "index": 13,
        "section": "kn",
        "title": {
            "en": "Kinh Tiểu Bộ VI",
            "th": "ขุททกนิกาย ภาค 6 --- มหานิทเทส, จูฬนิทเทส, ปฏิสัมภิทามรรค, อปทาน, พุทธวงศ์, จริยาปิฎก",
        },
    },
]

# === NDZ_JAPANESE_VOLUMES ===
# hall edition code(s): ndz/ja2544
# source: tipitaka-catalog/catalog/content/ndz-japanese.tex
# count: 71
# 65 set / ~70 physical with splits; includes 蔵外 + index note. title.en = Japanese (+ Roman of Pāli); title.th = Thai-script Pāli from TeX.
NDZ_JAPANESE_VOLUMES = [
    {
        "index": 1,
        "section": "vin",
        "title": {
            "en": "律 蔵１ (Mahāvibhaṅga)",
            "th": "มหาวิภงฺค",
        },
    },
    {
        "index": 2,
        "section": "vin",
        "title": {
            "en": "律 蔵２ (Suttavibhaṅga; Bhikkhunīvibhaṅga)",
            "th": "สุตฺตวิภงฺค; ภิกฺขุนีวิภงฺค",
        },
    },
    {
        "index": 3,
        "section": "vin",
        "title": {
            "en": "律 蔵３ (Mahāvagga)",
            "th": "มหาวคฺค",
        },
    },
    {
        "index": 4,
        "section": "vin",
        "title": {
            "en": "律 蔵４ (Cullavagga)",
            "th": "จุลฺลวคฺค",
        },
    },
    {
        "index": 5,
        "section": "vin",
        "title": {
            "en": "律 蔵５ (Parivāra)",
            "th": "ปริวาร",
        },
    },
    {
        "index": 6,
        "section": "dn",
        "title": {
            "en": "長部経典１ (Sīlakkhandhavagga; Mahāvagga)",
            "th": "สีลกฺขนฺธวคฺค; มหาวคฺค",
        },
    },
    {
        "index": 7,
        "section": "dn",
        "title": {
            "en": "長部経典２ (Mahāvagga)",
            "th": "มหาวคฺค",
        },
    },
    {
        "index": 8,
        "section": "dn",
        "title": {
            "en": "長部経典３ (Pāṭikavagga)",
            "th": "ปาฏิกวคฺค",
        },
    },
    {
        "index": 9,
        "section": "mn",
        "title": {
            "en": "中部経典１ (Mūlapaṇṇāsaka)",
            "th": "มูลปณฺณาสก",
        },
    },
    {
        "index": 10,
        "section": "mn",
        "title": {
            "en": "中部経典２ (Majjhimapaṇṇāsaka)",
            "th": "มชฺฌิมปณฺณาสก",
        },
    },
    {
        "index": 11,
        "section": "mn",
        "title": {
            "en": "中部経典３ 上 (Majjhimapaṇṇāsaka; Uparipaṇṇāsaka)",
            "th": "มชฺฌิมปณฺณาสก; อุปริปณฺณาสก",
        },
    },
    {
        "index": 12,
        "section": "mn",
        "title": {
            "en": "中部経典４ 下 (Uparipaṇṇāsaka)",
            "th": "อุปริปณฺณาสก",
        },
    },
    {
        "index": 13,
        "section": "sn",
        "title": {
            "en": "相応部経典１ (Sagāthavagga)",
            "th": "สคาถวคฺค",
        },
    },
    {
        "index": 14,
        "section": "sn",
        "title": {
            "en": "相応部経典２ (Nidānavagga)",
            "th": "นิทานวคฺค",
        },
    },
    {
        "index": 15,
        "section": "sn",
        "title": {
            "en": "相応部経典３ (Khandhavāravagga)",
            "th": "ขนฺธวารวคฺค",
        },
    },
    {
        "index": 16,
        "section": "sn",
        "title": {
            "en": "相応部経典４ (Saḷāyatanavagga)",
            "th": "สฬายตนวคฺค",
        },
    },
    {
        "index": 17,
        "section": "sn",
        "title": {
            "en": "相応部経典５ 上 (Saḷāyatanavagga; Mahāvagga 1)",
            "th": "สฬายตนวคฺค; มหาวคฺค ๑",
        },
    },
    {
        "index": 18,
        "section": "sn",
        "title": {
            "en": "相応部経典６ 下 (Mahāvagga 2)",
            "th": "มหาวคฺค ๒",
        },
    },
    {
        "index": 19,
        "section": "an",
        "title": {
            "en": "増支部経典１ (Ekaka-duka-tikanipāta)",
            "th": "เอกก-ทุก-ติกนิปาต",
        },
    },
    {
        "index": 20,
        "section": "an",
        "title": {
            "en": "増支部経典２ (Catukkanipāta)",
            "th": "จตุกฺกนิปาต",
        },
    },
    {
        "index": 21,
        "section": "an",
        "title": {
            "en": "増支部経典３ (Pañcaka; Chakkanipāta)",
            "th": "ปญฺจก; ฉกฺกนิปาต",
        },
    },
    {
        "index": 22,
        "section": "an",
        "title": {
            "en": "増支部経典４ (Sattakanipāta)",
            "th": "สตฺตกนิปาต",
        },
    },
    {
        "index": 23,
        "section": "an",
        "title": {
            "en": "増支部経典５ (Aṭṭhakanipāta)",
            "th": "อฏฺฐกนิปาต",
        },
    },
    {
        "index": 24,
        "section": "an",
        "title": {
            "en": "増支部経典６ 上 (Navakanipāta; Dasakanipāta)",
            "th": "นวกนิปาต; ทสกนิปาต",
        },
    },
    {
        "index": 25,
        "section": "an",
        "title": {
            "en": "増支部経典７ 下 (Dasakanipāta; Ekādasakanipāta)",
            "th": "ทสกนิปาต; เอกาทสกนิปาต",
        },
    },
    {
        "index": 26,
        "section": "kn",
        "title": {
            "en": "小部経典１ (Khuddakapāṭha; Dhammapada; Udāna; Itivuttaka)",
            "th": "ขุทฺทกปาฐ; ธมฺมปท; อุทาน; อิติวุตฺตก",
        },
    },
    {
        "index": 27,
        "section": "kn",
        "title": {
            "en": "小部経典２ (Suttanipāta; Vimānavatthu)",
            "th": "สุตฺตนิปาต; วิมานวตฺถุ",
        },
    },
    {
        "index": 28,
        "section": "kn",
        "title": {
            "en": "小部経典３ (Petavatthu; Theragāthā; Therīgāthā)",
            "th": "เปตวตฺถุ; เถรคาถา; เถรีคาถา",
        },
    },
    {
        "index": 29,
        "section": "kn",
        "title": {
            "en": "小部経典４ (Apadāna 1)",
            "th": "อปทาน ๑",
        },
    },
    {
        "index": 30,
        "section": "kn",
        "title": {
            "en": "小部経典５ (Apadāna 2)",
            "th": "อปทาน ๒",
        },
    },
    {
        "index": 31,
        "section": "kn",
        "title": {
            "en": "小部経典６ (Jātaka 1)",
            "th": "ชาตก ๑",
        },
    },
    {
        "index": 32,
        "section": "kn",
        "title": {
            "en": "小部経典７ (Jātaka 2)",
            "th": "ชาตก ๒",
        },
    },
    {
        "index": 33,
        "section": "kn",
        "title": {
            "en": "小部経典８ (Jātaka 3)",
            "th": "ชาตก ๓",
        },
    },
    {
        "index": 34,
        "section": "kn",
        "title": {
            "en": "小部経典９ (Jātaka 4)",
            "th": "ชาตก ๔",
        },
    },
    {
        "index": 35,
        "section": "kn",
        "title": {
            "en": "小部経典10 (Jātaka 5)",
            "th": "ชาตก ๕",
        },
    },
    {
        "index": 36,
        "section": "kn",
        "title": {
            "en": "小部経典11 (Jātaka 6)",
            "th": "ชาตก ๖",
        },
    },
    {
        "index": 37,
        "section": "kn",
        "title": {
            "en": "小部経典12 (Jātaka 7)",
            "th": "ชาตก ๗",
        },
    },
    {
        "index": 38,
        "section": "kn",
        "title": {
            "en": "小部経典13 (Jātaka 8)",
            "th": "ชาตก ๘",
        },
    },
    {
        "index": 39,
        "section": "kn",
        "title": {
            "en": "小部経典14 (Jātaka 9)",
            "th": "ชาตก ๙",
        },
    },
    {
        "index": 40,
        "section": "kn",
        "title": {
            "en": "小部経典15 (Jātaka 10)",
            "th": "ชาตก ๑๐",
        },
    },
    {
        "index": 41,
        "section": "kn",
        "title": {
            "en": "小部経典16 (Jātaka 11)",
            "th": "ชาตก ๑๑",
        },
    },
    {
        "index": 42,
        "section": "kn",
        "title": {
            "en": "小部経典17 (Jātaka 12)",
            "th": "ชาตก ๑๒",
        },
    },
    {
        "index": 43,
        "section": "kn",
        "title": {
            "en": "小部経典18 (Paṭisambhidāmagga 1)",
            "th": "ปฏิสมฺภิทามคฺค ๑",
        },
    },
    {
        "index": 44,
        "section": "kn",
        "title": {
            "en": "小部経典19 (Paṭisambhidāmagga 2)",
            "th": "ปฏิสมฺภิทามคฺค ๒",
        },
    },
    {
        "index": 45,
        "section": "kn",
        "title": {
            "en": "小部経典20 (Mahānidesa 1)",
            "th": "มหานิเทส ๑",
        },
    },
    {
        "index": 46,
        "section": "kn",
        "title": {
            "en": "小部経典21 (Mahānidesa 2)",
            "th": "มหานิเทส ๒",
        },
    },
    {
        "index": 47,
        "section": "kn",
        "title": {
            "en": "小部経典22 (Cullanidesa)",
            "th": "จุลฺลนิเทส",
        },
    },
    {
        "index": 48,
        "section": "abh",
        "title": {
            "en": "法集論 (Dhammasaṅgaṇī)",
            "th": "ธมฺมสงฺคณี",
        },
    },
    {
        "index": 49,
        "section": "abh",
        "title": {
            "en": "分別論 (Vibhaṅga 1)",
            "th": "วิภงฺค ๑",
        },
    },
    {
        "index": 50,
        "section": "abh",
        "title": {
            "en": "分別論・界論・人施設論 (Vibhaṅga 2; Dhātukathā; Puggalapaññatti)",
            "th": "วิภงฺค ๒; ธาตุกถา; ปุคฺคลปญฺญตฺติ",
        },
    },
    {
        "index": 51,
        "section": "abh",
        "title": {
            "en": "双 論１ 上 (Yamaka 1)",
            "th": "ยมก ๑",
        },
    },
    {
        "index": 52,
        "section": "abh",
        "title": {
            "en": "双 論２ 下 (Yamaka 2)",
            "th": "ยมก ๒",
        },
    },
    {
        "index": 53,
        "section": "abh",
        "title": {
            "en": "双 論３ (Yamaka 3)",
            "th": "ยมก ๓",
        },
    },
    {
        "index": 54,
        "section": "abh",
        "title": {
            "en": "発趣論１ (Paṭṭhāna 1)",
            "th": "ปฏฺฐาน ๑",
        },
    },
    {
        "index": 55,
        "section": "abh",
        "title": {
            "en": "発趣論２ (Paṭṭhāna 2)",
            "th": "ปฏฺฐาน ๒",
        },
    },
    {
        "index": 56,
        "section": "abh",
        "title": {
            "en": "発趣論３ (Paṭṭhāna 3)",
            "th": "ปฏฺฐาน ๓",
        },
    },
    {
        "index": 57,
        "section": "abh",
        "title": {
            "en": "発趣論４ (Paṭṭhāna 4)",
            "th": "ปฏฺฐาน ๔",
        },
    },
    {
        "index": 58,
        "section": "abh",
        "title": {
            "en": "発趣論５ (Paṭṭhāna 5)",
            "th": "ปฏฺฐาน ๕",
        },
    },
    {
        "index": 59,
        "section": "abh",
        "title": {
            "en": "発趣論６ (Paṭṭhāna 6)",
            "th": "ปฏฺฐาน ๖",
        },
    },
    {
        "index": 60,
        "section": "abh",
        "title": {
            "en": "発趣論７ (Paṭṭhāna 7)",
            "th": "ปฏฺฐาน ๗",
        },
    },
    {
        "index": 61,
        "section": "abh",
        "title": {
            "en": "論 事１ (Kathāvatthu 1)",
            "th": "กถาวตฺถุ ๑",
        },
    },
    {
        "index": 62,
        "section": "abh",
        "title": {
            "en": "論 事２ (Kathāvatthu 2)",
            "th": "กถาวตฺถุ ๒",
        },
    },
    {
        "index": 63,
        "section": "kn",
        "title": {
            "en": "弥蘭王問経１ 上 (Milindapañha 1)",
            "th": "มิลินฺทปญฺห ๑",
        },
    },
    {
        "index": 64,
        "section": "kn",
        "title": {
            "en": "弥蘭王問経２ 下 (Milindapañha 2)",
            "th": "มิลินฺทปญฺห ๒",
        },
    },
    {
        "index": 65,
        "section": "kn",
        "title": {
            "en": "島王統史・大王統史 (Dīpavaṃsa; Mahāvaṃsa)",
            "th": "ทีปวํส; มหาวํส",
        },
    },
    {
        "index": 66,
        "section": "kn",
        "title": {
            "en": "小王統史 (Cullavaṃsa)",
            "th": "จุลฺลวํส",
        },
    },
    {
        "index": 67,
        "section": "kn",
        "title": {
            "en": "清浄道論１ (Visuddhimagga 1)",
            "th": "วิสุทธิมคฺค ๑",
        },
    },
    {
        "index": 68,
        "section": "kn",
        "title": {
            "en": "清浄道論２ (Visuddhimagga 2)",
            "th": "วิสุทธิมคฺค ๒",
        },
    },
    {
        "index": 69,
        "section": "kn",
        "title": {
            "en": "清浄道論３ (Visuddhimagga 3)",
            "th": "วิสุทธิมคฺค ๓",
        },
    },
    {
        "index": 70,
        "section": "kn",
        "title": {
            "en": "一切善見律註序・摂阿毘達磨義論・阿育王刻文 (Samantapāsādikā; Abhidhammatthasaṅgaha; Asokalekhā)",
            "th": "สมนฺตปาสาทิกา; อภิธมฺมตฺถสงฺคห; อโสกเลขา",
        },
    },
    {
        "index": 71,
        "section": "kn",
        "title": {
            "en": "パーリ原典対照 南伝大蔵経総目録 (General Index with Pali Concordance) --- สารบัญรวมจับคู่กับต้นฉบับบาลี",
            "th": "パーリ原典対照 南伝大蔵経総目録 (General Index with Pali Concordance) --- สารบัญรวมจับคู่กับต้นฉบับบาลี",
        },
    },
]

# === YCS_CHINESE_VOLUMES ===
# hall edition code(s): ych/zh2533
# source: tipitaka-catalog/catalog/content/ycs-chinese.tex
# count: 71
# Parallel to NDZ structure; title.en = Chinese (+ Roman Pāli); title.th = Thai-script Pāli.
YCS_CHINESE_VOLUMES = [
    {
        "index": 1,
        "section": "vin",
        "title": {
            "en": "律藏一 (Mahāvibhaṅga)",
            "th": "มหาวิภังฺค",
        },
    },
    {
        "index": 2,
        "section": "vin",
        "title": {
            "en": "律藏二 (Suttavibhaṅga; Bhikkhunīvibhaṅga)",
            "th": "สุตฺตวิภังฺค; ภิกฺขุนีวิภังฺค",
        },
    },
    {
        "index": 3,
        "section": "vin",
        "title": {
            "en": "律藏三 (Mahāvagga)",
            "th": "มหาวคฺค",
        },
    },
    {
        "index": 4,
        "section": "vin",
        "title": {
            "en": "律藏四 (Cullavagga)",
            "th": "จุลฺลวคฺค",
        },
    },
    {
        "index": 5,
        "section": "vin",
        "title": {
            "en": "律藏五 (Parivāra)",
            "th": "ปริวาร",
        },
    },
    {
        "index": 6,
        "section": "dn",
        "title": {
            "en": "长部经典一 (Sīlakkhandhavagga; Mahāvagga)",
            "th": "สีลกฺขนฺธวคฺค; มหาวคฺค",
        },
    },
    {
        "index": 7,
        "section": "dn",
        "title": {
            "en": "长部经典二 (Mahāvagga)",
            "th": "มหาวคฺค",
        },
    },
    {
        "index": 8,
        "section": "dn",
        "title": {
            "en": "长部经典三 (Pāṭikavagga)",
            "th": "ปาฏิกวคฺค",
        },
    },
    {
        "index": 9,
        "section": "mn",
        "title": {
            "en": "中部经典一 (Mūlapaṇṇāsaka)",
            "th": "มูลปณฺณาสก",
        },
    },
    {
        "index": 10,
        "section": "mn",
        "title": {
            "en": "中部经典二 (Majjhimapaṇṇāsaka)",
            "th": "มชฺฌิมปณฺณาสก",
        },
    },
    {
        "index": 11,
        "section": "mn",
        "title": {
            "en": "中部经典三 上 (Majjhimapaṇṇāsaka)",
            "th": "มชฺฌิมปณฺณาสก",
        },
    },
    {
        "index": 12,
        "section": "mn",
        "title": {
            "en": "中部经典四 下 (Uparipaṇṇāsaka)",
            "th": "อุปริปณฺณาสก",
        },
    },
    {
        "index": 13,
        "section": "sn",
        "title": {
            "en": "相应部经典一 (Sagāthavagga)",
            "th": "สคาถวคฺค",
        },
    },
    {
        "index": 14,
        "section": "sn",
        "title": {
            "en": "相应部经典二 (Nidānavagga)",
            "th": "นิทานวคฺค",
        },
    },
    {
        "index": 15,
        "section": "sn",
        "title": {
            "en": "相应部经典三 (Khandhavāravagga)",
            "th": "ขนฺธวารวคฺค",
        },
    },
    {
        "index": 16,
        "section": "sn",
        "title": {
            "en": "相应部经典四 上 (Saḷāyatanavagga)",
            "th": "สฬายตนวคฺค",
        },
    },
    {
        "index": 17,
        "section": "sn",
        "title": {
            "en": "相应部经典五 下 (Mahāvagga 1)",
            "th": "มหาวคฺค ๑",
        },
    },
    {
        "index": 18,
        "section": "sn",
        "title": {
            "en": "相应部经典六 (Mahāvagga 2)",
            "th": "มหาวคฺค ๒",
        },
    },
    {
        "index": 19,
        "section": "an",
        "title": {
            "en": "增支部经典一 (Ekaka-duka-tikanipāta)",
            "th": "เอกก-ทุก-ติกนิปาต",
        },
    },
    {
        "index": 20,
        "section": "an",
        "title": {
            "en": "增支部经典二 (Catukkanipāta)",
            "th": "จตุกฺกนิปาต",
        },
    },
    {
        "index": 21,
        "section": "an",
        "title": {
            "en": "增支部经典三 (Pañcakanipāta)",
            "th": "ปญฺจกนิปาต",
        },
    },
    {
        "index": 22,
        "section": "an",
        "title": {
            "en": "增支部经典四 上 (Chakka; Sattakanipāta)",
            "th": "ฉกฺก; สตฺตกนิปาต",
        },
    },
    {
        "index": 23,
        "section": "an",
        "title": {
            "en": "增支部经典五 下 (Aṭṭhakanipāta)",
            "th": "อฏฺฐกนิปาต",
        },
    },
    {
        "index": 24,
        "section": "an",
        "title": {
            "en": "增支部经典六 (Navaka; Dasakanipāta)",
            "th": "นวก; ทสกนิปาต",
        },
    },
    {
        "index": 25,
        "section": "an",
        "title": {
            "en": "增支部经典七 (Ekādasakanipāta)",
            "th": "เอกาทสกนิปาต",
        },
    },
    {
        "index": 26,
        "section": "kn",
        "title": {
            "en": "小部经典一 (Khuddakapāṭha; Dhammapada; Udāna; Itivuttaka)",
            "th": "ขุทฺทกปาฐ; ธมฺมปท; อุทาน; อิติวุตฺตก",
        },
    },
    {
        "index": 27,
        "section": "kn",
        "title": {
            "en": "小部经典二 (Suttanipāta; Vimānavatthu)",
            "th": "สุตฺตนิปาต; วิมานวตฺถุ",
        },
    },
    {
        "index": 28,
        "section": "kn",
        "title": {
            "en": "小部经典三 (Petavatthu; Theragāthā; Therīgāthā)",
            "th": "เปตวตฺถุ; เถรคาถา; เถรีคาถา",
        },
    },
    {
        "index": 29,
        "section": "kn",
        "title": {
            "en": "小部经典四 (Apadāna 1)",
            "th": "อปทาน ๑",
        },
    },
    {
        "index": 30,
        "section": "kn",
        "title": {
            "en": "小部经典五 (Apadāna 2)",
            "th": "อปทาน ๒",
        },
    },
    {
        "index": 31,
        "section": "kn",
        "title": {
            "en": "小部经典六 (Jātaka 1)",
            "th": "ชาตก ๑",
        },
    },
    {
        "index": 32,
        "section": "kn",
        "title": {
            "en": "小部经典七 (Jātaka 2)",
            "th": "ชาตก ๒",
        },
    },
    {
        "index": 33,
        "section": "kn",
        "title": {
            "en": "小部经典八 (Jātaka 3)",
            "th": "ชาตก ๓",
        },
    },
    {
        "index": 34,
        "section": "kn",
        "title": {
            "en": "小部经典九 (Jātaka 4)",
            "th": "ชาตก ๔",
        },
    },
    {
        "index": 35,
        "section": "kn",
        "title": {
            "en": "小部经典十 (Jātaka 5)",
            "th": "ชาตก ๕",
        },
    },
    {
        "index": 36,
        "section": "kn",
        "title": {
            "en": "小部经典十一 (Jātaka 6)",
            "th": "ชาตก ๖",
        },
    },
    {
        "index": 37,
        "section": "kn",
        "title": {
            "en": "小部经典十二 (Jātaka 7)",
            "th": "ชาตก ๗",
        },
    },
    {
        "index": 38,
        "section": "kn",
        "title": {
            "en": "小部经典十三 (Jātaka 8)",
            "th": "ชาตก ๘",
        },
    },
    {
        "index": 39,
        "section": "kn",
        "title": {
            "en": "小部经典十四 (Jātaka 9)",
            "th": "ชาตก ๙",
        },
    },
    {
        "index": 40,
        "section": "kn",
        "title": {
            "en": "小部经典十五 (Jātaka 10)",
            "th": "ชาตก ๑๐",
        },
    },
    {
        "index": 41,
        "section": "kn",
        "title": {
            "en": "小部经典十六 (Jātaka 11)",
            "th": "ชาตก ๑๑",
        },
    },
    {
        "index": 42,
        "section": "kn",
        "title": {
            "en": "小部经典十七 (Jātaka 12)",
            "th": "ชาตก ๑๒",
        },
    },
    {
        "index": 43,
        "section": "kn",
        "title": {
            "en": "小部经典十八 (Paṭisambhidāmagga 1)",
            "th": "ปฏิสมฺภิทามคฺค ๑",
        },
    },
    {
        "index": 44,
        "section": "kn",
        "title": {
            "en": "小部经典十九 (Paṭisambhidāmagga 2; Buddhavṃsa; Cariyāpiฎka)",
            "th": "ปฏิสมฺภิทามคฺค ๒; พุทฺธวํส; จริยาปิฎก",
        },
    },
    {
        "index": 45,
        "section": "kn",
        "title": {
            "en": "小部经典二十 (Mahānidesa 1)",
            "th": "มหานิเทส ๑",
        },
    },
    {
        "index": 46,
        "section": "kn",
        "title": {
            "en": "小部经典二十一 (Mahānidesa 2)",
            "th": "มหานิเทส ๒",
        },
    },
    {
        "index": 47,
        "section": "kn",
        "title": {
            "en": "小部经典二十二 (Cullanidesa)",
            "th": "จุลฺลนิเทส",
        },
    },
    {
        "index": 48,
        "section": "abh",
        "title": {
            "en": "法集论 (Dhammasaṅgaṇī)",
            "th": "ธมฺมสงฺคณี",
        },
    },
    {
        "index": 49,
        "section": "abh",
        "title": {
            "en": "分别论一 (Vibhaṅga 1)",
            "th": "วิภงฺค ๑",
        },
    },
    {
        "index": 50,
        "section": "abh",
        "title": {
            "en": "分别论二·界论·人施设论 (Vibhaṅga 2; Dhātukathā; Puggalapaññatti)",
            "th": "วิภงฺค ๒; ธาตุกถา; ปุคฺคลปญฺญตฺติ",
        },
    },
    {
        "index": 51,
        "section": "abh",
        "title": {
            "en": "双论一 (Yamaka 1)",
            "th": "ยมก ๑",
        },
    },
    {
        "index": 52,
        "section": "abh",
        "title": {
            "en": "双论二 (Yamaka 2)",
            "th": "ยมก ๒",
        },
    },
    {
        "index": 53,
        "section": "abh",
        "title": {
            "en": "双论三 (Yamaka 3)",
            "th": "ยมก ๓",
        },
    },
    {
        "index": 54,
        "section": "abh",
        "title": {
            "en": "发趣论一 (Paṭṭhāna 1)",
            "th": "ปฏฺฐาน ๑",
        },
    },
    {
        "index": 55,
        "section": "abh",
        "title": {
            "en": "发趣论二 (Paṭṭhāna 2)",
            "th": "ปฏฺฐาน ๒",
        },
    },
    {
        "index": 56,
        "section": "abh",
        "title": {
            "en": "发趣论三 (Paṭṭhāna 3)",
            "th": "ปฏฺฐาน ๓",
        },
    },
    {
        "index": 57,
        "section": "abh",
        "title": {
            "en": "发趣论四 (Paṭṭhāna 4)",
            "th": "ปฏฺฐาน ๔",
        },
    },
    {
        "index": 58,
        "section": "abh",
        "title": {
            "en": "发趣论五 (Paṭṭhāna 5)",
            "th": "ปฏฺฐาน ๕",
        },
    },
    {
        "index": 59,
        "section": "abh",
        "title": {
            "en": "发趣论六 (Paṭṭhāna 6)",
            "th": "ปฏฺฐาน ๖",
        },
    },
    {
        "index": 60,
        "section": "abh",
        "title": {
            "en": "发趣论七 (Paṭṭhāna 7)",
            "th": "ปฏฺฐาน ๗",
        },
    },
    {
        "index": 61,
        "section": "abh",
        "title": {
            "en": "论事一 (Kathāvatthu 1)",
            "th": "กถาวตฺถุ ๑",
        },
    },
    {
        "index": 62,
        "section": "abh",
        "title": {
            "en": "论事二 (Kathāvatthu 2)",
            "th": "กถาวตฺถุ ๒",
        },
    },
    {
        "index": 63,
        "section": "kn",
        "title": {
            "en": "弥兰王问经一 (Milindapañha 1)",
            "th": "มิลินฺทปญฺห ๑",
        },
    },
    {
        "index": 64,
        "section": "kn",
        "title": {
            "en": "弥兰王问经二 (Milindapañha 2)",
            "th": "มิลินฺทปญฺห ๒",
        },
    },
    {
        "index": 65,
        "section": "kn",
        "title": {
            "en": "岛王统史·大王统史 (Dīpavṃsa; Mahāvṃsa)",
            "th": "ทีปวํส; มหาวํส",
        },
    },
    {
        "index": 66,
        "section": "kn",
        "title": {
            "en": "小王统史 (Cullavṃsa)",
            "th": "จุลฺลวํส",
        },
    },
    {
        "index": 67,
        "section": "kn",
        "title": {
            "en": "清净道论一 (Visudadhimagga 1)",
            "th": "วิสุทธิมคฺค ๑",
        },
    },
    {
        "index": 68,
        "section": "kn",
        "title": {
            "en": "清净道论二 (Visudadhimagga 2)",
            "th": "วิสุทธิมคฺค ๒",
        },
    },
    {
        "index": 69,
        "section": "kn",
        "title": {
            "en": "清净道论三 (Visudadhimagga 3)",
            "th": "วิสุทธิมคฺค ๓",
        },
    },
    {
        "index": 70,
        "section": "kn",
        "title": {
            "en": "一切善见律注序·摄阿毗达磨义论·阿育王刻文 (Samantapāsādhikā; Abhidhammaatthasaṅgaha; Asaokalekhā)",
            "th": "สมนฺตปาสาธิกา; อภิธมฺมอตฺถสงฺคห; อสโอกเลขา",
        },
    },
    {
        "index": 71,
        "section": "kn",
        "title": {
            "en": "汉译南传大藏经总目录 --- สารบัญรวมของชุด เล่ม 71",
            "th": "汉译南传大藏经总目录 --- สารบัญรวมของชุด เล่ม 71",
        },
    },
]

# === RPO_LANNA_VOLUMES ===
# hall edition code(s): lan/lanna2556
# source: tipitaka-catalog/catalog/content/rpo-pali-lanna.tex
# count: 80
# 80 vols; order Suttanta→Abhidhamma→Vinaya (Wat Rampoeng).
RPO_LANNA_VOLUMES = [
    {
        "index": 1,
        "section": "dn",
        "title": {
            "en": "Suttantapiṭake Dīghanikāyassa Sīlakkhandhavaggo",
            "th": "สุตฺตนฺตปิฏเก ทีฆนิกายสฺส สีลกฺขนฺธวคฺโค",
        },
    },
    {
        "index": 2,
        "section": "dn",
        "title": {
            "en": "Suttantapiṭake Dīghanikāyassa Mahāvaggo [paṭhamo Bhāgo]",
            "th": "สุตฺตนฺตปิฏเก ทีฆนิกายสฺส มหาวคฺโค [ปฐโม ภาโค]",
        },
    },
    {
        "index": 3,
        "section": "dn",
        "title": {
            "en": "Suttantapiṭake Dīghanikāyassa Mahāvaggo [dutiyo Bhāgo]",
            "th": "สุตฺตนฺตปิฏเก ทีฆนิกายสฺส มหาวคฺโค [ทุติโย ภาโค]",
        },
    },
    {
        "index": 4,
        "section": "dn",
        "title": {
            "en": "Suttantapiṭake Dīghanikāyassa Pāṭikavaggo [paṭhamo Bhāgo]",
            "th": "สุตฺตนฺตปิฏเก ทีฆนิกายสฺส ปาฏิกวคฺโค [ปฐโม ภาโค]",
        },
    },
    {
        "index": 5,
        "section": "dn",
        "title": {
            "en": "Suttantapiṭake Dīghanikāyassa Pāṭikavaggo [dutiyo Bhāgo]",
            "th": "สุตฺตนฺตปิฏเก ทีฆนิกายสฺส ปาฏิกวคฺโค [ทุติโย ภาโค]",
        },
    },
    {
        "index": 6,
        "section": "mn",
        "title": {
            "en": "Suttantapiṭake Majjhimanikāyassa Mūlapaṇṇāsakṃ",
            "th": "สุตฺตนฺตปิฏเก มชฺฌิมนิกายสฺส มูลปณฺณาสกํ",
        },
    },
    {
        "index": 7,
        "section": "mn",
        "title": {
            "en": "Suttantapiṭake Majjhimanikāyassa Mūlapaṇṇāsakṃ-majjhimapaṇṇāsakṃ",
            "th": "สุตฺตนฺตปิฏเก มชฺฌิมนิกายสฺส มูลปณฺณาสกํ-มชฺฌิมปณฺณาสกํ",
        },
    },
    {
        "index": 8,
        "section": "mn",
        "title": {
            "en": "Suttantapiṭake Majjhimanikāyassa Majjhimapaṇṇāsakṃ [paṭhamo Bhāgo]",
            "th": "สุตฺตนฺตปิฏเก มชฺฌิมนิกายสฺส มชฺฌิมปณฺณาสกํ [ปฐโม ภาโค]",
        },
    },
    {
        "index": 9,
        "section": "mn",
        "title": {
            "en": "Suttantapiṭake Majjhimanikāyassa Majjhimapaṇṇāsakṃ [dutiyo Bhāgo]",
            "th": "สุตฺตนฺตปิฏเก มชฺฌิมนิกายสฺส มชฺฌิมปณฺณาสกํ [ทุติโย ภาโค]",
        },
    },
    {
        "index": 10,
        "section": "mn",
        "title": {
            "en": "Suttantapiṭake Majjhimanikāyassa Majjhimapaṇṇāsakṃ-uparipaṇṇāsakṃ",
            "th": "สุตฺตนฺตปิฏเก มชฺฌิมนิกายสฺส มชฺฌิมปณฺณาสกํ-อุปริปณฺณาสกํ",
        },
    },
    {
        "index": 11,
        "section": "mn",
        "title": {
            "en": "Suttantapiṭake Majjhimanikāyassa Uparipaṇṇāsakṃ [paṭhamo Bhāgo]",
            "th": "สุตฺตนฺตปิฏเก มชฺฌิมนิกายสฺส อุปริปณฺณาสกํ [ปฐโม ภาโค]",
        },
    },
    {
        "index": 12,
        "section": "mn",
        "title": {
            "en": "Suttantapiṭake Majjhimanikāyassa Uparipaṇṇāsakṃ [dutiyo Bhāgo]",
            "th": "สุตฺตนฺตปิฏเก มชฺฌิมนิกายสฺส อุปริปณฺณาสกํ [ทุติโย ภาโค]",
        },
    },
    {
        "index": 13,
        "section": "sn",
        "title": {
            "en": "Suttantapiṭake Sṃyuttanikāyassa Sagāthavaggo-nidānavaggo",
            "th": "สุตฺตนฺตปิฏเก สํยุตฺตนิกายสฺส สคาถวคฺโค-นิทานวคฺโค",
        },
    },
    {
        "index": 14,
        "section": "sn",
        "title": {
            "en": "Suttantapiṭake Sṃyuttanikāyassa Nidānavaggo-khandhavāravaggo",
            "th": "สุตฺตนฺตปิฏเก สํยุตฺตนิกายสฺส นิทานวคฺโค-ขนฺธวารวคฺโค",
        },
    },
    {
        "index": 15,
        "section": "sn",
        "title": {
            "en": "Suttantapiṭake Sṃyuttanikāyassa Khandhavāravaggo-saḷāyatanavaggo",
            "th": "สุตฺตนฺตปิฏเก สํยุตฺตนิกายสฺส ขนฺธวารวคฺโค-สฬายตนวคฺโค",
        },
    },
    {
        "index": 16,
        "section": "sn",
        "title": {
            "en": "Suttantapiṭake Sṃyuttanikāyassa Saḷāyatanavaggo-mahāvāravaggo",
            "th": "สุตฺตนฺตปิฏเก สํยุตฺตนิกายสฺส สฬายตนวคฺโค-มหาวารวคฺโค",
        },
    },
    {
        "index": 17,
        "section": "sn",
        "title": {
            "en": "Suttantapiṭake Sṃyuttanikāyassa Mahāvāravaggo [paṭhamo Bhāgo]",
            "th": "สุตฺตนฺตปิฏเก สํยุตฺตนิกายสฺส มหาวารวคฺโค [ปฐโม ภาโค]",
        },
    },
    {
        "index": 18,
        "section": "sn",
        "title": {
            "en": "Suttantapiṭake Sṃyuttanikāyassa Mahāvāravaggo [dutiyo Bhāgo]",
            "th": "สุตฺตนฺตปิฏเก สํยุตฺตนิกายสฺส มหาวารวคฺโค [ทุติโย ภาโค]",
        },
    },
    {
        "index": 19,
        "section": "an",
        "title": {
            "en": "Suttantapiṭake Aṅguttaranikāyassa Ekanipāta",
            "th": "สุตฺตนฺตปิฏเก องฺคุตฺตรนิกายสฺส เอกนิปาต",
        },
    },
    {
        "index": 20,
        "section": "an",
        "title": {
            "en": "Suttantapiṭake Aṅguttaranikāyassa Dukanipāta-tikanipāta",
            "th": "สุตฺตนฺตปิฏเก องฺคุตฺตรนิกายสฺส ทุกนิปาต-ติกนิปาต",
        },
    },
    {
        "index": 21,
        "section": "an",
        "title": {
            "en": "Suttantapiṭake Aṅguttaranikāyassa Tikanipāta",
            "th": "สุตฺตนฺตปิฏเก องฺคุตฺตรนิกายสฺส ติกนิปาต",
        },
    },
    {
        "index": 22,
        "section": "an",
        "title": {
            "en": "Suttantapiṭake Aṅguttaranikāyassa Catukkanipāta-pañcakanipāta",
            "th": "สุตฺตนฺตปิฏเก องฺคุตฺตรนิกายสฺส จตุกฺกนิปาต-ปญฺจกนิปาต",
        },
    },
    {
        "index": 23,
        "section": "an",
        "title": {
            "en": "Suttantapiṭake Aṅguttaranikāyassa Chakkanipāta-sattakanipāta",
            "th": "สุตฺตนฺตปิฏเก องฺคุตฺตรนิกายสฺส ฉกฺกนิปาต-สตฺตกนิปาต",
        },
    },
    {
        "index": 24,
        "section": "an",
        "title": {
            "en": "Suttantapiṭake Aṅguttaranikāyassa Sattakanipāta-aṭṭhakanipāta",
            "th": "สุตฺตนฺตปิฏเก องฺคุตฺตรนิกายสฺส สตฺตกนิปาต-อฏฺฐกนิปาต",
        },
    },
    {
        "index": 25,
        "section": "an",
        "title": {
            "en": "Suttantapiṭake Aṅguttaranikāyassa Navakanipāta-dasakanipāta",
            "th": "สุตฺตนฺตปิฏเก องฺคุตฺตรนิกายสฺส นวกนิปาต-ทสกนิปาต",
        },
    },
    {
        "index": 26,
        "section": "an",
        "title": {
            "en": "Suttantapiṭake Aṅguttaranikāyassa Ekādasanipāta-dvādasanipāta",
            "th": "สุตฺตนฺตปิฏเก องฺคุตฺตรนิกายสฺส เอกาทสนิปาต-ทฺวาทสนิปาต",
        },
    },
    {
        "index": 27,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭake Khuddakanikāyassa Khuddakapāṭha-dhammapada",
            "th": "สุตฺตนฺตปิฏเก ขุทฺทกนิกายสฺส ขุทฺทกปาฐ-ธมฺมปท",
        },
    },
    {
        "index": 28,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭake Khuddakanikāyassa Dhammapada-udāna",
            "th": "สุตฺตนฺตปิฏเก ขุทฺทกนิกายสฺส ธมฺมปท-อุทาน",
        },
    },
    {
        "index": 29,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭake Khuddakanikāyassa Itivuttaka-suttanipāta",
            "th": "สุตฺตนฺตปิฏเก ขุทฺทกนิกายสฺส อิติวุตฺตก-สุตฺตนิปาต",
        },
    },
    {
        "index": 30,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭake Khuddakanikāyassa Suttanipāta-vimānavatthu",
            "th": "สุตฺตนฺตปิฏเก ขุทฺทกนิกายสฺส สุตฺตนิปาต-วิมานวตฺถุ",
        },
    },
    {
        "index": 31,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭake Khuddakanikāyassa Petavatthu",
            "th": "สุตฺตนฺตปิฏเก ขุทฺทกนิกายสฺส เปตวตฺถุ",
        },
    },
    {
        "index": 32,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭake Khuddakanikāyassa Petavatthu-theragāthā",
            "th": "สุตฺตนฺตปิฏเก ขุทฺทกนิกายสฺส เปตวตฺถุ-เถรคาถา",
        },
    },
    {
        "index": 33,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭake Khuddakanikāyassa Jāดkṃ [paṭhamo Bhāgo] (eka-cattālīsanipāta)",
            "th": "สุตฺตนฺตปิฏเก ขุทฺทกนิกายสฺส ชาดกํ [ปฐโม ภาโค] (เอก-จตฺตาลีสนิปาต)",
        },
    },
    {
        "index": 34,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭake Khuddakanikāyassa Jāดkṃ [dutiyo Bhāgo] (eka-cattālīsanipāta)",
            "th": "สุตฺตนฺตปิฏเก ขุทฺทกนิกายสฺส ชาดกํ [ทุติโย ภาโค] (เอก-จตฺตาลีสนิปาต)",
        },
    },
    {
        "index": 35,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭake Khuddakanikāyassa Jāดkṃ [tatiyo Bhāgo] (eka-cattālīsanipāta)",
            "th": "สุตฺตนฺตปิฏเก ขุทฺทกนิกายสฺส ชาดกํ [ตติโย ภาโค] (เอก-จตฺตาลีสนิปาต)",
        },
    },
    {
        "index": 36,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭake Khuddakanikāyassa Jāดkṃ [catuttho Bhāgo] (eka-cattālīsanipāta)",
            "th": "สุตฺตนฺตปิฏเก ขุทฺทกนิกายสฺส ชาดกํ [จตุตฺโถ ภาโค] (เอก-จตฺตาลีสนิปาต)",
        },
    },
    {
        "index": 37,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭake Khuddakanikāyassa Jāดkṃ [pañcamo Bhāgo] (eka-cattālīsanipāta)",
            "th": "สุตฺตนฺตปิฏเก ขุทฺทกนิกายสฺส ชาดกํ [ปญฺจโม ภาโค] (เอก-จตฺตาลีสนิปาต)",
        },
    },
    {
        "index": 38,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭake Khuddakanikāyassa Jāดkṃ [chaṭṭho Bhāgo] (eka-cattālīsanipāta)",
            "th": "สุตฺตนฺตปิฏเก ขุทฺทกนิกายสฺส ชาดกํ [ฉฏฺโฐ ภาโค] (เอก-จตฺตาลีสนิปาต)",
        },
    },
    {
        "index": 39,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭake Khuddakanikāyassa Jāดkṃ [sattamo Bhāgo] (eka-cattālīsanipāta)",
            "th": "สุตฺตนฺตปิฏเก ขุทฺทกนิกายสฺส ชาดกํ [สตฺตโม ภาโค] (เอก-จตฺตาลีสนิปาต)",
        },
    },
    {
        "index": 40,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭake Khuddakanikāyassa Jāดkṃ [aṭṭhamo Bhāgo] (eka-cattālīsanipāta)",
            "th": "สุตฺตนฺตปิฏเก ขุทฺทกนิกายสฺส ชาดกํ [อฏฺฐโม ภาโค] (เอก-จตฺตาลีสนิปาต)",
        },
    },
    {
        "index": 41,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭake Khuddakanikāyassa Jāดkṃ [navamo Bhāgo] (eka-cattālīsanipāta)",
            "th": "สุตฺตนฺตปิฏเก ขุทฺทกนิกายสฺส ชาดกํ [นวโม ภาโค] (เอก-จตฺตาลีสนิปาต)",
        },
    },
    {
        "index": 42,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭake Khuddakanikāyassa Jāดkṃ [dasamo Bhāgo] (eka-cattālīsanipāta)",
            "th": "สุตฺตนฺตปิฏเก ขุทฺทกนิกายสฺส ชาดกํ [ทสโม ภาโค] (เอก-จตฺตาลีสนิปาต)",
        },
    },
    {
        "index": 43,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭake Khuddakanikāyassa Mahāniddeso",
            "th": "สุตฺตนฺตปิฏเก ขุทฺทกนิกายสฺส มหานิทฺเทโส",
        },
    },
    {
        "index": 44,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭake Khuddakanikāyassa Mahāniddeso-cūḷaniddeso",
            "th": "สุตฺตนฺตปิฏเก ขุทฺทกนิกายสฺส มหานิทฺเทโส-จูฬนิทฺเทโส",
        },
    },
    {
        "index": 45,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭake Khuddakanikāyassa Cūḷaniddeso-paṭisambhidāmaggo",
            "th": "สุตฺตนฺตปิฏเก ขุทฺทกนิกายสฺส จูฬนิทฺเทโส-ปฏิสมฺภิทามคฺโค",
        },
    },
    {
        "index": 46,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭake Khuddakanikāyassa Paṭisambhidāmaggo",
            "th": "สุตฺตนฺตปิฏเก ขุทฺทกนิกายสฺส ปฏิสมฺภิทามคฺโค",
        },
    },
    {
        "index": 47,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭake Khuddakanikāyassa Apadāna [paṭhamo Bhāgo]",
            "th": "สุตฺตนฺตปิฏเก ขุทฺทกนิกายสฺส อปทาน [ปฐโม ภาโค]",
        },
    },
    {
        "index": 48,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭake Khuddakanikāyassa Apadāna [dutiyo Bhāgo]",
            "th": "สุตฺตนฺตปิฏเก ขุทฺทกนิกายสฺส อปทาน [ทุติโย ภาโค]",
        },
    },
    {
        "index": 49,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭake Khuddakanikāyassa Apadāna-therīapadāna",
            "th": "สุตฺตนฺตปิฏเก ขุทฺทกนิกายสฺส อปทาน-เถรีอปทาน",
        },
    },
    {
        "index": 50,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭake Khuddakanikāyassa Buddhavṃsa [paṭhamo Bhāgo]",
            "th": "สุตฺตนฺตปิฏเก ขุทฺทกนิกายสฺส พุทฺธวํส [ปฐโม ภาโค]",
        },
    },
    {
        "index": 51,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭake Khuddakanikāyassa Buddhavṃsa [dutiyo Bhāgo]",
            "th": "สุตฺตนฺตปิฏเก ขุทฺทกนิกายสฺส พุทฺธวํส [ทุติโย ภาโค]",
        },
    },
    {
        "index": 52,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭake Khuddakanikāyassa Buddhavṃsa [tatiyo Bhāgo]",
            "th": "สุตฺตนฺตปิฏเก ขุทฺทกนิกายสฺส พุทฺธวํส [ตติโย ภาโค]",
        },
    },
    {
        "index": 53,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭake Khuddakanikāyassa Cariyāpiṭaka [paṭhamo Bhāgo]",
            "th": "สุตฺตนฺตปิฏเก ขุทฺทกนิกายสฺส จริยาปิฏก [ปฐโม ภาโค]",
        },
    },
    {
        "index": 54,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭake Khuddakanikāyassa Cariyāpiṭaka [dutiyo Bhāgo]",
            "th": "สุตฺตนฺตปิฏเก ขุทฺทกนิกายสฺส จริยาปิฏก [ทุติโย ภาโค]",
        },
    },
    {
        "index": 55,
        "section": "kn",
        "title": {
            "en": "Suttantapiṭake Khuddakanikāyassa Cariyāpiṭaka [tatiyo Bhāgo]",
            "th": "สุตฺตนฺตปิฏเก ขุทฺทกนิกายสฺส จริยาปิฏก [ตติโย ภาโค]",
        },
    },
    {
        "index": 56,
        "section": "abh",
        "title": {
            "en": "Abhidhammapiṭake Dhammasaṅgaṇi [paṭhamo Bhāgo]",
            "th": "อภิธมฺมปิฏเก ธมฺมสงฺคณิ [ปฐโม ภาโค]",
        },
    },
    {
        "index": 57,
        "section": "abh",
        "title": {
            "en": "Abhidhammapiṭake Dhammasaṅgaṇi [dutiyo Bhāgo]",
            "th": "อภิธมฺมปิฏเก ธมฺมสงฺคณิ [ทุติโย ภาโค]",
        },
    },
    {
        "index": 58,
        "section": "abh",
        "title": {
            "en": "Abhidhammapiṭake Dhammasaṅgaṇi [tatiyo Bhāgo]",
            "th": "อภิธมฺมปิฏเก ธมฺมสงฺคณิ [ตติโย ภาโค]",
        },
    },
    {
        "index": 59,
        "section": "abh",
        "title": {
            "en": "Abhidhammapiṭake Dhammasaṅgaṇi-citatuppāda",
            "th": "อภิธมฺมปิฏเก ธมฺมสงฺคณิ-จิตตุปฺปาท",
        },
    },
    {
        "index": 60,
        "section": "abh",
        "title": {
            "en": "Abhidhammapiṭake Citatuppāda [paṭhamo Bhāgo]",
            "th": "อภิธมฺมปิฏเก จิตตุปฺปาท [ปฐโม ภาโค]",
        },
    },
    {
        "index": 61,
        "section": "abh",
        "title": {
            "en": "Abhidhammapiṭake Citatuppāda [dutiyo Bhāgo]",
            "th": "อภิธมฺมปิฏเก จิตตุปฺปาท [ทุติโย ภาโค]",
        },
    },
    {
        "index": 62,
        "section": "abh",
        "title": {
            "en": "Abhidhammapiṭake Citatuppāda [tatiyo Bhāgo]",
            "th": "อภิธมฺมปิฏเก จิตตุปฺปาท [ตติโย ภาโค]",
        },
    },
    {
        "index": 63,
        "section": "abh",
        "title": {
            "en": "Abhidhammapiṭake Vibhaṅgo",
            "th": "อภิธมฺมปิฏเก วิภงฺโค",
        },
    },
    {
        "index": 64,
        "section": "abh",
        "title": {
            "en": "Abhidhammapiṭake Dhātukathā",
            "th": "อภิธมฺมปิฏเก ธาตุกถา",
        },
    },
    {
        "index": 65,
        "section": "abh",
        "title": {
            "en": "Abhidhammapiṭake Puggalapaññatti",
            "th": "อภิธมฺมปิฏเก ปุคฺคลปญฺญตฺติ",
        },
    },
    {
        "index": 66,
        "section": "abh",
        "title": {
            "en": "Abhidhammapiṭake Kathāvatthu-yamaka",
            "th": "อภิธมฺมปิฏเก กถาวตฺถุ-ยมก",
        },
    },
    {
        "index": 67,
        "section": "abh",
        "title": {
            "en": "Abhidhammapiṭake Paṭṭhānṃ",
            "th": "อภิธมฺมปิฏเก ปฏฺฐานํ",
        },
    },
    {
        "index": 68,
        "section": "vin",
        "title": {
            "en": "Vinayapiṭake Pārājikṃ [paṭhamo Bhāgo]",
            "th": "วินยปิฏเก ปาราชิกํ [ปฐโม ภาโค]",
        },
    },
    {
        "index": 69,
        "section": "vin",
        "title": {
            "en": "Vinayapiṭake Pārājikṃ [dutiyo Bhāgo]",
            "th": "วินยปิฏเก ปาราชิกํ [ทุติโย ภาโค]",
        },
    },
    {
        "index": 70,
        "section": "vin",
        "title": {
            "en": "Vinayapiṭake Pārājikṃ [tatiyo Bhāgo]",
            "th": "วินยปิฏเก ปาราชิกํ [ตติโย ภาโค]",
        },
    },
    {
        "index": 71,
        "section": "vin",
        "title": {
            "en": "Vinayapiṭake Pārājikṃ-pācitti",
            "th": "วินยปิฏเก ปาราชิกํ-ปาจิตฺติ",
        },
    },
    {
        "index": 72,
        "section": "vin",
        "title": {
            "en": "Vinayapiṭake Pācitti [paṭhamo Bhāgo]",
            "th": "วินยปิฏเก ปาจิตฺติ [ปฐโม ภาโค]",
        },
    },
    {
        "index": 73,
        "section": "vin",
        "title": {
            "en": "Vinayapiṭake Pācitti [dutiyo Bhāgo]",
            "th": "วินยปิฏเก ปาจิตฺติ [ทุติโย ภาโค]",
        },
    },
    {
        "index": 74,
        "section": "vin",
        "title": {
            "en": "Vinayapiṭake Mahāvaggo [paṭhamo Bhāgo]",
            "th": "วินยปิฏเก มหาวคฺโค [ปฐโม ภาโค]",
        },
    },
    {
        "index": 75,
        "section": "vin",
        "title": {
            "en": "Vinayapiṭake Mahāvaggo [dutiyo Bhāgo]",
            "th": "วินยปิฏเก มหาวคฺโค [ทุติโย ภาโค]",
        },
    },
    {
        "index": 76,
        "section": "vin",
        "title": {
            "en": "Vinayapiṭake Mahāvaggo [tatiyo Bhāgo]",
            "th": "วินยปิฏเก มหาวคฺโค [ตติโย ภาโค]",
        },
    },
    {
        "index": 77,
        "section": "vin",
        "title": {
            "en": "Vinayapiṭake Cullavaggo [paṭhamo Bhāgo]",
            "th": "วินยปิฏเก จุลฺลวคฺโค [ปฐโม ภาโค]",
        },
    },
    {
        "index": 78,
        "section": "vin",
        "title": {
            "en": "Vinayapiṭake Cullavaggo [dutiyo Bhāgo]",
            "th": "วินยปิฏเก จุลฺลวคฺโค [ทุติโย ภาโค]",
        },
    },
    {
        "index": 79,
        "section": "vin",
        "title": {
            "en": "Vinayapiṭake Cullavaggo-parivāra",
            "th": "วินยปิฏเก จุลฺลวคฺโค-ปริวาร",
        },
    },
    {
        "index": 80,
        "section": "vin",
        "title": {
            "en": "Vinayapiṭake Parivāra",
            "th": "วินยปิฏเก ปริวาร",
        },
    },
]

# === KHM_PALI_VOLUMES ===
# hall edition code(s): kmr/pali2472
# source: tipitaka-catalog/catalog/content/khm-pali-khmer.tex
# count: 110
# Range-based catalog expanded to 110 individual volume numbers.
KHM_PALI_VOLUMES = [
    {
        "index": 1,
        "section": "vin",
        "title": {
            "en": "Mahāvibhaṅga — Pārājika and Saṅghādisesa",
            "th": "มหาวิภังค์ --- ภาค ปาราชิก และ สังฆาทิเสส",
        },
    },
    {
        "index": 2,
        "section": "vin",
        "title": {
            "en": "Mahāvibhaṅga — Pācittiya",
            "th": "มหาวิภังค์ --- ภาค ปาจิตฺติย",
        },
    },
    {
        "index": 3,
        "section": "vin",
        "title": {
            "en": "Bhikkhunīvibhaṅga",
            "th": "ภิกฺขุนีวิภงฺค",
        },
    },
    {
        "index": 4,
        "section": "vin",
        "title": {
            "en": "Mahāvagga (vol. 4)",
            "th": "มหาวคฺค (เล่ม 4)",
        },
    },
    {
        "index": 5,
        "section": "vin",
        "title": {
            "en": "Mahāvagga (vol. 5)",
            "th": "มหาวคฺค (เล่ม 5)",
        },
    },
    {
        "index": 6,
        "section": "vin",
        "title": {
            "en": "Cūḷavagga (vol. 6)",
            "th": "จูฬวคฺค (เล่ม 6)",
        },
    },
    {
        "index": 7,
        "section": "vin",
        "title": {
            "en": "Cūḷavagga (vol. 7)",
            "th": "จูฬวคฺค (เล่ม 7)",
        },
    },
    {
        "index": 8,
        "section": "vin",
        "title": {
            "en": "Cūḷavagga (vol. 8)",
            "th": "จูฬวคฺค (เล่ม 8)",
        },
    },
    {
        "index": 9,
        "section": "vin",
        "title": {
            "en": "Parivāra (vol. 9)",
            "th": "ปริวาร (เล่ม 9)",
        },
    },
    {
        "index": 10,
        "section": "vin",
        "title": {
            "en": "Parivāra (vol. 10)",
            "th": "ปริวาร (เล่ม 10)",
        },
    },
    {
        "index": 11,
        "section": "vin",
        "title": {
            "en": "Parivāra (vol. 11)",
            "th": "ปริวาร (เล่ม 11)",
        },
    },
    {
        "index": 12,
        "section": "vin",
        "title": {
            "en": "Parivāra (vol. 12)",
            "th": "ปริวาร (เล่ม 12)",
        },
    },
    {
        "index": 13,
        "section": "vin",
        "title": {
            "en": "Parivāra (vol. 13)",
            "th": "ปริวาร (เล่ม 13)",
        },
    },
    {
        "index": 14,
        "section": "dn",
        "title": {
            "en": "Sīlakkhandhavagga (vol. 14)",
            "th": "สีลกฺขนฺธวคฺค (เล่ม 14)",
        },
    },
    {
        "index": 15,
        "section": "dn",
        "title": {
            "en": "Sīlakkhandhavagga (vol. 15)",
            "th": "สีลกฺขนฺธวคฺค (เล่ม 15)",
        },
    },
    {
        "index": 16,
        "section": "dn",
        "title": {
            "en": "Mahāvagga (vol. 16)",
            "th": "มหาวคฺค (เล่ม 16)",
        },
    },
    {
        "index": 17,
        "section": "dn",
        "title": {
            "en": "Mahāvagga (vol. 17)",
            "th": "มหาวคฺค (เล่ม 17)",
        },
    },
    {
        "index": 18,
        "section": "dn",
        "title": {
            "en": "Pāṭikavagga (vol. 18)",
            "th": "ปาฏิกวคฺค (เล่ม 18)",
        },
    },
    {
        "index": 19,
        "section": "dn",
        "title": {
            "en": "Pāṭikavagga (vol. 19)",
            "th": "ปาฏิกวคฺค (เล่ม 19)",
        },
    },
    {
        "index": 20,
        "section": "mn",
        "title": {
            "en": "Mūlapaṇṇāsaka (vol. 20)",
            "th": "มูลปณฺณาสก (เล่ม 20)",
        },
    },
    {
        "index": 21,
        "section": "mn",
        "title": {
            "en": "Mūlapaṇṇāsaka (vol. 21)",
            "th": "มูลปณฺณาสก (เล่ม 21)",
        },
    },
    {
        "index": 22,
        "section": "mn",
        "title": {
            "en": "Mūlapaṇṇāsaka (vol. 22)",
            "th": "มูลปณฺณาสก (เล่ม 22)",
        },
    },
    {
        "index": 23,
        "section": "mn",
        "title": {
            "en": "Majjhimapaṇṇāsaka (vol. 23)",
            "th": "มชฺฌิมปณฺณาสก (เล่ม 23)",
        },
    },
    {
        "index": 24,
        "section": "mn",
        "title": {
            "en": "Majjhimapaṇṇāsaka (vol. 24)",
            "th": "มชฺฌิมปณฺณาสก (เล่ม 24)",
        },
    },
    {
        "index": 25,
        "section": "mn",
        "title": {
            "en": "Majjhimapaṇṇāsaka (vol. 25)",
            "th": "มชฺฌิมปณฺณาสก (เล่ม 25)",
        },
    },
    {
        "index": 26,
        "section": "mn",
        "title": {
            "en": "Uparipaṇṇāsaka (vol. 26)",
            "th": "อุปริปณฺณาสก (เล่ม 26)",
        },
    },
    {
        "index": 27,
        "section": "mn",
        "title": {
            "en": "Uparipaṇṇāsaka (vol. 27)",
            "th": "อุปริปณฺณาสก (เล่ม 27)",
        },
    },
    {
        "index": 28,
        "section": "mn",
        "title": {
            "en": "Uparipaṇṇāsaka (vol. 28)",
            "th": "อุปริปณฺณาสก (เล่ม 28)",
        },
    },
    {
        "index": 29,
        "section": "sn",
        "title": {
            "en": "Sagāthavagga (vol. 29)",
            "th": "สคาถวคฺค (เล่ม 29)",
        },
    },
    {
        "index": 30,
        "section": "sn",
        "title": {
            "en": "Sagāthavagga (vol. 30)",
            "th": "สคาถวคฺค (เล่ม 30)",
        },
    },
    {
        "index": 31,
        "section": "sn",
        "title": {
            "en": "Nidānavagga (vol. 31)",
            "th": "นิทานวคฺค (เล่ม 31)",
        },
    },
    {
        "index": 32,
        "section": "sn",
        "title": {
            "en": "Nidānavagga (vol. 32)",
            "th": "นิทานวคฺค (เล่ม 32)",
        },
    },
    {
        "index": 33,
        "section": "sn",
        "title": {
            "en": "Khandhavāravagga (vol. 33)",
            "th": "ขนฺธวารวคฺค (เล่ม 33)",
        },
    },
    {
        "index": 34,
        "section": "sn",
        "title": {
            "en": "Khandhavāravagga (vol. 34)",
            "th": "ขนฺธวารวคฺค (เล่ม 34)",
        },
    },
    {
        "index": 35,
        "section": "sn",
        "title": {
            "en": "Saḷāyatanavagga (vol. 35)",
            "th": "สฬายตนวคฺค (เล่ม 35)",
        },
    },
    {
        "index": 36,
        "section": "sn",
        "title": {
            "en": "Saḷāyatanavagga (vol. 36)",
            "th": "สฬายตนวคฺค (เล่ม 36)",
        },
    },
    {
        "index": 37,
        "section": "sn",
        "title": {
            "en": "Saḷāyatanavagga (vol. 37)",
            "th": "สฬายตนวคฺค (เล่ม 37)",
        },
    },
    {
        "index": 38,
        "section": "sn",
        "title": {
            "en": "Mahāvāravagga (vol. 38)",
            "th": "มหาวารวคฺค (เล่ม 38)",
        },
    },
    {
        "index": 39,
        "section": "sn",
        "title": {
            "en": "Mahāvāravagga (vol. 39)",
            "th": "มหาวารวคฺค (เล่ม 39)",
        },
    },
    {
        "index": 40,
        "section": "an",
        "title": {
            "en": "Ekaka–Duka–Tika Nipāta (vol. 40)",
            "th": "เอกก-ทุก-ติกนิปาต (เล่ม 40)",
        },
    },
    {
        "index": 41,
        "section": "an",
        "title": {
            "en": "Ekaka–Duka–Tika Nipāta (vol. 41)",
            "th": "เอกก-ทุก-ติกนิปาต (เล่ม 41)",
        },
    },
    {
        "index": 42,
        "section": "an",
        "title": {
            "en": "Catukka Nipāta (vol. 42)",
            "th": "จตุกฺกนิปาต (เล่ม 42)",
        },
    },
    {
        "index": 43,
        "section": "an",
        "title": {
            "en": "Catukka Nipāta (vol. 43)",
            "th": "จตุกฺกนิปาต (เล่ม 43)",
        },
    },
    {
        "index": 44,
        "section": "an",
        "title": {
            "en": "Pañcaka–Chakka Nipāta (vol. 44)",
            "th": "ปญฺจก-ฉกฺกนิปาต (เล่ม 44)",
        },
    },
    {
        "index": 45,
        "section": "an",
        "title": {
            "en": "Pañcaka–Chakka Nipāta (vol. 45)",
            "th": "ปญฺจก-ฉกฺกนิปาต (เล่ม 45)",
        },
    },
    {
        "index": 46,
        "section": "an",
        "title": {
            "en": "Sattaka–Aṭṭhaka–Navaka Nipāta (vol. 46)",
            "th": "สตฺตก-อฏฺฐก-นวกนิปาต (เล่ม 46)",
        },
    },
    {
        "index": 47,
        "section": "an",
        "title": {
            "en": "Sattaka–Aṭṭhaka–Navaka Nipāta (vol. 47)",
            "th": "สตฺตก-อฏฺฐก-นวกนิปาต (เล่ม 47)",
        },
    },
    {
        "index": 48,
        "section": "an",
        "title": {
            "en": "Sattaka–Aṭṭhaka–Navaka Nipāta (vol. 48)",
            "th": "สตฺตก-อฏฺฐก-นวกนิปาต (เล่ม 48)",
        },
    },
    {
        "index": 49,
        "section": "an",
        "title": {
            "en": "Dasaka–Ekādasaka Nipāta (vol. 49)",
            "th": "ทสก-เอกาทสกนิปาต (เล่ม 49)",
        },
    },
    {
        "index": 50,
        "section": "an",
        "title": {
            "en": "Dasaka–Ekādasaka Nipāta (vol. 50)",
            "th": "ทสก-เอกาทสกนิปาต (เล่ม 50)",
        },
    },
    {
        "index": 51,
        "section": "an",
        "title": {
            "en": "Dasaka–Ekādasaka Nipāta (vol. 51)",
            "th": "ทสก-เอกาทสกนิปาต (เล่ม 51)",
        },
    },
    {
        "index": 52,
        "section": "kn",
        "title": {
            "en": "Khuddakapāṭha · Dhammapada · Udāna",
            "th": "ขุทฺทกปาถ · ธมฺมปท · อุทาน",
        },
    },
    {
        "index": 53,
        "section": "kn",
        "title": {
            "en": "Itivuttaka",
            "th": "อิติวุตฺตก",
        },
    },
    {
        "index": 54,
        "section": "kn",
        "title": {
            "en": "Suttanipāta",
            "th": "สุตฺตนิปาต",
        },
    },
    {
        "index": 55,
        "section": "kn",
        "title": {
            "en": "Vimānavatthu",
            "th": "วิมานวตฺถุ",
        },
    },
    {
        "index": 56,
        "section": "kn",
        "title": {
            "en": "Petavatthu · Theragāthā",
            "th": "เปตวตฺถุ · เถรคาถา",
        },
    },
    {
        "index": 57,
        "section": "kn",
        "title": {
            "en": "Therīgāthā",
            "th": "เถรีคาถา",
        },
    },
    {
        "index": 58,
        "section": "kn",
        "title": {
            "en": "Jātaka (vol. 58)",
            "th": "ชาตก --- 6 เล่ม (เล่ม 58)",
        },
    },
    {
        "index": 59,
        "section": "kn",
        "title": {
            "en": "Jātaka (vol. 59)",
            "th": "ชาตก --- 6 เล่ม (เล่ม 59)",
        },
    },
    {
        "index": 60,
        "section": "kn",
        "title": {
            "en": "Jātaka (vol. 60)",
            "th": "ชาตก --- 6 เล่ม (เล่ม 60)",
        },
    },
    {
        "index": 61,
        "section": "kn",
        "title": {
            "en": "Jātaka (vol. 61)",
            "th": "ชาตก --- 6 เล่ม (เล่ม 61)",
        },
    },
    {
        "index": 62,
        "section": "kn",
        "title": {
            "en": "Jātaka (vol. 62)",
            "th": "ชาตก --- 6 เล่ม (เล่ม 62)",
        },
    },
    {
        "index": 63,
        "section": "kn",
        "title": {
            "en": "Jātaka (vol. 63)",
            "th": "ชาตก --- 6 เล่ม (เล่ม 63)",
        },
    },
    {
        "index": 64,
        "section": "kn",
        "title": {
            "en": "Mahāniddesa (vol. 64)",
            "th": "มหานิทฺเทส --- 3 เล่ม (เล่ม 64)",
        },
    },
    {
        "index": 65,
        "section": "kn",
        "title": {
            "en": "Mahāniddesa (vol. 65)",
            "th": "มหานิทฺเทส --- 3 เล่ม (เล่ม 65)",
        },
    },
    {
        "index": 66,
        "section": "kn",
        "title": {
            "en": "Mahāniddesa (vol. 66)",
            "th": "มหานิทฺเทส --- 3 เล่ม (เล่ม 66)",
        },
    },
    {
        "index": 67,
        "section": "kn",
        "title": {
            "en": "Cullaniddesa (vol. 67)",
            "th": "จุลฺลนิทฺเทส --- 2 เล่ม (เล่ม 67)",
        },
    },
    {
        "index": 68,
        "section": "kn",
        "title": {
            "en": "Cullaniddesa (vol. 68)",
            "th": "จุลฺลนิทฺเทส --- 2 เล่ม (เล่ม 68)",
        },
    },
    {
        "index": 69,
        "section": "kn",
        "title": {
            "en": "Paṭisambhidāmagga (vol. 69)",
            "th": "ปฏิสมฺภิทามคฺค --- 3 เล่ม (เล่ม 69)",
        },
    },
    {
        "index": 70,
        "section": "kn",
        "title": {
            "en": "Paṭisambhidāmagga (vol. 70)",
            "th": "ปฏิสมฺภิทามคฺค --- 3 เล่ม (เล่ม 70)",
        },
    },
    {
        "index": 71,
        "section": "kn",
        "title": {
            "en": "Paṭisambhidāmagga (vol. 71)",
            "th": "ปฏิสมฺภิทามคฺค --- 3 เล่ม (เล่ม 71)",
        },
    },
    {
        "index": 72,
        "section": "kn",
        "title": {
            "en": "Apadāna (vol. 72)",
            "th": "อปทาน --- 5 เล่ม (เล่ม 72)",
        },
    },
    {
        "index": 73,
        "section": "kn",
        "title": {
            "en": "Apadāna (vol. 73)",
            "th": "อปทาน --- 5 เล่ม (เล่ม 73)",
        },
    },
    {
        "index": 74,
        "section": "kn",
        "title": {
            "en": "Apadāna (vol. 74)",
            "th": "อปทาน --- 5 เล่ม (เล่ม 74)",
        },
    },
    {
        "index": 75,
        "section": "kn",
        "title": {
            "en": "Apadāna (vol. 75)",
            "th": "อปทาน --- 5 เล่ม (เล่ม 75)",
        },
    },
    {
        "index": 76,
        "section": "kn",
        "title": {
            "en": "Apadāna (vol. 76)",
            "th": "อปทาน --- 5 เล่ม (เล่ม 76)",
        },
    },
    {
        "index": 77,
        "section": "kn",
        "title": {
            "en": "Buddhavaṃsa · Cariyāpiṭaka",
            "th": "พุทฺธวํส · จริยาปิฏก",
        },
    },
    {
        "index": 78,
        "section": "abh",
        "title": {
            "en": "Dhammasaṅgaṇī (vol. 78)",
            "th": "ธมฺมสงฺคณี (เล่ม 78)",
        },
    },
    {
        "index": 79,
        "section": "abh",
        "title": {
            "en": "Dhammasaṅgaṇī (vol. 79)",
            "th": "ธมฺมสงฺคณี (เล่ม 79)",
        },
    },
    {
        "index": 80,
        "section": "abh",
        "title": {
            "en": "Vibhaṅga (vol. 80)",
            "th": "วิภงฺค (เล่ม 80)",
        },
    },
    {
        "index": 81,
        "section": "abh",
        "title": {
            "en": "Vibhaṅga (vol. 81)",
            "th": "วิภงฺค (เล่ม 81)",
        },
    },
    {
        "index": 82,
        "section": "abh",
        "title": {
            "en": "Vibhaṅga (vol. 82)",
            "th": "วิภงฺค (เล่ม 82)",
        },
    },
    {
        "index": 83,
        "section": "abh",
        "title": {
            "en": "Dhātukathā · Puggalapaññatti",
            "th": "ธาตุกถา · ปุคฺคลปญฺญตฺติ",
        },
    },
    {
        "index": 84,
        "section": "abh",
        "title": {
            "en": "Kathāvatthu (vol. 84)",
            "th": "กถาวตฺถุ (เล่ม 84)",
        },
    },
    {
        "index": 85,
        "section": "abh",
        "title": {
            "en": "Kathāvatthu (vol. 85)",
            "th": "กถาวตฺถุ (เล่ม 85)",
        },
    },
    {
        "index": 86,
        "section": "abh",
        "title": {
            "en": "Kathāvatthu (vol. 86)",
            "th": "กถาวตฺถุ (เล่ม 86)",
        },
    },
    {
        "index": 87,
        "section": "abh",
        "title": {
            "en": "Yamaka (vol. 87)",
            "th": "ยมก --- 7 เล่ม (เล่ม 87)",
        },
    },
    {
        "index": 88,
        "section": "abh",
        "title": {
            "en": "Yamaka (vol. 88)",
            "th": "ยมก --- 7 เล่ม (เล่ม 88)",
        },
    },
    {
        "index": 89,
        "section": "abh",
        "title": {
            "en": "Yamaka (vol. 89)",
            "th": "ยมก --- 7 เล่ม (เล่ม 89)",
        },
    },
    {
        "index": 90,
        "section": "abh",
        "title": {
            "en": "Yamaka (vol. 90)",
            "th": "ยมก --- 7 เล่ม (เล่ม 90)",
        },
    },
    {
        "index": 91,
        "section": "abh",
        "title": {
            "en": "Yamaka (vol. 91)",
            "th": "ยมก --- 7 เล่ม (เล่ม 91)",
        },
    },
    {
        "index": 92,
        "section": "abh",
        "title": {
            "en": "Yamaka (vol. 92)",
            "th": "ยมก --- 7 เล่ม (เล่ม 92)",
        },
    },
    {
        "index": 93,
        "section": "abh",
        "title": {
            "en": "Yamaka (vol. 93)",
            "th": "ยมก --- 7 เล่ม (เล่ม 93)",
        },
    },
    {
        "index": 94,
        "section": "abh",
        "title": {
            "en": "Paṭṭhāna (vol. 94)",
            "th": "ปฏฺฐาน --- 17 เล่ม (เล่ม 94)",
        },
    },
    {
        "index": 95,
        "section": "abh",
        "title": {
            "en": "Paṭṭhāna (vol. 95)",
            "th": "ปฏฺฐาน --- 17 เล่ม (เล่ม 95)",
        },
    },
    {
        "index": 96,
        "section": "abh",
        "title": {
            "en": "Paṭṭhāna (vol. 96)",
            "th": "ปฏฺฐาน --- 17 เล่ม (เล่ม 96)",
        },
    },
    {
        "index": 97,
        "section": "abh",
        "title": {
            "en": "Paṭṭhāna (vol. 97)",
            "th": "ปฏฺฐาน --- 17 เล่ม (เล่ม 97)",
        },
    },
    {
        "index": 98,
        "section": "abh",
        "title": {
            "en": "Paṭṭhāna (vol. 98)",
            "th": "ปฏฺฐาน --- 17 เล่ม (เล่ม 98)",
        },
    },
    {
        "index": 99,
        "section": "abh",
        "title": {
            "en": "Paṭṭhāna (vol. 99)",
            "th": "ปฏฺฐาน --- 17 เล่ม (เล่ม 99)",
        },
    },
    {
        "index": 100,
        "section": "abh",
        "title": {
            "en": "Paṭṭhāna (vol. 100)",
            "th": "ปฏฺฐาน --- 17 เล่ม (เล่ม 100)",
        },
    },
    {
        "index": 101,
        "section": "abh",
        "title": {
            "en": "Paṭṭhāna (vol. 101)",
            "th": "ปฏฺฐาน --- 17 เล่ม (เล่ม 101)",
        },
    },
    {
        "index": 102,
        "section": "abh",
        "title": {
            "en": "Paṭṭhāna (vol. 102)",
            "th": "ปฏฺฐาน --- 17 เล่ม (เล่ม 102)",
        },
    },
    {
        "index": 103,
        "section": "abh",
        "title": {
            "en": "Paṭṭhāna (vol. 103)",
            "th": "ปฏฺฐาน --- 17 เล่ม (เล่ม 103)",
        },
    },
    {
        "index": 104,
        "section": "abh",
        "title": {
            "en": "Paṭṭhāna (vol. 104)",
            "th": "ปฏฺฐาน --- 17 เล่ม (เล่ม 104)",
        },
    },
    {
        "index": 105,
        "section": "abh",
        "title": {
            "en": "Paṭṭhāna (vol. 105)",
            "th": "ปฏฺฐาน --- 17 เล่ม (เล่ม 105)",
        },
    },
    {
        "index": 106,
        "section": "abh",
        "title": {
            "en": "Paṭṭhāna (vol. 106)",
            "th": "ปฏฺฐาน --- 17 เล่ม (เล่ม 106)",
        },
    },
    {
        "index": 107,
        "section": "abh",
        "title": {
            "en": "Paṭṭhāna (vol. 107)",
            "th": "ปฏฺฐาน --- 17 เล่ม (เล่ม 107)",
        },
    },
    {
        "index": 108,
        "section": "abh",
        "title": {
            "en": "Paṭṭhāna (vol. 108)",
            "th": "ปฏฺฐาน --- 17 เล่ม (เล่ม 108)",
        },
    },
    {
        "index": 109,
        "section": "abh",
        "title": {
            "en": "Paṭṭhāna (vol. 109)",
            "th": "ปฏฺฐาน --- 17 เล่ม (เล่ม 109)",
        },
    },
    {
        "index": 110,
        "section": "abh",
        "title": {
            "en": "Paṭṭhāna (vol. 110)",
            "th": "ปฏฺฐาน --- 17 เล่ม (เล่ม 110)",
        },
    },
]


# === SDB_THAI_VOLUMES ===
# hall edition code(s): th2528
# source: tipitaka-catalog/catalog/content/sdb-pali-thai.tex
# count: 100
# Titles aligned to printed 100-vol list (คัมภีร์/นิกาย prefixes);
# ranges expanded to 1–100 with ภาค for multi-volume titles.
SDB_THAI_VOLUMES = [
    {
        "index": 1,
        "section": "vin",
        "title": {
            "en": 'Ādikamma, Part 1',
            "th": 'คัมภีร์อาทิกรรม ภาค ๑',
        },
    },
    {
        "index": 2,
        "section": "vin",
        "title": {
            "en": 'Ādikamma, Part 2',
            "th": 'คัมภีร์อาทิกรรม ภาค ๒',
        },
    },
    {
        "index": 3,
        "section": "vin",
        "title": {
            "en": 'Pācittiya, Part 1',
            "th": 'คัมภีร์ปาจิตตีย์ ภาค ๑',
        },
    },
    {
        "index": 4,
        "section": "vin",
        "title": {
            "en": 'Pācittiya, Part 2',
            "th": 'คัมภีร์ปาจิตตีย์ ภาค ๒',
        },
    },
    {
        "index": 5,
        "section": "vin",
        "title": {
            "en": 'Mahāvagga, Part 1',
            "th": 'คัมภีร์มหาวรรค ภาค ๑',
        },
    },
    {
        "index": 6,
        "section": "vin",
        "title": {
            "en": 'Mahāvagga, Part 2',
            "th": 'คัมภีร์มหาวรรค ภาค ๒',
        },
    },
    {
        "index": 7,
        "section": "vin",
        "title": {
            "en": 'Cullavagga, Part 1',
            "th": 'คัมภีร์จุลวรรค ภาค ๑',
        },
    },
    {
        "index": 8,
        "section": "vin",
        "title": {
            "en": 'Cullavagga, Part 2',
            "th": 'คัมภีร์จุลวรรค ภาค ๒',
        },
    },
    {
        "index": 9,
        "section": "vin",
        "title": {
            "en": 'Parivāra, Part 1',
            "th": 'คัมภีร์ปริวาร ภาค ๑',
        },
    },
    {
        "index": 10,
        "section": "vin",
        "title": {
            "en": 'Parivāra, Part 2',
            "th": 'คัมภีร์ปริวาร ภาค ๒',
        },
    },
    {
        "index": 11,
        "section": "dn",
        "title": {
            "en": 'Dīghanikāya Sīlakkhandhavagga, Part 1',
            "th": 'ทีฆนิกาย สีลขันธวรรค ภาค ๑',
        },
    },
    {
        "index": 12,
        "section": "dn",
        "title": {
            "en": 'Dīghanikāya Sīlakkhandhavagga, Part 2',
            "th": 'ทีฆนิกาย สีลขันธวรรค ภาค ๒',
        },
    },
    {
        "index": 13,
        "section": "dn",
        "title": {
            "en": 'Dīghanikāya Mahāvagga, Part 1',
            "th": 'ทีฆนิกาย มหาวรรค ภาค ๑',
        },
    },
    {
        "index": 14,
        "section": "dn",
        "title": {
            "en": 'Dīghanikāya Mahāvagga, Part 2',
            "th": 'ทีฆนิกาย มหาวรรค ภาค ๒',
        },
    },
    {
        "index": 15,
        "section": "dn",
        "title": {
            "en": 'Dīghanikāya Pāṭikavagga, Part 1',
            "th": 'ทีฆนิกาย ปาฏิกวรรค ภาค ๑',
        },
    },
    {
        "index": 16,
        "section": "dn",
        "title": {
            "en": 'Dīghanikāya Pāṭikavagga, Part 2',
            "th": 'ทีฆนิกาย ปาฏิกวรรค ภาค ๒',
        },
    },
    {
        "index": 17,
        "section": "mn",
        "title": {
            "en": 'Majjhimanikāya Mūlapaṇṇāsaka, Part 1',
            "th": 'มัชฌิมนิกาย มูลปัณณาสก์ ภาค ๑',
        },
    },
    {
        "index": 18,
        "section": "mn",
        "title": {
            "en": 'Majjhimanikāya Mūlapaṇṇāsaka, Part 2',
            "th": 'มัชฌิมนิกาย มูลปัณณาสก์ ภาค ๒',
        },
    },
    {
        "index": 19,
        "section": "mn",
        "title": {
            "en": 'Majjhimanikāya Majjhimapaṇṇāsaka, Part 1',
            "th": 'มัชฌิมนิกาย มัชฌิมปัณณาสก์ ภาค ๑',
        },
    },
    {
        "index": 20,
        "section": "mn",
        "title": {
            "en": 'Majjhimanikāya Majjhimapaṇṇāsaka, Part 2',
            "th": 'มัชฌิมนิกาย มัชฌิมปัณณาสก์ ภาค ๒',
        },
    },
    {
        "index": 21,
        "section": "mn",
        "title": {
            "en": 'Majjhimanikāya Uparipaṇṇāsaka, Part 1',
            "th": 'มัชฌิมนิกาย อุปริปัณณาสก์ ภาค ๑',
        },
    },
    {
        "index": 22,
        "section": "mn",
        "title": {
            "en": 'Majjhimanikāya Uparipaṇṇāsaka, Part 2',
            "th": 'มัชฌิมนิกาย อุปริปัณณาสก์ ภาค ๒',
        },
    },
    {
        "index": 23,
        "section": "sn",
        "title": {
            "en": 'Saṃyuttanikāya Sagāthavagga, Part 1',
            "th": 'สังยุตตนิกาย สคาถวรรค ภาค ๑',
        },
    },
    {
        "index": 24,
        "section": "sn",
        "title": {
            "en": 'Saṃyuttanikāya Sagāthavagga, Part 2',
            "th": 'สังยุตตนิกาย สคาถวรรค ภาค ๒',
        },
    },
    {
        "index": 25,
        "section": "sn",
        "title": {
            "en": 'Saṃyuttanikāya Nidāna Khandhavagga, Part 1',
            "th": 'สังยุตตนิกาย นิทาน ขันธวรรค ภาค ๑',
        },
    },
    {
        "index": 26,
        "section": "sn",
        "title": {
            "en": 'Saṃyuttanikāya Nidāna Khandhavagga, Part 2',
            "th": 'สังยุตตนิกาย นิทาน ขันธวรรค ภาค ๒',
        },
    },
    {
        "index": 27,
        "section": "sn",
        "title": {
            "en": 'Saṃyuttanikāya Nidāna Khandhavagga, Part 3',
            "th": 'สังยุตตนิกาย นิทาน ขันธวรรค ภาค ๓',
        },
    },
    {
        "index": 28,
        "section": "sn",
        "title": {
            "en": 'Saṃyuttanikāya Saḷāyatanavagga, Part 1',
            "th": 'สังยุตตนิกาย สฬายตนวรรค ภาค ๑',
        },
    },
    {
        "index": 29,
        "section": "sn",
        "title": {
            "en": 'Saṃyuttanikāya Saḷāyatanavagga, Part 2',
            "th": 'สังยุตตนิกาย สฬายตนวรรค ภาค ๒',
        },
    },
    {
        "index": 30,
        "section": "sn",
        "title": {
            "en": 'Saṃyuttanikāya Mahāvāravagga, Part 1',
            "th": 'สังยุตตนิกาย มหาวารวรรค ภาค ๑',
        },
    },
    {
        "index": 31,
        "section": "sn",
        "title": {
            "en": 'Saṃyuttanikāya Mahāvāravagga, Part 2',
            "th": 'สังยุตตนิกาย มหาวารวรรค ภาค ๒',
        },
    },
    {
        "index": 32,
        "section": "sn",
        "title": {
            "en": 'Saṃyuttanikāya Mahāvāravagga, Part 3',
            "th": 'สังยุตตนิกาย มหาวารวรรค ภาค ๓',
        },
    },
    {
        "index": 33,
        "section": "an",
        "title": {
            "en": 'Eka and Duka Nipāta, Part 1',
            "th": 'เอกนิบาต กับทุกนิบาต ภาค ๑',
        },
    },
    {
        "index": 34,
        "section": "an",
        "title": {
            "en": 'Eka and Duka Nipāta, Part 2',
            "th": 'เอกนิบาต กับทุกนิบาต ภาค ๒',
        },
    },
    {
        "index": 35,
        "section": "an",
        "title": {
            "en": 'Eka and Duka Nipāta, Part 3',
            "th": 'เอกนิบาต กับทุกนิบาต ภาค ๓',
        },
    },
    {
        "index": 36,
        "section": "an",
        "title": {
            "en": 'Aṅguttaranikāya Tika Nipāta',
            "th": 'อังคุตตรนิกาย ติกนิบาต',
        },
    },
    {
        "index": 37,
        "section": "an",
        "title": {
            "en": 'Aṅguttaranikāya Catukka Nipāta, Part 1',
            "th": 'อังคุตตรนิกาย จตุกกนิบาต ภาค ๑',
        },
    },
    {
        "index": 38,
        "section": "an",
        "title": {
            "en": 'Aṅguttaranikāya Catukka Nipāta, Part 2',
            "th": 'อังคุตตรนิกาย จตุกกนิบาต ภาค ๒',
        },
    },
    {
        "index": 39,
        "section": "an",
        "title": {
            "en": 'Aṅguttaranikāya Pañcaka Nipāta, Part 1',
            "th": 'อังคุตตรนิกาย ปัญจกนิบาต ภาค ๑',
        },
    },
    {
        "index": 40,
        "section": "an",
        "title": {
            "en": 'Aṅguttaranikāya Pañcaka Nipāta, Part 2',
            "th": 'อังคุตตรนิกาย ปัญจกนิบาต ภาค ๒',
        },
    },
    {
        "index": 41,
        "section": "an",
        "title": {
            "en": 'Aṅguttaranikāya Chakka Nipāta',
            "th": 'อังคุตตรนิกาย ฉักกนิบาต',
        },
    },
    {
        "index": 42,
        "section": "an",
        "title": {
            "en": 'Aṅguttaranikāya Sattaka-Aṭṭha-Navaka Nipāta, Part 1',
            "th": 'อังคุตตรนิกาย สัตตก-อัฏฐ-นวกนิบาต ภาค ๑',
        },
    },
    {
        "index": 43,
        "section": "an",
        "title": {
            "en": 'Aṅguttaranikāya Sattaka-Aṭṭha-Navaka Nipāta, Part 2',
            "th": 'อังคุตตรนิกาย สัตตก-อัฏฐ-นวกนิบาต ภาค ๒',
        },
    },
    {
        "index": 44,
        "section": "an",
        "title": {
            "en": 'Aṅguttaranikāya Dasaka Nipāta, Part 1',
            "th": 'อังคุตตรนิกาย ทสกนิบาต ภาค ๑',
        },
    },
    {
        "index": 45,
        "section": "an",
        "title": {
            "en": 'Aṅguttaranikāya Dasaka Nipāta, Part 2',
            "th": 'อังคุตตรนิกาย ทสกนิบาต ภาค ๒',
        },
    },
    {
        "index": 46,
        "section": "an",
        "title": {
            "en": 'Aṅguttaranikāya Ekādasaka Nipāta',
            "th": 'อังคุตตรนิกาย เอกาทสกนิบาต',
        },
    },
    {
        "index": 47,
        "section": "kn",
        "title": {
            "en": 'Khuddakanikāya Khuddakapāṭha',
            "th": 'ขุททกนิกาย ขุททกปาฐะ',
        },
    },
    {
        "index": 48,
        "section": "kn",
        "title": {
            "en": 'Khuddakanikāya Dhammapada, Part 1',
            "th": 'ขุททกนิกาย ธรรมบท ภาค ๑',
        },
    },
    {
        "index": 49,
        "section": "kn",
        "title": {
            "en": 'Khuddakanikāya Dhammapada, Part 2',
            "th": 'ขุททกนิกาย ธรรมบท ภาค ๒',
        },
    },
    {
        "index": 50,
        "section": "kn",
        "title": {
            "en": 'Khuddakanikāya Dhammapada, Part 3',
            "th": 'ขุททกนิกาย ธรรมบท ภาค ๓',
        },
    },
    {
        "index": 51,
        "section": "kn",
        "title": {
            "en": 'Khuddakanikāya Dhammapada, Part 4',
            "th": 'ขุททกนิกาย ธรรมบท ภาค ๔',
        },
    },
    {
        "index": 52,
        "section": "kn",
        "title": {
            "en": 'Khuddakanikāya Dhammapada, Part 5',
            "th": 'ขุททกนิกาย ธรรมบท ภาค ๕',
        },
    },
    {
        "index": 53,
        "section": "kn",
        "title": {
            "en": 'Khuddakanikāya Udāna',
            "th": 'ขุททกนิกาย พุทธอุทาน',
        },
    },
    {
        "index": 54,
        "section": "kn",
        "title": {
            "en": 'Khuddakanikāya Itivuttaka, Part 1',
            "th": 'ขุททกนิกาย อิติวุตตก ภาค ๑',
        },
    },
    {
        "index": 55,
        "section": "kn",
        "title": {
            "en": 'Khuddakanikāya Itivuttaka, Part 2',
            "th": 'ขุททกนิกาย อิติวุตตก ภาค ๒',
        },
    },
    {
        "index": 56,
        "section": "kn",
        "title": {
            "en": 'Khuddakanikāya Suttanipāta, Part 1',
            "th": 'ขุททกนิกาย สุตตนิบาต ภาค ๑',
        },
    },
    {
        "index": 57,
        "section": "kn",
        "title": {
            "en": 'Khuddakanikāya Suttanipāta, Part 2',
            "th": 'ขุททกนิกาย สุตตนิบาต ภาค ๒',
        },
    },
    {
        "index": 58,
        "section": "kn",
        "title": {
            "en": 'Khuddakanikāya Suttanipāta, Part 3',
            "th": 'ขุททกนิกาย สุตตนิบาต ภาค ๓',
        },
    },
    {
        "index": 59,
        "section": "kn",
        "title": {
            "en": 'Khuddakanikāya Suttanipāta, Part 4',
            "th": 'ขุททกนิกาย สุตตนิบาต ภาค ๔',
        },
    },
    {
        "index": 60,
        "section": "kn",
        "title": {
            "en": 'Khuddakanikāya Vimānavatthu',
            "th": 'ขุททกนิกาย วิมานวัตถุ',
        },
    },
    {
        "index": 61,
        "section": "kn",
        "title": {
            "en": 'Khuddakanikāya Petavatthu',
            "th": 'ขุททกนิกาย เปตวัตถุ',
        },
    },
    {
        "index": 62,
        "section": "kn",
        "title": {
            "en": 'Khuddakanikāya Theragāthā, Part 1',
            "th": 'ขุททกนิกาย เถรคาถา ภาค ๑',
        },
    },
    {
        "index": 63,
        "section": "kn",
        "title": {
            "en": 'Khuddakanikāya Theragāthā, Part 2',
            "th": 'ขุททกนิกาย เถรคาถา ภาค ๒',
        },
    },
    {
        "index": 64,
        "section": "kn",
        "title": {
            "en": 'Khuddakanikāya Therīgāthā',
            "th": 'ขุททกนิกาย เถรีคาถา',
        },
    },
    {
        "index": 65,
        "section": "kn",
        "title": {
            "en": 'Khuddakanikāya Jātaka (500 births), Part 1',
            "th": 'ขุททกนิกาย ชาดก (๕๐๐ ชาติ) ภาค ๑',
        },
    },
    {
        "index": 66,
        "section": "kn",
        "title": {
            "en": 'Khuddakanikāya Jātaka (500 births), Part 2',
            "th": 'ขุททกนิกาย ชาดก (๕๐๐ ชาติ) ภาค ๒',
        },
    },
    {
        "index": 67,
        "section": "kn",
        "title": {
            "en": 'Khuddakanikāya Jātaka (500 births), Part 3',
            "th": 'ขุททกนิกาย ชาดก (๕๐๐ ชาติ) ภาค ๓',
        },
    },
    {
        "index": 68,
        "section": "kn",
        "title": {
            "en": 'Khuddakanikāya Jātaka (500 births), Part 4',
            "th": 'ขุททกนิกาย ชาดก (๕๐๐ ชาติ) ภาค ๔',
        },
    },
    {
        "index": 69,
        "section": "kn",
        "title": {
            "en": 'Khuddakanikāya Jātaka (500 births), Part 5',
            "th": 'ขุททกนิกาย ชาดก (๕๐๐ ชาติ) ภาค ๕',
        },
    },
    {
        "index": 70,
        "section": "kn",
        "title": {
            "en": 'Khuddakanikāya Mahāniddesa, Part 1',
            "th": 'ขุททกนิกาย มหานิทเทส ภาค ๑',
        },
    },
    {
        "index": 71,
        "section": "kn",
        "title": {
            "en": 'Khuddakanikāya Mahāniddesa, Part 2',
            "th": 'ขุททกนิกาย มหานิทเทส ภาค ๒',
        },
    },
    {
        "index": 72,
        "section": "kn",
        "title": {
            "en": 'Khuddakanikāya Mahāniddesa, Part 3',
            "th": 'ขุททกนิกาย มหานิทเทส ภาค ๓',
        },
    },
    {
        "index": 73,
        "section": "kn",
        "title": {
            "en": 'Khuddakanikāya Mahāniddesa, Part 4',
            "th": 'ขุททกนิกาย มหานิทเทส ภาค ๔',
        },
    },
    {
        "index": 74,
        "section": "kn",
        "title": {
            "en": 'Khuddakanikāya Cūḷaniddesa, Part 1',
            "th": 'ขุททกนิกาย จูฬนิทเทส ภาค ๑',
        },
    },
    {
        "index": 75,
        "section": "kn",
        "title": {
            "en": 'Khuddakanikāya Cūḷaniddesa, Part 2',
            "th": 'ขุททกนิกาย จูฬนิทเทส ภาค ๒',
        },
    },
    {
        "index": 76,
        "section": "kn",
        "title": {
            "en": 'Khuddakanikāya Paṭisambhidāmagga, Part 1',
            "th": 'ขุททกนิกาย ปฏิสัมภิทามรรค ภาค ๑',
        },
    },
    {
        "index": 77,
        "section": "kn",
        "title": {
            "en": 'Khuddakanikāya Paṭisambhidāmagga, Part 2',
            "th": 'ขุททกนิกาย ปฏิสัมภิทามรรค ภาค ๒',
        },
    },
    {
        "index": 78,
        "section": "kn",
        "title": {
            "en": 'Khuddakanikāya Paṭisambhidāmagga, Part 3',
            "th": 'ขุททกนิกาย ปฏิสัมภิทามรรค ภาค ๓',
        },
    },
    {
        "index": 79,
        "section": "kn",
        "title": {
            "en": 'Khuddakanikāya Paṭisambhidāmagga, Part 4',
            "th": 'ขุททกนิกาย ปฏิสัมภิทามรรค ภาค ๔',
        },
    },
    {
        "index": 80,
        "section": "kn",
        "title": {
            "en": 'Khuddakanikāya Apadāna, Part 1',
            "th": 'ขุททกนิกาย อปทาน ภาค ๑',
        },
    },
    {
        "index": 81,
        "section": "kn",
        "title": {
            "en": 'Khuddakanikāya Apadāna, Part 2',
            "th": 'ขุททกนิกาย อปทาน ภาค ๒',
        },
    },
    {
        "index": 82,
        "section": "kn",
        "title": {
            "en": 'Khuddakanikāya Apadāna, Part 3',
            "th": 'ขุททกนิกาย อปทาน ภาค ๓',
        },
    },
    {
        "index": 83,
        "section": "kn",
        "title": {
            "en": 'Khuddakanikāya Apadāna, Part 4',
            "th": 'ขุททกนิกาย อปทาน ภาค ๔',
        },
    },
    {
        "index": 84,
        "section": "kn",
        "title": {
            "en": 'Khuddakanikāya Buddhavaṃsa',
            "th": 'ขุททกนิกาย พุทธวงศ์',
        },
    },
    {
        "index": 85,
        "section": "kn",
        "title": {
            "en": 'Khuddakanikāya Cariyāpiṭaka, Part 1',
            "th": 'ขุททกนิกาย จริยาปิฎก ภาค ๑',
        },
    },
    {
        "index": 86,
        "section": "kn",
        "title": {
            "en": 'Khuddakanikāya Cariyāpiṭaka, Part 2',
            "th": 'ขุททกนิกาย จริยาปิฎก ภาค ๒',
        },
    },
    {
        "index": 87,
        "section": "abh",
        "title": {
            "en": 'Dhammasaṅgaṇī, Part 1',
            "th": 'คัมภีร์พระสังคณี ภาค ๑',
        },
    },
    {
        "index": 88,
        "section": "abh",
        "title": {
            "en": 'Dhammasaṅgaṇī, Part 2',
            "th": 'คัมภีร์พระสังคณี ภาค ๒',
        },
    },
    {
        "index": 89,
        "section": "abh",
        "title": {
            "en": 'Vibhaṅga, Part 1',
            "th": 'คัมภีร์พระวิภังค์ ภาค ๑',
        },
    },
    {
        "index": 90,
        "section": "abh",
        "title": {
            "en": 'Vibhaṅga, Part 2',
            "th": 'คัมภีร์พระวิภังค์ ภาค ๒',
        },
    },
    {
        "index": 91,
        "section": "abh",
        "title": {
            "en": 'Dhātukathā–Puggalapaññatti, Part 1',
            "th": 'พระธาตุกถา-พระปุคคลบัญญัติ ภาค ๑',
        },
    },
    {
        "index": 92,
        "section": "abh",
        "title": {
            "en": 'Dhātukathā–Puggalapaññatti, Part 2',
            "th": 'พระธาตุกถา-พระปุคคลบัญญัติ ภาค ๒',
        },
    },
    {
        "index": 93,
        "section": "abh",
        "title": {
            "en": 'Kathāvatthu, Part 1',
            "th": 'คัมภีร์พระกถาวัตถุ ภาค ๑',
        },
    },
    {
        "index": 94,
        "section": "abh",
        "title": {
            "en": 'Kathāvatthu, Part 2',
            "th": 'คัมภีร์พระกถาวัตถุ ภาค ๒',
        },
    },
    {
        "index": 95,
        "section": "abh",
        "title": {
            "en": 'Yamaka, Part 1',
            "th": 'คัมภีร์พระยมก ภาค ๑',
        },
    },
    {
        "index": 96,
        "section": "abh",
        "title": {
            "en": 'Yamaka, Part 2',
            "th": 'คัมภีร์พระยมก ภาค ๒',
        },
    },
    {
        "index": 97,
        "section": "abh",
        "title": {
            "en": 'Mahāpaṭṭhāna, Part 1',
            "th": 'คัมภีร์พระมหาปัฏฐาน ภาค ๑',
        },
    },
    {
        "index": 98,
        "section": "abh",
        "title": {
            "en": 'Mahāpaṭṭhāna, Part 2',
            "th": 'คัมภีร์พระมหาปัฏฐาน ภาค ๒',
        },
    },
    {
        "index": 99,
        "section": "abh",
        "title": {
            "en": 'Mahāpaṭṭhāna, Part 3',
            "th": 'คัมภีร์พระมหาปัฏฐาน ภาค ๓',
        },
    },
    {
        "index": 100,
        "section": "abh",
        "title": {
            "en": 'Mahāpaṭṭhāna, Part 4',
            "th": 'คัมภีร์พระมหาปัฏฐาน ภาค ๔',
        },
    },
]

# (collection_code, edition_code) → volume list
# (Theravāda only; excludes Mahayana / Tibetan).
# Edition codes may repeat across collections; always key with collection.
CATALOG_VOLUME_SETS: dict[tuple[str, str], list[dict]] = {
    ("mc", "pali2506"): MCH_PALI_VOLUMES,
    ("sdb", "th2528"): SDB_THAI_VOLUMES,
    ("sy", "th2559"): MMR_THAI_VOLUMES,
    ("mc", "th2539"): MCH_THAI_VOLUMES,
    ("dr", "th2549"): CLPK_THAI_VOLUMES,
    ("sy", "th2525"): MMR_91_VOLUMES,
    ("sy", "th2552"): MMR_91_VOLUMES,
    ("lao", "pali2556"): LAO_PALI_VOLUMES,
    ("nld", "pali2560"): NLD_PALI_VOLUMES,
    ("bj", "pali2499"): SLK_PALI_VOLUMES,
    ("pts", "pali2424"): PTS_PALI_VOLUMES_WITH_INDEX,
    ("pts", "en2438"): PTS_ENGLISH_VOLUMES,
    ("tai", "pali2567"): TAI_PALI_VOLUMES,
    ("vnm", "vi2563"): VNM_VIETNAMESE_VOLUMES,
    ("ndz", "ja2544"): NDZ_JAPANESE_VOLUMES,
    ("ych", "zh2533"): YCS_CHINESE_VOLUMES,
    ("lan", "lanna2556"): RPO_LANNA_VOLUMES,
    ("kmr", "pali2472"): KHM_PALI_VOLUMES,
}


def volume_code(index: int) -> str:
    return f"vol-{index:02d}"


def thai_digits(n: int | str) -> str:
    return "".join(
        "๐๑๒๓๔๕๖๗๘๙"[int(ch)] if ch.isdigit() else ch for ch in str(n)
    )

