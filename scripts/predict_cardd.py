"""CLI for damage-only inference and versioned evidence JSON."""

import argparse
import contextlib
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.services.vision.damage_detector import BASELINE_SHA256, DEFAULT_WEIGHTS, CarddDamageDetector  # noqa: E402


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--image", type=Path, required=True)
    p.add_argument("--weights", type=Path, default=DEFAULT_WEIGHTS)
    p.add_argument("--expected-sha256", default=BASELINE_SHA256)
    p.add_argument("--output", type=Path)
    p.add_argument("--device", default="cpu")
    p.add_argument("--threshold", type=float, default=0.25)
    args = p.parse_args()
    detector = CarddDamageDetector(
        args.weights, expected_sha256=args.expected_sha256, threshold=args.threshold, device=args.device
    )
    # Limit reads before allocation; service applies the same bound.
    with args.image.open("rb") as image:
        content = image.read(detector.max_bytes + 1)
    started = time.perf_counter()
    config = Path(
        os.environ.get("YOLO_CONFIG_DIR", str(Path(__file__).resolve().parents[1] / "data/vision/runtime-config"))
    )
    config.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("YOLO_CONFIG_DIR", str(config))
    # First-time framework setup messages must not corrupt the JSON on stdout.
    with contextlib.redirect_stdout(sys.stderr):
        evidence = detector.analyze(content)
    serialized = evidence.model_dump_json(indent=2)
    print(serialized)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")
    print(json.dumps({"elapsed_seconds": time.perf_counter() - started}), file=sys.stderr)
    return 2 if evidence.damage.status == "unavailable" else 0


if __name__ == "__main__":
    raise SystemExit(main())
