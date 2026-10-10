import argparse
import json
import sys
import tempfile
import types
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from scripts.export_vision_cloud import export_bundle
from scripts.train_vision_baseline import preflight, run
from src.services.vision.contract import damage_result, vehicle_result


class TestVisionCloud(unittest.TestCase):
    def test_notebooks_migrate_old_numpy_pin_and_require_restart_for_loaded_kernel(self):
        repo = Path(__file__).resolve().parents[1]
        from packaging.requirements import Requirement

        for task in ("vehicles", "damage"):
            notebook = json.loads((repo / f"notebooks/train_{task}_baseline.ipynb").read_text(encoding="utf-8"))
            install = "".join(notebook["cells"][3]["source"])
            with tempfile.TemporaryDirectory() as tmp:
                data = Path(tmp)
                (data / "requirements-vision-train.txt").write_text("numpy>=1.26,<2\npydantic>=2.10,<3\n")
                calls = []
                namespace = {
                    "DATA": data,
                    "sys": types.SimpleNamespace(executable="python", modules={"numpy": object()}),
                    "subprocess": types.SimpleNamespace(run=lambda *a, **k: calls.append((a, k))),
                }
                with self.assertRaisesRegex(RuntimeError, "Restart"):
                    exec(compile(install, task, "exec"), namespace)
                pins = [Requirement(line) for line in (data / "requirements-vision-notebook.txt").read_text().splitlines()]
                active = [r for r in pins if r.name == "numpy" and r.marker.evaluate({"python_version": "3.13"})]
                self.assertEqual(len(active), 1)
                self.assertIn("2.1.0", active[0].specifier)
                self.assertNotIn("1.26.4", active[0].specifier)
                self.assertEqual(len(calls), 2, "install and check in a fresh process")

    def test_portable_bundle_preserves_split_and_label_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base = root / "baseline"
            stage = root / "stage"
            for split in ("train", "val"):
                folder = base / "vehicles" / split / "vf3"
                folder.mkdir(parents=True)
                (folder / (split + ".jpg")).write_bytes(b"image")
                damage = base / "damage"
                damage.mkdir(exist_ok=True)
                image = stage / "images" / "mirror_train" / (split + ".jpg")
                image.parent.mkdir(parents=True, exist_ok=True)
                image.write_bytes(b"image")
                label = stage / "labels" / "mirror_train" / (split + ".txt")
                label.parent.mkdir(parents=True, exist_ok=True)
                label.write_text("0 0.5 0.5 0.2 0.2\n")
                (damage / (split + ".jsonl")).write_text(
                    json.dumps(
                        {
                            "id": split,
                            "image_path": str(image),
                            "label_file": str(label.relative_to(stage)),
                            "sha256": "abc",
                            "similarity_group": split,
                        }
                    )
                    + "\n"
                )
            (stage / "class-map.json").write_text(json.dumps({"yolo_classes": {"dent": 0}}))
            source = root / "source"
            source.mkdir()
            (source / "CarDD_license.pdf").write_bytes(b"license")
            (base / "baseline-report.json").write_text("{}")
            out = root / "bundle.zip"
            export_bundle(base, stage, source, out)
            with zipfile.ZipFile(out) as z:
                self.assertIn("vision-baseline/damage/images/val/val.jpg", z.namelist())
                self.assertIn("vision-baseline/damage/labels/val/val.txt", z.namelist())
                self.assertIn("vision-baseline/sources/CarDD_license.pdf", z.namelist())
                self.assertNotIn(str(root), z.read("vision-baseline/damage/val.jsonl").decode())
            with self.assertRaises(FileExistsError):
                export_bundle(base, stage, source, out)

    def test_preflight_rejects_classifier_label_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for split, label in [("train", "vf3"), ("val", "vf5")]:
                folder = root / "vehicles" / split / label
                folder.mkdir(parents=True)
                (folder / "one.jpg").write_bytes(b"image")
            with self.assertRaises(ValueError):
                preflight(root, "vehicles")

    def test_contract_abstains_and_keeps_failure_distinct(self):
        result = vehicle_result([("vf3", 0.4), ("vf5", 0.3)], "checkpoint-sha", threshold=0.7)
        self.assertEqual(result.status, "unknown")
        self.assertIsNone(result.model_label)
        self.assertEqual(vehicle_result([("vf3", 0.9)], "sha").status, "candidate")
        from src.services.vision.contract import DamageResult

        self.assertEqual(DamageResult(status="unavailable", reason="weights_missing").status, "unavailable")
        self.assertEqual(damage_result([], "sha").status, "not_detected")

    def test_contract_rejects_invalid_boxes_and_nonfinite_scores(self):
        with self.assertRaises(ValueError):
            damage_result([{"label": "dent", "confidence": 0.8, "bbox_xyxy": [0.8, 0.2, 0.1, 0.7]}], "sha")
        with self.assertRaises(ValueError):
            vehicle_result([("vf3", float("nan"))], "sha")

    def test_damage_preflight_rejects_invalid_yolo_labels(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for split in ("train", "val"):
                images = root / "damage/images" / split
                labels = root / "damage/labels" / split
                images.mkdir(parents=True)
                labels.mkdir(parents=True)
                (images / "one.jpg").write_bytes(split.encode())
                (labels / "one.txt").write_text("6 0.5 0.5 0.2 0.2\n")
            with self.assertRaises(ValueError):
                preflight(root, "damage")

    def test_preflight_detects_exact_image_leakage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for split in ("train", "val"):
                folder = root / "vehicles" / split / "vf3"
                folder.mkdir(parents=True)
                (folder / "one.jpg").write_bytes(b"same-photo")
            with self.assertRaisesRegex(ValueError, "leakage"):
                preflight(root, "vehicles")

    def test_damage_preflight_accepts_decimal_rounding_at_border(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for split in ("train", "val"):
                images = root / "damage/images" / split
                labels = root / "damage/labels" / split
                images.mkdir(parents=True)
                labels.mkdir(parents=True)
                (images / "one.jpg").write_bytes(split.encode())
                (labels / "one.txt").write_text("1 0.354250000 0.157841079 0.152960000 0.315682159\n")
            self.assertEqual(preflight(root, "damage")["counts"], {"train": 1, "val": 1})

    def test_training_handoff_records_checkpoint_metrics_and_runtime_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = root / "data"
            names = ["dent", "scratch", "crack", "glass shatter", "lamp broken", "tire flat"]
            for split in ("train", "val"):
                images = data / "damage/images" / split
                labels = data / "damage/labels" / split
                images.mkdir(parents=True)
                labels.mkdir(parents=True)
                (images / "one.jpg").write_bytes(split.encode())
                (labels / "one.txt").write_text("0 0.5 0.5 0.2 0.2\n")
            # JSON is also valid YAML; the portable config must stay untouched.
            config = {"train": "images/train", "val": "images/val", "names": dict(enumerate(names))}
            import yaml

            (data / "damage/data.yaml").write_text(yaml.safe_dump(config))
            calls = []

            class FakeEngine:
                task = "detect"

                def __init__(self, checkpoint):
                    self.names = dict(enumerate(names))

                def train(self, **kw):
                    calls.append(kw)
                    folder = Path(kw["project"]) / kw["name"]
                    (folder / "weights").mkdir(parents=True)
                    (folder / "weights/best.pt").write_bytes(b"test-checkpoint")
                    self.trainer = types.SimpleNamespace(save_dir=folder)

                def val(self, **kw):
                    calls.append(kw)
                    return types.SimpleNamespace(
                        results_dict={"metrics/mAP50-95(B)": 0.2},
                        box=types.SimpleNamespace(ap_class_index=[0], ap=[0.2]),
                    )

            cuda = types.SimpleNamespace(is_available=lambda: True, get_device_name=lambda n: "test-GPU")
            args = argparse.Namespace(
                data_root=data,
                task="damage",
                check_only=False,
                device="0",
                output=root / "runs",
                model=None,
                epochs=1,
                imgsz=None,
                batch=2,
            )
            with (
                patch.dict(
                    sys.modules,
                    {"torch": types.SimpleNamespace(cuda=cuda), "ultralytics": types.SimpleNamespace(YOLO=FakeEngine)},
                ),
                patch("importlib.metadata.version", return_value="test"),
            ):
                report = run(args)
            runtime = yaml.safe_load((data / "damage/runtime.yaml").read_text())
            self.assertEqual(runtime["path"], str((data / "damage").resolve()))
            self.assertNotIn("path", yaml.safe_load((data / "damage/data.yaml").read_text()))
            self.assertEqual(calls[1]["split"], "val")
            self.assertEqual(report["per_class_ap50_95"], {"dent": 0.2})
            self.assertTrue((root / "runs/damage/evaluation.json").is_file())
            self.assertFalse(report["thresholds_calibrated"])


if __name__ == "__main__":
    unittest.main()
