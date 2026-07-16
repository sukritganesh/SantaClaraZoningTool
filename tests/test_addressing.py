"""Unit tests for controlled Santa Clara address matching."""

from __future__ import annotations

import unittest

from santa_clara_zoning.addressing import AddressIndex, normalize_address


def address_feature(object_id: int, display_address: str) -> dict:
    return {
        "type": "Feature",
        "properties": {
            "OBJECTID": object_id,
            "CSCADDR": display_address,
            "CSCSTATUS": "A",
        },
        "geometry": {"type": "Point", "coordinates": [-121.9, 37.3]},
    }


class AddressNormalizationTest(unittest.TestCase):
    def test_suffix_locality_unit_and_punctuation_normalize(self) -> None:
        cases = {
            "636 Barto Street, Santa Clara, CA 95051": "636 BARTO ST",
            "108 brookside av": "108 BROOKSIDE AVE",
            "324 Los Padres Blvd.": "324 LOS PADRES BLVD",
            "1577 Pomeroy Avenue, Unit #202": "1577 POMEROY AVE 202",
        }
        for entered, expected in cases.items():
            with self.subTest(entered=entered):
                self.assertEqual(normalize_address(entered), expected)

    def test_empty_input_normalizes_to_empty_key(self) -> None:
        self.assertEqual(normalize_address("  "), "")


class AddressIndexTest(unittest.TestCase):
    def test_exact_normalized_match(self) -> None:
        feature = address_feature(1, "636 Barto Street")
        index = AddressIndex([feature])
        self.assertEqual(index.match("636 Barto St, Santa Clara CA"), (feature,))

    def test_duplicate_source_records_are_preserved(self) -> None:
        first = address_feature(2, "324 Los Padres Boulevard")
        second = address_feature(1, "324 Los Padres Boulevard")
        index = AddressIndex([first, second])
        self.assertEqual(index.match("324 Los Padres Blvd"), (second, first))


if __name__ == "__main__":
    unittest.main()
