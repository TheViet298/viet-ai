"""Run the trusted local CarDD CLI in its isolated CPU environment."""

import asyncio
import subprocess
import sys
from pathlib import Path

from src.config import get_settings
from src.services.vision.contract import DamageResult, VisionEvidence

ROOT = Path(__file__).resolve().parents[3]


async def analyze_exterior_image(path: str | Path, image_id: str) -> dict:
    settings = get_settings()
    bundled = ROOT / "data/vision/runtime-env" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    interpreter = settings.cardd_python_executable or (str(bundled) if bundled.is_file() else sys.executable)

    def unavailable(reason):
        return VisionEvidence(image_id=image_id, damage=DamageResult(status="unavailable", reason=reason)).model_dump(mode="json")

    try:
        result = await asyncio.to_thread(
            subprocess.run,
            [interpreter, str(ROOT / "scripts/predict_cardd.py"), "--image", str(Path(path).resolve()), "--device", "cpu"],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
            timeout=settings.cardd_inference_timeout_s, check=False,
        )
        if result.returncode not in (0, 2):
            return unavailable("inference_failed")
        evidence = VisionEvidence.model_validate_json(result.stdout)
        evidence.image_id = image_id
        return evidence.model_dump(mode="json")
    except subprocess.TimeoutExpired:
        return unavailable("inference_timeout")
    except (OSError, ValueError):
        return unavailable("runtime_unavailable")
