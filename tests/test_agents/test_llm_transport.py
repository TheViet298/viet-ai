from src.services import llm


def test_transport_deadline_does_not_send_invalid_short_provider_deadline(monkeypatch):
    created = []
    monkeypatch.setattr(llm, 'ChatGoogleGenerativeAI', lambda **kwargs: created.append(kwargs) or object())
    monkeypatch.setattr(llm, 'ChatOpenAI', lambda **kwargs: created.append(kwargs) or object())
    llm._client.cache_clear()
    first = llm.get_llm()
    assert llm.get_llm() is first
    assert len(created) == 1
    assert created[0]['timeout'] >= 10
    assert created[0]['max_retries'] == 0
    llm._client.cache_clear()
