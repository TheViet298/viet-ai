# Báo cáo kiểm thử MVP: Gate 2

**Dự án:** VinFast ServiceFlow AI (P-142)  
**Nhánh:** `feature/agent-long`  
**Commit kiểm thử:** `3da9eccdedc92bd751b9675f7892951d8394b599`  
**Thời gian:** 04/10/2026, từ 23:23 đến 23:24 (giờ Việt Nam, UTC+7)

## 1. Mục đích kiểm thử

Em chạy 5 tình huống thực tế để kiểm tra luồng nhận yêu cầu, phản hồi khách hàng và tạo hồ sơ cho nhân viên. Báo cáo ghi nhận lại toàn bộ dữ liệu gửi/nhận qua API cùng các vấn đề cần xử lý tiếp.

Các request được gửi trực tiếp tới API backend local (`http://127.0.0.1:8013`) qua tài khoản Customer và Staff demo, sử dụng database SQLite kiểm thử độc lập. Quá trình kiểm thử không can thiệp code xử lý, không mock phản hồi và không đè lên database chính của dự án. Đợt này chỉ kiểm tra tầng API backend, chưa thao tác trực tiếp trên giao diện web hoặc quay chụp màn hình.

## 2. Kết quả tổng hợp

| Ca | Nội dung kiểm tra | Kết quả | Nhận xét chính |
| --- | --- | --- | --- |
| TC01 | Báo lỗi sạc, nhân viên duyệt, khách xem tiến độ | FAIL: còn lỗi dữ kiện | Luồng bàn giao và cập nhật trạng thái chạy được, nhưng địa điểm khách nhập bị đổi thành tên mặc định. |
| TC02 | Khách thiếu thông tin sau 2 lượt hỏi | FAIL: còn lỗi dữ kiện | Hệ thống dừng hỏi đúng 2 lượt và tạo hồ sơ thiếu thông tin, nhưng tự gán dòng xe VF8 dù khách chưa nói. |
| TC03 | Xe bốc khói khi đang sạc | FAIL: nội dung cần sửa | Phân loại khẩn cấp chính xác, nhưng câu trả lời và hướng dẫn chưa khớp với tình huống xe đỗ sạc. |
| TC04 | Khách khiếu nại dịch vụ | PASS trong phạm vi tiếp nhận | Hồ sơ khiếu nại được tạo đầy đủ nội dung để nhân viên tiếp nhận rà soát. |
| TC05 | Giải thích cảnh báo và tra cứu bảo hành | PASS sau khi thử lại | Lần tra cứu bảo hành đầu tiên bị timeout, lần gửi lại trả đủ nội dung, nguồn trích dẫn và trace LLM thật. |

Một ca chỉ được tính là PASS khi đáp ứng đúng tiêu chí nghiệp vụ, không dựa vào mã HTTP 200. Đợt kiểm thử ghi nhận 1 ca đạt ngay (TC04), 1 ca đạt sau khi gửi lại (TC05) và 3 ca còn lỗi xử lý dữ kiện hoặc nội dung (TC01, TC02, TC03). Do đó, hệ thống chưa đủ điều kiện để nghiệm thu toàn bộ phạm vi Gate 2.

## 3. Chi tiết từng tình huống

### TC01: Báo lỗi sạc và theo dõi hồ sơ

**Mong đợi:** Hệ thống giữ đúng dữ kiện khách nhập, tạo hồ sơ để nhân viên duyệt và cập nhật trạng thái tương ứng phía khách hàng.

**Input:**

> Xe VF8 của tôi không nhận sạc tại trụ P01, mã lỗi CC01, pin còn 25%, xe đang đỗ tại trạm demo A.

**Output thực tế:**

> Dạ VinFast đã ghi nhận sự cố sạc của xe VF8:
> 📍 **Vị trí trạm:** Trạm sạc VinFast công cộng
> 🔌 **Trụ sạc:** TRỤ P01
> ⚠️ **Mã lỗi:** CC01
> 
> Hệ thống đã tự động tạo hồ sơ hỗ trợ (Mã: CASE-20261004-001) và chuyển dữ liệu trực tiếp tới Chuyên viên Kỹ thuật trạm sạc. Anh/chị vui lòng theo dõi cập nhật tiến độ giải quyết trực tiếp trên màn hình này ạ.

**Kết quả kiểm tra:**

- Hệ thống tạo hồ sơ `CASE-20261004-001`, phân loại `Charging/Battery`, mức ưu tiên `HIGH`, trạng thái `Staff Reviewing`.
- API nhân viên đọc được đầy đủ thông tin: dòng xe VF8, mức pin 25%, trụ P01 và mã lỗi CC01.
- Sau khi nhân viên bấm duyệt (`APPROVE`), API phía khách chuyển trạng thái sang `In Progress` cho cùng mã hồ sơ.
- Tuy nhiên, chuỗi "trạm demo A" bị thay bằng "Trạm sạc VinFast công cộng" ở cả tin nhắn phản hồi lẫn tóm tắt sự cố.

**Đánh giá:** Luồng nghiệp vụ từ khách sang nhân viên và cập nhật trạng thái hoạt động thông suốt. Ca này vẫn tính FAIL vì hệ thống làm sai lệch địa điểm khách cung cấp. Phản hồi được sinh từ logic backend có sẵn, chưa ghi nhận trace LLM.

**Minh chứng:** [Input, response, hồ sơ nhân viên và trạng thái khách](evidence/gate2/TC01-response.json).

### TC02: Khách chưa có đủ thông tin

**Mong đợi:** Hệ thống hỏi làm rõ tối đa 2 lượt rồi tạo hồ sơ `Needs Information`, đồng thời ghi nhận rõ ràng các trường thông tin còn thiếu.

**Input và diễn biến:**

1. `Xe tôi không sạc được.`
2. Sau câu hỏi thứ nhất: `Xe vẫn không sạc được, tôi chưa biết mã trụ và không nhớ dòng xe.`
3. Sau câu hỏi thứ hai: `Xe vẫn không sạc được, tôi vẫn chưa có thêm thông tin.`

**Output ở lượt hỏi thứ nhất và thứ hai:**

> Dạ em ghi nhận xe VF8 đang gặp vấn đề kỹ thuật liên quan đến sạc/vận hành. Anh/chị có thể cho em biết trạm sạc, số trụ hoặc mã lỗi hiển thị trên táp-lô (ví dụ: CC01, 0x41) không ạ? (Anh/chị cũng có thể tải ảnh màn hình để em nhận diện sơ bộ).

**Output sau 2 lượt hỏi:**

> Hệ thống đã tạo hồ sơ ghi nhận (Mã: CASE-20261004-002). Do chưa đủ một số dữ kiện kỹ thuật, hồ sơ được chuyển sang hàng đợi nhân viên hỗ trợ; nhân viên sẽ kiểm tra hoặc gửi yêu cầu bổ sung thông tin cho anh/chị.

**Kết quả kiểm tra:** Hệ thống tạo hồ sơ `CASE-20261004-002` ở trạng thái `Needs Information`. Giao diện nhân viên hiển thị đúng lịch sử hội thoại cùng danh sách trường còn thiếu gồm `error_code`, `station_id` và `current_soc`. Điểm lỗi là hệ thống tự điền dòng xe VF8 vào hồ sơ dù khách đã nói rõ là không nhớ, và request cũng không kèm `client_context`.

**Đánh giá:** Logic ngắt sau 2 lượt hỏi hoạt động đúng quy định, nhưng bị FAIL về độ chính xác của dữ kiện. Khi khách chưa biết dòng xe, hồ sơ phải ghi nhận là chưa rõ thay vì tự lấy giá trị mặc định. Ca này chưa có trace LLM thành công.

**Minh chứng:** [Ba lượt hội thoại và hồ sơ thiếu thông tin](evidence/gate2/TC02-response.json).

### TC03: Xe bốc khói khi đang sạc

**Mong đợi:** Hệ thống nhận diện tình huống khẩn cấp, đẩy hồ sơ cho nhân viên ngay và đưa ra hướng dẫn an toàn phù hợp với bối cảnh xe đang đỗ sạc. Không thông báo đã kích hoạt hành động bên ngoài nếu thực tế chưa làm.

**Input:**

> Xe VF8 của tôi đang bốc khói và có mùi khét ở khu vực pin khi sạc tại bãi xe demo A.

**Output thực tế:**

> Dạ VinFast đã ghi nhận tình trạng khẩn cấp của xe VF8. Hệ thống đã tự động tạo hồ sơ khẩn cấp (Mã: CASE-20261004-003) và kích hoạt đường dây nóng tới kỹ thuật viên.
> 
> ⚠️ HƯỚNG DẪN AN TOÀN NGAY LẬP TỨC: Anh/chị vui lòng bật đèn khẩn cấp (Hazard), từ từ tấp xe vào làn dừng khẩn cấp an toàn và gọi hotline cứu hộ 1900-232389.

**Kết quả kiểm tra:** Hệ thống tạo hồ sơ `CASE-20261004-003`, mức ưu tiên `CRITICAL`, trạng thái `Staff Reviewing`. Cờ `show_emergency_banner` trả về `true` và nhân viên nhìn thấy hồ sơ trên hàng đợi.

**Điểm còn lỗi:** Tin nhắn thông báo hệ thống đã "kích hoạt đường dây nóng tới kỹ thuật viên", nhưng backend thực tế chưa có cơ chế kết nối cuộc gọi. Lời khuyên "từ từ tấp xe vào làn dừng khẩn cấp" và nội dung điều động cứu hộ cao tốc trong brief cũng không phù hợp với tình huống xe đang đứng sạc ở bãi xe.

**Đánh giá:** FAIL về nội dung hướng dẫn. Cơ chế kích hoạt khẩn cấp bằng rule hoạt động tốt, nhưng câu chữ phản hồi cần sửa lại sát thực tế hơn. Ca này xử lý hoàn toàn bằng rule an toàn trước khi vào LLM.

**Minh chứng:** [Phản hồi khẩn cấp và hồ sơ nhân viên](evidence/gate2/TC03-response.json).

### TC04: Khiếu nại dịch vụ

**Mong đợi:** Ghi nhận phản ánh khách hàng, tạo hồ sơ chuyển nhân viên và giữ nguyên vẹn nội dung khiếu nại; không tự ý nhận lỗi hay hứa hẹn bồi thường ngoài thẩm quyền.

**Input:**

> Tôi muốn khiếu nại thái độ nhân viên tại xưởng demo A. Tôi đã chờ 2 giờ nhưng chưa được hỗ trợ, mong có người phụ trách liên hệ trên ứng dụng.

**Output thực tế:**

> Dạ em rất tiếc về trải nghiệm chưa thuận tiện của anh/chị. Hệ thống đã ghi nhận phản hồi vào hồ sơ hỗ trợ chuyên trách (Mã: CASE-20261004-004) và chuyển ngay đến bộ phận Chăm sóc Khách hàng để rà soát, xử lý ưu tiên. Anh/chị vui lòng theo dõi cập nhật trực tiếp tại đây nhé ạ.

**Kết quả kiểm tra:** Tạo hồ sơ `CASE-20261004-004`, nhóm `Complaint/Feedback`, trạng thái `Staff Reviewing`. Nhân viên xem được đầy đủ chi tiết gồm xưởng demo A và thời gian chờ 2 giờ. Câu trả lời của bot giữ chừng mực, không cam kết bồi thường.

**Đánh giá:** PASS trong phạm vi tiếp nhận ban đầu và bàn giao cho nhân viên. Đợt test chưa bao gồm khâu nhân viên xử lý tiếp sau đó. Trường dòng xe trong hồ sơ vẫn bị gán mặc định là VF8 như ở TC02. Ca này chạy qua rule tiếp nhận, chưa kích hoạt LLM.

**Minh chứng:** [Phản hồi và nội dung khiếu nại phía nhân viên](evidence/gate2/TC04-response.json).

### TC05: Giải thích cảnh báo và tra cứu bảo hành

**Mong đợi:** Hệ thống tra cứu tài liệu chính xác, trích dẫn đúng nguồn và có dữ liệu trace chứng minh gọi LLM thật thành công. Nếu gặp lỗi kết nối phải ghi nhận rõ ràng.

**Lượt 1 (hỏi ý nghĩa cảnh báo):**

> Biểu tượng con rùa trên xe VF8 nghĩa là gì?

**Output:**

> Biểu tượng con rùa (Turtle Mode) thường báo xe đang giới hạn công suất, nên khả năng tăng tốc có thể giảm. Đây là cơ chế bảo vệ; pin yếu, nhiệt độ bất thường hoặc lỗi hệ thống có thể là những nguyên nhân, nhưng chỉ biểu tượng này chưa đủ để xác định nguyên nhân của xe cụ thể.
> 
> Đây là kiến thức chung về xe, chưa đối chiếu sổ tay đúng mẫu/đời xe; không phải kết luận chẩn đoán.

Câu trả lời nêu rõ đây là thông tin chung và không kèm trích dẫn nguồn, nên em không dùng lượt này làm minh chứng cho năng lực tra cứu sổ tay VF8 của LLM.

**Lượt 2 (hỏi thời hạn bảo hành):**

> Thời hạn bảo hành xe VinFast VF8 tiêu chuẩn là bao nhiêu năm hoặc bao nhiêu km?

**Output lần đầu:**

> Hệ thống tra cứu hiện chưa hoàn tất được yêu cầu. Tôi sẽ chuyển chuyên viên kiểm tra.
> 
> Hệ thống đã ghi nhận câu hỏi để chuyên viên dịch vụ kiểm tra và phản hồi sớm nhất đến anh/chị.
> 
> Mã hồ sơ: CASE-20261004-001.

Lần gọi này kéo dài 5,219 giây và trả về trace `retrieval_status=TIMEOUT`. Dù câu trả lời có nhắc đến mã hồ sơ CASE-20261004-001, trường `case_id` trong payload lại mang giá trị `null`, nghĩa là hồ sơ thực tế chưa được tạo trên hệ thống.

**Lượt 3 (hỏi lại về thời hạn bảo hành):**

> Theo tài liệu VinFast:
> 
> Thời hạn bảo hành xe VinFast VF 8 theo điều kiện sử dụng tiêu chuẩn là 10 năm hoặc 200.000 km, tùy điều kiện nào đến trước.

**Kết quả sau khi thử lại:**

- API trả kết quả `FAQ_ANSWER` sau 4,125 giây.
- Trích dẫn nguồn `SRC-002` với tiêu đề "Chính sách bảo hành xe ô tô VinFast".
- Trace ghi nhận: `kind=llm`, `node=rag_qa`, `gate_decision=parsed`, model `gemini-3.8-flash`.
- Thống kê tài nguyên: 697 input tokens và 310 output tokens.

**Đánh giá:** PASS sau khi thử lại đối với luồng tra cứu tài liệu và dùng LLM tạo câu trả lời kèm citation. Đây là ca duy nhất ghi nhận bằng chứng gọi LLM thật trong app. Do lượt đầu bị timeout và mã case trả về chưa nhất quán với database, luồng tra cứu này vẫn cần tối ưu thêm về độ ổn định.

**Minh chứng:** [Cả ba lượt, response và trace LLM](evidence/gate2/TC05-response.json).

## 4. Kế hoạch khắc phục và hoàn thiện

Từ các lỗi ghi nhận trong đợt test, em ưu tiên xử lý các đầu việc sau:

1. Sửa parser trích xuất dữ kiện để giữ nguyên địa điểm khách cung cấp; không tự động điền giá trị mặc định cho các trường chưa xác định (đặc biệt là dòng xe).
2. Viết lại mẫu câu phản hồi sự cố khẩn cấp: bỏ câu tuyên bố kích hoạt hotline khi hệ thống chưa tích hợp, đồng thời phân biệt hướng dẫn dừng xe trên đường với hướng dẫn khi xe đang đỗ tại trạm sạc.
3. Tối ưu thời gian phản hồi của bước tra cứu RAG để tránh chạm ngưỡng timeout 5 giây, đồng thời sửa logic tạo case dự phòng khi tra cứu thất bại để trường `case_id` khớp với nội dung thông báo.
4. Chạy lại kiểm thử toàn bộ 5 ca sau khi chỉnh sửa code, sau đó tiến hành kiểm thử trên giao diện web để thu thập video và ảnh chụp màn hình chứng minh luồng end-to-end.

## 5. Danh mục file minh chứng

Toàn bộ file JSON lưu vết thời điểm gọi, dữ liệu request/response và trace LLM được lưu trong thư mục `docs/evidence/gate2/`. Các dữ liệu nhạy cảm như token và API key đều đã được loại bỏ:

- [TC01: Lỗi sạc và nhân viên duyệt](evidence/gate2/TC01-response.json)
- [TC02: Thiếu thông tin](evidence/gate2/TC02-response.json)
- [TC03: Khẩn cấp](evidence/gate2/TC03-response.json)
- [TC04: Khiếu nại](evidence/gate2/TC04-response.json)
- [TC05: Tra cứu và LLM thật](evidence/gate2/TC05-response.json)

Thư mục `evidence/gate2/develop-precheck/` lưu kết quả chạy thử trước đó trên commit `39e6715` của nhánh `develop` (từng gặp lỗi thiếu import và timeout 10 giây). Các file này chỉ dùng để đối chiếu lịch sử kiểm thử, không tính vào kết quả của nhánh `feature/agent-long`.
