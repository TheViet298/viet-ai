"""Prepare the user-provided public CarDD mirror for local inspection, not training."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests
from PIL import Image

REPO = "mouen5/CarDD"


def convert_bbox(box: list[float]) -> tuple[float, float, float, float]:
    if len(box) != 4 or not all(math.isfinite(v) for v in box):
        raise ValueError("Non-finite/invalid bbox")
    x, y, w, h = box
    if x < 0 or y < 0 or w <= 0 or h <= 0 or x + w > 1.000001 or y + h > 1.000001:
        raise ValueError("BBox outside normalized image bounds")
    return x + w / 2, y + h / 2, w, h


def prepare(source: Path, output: Path, workers: int, download: bool) -> dict:
    source, output = source.resolve(), output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    meta = json.loads((source / "hf-metadata.json").read_text(encoding="utf-8"))
    revision = meta["sha"]
    dataset = json.loads((source / "metadata.json").read_text(encoding="utf-8"))
    categories = sorted(dataset["info"]["categories"], key=lambda cat: cat["id"])
    names = [cat["name"] for cat in categories]
    mapping = {name: index for index, name in enumerate(names)}
    samples = json.loads((source / "samples.json").read_text(encoding="utf-8"))["samples"]
    images = output / "images" / "mirror_train"
    labels = output / "labels" / "mirror_train"
    images.mkdir(parents=True, exist_ok=True)
    labels.mkdir(parents=True, exist_ok=True)
    errors, rows, counts = [], [], Counter()

    def one(sample: dict) -> dict:
        rel = Path(sample["filepath"])
        if rel.is_absolute() or ".." in rel.parts or rel.suffix.lower() != ".jpg":
            raise ValueError("Unsafe/unexpected mirror image path")
        target = images / rel.name
        if download and not target.exists():
            url = f"https://huggingface.co/datasets/{REPO}/resolve/{revision}/{rel.as_posix()}"
            for attempt in range(3):
                try:
                    response = requests.get(url, timeout=(15, 60))
                    response.raise_for_status()
                    content = response.content
                    from io import BytesIO

                    with Image.open(BytesIO(content)) as im:
                        im.verify()
                    temporary = target.with_suffix(".part")
                    temporary.write_bytes(content)
                    temporary.replace(target)
                    break
                except Exception:
                    if attempt == 2:
                        raise
                    time.sleep(attempt + 1)
        if not target.is_file():
            raise FileNotFoundError(target.name)
        with Image.open(target) as im:
            im.load()
            width, height = im.size
        expected = sample["metadata"]
        if (width, height) != (expected["width"], expected["height"]):
            raise ValueError("Image size does not match annotation metadata")
        annotations, lines = [], []
        for detection in sample["detections"]["detections"]:
            name = detection["label"]
            if name not in mapping:
                raise ValueError("Unknown class name")
            box = convert_bbox(detection["bounding_box"])
            lines.append(str(mapping[name]) + " " + " ".join(f"{v:.9f}" for v in box))
            annotations.append(
                {"class_id": mapping[name], "label": name, "bbox_xywh_normalized": detection["bounding_box"]}
            )
        (labels / target.with_suffix(".txt").name).write_text("\n".join(lines) + "\n", encoding="utf-8")
        return {
            "image": target.relative_to(output).as_posix(),
            "label_file": f"labels/mirror_train/{target.stem}.txt",
            "source_filepath": sample["filepath"],
            "width": width,
            "height": height,
            "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
            "source_split": "mirror_train",
            "split_verified_against_original": False,
            "annotations": annotations,
        }

    with ThreadPoolExecutor(max_workers=workers) as pool:
        pending = {pool.submit(one, sample): sample["filepath"] for sample in samples}
        for number, future in enumerate(as_completed(pending), 1):
            try:
                row = future.result()
                rows.append(row)
                counts.update(ann["label"] for ann in row["annotations"])
            except Exception as exc:
                errors.append({"image": pending[future], "error_type": type(exc).__name__, "message": str(exc)[:160]})
            if number % 100 == 0 or number == len(samples):
                print(f"checked={number}/{len(samples)} ready={len(rows)} errors={len(errors)}", flush=True)
    rows.sort(key=lambda row: row["image"])
    hashes = Counter(row["sha256"] for row in rows)
    summary = {
        "repo": REPO,
        "revision": revision,
        "status": "inspection_staging; permission_not_verified; not_approved_for_training",
        "expected_images": len(samples),
        "ready_images": len(rows),
        "annotations": sum(counts.values()),
        "classes": names,
        "by_class": dict(counts),
        "errors": errors,
        "byte_duplicate_extras": sum(n - 1 for n in hashes.values()),
        "splits": {"mirror_train": len(rows)},
        "original_validation_test_available": False,
        "note": "Source mirror provides 2816 samples only. No original val/test recreated. Masks remain in samples.json; export is bbox detection only.",
    }
    (output / "manifest.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8"
    )
    (output / "preparation-report.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "class-map.json").write_text(
        json.dumps({"yolo_classes": mapping, "original_categories": categories}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    # No data.yaml train/val aliases: the original held-out splits are unavailable.
    (output / "README.md").write_text(
        "# CarDD mirror inspection staging\n\n"
        "Source: https://huggingface.co/datasets/mouen5/CarDD\n\n"
        f"Revision: `{revision}`. Actual counts in preparation-report.json.\n\n"
        "Images and validated YOLO bbox labels are in images/mirror_train and labels/mirror_train. "
        "Original validation/test splits are not supplied by this mirror. No train-ready split is claimed.\n\n"
        "YOLO label IDs follow source metadata: 0 dent, 1 scratch, 2 crack, 3 glass shatter, 4 lamp broken, 5 tire flat.\n\n"
        "Original CarDD license requires prior author consent. User reports consent not yet obtained. "
        "This local copy is for inspection/preparation; training/commercial permission is unverified. "
        "Do not redistribute data; preserve original metadata and license in ../cardd-source.\n",
        encoding="utf-8",
    )
    print(json.dumps({k: v for k, v in summary.items() if k != "errors"}, ensure_ascii=False, indent=2))
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args()
    report = prepare(args.source, args.output, args.workers, args.download)
    raise SystemExit(1 if report["errors"] else 0)
