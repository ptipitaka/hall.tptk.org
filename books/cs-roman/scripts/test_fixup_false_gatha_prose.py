"""Tests for false gāthā prose peel + extract guards."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from extract_cs_roman_pdf import (  # noqa: E402
    Segment,
    _looks_like_gatha_line,
    _looks_like_gatha_seed_line,
    _looks_like_prose_not_gatha_wak,
    _one_bat_wak_romans,
    group_gatha_stanzas,
)
from fixup_false_gatha_prose import fix_segments  # noqa: E402


def _wak(roman: str, thai: str = "") -> dict:
    text = [{"script": "roman", "value": roman}]
    if thai:
        text.append({"script": "thai", "value": thai})
    return {"text": text}


def _bat(*romans: str) -> dict:
    return {"waks": [_wak(r) for r in romans]}


class ProseNotGathaWakTests(unittest.TestCase):
    def test_speech_intro_dash(self) -> None:
        self.assertTrue(
            _looks_like_prose_not_gatha_wak(
                "Tena kho pana samayena manussā bhikkhū disvā imāya gāthāya codenti–"
            )
        )
        self.assertFalse(_looks_like_gatha_seed_line(
            "Tena kho pana samayena manussā bhikkhū disvā imāya gāthāya codenti–"
        ))

    def test_iti_then_narrative(self) -> None:
        self.assertTrue(
            _looks_like_prose_not_gatha_wak(
                "no adhammenā”ti sattāhameva so saddo ahosi, sattāhassa accayena antaradhāyi."
            )
        )
        self.assertFalse(
            _looks_like_gatha_line(
                "no adhammenā”ti sattāhameva so saddo ahosi, sattāhassa accayena antaradhāyi."
            )
        )

    def test_verse_final_iti_ok(self) -> None:
        self.assertFalse(
            _looks_like_prose_not_gatha_wak('kā usūyā vijānatan”ti.')
        )
        self.assertTrue(_looks_like_gatha_line('kā usūyā vijānatan”ti.'))

    def test_narrative_then_quote(self) -> None:
        self.assertTrue(
            _looks_like_prose_not_gatha_wak(
                "Manussā “dhammena kira samaṇā Sakyaputtiyā nenti,"
            )
        )
        self.assertFalse(
            _looks_like_gatha_seed_line(
                "Manussā “dhammena kira samaṇā Sakyaputtiyā nenti,"
            )
        )


class HalfStanzaBatLineOnlyTests(unittest.TestCase):
    def test_wak_leftover_not_merged_as_half(self) -> None:
        """03Vin03 p.55: prose wak pair must not become 3rd บาท."""
        full = [
            Segment(
                page=55,
                order=1,
                item=None,
                segment_type="gatha",
                text="“Nayanti ve mahāvīrā, saddhammena Tathāgatā.",
            ),
            Segment(
                page=55,
                order=2,
                item=None,
                segment_type="gatha",
                text="Dhammena nayamānānaṃ, kā usūyā vijānatan”ti.",
            ),
            Segment(
                page=55,
                order=3,
                item=None,
                segment_type="gatha",
                text="Manussā “dhammena kira samaṇā Sakyaputtiyā nenti,",
            ),
            Segment(
                page=55,
                order=4,
                item=None,
                segment_type="gatha",
                text="no adhammenā”ti sattāhameva so saddo ahosi, sattāhassa accayena antaradhāyi.",
            ),
        ]
        grouped = group_gatha_stanzas(full)
        gathas = [s for s in grouped if s.segment_type == "gatha"]
        proses = [s for s in grouped if s.segment_type == "prose"]
        self.assertEqual(len(gathas), 1)
        self.assertEqual(len(gathas[0].bats or []), 2)
        self.assertGreaterEqual(len(proses), 1)
        self.assertTrue(
            any("Manussā" in (s.text or "") or "sattāhameva" in (s.text or "") for s in proses)
            or any("Manussā" in (s.text or "") for s in proses)
        )

    def test_true_bat_half_still_merges(self) -> None:
        lines = [
            Segment(
                page=8,
                order=1,
                item=None,
                segment_type="gatha",
                text="Manāpameva bhāseyya, nā’manāpaṃ kudācanaṃ.",
            ),
            Segment(
                page=8,
                order=2,
                item=None,
                segment_type="gatha",
                text="Manāpaṃ bhāsamānassa, garuṃ bhāraṃ udabbahi.",
            ),
            Segment(
                page=8,
                order=3,
                item=None,
                segment_type="gatha",
                text="Dhanañca naṃ alābhesi, tena ca’ttamano ahūti.",
            ),
        ]
        grouped = group_gatha_stanzas(lines)
        gathas = [s for s in grouped if s.segment_type == "gatha"]
        self.assertEqual(len(gathas), 1)
        self.assertEqual(len(gathas[0].bats or []), 3)

    def test_one_bat_wak_romans_rejects_wak_line(self) -> None:
        a = Segment(page=1, order=1, item=None, segment_type="gatha", text="a,")
        b = Segment(page=1, order=2, item=None, segment_type="gatha", text="b.")
        buf = [("a,", "wak_line", a), ("b.", "wak_line", b)]
        self.assertIsNone(_one_bat_wak_romans(buf))


class FixupFalseGathaProseTests(unittest.TestCase):
    def test_peel_whole_segment_prose_mistag(self) -> None:
        """10Ma02 p.21 Sekha: commentary + Buddha approval + closing were
        printed in bat/wak columns but are narrative prose, not verse.
        Every บาท has a long (>70 char) วรรค, so peel each บาท to its own
        prose segment and leave no gāthā behind."""
        segs = [
            {
                "order": 1,
                "page": 21,
                "segment_type": "gatha",
                "source_layout": "bat_line",
                "bats": [
                    _bat(
                        "Sā kho panesā Mahānāma brahmunā Sanaṅkumārena gāthā sugītā no duggītā,",
                        "subhāsitā no dubbhāsitā, atthasaṃhitā no anatthasaṃhitā, anumatā Bhagavatāti.",
                    ),
                    _bat(
                        "Atha kho Bhagavā uṭṭhahitvā āyasmantaṃ Ānandaṃ āmantesi “sādhu sādhu Ānanda,",
                        "sādhu kho tvaṃ Ānanda Kāpilavatthavānaṃ Sakyānaṃ sekhaṃ pāṭipadaṃ abhāsī”ti.",
                    ),
                    _bat(
                        "Idamavocāyasmā Ānando,",
                        "samanuñño sattā ahosi. Attamanā Kāpilavatthavā Sakyā āyasmato Ānandassa bhāsitaṃ abhinandunti.",
                    ),
                ],
            }
        ]
        out, n = fix_segments(segs)
        self.assertEqual(n, 1)
        self.assertEqual(len(out), 3)
        for s in out:
            self.assertEqual(s["segment_type"], "prose")
            self.assertNotIn("bats", s)
        roman0 = next(e["value"] for e in out[0]["text"] if e.get("script") == "roman")
        roman1 = next(e["value"] for e in out[1]["text"] if e.get("script") == "roman")
        roman2 = next(e["value"] for e in out[2]["text"] if e.get("script") == "roman")
        self.assertIn("Sā kho panesā", roman0)
        self.assertIn("Bhagavatāti", roman0)
        self.assertIn("Atha kho Bhagavā", roman1)
        self.assertIn("abhāsī”ti", roman1)
        self.assertIn("Idamavocāyasmā", roman2)
        self.assertIn("abhinandunti", roman2)

    def test_real_verse_with_quote_close_not_peeled(self) -> None:
        """15An01 p.322 / 18Khu01 p.253: short verse waks that trip the
        quote-close prose rule must NOT trigger a whole-segment peel."""
        segs = [
            {
                "order": 1,
                "page": 322,
                "segment_type": "gatha",
                "source_layout": "bat_line",
                "bats": [
                    _bat("Cetosamathasāmīciṃ,", 'sikkhamānaṃ sadā “sataṃ.'),
                    _bat('Satataṃ pahitatto”ti,', "āhu bhikkhuṃ tathāvidhanti.{{sp1}} Dutiyaṃ."),
                ],
            }
        ]
        out, n = fix_segments(segs)
        self.assertEqual(n, 0)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["segment_type"], "gatha")
        self.assertEqual(len(out[0]["bats"]), 2)

    def test_peel_third_bat_prose(self) -> None:
        segs = [
            {
                "order": 1,
                "page": 55,
                "segment_type": "gatha",
                "source_layout": "bat_line",
                "bats": [
                    _bat("“Nayanti ve mahāvīrā,", "saddhammena Tathāgatā."),
                    _bat("Dhammena nayamānānaṃ,", "kā usūyā vijānatan”ti."),
                    _bat(
                        "Manussā “dhammena kira samaṇā Sakyaputtiyā nenti,",
                        "no adhammenā”ti sattāhameva so saddo ahosi, sattāhassa accayena antaradhāyi.",
                    ),
                ],
            }
        ]
        out, n = fix_segments(segs)
        self.assertEqual(n, 1)
        self.assertEqual(out[0]["segment_type"], "gatha")
        self.assertEqual(len(out[0]["bats"]), 2)
        self.assertEqual(out[1]["segment_type"], "prose")
        roman = next(
            e["value"] for e in out[1]["text"] if e.get("script") == "roman"
        )
        self.assertIn("Manussā", roman)
        self.assertIn("sattāhameva", roman)

    def test_peel_speech_intro_wak_and_absorb_orphan(self) -> None:
        segs = [
            {
                "order": 1,
                "page": 55,
                "segment_type": "gatha",
                "source_layout": "wak_line",
                "bats": [
                    _bat(
                        "Tena kho pana samayena manussā bhikkhū disvā imāya gāthāya codenti–",
                        "“Āgato kho mahāsamaṇo,",
                    ),
                    _bat("Māgadhānaṃ Giribbajaṃ.", "Sabbe Sañcaye netvāna,"),
                ],
            },
            {
                "order": 2,
                "page": 55,
                "segment_type": "gatha",
                "source_layout": "bat_line",
                "needs_review": True,
                "review_reasons": ["irregular_gatha_stanza"],
                "bats": [_bat("kaṃsu dāni nayissatī”ti.")],
            },
        ]
        out, n = fix_segments(segs)
        self.assertEqual(n, 1)
        self.assertEqual(out[0]["segment_type"], "prose")
        self.assertIn("codenti", out[0]["text"][0]["value"])
        self.assertEqual(out[1]["segment_type"], "gatha")
        flat = [
            w["text"][0]["value"]
            for b in out[1]["bats"]
            for w in b["waks"]
        ]
        self.assertEqual(len(flat), 4)
        self.assertTrue(flat[0].startswith("“Āgato"))
        self.assertIn("kaṃsu", flat[3])
        self.assertNotIn("irregular_gatha_stanza", out[1].get("review_reasons") or [])

    def test_quote_ti_verse_lead_not_peeled(self) -> None:
        """19Khu02 p.320: wak_line บท starting ``“bhavissan”ti na hoti me.``."""
        segs = [
            {
                "order": 3787,
                "page": 320,
                "item": 715,
                "segment_type": "gatha",
                "source_layout": "wak_line",
                "bats": [
                    _bat("“bhavissan”ti na hoti me.", "Saṅkhārā vigamissanti,"),
                    _bat("tattha kā paridevanā."),
                ],
            }
        ]
        out, n = fix_segments(segs)
        self.assertEqual(n, 0)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["segment_type"], "gatha")
        self.assertEqual(out[0]["source_layout"], "wak_line")

    def test_peel_long_leading_prose_wak(self) -> None:
        """26Khu09 p.163: commentary วรรค glued as first wak_line unit."""
        commentary = (
            "passāsādimajjhapariyosānaṃ satiyā anugacchato "
            "bahiddhāvikkhepagataṃ cittaṃ samādhissa paripantho, "
            "assāsapaṭikaṅkhanā nikantitaṇhācittaṃ samādhissa paripantho."
        )
        self.assertGreater(len(commentary), 70)
        segs = [
            {
                "order": 840,
                "page": 163,
                "item": 154,
                "segment_type": "gatha",
                "source_layout": "wak_line",
                "bats": [
                    _bat(commentary, "Anugacchanā ca assāsaṃ,"),
                    _bat("passāsaṃ, anugacchanā."),
                ],
            }
        ]
        out, n = fix_segments(segs)
        self.assertEqual(n, 1)
        self.assertEqual(out[0]["segment_type"], "prose")
        self.assertIn("passāsādimajjhapariyosānaṃ", out[0]["text"][0]["value"])
        self.assertEqual(out[1]["segment_type"], "gatha")
        flat = [
            w["text"][0]["value"]
            for b in out[1]["bats"]
            for w in b["waks"]
        ]
        self.assertEqual(flat[0], "Anugacchanā ca assāsaṃ,")
        self.assertEqual(flat[1], "passāsaṃ, anugacchanā.")


if __name__ == "__main__":
    unittest.main()
