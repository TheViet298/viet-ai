"""Measure a supplied classifier locally; keep validation separate from smoke negatives."""

import argparse
import hashlib
import json
import time
from pathlib import Path


def summarize(rows, labels, threshold):
    per_class = {}
    for label in labels:
        tp = sum(r["truth"] == label and r["prediction"] == label for r in rows)
        support = sum(r["truth"] == label for r in rows)
        predicted = sum(r["prediction"] == label for r in rows)
        precision = tp / predicted if predicted else 0
        recall = tp / support if support else 0
        per_class[label] = {
            "support": support, "correct": tp, "precision": precision, "recall": recall,
            "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0,
        }
    accepted = [r for r in rows if r["confidence"] >= threshold]
    return {
        "count": len(rows), "correct": sum(r["correct"] for r in rows),
        "top1": sum(r["correct"] for r in rows) / len(rows) if rows else None,
        "top5": sum(r["truth"] in r["top5"] for r in rows) / len(rows) if rows else None,
        "macro_f1": sum(c["f1"] for c in per_class.values()) / len(labels),
        "threshold": threshold, "accepted_count": len(accepted),
        "accepted_correct": sum(r["correct"] for r in accepted),
        "accepted_accuracy": sum(r["correct"] for r in accepted) / len(accepted) if accepted else None,
        "coverage": len(accepted) / len(rows) if rows else None,
        "per_class": per_class,
    }


def run(args):
    from PIL import Image
    from ultralytics import YOLO

    checkpoint = args.artifacts / "weights/best.pt"
    previous = json.loads((args.artifacts / "evaluation.json").read_text())
    version = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
    if version != previous["checkpoint_sha256"]:
        raise ValueError("Checkpoint hash mismatch")
    if args.output.exists():
        raise FileExistsError(args.output)
    args.output.mkdir(parents=True)
    model = YOLO(str(checkpoint))
    labels = [previous["names"][str(i)] for i in range(len(previous["names"]))]
    if model.task != "classify" or [model.names[i] for i in range(len(model.names))] != labels:
        raise ValueError("Checkpoint task or label map mismatch")

    def predict(path):
        started = time.perf_counter()
        result = model.predict(str(path), device="cpu", imgsz=224, verbose=False)[0]
        scores = result.probs.data.cpu().tolist()
        ranked = sorted(range(len(scores)), key=scores.__getitem__, reverse=True)
        return {
            "prediction": result.names[ranked[0]], "confidence": float(scores[ranked[0]]),
            "margin": float(scores[ranked[0]] - scores[ranked[1]]),
            "top5": [result.names[i] for i in ranked[:5]],
            "elapsed_s": time.perf_counter() - started,
        }

    rows = []
    split_hashes = {}
    for split in ("train", "val"):
        paths = sorted((args.data / split).glob("*/*.jpg"))
        split_hashes[split] = {hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
        for path in paths:
            if path.parent.name not in labels:
                raise ValueError(f"Unexpected dataset label: {path.parent.name}")
            prediction = predict(path)
            rows.append({"split": split, "image": path.relative_to(args.data).as_posix(),
                         "truth": path.parent.name, "correct": prediction["prediction"] == path.parent.name,
                         **prediction})
        print(f"Measured {split}: {len(paths)} images", flush=True)
    if split_hashes["train"] & split_hashes["val"]:
        raise ValueError("Exact byte leakage between train and validation")

    # These are smoke negatives only, not a calibrated out-of-distribution benchmark.
    negatives = []
    for color in ("white", "black"):
        path = args.output / f"negative-{color}.png"
        Image.new("RGB", (224, 224), color).save(path)
        prediction = predict(path)
        negatives.append({"image": path.name, "type": "synthetic_blank", **prediction,
                          "falsely_accepted": prediction["confidence"] >= .7})
    for path in args.negative:
        prediction = predict(path)
        negatives.append({"image": path.name, "type": "user_selected_non_vehicle_fixture", **prediction,
                          "falsely_accepted": prediction["confidence"] >= .7})
    summaries = {split: summarize([r for r in rows if r["split"] == split], labels, .7)
                 for split in ("train", "val")}
    mismatches = [r for r in rows if r["split"] == "val" and not r["correct"]]
    report = {
        "checkpoint_sha256": version, "device": "cpu", "input_size": 224,
        "evaluation_type": "rerun_internal_validation_not_independent_test",
        "exact_byte_leakage": False, "metrics": summaries, "predictions": rows,
        "validation_mistakes": mismatches, "negative_smoke": negatives,
        "matches_notebook_top1": abs(summaries["val"]["top1"] - previous["metrics"]["metrics/accuracy_top1"]) < 1e-6,
        "limitations": ["Folder labels are not independently verified", "Threshold 0.7 uncalibrated",
                        "No independent labeled real-world test", "Synthetic/UI negatives are not representative"],
    }
    (args.output / "evaluation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"metrics": summaries, "validation_mistakes": mismatches,
                      "negative_smoke": negatives, "matches_notebook_top1": report["matches_notebook_top1"]}, indent=2))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--negative", type=Path, action="append", default=[])
    run(parser.parse_args())
