#!/usr/bin/env python3
"""Regression tests for fixup_glued_cakka_closers.

Locks the 01Vin01 p212 order 1423 item 327 case: ``Khaṇḍacakkaṃ.`` was
extracted glued onto the prose body instead of being its own centered
``prose`` segment (as it is on 10+ other folios of 01Vin01).
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from fixup_glued_cakka_closers import (  # noqa: E402
    _CAKKA_CLOSER_ROMAN,
    _CAKKA_CLOSER_THAI,
    _peel_cakka,
    unglue_cakka_closers,
)


class FixupGluedCakkaClosersTests(unittest.TestCase):
    def test_peel_cakka_after_stop(self) -> None:
        body, closer = _peel_cakka(
            "āpatti saṃghādisesassa. Khaṇḍacakkaṃ.", _CAKKA_CLOSER_ROMAN
        )
        self.assertEqual(body, "āpatti saṃghādisesassa.")
        self.assertEqual(closer, _CAKKA_CLOSER_ROMAN)

    def test_peel_rejects_standalone_closer(self) -> None:
        # Already-split closer segment must be left alone (no real body).
        self.assertIsNone(_peel_cakka(_CAKKA_CLOSER_ROMAN, _CAKKA_CLOSER_ROMAN))
        self.assertIsNone(
            _peel_cakka("Khaṇḍacakkaṃ niṭṭhitaṃ.", _CAKKA_CLOSER_ROMAN)
        )

    def test_peel_rejects_no_sentence_stop(self) -> None:
        # Closer glued without a preceding sentence stop is not peeled here.
        self.assertIsNone(_peel_cakka("sa Khaṇḍacakkaṃ.", _CAKKA_CLOSER_ROMAN))

    def test_peel_thai_marker(self) -> None:
        body, closer = _peel_cakka(
            "อาปตฺติ สํฆาทิเสสสฺส. " + _CAKKA_CLOSER_THAI, _CAKKA_CLOSER_THAI
        )
        self.assertEqual(body, "อาปตฺติ สํฆาทิเสสสฺส.")
        self.assertEqual(closer, _CAKKA_CLOSER_THAI)

    def test_unglue_splits_glued_cakka_and_keeps_item(self) -> None:
        roman = (
            "Saparidaṇḍāya yena daṇḍo ṭhapito hoti, so bhikkhuṃ pahiṇati "
            "“gaccha bhante itthannāmaṃ brūhi hotu itthannāmassa bhariyā "
            "dhanakkītā cā”ti, paṭiggaṇhāti vīmaṃsati paccāharati, "
            "āpatti saṃghādisesassa. Khaṇḍacakkaṃ."
        )
        seg = {
            "page": 212,
            "order": 1423,
            "segment_type": "prose",
            "item": 327,
            "text": [
                {"script": "roman", "value": roman},
                {"script": "thai", "value": "สปริทณฺฑาย … ขณฺฑจกฺกํ."},
            ],
        }
        out, splits = unglue_cakka_closers([seg])
        self.assertEqual(splits, 1)
        self.assertEqual(len(out), 2)
        # Body keeps the sentence stop, drops the glued closer.
        self.assertTrue(out[0]["text"][0]["value"].endswith("āpatti saṃghādisesassa."))
        self.assertFalse(out[0]["text"][0]["value"].endswith("Khaṇḍacakkaṃ."))
        # New closer segment: centered prose, keeps item, renumbered orders.
        self.assertEqual(out[1]["segment_type"], "prose")
        self.assertEqual(out[1]["source_layout"], "center")
        self.assertEqual(out[1]["item"], 327)
        self.assertEqual(out[1]["text"][0]["value"], _CAKKA_CLOSER_ROMAN)
        self.assertEqual(out[1]["order"], 2)
        self.assertEqual(out[0]["order"], 1)

    def test_unglue_idempotent_on_standalone_closer(self) -> None:
        seg = {
            "page": 211,
            "order": 1412,
            "segment_type": "prose",
            "item": 323,
            "source_layout": "center",
            "text": [{"script": "roman", "value": _CAKKA_CLOSER_ROMAN}],
        }
        out, splits = unglue_cakka_closers([seg])
        self.assertEqual(splits, 0)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["text"][0]["value"], _CAKKA_CLOSER_ROMAN)


if __name__ == "__main__":
    unittest.main()
