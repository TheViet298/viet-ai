"""Create provisional development splits; never claim an independent acceptance test."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image


def group_rows(rows: list[dict], similar_pairs: list[tuple[str, str]]) -> dict[str, list[dict]]:
    parent = {r["id"]: r["id"] for r in rows}
    if len(parent) != len(rows):
        raise ValueError("Duplicate row IDs")

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        if a in parent and b in parent:
            x, y = find(a), find(b)
            parent[max(x, y)] = min(x, y)

    hashes = {}
    for row in sorted(rows, key=lambda r: r["id"]):
        sha = row["sha256"]
        if sha in hashes:
            union(row["id"], hashes[sha])
        hashes[sha] = row["id"]
    for a, b in similar_pairs:
        union(a, b)
    groups = defaultdict(list)
    for row in sorted(rows, key=lambda r: r["id"]):
        groups[find(row["id"])].append(row)
    return dict(sorted(groups.items()))


def split_groups(groups: dict[str, list[dict]], val_fraction: float = 0.2, seed: int = 142) -> dict[str, list[str]]:
    if not 0 < val_fraction < 0.5:
        raise ValueError("Validation fraction must be between 0 and 0.5")
    totals = Counter(label for group in groups.values() for r in group for label in set(r["labels"]))
    occurrences = Counter(
        label for group in groups.values() for label in {value for r in group for value in r["labels"]}
    )
    targets = {label: max(1, round(n * val_fraction)) if occurrences[label] > 1 else 0 for label, n in totals.items()}
    val_counts, val_groups = Counter(), set()
    ordered = sorted(groups, key=lambda gid: hashlib.sha256(f"{seed}:{gid}".encode()).hexdigest())
    for gid in ordered:
        counts = Counter(label for r in groups[gid] for label in set(r["labels"]))
        if all(
            val_counts[label] + n <= targets[label] and val_counts[label] + n < totals[label]
            for label, n in counts.items()
        ):
            val_groups.add(gid)
            val_counts.update(counts)
    return {
        name: sorted(r["id"] for gid, group in groups.items() if (gid in val_groups) == (name == "val") for r in group)
        for name in ("train", "val")
    }


def damage_hashes(rows: list[dict], stage: Path) -> dict[str, int]:
    cache = stage / "perceptual-hashes.json"
    saved = json.loads(cache.read_text()) if cache.exists() else {}

    def fingerprint(row):
        rid = row["id"]
        if rid in saved and saved[rid]["sha256"] == row["sha256"]:
            return rid, saved[rid]
        with Image.open(row["image_path"]) as im:
            im.draft("L", (90, 80))
            gray = im.convert("L").resize((9, 8))
            pixels = list(gray.tobytes())
            bits = [pixels[y * 9 + x] > pixels[y * 9 + x + 1] for y in range(8) for x in range(8)]
            value = sum(int(bit) << i for i, bit in enumerate(bits))
        return rid, {"sha256": row["sha256"], "dhash": f"{value:016x}"}

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = dict(pool.map(fingerprint, rows))
    cache.write_text(json.dumps(results, indent=2))
    return {rid: int(value["dhash"], 16) for rid, value in results.items()}


def export(rows: list[dict], pairs: list[tuple[str, str]], destination: Path, classification: bool) -> dict:
    groups = group_rows(rows, pairs)
    split = split_groups(groups)
    where = {rid: name for name, ids in split.items() for rid in ids}
    group_ids = {r["id"]: gid for gid, group in groups.items() for r in group}
    deferred = []
    if classification:
        train_labels = {label for row in rows if where[row["id"]] == "train" for label in row["labels"]}
        val_labels = {label for row in rows if where[row["id"]] == "val" for label in row["labels"]}
        deferred = sorted(train_labels - val_labels)
        for group in groups.values():
            if any(label in deferred for row in group for label in row["labels"]):
                for row in group:
                    where[row["id"]] = "needs_data"
        active_train = {label for row in rows if where[row["id"]] == "train" for label in row["labels"]}
        active_val = {label for row in rows if where[row["id"]] == "val" for label in row["labels"]}
        if active_train != active_val:
            raise ValueError("Classifier needs identical supported label sets in train/val")
    destination.mkdir(parents=True)
    output_rows = []
    for row in sorted(rows, key=lambda r: r["id"]):
        name = where[row["id"]]
        item = {**row, "split": name, "similarity_group": group_ids[row["id"]]}
        if classification:
            target = destination / name / row["labels"][0] / Path(row["image_path"]).name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(row["image_path"], target)
            item["baseline_image"] = target.relative_to(destination).as_posix()
        output_rows.append(item)
    for name in ("train", "val", "needs_data") if classification else ("train", "val"):
        selected = [r for r in output_rows if r["split"] == name]
        (destination / f"{name}.jsonl").write_text(
            "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in selected), encoding="utf-8"
        )
        if not classification:
            (destination / f"{name}.txt").write_text(
                "".join(Path(r["image_path"]).resolve().as_posix() + "\n" for r in selected), encoding="utf-8"
            )
    counts = {
        name: dict(Counter(label for row in output_rows if row["split"] == name for label in set(row["labels"])))
        for name in ("train", "val")
    }
    report = {
        "status": "provisional_development_baseline",
        "images": len(rows),
        "groups": len(groups),
        "candidate_similarity_pairs": len(pairs),
        "largest_group": max(map(len, groups.values())),
        "train": sum(value == "train" for value in where.values()),
        "val": sum(value == "val" for value in where.values()),
        "needs_data": sum(value == "needs_data" for value in where.values()),
        "deferred_classes": deferred,
        "test": 0,
        "seed": 142,
        "by_class": counts,
        "train_only_classes": sorted(set(counts["train"]) - set(counts["val"])),
        "group_leakage": 0,
        "original_benchmark_split": False,
        "limitations": [
            "Heuristic perceptual groups are conservative, not verified capture IDs.",
            "Internal validation only; no independent real-world acceptance test.",
            "Source labels and permissions remain as documented in the data audit.",
        ],
    }
    (destination / "split-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def prepare(root: Path, output: Path) -> dict:
    root, output = root.resolve(), output.resolve()
    if output.exists():
        raise ValueError("Choose a new baseline output directory; existing splits are preserved")
    vehicle_source = root / "vinfast-reference-clean"
    vehicles = [
        json.loads(line) for line in (vehicle_source / "manifest.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    vehicle_rows = [
        {**row, "image_path": str(vehicle_source / row["prepared_image"]), "labels": [row["source_model"]]}
        for row in vehicles
    ]
    similarities = json.loads((root / "audit-20261004/summary.json").read_text(encoding="utf-8"))["near_pairs"]
    valid_ids = {row["id"] for row in vehicle_rows}
    pairs = [(p["left"], p["right"]) for p in similarities if p["left"] in valid_ids and p["right"] in valid_ids]
    vehicle_report = export(vehicle_rows, pairs, output / "vehicles", True)
    stage = root / "cardd-yolo-staging"
    damage = [json.loads(line) for line in (stage / "manifest.jsonl").read_text(encoding="utf-8").splitlines()]
    damage_rows = [
        {
            **row,
            "id": Path(row["image"]).stem,
            "image_path": str(stage / row["image"]),
            "labels": sorted({a["label"] for a in row["annotations"]}),
        }
        for row in damage
    ]
    fingerprints = damage_hashes(damage_rows, stage)
    print("CarDD fingerprints complete; grouping similar samples", flush=True)
    items = sorted(fingerprints.items())
    pairs = [(a, b) for i, (a, ha) in enumerate(items) for b, hb in items[i + 1 :] if (ha ^ hb).bit_count() <= 5]
    damage_report = export(damage_rows, pairs, output / "damage", False)
    classes = json.loads((stage / "class-map.json").read_text(encoding="utf-8"))["yolo_classes"]
    config = [
        "# Internal development split; not the original CarDD benchmark.",
        "# Re-run exporter after moving to cloud: image lists contain local absolute paths.",
        "path: " + json.dumps((output / "damage").as_posix()),
        "train: train.txt",
        "val: val.txt",
        "names:",
    ]
    config += [f"  {idx}: " + json.dumps(name) for name, idx in sorted(classes.items(), key=lambda p: p[1])]
    (output / "damage/data.yaml").write_text("\n".join(config) + "\n", encoding="utf-8")
    report = {"vehicles": vehicle_report, "damage": damage_report, "trained_model": False}
    (output / "baseline-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, default=Path("data/vision"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    prepare(args.data_root, args.output)
