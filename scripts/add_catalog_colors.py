"""Copy a verified child index and add model-level catalog color evidence."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def build(source: Path, output: Path) -> dict:
    from tokenizers import Tokenizer
    from scripts.build_rag_candidate import validate_target
    from scripts.process_chunks import process_cars_jsonl
    from src.services.rag_index import content_hash, load_parent_map, make_child_records
    from src.services.rag_service import get_collection

    validate_target(source, output)
    parents = load_parent_map(str(source))
    if not parents:
        raise ValueError('A verified child index with parent mapping is required')
    collection = get_collection(str(source))
    encoder = collection.configuration['embedding_function']
    tokenizer = Tokenizer.from_file(str(ROOT / encoder.get_config()['model_dir'] / 'tokenizer.json'))
    tokenizer.no_truncation()
    tokenizer.no_padding()
    chunks = [c for c in process_cars_jsonl() if c.get('catalog_scope') == 'model_colors']
    if not chunks:
        raise ValueError('No catalog color evidence found')
    records = [{'id': c['chunk_id'], 'document': c['content'], 'metadata': {
        **{k: c[k] for k in ('source_id', 'title', 'url', 'verified_at', 'catalog_scope')},
        'applicable_models': ','.join(c['applicable_models']),
    }} for c in chunks]
    if any(r['id'] in parents for r in records):
        raise ValueError('Color evidence already exists; rebuild from the original index')
    children, additions = make_child_records(records, tokenizer)
    embeddings = encoder.encode_passages_strict([c['document'] for c in children], tokenizer)
    # Stop the serving backend before copying to keep SQLite and sidecars consistent.
    shutil.copytree(source, output)
    target = get_collection(str(output))
    target.add(ids=[c['id'] for c in children], documents=[c['document'] for c in children],
               metadatas=[c['metadata'] for c in children], embeddings=embeddings)
    parents.update(additions)
    mapping = output / 'parent-map.json'
    mapping.write_text(json.dumps(parents, ensure_ascii=False, sort_keys=True), encoding='utf-8')
    manifest_path = output / 'build-manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    corpus = target.get(include=['documents', 'metadatas'])
    all_children = [{'id': i, 'document': d, 'metadata': m} for i, d, m in zip(
        corpus['ids'], corpus['documents'], corpus['metadatas'], strict=True)]
    manifest.update(parent_count=len(parents), child_count=target.count(),
                    parent_map_sha256=sha256(mapping.read_bytes()).hexdigest(),
                    children_sha256=content_hash(all_children), catalog_color_parent_ids=list(additions))
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    load_parent_map(str(output))
    return {'output': str(output), 'added_parents': list(additions), 'added_children': len(children)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.source, args.output), ensure_ascii=False))
