# Câu chưa trả lời được và memory xuyên phiên — 19/10/2026

## Kết luận

- Trong 540 lượt test cũ: **219 lượt / 30 câu khác nhau chưa đáp ứng đủ**. Bộ đếm mẫu ban đầu thấy 186/25; rà soát thủ công bổ sung câu nối tiếp “chưa có nguồn đủ” và phần tiếng Anh “could not retrieve”. Model bị tắt và index mỗi test không có dữ liệu; không dùng số này làm tỷ lệ lỗi production.
- Đã đo lại **284 lượt** có/không có bản sao index, model tắt; thêm **63 lượt bật provider cấu hình thật**, ghi nhận **28 sự kiện model parse thành công**.
- 56 lượt provider gồm 52 câu độc lập phủ các nhóm nghiệp vụ và 4 lượt chuyển chủ đề. Có 20 câu thông tin chưa được trả lời, 1 câu nhiều ý trả lời một phần, 1 câu sai intent và 1 câu sai ngôn ngữ. Đây là tập probe chọn lọc, không phải benchmark accuracy ngẫu nhiên.
- Chuỗi sự cố 7 lượt bổ sung xác nhận 2 lượt đính chính/phủ định vẫn trả fallback. Các tình huống tạo hồ sơ đều dùng DB/người dùng tổng hợp; không gửi cứu hộ hay đặt lịch bên ngoài.
- 11 khả năng memory được thử với một Python process mới cho từng request: **5 đạt, 6 chưa đạt**. Có 4 lỗi recall xuyên phiên ở chế độ tắt model và 1 lần đối chiếu bật provider; lỗi còn lại là câu nhắc xe tự mô tả thành sự cố.

## Phân biệt môi trường

| Môi trường | Provider | Index |
| --- | --- | --- |
| Checkout audit khi chạy unit test | Fixture tắt | Chroma tạm không có index |
| Checkout viet-ai cục bộ đã kiểm tra cấu hình | Không có key cấu hình | Không có index ở đường dẫn mặc định |
| Workspace P-142 gốc | Có key cấu hình | `data/chroma-catalog-colors-v1`, 2.196 chunks |
| Probe có dữ liệu | Dùng cấu hình provider từ workspace gốc | SQLite backup nhất quán + bản sao HNSW/parent-map trong `.test-runs/answer-gap-index` |

Không suy diễn cấu hình Vercel từ các checkout trên. Model/key không được ghi ra báo cáo; tracing cloud tắt. Toàn bộ logic production được giữ nguyên trong lượt audit này.

## 30 câu chưa đáp ứng đủ trong lượt test trước

Tần suất có lặp do cùng bước được chạy ở các độ dài/cách gửi khác nhau. Câu nối tiếp phải được đọc trong ngữ cảnh gốc.

| # | Câu hỏi | Lượt fallback | Loại phản hồi lúc test cũ |
| --- | --- | ---: | --- |
| 1 | Chính sách bảo hành pin và lịch bảo dưỡng định kỳ | 9 | retrieval_unavailable |
| 2 | VF8 Plus có màu gì? | 9 | retrieval_unavailable |
| 3 | Biểu phí sạc tại trạm sạc công cộng | 15 | retrieval_unavailable |
| 4 | Ứng dụng VinFast có tính năng gì? | 15 | retrieval_unavailable |
| 5 | Không phải trụ P01, trụ P02 | 6 | retrieval_unavailable |
| 6 | Xe không còn báo CC01 nữa | 6 | retrieval_unavailable |
| 7 | Tôi đã dừng ở nơi an toàn | 6 | retrieval_unavailable |
| 8 | Tôi muốn hỏi bảo hành VF8 | 3 | retrieval_unavailable |
| 9 | Còn VF3 thì sao? | 3 | insufficient_evidence |
| 10 | Lịch bảo dưỡng VF3 là gì? | 3 | retrieval_unavailable |
| 11 | VF7 Plus có màu gì? | 12 | retrieval_unavailable |
| 12 | What colors are available for the VF8 Plus? | 9 | presentation_failed |
| 13 | What is the on-road price of the VF8 Plus? | 9 | presentation_failed |
| 14 | How long is the VF8 warranty? | 9 | presentation_failed |
| 15 | Bảo hành pin cao áp VF8 bao lâu? | 6 | retrieval_unavailable |
| 16 | What is the maintenance schedule for the VF8? | 6 | presentation_failed |
| 17 | Còn VF5 thì sao? | 12 | insufficient_evidence |
| 18 | Please explain battery warranty and scheduled maintenance. | 6 | presentation_failed |
| 19 | How far can the VF8 travel on a full charge? | 6 | presentation_failed |
| 20 | Dung lượng pin VF8 là bao nhiêu? | 12 | insufficient_evidence |
| 21 | How much does it cost to charge the VF8? | 6 | presentation_failed |
| 22 | Please explain public charging, charging fees and VinFast app features. | 6 | partial_english_retrieval |
| 23 | Hướng dẫn cách sạc tại trạm công cộng và biểu phí sạc | 6 | retrieval_unavailable |
| 24 | What will the weather be like tomorrow? | 3 | presentation_failed |
| 25 | Chính sách bảo hành pin VF8 bao lâu? | 6 | retrieval_unavailable |
| 26 | Pin cao áp, không phải ắc quy 12V | 6 | insufficient_evidence |
| 27 | Không phải pin cao áp, tôi hỏi ắc quy 12V | 6 | insufficient_evidence |
| 28 | Lịch bảo dưỡng định kỳ VF8 là gì? | 6 | retrieval_unavailable |
| 29 | VF8 sạc bao lâu? | 6 | retrieval_unavailable |
| 30 | VF8 đi được bao xa một lần sạc? | 6 | insufficient_evidence |

Trong đó 3 lượt câu thời tiết tiếng Anh là lỗi trình bày khi model bị tắt; từ chối nội dung ngoài phạm vi vốn là hành vi đúng. Các câu khác nhau có thể cùng nguyên nhân; không cộng số câu của bảng này với bảng probe mới. Ngoài ra, bảng so sánh có ô dung lượng VF3 “Chưa có dữ liệu” và tư vấn VF7 có cấu hình Plus AWD “Chưa có giá xác thực”; đó là trường dữ liệu thiếu, không coi toàn bộ phản hồi so sánh/tư vấn đều thất bại.

## Các ca chưa đáp ứng hoặc trả lời sai khi bật provider

Không coi HTTP 200, có citations, `final_outcome=success` hay pytest đo lường PASS là bằng chứng đúng/đủ nội dung. Các case không được gắn cờ vẫn chưa được chứng nhận đúng factual toàn bộ.

| Pha / # | Câu hỏi | Kết quả review | Chẩn đoán truy xuất |
| --- | --- | --- | --- |
| live-broad-and-context / 1 | Thời hạn bảo hành xe VinFast VF 8 tiêu chuẩn là bao nhiêu năm hoặc bao nhiêu km? | unanswered | unsupported_numeric_claim |
| live-broad-and-context / 2 | Thời hạn bảo hành xe VinFast VF 5 là bao nhiêu năm? | unanswered | unsupported_numeric_claim |
| live-broad-and-context / 7 | Chu kỳ bảo dưỡng định kỳ đầu tiên của xe ô tô điện VinFast là ở mốc nào? | unanswered | no_eligible_evidence |
| live-broad-and-context / 10 | Hệ thống hỗ trợ người lái ADAS trên xe VF 8 bao gồm những tính năng cơ bản nào? | wrong_intent_incident_instead_of_information | routing/language |
| live-broad-and-context / 12 | Cách tự đấu dây điện để can thiệp tăng công suất pin xe điện tại nhà? | wrong_language_expected_vietnamese | routing/language |
| live-broad-and-context / 21 | Ứng dụng VinFast có tính năng gì? | unanswered | unsupported_textual_claim |
| live-broad-and-context / 22 | VF7 Plus có màu gì? | unanswered | no_eligible_evidence |
| live-broad-and-context / 24 | Bảo hành pin cao áp VF8 bao lâu? | unanswered | unsupported_numeric_claim |
| live-broad-and-context / 25 | Bảo hành ắc quy 12V VF8 bao lâu? | unanswered | unsupported_numeric_claim |
| live-broad-and-context / 26 | VF8 chạy dịch vụ thương mại được bảo hành thế nào? | unanswered | unsupported_numeric_claim |
| live-broad-and-context / 28 | Lịch bảo dưỡng định kỳ VF8 là gì? | unanswered | no_eligible_evidence |
| live-broad-and-context / 29 | VF3 bảo dưỡng lần đầu ở bao nhiêu km? | unanswered | no_eligible_evidence |
| live-broad-and-context / 30 | VF5 bảo dưỡng mỗi bao nhiêu km? | unanswered | unsupported_numeric_claim |
| live-broad-and-context / 31 | Chi phí bảo dưỡng VF8 bao nhiêu? | unanswered | unsupported_textual_claim |
| live-broad-and-context / 33 | VF8 đi được bao xa một lần sạc? | unanswered | unresolved_catalog_scope |
| live-broad-and-context / 35 | Dung lượng pin VF8 là bao nhiêu? | unanswered | unresolved_catalog_scope |
| live-broad-and-context / 36 | Dung lượng pin VF3 là bao nhiêu? | unanswered | unresolved_catalog_scope |
| live-broad-and-context / 37 | VF8 Plus sạc nhanh bao lâu? | unanswered | unsupported_numeric_claim |
| live-broad-and-context / 38 | Tôi quên mật khẩu ứng dụng VinFast thì làm sao? | unanswered | context_budget_exceeded |
| live-broad-and-context / 40 | Mobile Service hỗ trợ những gì? | unanswered | unsupported_textual_claim |
| live-broad-and-context / 50 | How long is the VF8 warranty? | unanswered | unsupported_numeric_claim |
| live-broad-and-context / 54 | Ứng dụng VinFast có tính năng gì? | unanswered | context_budget_exceeded |
| live-broad-and-context / 56 | Chính sách bảo hành pin và lịch bảo dưỡng định kỳ | partially_answered_despite_success_diagnostic | compound_warranty_maintenance |
| live-incident-sequence / 5 | Không phải trụ P01, trụ P02 | unanswered | unsupported_textual_claim |
| live-incident-sequence / 6 | Xe không còn báo CC01 nữa | unanswered | unsupported_numeric_claim |

## Nguyên nhân và dữ liệu cần bổ sung

| Khu vực | Bằng chứng và nguyên nhân | Data / sửa xử lý cần có |
| --- | --- | --- |
| Bảo hành VF8/VF5, pin/ắc quy | Có đoạn SRC-002 được truy xuất, nhưng `answer_evidence.py:60` tách từng dòng/câu; `:163` đòi model + bộ phận cùng đoạn số; `:180` đòi điều kiện cùng đoạn. Ví dụ tiêu đề pin và điều kiện nằm trước dòng VF8 chứa thời hạn nên claim bị loại. | Giữ cấu trúc tiêu đề–điều kiện–giá trị, chuẩn hóa claim theo model/năm/bộ phận/mua/thuê/thay thế/sử dụng thương mại. Không cần thu thập lại toàn bộ chính sách vốn đã có. |
| Bảo dưỡng VF8 | Có sổ tay nhưng phần đã thu thập chưa có bảng chu kỳ tổng quát km/tháng dùng được. Ghi chú thay dung dịch làm mát có số năm lại bị bộ lọc yêu cầu chữ “bảo dưỡng/chu kỳ” cùng dòng loại. | Thu bảng chu kỳ đúng mẫu/đời xe, hạng mục, điều kiện nặng; sửa lọc để hiểu ghi chú hạng mục. |
| Bảo dưỡng VF3/VF6/VF7/VF9/e34 | Registry hiện chỉ có manual VF5 và VF8; trang dịch vụ chung không thay thế lịch định kỳ theo mẫu. | Manual và bảng lịch của các mẫu còn thiếu; bảng thời gian/km, điều kiện áp dụng. |
| VF5 bảo dưỡng | Probe tìm được nguồn rồi bị `unsupported_numeric_claim`; không gộp thành thiếu toàn bộ lịch VF5. | Đối chiếu đoạn số, hạng mục và điều kiện bị validator loại. |
| Màu xe | Snapshot màu đã rà soát và record `model_colors` hiện chỉ VF8. VF8 trả được danh sách chung với index; VF7 Plus không có evidence đáp ứng. | Màu ngoại thất/nội thất các mẫu còn lại, xác minh riêng phiên bản/đời xe; không suy ra tồn kho. |
| Quãng đường/dung lượng | VF8 Eco và dung lượng VF8 Plus trả được. Câu VF8 không có phiên bản bị `unresolved_catalog_scope`, không phải thiếu toàn bộ thông số. Catalog có 12 cấu hình, năm đều null; dung lượng VF3 Eco/Plus và VF5 null, thiếu e34. | Hỏi lại cấu hình khi mơ hồ; bổ sung ô thực sự null, đời xe, tiêu chuẩn đo, SOC/công suất/nhiệt độ sạc. |
| Thời gian sạc VF8 Plus | Có nguồn, probe bị validator loại số/điều kiện. | Chuẩn hóa đúng khoảng SOC, công suất và điều kiện sạc trong cùng claim; chưa kết luận cần dữ liệu mới. |
| App/quên mật khẩu | Có nguồn SRC-001. Probe quên mật khẩu và app sau VF8 mất nguồn ở prompt (`context_budget_exceeded`) dù retrieval chưa vượt 6.000 byte; prompt tổng giới hạn 8.000 byte. Một câu app khác bị textual validator. | Phân bổ ngân sách prompt, giữ đoạn thao tác cần hỏi, tóm lịch sử, kiểm tra claim diễn đạt. Dữ liệu hướng dẫn hiện có nguồn năm 2022; cần bổ sung hướng dẫn UI phiên bản hiện hành. |
| Câu chung sau khi tư vấn xe | Subject cũ được đưa vào resolved query; compound kế thừa model. `warranty_questions.py:23` từ chối snapshot chung nếu có model, `generic_help_query` dùng whitelist token chặt. | Phân biệt phạm vi câu hiện tại với model chỉ được kế thừa; giữ memory riêng thay vì chèn mọi slot vào truy vấn. |
| Mobile Service/chi phí bảo dưỡng | Có hướng dẫn dịch vụ chung; probe bị textual validator. Giá chính xác, địa bàn khả dụng và lịch trống không được chứng minh bởi văn bản chung. | Giữ phần giải thích chung trả lời được; bảng giá theo xưởng/hạng mục và nguồn giao dịch cho khả dụng thực tế. |
| Đính chính sự cố | Sau câu hỏi trạng thái, context vẫn goal incident nhưng handler có thể đi sang RAG. Sửa trụ và rút mã lỗi nhận câu fallback; chuỗi ngắn không có lượt hỏi trạng thái lại sửa P02 được. | Đồng bộ ConversationContext và vehicle_context, xử lý correct/supply_info/retraction như cập nhật hồ sơ, không tìm tài liệu cho chính câu đính chính. |
| ADAS | Regex incident không dấu nhận `xe VF8 bao` trong “bao gồm” như “báo”. Nhánh current failure chạy trước FAQ “tính năng”. | Sửa ranh giới mẫu câu và ưu tiên hiểu câu hỏi; không phải thiếu manual ADAS. |
| Nhắc lại mẫu xe | Câu recall đầu tiên có “mẫu xe” bị fold thành “mau xe”, trùng nhánh màu sắc nên goal=appearance. | Không dùng nhận dạng màu trên từ đã bỏ dấu mà không phân biệt “mẫu”. Probe xuyên phiên đã chạy lại bằng câu không chứa cụm này để tách confound. |
| Đính chính mẫu xe | Câu “Không phải VF8, xe tôi là VF5, tôi ở Đà Nẵng” sửa state sang VF5/Đà Nẵng nhưng output tự so sánh VF8 Eco với VF5. | Correct phải ưu tiên cập nhật/xác nhận, không tự suy thành yêu cầu so sánh. Đây là lỗi output riêng, không phải mất state. |
| VI/EN | “can thiệp” chứa token `can`; nhánh English chạy trước kiểm tra chữ có dấu khi không trúng whitelist VI. | Sửa phát hiện ngôn ngữ toàn câu; không phải thiếu data tiếng Anh/Vietnamese. |
| Câu nhiều ý | Sau VF8, phần bảo hành có trả lời nhưng mục bảo dưỡng vẫn fallback; API lại ghi final success. | Trạng thái PARTIAL phải theo từng ý, không báo đủ khi chỉ có một phần có nguồn. |

Các giá trị chính sách/thông số trong output là dữ liệu snapshot được kiểm thử, không phải xác nhận chính sách thương mại hiện hành.

## Memory xuyên phiên và restart

Mỗi request được thực hiện bởi một subprocess Python mới, dùng chung SQLite kiểm thử. Seed có xác nhận model/Plus/Hà Nội đã vào state trước khi thử nhớ ở phiên tiếp theo. Profile control được ghi trước vào User.vehicle_model, không phải kết quả tự học từ chat.

| Capability | Kết quả |
| --- | --- |
| same_session_restart | Đạt |
| same_session_explicit_recall | Đạt |
| new_session_model | Chưa đạt |
| new_session_trim | Chưa đạt |
| new_session_city | Chưa đạt |
| latest_correction_new_session | Chưa đạt |
| profile_model_new_session | Đạt |
| other_user_isolation | Đạt |
| fresh_incident_isolation | Đạt |
| new_session_configured_provider | Chưa đạt |
| same_session_recall_wording | Chưa đạt |

Cụ thể: phiên A nói “Hãy nhớ xe của tôi là VF8 Plus, tôi ở Hà Nội”; phiên B cùng user hỏi lại không có subject/phiên bản/thành phố trong context. Sau đính chính sang VF5/Đà Nẵng ở A, B vẫn không nhận bản mới. Bật provider không bổ sung được cơ chế hydrate memory theo user.

Rà soát probe: câu hỏi đầu “Tôi đã nói tôi sử dụng mẫu xe, phiên bản nào và ở thành phố nào?” còn mắc lỗi routing appearance. Bốn capability xuyên phiên đã được đo lại với “Xe tôi là dòng nào?”, “Tôi đã chọn phiên bản nào ở cuộc trò chuyện trước?”, “Thành phố tôi đã chọn ở cuộc trò chuyện trước là gì?” và câu nhắc lại thông tin. Artifact cuối thay các kết quả đầu bằng lượt kiểm tra không chứa “mẫu xe”; không quy mọi lỗi recall đầu tiên chỉ cho hydration.

Nguyên nhân kiến trúc:

- `chat_turns.py:96–109` đọc snapshot theo session_id; `application_memory.py:17` và `:52` cũng lưu theo session. Compact/summary vẫn thuộc phiên đó.
- Legacy `read_existing_state(session_id, owner, role)` yêu cầu cùng session_id và chủ sở hữu, không tìm các phiên của cùng người dùng.
- `User.vehicle_model` có thể được đọc trong luồng sự cố (`customer.py:510–569`), nhưng thông tin chat không được tự tổng hợp/ghi thành profile memory có provenance. Chưa có kho user fact theo key, bản sửa mới nhất, consent và forget.
- Có thể nhớ model trong cùng phiên nhưng template recall luôn gọi đó là “xe đang ghi nhận sự cố”, dù seed chỉ khai báo xe sở hữu. Ca wording đã tái hiện thất bại riêng.

Hướng bổ sung: user-scoped facts có nguồn lượt chat, thời điểm/hiệu lực, xác nhận và quyền xóa; chỉ hydrate sở thích/thông tin bền vững phù hợp. Không mang goal, cảnh báo nguy hiểm, mã sự cố hay ý định đặt lịch cũ sang phiên mới. Giữ nguyên các control không lẫn người dùng và không lấy xe từng hỏi mua làm xe đang báo sự cố.

## Bằng chứng, cách chạy và giới hạn

- Kết quả cấu trúc và đầy đủ response: `eval/results/answer-gap-audit-2026-10-19.json`.
- Thống kê đầy đủ câu cũ: `eval/results/unanswered-long-memory-2026-10-19.json`.
- Probe đo coverage: 8 test chạy xong tương ứng 284 request; pytest PASS ở đây chỉ xác nhận phép đo hoàn tất, không xác nhận câu trả lời đúng.
- Probe memory offline: 5 pass/4 fail ở lượt 9 capability, thêm 1 fail wording; provider control 1 fail. Hai semantic contract ADAS/ngôn ngữ đều fail có chủ đích để lưu lỗi hiện tại.
- Đây là API text ở local, người dùng tổng hợp, index bản sao; không phải kiểm thử Vercel, ảnh/OCR, UI thật, GPS thiết bị, tải nhiều người dùng hay mọi câu có thể hỏi.
- Golden cũ chỉ dùng để chọn probe/keyword phụ trợ; nhãn cũ chưa phải oracle đã duyệt. Không coi thiếu keyword là bằng chứng trả lời sai độc lập.

```powershell
$env:LANGFUSE_TRACING_ENABLED='false'
$env:ANSWER_GAP_AUDIT='1'
python -m pytest tests/test_api/test_cross_session_memory_audit.py -q
python -m pytest tests/test_api/test_answer_gap_audit.py -q -k "not configured"
# Probe index cần bản sao .test-runs/answer-gap-index và embedding model cục bộ.
# Bật provider chỉ khi muốn gọi cấu hình .env của workspace gốc:
$env:ANSWER_GAP_LIVE='1'
python -m pytest tests/test_api/test_answer_gap_audit.py -q -k configured
```

Ưu tiên: (1) sửa xử lý bằng chứng, budgets, partial và routing; (2) bổ sung lịch bảo dưỡng/màu/cấu hình thực sự thiếu; (3) bổ sung user memory xuyên phiên cùng các control cách ly/cập nhật/xóa. Lượt audit này chưa triển khai các sửa đổi đó.
