"""Capture official source snapshots including tables; build a separate candidate KB."""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def extract_blocks(html: str) -> list[str]:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    main = soup.find("main") or soup.find("article") or soup.body or soup
    for tag in main.select("script, style, nav, footer, header"):
        tag.decompose()
    blocks = []
    heading = ""
    for tag in main.find_all(["h1", "h2", "h3", "h4", "p", "li", "table"]):
        if tag.find_parent(["table", "li"]):
            continue
        if tag.name.startswith("h"):
            heading = tag.get_text(" ", strip=True)
        if tag.name == "table":
            rows = [" | ".join(cell.get_text(" ", strip=True) for cell in row.find_all(["td", "th"])) for row in tag.find_all("tr")]
            text = "\n".join(rows)
        else:
            text = tag.get_text(" ", strip=True)
        block = heading + "\n" + text if heading and text != heading else text
        if block and block not in blocks:
            blocks.append(block)
    return blocks


def fetch_sources(output: Path, verified_at: str) -> list[dict]:
    import httpx

    from src.services.rag_service import source_registry
    date.fromisoformat(verified_at)
    registry = source_registry()
    requests = [(sid, registry[sid]["url"], "ALL") for sid in ["SRC-001", "SRC-002", "SRC-003", "SRC-004"]]
    requests.extend([("SRC-009", "https://vinfastauto.com/vn_vi/dat-coc-xe-dien-vf6", "VF6"), ("SRC-009", "https://vinfastauto.com/vn_vi/dat-coc-xe-dien-vf7", "VF7")])
    output.mkdir(parents=True, exist_ok=True)
    manifest = []
    with httpx.Client(timeout=20, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0", "Accept": "text/html"}) as client:
        for index, (sid, url, model) in enumerate(requests):
            response = client.get(url)
            if response.status_code != 200:
                print(sid, model, response.status_code, "skipped", flush=True)
                continue
            if urlparse(str(response.url)).hostname != "vinfastauto.com":
                raise ValueError("Official source redirected outside approved domain")
            name = f"{sid}-{model}-{index}"
            html_path = output / (name + ".html")
            html_path.write_text(response.text, encoding="utf-8")
            blocks = extract_blocks(response.text)
            (output / (name + ".json")).write_text(json.dumps(blocks, ensure_ascii=False, indent=2), encoding="utf-8")
            manifest.append({"source_id": sid, "url": str(response.url), "status_code": response.status_code, "verified_at": verified_at, "applicable_models": [model], "snapshot": name, "sha256": sha256(response.content).hexdigest(), "blocks": len(blocks)})
            print(sid, model, response.status_code, len(blocks), flush=True)
    if manifest:
        (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def build_candidate(snapshot_dir: Path, chroma_dir: Path) -> int:
    import chromadb

    from src.services.rag_service import source_registry
    registry = source_registry()
    records = [json.loads(line) for line in (ROOT / "data/processed/chunks.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    manifest = json.loads((snapshot_dir / "manifest.json").read_text(encoding="utf-8"))
    refreshed = {m["source_id"] for m in manifest if m["source_id"] != "SRC-009"}
    records = [r for r in records if r["source_id"] not in refreshed]
    for item in manifest:
        for index, block in enumerate(json.loads((snapshot_dir / (item["snapshot"] + ".json")).read_text(encoding="utf-8"))):
            if len(block) < 30:
                continue
            # Tables remain whole. Document text is kept intact for lexical indexing;
            # response evidence will still obey the three-chunk / 1,200 budget.
            records.append({**registry[item["source_id"]], **item, "chunk_id": item["snapshot"] + f"-{index}", "content": block})
    chroma_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(chroma_dir))
    collection = client.get_or_create_collection("vinfast_knowledge_base")
    for offset in range(0, len(records), 100):
        batch = records[offset:offset + 100]
        collection.upsert(ids=[r["chunk_id"] for r in batch], documents=[r["content"] for r in batch], metadatas=[{
            "source_id": r["source_id"], "url": r["url"], "source_type": registry[r["source_id"]]["source_type"],
            "verified_at": r["verified_at"], "applicable_models": ",".join(r.get("applicable_models", ["ALL"])),
            "title": registry[r["source_id"]]["title"],
        } for r in batch])
    (chroma_dir / "build-manifest.json").write_text(json.dumps({"count": collection.count(), "sources": manifest, "metric": "default squared L2", "embedding": "Chroma default all-MiniLM-L6-v2"}, indent=2), encoding="utf-8")
    return collection.count()


def build_multilingual_candidate(chroma_dir: Path) -> int:
    import chromadb

    from src.services.multilingual_embeddings import MultilingualE5
    records = [json.loads(line) for line in (ROOT / "data/processed/chunks.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    chroma_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(chroma_dir))
    collection = client.get_or_create_collection("vinfast_knowledge_base", embedding_function=MultilingualE5())
    for offset in range(0, len(records), 64):
        batch = records[offset:offset + 64]
        collection.upsert(ids=[r["chunk_id"] for r in batch], documents=[r["content"] for r in batch], metadatas=[{
            "source_id": r["source_id"], "url": r["url"], "verified_at": r["verified_at"],
            "applicable_models": ",".join(r["applicable_models"]), "title": r["title"],
        } for r in batch])
        print("Embedded:",min(offset + 64, len(records)), "/",len(records),flush=True)
    manifest = {"count": collection.count(), "metric": "squared L2 over normalized vectors", "embedding": "Xenova/multilingual-e5-small", "revision": "761b726", "artifact": "onnx/model_quantized.onnx", "source_chunks_sha256": sha256((ROOT / "data/processed/chunks.jsonl").read_bytes()).hexdigest(), "source_refresh": "not refreshed: direct HTTP 403"}
    (chroma_dir / "build-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return collection.count()


def source_sections(text: str) -> list[str]:
    chunks = []
    buffer = []
    heading = ""
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        is_heading = bool(re.match(r"^\d+(?:\.\d+)?\.\s", line))
        in_instruction = any(re.match(r"^Bước\s+\d+", item) for item in buffer)
        if buffer and (is_heading or (len("\n".join(buffer)) + len(line) > 600 and not in_instruction and not line.startswith("Bước "))):
            chunks.append("\n".join(buffer))
            buffer = [heading] if heading and not is_heading else []
        if is_heading:
            heading = line
        buffer.append(line)
    if buffer:
        chunks.append("\n".join(buffer))
    return chunks


def rewrite_source_candidate(previous: Path, output: Path) -> int:
    import chromadb

    from src.services.multilingual_embeddings import MultilingualE5
    from src.services.rag_service import get_collection, source_registry
    registry = source_registry()
    prior = get_collection(str(previous)).get(include=["documents", "metadatas", "embeddings"])
    client = chromadb.PersistentClient(path=str(output))
    collection = client.get_or_create_collection("vinfast_knowledge_base", embedding_function=MultilingualE5())
    indices = [i for i, meta in enumerate(prior["metadatas"]) if meta["source_id"] in ["SRC-007", "SRC-008", "SRC-009"]]
    for start in range(0, len(indices), 100):
        batch = indices[start:start + 100]
        collection.upsert(ids=[prior["ids"][i] for i in batch], documents=[prior["documents"][i] for i in batch], metadatas=[prior["metadatas"][i] for i in batch], embeddings=[prior["embeddings"][i] for i in batch])
    for sid in ["SRC-001", "SRC-002", "SRC-003", "SRC-004", "SRC-005", "SRC-006"]:
        blocks = source_sections((ROOT / f"data/raw/{sid}.txt").read_text(encoding="utf-8"))
        if sid == "SRC-002":
            evidence = json.loads((ROOT / "docs/data-evidence/2026-10-03-source-002-table.json").read_text(encoding="utf-8"))
            blocks = evidence["content"] + blocks
        metadata = {k: v for k, v in registry[sid].items() if k != "approved_urls"}
        collection.upsert(ids=[f"{sid}-sections-{i}" for i in range(len(blocks))], documents=blocks, metadatas=[{**metadata, "source_id": sid, "applicable_models": "ALL"} for _ in blocks])
        print("Rebuilt source:",sid,len(blocks),flush=True)
    (output / "build-manifest.json").write_text(json.dumps({"count":collection.count(), "embedding":"Xenova/multilingual-e5-small@761b726", "metric":"squared L2 normalized vectors", "source_sections":"complete lines; original raw snapshots retained", "supplement":"docs/data-evidence/2026-10-03-source-002-table.json", "direct_refresh":"HTTP 403; no new HTTP 200 claimed"},indent=2),encoding="utf-8")
    return collection.count()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshots", type=Path, default=ROOT / "data/raw/quality-v2")
    parser.add_argument("--verified-at")
    parser.add_argument("--build", type=Path)
    parser.add_argument("--multilingual", type=Path)
    parser.add_argument("--rewrite-source-sections", type=Path)
    parser.add_argument("--from-candidate", type=Path)
    args = parser.parse_args()
    if args.verified_at:
        fetch_sources(args.snapshots, args.verified_at)
    if args.build:
        print("Candidate chunks:", build_candidate(args.snapshots, args.build))
    if args.multilingual:
        print("Multilingual candidate:", build_multilingual_candidate(args.multilingual))
    if args.rewrite_source_sections:
        if not args.from_candidate:
            parser.error("--from-candidate is required")
        print("Source-preserving candidate:",rewrite_source_candidate(args.from_candidate,args.rewrite_source_sections))
