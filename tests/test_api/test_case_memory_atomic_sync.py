import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.db import Base, get_db
from src.main import app
from src.models.db_models import Case, CaseBrief, User
from src.services.auth import get_optional_user, require_customer
from src.agents.nodes.triage_node import classify_request_kind

@pytest.fixture
def customer_db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'sync.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        user = User(id="sync-customer-id", username="sync_customer", password_hash="unused", role="CUSTOMER")
        db.add(user)
        db.commit()
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_customer] = lambda: user
        app.dependency_overrides[get_optional_user] = lambda: user
        yield db
    app.dependency_overrides.clear()
    engine.dispose()

def test_verification_question_classified_as_faq():
    text = "Xe này có phải đang lỗi CC01 ở P02 không?"
    assert classify_request_kind(text) == "faq"

@pytest.mark.asyncio
async def test_correction_syncs_case_vehicle_model(client, customer_db):
    session_id = "test-sync-session"
    
    # Lượt 1: Báo sự cố sạc trên VF8 tại trụ P01
    res1 = await client.post("/api/v1/customer/chat", json={
        "session_id": session_id,
        "message": "Xe VF8 của tôi không sạc được tại trụ P01 báo lỗi CC01",
    })
    assert res1.status_code == 200
    data1 = res1.json()["data"]
    case_id = data1.get("case_id")
    assert case_id is not None
    
    case1 = customer_db.get(Case, case_id)
    assert case1.vehicle_model == "VF8"
    
    # Lượt 2: Khách đính chính lại dòng xe và trụ sạc
    res2 = await client.post("/api/v1/customer/chat", json={
        "session_id": session_id,
        "message": "Sự cố xảy ra trên xe VF5 tại trụ P02, không phải VF8 P01",
    })
    assert res2.status_code == 200
    
    customer_db.expire_all()
    case2 = customer_db.get(Case, case_id)
    assert case2.vehicle_model == "VF5"
    
    brief = customer_db.query(CaseBrief).filter_by(case_id=case_id).first()
    assert brief is not None
    assert brief.captured_fields.get("vehicle_model") == "VF5"
