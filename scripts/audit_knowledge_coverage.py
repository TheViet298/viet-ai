"""Read-only inventory of source coverage; availability is not answer correctness."""
from __future__ import annotations
import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

DOMAINS = {
    'overview': ('catalog', r'thong so|san pham|phien ban|phan khuc'),
    'range': ('catalog', r'quang duong|nedc|wltp'),
    'capacity': ('catalog', r'dung luong|kwh'),
    'colors': ('catalog', r'mau sac|mau ngoai that|colors'),
    'price': ('catalog', r'gia ban|price_from|gia niem yet'),
    'warranty': ('policy', r'bao hanh'),
    'maintenance': ('manual', r'bao duong'),
    'application': ('guide', r'ung dung|dang nhap|mat khau'),
    'charging_network': ('guide', r'tram sac|diem sac'),
}


def coverage_rows(metadata: list[dict], documents: list[str], registry: dict) -> list[dict]:
    from src.services.answer_evidence import normalized
    rows = []
    applicability = {'VF3': ['Eco', 'Plus'], 'VF5': [], 'VF6': ['Eco', 'Plus'], 'VF7': ['Eco', 'Plus', 'Plus AWD'], 'VF8': ['Eco', 'Plus'], 'VF9': ['Eco', 'Plus'], 'e34': []}
    for model, trims in applicability.items():
        for trim in ['unspecified', *trims]:
            for domain, (purpose, pattern) in DOMAINS.items():
                matches, unverified, expired = [], [], []
                for meta, text in zip(metadata, documents, strict=True):
                    body = normalized(text)
                    if not re.search(pattern, body):
                        continue
                    source_id = meta.get('source_id')
                    source = registry.get(source_id, {})
                    merged = {**source, **meta}
                    models = merged.get('applicable_models') or []
                    if isinstance(models, str):
                        models = models.split(',')
                    models = {re.sub(r'\s+', '', item).upper().removeprefix('VF') for item in models}
                    target = model.upper().removeprefix('VF')
                    mentioned = bool(re.search(r'\b(?:vf\s*)?' + re.escape(target.casefold()) + r'\b', body))
                    if models and target not in models and 'ALL' not in models:
                        continue
                    if not models and not mentioned:
                        continue
                    if trim != 'unspecified' and not re.search(r'\b' + trim.lower() + r'\b', body):
                        continue
                    if not source or not models or not source.get('verified_at'):
                        unverified.append(source_id)
                        continue
                    source_type = merged.get('source_type')
                    accepted = {'maintenance': {'official_manual', 'official_service'}, 'charging_network': {'official_guide', 'official_service'}}.get(domain, {'official_' + purpose})
                    if source_type not in accepted:
                        continue
                    until = merged.get('valid_until')
                    try:
                        stale = until is not None and date.fromisoformat(until) < date.today()
                    except (ValueError, TypeError):
                        unverified.append(source_id)
                        continue
                    if stale:
                        expired.append(source_id)
                    else:
                        matches.append(source_id)
                status = 'available' if matches else 'expired' if expired else 'unknown-applicability' if unverified else 'missing'
                rows.append({'model': model, 'trim': trim, 'domain': domain, 'source_need': purpose,
                             'status': status, 'source_ids': sorted({s for s in matches if s}),
                             'unverified_source_ids': sorted({s for s in unverified if s})})
    return rows


def audit_knowledge_coverage(index_path: str) -> dict:
    from src.services.rag_service import get_collection, get_corpus, source_registry
    if not Path(index_path, 'chroma.sqlite3').is_file():
        return {'index': index_path, 'status': 'missing', 'rows': [], 'conflicts': 'NOT_MEASURED'}
    collection = get_collection(index_path)
    corpus = get_corpus(index_path, collection.count())
    rows = coverage_rows(corpus['metadatas'], corpus['documents'], source_registry())
    return {'index': index_path, 'chunks': len(corpus['ids']), 'rows': rows,
            'conflicts': 'NOT_MEASURED: differing values require condition/applicability review',
            'available_means': 'verified source inventory only, not successful retrieval or correct answers'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--index', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    result = audit_knowledge_coverage(args.index)
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
