"""Bounded compaction evidence independent of a generated summary."""
from hashlib import sha256


def compact_memory(state: dict) -> bool:
    messages = state.get('messages', [])
    if len(messages) <= 10 and sum(len(str(m.content).encode('utf-8')) for m in messages) <= 8000:
        return False
    old = messages[:-6]
    evidence = list(state.get('summary_evidence', []))
    for index, message in enumerate(old):
        content = str(message.content)
        message_id = message.id or sha256(f"{state.get('turn')}:{index}:{message.type}:{content}".encode()).hexdigest()
        evidence.append({'message_id': message_id, 'role': message.type,
                         'content': content if len(content) <= 2000 else content[:1000] + '\n[…]\n' + content[-1000:]})
    state['summary_evidence'] = evidence[-20:]
    state['summary_covered_turn'] = state.get('turn', 0)
    state['memory_summary'] = (state.get('memory_summary', '') + '\n' + '\n'.join(str(m.content) for m in old))[-1800:]
    state['messages'] = messages[-6:]
    return True
