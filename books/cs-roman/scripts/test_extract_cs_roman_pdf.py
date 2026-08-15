"""Unit tests for cs-roman page-break merge and word repair."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from extract_cs_roman_pdf import (  # noqa: E402
    SECTION_RULE_FLAG,
    Segment,
    _blocks_from_region,
    _is_running_header,
    _is_section_rule_line,
    _normalize_inline,
    _repair_mid_word_split,
    _segment_to_json,
    _split_false_pa_join,
    attach_notes_sacred_style,
    detect_running_headers,
    extract_page_blocks,
    is_running_header_folio_label,
    merge_blocks,
    peel_glued_gatha_title_raw,
    peel_glued_gatha_title_text,
    peel_glued_running_header_prefix,
    peel_glued_uddesa_heading,
    peel_leading_running_headers,
    peel_page_top_running_header_furniture,
    unglue_false_pa_page_joins,
)


class RepairMidWordSplitTests(unittest.TestCase):
    def test_no_hyphen_keeps_separate_words(self) -> None:
        prev, nxt, joined = _repair_mid_word_split(
            "… sāmantā hasamānā ṭhitā",
            "hoti. So bhikkhu …",
        )
        self.assertEqual(prev, "… sāmantā hasamānā ṭhitā")
        self.assertEqual(nxt, "hoti. So bhikkhu …")
        self.assertFalse(joined)

    def test_hyphen_joins_leading_word(self) -> None:
        prev, nxt, joined = _repair_mid_word_split(
            "agārasmā anagāriyaṃ pabbaj-",
            "jāya. Evaṃ …",
        )
        self.assertEqual(prev, "agārasmā anagāriyaṃ pabbajjāya")
        self.assertEqual(nxt, ". Evaṃ …")
        self.assertTrue(joined)

    def test_soft_hyphen_joins_leading_word(self) -> None:
        prev, nxt, joined = _repair_mid_word_split(
            "pabbaj\u00ad",
            "jāya.",
        )
        self.assertEqual(prev, "pabbajjāya")
        self.assertEqual(nxt, ".")
        self.assertTrue(joined)

    def test_peyyala_marker_not_joined(self) -> None:
        prev, nxt, joined = _repair_mid_word_split(
            "taṃ jīvitā voropesi -pa-",
            "aññaṃ maññamāno …",
        )
        self.assertEqual(prev, "taṃ jīvitā voropesi -pa-")
        self.assertEqual(nxt, "aññaṃ maññamāno …")
        self.assertFalse(joined)

    def test_peyyala_marker_case_insensitive_token(self) -> None:
        prev, nxt, joined = _repair_mid_word_split(
            "ahosi -PA-",
            "Āpattiṃ tvaṃ",
        )
        self.assertEqual(prev, "ahosi -PA-")
        self.assertEqual(nxt, "Āpattiṃ tvaṃ")
        self.assertFalse(joined)


class FalsePaJoinRepairTests(unittest.TestCase):
    def test_split_false_pa_join(self) -> None:
        self.assertEqual(
            _split_false_pa_join("voropesi -paaññaṃ"),
            ("voropesi -pa-", "aññaṃ"),
        )
        self.assertIsNone(_split_false_pa_join("voropesi -pa-"))
        self.assertIsNone(
            _split_false_pa_join("bhesajja-parikkhārā")
        )

    def test_unglue_moves_word_to_continuation(self) -> None:
        segments = [
            {
                "page": 109,
                "segment_type": "prose",
                "item": 188,
                "text": [
                    {
                        "script": "roman",
                        "value": "voropesi -paaññaṃ",
                    },
                    {"script": "thai", "value": "โวโรเปสิ -ปอญฺญํ"},
                ],
            },
            {
                "page": 110,
                "segment_type": "prose_continuation",
                "item": 188,
                "text": [
                    {
                        "script": "roman",
                        "value": "maññamāno taṃ",
                    },
                    {"script": "thai", "value": "มญฺญมาโน ตํ"},
                ],
            },
        ]
        self.assertEqual(unglue_false_pa_page_joins(segments), 1)
        self.assertEqual(segments[0]["text"][0]["value"], "voropesi -pa-")
        self.assertEqual(
            segments[1]["text"][0]["value"], "aññaṃ maññamāno taṃ"
        )


class MergeBlocksContinuationTests(unittest.TestCase):
    def test_cross_page_itemless_stays_prose_until_geometry(self) -> None:
        """merge_blocks must not assume continuation (new para under same item)."""
        blocks = [
            {
                "kind": "prose",
                "item": 46,
                "text": (
                    "Atha vā pana … yadi panāhaṃ Buddhaṃ paccakkheyyanti"
                ),
                "flags": [],
                "page": 29,
                "pdf_page": 52,
            },
            {
                "kind": "prose",
                "item": None,
                "text": "vadati viññāpeti -pa- yadi panāhaṃ asakyaputtiyo",
                "flags": [],
                "page": 30,
                "pdf_page": 53,
            },
        ]
        segs = merge_blocks(blocks)
        self.assertEqual(len(segs), 2)
        self.assertEqual(segs[0].segment_type, "prose")
        self.assertEqual(segs[0].item, 46)
        # Geometry (flush x0) upgrades this later; merge alone keeps prose.
        self.assertEqual(segs[1].segment_type, "prose")

    def test_cross_page_peyyala_not_glued(self) -> None:
        blocks = [
            {
                "kind": "prose",
                "item": 188,
                "text": "taṃ jīvitā voropesi -pa-",
                "flags": [],
                "page": 109,
                "pdf_page": 132,
            },
            {
                "kind": "prose",
                "item": None,
                "text": "aññaṃ maññamāno taṃ jīvitā voropesi",
                "flags": [],
                "page": 110,
                "pdf_page": 133,
            },
        ]
        segs = merge_blocks(blocks)
        self.assertEqual(len(segs), 2)
        self.assertEqual(segs[0].text, "taṃ jīvitā voropesi -pa-")
        self.assertEqual(
            segs[1].text, "aññaṃ maññamāno taṃ jīvitā voropesi"
        )
        # Must not upgrade to continuation solely from a false hyphen join.
        self.assertEqual(segs[1].segment_type, "prose")
        self.assertEqual(segs[1].item, 188)

    def test_cross_page_still_repairs_hyphen(self) -> None:
        blocks = [
            {
                "kind": "prose",
                "item": 10,
                "text": "agārasmā anagāriyaṃ pabbaj-",
                "flags": [],
                "page": 1,
                "pdf_page": 24,
            },
            {
                "kind": "prose",
                "item": None,
                "text": "jāya. Evaṃ vadati.",
                "flags": [],
                "page": 2,
                "pdf_page": 25,
            },
        ]
        segs = merge_blocks(blocks)
        self.assertEqual(segs[0].text, "agārasmā anagāriyaṃ pabbajjāya")
        self.assertEqual(segs[1].text, ". Evaṃ vadati.")
        # Joined hyphen across the page break ⇒ continuation, not a new para.
        self.assertEqual(segs[1].segment_type, "prose_continuation")
        self.assertEqual(segs[1].item, 10)

    def test_same_page_itemless_is_new_prose(self) -> None:
        blocks = [
            {
                "kind": "prose",
                "item": 10,
                "text": "Evaṃ hoti.",
                "flags": [],
                "page": 1,
                "pdf_page": 24,
            },
            {
                "kind": "prose",
                "item": None,
                "text": "So bhikkhu evaṃ vadati.",
                "flags": [],
                "page": 1,
                "pdf_page": 24,
            },
        ]
        segs = merge_blocks(blocks)
        self.assertEqual(segs[1].segment_type, "prose")
        self.assertEqual(segs[1].item, 10)


class SectionNoHeadingTests(unittest.TestCase):
    def test_numbered_heading_keeps_section_no_not_item(self) -> None:
        blocks = _blocks_from_region(
            "1. Pārājikakaṇḍa",
            printed_page=13,
            pdf_page=36,
            headers=set(),
            as_notes=False,
        )
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0]["kind"], "chapter")
        self.assertEqual(blocks[0]["text"], "Pārājikakaṇḍa")
        self.assertIsNone(blocks[0]["item"])
        self.assertEqual(blocks[0]["section_no"], 1)

        segs = merge_blocks(blocks)
        self.assertEqual(segs[0].section_no, 1)
        self.assertIsNone(segs[0].item)
        payload = _segment_to_json(segs[0])
        self.assertEqual(payload["section_no"], 1)
        self.assertIsNone(payload.get("item"))

    def test_numbered_title_heading(self) -> None:
        blocks = _blocks_from_region(
            "1. Paṭhamapārājika Sudinnabhāṇavāra",
            printed_page=13,
            pdf_page=36,
            headers=set(),
            as_notes=False,
        )
        self.assertEqual(blocks[0]["kind"], "title")
        self.assertEqual(blocks[0]["section_no"], 1)
        self.assertEqual(
            blocks[0]["text"], "Paṭhamapārājika Sudinnabhāṇavāra"
        )

    def test_long_numbered_prose_keeps_item(self) -> None:
        body = (
            "1. Tena kho pana samayena Vesāliyā avidūre Kalandagāmo nāma "
            "atthi, tattha Sudinno nāma Kalandaputto seṭṭhiputto hoti. "
            "Atha kho Sudinno Kalandaputto sambahulehi sahāyakehi saddhiṃ "
            "Vesāliṃ agamāsi kenacideva karaṇīyena."
        )
        blocks = _blocks_from_region(
            body,
            printed_page=13,
            pdf_page=36,
            headers=set(),
            as_notes=False,
        )
        self.assertEqual(blocks[0]["kind"], "prose")
        self.assertEqual(blocks[0]["item"], 1)
        self.assertNotIn("section_no", blocks[0])

    def test_glued_civaravagga_uddesa_peels_to_section_no(self) -> None:
        blocks = _blocks_from_region(
            "1. Cīvaravagga 1. Paṭhamakathinasikkhāpada Ime kho panāyasmanto "
            "tiṃsa nissaggiyā pācittiyā dhammā uddesaṃ āgacchanti.",
            printed_page=294,
            pdf_page=317,
            headers=set(),
            as_notes=False,
        )
        self.assertEqual(len(blocks), 2)
        self.assertEqual(blocks[0]["kind"], "chapter")
        self.assertEqual(blocks[0]["section_no"], 1)
        self.assertIsNone(blocks[0]["item"])
        self.assertEqual(
            blocks[0]["text"], "Cīvaravagga 1. Paṭhamakathinasikkhāpada"
        )
        self.assertEqual(blocks[1]["kind"], "prose")
        self.assertIsNone(blocks[1]["item"])
        self.assertTrue(blocks[1]["text"].startswith("Ime kho"))

    def test_glued_sikkhapada_uddesa_peels_to_title(self) -> None:
        blocks = _blocks_from_region(
            "1. Sukkavissaṭṭhisikkhāpada Ime kho panāyasmanto terasa "
            "saṃghādisesā dhammā uddesaṃ āgacchanti.",
            printed_page=151,
            pdf_page=174,
            headers=set(),
            as_notes=False,
        )
        self.assertEqual(len(blocks), 2)
        self.assertEqual(blocks[0]["kind"], "title")
        self.assertEqual(blocks[0]["section_no"], 1)
        self.assertEqual(blocks[0]["text"], "Sukkavissaṭṭhisikkhāpada")
        self.assertTrue(blocks[1]["text"].startswith("Ime kho"))

    def test_peel_helper_strips_sentence_spacers(self) -> None:
        peeled = peel_glued_uddesa_heading(
            "Cīvaravagga 1.{{sp1}} Paṭhamakathinasikkhāpada Ime kho "
            "panāyasmanto tiṃsa nissaggiyā pācittiyā dhammā uddesaṃ āgacchanti."
        )
        self.assertIsNotNone(peeled)
        assert peeled is not None
        title, body = peeled
        self.assertEqual(title, "Cīvaravagga 1. Paṭhamakathinasikkhāpada")
        self.assertTrue(body.startswith("Ime kho"))

    def test_peel_rejects_ordinary_ime_kho_lists(self) -> None:
        self.assertIsNone(
            peel_glued_uddesa_heading(
                "Puggalavagga lokasmiṃ. Katame tayo? Kāyasakkhī diṭṭhippatto "
                "saddhāvimutto. Ime kho āvuso tayo puggalā santo saṃvijjamānā "
                "lokasmiṃ."
            )
        )
        self.assertIsNone(
            peel_glued_uddesa_heading(
                "Dasakanipātapāḷi Ime kho bhikkhave tayo dhamme pahāya bhabbo."
            )
        )


class GluedGathaTitlePeelTests(unittest.TestCase):
    def test_raw_tassuddana_peels_title_and_bat_lines(self) -> None:
        peeled = peel_glued_gatha_title_raw(
            "Tassuddānaṃ\n"
            "Ubbhataṃ kathinaṃ tīṇi, dhovanañca paṭiggaho.\n"
            "Aññātakāni tīṇeva, ubhinnaṃ dūtakena cāti.\n"
            "_____"
        )
        self.assertIsNotNone(peeled)
        assert peeled is not None
        title, lines = peeled
        self.assertEqual(title, "Tassuddānaṃ")
        self.assertEqual(len(lines), 3)
        self.assertTrue(lines[0].startswith("Ubbhataṃ"))
        self.assertTrue(lines[1].startswith("Aññātakāni"))
        self.assertTrue(_is_section_rule_line(lines[2]))

    def test_blocks_from_region_emits_title_then_verse_prose(self) -> None:
        blocks = _blocks_from_region(
            "Tassuddānaṃ\n"
            "Ubbhataṃ kathinaṃ tīṇi, dhovanañca paṭiggaho.\n"
            "Aññātakāni tīṇeva, ubhinnaṃ dūtakena cāti.\n"
            "_____",
            printed_page=328,
            pdf_page=351,
            headers=set(),
            as_notes=False,
        )
        self.assertEqual(len(blocks), 3)
        self.assertEqual(blocks[0]["kind"], "tassuddānaṃ")
        self.assertEqual(blocks[0]["text"], "Tassuddānaṃ")
        self.assertEqual(blocks[1]["kind"], "prose")
        self.assertTrue(blocks[1]["text"].startswith("Ubbhataṃ"))
        self.assertTrue(blocks[2]["text"].startswith("Aññātakāni"))
        # Section rule attaches to last verse body.
        self.assertIn("_____", blocks[2]["text"] or "")

    def test_normalized_text_peel_and_reject_commentary(self) -> None:
        peeled = peel_glued_gatha_title_text(
            "Tassuddānaṃ Ubbhataṃ kathinaṃ tīṇi, dhovanañca paṭiggaho."
            "{{sp1}} Aññātakāni tīṇeva, ubhinnaṃ dūtakena cāti."
        )
        self.assertIsNotNone(peeled)
        assert peeled is not None
        title, parts = peeled
        self.assertEqual(title, "Tassuddānaṃ")
        self.assertEqual(len(parts), 2)
        # Long niddesa titles that merely contain ``gāthā`` must not peel.
        self.assertIsNone(
            peel_glued_gatha_title_text(
                "Pārāyanatthutigāthāniddesa imassa pārāyanassāti tasmā "
                "imassa dhammapariyāyassa.{{sp1}} Pārāyananteva adhivacanaṃ."
            )
        )


class SectionRuleAttachTests(unittest.TestCase):
    def test_same_block_trailing_underscores_set_flag(self) -> None:
        """Closer + short rule without a blank line → section_rule flag."""
        blocks = _blocks_from_region(
            "Sudinnabhāṇavāro niṭṭhito.\n_____",
            printed_page=25,
            pdf_page=48,
            headers=set(),
            as_notes=False,
        )
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0]["kind"], "niṭṭhitaṃ")
        self.assertTrue(blocks[0]["text"].rstrip().endswith("_____"))
        segs = merge_blocks(blocks)
        payload = _segment_to_json(segs[0])
        self.assertIn(SECTION_RULE_FLAG, payload.get("flags") or [])
        self.assertEqual(
            payload["text"][0]["value"], "Sudinnabhāṇavāro niṭṭhito."
        )

    def test_separate_underscore_line_attaches_to_previous(self) -> None:
        """Blank line before _____ must still attach (not a new segment)."""
        blocks = _blocks_from_region(
            "Makkaṭīvatthu niṭṭhitaṃ.\n\n_____\n\nSanthatabhāṇavāra",
            printed_page=27,
            pdf_page=50,
            headers=set(),
            as_notes=False,
        )
        self.assertEqual(len(blocks), 2)
        self.assertEqual(blocks[0]["kind"], "niṭṭhitaṃ")
        self.assertTrue(blocks[0]["text"].rstrip().endswith("_____"))
        self.assertNotEqual(blocks[1]["kind"], "niṭṭhitaṃ")
        segs = merge_blocks(blocks)
        self.assertEqual(len(segs), 2)
        payload = _segment_to_json(segs[0])
        self.assertIn(SECTION_RULE_FLAG, payload.get("flags") or [])

    def test_long_footnote_rule_not_section_rule(self) -> None:
        self.assertTrue(_is_section_rule_line("_" * 8))  # decorative title rule
        self.assertFalse(_is_section_rule_line("_" * 62))
        self.assertTrue(_is_section_rule_line("_____"))
        blocks = _blocks_from_region(
            "Verañjabhāṇavāro niṭṭhito.\n\n"
            + ("_" * 62)
            + "\n\n1. Vassaṃvutthā (Sī)",
            printed_page=12,
            pdf_page=35,
            headers=set(),
            as_notes=False,
        )
        # Footnote separator is dropped; closer must not gain section_rule.
        closer = next(b for b in blocks if "niṭṭhito" in b["text"])
        self.assertFalse(closer["text"].rstrip().endswith("_____"))
        segs = merge_blocks([closer])
        payload = _segment_to_json(segs[0])
        self.assertNotIn(SECTION_RULE_FLAG, payload.get("flags") or [])

    def test_opening_decorative_rule_not_footnote_split(self) -> None:
        """Medium underscore rule under gambhīra must stay body (02Vin02)."""
        page = (
            "Vinayapiṭaka\n\nPācittiyapāḷi\n\n________\n\n"
            "Namo tassa Bhagavato Arahato Sammāsambuddhassa.\n\n"
            "5. Pācittiyakaṇḍa\n\n"
            "1. Musāvādavagga    1. Musāvādasikkhāpada\n\n"
            "Ime kho panāyasmanto dvenavuti pācittiyā dhammā uddesaṃ "
            "āgacchanti.\n"
        )
        blocks = extract_page_blocks(
            page,
            printed_page=1,
            pdf_page=15,
            headers={"Vinayapiṭaka", "Pācittiyapāḷi"},
            is_opening_page=True,
        )
        kinds = [b["kind"] for b in blocks]
        self.assertNotIn("note", kinds)
        self.assertNotIn("note_continuation", kinds)
        joined = " ".join(b["text"] for b in blocks)
        self.assertIn("Namo tassa", joined)
        self.assertIn("Pācittiyakaṇḍa", joined)
        self.assertIn("Ime kho panāyasmanto", joined)

    def test_merge_attaches_orphan_rule_block(self) -> None:
        blocks = [
            {
                "kind": "niṭṭhitaṃ",
                "item": None,
                "text": "Sudinnabhāṇavāro niṭṭhito.",
                "flags": [],
                "page": 25,
                "pdf_page": 48,
            },
            {
                "kind": "prose",
                "item": None,
                "text": "_____",
                "flags": [],
                "page": 25,
                "pdf_page": 48,
            },
        ]
        segs = merge_blocks(blocks)
        self.assertEqual(len(segs), 1)
        self.assertTrue(segs[0].text.rstrip().endswith("_____"))
        payload = _segment_to_json(segs[0])
        self.assertIn(SECTION_RULE_FLAG, payload.get("flags") or [])


class AttachSymbolNotesTests(unittest.TestCase):
    def test_repeated_plus_keeps_mark_without_second_note(self) -> None:
        """Second + callout keeps {{+}} even when only one + footnote exists."""
        segs = [
            Segment(
                page=116,
                order=1,
                item=None,
                segment_type="prose",
                text="Kāsāvakaṇṭhā bahavo, pāpadhammā asaññatā.",
                flags=["plus"],
            ),
            Segment(
                page=116,
                order=2,
                item=None,
                segment_type="prose",
                text="Seyyo ayoguḷo bhutto, tatto aggisikhūpamo.",
                flags=["plus"],
            ),
            Segment(
                page=116,
                order=3,
                item=None,
                segment_type="note",
                text="Khu 1. 57 piṭṭhe dhammapadepi.",
                flags=["plus"],
            ),
        ]
        out = attach_notes_sacred_style(segs)
        body = [s for s in out if s.segment_type == "prose"]
        self.assertEqual(len(body), 2)
        shared = "Khu 1. 57 piṭṭhe dhammapadepi."
        self.assertTrue(body[0].text.startswith("{{+}}"))
        self.assertEqual(body[0].symbol_notes.get("+"), shared)
        # Second + callout shares the same note body (one + foot-note on the page).
        self.assertTrue(body[1].text.startswith("{{+}}"))
        self.assertEqual(body[1].symbol_notes.get("+"), shared)


class AttachNumberedCalloutTests(unittest.TestCase):
    def test_glued_callout_binds_note(self) -> None:
        segs = [
            Segment(
                page=74,
                order=1,
                item=149,
                segment_type="prose",
                text="eso bhaginiyo ovādo”ti niyyādetabbo1. Sace",
            ),
            Segment(
                page=74,
                order=2,
                item=1,
                segment_type="note",
                text="Niyyātetabbo (Itipi)",
            ),
        ]
        out = attach_notes_sacred_style(segs)
        body = next(s for s in out if s.segment_type == "prose")
        self.assertIn("niyyādetabbo{{n0}}", body.text)
        self.assertEqual(body.notes, ["Niyyātetabbo (Itipi)"])
        self.assertFalse(any(s.segment_type == "note" for s in out))

    def test_glued_midword_callout_binds_note(self) -> None:
        """``Kaṇṭakassa1nāma`` (02Vin02 p.181) — digit glued before a letter."""
        segs = [
            Segment(
                page=181,
                order=1,
                item=428,
                segment_type="prose",
                text=(
                    "Tena kho pana samayena Kaṇṭakassa1nāma "
                    "samaṇuddesassa evarūpaṃ"
                ),
            ),
            Segment(
                page=181,
                order=2,
                item=1,
                segment_type="note",
                text="Kaṇḍakassa (Syā, Ka)",
            ),
        ]
        out = attach_notes_sacred_style(segs)
        body = next(s for s in out if s.segment_type == "prose")
        self.assertIn("Kaṇṭakassa{{n0}}nāma", body.text)
        self.assertEqual(body.notes, ["Kaṇḍakassa (Syā, Ka)"])
        self.assertFalse(any(s.segment_type == "note" for s in out))

    def test_paren_note_binds_to_body_paren(self) -> None:
        """``(  ) (katthaci natthi)`` binds next to body ``(`` (02Vin02 p.317)."""
        segs = [
            Segment(
                page=317,
                order=1,
                item=None,
                segment_type="prose",
                text="tattha (sā bhikkhunī) abbhetabbā.",
            ),
            Segment(
                page=317,
                order=2,
                item=None,
                segment_type="note",
                text="(  ) (katthaci natthi)",
            ),
        ]
        out = attach_notes_sacred_style(segs)
        body = next(s for s in out if s.segment_type == "prose")
        self.assertTrue(body.text.startswith("tattha ({{()}}"))
        self.assertEqual(body.symbol_notes.get("()"), "(katthaci natthi)")
        self.assertFalse(any(s.segment_type == "note" for s in out))

    def test_numbered_paren_body_not_stolen_by_folio(self) -> None:
        """Numbered note ``2. ( ) (?) …`` must bind to ``(te)2``, not ``(150)``.

        Regression: 01Vin01 p.86 bound note 2 onto folio ``(150)`` as
        ``({{()}}150)`` and left literal ``(te)2`` in the next segment.
        """
        segs = [
            Segment(
                page=86,
                order=1,
                item=161,
                segment_type="prose_continuation",
                text="So bhikkhu abhiramatīti1. (150)",
            ),
            Segment(
                page=86,
                order=2,
                item=162,
                segment_type="prose",
                text=(
                    'bhāsatī”ti (te)2 anekākāravokāraṃ '
                    "asubhabhāvanānuyogamanuyuttā viharanti."
                ),
                flags=["star"],
            ),
            Segment(
                page=86,
                order=3,
                item=1,
                segment_type="note",
                text="Abhiramīti (Sī, Syā)",
            ),
            Segment(
                page=86,
                order=4,
                item=2,
                segment_type="note",
                text="( ) (?) Evamuparipi īdisesu ṭhānesu.",
            ),
            Segment(
                page=86,
                order=5,
                item=None,
                segment_type="note",
                text="Idaṃ vatthu Saṃ 3. 278 piṭṭhepi āgataṃ.",
                flags=["star"],
            ),
        ]
        out = attach_notes_sacred_style(segs)
        bodies = [s for s in out if s.segment_type != "note"]
        cont = next(s for s in bodies if s.segment_type == "prose_continuation")
        prose = next(s for s in bodies if s.segment_type == "prose")
        self.assertIn("abhiramatīti{{n0}}", cont.text)
        self.assertIn("(150)", cont.text)
        self.assertNotIn("{{()}}", cont.text)
        self.assertNotIn("()", (cont.symbol_notes or {}))
        self.assertIn("(te){{n0}}", prose.text)
        self.assertNotIn("(te)2", prose.text)
        self.assertEqual(
            prose.notes,
            ["( ) (?) Evamuparipi īdisesu ṭhānesu."],
        )
        self.assertEqual(
            prose.symbol_notes.get("*"),
            "Idaṃ vatthu Saṃ 3. 278 piṭṭhepi āgataṃ.",
        )
        self.assertFalse(any(s.segment_type == "note" for s in out))

    def test_spaced_callout_binds_note(self) -> None:
        """PDF superscript gap: ``paccāsīsitabbā 1 uposatha`` (02Vin02 p.75)."""
        segs = [
            Segment(
                page=75,
                order=1,
                item=149,
                segment_type="prose_continuation",
                text=(
                    "dve dhammā paccāsīsitabbā 1 uposathapucchakañca "
                    "ovādupasaṅkamanañca,"
                ),
            ),
            Segment(
                page=75,
                order=2,
                item=1,
                segment_type="note",
                text="Paccāsiṃ sitabbā (Itipi)",
            ),
        ]
        out = attach_notes_sacred_style(segs)
        body = next(s for s in out if s.segment_type == "prose_continuation")
        self.assertIn("paccāsīsitabbā{{n0}}", body.text)
        self.assertNotIn("paccāsīsitabbā 1 ", body.text)
        self.assertEqual(body.notes, ["Paccāsiṃ sitabbā (Itipi)"])
        self.assertFalse(any(s.segment_type == "note" for s in out))

    def test_spaced_outline_number_not_bound(self) -> None:
        """``vagga 1. Title`` must not consume footnote 1."""
        segs = [
            Segment(
                page=10,
                order=1,
                item=None,
                segment_type="chapter",
                text="Cīvaravagga 1. Paṭhamakathinasikkhāpada",
            ),
            Segment(
                page=10,
                order=2,
                item=None,
                segment_type="prose",
                text="Ime kho panāyasmanto dvenavuti1 pācittiyā.",
            ),
            Segment(
                page=10,
                order=3,
                item=1,
                segment_type="note",
                text="Variant (Itipi)",
            ),
        ]
        out = attach_notes_sacred_style(segs)
        chapter = next(s for s in out if s.segment_type == "chapter")
        prose = next(s for s in out if s.segment_type == "prose")
        self.assertEqual(chapter.text, "Cīvaravagga 1. Paṭhamakathinasikkhāpada")
        self.assertIn("dvenavuti{{n0}}", prose.text)
        self.assertEqual(prose.notes, ["Variant (Itipi)"])

    def test_inline_plus_callout_binds_note(self) -> None:
        """Mid-paragraph ``Te + evarūpaṃ`` (01Vin01 p.274) binds + note."""
        segs = [
            Segment(
                page=274,
                order=1,
                item=431,
                segment_type="prose",
                text="nāma1 Kīṭāgirismiṃ. Te + evarūpaṃ anācāraṃ ācaranti.",
                flags=["star"],
            ),
            Segment(
                page=274,
                order=2,
                item=1,
                segment_type="note",
                text="Nāma bhikkhū (Ka)",
            ),
            Segment(
                page=274,
                order=3,
                item=None,
                segment_type="note",
                text="Idaṃ vatthu Vi 4. 22 piṭṭhādīsupi āgataṃ.",
                flags=["star"],
            ),
            Segment(
                page=274,
                order=4,
                item=None,
                segment_type="note",
                text="Vi 4. 284 piṭṭhādīsupi.",
                flags=["plus"],
            ),
        ]
        out = attach_notes_sacred_style(segs)
        body = next(s for s in out if s.segment_type == "prose")
        self.assertIn("{{*}}", body.text)
        self.assertIn("Te{{+}}evarūpaṃ", body.text.replace(" ", ""))
        self.assertEqual(body.symbol_notes.get("+"), "Vi 4. 284 piṭṭhādīsupi.")
        self.assertFalse(any(s.segment_type == "note" for s in out))

    def test_bracket_note_binds_to_omission_bracket(self) -> None:
        """``[  ] Etthantare…`` binds next to body ``[`` (01Vin01 p.134)."""
        segs = [
            Segment(
                page=134,
                order=1,
                item=None,
                segment_type="prose",
                text="[ 219. Tīhā kārehi dutiyañca jhānaṃ",
            ),
            Segment(
                page=134,
                order=2,
                item=None,
                segment_type="note",
                text="[  ] Etthantare pāṭhā Syāmapotthake natthi.",
            ),
        ]
        out = attach_notes_sacred_style(segs)
        body = next(s for s in out if s.segment_type == "prose")
        self.assertTrue(body.text.startswith("[{{[]}}"))
        self.assertEqual(
            body.symbol_notes.get("[]"),
            "Etthantare pāṭhā Syāmapotthake natthi.",
        )
        self.assertFalse(any(s.segment_type == "note" for s in out))


class _FakePage:
    def __init__(self, text: str) -> None:
        self._text = text

    def get_text(self, *_args: object, **_kwargs: object) -> str:
        return self._text


class _FakeDoc:
    def __init__(self, pages: list[str]) -> None:
        self._pages = [_FakePage(t) for t in pages]

    @property
    def page_count(self) -> int:
        return len(self._pages)

    def __getitem__(self, index: int) -> _FakePage:
        return self._pages[index]


class RunningHeaderTests(unittest.TestCase):
    def test_detect_scans_beyond_first_twelve_pages(self) -> None:
        pages = [f"1. EarlySutta\n{i + 1}\nbody text here.\n" for i in range(15)]
        pages.extend(
            f"10. Subhasutta\n{i + 1}\nkhayañāṇāya cittaṃ abhinīharati.\n"
            for i in range(15, 30)
        )
        headers = detect_running_headers(_FakeDoc(pages), 0)
        self.assertIn("1. EarlySutta", headers)
        self.assertIn("10. Subhasutta", headers)

    def test_detect_ignores_mid_page_body_repeats(self) -> None:
        filler = "\n".join(f"body line {n} with enough words here." for n in range(8))
        pages = [
            f"BookLabel\n{i + 1}\n{filler}\nvadeyya.\nvadeyya.\nvadeyya.\n"
            for i in range(10)
        ]
        headers = detect_running_headers(_FakeDoc(pages), 0)
        self.assertIn("BookLabel", headers)
        self.assertNotIn("vadeyya.", headers)

    def test_detect_excludes_tassuddana_label(self) -> None:
        pages = [
            f"Tassuddānaṃ\n{i + 1}\nTathāgataṃ Padaṃ Kūṭaṃ, Mūlaṃ Sārena Vassikaṃ.\n"
            for i in range(10)
        ]
        headers = detect_running_headers(_FakeDoc(pages), 0)
        self.assertNotIn("Tassuddānaṃ", headers)
        self.assertFalse(_is_running_header("Tassuddānaṃ", {"Tassuddānaṃ"}))

    def test_peel_multiline_glued_header_and_folio(self) -> None:
        raw = (
            "10. Subhasutta \n"
            "203 \n"
            "khayañāṇāya cittaṃ abhinīharati abhininnāmeti."
        )
        headers = {"10. Subhasutta", "Sīlakkhandhavaggapāḷi"}
        out = peel_leading_running_headers(raw, headers)
        self.assertTrue(
            _normalize_inline(out).startswith("khayañāṇāya cittaṃ"),
            out,
        )

    def test_peel_keeps_isolated_chapter_title(self) -> None:
        raw = "10. Subhasutta "
        out = peel_leading_running_headers(raw, {"10. Subhasutta"})
        self.assertEqual(_normalize_inline(out), "10. Subhasutta")

    def test_is_running_header_keeps_numbered_title(self) -> None:
        self.assertFalse(
            _is_running_header("10. Subhasutta", {"10. Subhasutta"})
        )

    def test_is_running_header_drops_unnumbered_book_label(self) -> None:
        self.assertTrue(
            _is_running_header(
                "Sīlakkhandhavaggapāḷi", {"Sīlakkhandhavaggapāḷi"}
            )
        )

    def test_extract_page_blocks_peels_glued_header(self) -> None:
        page = (
            "10. Subhasutta \n"
            "203 \n"
            "khayañāṇāya cittaṃ abhinīharati.\n"
            "\n"
            "Seyyathāpi māṇava pabbatasaṅkhepe udakarahado.\n"
        )
        blocks = extract_page_blocks(
            page,
            printed_page=203,
            pdf_page=221,
            headers={"10. Subhasutta"},
        )
        self.assertGreaterEqual(len(blocks), 1)
        self.assertTrue(
            blocks[0]["text"].startswith("khayañāṇāya"),
            blocks[0]["text"],
        )
        self.assertIsNone(blocks[0].get("item"))

    def test_extract_keeps_chapter_open_title_block(self) -> None:
        page = (
            "10. Subhasutta \n"
            "\n"
            "Subhamāṇavavatthu \n"
            "\n"
            "444. Evaṃ me sutaṃ–ekaṃ samayaṃ.\n"
        )
        blocks = extract_page_blocks(
            page,
            printed_page=188,
            pdf_page=206,
            headers={"10. Subhasutta"},
        )
        kinds_texts = [(b["kind"], b["text"], b.get("section_no")) for b in blocks]
        self.assertTrue(
            any(
                k in {"title", "chapter", "subhead"} and t == "Subhasutta"
                for k, t, _sn in kinds_texts
            ),
            kinds_texts,
        )

    def test_peel_glued_prefix_from_stored_prose(self) -> None:
        headers = {"10. Subhasutta", "2. Sāmaññaphalasutta"}
        peeled = peel_glued_running_header_prefix(
            "Subhasutta khayañāṇāya cittaṃ abhinīharati abhininnāmeti, "
            "so idaṃ dukkhanti yathābhūtaṃ pajānāti.",
            headers,
        )
        assert peeled is not None
        rest, label, item = peeled
        self.assertEqual(label, "Subhasutta")
        self.assertEqual(item, 10)
        self.assertTrue(rest.startswith("khayañāṇāya"))

    def test_detect_folio_header_from_single_page(self) -> None:
        """Short suttas may appear at page top only once — still detect."""
        pages = [
            "Aṭṭhakanāgarasutta (52)\n13\n"
            "Bhagavatā jānatā passatā Arahatā Sammāsambuddhena "
            "ekadhammo akkhāto, yattha bhikkhuno.\n"
        ]
        headers = detect_running_headers(_FakeDoc(pages), 0)
        self.assertIn("Aṭṭhakanāgarasutta (52)", headers)

    def test_peel_folio_prefix_without_frequency_set(self) -> None:
        peeled = peel_glued_running_header_prefix(
            "Aṭṭhakanāgarasutta (52) Bhagavatā jānatā passatā Arahatā "
            "Sammāsambuddhena ekadhammo akkhāto, yattha bhikkhuno "
            "appamattassa ātāpino pahitattassa viharato.",
            set(),
        )
        assert peeled is not None
        rest, label, item = peeled
        self.assertEqual(label, "Aṭṭhakanāgarasutta (52)")
        self.assertIsNone(item)
        self.assertTrue(rest.startswith("Bhagavatā"), rest)

    def test_peel_numbered_folio_prefix_pattern(self) -> None:
        peeled = peel_glued_running_header_prefix(
            "4. Potaliyasutta (54) liṅgā te nimittā yathā taṃ "
            "gahapatissāti. Tathā hi pana me bho gotama sabbe "
            "kammantā paṭikkhittā, sabbe vohārā samucchinnāti.",
            set(),
        )
        assert peeled is not None
        rest, label, item = peeled
        self.assertEqual(label, "4. Potaliyasutta (54)")
        self.assertEqual(item, 4)
        self.assertTrue(rest.startswith("liṅgā"), rest)

    def test_is_running_header_drops_folio_label(self) -> None:
        self.assertTrue(is_running_header_folio_label("Potaliyasutta (54)"))
        self.assertTrue(
            _is_running_header("Potaliyasutta (54)", {"4. Potaliyasutta (54)"})
        )
        self.assertTrue(_is_running_header("4. Potaliyasutta (54)", set()))

    def test_is_running_header_keeps_chapter_open_without_folio(self) -> None:
        self.assertFalse(is_running_header_folio_label("10. Subhasutta"))
        self.assertFalse(
            _is_running_header("10. Subhasutta", {"10. Subhasutta"})
        )

    def test_peel_page_top_continuation_header_with_edition_folio(self) -> None:
        """Centered saṃyutta running header + outer edition page → furniture."""
        page = (
            "12. Vacchagottasaṃyutta \n"
            "\n"
            "\n"
            "223 \n"
            "Sāvatthinidānaṃ. Saṅkhāresu kho Vaccha appaccakkhakammā -pa-.\n"
        )
        headers = {"12. Vacchagottasaṃyutta"}
        out = peel_page_top_running_header_furniture(page, headers)
        self.assertTrue(
            _normalize_inline(out).startswith("Sāvatthinidānaṃ"),
            out,
        )
        blocks = extract_page_blocks(
            page, printed_page=223, pdf_page=241, headers=headers
        )
        texts = [_normalize_inline(b["text"]) for b in blocks]
        self.assertTrue(texts, blocks)
        self.assertTrue(texts[0].startswith("Sāvatthinidānaṃ"), texts)
        self.assertFalse(
            any("Vacchagottasaṃyutta" in t for t in texts),
            texts,
        )

    def test_peel_page_top_keeps_chapter_open_before_child_title(self) -> None:
        page = (
            "12. Vacchagottasaṃyutta \n"
            "\n"
            "1. Rūpa-aññāṇasutta \n"
            "\n"
            "607. Ekaṃ samayaṃ Bhagavā Sāvatthiyaṃ viharati.\n"
        )
        headers = {"12. Vacchagottasaṃyutta"}
        out = peel_page_top_running_header_furniture(page, headers)
        self.assertIn("Vacchagottasaṃyutta", out)
        blocks = extract_page_blocks(
            page, printed_page=218, pdf_page=236, headers=headers
        )
        kinds_texts = [
            (b["kind"], _normalize_inline(b["text"])) for b in blocks
        ]
        self.assertTrue(
            any(
                "Vacchagottasaṃyutta" in t or t == "Vacchagottasaṃyutta"
                for _k, t in kinds_texts
            ),
            kinds_texts,
        )

    def test_peel_page_top_keeps_header_when_folio_then_child_title(self) -> None:
        """Header + edition folio + child title → still a chapter open."""
        page = (
            "12. Vacchagottasaṃyutta \n"
            "\n"
            "218 \n"
            "\n"
            "1. Rūpa-aññāṇasutta \n"
            "\n"
            "607. Ekaṃ samayaṃ Bhagavā Sāvatthiyaṃ viharati.\n"
        )
        headers = {"12. Vacchagottasaṃyutta"}
        out = peel_page_top_running_header_furniture(page, headers)
        self.assertIn("Vacchagottasaṃyutta", out)

    def test_extract_drops_isolated_folio_header_block(self) -> None:
        page = (
            "Potaliyasutta (54) \n"
            "\n"
            "Ime kho gahapati aṭṭha dhammā saṃkhittena vuttā.\n"
        )
        blocks = extract_page_blocks(
            page,
            printed_page=27,
            pdf_page=33,
            headers={"4. Potaliyasutta (54)"},
        )
        texts = [b["text"] for b in blocks]
        self.assertFalse(
            any(is_running_header_folio_label(t) for t in texts),
            texts,
        )
        self.assertTrue(
            any(t.startswith("Ime kho") for t in texts),
            texts,
        )


if __name__ == "__main__":
    unittest.main()
