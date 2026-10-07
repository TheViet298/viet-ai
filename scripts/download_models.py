import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "data" / "models" / "multilingual-e5-small"

FILES = [
    (
        "tokenizer.json",
        "https://huggingface.co/Xenova/multilingual-e5-small/resolve/main/tokenizer.json",
    ),
    (
        "onnx/model_quantized.onnx",
        "https://huggingface.co/Xenova/multilingual-e5-small/resolve/main/onnx/model_quantized.onnx",
    ),
]


def download_progress(block_num, block_size, total_size):
    downloaded = block_num * block_size
    if total_size > 0:
        percent = min(100.0, downloaded * 100.0 / total_size)
        mb_down = downloaded / (1024 * 1024)
        mb_total = total_size / (1024 * 1024)
        sys.stdout.write(f"\r  -> Progress: {percent:.1f}% ({mb_down:.1f}/{mb_total:.1f} MB)")
        sys.stdout.flush()


def ensure_models():
    print(f"[*] Checking AI embedding models in: {MODEL_DIR}")
    for rel_path, url in FILES:
        dest = MODEL_DIR / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.is_file() and dest.stat().st_size > 1000:
            print(f"  [✓] {rel_path} already exists ({dest.stat().st_size / 1024 / 1024:.1f} MB)")
            continue

        print(f"  [↓] Downloading {rel_path} from {url}...")
        try:
            # Fake a standard browser user-agent to avoid HF 403
            opener = urllib.request.build_opener()
            opener.addheaders = [("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)")]
            urllib.request.install_opener(opener)
            urllib.request.urlretrieve(url, str(dest), reporthook=download_progress)
            print(f"\n  [✓] Downloaded {rel_path} successfully!")
        except Exception as e:
            print(f"\n  [✗] Failed to download {rel_path}: {e}")
            if dest.exists():
                dest.unlink()
            raise


if __name__ == "__main__":
    ensure_models()
