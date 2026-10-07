import hashlib
import io
import tempfile
import types
import unittest
from pathlib import Path

from PIL import Image

from src.services.vision.damage_detector import CarddDamageDetector

NAMES = dict(enumerate(["dent", "scratch", "crack", "glass shatter", "lamp broken", "tire flat"]))


def photo():
    stream = io.BytesIO()
    Image.new("RGB", (48, 32), "silver").save(stream, format="JPEG")
    return stream.getvalue()


class Array:
    def __init__(self, values):
        self.values = values

    def cpu(self):
        return self

    def tolist(self):
        return self.values


class Engine:
    task = "detect"
    names = NAMES

    def __init__(self, boxes=None):
        self.boxes = (
            boxes
            if boxes is not None
            else types.SimpleNamespace(cls=Array([1]), conf=Array([0.9]), xyxyn=Array([[0.1, 0.2, 0.6, 0.7]]))
        )
        self.calls = []

    def predict(self, **kw):
        self.calls.append(kw)
        return [types.SimpleNamespace(boxes=self.boxes, names=self.names)]


class TestCarddInference(unittest.TestCase):
    def setup_detector(self, folder, engine):
        weights = Path(folder) / "best.pt"
        weights.write_bytes(b"local-checkpoint")
        digest = hashlib.sha256(weights.read_bytes()).hexdigest()
        return CarddDamageDetector(weights, expected_sha256=digest, loader=lambda path: engine)

    def test_prediction_is_damage_only_and_model_is_reused(self):
        with tempfile.TemporaryDirectory() as folder:
            engine = Engine()
            detector = self.setup_detector(folder, engine)
            result = detector.analyze(photo(), image_id="image-1")
            self.assertEqual(result.damage.status, "detected")
            self.assertEqual(result.damage.detections[0].label, "scratch")
            self.assertEqual(result.vehicle.status, "not_requested")
            self.assertEqual(result.ocr, "deferred_to_ocr")
            self.assertEqual(engine.calls[0]["device"], "cpu")
            self.assertEqual(engine.calls[0]["source"].mode, "RGB")
            detector.analyze(photo())
            self.assertEqual(len(engine.calls), 2)

    def test_missing_weights_does_not_download_or_claim_no_damage(self):
        detector = CarddDamageDetector(Path("missing-local-checkpoint.pt"), loader=lambda p: self.fail("must not load"))
        self.assertEqual(detector.analyze(photo()).damage.reason, "weights_missing")

    def test_not_requested_skips_image_and_weights(self):
        detector = CarddDamageDetector(Path("missing.pt"))
        self.assertEqual(detector.analyze(b"", image_id="x", requested=False).damage.status, "not_requested")

    def test_bad_image_and_oversize_are_unavailable(self):
        detector = CarddDamageDetector(Path("missing.pt"), max_bytes=20)
        self.assertEqual(detector.analyze(b"not an image").damage.reason, "invalid_image")
        self.assertEqual(detector.analyze(photo()).damage.reason, "image_too_large")

    def test_hash_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "best.pt"
            path.write_bytes(b"wrong")
            detector = CarddDamageDetector(path, expected_sha256="0" * 64, loader=lambda p: self.fail("must not load"))
            self.assertEqual(detector.analyze(photo()).damage.reason, "checkpoint_hash_mismatch")

    def test_wrong_class_map_is_unavailable(self):
        with tempfile.TemporaryDirectory() as folder:
            engine = Engine()
            engine.names = {0: "car"}
            self.assertEqual(self.setup_detector(folder, engine).analyze(photo()).damage.reason, "model_incompatible")

    def test_empty_detection_is_not_detected_and_error_is_unavailable(self):
        with tempfile.TemporaryDirectory() as folder:
            empty = types.SimpleNamespace(cls=Array([]), conf=Array([]), xyxyn=Array([]))
            detector = self.setup_detector(folder, Engine(empty))
            self.assertEqual(detector.analyze(photo()).damage.status, "not_detected")
            detector._model.predict = lambda **kw: (_ for _ in ()).throw(RuntimeError("engine error"))
            self.assertEqual(detector.analyze(photo()).damage.reason, "inference_failed")

    def test_invalid_detection_box_does_not_become_no_damage(self):
        with tempfile.TemporaryDirectory() as folder:
            engine = Engine(
                types.SimpleNamespace(cls=Array([1]), conf=Array([0.8]), xyxyn=Array([[0.9, 0.2, 0.1, 0.7]]))
            )
            self.assertEqual(self.setup_detector(folder, engine).analyze(photo()).damage.reason, "invalid_model_output")

    def test_exif_orientation_is_applied_before_prediction(self):
        stream = io.BytesIO()
        exif = Image.Exif()
        exif[274] = 6
        Image.new("RGB", (48, 32), "silver").save(stream, format="JPEG", exif=exif)
        with tempfile.TemporaryDirectory() as folder:
            engine = Engine()
            detector = self.setup_detector(folder, engine)
            self.assertEqual(detector.analyze(stream.getvalue()).damage.status, "detected")
            self.assertEqual(engine.calls[0]["source"].size, (32, 48))


if __name__ == "__main__":
    unittest.main()
