"""Focused data conversion tests; do not require a dataset or network."""

import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from scripts.prepare_cardd_hf import convert_bbox, prepare


class TestDamagePreparation(unittest.TestCase):
    def test_normalized_top_left_bbox_to_yolo_center(self):
        self.assertEqual(convert_bbox([0.1, 0.2, 0.4, 0.6]), (0.30000000000000004, 0.5, 0.4, 0.6))

    def test_invalid_boxes_are_rejected(self):
        for box in (
            [0, 0, 0, 1],
            [-0.1, 0, 0.2, 0.2],
            [0.9, 0, 0.2, 0.2],
            [0, 0, float("nan"), 1],
            [0, 0, 1, float("inf")],
            [0, 1],
        ):
            with self.subTest(box=box), self.assertRaises(ValueError):
                convert_bbox(box)

    def test_source_class_ids_and_file_dimensions_are_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, output = root / "source", root / "output"
            source.mkdir()
            (source / "hf-metadata.json").write_text(json.dumps({"sha": "test-revision"}))
            categories = [{"id": 6, "name": "tire flat"}, {"id": 5, "name": "lamp broken"}]
            (source / "metadata.json").write_text(json.dumps({"info": {"categories": categories}}))
            sample = {
                "filepath": "data/000001.jpg",
                "metadata": {"width": 100, "height": 50},
                "detections": {"detections": [{"label": "tire flat", "bounding_box": [0.1, 0.2, 0.4, 0.6]}]},
            }
            (source / "samples.json").write_text(json.dumps({"samples": [sample]}))
            target = output / "images/mirror_train/000001.jpg"
            target.parent.mkdir(parents=True)
            Image.new("RGB", (100, 50), "white").save(target)
            report = prepare(source, output, 1, False)
            self.assertEqual(report["classes"], ["lamp broken", "tire flat"])
            self.assertEqual(report["ready_images"], 1)
            self.assertEqual(report["annotations"], 1)
            self.assertEqual(report["errors"], [])
            self.assertEqual(
                (output / "labels/mirror_train/000001.txt").read_text().strip(),
                "1 0.300000000 0.500000000 0.400000000 0.600000000",
            )
            self.assertFalse((output / "data.yaml").exists())
            sample["metadata"]["width"] = 101
            (source / "samples.json").write_text(json.dumps({"samples": [sample]}))
            report = prepare(source, output, 1, False)
            self.assertEqual(report["ready_images"], 0)
            self.assertEqual(len(report["errors"]), 1)


if __name__ == "__main__":
    unittest.main()
