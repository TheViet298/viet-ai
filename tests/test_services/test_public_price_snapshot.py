from datetime import date

from src.services import rag_service


def test_verified_public_price_snapshot_filters_variant(monkeypatch):
    class VerifiedDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 10, 16)
    monkeypatch.setattr(rag_service, 'date', VerifiedDate)
    result = rag_service.RAGService().retrieve('Giá xe VF8 Plus', vehicle_model='VF8')
    assert result['status'] == 'SUCCESS'
    assert len(result['citations']) == 1
    assert 'VF8 Plus' in result['citations'][0]['relevant_snippet']
    assert 'VF8 Eco' not in result['citations'][0]['relevant_snippet']
    assert result['diagnostics']['category'] == 'verified_public_price_snapshot'


def test_expired_public_price_snapshot_is_not_used(monkeypatch):
    class ExpiredDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 10, 24)
    monkeypatch.setattr(rag_service, 'date', ExpiredDate)
    result = rag_service.RAGService().retrieve('Giá xe VF8 Plus', vehicle_model='VF8')
    assert result.get('diagnostics', {}).get('category') != 'verified_public_price_snapshot'
    assert not result['citations']


def test_purchase_price_cannot_borrow_plus_price_for_plus_awd(monkeypatch):
    class ReviewedDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 10, 16)
    monkeypatch.setattr(rag_service, 'date', ReviewedDate)
    result = rag_service.RAGService().retrieve('Giá xe VF7 Plus AWD', vehicle_model='VF7')
    assert result['citations'] == []
