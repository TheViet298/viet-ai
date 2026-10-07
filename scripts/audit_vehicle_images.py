"""Read-only source audit; write manifests and contact sheets to a separate output."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


def audit(source: Path, output: Path) -> dict:
    source, output = source.resolve(), output.resolve()
    if output == source or source in output.parents:
        raise ValueError("Output must be outside the original source tree")
    output.mkdir(parents=True, exist_ok=True)
    sheet_dir = output / "contact_sheets"
    sheet_dir.mkdir(exist_ok=True)
    rows, hashes, pixels = [], defaultdict(list), defaultdict(list)
    for number, path in enumerate(sorted(source.rglob("*"))):
        if not path.is_file():
            continue
        rel = path.relative_to(source)
        parts = rel.parts
        row = {
            "id": f"IMG-{len(rows) + 1:04d}",
            "path": str(path),
            "relative_path": rel.as_posix(),
            "source_model": parts[0],
            "category": parts[1] if len(parts) > 2 else "unknown",
            "bytes": path.stat().st_size,
            "flags": [],
            "review": "pending",
            "provenance": "user_provided; upstream source/license not supplied",
            "capture_group_id": None,
        }
        row["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        hashes[row["sha256"]].append(row["id"])
        try:
            with Image.open(path) as image:
                row["format"] = image.format
                image.load()
                row["frames"] = getattr(image, "n_frames", 1)
                row["has_exif"] = bool(image.getexif())
                upright = ImageOps.exif_transpose(image).convert("RGBA")
                row["width"], row["height"] = upright.size
                row["transparent"] = upright.getextrema()[3][0] < 255
                row["pixel_sha256"] = hashlib.sha256(str(upright.size).encode() + upright.tobytes()).hexdigest()
                pixels[row["pixel_sha256"]].append(row["id"])
                background = Image.new("RGBA", upright.size, "white")
                background.alpha_composite(upright)
                gray = background.convert("L").resize((9, 8))
                values = list(gray.getdata())
                bits = [values[y * 9 + x] > values[y * 9 + x + 1] for y in range(8) for x in range(8)]
                row["dhash"] = f"{sum(int(v) << i for i, v in enumerate(bits)):016x}"
                if min(upright.size) < 224:
                    row["flags"].append("small_resolution")
                if row["width"] / row["height"] > 3 or row["height"] / row["width"] > 3:
                    row["flags"].append("extreme_aspect_ratio")
                if row["frames"] != 1:
                    row["flags"].append("animated")
                row["decode_ok"] = True
        except Exception as exc:
            row["decode_ok"] = False
            row["flags"].append("decode_error")
            row["decode_error"] = str(exc)
        rows.append(row)
    by_id = {row["id"]: row for row in rows}
    duplicates = [ids for ids in pixels.values() if len(ids) > 1]
    for group in duplicates:
        for rid in group[1:]:
            by_id[rid]["duplicate_of"] = group[0]
            by_id[rid]["flags"].append("exact_pixel_duplicate")
        if len({by_id[rid]["source_model"] for rid in group}) > 1:
            for rid in group:
                by_id[rid]["flags"].append("cross_model_duplicate")
    near = []
    decoded = [row for row in rows if row.get("decode_ok")]
    for i, left in enumerate(decoded):
        for right in decoded[i + 1 :]:
            if left["pixel_sha256"] == right["pixel_sha256"]:
                continue
            distance = (int(left["dhash"], 16) ^ int(right["dhash"], 16)).bit_count()
            if distance <= 5:
                near.append(
                    {
                        "left": left["id"],
                        "right": right["id"],
                        "distance": distance,
                        "review": "pending",
                        "reason": "similar structure only; not an automatic duplicate decision",
                    }
                )
    for row in rows:
        row["classifier_candidate"] = bool(
            row.get("decode_ok")
            and row["category"] in {"exterior", "color"}
            and not row.get("duplicate_of")
            and not row["flags"]
        )
    font_path = Path("C:/Windows/Fonts/arial.ttf")
    font = ImageFont.truetype(str(font_path), 13) if font_path.exists() else ImageFont.load_default()
    for offset in range(0, len(rows), 60):
        page = rows[offset : offset + 60]
        canvas = Image.new("RGB", (1200, 10 * 146), "#eeeeee")
        draw = ImageDraw.Draw(canvas)
        for index, row in enumerate(page):
            x, y = (index % 6) * 200, (index // 6) * 146
            if row.get("decode_ok"):
                with Image.open(row["path"]) as raw:
                    im = ImageOps.exif_transpose(raw).convert("RGBA")
                    im.thumbnail((194, 110))
                    tile = Image.new("RGBA", im.size, "white")
                    tile.alpha_composite(im)
                    canvas.paste(tile.convert("RGB"), (x + (200 - im.width) // 2, y))
            draw.text((x + 3, y + 111), f"{row['id']} {row['source_model']}", fill="black", font=font)
            draw.text(
                (x + 3, y + 128),
                row["category"] + (" DUP" if row.get("duplicate_of") else ""),
                fill="red" if row["flags"] else "#333333",
                font=font,
            )
        canvas.save(sheet_dir / f"page-{offset // 60 + 1:02d}.jpg", quality=90)
    (output / "manifest.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8"
    )
    summary = {
        "source": str(source),
        "total_files": len(rows),
        "decode_ok": sum(row.get("decode_ok", False) for row in rows),
        "decode_errors": [row["id"] for row in rows if not row.get("decode_ok")],
        "bytes": sum(row["bytes"] for row in rows),
        "by_model": dict(Counter(row["source_model"] for row in rows)),
        "by_category": dict(Counter(row["category"] for row in rows)),
        "flags": dict(Counter(flag for row in rows for flag in row["flags"])),
        "byte_duplicate_groups": [ids for ids in hashes.values() if len(ids) > 1],
        "pixel_duplicate_groups": duplicates,
        "near_pairs": near,
        "technical_candidates": sum(row["classifier_candidate"] for row in rows),
        "note": "Candidates require visual/label/provenance review; no train/test split or source deletion.",
    }
    (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                key: value
                for key, value in summary.items()
                if key not in {"near_pairs", "pixel_duplicate_groups", "byte_duplicate_groups"}
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    print(f"pixel_duplicate_groups={len(duplicates)}; near_pairs={len(near)}")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    audit(args.source, args.output)
