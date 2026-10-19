"""Portable audit inputs and honest output metrics, separate from factual review."""
from collections import Counter
from hashlib import sha256
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def audit_config_file() -> Path:
    value = os.getenv('AUDIT_CONFIG_FILE')
    if not value or not Path(value).is_file():
        raise ValueError('Set AUDIT_CONFIG_FILE to an existing local provider configuration')
    return Path(value).resolve()


def audit_index_dir() -> Path:
    return Path(os.getenv('AUDIT_INDEX_DIR', str(ROOT / '.test-runs/answer-gap-index'))).resolve()


def index_identity(directory: Path) -> dict:
    return {name: sha256((directory / name).read_bytes()).hexdigest()
            for name in ('chroma.sqlite3', 'build-manifest.json', 'parent-map.json') if (directory / name).is_file()}


def summarize_outputs(rows: list[dict]) -> dict:
    return {'turns': len(rows), 'answer_status_counts': dict(Counter(
                (row.get('final_diagnostics') or {}).get('answer_status', 'unclassified') for row in rows)),
            'model_parsed_events': sum(outcome.get('decision') == 'parsed'
                for row in rows for outcome in row.get('llm_outcomes', [])),
            'model_error_events': sum(outcome.get('decision') in {'timeout', 'provider_error', 'parse_error'}
                for row in rows for outcome in row.get('llm_outcomes', [])),
            'factual_certification': 'NOT_REVIEWED'}


def load_reviewed_holdout(path: Path) -> list[dict]:
    rows = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
    if any(row.get('review_status') != 'verified' or not row.get('reviewer') or not row.get('reviewed_at') for row in rows):
        raise ValueError('Holdout requires independent review before use as an acceptance oracle')
    if (len(rows) != 40 or len({row['id'] for row in rows}) != 40
            or Counter(row['language'] for row in rows) != {'vi': 20, 'en': 20}
            or Counter(row['category'] for row in rows) != {'answerable': 30, 'boundary': 10}):
        raise ValueError('Holdout requires 40 unique cases: 20 VI/20 EN, 30 answerable/10 boundary')
    if any(not row.get('evidence') for row in rows if row['category'] == 'answerable'):
        raise ValueError('Answerable holdout requires reviewed evidence')
    manifest = path.with_suffix('.manifest.json')
    if not manifest.is_file() or json.loads(manifest.read_text(encoding='utf-8')).get('sha256') != sha256(path.read_bytes()).hexdigest():
        raise ValueError('Holdout requires a frozen manifest matching the reviewed bytes')
    return rows
