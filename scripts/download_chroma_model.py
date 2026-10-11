import os
import sys
import tarfile
import urllib.request
from pathlib import Path

MODEL_NAME = "all-MiniLM-L6-v2"
DEST_DIR = Path.home() / ".cache" / "chroma" / "onnx_models" / MODEL_NAME
ARCHIVE_PATH = DEST_DIR / "onnx.tar.gz"
URL = "https://chroma-onnx-models.s3.amazonaws.com/all-MiniLM-L6-v2/onnx.tar.gz"
EXPECTED_SHA256 = "913d7300ceae3b2dbc2c50d1de4baacab4be7b9380491c27fab7418616a16ec3"


def download_progress(block_num, block_size, total_size):
    downloaded = block_num * block_size
    if total_size > 0:
        percent = min(100.0, downloaded * 100.0 / total_size)
        mb_down = downloaded / (1024 * 1024)
        mb_total = total_size / (1024 * 1024)
        sys.stdout.write(f"\r  -> Downloading {MODEL_NAME}: {percent:.1f}% ({mb_down:.1f}/{mb_total:.1f} MB)")
        sys.stdout.flush()


def main():
    print(f"[*] Ensuring Chroma ONNX model at: {DEST_DIR}")
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    
    extracted_dir = DEST_DIR / "onnx"
    if (extracted_dir / "model.onnx").is_file():
        print("  [✓] Model ONNX already extracted and ready to use!")
        return

    # Delete partial/corrupted archive if present
    if ARCHIVE_PATH.exists():
        ARCHIVE_PATH.unlink()

    print(f"  [↓] Downloading from {URL} (timeout=120s)...")
    opener = urllib.request.build_opener()
    opener.addheaders = [("User-Agent", "Mozilla/5.0")]
    urllib.request.install_opener(opener)
    urllib.request.urlretrieve(URL, str(ARCHIVE_PATH), reporthook=download_progress)
    print("\n  [✓] Download completed!")

    print("  [*] Extracting tar.gz archive...")
    with tarfile.open(str(ARCHIVE_PATH), "r:gz") as tar:
        tar.extractall(path=str(DEST_DIR))
    print("  [✓] Extraction finished! Model is ready.")


if __name__ == "__main__":
    main()
