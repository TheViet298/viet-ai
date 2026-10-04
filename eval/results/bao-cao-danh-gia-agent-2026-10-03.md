# Báo cáo đánh giá hệ thống Agent

**Ngày báo cáo:** 03/10/2026 — múi giờ Việt Nam (Asia/Saigon)  
**Tài liệu triển khai:** `2026-10-01-complete-agent-system.md`  
**Phạm vi:** Kiểm thử chức năng và đánh giá chất lượng hệ thống Agent trên dữ liệu kiểm thử hiện có.

## 1. Kết quả tổng quan

Hệ thống đã được triển khai và đánh giá bằng 82 bài kiểm thử hồi quy cùng bộ eval gồm 45 tình huống. Các bài kiểm thử hồi quy đều đạt, nhưng kết quả eval chưa đáp ứng đầy đủ mục tiêu MVP.

Chế độ offline đạt 3/7 chỉ số mục tiêu. Chế độ online kết hợp cơ chế dự phòng đạt 2/7 chỉ số. Các điểm cần cải thiện gồm phân loại yêu cầu, định tuyến xử lý, trích dẫn có căn cứ và quyết định chuyển nhân viên xem xét. Chế độ online còn vượt mục tiêu về thời gian phản hồi.

Kết quả này xác nhận hệ thống đã có khả năng chạy và được kiểm thử; chưa đủ cơ sở để kết luận sẵn sàng vận hành thực tế.

## 2. Phạm vi và phương pháp đánh giá

Mỗi chế độ được đánh giá trên cùng bộ 45 tình huống:

- **30 tình huống triage:** kiểm tra phân loại yêu cầu, định tuyến, nhận diện nguy hiểm và nhu cầu nhân viên xem xét.
- **15 tình huống RAG:** kiểm tra câu trả lời dựa trên tài liệu và cách xử lý khi thiếu nguồn phù hợp.

**Offline:** tắt Gemini, sử dụng phân loại theo quy tắc và truy xuất từ kho Chroma cục bộ thật. Offline không có nghĩa là tắt truy xuất tài liệu.

**Online kết hợp dự phòng:** bật Gemini và sử dụng cùng kho Chroma. Khi lời gọi model không cung cấp kết quả hợp lệ trong giới hạn xử lý, hệ thống dùng cơ chế dự phòng. Vì vậy, báo cáo online phản ánh hành vi của toàn bộ cấu hình này, không phải chất lượng riêng của Gemini.

Số liệu được tính từ đầu ra thực tế của luồng Agent. Bộ mẫu dùng để tính từng chỉ số khác nhau: 1 tình huống nguy hiểm nghiêm trọng, 10 tình huống cần nguồn, 5 tình huống không có nguồn hoặc cần từ chối theo chính sách, và 30 tình huống đánh giá chuyển nhân viên.

## 3. Bảng kết quả

| Chỉ số | Mục tiêu MVP | Offline | Kết luận offline | Online + dự phòng | Kết luận online |
|---|---:|---:|---|---:|---|
| Tỷ lệ nhận diện tình huống nguy hiểm nghiêm trọng | 100% | 100% | Đạt | 100% | Đạt |
| Độ chính xác phân loại yêu cầu | ≥ 85% | 76,67% | Chưa đạt | 70% | Chưa đạt |
| Độ chính xác định tuyến xử lý | ≥ 80% | 60% | Chưa đạt | 56,67% | Chưa đạt |
| Tỷ lệ câu trả lời có trích dẫn đáp ứng tiêu chí đánh giá | ≥ 85% | 20% | Chưa đạt | 20% | Chưa đạt |
| Tỷ lệ xử lý đúng khi thiếu nguồn hoặc cần từ chối | ≥ 80% | 100% | Đạt | 100% | Đạt |
| Thời gian phản hồi trung bình | ≤ 2,5 giây | 0,201 giây | Đạt | 11,228 giây | Chưa đạt |
| Mức độ khớp nhãn về chuyển nhân viên xem xét | ≥ 85% | 70% | Chưa đạt | 70% | Chưa đạt |

Phân loại yêu cầu đúng 23/30 tình huống ở chế độ offline và 21/30 ở chế độ online. Định tuyến đúng lần lượt 18/30 và 17/30. Chỉ số trích dẫn đạt ở 2/10 tình huống cần nguồn; quyết định chuyển nhân viên khớp nhãn ở 21/30 tình huống trong cả hai chế độ.

## 4. Kiểm tra tích hợp Gemini

Kết nối Gemini và một lời gọi triage có đầu ra cấu trúc đã được kiểm tra thành công với `gemini-3.8-flash`. Model cấu hình trước đó, `gemini-2.5-flash`, bị provider thông báo không còn khả dụng cho người dùng mới.

Trong bộ eval online, hệ thống ghi nhận **6 sự kiện LLM có đầu ra được phân tích thành công**. Đây là số sự kiện gọi model, không phải số tình huống hoàn tất hoàn toàn bằng Gemini. Một tình huống có thể gọi model ở nhiều bước.

Lần kiểm tra provider sau bộ eval trả về `GoogleRateLimitError`, xác nhận có hạn chế quota hoặc tốc độ gọi API. Tuy nhiên, dữ liệu hiện có chưa đủ để quy toàn bộ các lần dùng dự phòng cho nguyên nhân này. Cần đo riêng lỗi provider, quá thời gian và lỗi cấu trúc đầu ra trong lần đánh giá tiếp theo.

Khóa API được lưu trong `.env` cục bộ, được Git bỏ qua và không đưa vào báo cáo. Việc gửi trace lên dịch vụ đám mây đã được tắt trong quá trình kiểm tra này.

## 5. Kiểm thử chức năng

Kết quả kiểm thử hồi quy gần nhất: **82/82 bài đạt**. Kiểm tra Ruff đã đạt trong đợt xác minh triển khai; kiểm tra khác biệt Git sau cập nhật báo cáo không phát hiện lỗi khoảng trắng.

Các nhóm hành vi đã được kiểm thử gồm bảo vệ phản hồi khẩn cấp, giới hạn hỏi làm rõ, lưu phiên và hồ sơ, kiểm soát quyền truy cập, vòng đời xử lý của nhân viên, kiểm tra nguồn RAG, che thông tin cá nhân và cơ chế dự phòng khi provider gặp lỗi.

Kiểm thử chức năng đạt không đồng nghĩa với việc chất lượng câu trả lời đã đạt mục tiêu eval.

## 6. Giới hạn khi diễn giải kết quả

- **Mẫu nguy hiểm còn ít:** tỷ lệ 100% chỉ dựa trên một tình huống nghiêm trọng; chưa thể suy rộng cho mọi tình huống an toàn.
- **Đánh giá trích dẫn có phạm vi hẹp:** tiêu chí kiểm tra nguồn kỳ vọng và từ khóa trong câu trả lời, chưa chứng minh toàn bộ nội dung đúng về ngữ nghĩa.
- **Một số nhãn có thể xung đột chính sách:** cần đối chiếu từng tình huống với quy định bắt buộc chuyển nhân viên; không nên giảm mức bảo vệ chỉ để tăng điểm.
- **Online có nhiều lần dùng dự phòng:** kết quả chưa đại diện cho một lần chạy mà tất cả lời gọi Gemini đều thành công.
- **Chưa xác minh đầy đủ môi trường vận hành:** xác thực sản xuất, trace đám mây và triển khai API thực tế cần được kiểm tra riêng. Điểm dịch vụ mẫu vẫn là dữ liệu minh họa.

## 7. Đề xuất cải thiện

1. **Rà soát từng tình huống sai:** đối chiếu đầu vào, nhãn kỳ vọng, kết quả Agent và chính sách xử lý để phân biệt lỗi triển khai với lỗi nhãn.
2. **Ưu tiên chất lượng RAG:** kiểm tra độ phủ tài liệu, nguồn kỳ vọng, điều kiện lọc và nội dung truy xuất cho 8/10 tình huống chưa đạt tiêu chí trích dẫn.
3. **Cải thiện phân loại và định tuyến:** bổ sung trường hợp biên từ các lỗi đã xác nhận; chạy lại bộ kiểm thử và eval sau mỗi thay đổi.
4. **Đo rõ lỗi tích hợp model:** thống kê tỷ lệ thành công, lỗi quota, quá thời gian, lỗi phân tích đầu ra và số lần dùng dự phòng; điều chỉnh tần suất gọi theo quota thực tế.
5. **Mở rộng bộ đánh giá:** bổ sung tình huống nguy hiểm, hội thoại nhiều lượt và kiểm tra đúng nội dung bằng rà soát của con người.

## 8. Kết luận

Hệ thống đã hoàn tất triển khai chức năng trong phạm vi hiện tại, có kết quả kiểm thử hồi quy đạt và có báo cáo eval đo từ đầu ra thực tế. Tuy nhiên, chất lượng phân loại, định tuyến, trích dẫn và chuyển nhân viên vẫn dưới mục tiêu; cấu hình online còn chịu hạn chế provider và độ trễ cao.

Đề xuất tiếp tục cải thiện theo các tình huống sai đã ghi nhận, sau đó chạy lại eval trước khi xác nhận đạt MVP.

## 9. Tài liệu đối chiếu

- [Báo cáo offline gốc](agent/agent_report.md)
- [Kết quả từng tình huống offline](agent/agent_results.json)
- [Báo cáo online gốc](agent-online/agent_report.md)
- [Kết quả từng tình huống online và bằng chứng tích hợp](agent-online/agent_results.json)
- [Hướng dẫn hệ thống Agent](../../docs/guide/agent-system.md)

