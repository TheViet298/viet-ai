# GPS integration review — 16/10/2026

## Trạng thái và phạm vi

- Gốc IDE: feature/ai-khoi e6b9d9d; upstream origin/feature/ai-khoi; behind 2. Không thay đổi HEAD, index hoặc bất kỳ file có sẵn nào ở checkout gốc. Checksum 70 file và git status khớp bản sao lưu.
- GitHub feature/ai-khoi: 2eb4317664789923ec0f2c79a8fbf0b8c8c06d04. Hai commit mới so với IDE: 96929a9 và 2eb4317, đều GPS.
- GitHub feature/agent-long: ccee2badf1ee3a03f954412ee251e7187982421c. Không có commit mới so với lần kiểm tra ngày 15/10.
- Quan hệ hai remote branches trước merge: Khoi có 73 commit riêng, Long có 2 commit riêng.
- Bản sao tích hợp: bản sao tích hợp cô lập. Đã fast-forward tới remote Khoi rồi merge --no-commit --no-ff Long, xử lý conflict và stage kết quả. Chưa commit merge, push, tạo PR hoặc merge PR.
- Review tree (không phải commit): 4d05bf2e193e9f0a99a2e65f4ff839f8fb6a90bb.
- GPS local có 62 file khớp byte remote Khoi, không cần commit trùng. 8 file hooks/logging local khác remote được giữ ở checkout gốc và không nhập vào bản tích hợp.

## Các diff

- diff tích hợp GPS: 6 file giao nhau và 3 file test, so với remote Khoi mới nhất.
- diff so với Khoi: toàn bộ thay đổi bản tích hợp so với remote Khoi, 89 file (86 file nhận/gộp từ Long và 3 file test).
- diff so với Long: toàn bộ bản tích hợp so với remote Long, 331 file. Đây là nội dung dự kiến của PR sau merge commit, không phải PR chỉ GPS.
- *-files.txt và *-stat.txt: danh sách và thống kê tương ứng.

## Bảng so sánh chỉ GPS

| Hành vi | Long ccee2bad | Khoi 2eb4317 | Bản tích hợp |
| --- | --- | --- | --- |
| Nhận diện yêu cầu | Dò từ khóa, cờ request_location | NearbyAction có category, vehicle_type, area_text và request/turn ID | Giữ Khoi, chạy sau chuẩn hóa của Long; câu không dấu được kiểm tra qua API thật |
| GPS | getCurrentPosition sau lựa chọn; popup dựa trên request_location/critical | Chỉ action nearby có chủ đích, không login/FAQ/reload tự mở; GPS one-shot | Giữ Khoi |
| Nhập tay/bỏ qua | Có card vị trí | Có nhập tay, khu vực tham chiếu, bỏ qua và timeout/denied fallback | Giữ Khoi |
| Đổi tài khoản | Chờ auth, remount CustomerChatSession theo user ID | Reset một số state theo user ID | Kết hợp wrapper Long với workflow Khoi; logout xóa kết quả/consent và cần chọn lại |
| Dữ liệu kết quả | UI map nhận servicePoints=[]; chưa có adapter snapshot/endpoint nearby mới | Catalog snapshot, lọc loại xe/nguồn, top 5 theo Haversine, mở rộng bán kính | Giữ Khoi; dữ liệu vẫn UNVERIFIED, không khẳng định hoạt động thực tế |
| Map/chỉ đường | Panel cũ | Kết quả trong chat, map gọn mặc định đóng, link Google Maps theo điểm | Giữ Khoi; E2E kiểm tra viewport và link, không điều hướng Maps ngoài web |
| Vị trí với case | Chưa có consent riêng shareWithCase ở UI | Tra cứu không tự lưu vào case; nút chia sẻ riêng, revoke xóa tọa độ | Giữ Khoi |
| Request cũ | Không có workflow nearby mới | Abort tìm kiếm cũ và vô hiệu hóa callback GPS muộn | Giữ Khoi, regression/E2E pass |

## File cần xem kỹ

| File | Quyết định gộp và ý nghĩa |
| --- | --- |
| frontend/src/features/chat/api/chatApi.ts | Giữ API nearby của Khoi, Citation[] và timeout 30s; nhận fields lịch sử thẻ xe của Long để tương thích phần tự gộp |
| frontend/src/features/chat/components/CustomerChatContainer.tsx | Giữ toàn bộ luồng GPS của Khoi; thêm wrapper auth-ready/remount theo tài khoản của Long |
| frontend/src/features/chat/hooks/useChat.ts | Giữ nearbyAction; nhận xử lý lịch sử 401/403 và fields thẻ xe của Long. Không khôi phục consent GPS từ history |
| frontend/src/features/chat/types.ts | Kết hợp NearbyAction với VehicleCard, không thay kiểu nearby bằng kiểu thẻ xe |
| src/models/schemas.py | Kết hợp NearbyAction và schema thẻ xe; giữ field nearby_action trong ChatResponseData |
| src/api/customer.py | Giữ classify_location_request, vinfast_nearby_search và endpoint GPS; nhận normalization/clarification Long. Giữ nguyên thông báo giới hạn khách và fallback RAG của Khoi để không đổi logic RAG ngoài phạm vi GPS |
| frontend/tests/location-runtime.test.cjs | Harness chạy component session con và cung cấp auth-ready; giữ nguyên các assert consent/revoke/callback muộn |
| frontend/tests/e2e/gps-real.spec.ts | Thêm kiểm tra logout xóa consent/kết quả; thao tác tìm mới yêu cầu chọn vị trí lại |
| tests/test_api/test_contextual_nearby.py | Thêm câu không dấu vào chuỗi API chat thật để kiểm tra normalization + nearby |

4 file conflict do Git xác nhận: chatApi.ts, types.ts, customer.py, schemas.py. CustomerChatContainer.tsx và useChat.ts tự gộp, vẫn được review và kiểm thử.

## Kiểm thử thực hiện trong bản tích hợp

| Nhóm | Kết quả |
| --- | --- |
| Lint | PASS |
| Frontend tests sau cập nhật harness | 63/63 PASS |
| TypeScript | PASS |
| Backend location | 26 PASS |
| Backend location API regression | 1 PASS, 15 deselected |
| Backend nearby/catalog/privacy | 44 PASS |
| Frontend production build | PASS |
| Regression normalization/chat/nearby/privacy | 121 PASS, giao nhau với các nhóm trên, không cộng tổng |
| Production E2E Chromium + Firefox | 20/20 PASS; geolocation giả lập, backend/DB riêng |
| Conflict index và whitespace source/test đã gộp | Không còn unmerged paths; PASS |

Lượt verifier đầu có 5 frontend test lỗi do harness cũ không render component con của Long; đã cập nhật harness rồi chạy lại toàn bộ frontend tests, 63/63 pass. Verifier ban đầu có exit 1 vì các lỗi này; không trình bày log đó là toàn bộ verifier pass. Lượt trong sandbox dừng ở lint, bị ngắt và chạy ngoài sandbox; không tính lượt bị ngắt là pass.

Diff whitespace toàn bộ nhánh còn finding có sẵn từ artifact eval/PDF của Long; không sửa artifact ngoài GPS. Chưa chạy CI GitHub, toàn bộ pytest hoặc provider LLM online. Không có bằng chứng tối ưu tốc độ so với baseline; tối ưu ở bước thao tác, hạn chế request/GPS nền và tách phiên người dùng.

## Điều cần quyết định trước PR

PR từ Khoi về Long hiện mang 331 file gồm GPS lẫn lịch sử ngoài GPS: case/auth/RAG, tài liệu, công cụ/logging và eval. Cần review toàn bộ danh sách trước khi tiếp tục. Nếu chỉ muốn GPS, cần một nhánh nguồn giới hạn GPS dựa trên Long thay vì dùng nguyên lịch sử Khoi. Chưa tạo nhánh remote hoặc PR nào; các PR mở hiện có không có cặp Khoi -> Long.

## Bàn giao PR

Báo cáo này ghi nhận kiểm tra local trước khi tạo PR. Hai PR draft cùng nguồn review/gps-integration-oct16, đích feature/agent-long và main. Chưa merge PR. Các con số diff phía trên chưa gồm gói tài liệu review này. Không đính kèm log cá nhân, bản backup hoặc credential.
