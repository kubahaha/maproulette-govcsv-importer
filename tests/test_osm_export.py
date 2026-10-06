import unittest
from types import SimpleNamespace
from unittest.mock import patch

from src.fill.fill_csv import fill_with_matches
from src.match.match_and_fill import fill
from src.osm_model.osm_types import OsmNode


class OSMExportTests(unittest.TestCase):
    def setUp(self):
        self.config = SimpleNamespace(
            tags_to_delete={},
            tags_to_add={},
            tags_to_replace={},
            rules={},
            tags_source={"source:office": "Gov feed"},
        )

    def test_changed_match_gets_modify_action_and_next_version(self):
        osm = OsmNode(lat=52, lon=21, id=42, version=2, tags={"name": "Old name"})
        gov = SimpleNamespace(tags={"name": "New name"})

        with patch("src.match.match_and_fill.importlib.import_module", return_value=self.config):
            updated = fill("fixture", osm, gov)

        xml = updated.print()
        self.assertIn('version="3"', xml)
        self.assertIn('action="modify"', xml)
        self.assertEqual(updated.tags["source:office"], "Gov feed")

    def test_unchanged_match_is_not_marked_or_versioned(self):
        osm = OsmNode(lat=52, lon=21, id=42, version=4, tags={"name": "Same name"})
        gov = SimpleNamespace(tags={"name": "Same name"})

        with patch("src.match.match_and_fill.importlib.import_module", return_value=self.config):
            unchanged = fill("fixture", osm, gov)

        xml = unchanged.print()
        self.assertIn('version="4"', xml)
        self.assertNotIn('action="modify"', xml)
        self.assertEqual(unchanged.tags, osm.tags)

    def test_fill_with_matches_omits_unchanged_objects(self):
        changed = SimpleNamespace(id=42, modify=True)
        unchanged = SimpleNamespace(id=43, modify=False)
        gov_rows = [SimpleNamespace(id=-1), SimpleNamespace(id=-2)]
        osm_rows = [SimpleNamespace(id=42), SimpleNamespace(id=43)]

        with (
            patch("src.fill.fill_csv.read_matches", return_value={-1: 42, -2: 43}),
            patch("src.fill.fill_csv.read_file", side_effect=[gov_rows, osm_rows]),
            patch("src.fill.fill_csv.fill", side_effect=[changed, unchanged]),
        ):
            output = fill_with_matches("fixture", SimpleNamespace(), [])

        self.assertEqual(output, [changed])


if __name__ == "__main__":
    unittest.main()