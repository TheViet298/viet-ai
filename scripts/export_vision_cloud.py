"""Package existing splits and code for a notebook; does not upload or train."""

import argparse
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def export_bundle(baseline: Path, stage: Path, source: Path, output: Path) -> dict:
    if output.exists():
        raise FileExistsError(output)
    if not (source / "CarDD_license.pdf").is_file():
        raise FileNotFoundError("Source CarDD license must travel with the bundle")
    output.parent.mkdir(parents=True, exist_ok=True)
    prefix = "vision-baseline/"
    counts = {}
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_STORED, allowZip64=True) as archive:
        for split in ("train", "val", "needs_data"):
            images = sorted((baseline / "vehicles" / split).rglob("*.jpg"))
            counts["vehicles_" + split] = len(images)
            for image in images:
                archive.write(image, prefix + image.relative_to(baseline).as_posix())
            manifest = baseline / "vehicles" / f"{split}.jsonl"
            if manifest.exists():
                rows = [json.loads(s) for s in manifest.read_text(encoding="utf-8").splitlines()]
                portable = [
                    {k: r[k] for k in ("id", "sha256", "similarity_group", "labels", "split", "baseline_image")}
                    for r in rows
                ]
                archive.writestr(prefix + f"vehicles/{split}.jsonl", "".join(json.dumps(r) + "\n" for r in portable))
        for split in ("train", "val"):
            rows = [
                json.loads(s) for s in (baseline / "damage" / f"{split}.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            portable = []
            for row in rows:
                image = Path(row["image_path"])
                label = stage / row["label_file"]
                image_name = f"damage/images/{split}/{image.name}"
                label_name = f"damage/labels/{split}/{image.stem}.txt"
                archive.write(image, prefix + image_name)
                archive.write(label, prefix + label_name)
                portable.append({k: row[k] for k in ("id", "sha256", "similarity_group")})
                portable[-1].update(image=image_name, label_file=label_name, split=split)
            counts["damage_" + split] = len(rows)
            archive.writestr(prefix + f"damage/{split}.jsonl", "".join(json.dumps(r) + "\n" for r in portable))
        classes = json.loads((stage / "class-map.json").read_text(encoding="utf-8"))["yolo_classes"]
        yaml = "train: images/train\nval: images/val\nnames:\n"
        yaml += "".join(f"  {idx}: {json.dumps(name)}\n" for name, idx in sorted(classes.items(), key=lambda p: p[1]))
        archive.writestr(prefix + "damage/data.yaml", yaml)
        archive.write(baseline / "baseline-report.json", prefix + "baseline-report.json")
        for name in ("CarDD_license.pdf", "README.md", "metadata.json", "hf-metadata.json"):
            path = source / name
            if path.exists():
                archive.write(path, prefix + "sources/" + name)
        for name in (
            "scripts/train_vision_baseline.py",
            "requirements-vision-train.txt",
            "src/__init__.py",
            "src/services/__init__.py",
            "src/services/vision/__init__.py",
            "src/services/vision/contract.py",
        ):
            archive.write(ROOT / name, prefix + name)
        archive.writestr(
            prefix + "bundle-manifest.json",
            json.dumps(
                {
                    "status": "provisional_internal_validation",
                    "counts": counts,
                    "cardd_permission": "unverified",
                    "trained_model": False,
                },
                indent=2,
            ),
        )
    return counts


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--baseline", type=Path, default=Path("data/vision/baseline-20261004-v1"))
    p.add_argument("--stage", type=Path, default=Path("data/vision/cardd-yolo-staging"))
    p.add_argument("--source", type=Path, default=Path("data/vision/cardd-source"))
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    print(json.dumps(export_bundle(args.baseline, args.stage, args.source, args.output), indent=2))
