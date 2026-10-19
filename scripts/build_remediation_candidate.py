"""Rebuild a separate E5 candidate from intact parents and reviewed additions."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def reviewed_records() -> list[dict]:
    from src.services.rag_service import source_registry
    from src.services.reviewed_knowledge import _approved
    from src.services.vehicle_catalog import catalog_facts
    registry = source_registry()
    schedules = json.loads((ROOT / 'fixtures/knowledge/maintenance_schedules.json').read_text(encoding='utf-8'))
    colors = json.loads((ROOT / 'data/verified/catalog_colors.json').read_text(encoding='utf-8'))['records']
    records = []
    for kind, rows in [('schedule', schedules), ('colors', colors)]:
        for row in rows:
            if not _approved(row):
                continue
            source = registry[row['source_id']]
            url = row['source_url']
            metadata = {key: source[key] for key in ('title', 'source_type')}
            metadata.update(source_id=row['source_id'], url=url,
                verified_at=source.get('approved_urls', {}).get(url) or source['verified_at'],
                applicable_models=row['model'], source_section=row['source_section'],
                content_reviewed_at=row['reviewed_at'],
                reviewed_scope_json=json.dumps({'model': row['model'], 'model_year': row.get('model_year'),
                    'variant': row.get('variant'), 'usage': None}, sort_keys=True))
            if kind == 'colors':
                metadata.update(catalog_scope='model_colors')
            records.append({'id': f"reviewed-{row['model']}-{kind}-{row['reviewed_at']}",
                            'document': row['relevant_snippet'], 'metadata': metadata})
    for fact in catalog_facts():
        evidence = fact['claim_evidence'].get('capacity', {})
        if evidence.get('reviewer') != 'Codex/root, source reading' or evidence.get('reviewed_at') != '2026-10-19':
            continue
        scope = fact['scope']
        url = evidence['source_url']
        source = registry['SRC-009']
        records.append({'id': f"reviewed-{scope['model']}-capacity-2026-10-19",
            'document': f"Thông số kỹ thuật {scope['model']}\n{scope['model']} dung lượng pin khả dụng: {evidence['value']}.\nTrang sản phẩm không xác định đời xe.",
            'metadata': {'source_id': 'SRC-009', 'source_type': 'official_catalog', 'title': source['title'],
                         'url': url, 'verified_at': source['approved_urls'][url], 'applicable_models': scope['model'],
                         'source_section': evidence['source_section'], 'content_reviewed_at': evidence['reviewed_at'],
                         'reviewed_scope_json': json.dumps({'model': scope['model'], 'variant': scope['variant'],
                             'model_year': scope['model_year'], 'usage': None}, sort_keys=True)}})
    return records


def recover_parents(corpus: dict, mapping: dict) -> list[dict]:
    from src.services.rag_index import content_hash
    records = {}
    for identity, document, metadata in zip(corpus['ids'], corpus['documents'], corpus['metadatas'], strict=True):
        parent_id = metadata.get('parent_chunk_id')
        if parent_id:
            parent = mapping.get(parent_id)
            if (not parent or metadata.get('parent_sha256') != parent['sha256']
                    or not re.fullmatch(re.escape(parent_id) + r'::child:\d+:' + content_hash(document)[:12], identity)
                    or document not in parent['document']):
                raise ValueError('Source child-parent integrity mismatch')
            record = {key: parent[key] for key in ('id', 'document', 'metadata')}
            if content_hash(record) != parent['sha256']:
                raise ValueError('Source parent integrity mismatch')
        else:
            record = {'id': identity, 'document': document, 'metadata': metadata}
        if record['id'] in records and records[record['id']] != record:
            raise ValueError('Conflicting parent identity')
        records[record['id']] = record
    return list(records.values())


def build(source: Path, output: Path) -> dict:
    from scripts.build_rag_candidate import validate_target
    from src.services.rag_index import content_hash, load_parent_map, make_child_records
    from src.services.rag_service import get_collection, knowledge_fingerprint
    from tokenizers import Tokenizer
    validate_target(source, output)
    collection = get_collection(str(source))
    function = collection.configuration.get('embedding_function')
    if (not function or function.name() != 'vinfast-multilingual-e5-onnx'
            or collection.configuration.get('hnsw', {}).get('space') != 'l2'):
        raise ValueError('Expected the existing E5 embedding configuration')
    model_dir = ROOT / function.get_config()['model_dir']
    tokenizer = Tokenizer.from_file(str(model_dir / 'tokenizer.json'))
    tokenizer.no_padding()
    tokenizer.no_truncation()
    corpus = collection.get(include=['documents', 'metadatas'])
    records = recover_parents(corpus, load_parent_map(str(source)))
    additions = reviewed_records()
    if {record['id'] for record in records} & {record['id'] for record in additions}:
        raise ValueError('Reviewed additions already exist; choose the base source index')
    children, parents = make_child_records([*records, *additions], tokenizer)
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    from src.services.multilingual_embeddings import MultilingualE5
    encoder = MultilingualE5(function.get_config()['model_dir'])
    output.mkdir(parents=True, exist_ok=True)  # validate_target required an empty target
    target = chromadb.PersistentClient(path=str(output), settings=ChromaSettings(anonymized_telemetry=False)).create_collection(
        'vinfast_knowledge_base', embedding_function=encoder, configuration={'hnsw': {'space': 'l2'}})
    for start in range(0, len(children), 64):
        batch = children[start:start + 64]
        target.add(ids=[child['id'] for child in batch], documents=[child['document'] for child in batch],
                   metadatas=[child['metadata'] for child in batch],
                   embeddings=encoder.encode_passages_strict([child['document'] for child in batch], tokenizer))
        print('Embedded', min(start + 64, len(children)), '/', len(children), flush=True)
    mapping = output / 'parent-map.json'
    mapping.write_text(json.dumps(parents, ensure_ascii=False, sort_keys=True), encoding='utf-8')
    gap_register = json.loads((ROOT / 'data/verified/knowledge_gap_register.json').read_text(encoding='utf-8'))
    manifest = {'chunking_version': 'rag-foundations-v1', 'build_kind': 'reviewed-knowledge-remediation-v1',
        'source_path': str(source.resolve()), 'source_content_sha256': knowledge_fingerprint(str(source)),
        'parent_count': len(parents), 'child_count': len(children), 'children_sha256': content_hash(children),
        'parent_map_sha256': sha256(mapping.read_bytes()).hexdigest(),
        'max_child_tokens': max(len(tokenizer.encode('passage: ' + child['document']).ids) for child in children),
        'model': function.name(), 'dimension': 384, 'metric': 'squared L2 over normalized vectors',
        'tokenizer_sha256': sha256((model_dir / 'tokenizer.json').read_bytes()).hexdigest(),
        'model_sha256': sha256((model_dir / 'onnx/model_quantized.onnx').read_bytes()).hexdigest(),
        'reviewed_additions': [{'id': record['id'], 'sha256': content_hash(record), 'metadata': record['metadata']} for record in additions],
        'unresolved_gaps': [gap['id'] for gap in gap_register['gaps'] if gap['status'] != 'verified'],
        'acceptance': 'PENDING independent holdout, provider and regression gates; active configuration unchanged'}
    (output / 'build-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    load_parent_map(str(output))
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.source, args.output), ensure_ascii=True, indent=2))
