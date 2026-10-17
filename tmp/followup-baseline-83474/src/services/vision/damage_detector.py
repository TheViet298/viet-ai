"""Local CarDD inference. No downloads, upload routes or vehicle model inference."""

import hashlib
import io
import logging
import math
import threading
import warnings
from collections.abc import Callable
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from src.services.vision.contract import DamageResult, VisionEvidence, damage_result

LOGGER = logging.getLogger(__name__)
CLASS_NAMES = ["dent", "scratch", "crack", "glass shatter", "lamp broken", "tire flat"]
BASELINE_SHA256 = "f0adf5fbcec8ddaf2cecd78ce5618c7244b484263e34d00002a6e9c765137efa"
DEFAULT_WEIGHTS = Path(__file__).resolve().parents[3] / "data/vision/trained/cardd-damage-baseline-v1/weights/best.pt"


class DetectorUnavailableError(Exception):
    """A stable failure reason suitable for evidence."""


def load_local_model(path: Path):
    from ultralytics import YOLO

    return YOLO(str(path), task="detect")


class CarddDamageDetector:
    """Reuse one instance per worker; serialize model load/predict for thread safety."""

    def __init__(
        self,
        weights: Path = DEFAULT_WEIGHTS,
        *,
        expected_sha256: str | None = BASELINE_SHA256,
        threshold: float = 0.25,
        device: str = "cpu",
        max_bytes: int = 5 * 1024 * 1024,
        max_pixels: int = 20_000_000,
        loader: Callable = load_local_model,
    ):
        if not math.isfinite(threshold) or not 0 <= threshold <= 1:
            raise ValueError("threshold must be finite in [0,1]")
        if max_bytes < 1 or max_pixels < 1:
            raise ValueError("image limits must be positive")
        self.weights = Path(weights)
        self.expected_sha256 = expected_sha256
        self.threshold, self.device = threshold, device
        self.max_bytes, self.max_pixels = max_bytes, max_pixels
        self.loader = loader
        self._model = None
        self._version = None
        self._lock = threading.Lock()

    def _load(self):
        if self._model is not None:
            return
        if not self.weights.is_file():
            raise DetectorUnavailableError("weights_missing")
        digest = hashlib.sha256(self.weights.read_bytes()).hexdigest()
        if self.expected_sha256 and digest != self.expected_sha256:
            raise DetectorUnavailableError("checkpoint_hash_mismatch")
        try:
            model = self.loader(self.weights)
        except ImportError as exc:
            raise DetectorUnavailableError("runtime_dependency_missing") from exc
        except Exception as exc:
            LOGGER.exception("Could not initialize CarDD model")
            raise DetectorUnavailableError("model_load_failed") from exc
        if model.task != "detect" or model.names != dict(enumerate(CLASS_NAMES)):
            raise DetectorUnavailableError("model_incompatible")
        self._model, self._version = model, digest

    def _decode(self, content: bytes) -> Image.Image:
        if len(content) > self.max_bytes:
            raise DetectorUnavailableError("image_too_large")
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(io.BytesIO(content)) as image:
                    if image.width * image.height > self.max_pixels:
                        raise DetectorUnavailableError("image_too_large")
                    if getattr(image, "n_frames", 1) != 1:
                        raise DetectorUnavailableError("animated_image_unsupported")
                    image.load()
                    return ImageOps.exif_transpose(image).convert("RGB")
        except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
            raise DetectorUnavailableError("image_too_large") from exc
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            raise DetectorUnavailableError("invalid_image") from exc

    def analyze(self, content: bytes, *, image_id: str | None = None, requested: bool = True) -> VisionEvidence:
        """Boxes refer to the EXIF-oriented image. Caller must display that same orientation."""
        identifier = image_id or hashlib.sha256(content).hexdigest()
        if not requested:
            return VisionEvidence(image_id=identifier)
        try:
            image = self._decode(content)
            with self._lock:
                self._load()
                try:
                    outputs = self._model.predict(
                        source=image, device=self.device, conf=self.threshold, imgsz=640, verbose=False
                    )
                except Exception as exc:
                    LOGGER.exception("CarDD prediction failed")
                    raise DetectorUnavailableError("inference_failed") from exc
                try:
                    if len(outputs) != 1 or outputs[0].boxes is None or outputs[0].names != self._model.names:
                        raise ValueError("Expected one detection result and matching labels")
                    boxes = outputs[0].boxes
                    labels, scores, coords = (
                        boxes.cls.cpu().tolist(),
                        boxes.conf.cpu().tolist(),
                        boxes.xyxyn.cpu().tolist(),
                    )
                    if len(labels) != len(scores) or len(scores) != len(coords):
                        raise ValueError("Inconsistent detection arrays")
                    detections = []
                    for cls, score, box in zip(labels, scores, coords):
                        if not math.isfinite(cls) or cls != int(cls) or int(cls) not in self._model.names:
                            raise ValueError("Invalid model class ID")
                        detections.append({"label": self._model.names[int(cls)], "confidence": score, "bbox_xyxy": box})
                    result = damage_result(detections, self._version, self.threshold)
                except (ValueError, TypeError, AttributeError, IndexError) as exc:
                    raise DetectorUnavailableError("invalid_model_output") from exc
            return VisionEvidence(image_id=identifier, damage=result)
        except DetectorUnavailableError as exc:
            return VisionEvidence(
                image_id=identifier,
                damage=DamageResult(
                    status="unavailable", reason=str(exc), model_version=self._version, threshold=self.threshold
                ),
            )
