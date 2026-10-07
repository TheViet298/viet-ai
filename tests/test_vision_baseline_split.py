"""Group split must keep similar/duplicate samples together, including cross-label pairs."""

import tempfile
import unittest
from pathlib import Path

from scripts.prepare_vision_baseline import export, group_rows, split_groups


def row(rid, label, sha=None):
    return {"id": rid, "labels": [label], "sha256": sha or rid}


class TestBaselineSplit(unittest.TestCase):
    def test_transitive_cross_label_and_exact_duplicate_groups(self):
        rows = [row("a", "VF5"), row("b", "Herio"), row("c", "VF5"), row("d", "VF8", "same"), row("e", "VF8", "same")]
        groups = group_rows(rows, [("a", "b"), ("b", "c")])
        self.assertEqual(sorted(sorted(r["id"] for r in g) for g in groups.values()), [["a", "b", "c"], ["d", "e"]])

    def test_deterministic_complete_split_with_no_group_leakage(self):
        rows = [row(f"a{i}", "VF5") for i in range(10)] + [row(f"b{i}", "VF8") for i in range(10)]
        pairs = [("a0", "a1"), ("a1", "b0")]
        groups = group_rows(rows, pairs)
        split = split_groups(groups, 0.2, 142)
        self.assertEqual(split, split_groups(group_rows(list(reversed(rows)), pairs), 0.2, 142))
        self.assertEqual(set(split["train"]) | set(split["val"]), {r["id"] for r in rows})
        self.assertFalse(set(split["train"]) & set(split["val"]))
        self.assertTrue(split["val"])
        for group in groups.values():
            self.assertEqual(len({"val" if r["id"] in split["val"] else "train" for r in group}), 1)

    def test_single_independent_group_is_train_only(self):
        groups = group_rows([row("only", "Nerio"), *[row(f"a{i}", "VF5") for i in range(8)]], [])
        split = split_groups(groups)
        self.assertIn("only", split["train"])
        self.assertNotIn("only", split["val"])

    def test_classifier_quarantines_labels_missing_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sample = root / "sample.jpg"
            sample.write_bytes(b"copy-fixture")
            rows = [row("only", "Nerio"), *[row(f"a{i}", "VF5") for i in range(8)]]
            for value in rows:
                value["image_path"] = str(sample)
            report = export(rows, [], root / "result", True)
            self.assertEqual(report["needs_data"], 1)
            self.assertEqual(report["deferred_classes"], ["Nerio"])
            train_labels = {p.name for p in (root / "result/train").iterdir()}
            val_labels = {p.name for p in (root / "result/val").iterdir()}
            self.assertEqual(train_labels, val_labels)
            self.assertEqual(train_labels, {"VF5"})


if __name__ == "__main__":
    unittest.main()
