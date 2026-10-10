# Báo cáo kiểm thử MVP

## 1. Kết quả tổng hợp

| Ca | Tình huống | Kết quả | Ghi nhận chính |
| --- | --- | --- | --- |
| TC01 | Chào hỏi | PASS | Chào hỏi, gợi ý chức năng; không tạo case. |
| TC02 | Giải thích cảnh báo con rùa | PASS | Giải thích kiến thức chung, ghi rõ chưa đối chiếu sổ tay. |
| TC03 | Tra cứu bảo hành VF8 | PASS | Ba lần gọi đều có đáp án, nguồn SRC-002 và trace LLM parsed. |
| TC04 | Tiếp nhận khiếu nại | PASS | Tạo hồ sơ khiếu nại; không tự gán dòng xe. |
| TC05 | Sự cố sạc đủ dữ kiện | PASS | Giữ tên địa điểm, trụ, mã lỗi và mức pin. |
| TC06 | Thiếu thông tin qua ba lượt | PASS | Hỏi tối đa hai lượt; giữ dòng xe chưa biết là null. |
| TC07 | Sửa dòng xe và giữ ngữ cảnh | PASS | Sửa VF8 thành VF9 trên cùng hồ sơ, giữ dữ kiện còn lại. |
| TC08 | Khẩn cấp khi xe đang đỗ sạc | FAIL | Nhận đúng khẩn cấp nhưng hướng dẫn chưa khớp xe đỗ sạc. |
| TC09 | Phân quyền hồ sơ | PASS | Chủ case được đọc; Customer khác và truy cập Staff bị chặn. |
| TC10 | Nhân viên xử lý và khách xác nhận đóng hồ sơ | PASS | In Progress → Resolved → Closed, database khớp. |

**9 ca PASS, 1 ca FAIL (TC08)** theo kết quả thực tế mới nhất. Hai phản hồi 403 trong TC09 là kết quả đúng của kiểm tra quyền. TC08 còn lỗi hướng dẫn khẩn cấp; chưa thể kết luận đạt toàn bộ Gate 2. Bộ này chưa kiểm tra UI, ảnh/OCR/vision, tải đồng thời hoặc điều phối dịch vụ bên ngoài.

## 2. Input và output thực tế

### TC01: Chào hỏi 

**Bước 1 — customer: `POST /api/v1/customer/chat`**

**Input:**

```json
{
  "session_id": "evidence-TC01",
  "message": "Chào bạn, bạn có thể hỗ trợ tôi những gì?"
}
```

**Output thực tế:** HTTP `200`, thời gian `0.074` giây.

> Chào bạn! Em là Trợ lý VF Serv. Em có thể hỗ trợ gì cho bạn hôm nay ạ?

**Trích trường payload:**

```json
{
  "response_type": "FAQ_ANSWER",
  "case_id": null,
  "status": null,
  "priority": null,
  "clarification_turn": null,
  "max_clarification_turns": null,
  "citations": null,
  "suggested_replies": [
    "Tư vấn xe",
    "Trạm sạc & ứng dụng",
    "Bảo hành & bảo dưỡng",
    "Báo sự cố kỹ thuật"
  ],
  "safe_guidance": null,
  "show_emergency_banner": false,
  "request_location": false,
  "emergency_context": null,
  "safety_status": "unconfirmed"
}
```

**Đánh giá: PASS.** API trả lời chào hỏi, cung cấp bốn nhóm gợi ý và không tạo hồ sơ. Phản hồi chưa liệt kê khả năng hỗ trợ trong chính câu trả lời; các lựa chọn nằm ở `suggested_replies`.

### TC02: Giải thích cảnh báo con rùa

**Bước 1 — customer: `POST /api/v1/customer/chat`**

**Input:**

```json
{
  "session_id": "evidence-TC02",
  "message": "Biểu tượng con rùa trên xe VF8 nghĩa là gì?"
}
```

**Output thực tế:** HTTP `200`, thời gian `0.101` giây.

> Biểu tượng con rùa (Turtle Mode) thường báo xe đang giới hạn công suất, nên khả năng tăng tốc có thể giảm. Đây là cơ chế bảo vệ; pin yếu, nhiệt độ bất thường hoặc lỗi hệ thống có thể là những nguyên nhân, nhưng chỉ biểu tượng này chưa đủ để xác định nguyên nhân của xe cụ thể.
>
> Đây là kiến thức chung về xe, chưa đối chiếu sổ tay đúng mẫu/đời xe; không phải kết luận chẩn đoán.

**Trích trường payload:**

```json
{
  "response_type": "FAQ_ANSWER",
  "case_id": null,
  "status": null,
  "priority": null,
  "clarification_turn": null,
  "max_clarification_turns": null,
  "citations": [],
  "suggested_replies": [
    "Xe tôi đang hiện biểu tượng này",
    "Khi nào xe tự giới hạn công suất?",
    "Tìm trạm sạc gần tôi"
  ],
  "safe_guidance": null,
  "show_emergency_banner": false,
  "request_location": false,
  "emergency_context": null,
  "safety_status": "unconfirmed"
}
```

**Đánh giá: PASS.** Trả lời về giới hạn công suất và nêu rõ giới hạn kiến thức chung. `citations=[]`, không tạo case. Ca này xác nhận phản hồi kiến thức chung, chưa chứng minh tra cứu sổ tay VF8.

### TC03: Tra cứu bảo hành VF8 

**Input:**

```json
{
  "session_id": "warranty-ef4610de-cold",
  "message": "Thời hạn bảo hành xe VinFast VF8 tiêu chuẩn là bao nhiêu năm hoặc bao nhiêu km?"
}
```

Gửi `POST /api/v1/customer/chat` bằng tài khoản Customer. Ba request dùng ba `session_id` riêng trong cùng tiến trình; câu hỏi, code và cấu hình ứng dụng giữ nguyên. Các nhãn “cold”, “warm-1”, “warm-2” trong bằng chứng phân biệt lần gọi đầu và các lần sau, không có nghĩa đã xóa cache của hệ điều hành.

**Lần 1:** HTTP `200`, thời gian `5.479` giây.

> Theo tài liệu VinFast:
>
> Thời hạn bảo hành xe VinFast VF8 là 10 năm hoặc 200.000 km, tùy điều kiện nào đến trước.

`response_type=FAQ_ANSWER`, `case_id=null`, nguồn `SRC-002`. Trace: `kind=llm`, `node=rag_qa`, `gate_decision=parsed`, model `gpt-4o-mini`; 980 input tokens, 44 output tokens.

**Lần 2:** HTTP `200`, thời gian `1.924` giây.

> Theo tài liệu VinFast:
>
> Thời hạn bảo hành cho xe VinFast VF8 là 10 năm hoặc 200.000 km, tùy điều kiện nào đến trước.

`response_type=FAQ_ANSWER`, `case_id=null`, nguồn `SRC-002`. Trace: `kind=llm`, `node=rag_qa`, `gate_decision=parsed`, model `gpt-4o-mini`; 980 input tokens, 45 output tokens.

**Lần 3:** HTTP `200`, thời gian `1.008` giây.

> Theo tài liệu VinFast:
>
> Thời hạn bảo hành xe VinFast VF8 là 10 năm hoặc 200.000 km, tùy điều kiện nào đến trước.

`response_type=FAQ_ANSWER`, `case_id=null`, nguồn `SRC-002`. Trace: `kind=llm`, `node=rag_qa`, `gate_decision=parsed`, model `gpt-4o-mini`; 980 input tokens, 44 output tokens.

**Nguồn trả về trong payload:**

```json
{
  "source_id": "SRC-002",
  "title": "Chính sách bảo hành xe ô tô VinFast",
  "url": "https://vinfastauto.com/vn_vi/chinh-sach-bao-hanh-oto",
  "verified_at": "2026-09-30",
  "status_code": 200,
  "applicable_models": [
    "ALL"
  ],
  "source_type": "official_policy",
  "relevant_snippet": "VinFast không có trách nhiệm thu hồi và thay thế sản phẩm khác cho khách hàng nếu việc sửa chữa bảo hành có thể khắc phục được lỗi chất lượng, lỗi vật liệu hay lỗi lắp ráp của nhà sản xuất.
Thời hạn bảo hành Ô tô
VinFast đã chuyển đổi Sổ Bảo Hành sang hình thức điện tử. Tại thời điểm bàn giao xe, Đại lý phân phối sẽ tư vấn, hướng dẫn Khách hàng xác nhận Sổ Bảo Hành điện tử và cách thức tra cứu, sử dụng.
Đối với xe được sử dụng ở điều kiện sử dụng tiêu chuẩn:
- VF 8, VF 9, Lạc Hồng 900LX: 10 năm hoặc 200.000 km (tùy điều kiện nào đến trước)."
}
```

**Đối chiếu thực tế:** vector store có 2.195 đoạn dữ liệu. Gọi truy xuất trực tiếp sau lần API đầu trả `SUCCESS` trong 0,090 giây; cả ba trace node `rag` của lần kiểm tra lại đều trả `retrieval_status=SUCCESS`. Không có hồ sơ sự cố được tạo trong database của lần kiểm tra lại; đây là hành vi phù hợp với câu hỏi FAQ được trả lời thành công.

**Đánh giá: PASS (3/3 request).** Cả ba lần trả lời có nguồn SRC-002 và trace LLM `parsed`. Dữ liệu input/output và trace đầy đủ nằm trong [bằng chứng TC03](../eval/results/evidence-20261010/warranty-recheck.json).

### TC04: Tiếp nhận khiếu nại

**Bước 1 — customer: `POST /api/v1/customer/chat`**

**Input:**

```json
{
  "session_id": "evidence-TC04",
  "message": "Tôi muốn khiếu nại thái độ nhân viên tại xưởng demo A. Tôi đã chờ 2 giờ nhưng chưa được hỗ trợ, mong có người phụ trách liên hệ trên ứng dụng."
}
```

**Output thực tế:** HTTP `200`, thời gian `0.026` giây.

> Dạ em rất tiếc về trải nghiệm chưa thuận tiện của anh/chị. Hệ thống đã ghi nhận phản hồi vào hồ sơ hỗ trợ chuyên trách (Mã: CASE-20261010-d33990ff2f3d45d4) và chuyển ngay đến bộ phận Chăm sóc Khách hàng để rà soát, xử lý ưu tiên. Anh/chị vui lòng theo dõi cập nhật trực tiếp tại đây nhé ạ.

**Trích trường payload:**

```json
{
  "response_type": "CASE_CREATED",
  "case_id": "CASE-20261010-d33990ff2f3d45d4",
  "status": "Staff Reviewing",
  "priority": "MEDIUM",
  "clarification_turn": null,
  "max_clarification_turns": null,
  "citations": null,
  "suggested_replies": null,
  "safe_guidance": "Chuyên viên CSKH đang xử lý hồ sơ này của Quý khách.",
  "show_emergency_banner": false,
  "request_location": false,
  "emergency_context": null,
  "safety_status": "unconfirmed"
}
```

**Đối chiếu database cuối lần chạy:**

```json
[
  {
    "id": "CASE-20261010-d33990ff2f3d45d4",
    "session_id": "evidence-TC04",
    "vehicle_model": null,
    "intent": "Complaint/Feedback",
    "priority": "MEDIUM",
    "status": "Staff Reviewing"
  }
]
```

**Đánh giá: PASS.** Tiếp nhận khiếu nại, trả mã hồ sơ và trạng thái `Staff Reviewing`, ưu tiên `MEDIUM`. Database ghi nhóm `Complaint/Feedback`, `vehicle_model=null`; không còn tự gán VF8 khi khách chưa cung cấp. Kết quả chỉ xác nhận tiếp nhận, chưa xác nhận CSKH thực tế đã liên hệ hoặc giải quyết khiếu nại.

### TC05: Sự cố sạc đủ dữ kiện

**Bước 1 — customer: `POST /api/v1/customer/chat`**

**Input:**

```json
{
  "session_id": "evidence-TC05",
  "message": "Xe VF8 của tôi không nhận sạc tại trụ P01, mã lỗi CC01, pin còn 25%, xe đang đỗ tại trạm demo A."
}
```

**Output thực tế:** HTTP `200`, thời gian `0.023` giây.

> Dạ VinFast đã ghi nhận sự cố sạc của xe VF8:
> Vị trí trạm: demo A
> Trụ sạc: P01
> Mã lỗi: CC01
>
> Hệ thống đã tự động tạo hồ sơ hỗ trợ (Mã: CASE-20261010-7818ff3c725f4974) và chuyển dữ liệu trực tiếp tới Chuyên viên Kỹ thuật trạm sạc. Anh/chị vui lòng theo dõi cập nhật tiến độ giải quyết trực tiếp trên màn hình này ạ.

**Trích trường payload:**

```json
{
  "response_type": "CASE_CREATED",
  "case_id": "CASE-20261010-7818ff3c725f4974",
  "status": "Staff Reviewing",
  "priority": "HIGH",
  "clarification_turn": null,
  "max_clarification_turns": null,
  "citations": null,
  "suggested_replies": null,
  "safe_guidance": "Anh/chị vui lòng giữ xe ở vị trí đỗ an toàn và theo dõi cập nhật trên giao diện này.",
  "show_emergency_banner": false,
  "request_location": false,
  "emergency_context": null,
  "safety_status": "unconfirmed"
}
```

**Bước 2 — staff: `GET /api/v1/staff/tickets/CASE-20261010-7818ff3c725f4974`**

**Input:**

Không có body; request dùng đường dẫn và tài khoản ở trên.

**Output thực tế:** HTTP `200`, thời gian `0.018` giây.

**Trích trường payload:**

```json
{
  "case": {
    "safety_status": "unconfirmed",
    "safety_acknowledged_at": null,
    "incident_version": 1,
    "id": "CASE-20261010-7818ff3c725f4974",
    "mock_customer_id": "CUST_MOCK_01",
    "vehicle_code_mock": null,
    "vehicle_model": "VF8",
    "intent": "Charging/Battery",
    "priority": "HIGH",
    "status": "Staff Reviewing"
  },
  "case_brief": {
    "summary": "Xe VF8 gặp sự cố sạc tại demo A (P01): báo lỗi CC01.",
    "captured_fields": {
      "vehicle_model": "VF8",
      "station_location": "demo A",
      "charger_id": "P01",
      "error_code": "CC01",
      "current_soc": "25%",
      "visual_signals": []
    },
    "suggested_action": "Kiểm tra tín hiệu handshake giao tiếp trụ sạc từ xa hoặc cử kỹ thuật viên trạm cắm lại cáp.",
    "confidence_score": 0.95,
    "is_edited_by_staff": false
  }
}
```

**Đối chiếu database cuối lần chạy:**

```json
[
  {
    "id": "CASE-20261010-7818ff3c725f4974",
    "session_id": "evidence-TC05",
    "vehicle_model": "VF8",
    "intent": "Charging/Battery",
    "priority": "HIGH",
    "status": "Closed"
  }
]
```

**Đánh giá: PASS.** API nhân viên đọc được VF8, địa điểm `demo A`, trụ P01, CC01 và mức pin 25%. Địa điểm được rút gọn bỏ tiền tố “trạm” nhưng giữ tên riêng, không còn bị thay bằng trạm mặc định. Hồ sơ ban đầu `Staff Reviewing`, nhóm `Charging/Battery`, ưu tiên `HIGH`. Hồ sơ này tiếp tục được dùng trong TC09–TC10.

### TC06: Thiếu thông tin qua ba lượt 

**Bước 1 — customer: `POST /api/v1/customer/chat`**

**Input:**

```json
{
  "session_id": "evidence-TC06",
  "message": "Xe tôi không sạc được."
}
```

**Output thực tế:** HTTP `200`, thời gian `0.020` giây.

> Anh/chị đang gặp sự cố với dòng xe nào ạ?

**Trích trường payload:**

```json
{
  "response_type": "CLARIFICATION",
  "case_id": null,
  "status": null,
  "priority": null,
  "clarification_turn": 1,
  "max_clarification_turns": 2,
  "citations": null,
  "suggested_replies": [
    "VF3",
    "VF5",
    "VF6",
    "VF7",
    "VF8",
    "VF9",
    "e34"
  ],
  "safe_guidance": null,
  "show_emergency_banner": false,
  "request_location": false,
  "emergency_context": null,
  "safety_status": "unconfirmed"
}
```

**Bước 2 — customer: `POST /api/v1/customer/chat`**

**Input:**

```json
{
  "session_id": "evidence-TC06",
  "message": "Xe vẫn không sạc được, tôi chưa biết mã trụ và không nhớ dòng xe."
}
```

**Output thực tế:** HTTP `200`, thời gian `0.016` giây.

> Anh/chị đang gặp sự cố với dòng xe nào ạ?

**Trích trường payload:**

```json
{
  "response_type": "CLARIFICATION",
  "case_id": null,
  "status": null,
  "priority": null,
  "clarification_turn": 2,
  "max_clarification_turns": 2,
  "citations": null,
  "suggested_replies": [
    "VF3",
    "VF5",
    "VF6",
    "VF7",
    "VF8",
    "VF9",
    "e34"
  ],
  "safe_guidance": null,
  "show_emergency_banner": false,
  "request_location": false,
  "emergency_context": null,
  "safety_status": "unconfirmed"
}
```

**Bước 3 — customer: `POST /api/v1/customer/chat`**

**Input:**

```json
{
  "session_id": "evidence-TC06",
  "message": "Xe vẫn không sạc được, tôi vẫn chưa có thêm thông tin."
}
```

**Output thực tế:** HTTP `200`, thời gian `0.019` giây.

> Hệ thống đã tạo hồ sơ ghi nhận (Mã: CASE-20261010-4d60082a561d44cc). Do chưa đủ một số dữ kiện kỹ thuật, hồ sơ được chuyển sang hàng đợi nhân viên hỗ trợ; nhân viên sẽ kiểm tra hoặc gửi yêu cầu bổ sung thông tin cho anh/chị.

**Trích trường payload:**

```json
{
  "response_type": "CASE_CREATED",
  "case_id": "CASE-20261010-4d60082a561d44cc",
  "status": "Needs Information",
  "priority": "MEDIUM",
  "clarification_turn": null,
  "max_clarification_turns": null,
  "citations": null,
  "suggested_replies": null,
  "safe_guidance": "Vui lòng giữ kết nối và theo dõi cập nhật trên giao diện này.",
  "show_emergency_banner": false,
  "request_location": false,
  "emergency_context": null,
  "safety_status": "unconfirmed"
}
```

**Đối chiếu database cuối lần chạy:**

```json
[
  {
    "id": "CASE-20261010-4d60082a561d44cc",
    "session_id": "evidence-TC06",
    "vehicle_model": null,
    "intent": "Service/Incident",
    "priority": "MEDIUM",
    "status": "Needs Information"
  }
]
```

**Đánh giá: PASS.** Hai lượt đầu hỏi dòng xe, `clarification_turn` lần lượt 1 và 2, `max_clarification_turns=2`; lượt thứ ba tạo hồ sơ `Needs Information`. Database giữ `vehicle_model=null`. Hệ thống không tự điền VF8, nhưng câu hỏi lặp nguyên văn ở lượt hai dù khách nói không nhớ dòng xe; đây là điểm cần cải thiện trải nghiệm.

### TC07: Sửa dòng xe và giữ ngữ cảnh

**Bước 1 — customer: `POST /api/v1/customer/chat`**

**Input:**

```json
{
  "session_id": "evidence-TC07",
  "message": "Xe VF8 của tôi không sạc được tại trụ P02, pin 30%, xe đang đỗ tại trạm demo B."
}
```

**Output thực tế:** HTTP `200`, thời gian `0.023` giây.

> Dạ VinFast đã ghi nhận sự cố sạc của xe VF8:
> Vị trí trạm: demo B
> Trụ sạc: P02
> Mã lỗi: chưa cung cấp
>
> Hệ thống đã tự động tạo hồ sơ hỗ trợ (Mã: CASE-20261010-bda879871b474910) và chuyển dữ liệu trực tiếp tới Chuyên viên Kỹ thuật trạm sạc. Anh/chị vui lòng theo dõi cập nhật tiến độ giải quyết trực tiếp trên màn hình này ạ.

**Trích trường payload:**

```json
{
  "response_type": "CASE_CREATED",
  "case_id": "CASE-20261010-bda879871b474910",
  "status": "Staff Reviewing",
  "priority": "HIGH",
  "clarification_turn": null,
  "max_clarification_turns": null,
  "citations": null,
  "suggested_replies": null,
  "safe_guidance": "Anh/chị vui lòng giữ xe ở vị trí đỗ an toàn và theo dõi cập nhật trên giao diện này.",
  "show_emergency_banner": false,
  "request_location": false,
  "emergency_context": null,
  "safety_status": "unconfirmed"
}
```

**Bước 2 — customer: `POST /api/v1/customer/chat`**

**Input:**

```json
{
  "session_id": "evidence-TC07",
  "message": "Tôi nói nhầm, xe của tôi là VF9, không phải VF8. Trụ P02 và pin 30% vẫn đúng."
}
```

**Output thực tế:** HTTP `200`, thời gian `0.020` giây.

> Dạ VinFast đã ghi nhận sự cố sạc của xe VF9:
> Vị trí trạm: demo B
> Trụ sạc: P02
> Mã lỗi: chưa cung cấp
>
> Hệ thống đã tự động tạo hồ sơ hỗ trợ (Mã: CASE-20261010-bda879871b474910) và chuyển dữ liệu trực tiếp tới Chuyên viên Kỹ thuật trạm sạc. Anh/chị vui lòng theo dõi cập nhật tiến độ giải quyết trực tiếp trên màn hình này ạ.

**Trích trường payload:**

```json
{
  "response_type": "CASE_CREATED",
  "case_id": "CASE-20261010-bda879871b474910",
  "status": "Staff Reviewing",
  "priority": "HIGH",
  "clarification_turn": null,
  "max_clarification_turns": null,
  "citations": null,
  "suggested_replies": null,
  "safe_guidance": "Anh/chị vui lòng giữ xe ở vị trí đỗ an toàn và theo dõi cập nhật trên giao diện này.",
  "show_emergency_banner": false,
  "request_location": false,
  "emergency_context": null,
  "safety_status": "unconfirmed"
}
```

**Bước 3 — staff: `GET /api/v1/staff/tickets/CASE-20261010-bda879871b474910`**

**Input:**

Không có body; request dùng đường dẫn và tài khoản ở trên.

**Output thực tế:** HTTP `200`, thời gian `0.005` giây.

**Trích trường payload:**

```json
{
  "case": {
    "safety_status": "unconfirmed",
    "safety_acknowledged_at": null,
    "incident_version": 1,
    "id": "CASE-20261010-bda879871b474910",
    "mock_customer_id": "CUST_MOCK_01",
    "vehicle_code_mock": null,
    "vehicle_model": "VF9",
    "intent": "Charging/Battery",
    "priority": "HIGH",
    "status": "Staff Reviewing"
  },
  "case_brief": {
    "summary": "Xe VF9 gặp sự cố sạc tại demo B (P02).",
    "captured_fields": {
      "vehicle_model": "VF9",
      "station_location": "demo B",
      "charger_id": "P02",
      "error_code": null,
      "current_soc": "30%",
      "visual_signals": []
    },
    "suggested_action": "Kiểm tra tín hiệu handshake giao tiếp trụ sạc từ xa hoặc cử kỹ thuật viên trạm cắm lại cáp.",
    "confidence_score": 0.95,
    "is_edited_by_staff": false
  }
}
```

**Đối chiếu database cuối lần chạy:**

```json
[
  {
    "id": "CASE-20261010-bda879871b474910",
    "session_id": "evidence-TC07",
    "vehicle_model": "VF9",
    "intent": "Charging/Battery",
    "priority": "HIGH",
    "status": "Staff Reviewing"
  }
]
```

**Đánh giá: PASS.** Hai lượt trả cùng mã hồ sơ. Sau sửa thông tin, API nhân viên và database đều ghi VF9; địa điểm demo B, trụ P02, pin 30% được giữ. `error_code=null` đúng với việc khách chưa đưa mã lỗi. Tin nhắn lượt hai vẫn dùng mẫu “tự động tạo hồ sơ” dù đang cập nhật hồ sơ có sẵn.

### TC08: Khẩn cấp khi xe đang đỗ sạc

**Bước 1 — customer: `POST /api/v1/customer/chat`**

**Input:**

```json
{
  "session_id": "evidence-TC08",
  "message": "Xe VF8 của tôi đang đỗ tại trạm sạc demo C, có khói và mùi khét ở khu vực pin khi đang sạc. Tôi cần làm gì ngay?"
}
```

**Output thực tế:** HTTP `200`, thời gian `0.023` giây.

> Dạ VinFast đã ghi nhận tình trạng khẩn cấp của xe VF8. Hệ thống đã tự động tạo hồ sơ khẩn cấp (Mã: CASE-20261010-a491bc02fb5a4fd4). Anh/chị vui lòng gọi hotline để được hỗ trợ.
>
> ⚠️ HƯỚNG DẪN AN TOÀN NGAY LẬP TỨC: Quý khách vui lòng giữ bình tĩnh, tấp xe vào lề an toàn nếu có thể, bật đèn cảnh báo khẩn cấp (hazard), di chuyển ra khỏi xe đến khu vực an toàn và gọi ngay Hotline Cứu hộ VinFast 1900-232389 để được hỗ trợ khẩn cấp.

**Trích trường payload:**

```json
{
  "response_type": "CASE_CREATED",
  "case_id": "CASE-20261010-a491bc02fb5a4fd4",
  "status": "Staff Reviewing",
  "priority": "CRITICAL",
  "clarification_turn": null,
  "max_clarification_turns": null,
  "citations": null,
  "suggested_replies": null,
  "safe_guidance": "Quý khách vui lòng giữ bình tĩnh, tấp xe vào lề an toàn nếu có thể, bật đèn cảnh báo khẩn cấp (hazard), di chuyển ra khỏi xe đến khu vực an toàn và gọi ngay Hotline Cứu hộ VinFast 1900-232389 để được hỗ trợ khẩn cấp.",
  "show_emergency_banner": true,
  "request_location": true,
  "emergency_context": {
    "case_id": "CASE-20261010-a491bc02fb5a4fd4",
    "incident_version": 1,
    "safety_status": "unconfirmed",
    "safety_acknowledged_at": null
  },
  "safety_status": "unconfirmed"
}
```

**Đối chiếu database cuối lần chạy:**

```json
[
  {
    "id": "CASE-20261010-a491bc02fb5a4fd4",
    "session_id": "evidence-TC08",
    "vehicle_model": "VF8",
    "intent": "Service/Incident",
    "priority": "CRITICAL",
    "status": "Staff Reviewing"
  }
]
```

**Đánh giá: FAIL.** Tạo hồ sơ `CRITICAL`, bật `show_emergency_banner=true`, `request_location=true`, có `emergency_context` và `safety_status=unconfirmed`. Tuy nhiên, cả `message` và `safe_guidance` vẫn chứa hướng dẫn “tấp xe vào lề” cho tình huống xe đang đỗ sạc. Đây là lỗi phù hợp ngữ cảnh an toàn; HTTP 200 và ưu tiên CRITICAL chưa đủ để kết luận ca đạt. Lần chạy không xác nhận cuộc gọi hotline hay điều phối cứu hộ thực tế.

### TC09: Phân quyền hồ sơ

**Bước 1 — customer: `GET /api/v1/customer/cases/CASE-20261010-7818ff3c725f4974`**

**Input:**

Không có body; request dùng đường dẫn và tài khoản ở trên.

**Output thực tế:** HTTP `200`, thời gian `0.011` giây.

**Trích trường payload:**

```json
{
  "case": {
    "safety_status": "unconfirmed",
    "safety_acknowledged_at": null,
    "incident_version": 1,
    "id": "CASE-20261010-7818ff3c725f4974",
    "vehicle_model": "VF8",
    "vehicle_code_mock": null,
    "intent": "Charging/Battery",
    "priority": "HIGH",
    "status": "Staff Reviewing",
    "summary": "Xe VF8 gặp sự cố sạc tại demo A (P01): báo lỗi CC01.",
    "created_at": "2026-10-10T00:47:27.529488+00:00",
    "updated_at": "2026-10-10T00:47:27.529488+00:00"
  },
  "case_brief": {
    "summary": "Xe VF8 gặp sự cố sạc tại demo A (P01): báo lỗi CC01.",
    "captured_fields": {
      "vehicle_model": "VF8",
      "station_location": "demo A",
      "charger_id": "P01",
      "error_code": "CC01",
      "current_soc": "25%",
      "visual_signals": []
    },
    "suggested_action": "Kiểm tra tín hiệu handshake giao tiếp trụ sạc từ xa hoặc cử kỹ thuật viên trạm cắm lại cáp.",
    "confidence_score": 0.95,
    "is_edited_by_staff": false
  }
}
```

**Bước 2 — other: `GET /api/v1/customer/cases/CASE-20261010-7818ff3c725f4974`**

**Input:**

Không có body; request dùng đường dẫn và tài khoản ở trên.

**Output thực tế:** HTTP `403`, thời gian `0.004` giây.

```json
{
  "detail": "Bạn không có quyền truy cập vào hồ sơ này."
}
```

**Bước 3 — customer: `GET /api/v1/staff/tickets`**

**Input:**

Không có body; request dùng đường dẫn và tài khoản ở trên.

**Output thực tế:** HTTP `403`, thời gian `0.003` giây.

```json
{
  "detail": "Từ chối truy cập: Chức năng chỉ dành cho Nhân viên Dịch vụ (Staff)."
}
```

**Đánh giá: PASS.** Chủ hồ sơ đọc được dữ liệu với HTTP 200. Customer khác bị HTTP 403 và không nhận nội dung hồ sơ. Customer truy cập hàng đợi Staff bị HTTP 403. Chỉ xác nhận ba request nêu dưới đây, không suy rộng thành kiểm toán bảo mật toàn hệ thống.

### TC10: Nhân viên xử lý và khách xác nhận đóng hồ sơ

**Bước 1 — staff: `POST /api/v1/staff/tickets/CASE-20261010-7818ff3c725f4974/actions`**

**Input:**

```json
{
  "action": "APPROVE",
  "staff_id": "evidence-staff",
  "notes": "Thao tác mô phỏng trong database kiểm thử riêng."
}
```

**Output thực tế:** HTTP `200`, thời gian `0.013` giây.

```json
{
  "success": true,
  "data": {
    "success": true,
    "case_id": "CASE-20261010-7818ff3c725f4974"
  },
  "error": null,
  "meta": {
    "timestamp": "2026-10-10T00:47:27.781134+00:00"
  }
}
```

**Bước 2 — customer: `GET /api/v1/customer/cases/CASE-20261010-7818ff3c725f4974/status`**

**Input:**

Không có body; request dùng đường dẫn và tài khoản ở trên.

**Output thực tế:** HTTP `200`, thời gian `0.035` giây.

```json
{
  "success": true,
  "data": {
    "emergency_context": null,
    "priority": "HIGH",
    "safety_status": "unconfirmed",
    "safety_acknowledged_at": null,
    "incident_version": 1,
    "case_id": "CASE-20261010-7818ff3c725f4974",
    "status": "In Progress",
    "status_description": "Chuyên viên kỹ thuật đang kiểm tra và tiến hành xử lý sự cố.",
    "customer_message": "Thao tác mô phỏng trong database kiểm thử riêng.",
    "created_at": "2026-10-10T00:47:27.529488",
    "updated_at": "2026-10-10T00:47:27.775209"
  },
  "error": null,
  "meta": {
    "timestamp": "2026-10-10T00:47:27.816306+00:00"
  }
}
```

**Bước 3 — staff: `POST /api/v1/staff/tickets/CASE-20261010-7818ff3c725f4974/actions`**

**Input:**

```json
{
  "action": "RESOLVE",
  "staff_id": "evidence-staff",
  "notes": "Thao tác mô phỏng trong database kiểm thử riêng."
}
```

**Output thực tế:** HTTP `200`, thời gian `0.008` giây.

```json
{
  "success": true,
  "data": {
    "success": true,
    "case_id": "CASE-20261010-7818ff3c725f4974"
  },
  "error": null,
  "meta": {
    "timestamp": "2026-10-10T00:47:27.828900+00:00"
  }
}
```

**Bước 4 — customer: `GET /api/v1/customer/cases/CASE-20261010-7818ff3c725f4974/status`**

**Input:**

Không có body; request dùng đường dẫn và tài khoản ở trên.

**Output thực tế:** HTTP `200`, thời gian `0.004` giây.

```json
{
  "success": true,
  "data": {
    "emergency_context": null,
    "priority": "HIGH",
    "safety_status": "unconfirmed",
    "safety_acknowledged_at": null,
    "incident_version": 1,
    "case_id": "CASE-20261010-7818ff3c725f4974",
    "status": "Resolved",
    "status_description": "Sự cố đã được xử lý hoàn tất.",
    "customer_message": "Thao tác mô phỏng trong database kiểm thử riêng.",
    "created_at": "2026-10-10T00:47:27.529488",
    "updated_at": "2026-10-10T00:47:27.824378"
  },
  "error": null,
  "meta": {
    "timestamp": "2026-10-10T00:47:27.834746+00:00"
  }
}
```

**Bước 5 — customer: `POST /api/v1/customer/cases/CASE-20261010-7818ff3c725f4974/confirmation`**

**Input:**

```json
{
  "confirmation": "RESOLVED_CONFIRMED",
  "feedback_note": "Xác nhận mô phỏng để kiểm tra trạng thái hồ sơ."
}
```

**Output thực tế:** HTTP `200`, thời gian `0.009` giây.

```json
{
  "success": true,
  "data": {
    "success": true,
    "case_id": "CASE-20261010-7818ff3c725f4974",
    "status": "Closed",
    "message": "Xác nhận thành công. Hồ sơ sự cố đã được đóng."
  },
  "error": null,
  "meta": {
    "timestamp": "2026-10-10T00:47:27.844337+00:00"
  }
}
```

**Bước 6 — customer: `GET /api/v1/customer/cases/CASE-20261010-7818ff3c725f4974/status`**

**Input:**

Không có body; request dùng đường dẫn và tài khoản ở trên.

**Output thực tế:** HTTP `200`, thời gian `0.004` giây.

```json
{
  "success": true,
  "data": {
    "emergency_context": null,
    "priority": "HIGH",
    "safety_status": "unconfirmed",
    "safety_acknowledged_at": null,
    "incident_version": 1,
    "case_id": "CASE-20261010-7818ff3c725f4974",
    "status": "Closed",
    "status_description": "Hồ sơ đã được đóng thành công.",
    "customer_message": "Cảm ơn quý khách đã xác nhận. Hồ sơ sự cố đã được đóng thành công.",
    "created_at": "2026-10-10T00:47:27.529488",
    "updated_at": "2026-10-10T00:47:27.838757"
  },
  "error": null,
  "meta": {
    "timestamp": "2026-10-10T00:47:27.849727+00:00"
  }
}
```

**Đánh giá: PASS.** Staff gửi APPROVE rồi RESOLVE; API khách xác nhận lần lượt `In Progress` và `Resolved`. Khách gửi `RESOLVED_CONFIRMED`, nhận `Closed`, và request kiểm tra cuối vẫn trả `Closed`; database cuối cùng khớp. Các thao tác xử lý và xác nhận trong ca này là mô phỏng nghiệp vụ trên database riêng, không phải bằng chứng xe thực tế đã được sửa.

## 3. Các vấn đề còn tồn tại

1. **TC08 — hướng dẫn khẩn cấp chưa phù hợp ngữ cảnh:** input nói xe đang đỗ sạc, output vẫn dùng hướng dẫn dành cho xe đang chạy. Cần phân biệt ngữ cảnh trước khi chọn nội dung phản hồi.
2. **TC06 — câu hỏi lặp:** lượt hai chưa thích ứng với việc khách không nhớ dòng xe, dù cơ chế dừng hỏi sau hai lượt và lưu null đã hoạt động.
3. **TC07 — thông báo cập nhật gây hiểu nhầm:** cùng case_id được giữ, nhưng mẫu trả lời vẫn nói tạo hồ sơ mới.


