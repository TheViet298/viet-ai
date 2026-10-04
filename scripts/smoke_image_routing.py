"""Live classification check: public cluster images, supplied exterior photo, blank image."""
import argparse
import asyncio
import io
import json
import time
from pathlib import Path

import httpx
from PIL import Image

from src.services.dashboard_vision_service import prepare_image
from src.services.image_routing import classify_vehicle_image


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--exterior-image", type=Path)
    parser.add_argument("--public-exterior", action="store_true")
    args = parser.parse_args()
    catalog = json.loads(Path("dataset/img_warning_taplo/images/image_catalog.json").read_text(encoding="utf-8"))
    cases = []
    async with httpx.AsyncClient(timeout=30) as client:
        for item in catalog[:2]:
            response = await client.get(item["source_url"])
            response.raise_for_status()
            cases.append((item["image_id"], response.content, "dashboard"))
        if args.public_exterior:
            # Public vehicle illustration linked by VinFast's aftersales page.
            response = await client.get("https://static-cms-prod.vinfastauto.com/statics/images/aftersale-shared/vehicle-oto.png")
            response.raise_for_status()
            cases.append(("public-exterior", response.content, "exterior"))
            Path(".test-runs").mkdir(exist_ok=True)
            Path(".test-runs/public-exterior.png").write_bytes(response.content)
    if args.exterior_image:
        cases.append(("supplied-exterior", args.exterior_image.read_bytes(), "exterior"))
    buffer = io.BytesIO()
    Image.new("RGB", (256, 256), "white").save(buffer, format="PNG")
    cases.append(("blank-negative", buffer.getvalue(), "unknown"))
    report = []
    for case_id, raw, expected in cases:
        image, mime = prepare_image(raw)
        started = time.monotonic()
        result = await classify_vehicle_image(image, mime)
        report.append({"case_id": case_id, "expected": expected, **result,
                       "elapsed_s": round(time.monotonic()-started, 2), "passed": result["image_kind"] == expected})
    output = Path(".test-runs/image-routing-live.json")
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=True))
    return 0 if all(row["passed"] for row in report) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
