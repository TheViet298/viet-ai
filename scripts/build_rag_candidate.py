"""Build a separate local E5 child index; never mutate the source collection."""
from __future__ import annotations

import argparse
import json
import sys
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def validate_target(source: Path, output: Path) -> None:
    source, output = source.resolve(), output.resolve()
    if source == output or source in output.parents or output in source.parents:
        raise ValueError('Source and candidate paths must be separate')
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ValueError('Candidate target must be empty')


def build(source: Path, output: Path, audit_only: bool = False) -> dict:
    from tokenizers import Tokenizer

    from src.services.rag_index import content_hash, make_child_records
    from src.services.rag_service import get_collection, knowledge_fingerprint
    validate_target(source, output)
    collection = get_collection(str(source))
    config = collection.configuration
    function = config.get('embedding_function')
    if not function or function.name() != 'vinfast-multilingual-e5-onnx' or config.get('hnsw', {}).get('space') != 'l2':
        raise ValueError('Candidate requires the existing local E5 squared L2 collection')
    model_dir = ROOT / function.get_config()['model_dir']
    tokenizer = Tokenizer.from_file(str(model_dir / 'tokenizer.json'))
    tokenizer.no_truncation()
    tokenizer.no_padding()
    corpus = collection.get(include=['documents', 'metadatas'])
    records = [{'id': pid, 'document': doc, 'metadata': meta} for pid, doc, meta in zip(
        corpus['ids'], corpus['documents'], corpus['metadatas'], strict=True)]
    children, parents = make_child_records(records, tokenizer)
    audit = {'parent_count': len(parents), 'child_count': len(children),
             'max_child_tokens': max((len(tokenizer.encode('passage: ' + c['document']).ids) for c in children), default=0),
             'oversized_parents': sum(len(tokenizer.encode('passage: ' + r['document']).ids) > 256 for r in records)}
    if audit_only:
        return audit
    import chromadb
    from chromadb.config import Settings as ChromaSettings

    from src.services.multilingual_embeddings import MultilingualE5
    encoder = MultilingualE5(function.get_config()['model_dir'])
    output.mkdir(parents=True, exist_ok=True)
    target = chromadb.PersistentClient(path=str(output), settings=ChromaSettings(anonymized_telemetry=False)).create_collection(
        'vinfast_knowledge_base', embedding_function=encoder, configuration={'hnsw': {'space': 'l2'}})
    for start in range(0, len(children), 64):
        batch = children[start:start + 64]
        # Strict encoding bypasses legacy silent truncation.
        target.add(ids=[c['id'] for c in batch], documents=[c['document'] for c in batch],
                   metadatas=[c['metadata'] for c in batch], embeddings=encoder.encode_passages_strict([c['document'] for c in batch], tokenizer))
    mapping = output / 'parent-map.json'
    mapping.write_text(json.dumps(parents, ensure_ascii=False, sort_keys=True), encoding='utf-8')
    manifest = {**audit, 'chunking_version': 'rag-foundations-v1', 'model': function.name(), 'dimension': 384,
                'metric': 'squared L2 over normalized vectors', 'source_content_sha256': knowledge_fingerprint(str(source)),
                'children_sha256': content_hash(children), 'parent_map_sha256': sha256(mapping.read_bytes()).hexdigest(),
                'tokenizer_sha256': sha256((model_dir / 'tokenizer.json').read_bytes()).hexdigest(),
                'model_sha256': sha256((model_dir / 'onnx/model_quantized.onnx').read_bytes()).hexdigest()}
    (output / 'build-manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--audit-only', action='store_true')
    args = parser.parse_args()
    print(json.dumps(build(args.source, args.output, args.audit_only), indent=2))
