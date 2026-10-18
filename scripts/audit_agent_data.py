"""Read-only data audit helpers; no ingestion, deletion or label rewriting."""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def normalize(text):
    # Accents distinguish cháy/fire from chạy/driving; never fold them here.
    return ' '.join(unicodedata.normalize('NFKC', str(text)).casefold().split()).strip(' .!?')


def duplicate_documents(rows):
    groups = defaultdict(list)
    for row in rows:
        text = normalize(row.get('text', ''))
        if text:
            groups[hashlib.sha256(text.encode()).hexdigest()].append(row['id'])
    return [{'ids':ids, 'excess':len(ids)-1} for ids in groups.values() if len(ids) > 1]


def split_collisions(datasets):
    groups = defaultdict(list)
    fields = ['expected_intent', 'expected_priority', 'expected_routing', 'expected_response_type', 'expected_staff_review']
    for name, cases in datasets.items():
        for row in cases:
            turns = row.get('turns') or [row]
            history = []
            for index, turn in enumerate(turns):
                text = turn.get('input') or turn.get('query')
                if not text:
                    continue
                labels = dict(turn)
                aliases = {'needs_staff_review':'staff_review'}
                for key, value in turn.get('expected', {}).items():
                    labels['expected_' + aliases.get(key, key)] = value
                labels['id'] = row.get('id') if not row.get('turns') else f"{row.get('id')}#turn-{index+1}"
                history.append(normalize(text))
                # A follow-up has different semantics from an identical fresh question.
                groups[' [TURN] '.join(history)].append((name, labels))
    result = []
    for text, group in groups.items():
        if len(group) < 2:
            continue
        conflicts = [key for key in fields if len({normalize(row[key]) for _,row in group if key in row}) > 1]
        result.append({'input':text, 'datasets':sorted({name for name,_ in group}),
                       'ids':[row.get('id') for _,row in group], 'conflicting_fields':conflicts})
    return result


def summarize_records(rows, registry):
    counts = Counter(row.get('source_id', 'MISSING') for row in rows)
    return {'count':len(rows), 'source_counts':dict(counts),
            'empty_text':sum(not str(row.get('text', '')).strip() for row in rows),
            'raw_missing_source_type':sum(not row.get('source_type') for row in rows),
            'effective_source_types':dict(Counter((row.get('source_type') or registry.get(row.get('source_id'), {}).get('source_type') or 'MISSING') for row in rows)),
            'unregistered_sources':sorted(key for key in counts if key not in registry),
            'exact_normalized_duplicates':duplicate_documents(rows)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    from src.config import get_settings
    from src.services.rag_service import get_collection, source_registry, knowledge_fingerprint
    from src.services.vehicle_catalog import select_vehicle_cards
    from src.services.knowledge_questions import MODEL_CATALOG
    settings = get_settings()
    registry = source_registry()
    collection = get_collection(settings.chroma_persist_dir)
    corpus = collection.get(include=['documents', 'metadatas'])
    rows = [{'id':key, 'text':text, **(meta or {})} for key,text,meta in zip(
        corpus['ids'], corpus['documents'], corpus['metadatas'], strict=True)]
    inventory = summarize_records(rows, registry)
    inventory['index'] = settings.chroma_persist_dir
    inventory['fingerprint'] = knowledge_fingerprint(settings.chroma_persist_dir)
    inventory['metadata_keys'] = dict(Counter(key for row in rows for key in row if key not in {'text','id'}))
    inventory['raw_model_scopes'] = dict(Counter(str(row.get('applicable_models')) for row in rows))
    inventory['verified_dates'] = dict(Counter(str(row.get('verified_at')) for row in rows))
    inventory['source_registry'] = registry
    inventory['bytes_utf8'] = sum(len(row['text'].encode()) for row in rows)
    inventory['code_instruction_candidates'] = [{'id':row['id'], 'source_id':row.get('source_id'),
        'terms':re.findall(r'ignore previous|system prompt|api[_ -]?key|<script|javascript:', row['text'], re.I)}
        for row in rows if re.search(r'ignore previous|system prompt|api[_ -]?key|<script|javascript:', row['text'], re.I)]
    inventory['boilerplate_candidates'] = [{'id':row['id'],'source_id':row.get('source_id')}
        for row in rows if re.search(r'cookie|chính sách bảo mật|đăng nhập|đăng ký nhận|tất cả quyền', row['text'], re.I)]
    (args.output_dir/'index-inventory.json').write_text(json.dumps(inventory, ensure_ascii=False, indent=2), encoding='utf-8')
    # Full corpus remains scratch, useful for evidence review, never a published DB dump.
    (args.output_dir/'corpus.jsonl').write_text('\n'.join(json.dumps(row, ensure_ascii=False) for row in rows)+'\n', encoding='utf-8')
    datasets, summaries = {}, {}
    for path in sorted((ROOT/'eval/datasets').glob('*.jsonl')):
        cases = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
        datasets[path.name] = cases
        summaries[path.name] = {'count':len(cases), 'duplicate_ids':[key for key,count in Counter(row.get('id') for row in cases).items() if count>1],
            'labels':dict(Counter(row.get('label_status', row.get('status', 'UNSPECIFIED')) for row in cases)),
            'splits':dict(Counter(row.get('split', 'UNSPECIFIED') for row in cases)),
            'unregistered_expected_sources': sorted({row['expected_source_id'] for row in cases if row.get('expected_source_id') and row['expected_source_id'] not in registry})}
    summaries['normalized_question_collisions'] = split_collisions(datasets)
    (args.output_dir/'evaluation-data.json').write_text(json.dumps(summaries, ensure_ascii=False, indent=2), encoding='utf-8')
    products = {model: [card.model_dump() for card in select_vehicle_cards('Tư vấn '+model)] for model in ['VF3','VF5','VF6','VF7','VF8','VF9','e34']}
    (args.output_dir/'product-data-stores.json').write_text(json.dumps({'cards':products,'comparison_catalog':MODEL_CATALOG,
        'price_fixture':json.loads((ROOT/'fixtures/verified_public_prices.json').read_text(encoding='utf-8')),
        'data_verified_prices':json.loads((ROOT/'data/verified/public_prices.json').read_text(encoding='utf-8'))}, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'chunks':inventory['count'], 'sources':inventory['source_counts'],
        'duplicate_groups':len(inventory['exact_normalized_duplicates']), 'duplicate_excess':sum(g['excess'] for g in inventory['exact_normalized_duplicates']),
        'question_collision_groups':len(summaries['normalized_question_collisions'])}))


if __name__ == '__main__':
    main()
