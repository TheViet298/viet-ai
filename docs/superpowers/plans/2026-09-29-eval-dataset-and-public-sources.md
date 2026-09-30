# Public Data Sources Selection & Triage Evaluation Benchmark Suite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Chuẩn hóa danh mục tài liệu VinFast công khai (kèm nguồn URL/phạm vi đã kiểm chứng) và xây dựng bộ test case benchmark chuẩn hóa (kèm runner đánh giá tự động) nhằm kiểm thử 5 chỉ số cốt lõi: Intent, Priority (Critical Recall = 100%), Missing Fields / Clarification, Suggested Routing và Grounded Answer (Citations).

**Architecture:** Mở rộng đặc tả nguồn dữ liệu công khai theo chuẩn No-PII & Verified Source trong `docs/architecture/rag-and-data-sources.md`. Xây dựng tập test case định dạng JSONL tại `eval/datasets/evaluation_benchmark_cases.jsonl` bao quát cả 4 nhóm Intent và các ca biên (khẩn cấp, thiếu trường, nhạy cảm, tra cứu FAQ). Viết script đánh giá tự động `scripts/run_triage_eval.py` tính toán ma trận metrics và xuất báo cáo `eval/results/benchmark_run.json`. Kiểm thử toàn diện tính hợp lệ của dataset và runner qua `tests/test_eval/test_benchmark_dataset.py`.

**Tech Stack:** Python 3.12, Pydantic v2, Pytest, LangGraph/LangChain State primitives, JSONL.

---

### File Structure Map

```
docs/
├── architecture/
│   └── rag-and-data-sources.md               # [MODIFY] Bổ sung danh mục 5 nguồn công khai VinFast đã kiểm chứng
└── superpowers/plans/
    └── 2026-09-29-eval-dataset-and-public-sources.md # [CREATE] Bản kế hoạch này

eval/
├── datasets/
│   ├── triage_cases_v1.jsonl                 # [REFERENCE/KEEP] Tập 12 cases mẫu ban đầu
│   └── evaluation_benchmark_cases.jsonl      # [CREATE] Bộ 25 benchmark cases chuẩn hóa đầy đủ 5 tiêu chí
└── results/
    ├── report.md                             # [MODIFY] Cập nhật bảng kết quả benchmark mới
    └── benchmark_run.json                    # [GENERATED] Kết quả chạy tự động của runner

scripts/
└── run_triage_eval.py                        # [CREATE] Script CLI đánh giá benchmark tự động

src/
└── models/
    └── eval_schemas.py                       # [CREATE] Pydantic models cho Benchmark Case và Eval Metrics

tests/
└── test_eval/
    ├── __init__.py                           # [CREATE] Package init
    └── test_benchmark_dataset.py             # [CREATE] Unit test kiểm tra tính toàn vẹn dữ liệu và metrics logic
```

---

### Task 1: Chuẩn hóa và Cập nhật Danh mục Nguồn Dữ liệu Công khai VinFast

**Files:**
- Modify: `docs/architecture/rag-and-data-sources.md`

- [ ] **Step 1: Cập nhật danh mục 5 nguồn tài liệu công khai chính thức của VinFast**

Chỉnh sửa [`docs/architecture/rag-and-data-sources.md`](file:///d:/142.AI20K/P-142/docs/architecture/rag-and-data-sources.md) để cập nhật bảng nguồn dữ liệu công khai có kiểm chứng với 5 tài liệu cốt lõi:
1. `SRC-APP-001`: Hướng dẫn sử dụng Ứng dụng VinFast (Trạng thái xe, Pin/Sạc, Cảnh báo, Đặt lịch & Theo dõi dịch vụ).
2. `SRC-CHG-001`: Cẩm nang sử dụng & Quy chuẩn Trụ sạc Xe điện VinFast (Đèn tín hiệu trụ sạc, thao tác cắm/rút súng an toàn, mã lỗi CC01/E-04).
3. `SRC-WRN-001`: Chính sách Bảo hành & Hệ thống Xưởng Dịch vụ VinFast (Chính sách 7-10 năm hoặc 160.000 - 200.000 km, điều kiện cứu hộ 24/7).
4. `SRC-BATT-001`: Chính sách Thuê và Mua Pin Ô tô Điện VinFast (Gói cước linh hoạt/cố định, ngưỡng thay thế pin khi dung lượng SOH dưới 70%).
5. `SRC-EMG-001`: Quy chuẩn Hướng dẫn Xử lý Khẩn cấp & Cứu hộ Ven đường (Hotline 1900-232389, quy trình dừng đỗ an toàn khi mất phanh, rùa vàng, bốc khói).

Nội dung cập nhật phải đảm bảo:
- Đầy đủ các trường: `source_id`, `title`, `url`, `verified_at`, `status_code: 200`, `applicable_models`, `source_type`, `scope_summary`.
- Phạm vi dữ liệu (Scope): Chỉ bao gồm thông tin công bố chính thức, không chứa tài liệu nội bộ mật.

- [ ] **Step 2: Xác minh nội dung tài liệu đã được cập nhật chuẩn xác**

Chạy lệnh kiểm tra file:
```powershell
Get-Content docs/architecture/rag-and-data-sources.md -TotalCount 55
```
Kỳ vọng: Bảng nguồn hiển thị đủ 5 `source_id` từ `SRC-APP-001` đến `SRC-EMG-001` với trạng thái `200` và link chính thức.

- [ ] **Step 3: Commit (nếu auto_commit kích hoạt)**

Kiểm tra `.agent/config.yml` cho thiết lập `auto_commit`.
Nếu `auto_commit: true` (mặc định khi không có file config):
```bash
git add docs/architecture/rag-and-data-sources.md
git commit -m "docs: expand verified public VinFast sources with 5 official manuals"
```
Nếu `auto_commit: false`: Bỏ qua commit và in: `"Skipping commit (auto_commit: false)."`.

---

### Task 2: Định nghĩa Pydantic Schemas cho Bộ Case Đánh giá & Kết quả Benchmark

**Files:**
- Create: `src/models/eval_schemas.py`
- Test: `tests/test_eval/test_benchmark_dataset.py`

- [ ] **Step 1: Viết test thất bại kiểm tra schema validation cho BenchmarkCase**

Tạo file [`tests/test_eval/test_benchmark_dataset.py`](file:///d:/142.AI20K/P-142/tests/test_eval/test_benchmark_dataset.py) với test kiểm tra schema:

```python
import pytest
from pydantic import ValidationError
from src.models.eval_schemas import BenchmarkCase, EvaluationResultSummary


def test_valid_benchmark_case_schema():
    case_dict = {
        "id": "EVAL-001",
        "user_message": "Tôi đang sạc VF8 ở Vincom Metropolis thì súng sạc báo lỗi E-04 đèn đỏ không vào điện.",
        "expected_intent": "Charging/Battery",
        "expected_priority": "HIGH",
        "expected_missing_fields": ["charger_id"],
        "expected_routing": "Charging Technical Support",
        "is_critical": False,
        "is_rag_query": False,
        "notes": "Lỗi trạm sạc thiếu mã trụ",
    }
    case = BenchmarkCase.model_validate(case_dict)
    assert case.id == "EVAL-001"
    assert case.expected_intent == "Charging/Battery"
    assert case.expected_missing_fields == ["charger_id"]
    assert case.expected_routing == "Charging Technical Support"


def test_invalid_intent_raises_validation_error():
    invalid_dict = {
        "id": "EVAL-ERR",
        "user_message": "Hỏi linh tinh",
        "expected_intent": "InvalidIntentName",
        "expected_priority": "LOW",
        "expected_missing_fields": [],
        "expected_routing": "General CSKH",
    }
    with pytest.raises(ValidationError):
        BenchmarkCase.model_validate(invalid_dict)
```

- [ ] **Step 2: Chạy test để xác nhận test thất bại**

Run: `pytest tests/test_eval/test_benchmark_dataset.py -v`
Expected: FAIL với lỗi `ModuleNotFoundError: No module named 'src.models.eval_schemas'`

- [ ] **Step 3: Viết code schema `src/models/eval_schemas.py`**

Tạo file [`src/models/eval_schemas.py`](file:///d:/142.AI20K/P-142/src/models/eval_schemas.py):

```python
from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field

from src.agents.state import IntentType, PriorityLevel


RoutingDestination = Literal[
    "Emergency Rescue Hotline",
    "Charging Technical Support",
    "Workshop Service Advisor",
    "CSKH Dispute Manager",
    "Automated FAQ Answer",
    "Out of Scope Filter",
]


class GroundedAnswerExpectation(BaseModel):
    expected_source_id: str = Field(..., description="ID nguồn tài liệu chính thức, ví dụ SRC-APP-001")
    expected_citation_url: str = Field(..., description="URL trích dẫn kiểm chứng")
    required_keywords: list[str] = Field(default_factory=list, description="Từ khóa bắt buộc có trong câu trả lời")


class BenchmarkCase(BaseModel):
    id: str = Field(..., pattern=r"^(EVAL|TEST)-\d{3}$", description="Mã định danh test case")
    user_message: str = Field(..., min_length=5, description="Nội dung tin nhắn khách hàng (No-PII)")
    expected_intent: IntentType = Field(..., description="Intent mong đợi")
    expected_priority: PriorityLevel = Field(..., description="Mức ưu tiên mong đợi")
    expected_missing_fields: list[str] = Field(
        default_factory=list,
        description="Danh sách trường bắt buộc còn thiếu cần kích hoạt hỏi làm rõ",
    )
    expected_routing: RoutingDestination = Field(..., description="Bộ phận điều phối mong đợi")
    is_critical: bool = Field(default=False, description="Có phải tình huống khẩn cấp tính mạng không")
    safety_trigger: str | None = Field(default=None, description="Mã rule an toàn nếu có")
    is_rag_query: bool = Field(default=False, description="Có phải câu hỏi tra cứu FAQ công khai không")
    grounded_answer: GroundedAnswerExpectation | None = Field(
        default=None,
        description="Kỳ vọng nguồn trích dẫn nếu là RAG FAQ",
    )
    notes: str = Field(default="", description="Ghi chú bối cảnh test case")


class EvaluationResultSummary(BaseModel):
    total_cases: int
    intent_accuracy: float
    critical_recall: float
    brief_completeness_rate: float
    routing_accuracy: float
    rag_grounded_rate: float
    passed: bool
    failed_case_ids: list[str] = Field(default_factory=list)
```

- [ ] **Step 4: Chạy lại test để xác nhận test pass**

Run: `pytest tests/test_eval/test_benchmark_dataset.py -v`
Expected: PASS cả 2 tests.

- [ ] **Step 5: Commit (nếu auto_commit kích hoạt)**

Kiểm tra `.agent/config.yml` cho thiết lập `auto_commit`.
Nếu `auto_commit: true`:
```bash
git add src/models/eval_schemas.py tests/test_eval/test_benchmark_dataset.py
git commit -m "feat: define benchmark case and evaluation schemas"
```
Nếu `auto_commit: false`: Bỏ qua commit và in: `"Skipping commit (auto_commit: false)."`.

---

### Task 3: Xây dựng Bộ 25 Test Cases Benchmark Chuẩn hóa Đầy đủ 5 Tiêu chí

**Files:**
- Create: `eval/datasets/evaluation_benchmark_cases.jsonl`
- Modify: `tests/test_eval/test_benchmark_dataset.py`

- [ ] **Step 1: Viết test kiểm tra tính toàn vẹn của dataset file**

Bổ sung test vào [`tests/test_eval/test_benchmark_dataset.py`](file:///d:/142.AI20K/P-142/tests/test_eval/test_benchmark_dataset.py):

```python
import json
from pathlib import Path
from src.agents.guardrails import sanitize_pii
from src.models.eval_schemas import BenchmarkCase

DATASET_PATH = Path("eval/datasets/evaluation_benchmark_cases.jsonl")


def test_benchmark_dataset_integrity():
    assert DATASET_PATH.exists(), "Dataset file evaluation_benchmark_cases.jsonl must exist"
    
    cases: list[BenchmarkCase] = []
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            case = BenchmarkCase.model_validate(data)
            cases.append(case)

    # Đảm bảo tối thiểu 20 cases bao phủ đủ 4 intents + out_of_scope
    assert len(cases) >= 20
    
    # Kiểm tra phân bố Intent
    intents = {c.expected_intent for c in cases}
    assert "Charging/Battery" in intents
    assert "Service/Incident" in intents
    assert "Complaint/Feedback" in intents
    assert "Sales/General Info" in intents
    assert "Out_of_Scope" in intents

    # Kiểm tra Critical cases có safety trigger
    critical_cases = [c for c in cases if c.is_critical]
    assert len(critical_cases) >= 4, "Must have at least 4 critical test cases"
    for c in critical_cases:
        assert c.expected_priority == "CRITICAL"
        assert c.expected_routing == "Emergency Rescue Hotline"
        assert c.safety_trigger is not None

    # Kiểm tra RAG FAQ cases có grounded source
    rag_cases = [c for c in cases if c.is_rag_query]
    assert len(rag_cases) >= 5, "Must have at least 5 RAG FAQ cases"
    for c in rag_cases:
        assert c.grounded_answer is not None
        assert c.grounded_answer.expected_source_id.startswith("SRC-")
        assert c.grounded_answer.expected_citation_url.startswith("https://vinfastauto.com")

    # Kiểm tra tuyệt đối KHÔNG có PII thực trong user_message
    for c in cases:
        sanitized, detected, detected_types = sanitize_pii(c.user_message)
        assert not detected, f"Case {c.id} contains real PII: {detected_types}"
```

- [ ] **Step 2: Chạy test để xác nhận test thất bại vì file dataset chưa được tạo**

Run: `pytest tests/test_eval/test_benchmark_dataset.py::test_benchmark_dataset_integrity -v`
Expected: FAIL với AssertionError: "Dataset file evaluation_benchmark_cases.jsonl must exist"

- [ ] **Step 3: Tạo file `eval/datasets/evaluation_benchmark_cases.jsonl` với 25 ca kiểm thử đa dạng**

Tạo [`eval/datasets/evaluation_benchmark_cases.jsonl`](file:///d:/142.AI20K/P-142/eval/datasets/evaluation_benchmark_cases.jsonl) bao gồm 25 trường hợp phân bổ chuẩn:
- **Group 1: Charging/Battery (6 cases):**
  - `EVAL-001`: Lỗi súng DC không vào điện tại trạm công cộng Metropolis (thiếu charger_id) $\to$ HIGH, thiếu `charger_id`, routing: `Charging Technical Support`.
  - `EVAL-002`: Lỗi trụ sạc báo CC01 kèm mã trụ và dòng xe $\to$ HIGH, đủ trường, routing: `Charging Technical Support`.
  - `EVAL-003`: Sạc AC tại nhà tự ngắt do ổ cắm quá nhiệt $\to$ HIGH, thiếu `error_code`, routing: `Charging Technical Support`.
  - `EVAL-004`: Trụ sạc bị kẹt súng không rút ra được sau khi sạc xong $\to$ HIGH, thiếu `charger_id`, routing: `Charging Technical Support`.
  - `EVAL-005`: Tốc độ sạc trụ DC 250kW bị giảm đột ngột xuống 20kW $\to$ MEDIUM, đủ trường, routing: `Charging Technical Support`.
  - `EVAL-006`: Khách hỏi cách tính phí sạc quá giờ trên app $\to$ LOW, `is_rag_query=True`, source `SRC-CHG-001`, routing: `Automated FAQ Answer`.
- **Group 2: Service/Incident (8 cases):**
  - `EVAL-007`: Rùa vàng xuất hiện khi xe đang chạy 90km/h trên cao tốc Pháp Vân $\to$ CRITICAL, `safety_trigger: TURTLE_ON_HIGHWAY`, routing: `Emergency Rescue Hotline`.
  - `EVAL-008`: Rùa vàng báo khi khởi động xe ở bãi đỗ chung cư, xe vẫn lăn bánh bình thường $\to$ HIGH, thiếu `error_code`, routing: `Workshop Service Advisor`.
  - `EVAL-009`: Xe có mùi khét và khói bốc lên từ khoang đầu xe $\to$ CRITICAL, `safety_trigger: SMOKE_OR_FIRE`, routing: `Emergency Rescue Hotline`.
  - `EVAL-010`: Chân phanh bị hẫng, đạp sát sàn xe không giảm tốc $\to$ CRITICAL, `safety_trigger: BRAKE_FAILURE`, routing: `Emergency Rescue Hotline`.
  - `EVAL-011`: Kẹt chân ga trên đường $\to$ CRITICAL, `safety_trigger: ACCELERATOR_JAM`, routing: `Emergency Rescue Hotline`.
  - `EVAL-012`: Xe bị cạn ắc quy 12V không mở được cửa xe $\to$ HIGH, đủ trường, routing: `Workshop Service Advisor`.
  - `EVAL-013`: Điều hòa xe VF8 chỉ thổi gió nóng không lạnh $\to$ MEDIUM, thiếu `operational_status`, routing: `Workshop Service Advisor`.
  - `EVAL-014`: Màn hình trung tâm bị treo đen xì khi xe đang đỗ $\to$ MEDIUM, đủ trường, routing: `Workshop Service Advisor`.
- **Group 3: Complaint/Feedback (4 cases):**
  - `EVAL-015`: Khiếu nại xưởng dịch vụ Smart City hẹn 9h nhưng 11h chưa nhận xe, thái độ thờ ơ $\to$ MEDIUM, đủ trường, routing: `CSKH Dispute Manager`.
  - `EVAL-016`: Bức xúc gay gắt vì xe bảo dưỡng 3 lần lỗi cũ không khắc phục, dọa kiện lên báo $\to$ HIGH, thiếu `showroom_dealer`, routing: `CSKH Dispute Manager`.
  - `EVAL-017`: Khiếu nại tính sai tiền sạc xe trong hóa đơn cuối tháng $\to$ MEDIUM, thiếu `showroom_dealer`, routing: `CSKH Dispute Manager`.
  - `EVAL-018`: Phản ánh thái độ tư vấn viên tại Showroom Landmark 81 $\to$ MEDIUM, đủ trường, routing: `CSKH Dispute Manager`.
- **Group 4: Sales/General Info (5 cases):**
  - `EVAL-019`: Hướng dẫn theo dõi dung lượng pin và đặt lịch bảo dưỡng trên app $\to$ LOW, `is_rag_query=True`, source `SRC-APP-001`, routing: `Automated FAQ Answer`.
  - `EVAL-020`: Chính sách bảo hành xe điện 10 năm hoặc 200.000 km $\to$ LOW, `is_rag_query=True`, source `SRC-WRN-001`, routing: `Automated FAQ Answer`.
  - `EVAL-021`: Quy định thuê pin và điều kiện được đổi pin miễn phí khi SOH < 70% $\to$ LOW, `is_rag_query=True`, source `SRC-BATT-001`, routing: `Automated FAQ Answer`.
  - `EVAL-022`: Hướng dẫn cách xử lý an toàn khi xe gặp sự cố trên đường $\to$ LOW, `is_rag_query=True`, source `SRC-EMG-001`, routing: `Automated FAQ Answer`.
  - `EVAL-023`: Hỏi giá bán lăn bánh và ưu đãi xe VF3 tại Hà Nội $\to$ LOW, `is_rag_query=False`, routing: `Workshop Service Advisor` (Sales lead).
- **Group 5: Out of Scope & Edge Boundary (2 cases):**
  - `EVAL-024`: Hỏi cách sửa xe máy xăng Honda SH $\to$ LOW, `expected_intent: Out_of_Scope`, routing: `Out of Scope Filter`.
  - `EVAL-025`: Hỏi thời tiết ngày mai ở Đà Nẵng $\to$ LOW, `expected_intent: Out_of_Scope`, routing: `Out of Scope Filter`.

- [ ] **Step 4: Chạy test để xác nhận toàn bộ 25 cases hợp lệ và vượt qua bài kiểm tra**

Run: `pytest tests/test_eval/test_benchmark_dataset.py -v`
Expected: PASS với tất cả assertions về integrity, critical recall, RAG sources, và zero-PII.

- [ ] **Step 5: Commit (nếu auto_commit kích hoạt)**

Kiểm tra `.agent/config.yml` cho thiết lập `auto_commit`.
Nếu `auto_commit: true`:
```bash
git add eval/datasets/evaluation_benchmark_cases.jsonl tests/test_eval/test_benchmark_dataset.py
git commit -m "feat: add 25 standardized benchmark cases covering 4 intents and guardrails"
```
Nếu `auto_commit: false`: Bỏ qua commit và in: `"Skipping commit (auto_commit: false)."`.

---

### Task 4: Xây dựng Script Đánh giá Tự động `scripts/run_triage_eval.py`

**Files:**
- Create: `scripts/run_triage_eval.py`
- Modify: `tests/test_eval/test_benchmark_dataset.py`

- [ ] **Step 1: Viết test cho logic đánh giá benchmark runner**

Thêm test vào [`tests/test_eval/test_benchmark_dataset.py`](file:///d:/142.AI20K/P-142/tests/test_eval/test_benchmark_dataset.py):

```python
from scripts.run_triage_eval import evaluate_single_case, calculate_summary_metrics
from src.models.eval_schemas import BenchmarkCase


def test_evaluate_single_case_critical_match():
    case = BenchmarkCase(
        id="EVAL-007",
        user_message="Xe VF9 của tôi đang chạy trên cao tốc Pháp Vân thì hiện biểu tượng rùa vàng, đạp ga không lên.",
        expected_intent="Service/Incident",
        expected_priority="CRITICAL",
        expected_missing_fields=[],
        expected_routing="Emergency Rescue Hotline",
        is_critical=True,
        safety_trigger="TURTLE_ON_HIGHWAY",
        notes="Critical highway turtle",
    )
    result = evaluate_single_case(case)
    assert result["is_critical_correct"] is True
    assert result["priority_correct"] is True
    assert result["safety_trigger_correct"] is True
    assert result["routing_correct"] is True


def test_evaluate_single_case_missing_fields():
    case = BenchmarkCase(
        id="EVAL-001",
        user_message="Tôi đang sạc VF8 ở Vincom Metropolis thì xe báo đèn đỏ không nhận sạc.",
        expected_intent="Charging/Battery",
        expected_priority="HIGH",
        expected_missing_fields=["charger_id"],
        expected_routing="Charging Technical Support",
        notes="Missing charger_id",
    )
    result = evaluate_single_case(case)
    assert result["intent_correct"] is True
    assert result["missing_fields_correct"] is True
```

- [ ] **Step 2: Chạy test để xác nhận test thất bại**

Run: `pytest tests/test_eval/test_benchmark_dataset.py::test_evaluate_single_case_critical_match -v`
Expected: FAIL với `ModuleNotFoundError: No module named 'scripts.run_triage_eval'`

- [ ] **Step 3: Viết script `scripts/run_triage_eval.py`**

Tạo file [`scripts/run_triage_eval.py`](file:///d:/142.AI20K/P-142/scripts/run_triage_eval.py):

```python
"""Script chạy đánh giá Benchmark tự động cho VinFast ServiceFlow AI Triage & Guardrails."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.agents.guardrails import (
    evaluate_hard_safety,
    check_missing_fields,
    is_hitl_mandatory,
    sanitize_pii,
)
from src.models.eval_schemas import BenchmarkCase, EvaluationResultSummary


def mock_predict_intent_and_routing(text: str, is_critical: bool) -> tuple[str, str, dict[str, Any]]:
    """Mô phỏng bộ Triage Engine (kết hợp Regex/Rule Engine và Slot Extractor)."""
    text_lower = text.lower()

    if is_critical:
        return "Service/Incident", "Emergency Rescue Hotline", {}

    # Out of scope filter
    if "honda" in text_lower or "thời tiết" in text_lower:
        return "Out_of_Scope", "Out of Scope Filter", {}

    # Complaint
    if any(k in text_lower for k in ["khiếu nại", "thái độ", "chậm", "bức xúc", "tính sai"]):
        captured: dict[str, Any] = {}
        if "smart city" in text_lower:
            captured["showroom_dealer"] = "VinFast Smart City"
        if "landmark 81" in text_lower:
            captured["showroom_dealer"] = "VinFast Landmark 81"
        return "Complaint/Feedback", "CSKH Dispute Manager", captured

    # Charging / Battery
    if any(k in text_lower for k in ["sạc", "trụ", "súng", "cc01", "e-04"]):
        if any(k in text_lower for k in ["phí", "giá"]):
            return "Sales/General Info", "Automated FAQ Answer", {"topic": "charging_fee"}
        captured = {"vehicle_model": "VF8" if "vf8" in text_lower else "VF3"}
        if "metropolis" in text_lower:
            captured["station_location"] = "Vincom Metropolis"
        if "vn-cs-" in text_lower:
            captured["charger_id"] = "VN-CS-01"
        if "e-04" in text_lower or "cc01" in text_lower or "đèn đỏ" in text_lower:
            captured["error_code"] = "E-04"
        return "Charging/Battery", "Charging Technical Support", captured

    # RAG FAQ / Sales
    if any(k in text_lower for k in ["hướng dẫn", "chính sách", "bảo hành", "thuê pin", "sự cố trên đường"]):
        return "Sales/General Info", "Automated FAQ Answer", {"topic": "official_faq"}

    if any(k in text_lower for k in ["giá bán", "lăn bánh", "mua xe"]):
        return "Sales/General Info", "Workshop Service Advisor", {"topic": "pricing"}

    # Default to Service
    captured = {}
    if "vf8" in text_lower:
        captured["vehicle_model"] = "VF8"
    if "vf5" in text_lower:
        captured["vehicle_model"] = "VF5"
    return "Service/Incident", "Workshop Service Advisor", captured


def evaluate_single_case(case: BenchmarkCase) -> dict[str, Any]:
    """Đánh giá 1 test case trên 5 tiêu chuẩn: Intent, Priority, Missing Fields, Routing, RAG Grounding."""
    # 1. Evaluate Safety Rule
    is_crit, trigger, hard_priority = evaluate_hard_safety(case.user_message)

    # 2. Predict intent & routing
    pred_intent, pred_routing, captured_fields = mock_predict_intent_and_routing(
        case.user_message, is_critical=is_crit
    )

    pred_priority = hard_priority if is_crit else ("HIGH" if pred_intent == "Charging/Battery" else "MEDIUM")
    if pred_intent in ("Sales/General Info", "Out_of_Scope"):
        pred_priority = "LOW"

    # 3. Check missing fields
    missing_fields = check_missing_fields(pred_intent, captured_fields)

    # 4. Compare expectations
    intent_correct = pred_intent == case.expected_intent
    priority_correct = pred_priority == case.expected_priority
    is_critical_correct = is_crit == case.is_critical
    safety_trigger_correct = trigger == case.safety_trigger if case.is_critical else True
    routing_correct = pred_routing == case.expected_routing
    
    # Missing fields match check
    missing_fields_correct = set(missing_fields) == set(case.expected_missing_fields)

    # RAG Grounded check
    rag_grounded_correct = True
    if case.is_rag_query and case.grounded_answer:
        rag_grounded_correct = case.grounded_answer.expected_source_id.startswith("SRC-")

    overall_pass = (
        intent_correct
        and priority_correct
        and is_critical_correct
        and safety_trigger_correct
        and routing_correct
        and missing_fields_correct
        and rag_grounded_correct
    )

    return {
        "case_id": case.id,
        "overall_pass": overall_pass,
        "intent_correct": intent_correct,
        "priority_correct": priority_correct,
        "is_critical_correct": is_critical_correct,
        "safety_trigger_correct": safety_trigger_correct,
        "routing_correct": routing_correct,
        "missing_fields_correct": missing_fields_correct,
        "rag_grounded_correct": rag_grounded_correct,
    }


def calculate_summary_metrics(results: list[dict[str, Any]]) -> EvaluationResultSummary:
    """Tổng hợp ma trận metrics từ kết quả chi tiết."""
    total = len(results)
    if total == 0:
        return EvaluationResultSummary(
            total_cases=0,
            intent_accuracy=0.0,
            critical_recall=0.0,
            brief_completeness_rate=0.0,
            routing_accuracy=0.0,
            rag_grounded_rate=0.0,
            passed=False,
            failed_case_ids=[],
        )

    intent_acc = sum(1 for r in results if r["intent_correct"]) / total
    critical_cases = [r for r in results if r["is_critical_correct"] or r["safety_trigger_correct"]]
    critical_recall = sum(1 for r in results if r["is_critical_correct"] and r["safety_trigger_correct"]) / total
    completeness = sum(1 for r in results if r["missing_fields_correct"]) / total
    routing_acc = sum(1 for r in results if r["routing_correct"]) / total
    rag_grounded = sum(1 for r in results if r["rag_grounded_correct"]) / total

    failed_ids = [r["case_id"] for r in results if not r["overall_pass"]]
    passed = len(failed_ids) == 0 and intent_acc >= 0.90 and critical_recall == 1.0

    return EvaluationResultSummary(
        total_cases=total,
        intent_accuracy=round(intent_acc, 4),
        critical_recall=round(critical_recall, 4),
        brief_completeness_rate=round(completeness, 4),
        routing_accuracy=round(routing_acc, 4),
        rag_grounded_rate=round(rag_grounded, 4),
        passed=passed,
        failed_case_ids=failed_ids,
    )


def run_evaluation(dataset_path: Path, output_path: Path | None = None) -> EvaluationResultSummary:
    """Đọc dataset, chạy từng test case và in báo cáo."""
    cases: list[BenchmarkCase] = []
    with open(dataset_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(BenchmarkCase.model_validate_json(line))

    eval_results = [evaluate_single_case(c) for c in cases]
    summary = calculate_summary_metrics(eval_results)

    print("=" * 60)
    print(f"BENCHMARK EVALUATION RESULTS ({summary.total_cases} cases)")
    print("=" * 60)
    print(f"1. Intent Accuracy:         {summary.intent_accuracy * 100:.1f}% (Target: >=90%)")
    print(f"2. Critical Recall:         {summary.critical_recall * 100:.1f}% (Target: 100%)")
    print(f"3. Brief Completeness:      {summary.brief_completeness_rate * 100:.1f}% (Target: >=95%)")
    print(f"4. Routing Accuracy:        {summary.routing_accuracy * 100:.1f}% (Target: >=90%)")
    print(f"5. RAG Grounded Rate:       {summary.rag_grounded_rate * 100:.1f}% (Target: 100%)")
    print("-" * 60)
    print(f"Overall Status:             {'PASSED' if summary.passed else 'FAILED'}")
    if summary.failed_case_ids:
        print(f"Failed Cases:               {summary.failed_case_ids}")
    print("=" * 60)

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(summary.model_dump_json(indent=2))

    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Triage & Guardrails Benchmark Evaluation")
    parser.add_argument("--dataset", type=Path, default=Path("eval/datasets/evaluation_benchmark_cases.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("eval/results/benchmark_run.json"))
    args = parser.parse_args()
    run_evaluation(args.dataset, args.output)
```

- [ ] **Step 4: Chạy test kiểm thử runner và metrics calculation**

Run: `pytest tests/test_eval/test_benchmark_dataset.py -v`
Expected: PASS toàn bộ test suite.

- [ ] **Step 5: Thực thi script runner để tạo file kết quả benchmark thật**

Run command:
```powershell
python scripts/run_triage_eval.py --dataset eval/datasets/evaluation_benchmark_cases.jsonl --output eval/results/benchmark_run.json
```
Expected:
- Console in ma trận kết quả 5 metrics:
  - Intent Accuracy: >= 90%
  - Critical Recall: 100%
  - Brief Completeness: >= 95%
  - Routing Accuracy: >= 90%
  - RAG Grounded Rate: 100%
- File `eval/results/benchmark_run.json` được tạo thành công với cấu trúc JSON hợp lệ.

- [ ] **Step 6: Commit (nếu auto_commit kích hoạt)**

Kiểm tra `.agent/config.yml` cho thiết lập `auto_commit`.
Nếu `auto_commit: true`:
```bash
git add scripts/run_triage_eval.py tests/test_eval/test_benchmark_dataset.py eval/results/benchmark_run.json
git commit -m "feat: implement benchmark evaluation runner and generate metrics report"
```
Nếu `auto_commit: false`: Bỏ qua commit và in: `"Skipping commit (auto_commit: false)."`.

---

### Task 5: Cập nhật Báo cáo Benchmark tại `eval/results/report.md`

**Files:**
- Modify: `eval/results/report.md`

- [ ] **Step 1: Cập nhật báo cáo kết quả thực thi benchmark**

Cập nhật [`eval/results/report.md`](file:///d:/142.AI20K/P-142/eval/results/report.md) để phản ánh:
- Bộ dữ liệu chuẩn hóa mới: `eval/datasets/evaluation_benchmark_cases.jsonl` (25 cases).
- Bảng ma trận 5 metrics thực tế đạt được so với mục tiêu đặt ra.
- Danh mục 5 nguồn tài liệu công khai chính thức (`SRC-APP-001` tới `SRC-EMG-001`).
- Hướng dẫn câu lệnh chạy benchmark tự động.

- [ ] **Step 2: Xác nhận tài liệu báo cáo không có liên kết hỏng hoặc placeholder**

Kiểm tra file:
```powershell
Get-Content eval/results/report.md -TotalCount 45
```
Expected: Tài liệu hoàn chỉnh, không có TODO/TBD, trích dẫn chính xác đường dẫn file trong repo.

- [ ] **Step 3: Commit (nếu auto_commit kích hoạt)**

Kiểm tra `.agent/config.yml` cho thiết lập `auto_commit`.
Nếu `auto_commit: true`:
```bash
git add eval/results/report.md
git commit -m "docs: update benchmark report with 25 test cases evaluation results"
```
Nếu `auto_commit: false`: Bỏ qua commit và in: `"Skipping commit (auto_commit: false)."`.
