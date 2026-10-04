# Trả lời kiến thức về xe

Luồng chat phân biệt kiến thức chung về xe với thông tin riêng của sản phẩm.

- Câu hỏi giải thích khái niệm chung (ví dụ con rùa vàng, ABS, TPMS, BMS,
  phanh tái sinh, ADAS, SOC/SOH, sạc AC/DC, dung lượng pin/kWh, mô-men xoắn)
  không bắt buộc có nguồn VinFast. Câu trả lời ghi rõ
  là kiến thức chung, chưa đối chiếu mẫu/đời xe và không phải chẩn đoán.
- Các khái niệm phổ biến có phần giải thích ngắn trong
  `src/services/vehicle_knowledge.py`, hoạt động cả khi LLM không sẵn sàng.
  Những câu hỏi chung khác dùng luồng hội thoại và prompt `general`.
- Câu so sánh trả lời cả hai khái niệm; câu hỏi tiếp như “Nó khác SOC thế nào?”
  tham chiếu câu hỏi kiến thức trước đó. “Dung lượng pin là gì?” là định nghĩa;
  “Dung lượng pin VF8 bao nhiêu?” vẫn cần nguồn thông số đúng mẫu xe.
- Giá, thông số, chính sách và bảo hành vẫn cần nguồn đã xác thực. Không
  dùng kiến thức chung để suy ra cam kết hay số liệu riêng từng mẫu xe.
- Xe đang gặp sự cố, ảnh cảnh báo và tình huống nguy hiểm vẫn qua luồng
  tiếp nhận sự cố; một câu hỏi định nghĩa không tự tạo hồ sơ.

Câu tư vấn nhiều ý được tách thành thông tin dòng xe, giá và lái thử.
Mỗi phần truy xuất riêng và được trình bày riêng, kể cả khi không có nguồn.
Tổng quan nhiều dòng xe không lọc theo bộ chọn VF8; mẫu xe được viết trực
tiếp trong câu hỏi có ưu tiên cao hơn bộ chọn. Dữ liệu giá hoặc đăng ký
lái thử chưa có trong kho sẽ được thông báo rõ, không dùng câu trả lời
viết sẵn hoặc nguồn chưa xác thực.

RAG loại đoạn không có chủ đề cần trả lời. Ví dụ câu hỏi con rùa không
được dùng đoạn giữ làn/HUD chỉ trùng từ “biểu tượng màu vàng”. Khi bật LLM
mà sinh câu trả lời thất bại, không chép nguyên đoạn trích cho người dùng.

Khi API chat lỗi hoặc trả envelope không có dữ liệu, frontend báo chưa nhận được
phản hồi và yêu cầu gửi lại. Không tự tạo câu trả lời mẫu, nguồn trích dẫn, mã hồ sơ
hoặc thông báo đã gọi cứu hộ. Banner khẩn cấp cục bộ vẫn hoạt động.

Các timeout cấu hình: `AGENT_TURN_TIMEOUT_S=20`,
`AGENT_LLM_TIMEOUT_S=12`, `RAG_RETRIEVAL_TIMEOUT_S=5`. Luồng khẩn cấp vẫn
kiểm tra trước và không chờ LLM. Cấu hình timeout không sửa được lỗi 503
từ nhà cung cấp; loại lỗi vẫn được ghi trong trace, không chứa khóa API.

Kiểm thử: `tests/test_agents/test_knowledge_answer_regressions.py`,
`tests/test_agents/test_vehicle_general_knowledge.py`,
`tests/test_api/test_knowledge_sales.py` và các test an toàn hiện có.
