"""Shared notebook CLI. Preflight is offline; training is explicit and requires GPU."""

import argparse
import hashlib
import importlib.metadata
import json
import math
import platform
import time
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def preflight(root: Path, task: str) -> dict:
    root = root.resolve()
    if task == "vehicles":
        splits = {
            s: {p.name: sorted(p.glob("*.jpg")) for p in (root / "vehicles" / s).iterdir() if p.is_dir()}
            for s in ("train", "val")
        }
        if not splits["train"] or set(splits["train"]) != set(splits["val"]):
            raise ValueError("Classifier train/val class directories must match")
        if any(not images for split in splits.values() for images in split.values()):
            raise ValueError("Empty classifier class")
        names = sorted(splits["train"])
        files = {s: [p for imgs in split.values() for p in imgs] for s, split in splits.items()}
        data = str(root / "vehicles")
    elif task == "damage":
        files = {s: sorted((root / "damage/images" / s).glob("*.jpg")) for s in ("train", "val")}
        if any(not images for images in files.values()):
            raise ValueError("Empty damage split")
        for split, images in files.items():
            for image in images:
                label = root / "damage/labels" / split / (image.stem + ".txt")
                if not label.is_file():
                    raise ValueError(f"Missing YOLO label: {label}")
                for line in label.read_text().splitlines():
                    values = line.split()
                    if len(values) != 5:
                        raise ValueError(f"Invalid YOLO row: {label}")
                    cls, x, y, w, h = map(float, values)
                    if not all(math.isfinite(v) for v in (cls, x, y, w, h)) or cls not in range(6):
                        raise ValueError(f"Invalid class/coordinates: {label}")
                    # Labels have nine decimal places; center/size rounding may move a border by <1e-9.
                    eps = 1e-8
                    if not (
                        0 < w <= 1
                        and 0 < h <= 1
                        and w / 2 - eps <= x <= 1 - w / 2 + eps
                        and h / 2 - eps <= y <= 1 - h / 2 + eps
                    ):
                        raise ValueError(f"Box outside image: {label}")
        names = ["dent", "scratch", "crack", "glass shatter", "lamp broken", "tire flat"]
        data = str(root / "damage/data.yaml")
    else:
        raise ValueError("Unknown task")
    hashes = {s: {sha256(p) for p in paths} for s, paths in files.items()}
    if hashes["train"] & hashes["val"]:
        raise ValueError("Exact image leakage between train and validation")
    digest = hashlib.sha256()
    for split, paths in files.items():
        for path in paths:
            digest.update(f"{split}:{path.relative_to(root).as_posix()}:{sha256(path)}\n".encode())
            if task == "damage":
                digest.update((root / "damage/labels" / split / (path.stem + ".txt")).read_bytes())
    return {
        "task": task,
        "data": data,
        "counts": {s: len(p) for s, p in files.items()},
        "names": names,
        "dataset_sha256": digest.hexdigest(),
        "evaluation": "internal_validation_only",
    }


def run(args):
    info = preflight(args.data_root, args.task)
    print(json.dumps(info, indent=2))
    if args.check_only:
        return info
    import torch
    import yaml
    from ultralytics import YOLO

    if args.device != "cpu" and not torch.cuda.is_available():
        raise RuntimeError("Enable a GPU notebook runtime, or explicitly pass --device cpu for a small smoke run")
    if (args.output / args.task).exists():
        raise FileExistsError("Choose a new --output directory; existing training artifacts are preserved")
    if args.task == "damage":
        cfg = yaml.safe_load(Path(info["data"]).read_text())
        actual = [cfg["names"][i] for i in sorted(cfg["names"])]
        if actual != info["names"]:
            raise ValueError("Damage class IDs differ from source metadata")
        cfg["path"] = str((args.data_root / "damage").resolve())
        # Runtime paths are set only on the new machine; portable source YAML remains unchanged.
        runtime = args.data_root / "damage/runtime.yaml"
        runtime.write_text(yaml.safe_dump(cfg, sort_keys=False))
        info["data"] = str(runtime.resolve())
    model = YOLO(args.model or ("yolo11n-cls.pt" if args.task == "vehicles" else "yolo11n.pt"))
    expected = "classify" if args.task == "vehicles" else "detect"
    if model.task != expected:
        raise ValueError(f"Expected {expected} checkpoint, got {model.task}")
    started = time.time()
    model.train(
        data=info["data"],
        epochs=args.epochs,
        imgsz=args.imgsz or (224 if args.task == "vehicles" else 640),
        batch=args.batch,
        device=args.device,
        seed=142,
        deterministic=True,
        workers=2,
        patience=10,
        project=str(args.output.resolve()),
        name=args.task,
        exist_ok=False,
        plots=True,
    )
    folder = Path(model.trainer.save_dir)
    checkpoint = folder / "weights/best.pt"
    if not checkpoint.is_file():
        raise RuntimeError("Training did not produce best.pt")
    best = YOLO(str(checkpoint))
    if [best.names[i] for i in sorted(best.names)] != info["names"]:
        raise ValueError("Checkpoint class map differs from dataset")
    metrics = best.val(
        data=info["data"],
        split="val",
        device=args.device,
        plots=True,
        project=str(folder),
        name="validation",
        exist_ok=False,
    )
    report = {
        **info,
        "checkpoint_sha256": sha256(checkpoint),
        "checkpoint": str(checkpoint),
        "selection": "Ultralytics validation fitness (classifier top1/top5; detector mAP), not test",
        "thresholds_calibrated": False,
        "elapsed_seconds": time.time() - started,
        "metrics": {k: float(v) for k, v in metrics.results_dict.items()},
        "arguments": {k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()},
        "python": platform.python_version(),
        "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "versions": {p: importlib.metadata.version(p) for p in ("ultralytics", "torch", "torchvision", "numpy")},
        "names": best.names,
        "limitations": ["No independent test", "No calibrated unknown rejection", "No VinFast damage evaluation"],
    }
    if args.task == "vehicles":
        from sklearn.metrics import classification_report, confusion_matrix

        truth, predictions = [], []
        paths = sorted((args.data_root / "vehicles/val").glob("*/*.jpg"))
        for path in paths:
            result = best.predict(str(path), device=args.device, verbose=False)[0]
            truth.append(path.parent.name)
            predictions.append(result.names[int(result.probs.top1)])
        report["per_class"] = classification_report(
            truth, predictions, labels=info["names"], output_dict=True, zero_division=0
        )
        report["macro_f1"] = report["per_class"]["macro avg"]["f1-score"]
        report["confusion_matrix"] = confusion_matrix(truth, predictions, labels=info["names"]).tolist()
    else:
        report["per_class_ap50_95"] = {
            best.names[i]: float(ap) for i, ap in zip(metrics.box.ap_class_index, metrics.box.ap)
        }
    (folder / "evaluation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Artifacts: {folder}")
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--task", choices=["vehicles", "damage"], required=True)
    p.add_argument("--data-root", type=Path, required=True)
    p.add_argument("--output", type=Path, default=Path("runs/vision"))
    p.add_argument("--model")
    p.add_argument("--epochs", type=int, default=40)
    p.add_argument("--batch", type=int, default=16)
    p.add_argument("--imgsz", type=int)
    p.add_argument("--device", default="0")
    p.add_argument("--check-only", action="store_true")
    run(p.parse_args())
