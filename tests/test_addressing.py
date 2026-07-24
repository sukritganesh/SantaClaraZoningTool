"""Unit tests for controlled Santa Clara address matching."""

from __future__ import annotations

import unittest

from santa_clara_zoning.addressing import AddressIndex, normalize_address


def address_feature(
    object_id: int,
    display_address: str,
    *,
    city: str = "SANTA CLARA",
    zip_code: int = 95050,
) -> dict:
    return {
        "type": "Feature",
        "properties": {
            "OBJECTID": object_id,
            "CSCADDR": display_address,
            "CSCSTATUS": "A",
            "ADDRCITY": city,
            "ADDRZIP5": zip_code,
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


class AddressSuggestionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.index = AddressIndex(
            [
                address_feature(1, "1240 WHITE DR", zip_code=95051),
                address_feature(2, "1241 WHITE DR", zip_code=95051),
                address_feature(3, "636 BARTO ST", zip_code=95050),
                address_feature(4, "10 BARTO ST", zip_code=95050),
                address_feature(5, "2 BARTO ST", zip_code=95050),
            ]
        )

    def test_exact_prefix_token_abbreviation_and_locality_matching(self) -> None:
        exact = self.index.suggest(
            "1240 White Drive, Santa Clara, CA 95051"
        )
        prefix = self.index.suggest("1240 whi")
        street_only = self.index.suggest("barto")

        self.assertEqual(exact["suggestions"][0]["value"], "1240 WHITE DR")
        self.assertEqual(exact["normalized_query"], "1240 WHITE DR")
        self.assertEqual(prefix["total_matches"], 1)
        self.assertEqual(prefix["suggestions"][0]["secondary_text"], "Santa Clara, CA 95051")
        self.assertEqual(
            [item["value"] for item in street_only["suggestions"]],
            ["2 BARTO ST", "10 BARTO ST", "636 BARTO ST"],
        )

    def test_short_empty_and_unmatched_queries_are_controlled(self) -> None:
        for query in ("", "12", " - "):
            with self.subTest(query=query):
                result = self.index.suggest(query)
                self.assertEqual(result["status"], "query_too_short")
                self.assertEqual(result["suggestions"], [])
                self.assertEqual(result["total_matches"], 0)
                self.assertFalse(result["truncated"])

        missing = self.index.suggest("99999 no such street")
        self.assertEqual(missing["status"], "ok")
        self.assertEqual(missing["suggestions"], [])
        self.assertEqual(missing["total_matches"], 0)

    def test_duplicate_source_values_are_collapsed_without_hiding_count(self) -> None:
        index = AddressIndex(
            [
                address_feature(2, "324 LOS PADRES BLVD"),
                address_feature(1, "324 LOS PADRES BLVD"),
            ]
        )

        result = index.suggest("324 los padres")

        self.assertEqual(result["total_matches"], 1)
        self.assertEqual(len(result["suggestions"]), 1)
        self.assertEqual(result["suggestions"][0]["source_record_count"], 2)
        self.assertEqual(len(index.match(result["suggestions"][0]["value"])), 2)

    def test_unit_heavy_results_are_bounded_and_require_more_typing(self) -> None:
        index = AddressIndex(
            [
                address_feature(
                    object_id,
                    f"2917 NOYCE PL {unit}",
                    zip_code=95051,
                )
                for object_id, unit in enumerate(range(100, 110), start=1)
            ]
        )

        broad = index.suggest("2917 Noyce Place")
        narrowed = index.suggest("2917 Noyce Place 109")

        self.assertEqual(broad["total_matches"], 10)
        self.assertEqual(len(broad["suggestions"]), 8)
        self.assertTrue(broad["truncated"])
        self.assertEqual(narrowed["total_matches"], 1)
        self.assertEqual(narrowed["suggestions"][0]["value"], "2917 NOYCE PL 109")
        self.assertFalse(narrowed["truncated"])

    def test_results_are_defensive_and_repeatable(self) -> None:
        first = self.index.suggest("1240 whi")
        first["suggestions"][0]["value"] = "MUTATED"

        second = self.index.suggest("1240 whi")

        self.assertEqual(second["suggestions"][0]["value"], "1240 WHITE DR")
        self.assertEqual(second, self.index.suggest("1240 whi"))

    def test_invalid_query_and_limit_fail_closed(self) -> None:
        with self.assertRaisesRegex(TypeError, "must be a string"):
            self.index.suggest(123)  # type: ignore[arg-type]
        with self.assertRaisesRegex(ValueError, "120-character"):
            self.index.suggest("a" * 121)
        for limit in (0, 9, True):
            with self.subTest(limit=limit):
                with self.assertRaisesRegex(ValueError, "between 1 and 8"):
                    self.index.suggest("1240 white", limit=limit)


if __name__ == "__main__":
    unittest.main()
