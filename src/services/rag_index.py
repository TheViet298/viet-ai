"""Lossless token-bounded passages and verified parent sidecar."""
from __future__ import annotations

import json
import re
from hashlib import sha256
from pathlib import Path


def content_hash(value) -> str:
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def split_passage(text: str, tokenizer, max_tokens: int = 256) -> list[str]:
    # Clone the real tokenizer to avoid padding/truncation hiding the true length.
    if hasattr(tokenizer, 'to_str') and (tokenizer.truncation or tokenizer.padding):
        from tokenizers import Tokenizer
        tokenizer = Tokenizer.from_str(tokenizer.to_str())
        tokenizer.no_truncation()
        tokenizer.no_padding()
    def fits(part):
        return len(tokenizer.encode('passage: ' + part).ids) <= max_tokens
    if not fits(''):
        raise ValueError('Token budget cannot fit passage prefix')
    parts = []
    while text:
        if fits(text):
            parts.append(text)
            break
        lo, hi = 0, len(text)
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if fits(text[:mid]):
                lo = mid
            else:
                hi = mid - 1
        if lo == 0:
            raise ValueError('Token budget cannot fit one character')
        boundaries = [m.end() for m in re.finditer(r'\n|[.!?]\s+|\s+', text[:lo]) if m.end() >= lo // 2]
        end = boundaries[-1] if boundaries else lo
        # Subword tokenization need not be monotonic at a word boundary.
        while end and not fits(text[:end]):
            end -= 1
        if not end:
            raise ValueError('Token budget cannot fit passage')
        parts.append(text[:end])
        text = text[end:]
    return parts


def make_child_records(records: list[dict], tokenizer) -> tuple[list[dict], dict]:
    children, parents = [], {}
    for record in records:
        pid = record['id']
        if pid in parents or not record['document']:
            raise ValueError('Duplicate or empty parent')
        parent = {**record, 'sha256': content_hash(record)}
        parents[pid] = parent
        for i, part in enumerate(split_passage(record['document'], tokenizer)):
            child_id = f'{pid}::child:{i}:{content_hash(part)[:12]}'
            children.append({'id': child_id, 'document': part, 'metadata': {
                **record['metadata'], 'parent_chunk_id': pid, 'parent_sha256': parent['sha256']}})
    return children, parents


def load_parent_map(index_dir: str) -> dict:
    directory = Path(index_dir)
    mapping = directory / 'parent-map.json'
    manifest_path = directory / 'build-manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8')) if manifest_path.is_file() else {}
    candidate = manifest.get('chunking_version') == 'rag-foundations-v1'
    if not mapping.is_file():
        if candidate:
            raise ValueError('Missing parent map')
        return {}  # Legacy index.
    if not candidate or manifest.get('parent_map_sha256') != sha256(mapping.read_bytes()).hexdigest():
        raise ValueError('Invalid parent mapping manifest')
    parents = json.loads(mapping.read_text(encoding='utf-8'))
    if not isinstance(parents, dict) or len(parents) != manifest.get('parent_count'):
        raise ValueError('Invalid parent count')
    for pid, parent in parents.items():
        record = {k: parent[k] for k in ('id', 'document', 'metadata')}
        if pid != parent['id'] or content_hash(record) != parent['sha256']:
            raise ValueError('Invalid parent record hash')
    return parents
