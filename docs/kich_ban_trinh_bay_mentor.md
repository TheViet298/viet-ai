# KỊCH BẢN BÁO CÁO MENTOR: VINFAST AI VIRTUAL ASSISTANT
## Báo Cáo Tiến Độ Phần Việc AI Engine, Knowledge Base (RAG) & Evaluation Suite

* **Người trình bày:** AI / RAG Engineer
* **Thời lượng dự kiến:** 5 – 7 phút (kèm Live Demo)
* **Tài liệu tham chiếu:** 
  - Kế hoạch tổng thể: `docs/data-workplan-mvp.md`
  - Quản trị nguồn & Quyết định kỹ thuật: `docs/decisions/ADR-003-data-and-evaluation.md`
  - Hợp đồng tích hợp Frontend & Backend: `docs/create_api_contract.md`
  - Báo cáo kết quả đo đạc: `eval/results/report.md` & `eval/results/benchmark_run.json`

---

## CÁC TÀI LIỆU CẦN MỞ SẴN TRÊN MÀN HÌNH (CHECKLIST TRƯỚC KHI BẮT ĐẦU)

1. Tab 1: `docs/data-sources.md` (Danh mục 9 nguồn dữ liệu công khai chính thức).
2. Tab 2: `eval/results/report.md` (Bảng chỉ số đánh giá Benchmark toàn diện).
3. Tab 3: `docs/create_api_contract.md` (Đặc tả API Contract kết nối Frontend/Backend).
4. Terminal: Đã mở sẵn thư mục dự án `d:\142.AI20K\P-142` để chạy Live Demo.

---

## NỘI DUNG KỊCH BẢN CHI TIẾT

### PHẦN 1: MỞ ĐẦU & TỔNG QUAN PHẠM VI (30 giây)

> **Hành động:** Mở slide hoặc màn hình chính dự án `P-142`.
>
> **Lời thoại:**
> *"Em chào anh/chị. Hôm nay em xin phép báo cáo tiến độ phần việc **AI Engine, Knowledge Base và Evaluation Suite** của dự án VinFast AI Virtual Assistant theo đúng định hướng trong `data-workplan-mvp.md` và `ADR-003`.*
> 
> *Trong nhóm, các bạn khác phụ trách UI và Core Database/Backend, còn em chịu trách nhiệm toàn bộ phần **bộ não của Agent**: từ việc chuẩn hóa nguồn dữ liệu RAG, thiết lập bộ benchmark test case đánh giá, đến xây dựng chatbot agent có kiểm soát an toàn và xuất bản API Contract để kết nối với Frontend/Backend.*
> 
> *Sau đây em xin báo cáo 3 khối công việc chính em đã hoàn thành:"*

---

### PHẦN 2: DỮ LIỆU KNOWLEDGE BASE RAG (NHÓM A) (1.5 phút)

> **Hành động:** Chuyển sang màn hình file `docs/data-sources.md`, lướt qua thư mục `data/raw/` và `data/processed/chunks.jsonl`.
>
> **Lời thoại:**
> *"Đầu tiên là **Nhóm A: Cơ sở tri thức phục vụ tra cứu RAG**. Để đảm bảo tính chính xác và tuyệt đối không dùng tin đồn hay vi phạm bản quyền:*
> 
> 1. *Em đã thu thập và kiểm chứng **9 nguồn dữ liệu công khai chính thức 100% từ VinFast**, gồm:*
>    - *Hướng dẫn ứng dụng VinFast (`SRC-001`).*
>    - *Chính sách bảo hành ô tô tiêu chuẩn (`SRC-002`): 10 năm/200.000km cho VF 7-9, 7 năm cho VF 3-6.*
>    - *Quy trình cứu hộ 24/7 và cứu hộ pin khẩn cấp (`SRC-003`).*
>    - *Dịch vụ bảo dưỡng (`SRC-004`), Mobile Service (`SRC-005`) và quy chuẩn trạm sạc pin (`SRC-006`).*
>    - *Đặc biệt, em đã crawl trọn vẹn **Sổ tay hướng dẫn sử dụng điện tử (Owner's Manual)** của 2 xe demo là **VF 8 (56 tiểu mục - `SRC-007`)** và **VF 5 (51 tiểu mục - `SRC-008`)** qua official API của VinFast.*
>    - *Cùng với catalog thông số kỹ thuật thương mại của 15 mẫu xe (`SRC-009`).*
> 
> 2. *Về kỹ thuật xử lý dữ liệu:*
>    - *Toàn bộ bản text sạch gốc (~1.2 MB) được lưu tại `data/raw/` kèm URL và ngày xác minh `2026-09-30`.*
>    - *Em đã cắt thành **2,164 chunks** (kích thước ~500 ký tự, overlap 80 ký tự, giữ nguyên vẹn bảng thông số kỹ thuật).*
>    - *Mỗi chunk đều có metadata truy nguyên gồm `source_id`, `chunk_id`, `url`, `applicable_models` và `section`.*
>    - *Toàn bộ 2,164 chunks đã được nạp persistent vào **Vector Database ChromaDB** tại `data/chroma/`.*
> 
> 3. *Quan trọng nhất, hệ thống tuân thủ nghiêm ngặt **Rule 2.4 & ADR-003**: Có nguồn thì trả lời kèm link trích dẫn; nếu khoảng cách vector vượt ngưỡng ($> 0.70$) thì bắt buộc trả về trạng thái `NO_SOURCE` và chuyển chuyên viên (Staff Review), tuyệt đối không để LLM bịa đặt thông tin kỹ thuật."*

---

### PHẦN 3: BỘ DỮ LIỆU ĐÁNH GIÁ & BENCHMARK (NHÓM B) (1.5 phút)

> **Hành động:** Chuyển sang file `eval/results/report.md` và mở bảng metrics.
>
> **Lời thoại:**
> *"Khối công việc thứ 2 là **Nhóm B: Dataset Triage & Evaluation Benchmark** theo Mục 3 của kế hoạch.*
> 
> *Thay vì viết prompt cảm tính, em đã xây dựng một bộ test case chuẩn gồm **55 Triage cases** và **15 RAG FAQ cases**, bao quát cả 5 nhóm intent của khách hàng:*
> - *18 ca về Pin & Sạc (`charging_battery`).*
> - *16 ca về Sự cố xe & Dịch vụ (`service_incident`).*
> - *7 ca về Thông tin sản phẩm (`sales_general_info`).*
> - *6 ca Khiếu nại dịch vụ (`complaint_feedback` - bắt buộc duyệt HITL).*
> - *8 ca An toàn khẩn cấp & Tấn công ngoài luồng (`safety_adversarial_oos`).*
> 
> *Để tránh rò rỉ dữ liệu (Data Leakage), em đã tách độc lập thành 3 tập:*
> - *`triage_train_v1.jsonl` (10 cases dùng làm few-shot).*
> - *`triage_dev_v1.jsonl` (15 cases dùng tinh chỉnh rule).*
> - *`triage_test_v1.jsonl` (30 cases là tập mù độc lập hoàn toàn để chấm điểm).*
> 
> *Em đã viết script tự động `scripts/run_triage_eval.py` để chấm điểm trực tiếp trên Chatbot Agent. Kết quả đạt được rất ấn tượng:*
> - *Chỉ số **Critical Safety Recall** đạt **100.0%**: 100% các tình huống cháy khói, mất phanh đều được phát hiện ngay lập tức.*
> - *Chỉ số **Top-K Grounded Citation Rate** đạt **100.0%**: 100% câu hỏi tra cứu thông số/bảo hành đều trích xuất đúng nguồn chính thức.*
> - *Chỉ số **No-Source Compliance** đạt **100.0%**: Tuyệt đối không sinh ảo giác (hallucination) khi gặp câu hỏi ngoài phạm vi.*
> - *Thời gian phản hồi trung bình chỉ **1.31 giây** / lượt chat.*
> - *Toàn bộ bằng chứng log chi tiết từng case được lưu tại `eval/results/benchmark_run.json`."*

---

### PHẦN 4: HẠT NHÂN CHATBOT & BÀN GIAO API CONTRACT (1.5 phút)

> **Hành động:** Chuyển sang file `docs/create_api_contract.md`.
>
> **Lời thoại:**
> *"Khối công việc thứ 3 là **Xây dựng Chatbot AI Agent hoàn chỉnh và xuất bản API Contract** để bạn Frontend và Backend có thể tích hợp ngay:*
> 
> 1. *Em đã xây dựng module `src/agents/chatbot_agent.py` theo luồng 4 tầng:*
>    - *Tầng 1: **Hard Safety Guardrail**: Bắt nhanh các rủi ro độc lập (cháy, mất phanh, kẹt ga, ngập nước) để cấp cứu nạn và hotline `1900-232389` trước mà không phụ thuộc vào LLM.*
>    - *Tầng 2: **PII Sanitizer**: Tự động che số điện thoại, biển số xe thật.*
>    - *Tầng 3: **RAG Engine**: Tra cứu ChromaDB, trích xuất căn cứ từ nguồn chính thức.*
>    - *Tầng 4: **Grounded Answer**: Sinh câu trả lời kèm liên kết Citation URL chính thức; nếu không có nguồn thì trả về cờ `NO_SOURCE` + đề xuất Staff Review.*
> 
> 2. *Về **API Contract**, em đã tạo sẵn 2 endpoint tại `src/api/routes.py`:*
>    - *`POST /api/v1/chat`: Dành cho bạn Frontend cắm nhanh vào khung chat demo.*
>    - *`POST /api/v1/customer/chat`: Dành cho bạn Backend theo đúng chuẩn Response Envelope (`success`, `data`, `meta`) của tài liệu kiến trúc.*
> 
> 3. *Toàn bộ hệ thống kiểm thử tự động `pytest` gồm **37/37 unit tests đều PASS 100%** trong 3.5 giây, không có bất kỳ regression hay lỗi vặt nào."*

---

### PHẦN 5: LIVE DEMO MINH HỌA (1 phút)

> **Hành động:** Mở Terminal và chạy lệnh:
> ```bash
> .\.venv\Scripts\python.exe scripts/test_chatbot_demo.py
> ```
>
> **Lời thoại:**
> *"Em xin phép chạy nhanh demo qua 3 tình huống tiêu biểu nhất của hệ thống:*
> 
> - ***Case 1 (Tra cứu RAG có nguồn):*** *Khách hỏi: 'Thời hạn bảo hành pin xe VinFast VF 8 là bao lâu?' $\rightarrow$ Bot trả lời đúng 10 năm/200.000km và trích dẫn chuẩn URL bài viết bảo hành của VinFast.*
> - ***Case 2 (An toàn khẩn cấp):*** *Khách báo: 'Cứu tôi với xe đang chạy dưới gầm bốc khói khét lẹt' $\rightarrow$ Hard Safety Rule kích hoạt ngay, Priority lên Critical, cấp ngay chỉ dẫn dừng xe khẩn cấp và gọi hotline `1900-232389`.*
> - ***Case 3 (Chống bịa đặt - Anti-hallucination):*** *Khách hỏi câu ngoài hệ sinh thái: 'Giá vé máy bay Vietnam Airlines đi Đà Nẵng' $\rightarrow$ Bot kích hoạt Rule 2.4, thông báo không có trong tài liệu chính thức và tạo cờ `needs_staff_review: True`."*

---

### PHẦN 6: KẾT LUẬN & BƯỚC TIẾP THEO (30 giây)

> **Lời thoại:**
> *"Tóm lại, phần việc của AI Engineer cho giai đoạn này đã hoàn tất 100% mục tiêu:*
> - *Knowledge Base 2,164 chunks đạt chuẩn.*
> - *Bộ Benchmark Triage & RAG đạt 100% Critical Recall và 100% No-Source Compliance.*
> - *Core Agent & API Contract đã sẵn sàng trên nhánh `develop` để bạn Frontend và Backend tích hợp qua Swagger UI tại `http://localhost:8000/docs`.*
> 
> *Bước tiếp theo, em sẽ phối hợp cùng bạn Backend để tạo thêm dữ liệu hạt giống (Mock Seed Data cho User và Ticket) và hỗ trợ bạn Frontend gắn giao diện chat vào. Em rất mong nhận được nhận xét và góp ý từ anh/chị ạ!"*

---

## BỘ CÂU HỎI MENTOR CÓ THỂ HỎI & CÁCH TRẢ LỜI NGAY (CHEAT SHEET)

1. **Mentor hỏi: *"Lỡ con bot bịa ra thông tin sai về kỹ thuật xe thì sao?"***
   - **Trả lời:** *"Dạ thưa anh/chị, hệ thống kiểm soát bằng **Rule 2.4 & ADR-003**: Khi độ tương đồng vector $> 0.70$ hoặc gặp chủ đề ngoài phạm vi, hệ thống ép trạng thái `NO_SOURCE` và từ chối trả lời ngay ở tầng logic, hoàn toàn không cho phép LLM tự do suy đoán."*

2. **Mentor hỏi: *"Tại sao Critical Recall phải đạt 100%?"***
   - **Trả lời:** *"Dạ đối với ô tô điện, các nguy cơ như cháy pin, mất phanh, kẹt chân ga liên quan trực tiếp đến tính mạng người dùng. Do đó, em cài đặt tầng **Hard Safety Guardrail** bằng regex/mã tiền xử lý, chặn ngay lập tức mà không phụ thuộc vào độ trễ hay tính ngẫu nhiên của LLM."*

3. **Mentor hỏi: *"Tại sao chia tập dữ liệu thành train, dev, test?"***
   - **Trả lời:** *"Dạ để tránh hiện tượng Data Leakage. Tập `test` (30 cases) được giữ kín hoàn toàn, không đưa vào prompt hay few-shot để đảm bảo kết quả đo đạc độ chính xác phản ánh đúng năng lực thật của mô hình."*

4. **Mentor hỏi: *"Thời gian phản hồi 1.3 giây đã tối ưu chưa?"***
   - **Trả lời:** *"Dạ 1.3 giây là tốc độ rất tốt cho RAG pipeline cục bộ (truy vấn ChromaDB + guardrails). Khi đưa vào production thực tế, chúng ta có thể bổ sung thêm Semantic Cache cho các câu hỏi phổ biến để đưa độ trễ về dưới 0.3 giây."*
