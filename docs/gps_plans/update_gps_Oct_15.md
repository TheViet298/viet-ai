# Cập nhật GPS — 15/10/2026

## Kết quả bàn giao

Đã triển khai workflow theo [kế hoạch](contextual-nearby-workflow-plan.md): khách chat yêu cầu tìm địa điểm → agent nhận diện loại địa điểm/phương tiện và ngữ cảnh → xin vị trí khi cần → tự trả tối đa 5 kết quả → nhấn **Chỉ đường Google Maps**. Bản đồ thu gọn mặc định, không cần chọn điểm để điền và gửi thêm một câu chat.

Đích bàn giao Git là `feature/ai-khoi`, upstream `origin/feature/ai-khoi`. Commit được chuẩn bị từ checkout cô lập dựa trên remote mới nhất; checkout IDE và các chỉnh sửa hooks/logging có sẵn được giữ nguyên. Kiểm chứng bên dưới được ghi nhận trước commit; SHA và kết quả push được đối chiếu qua lịch sử nhánh. Không triển khai production hoặc tạo API key.

## Các task đã thực hiện

| Bước trong plan | Triển khai và bằng chứng |
| --- | --- |
| 0. Truy vết login/permission | Card trước đây có thể bị mở bởi `criticalBanner`, boolean `request_location` hoặc chip chứa “sạc/trạm”. Không thấy lời gọi GPS vô điều kiện từ login. Loại các trigger rộng khỏi workflow tìm kiếm; test login/FAQ/reload không mở dialog, test legacy boolean không tự mở card |
| 1. Dữ liệu/adapter | Chuẩn hóa đủ 68.637 dòng; đóng gói gzip + metadata/checksum trong `fixtures/gps`, độc lập đường dẫn máy và thư mục `data/` bị ignore; cache và validate trước dùng |
| 2. Intent/context/action | `classify_location_request` nhận diện có/không dấu, phủ định, FAQ, câu tiếp nối, loại xe, khu vực đã nêu; `NearbyAction` có request_id/turn_id/category/vehicle/reason. Không tạo intent nghiệp vụ thứ năm |
| 3. Engine/tool | Nearby API và `vinfast_nearby_search` dùng chung Haversine/catalog; helper case/session dùng cùng engine. Mặc định top 5 trong 50 km; người dùng có thể mở rộng 100/200 km, không bịa đủ 5 |
| 4. UI/consent | Popup có lý do và GPS/nhập tay/bỏ qua; GPS one-shot; danh sách ngay trong chat; CTA Google Maps; map 280 px tùy chọn với marker đánh số. Tự cuộn trong feed để thấy điểm đầu hoặc canvas khi mở map, không kéo toàn trang |
| 5. Regression/bàn giao | 129 backend tests, 58 frontend tests, TypeScript/lint/build và E2E 18/18 Chromium/Firefox; cập nhật user guide, ảnh và báo cáo này |

## Hành vi mới

- Login, FAQ về cách sạc/giá sạc/bảo hành và reload không tự xin GPS. Cảnh báo an toàn vẫn ưu tiên; tìm gần đây không được vượt hard safety gate.
- “Tìm trạm sạc gần đây”, “tim tru sac gan day”, “quanh đây có chỗ sạc không?” mở đúng action. “Còn showroom thì sao” giữ ngữ cảnh loại xe; lựa chọn xe máy không bị profile ô tô ghi đè.
- “Showroom ở Huế” dùng điểm tham chiếu khu vực và không hỏi GPS. Địa chỉ chưa nhận diện được giữ dưới dạng chữ, không tạo tọa độ/khoảng cách giả. Các khu vực hỗ trợ hiện gồm Hà Nội, TP.HCM, Đà Nẵng, Huế và Cao tốc Long Thành.
- Chỉ gọi `getCurrentPosition` khi khách chọn GPS; không watch/tracking nền cho tra cứu. Tái dùng lựa chọn còn mới trong cùng phiên mounted tối đa 15 phút; logout/reset/hủy thao tác vô hiệu hóa callback muộn. Reload không tự khôi phục consent/popup.
- Request tìm kiếm cũ bị hủy khi đổi lượt, category, vị trí hoặc bỏ qua; response cũ không ghi đè kết quả mới. Block/timeout/unsupported có nhập tay. Mất mạng hiển thị lỗi + retry, không trộn demo vào snapshot.
- Tra cứu hoạt động trước khi có case; không tạo case giả. GPS tra cứu không tự POST `/customer/location`. Nút **Chia sẻ vị trí với hồ sơ** là consent riêng khi có case và GPS; dừng chia sẻ gửi xóa tọa độ nếu đã chia sẻ. Hàng đợi API giữ thứ tự khi revoke sau request đang chạy.
- Top 5 lọc loại địa điểm/phương tiện và điều kiện nguồn, rồi sort Haversine ổn định. Hiển thị khoảng cách đường chim bay, nguồn snapshot và chưa xác minh hoạt động hiện tại.
- URL Google Maps được tạo bằng tọa độ đã validate/encode. Chỉ thêm origin GPS khi được phép; khu vực tham chiếu không bị gửi thành GPS của khách. Nhấn link chuyển tọa độ sang Google Maps; không tự mở tab ngoài hoặc hứa booking.

## Dữ liệu đã tích hợp

| Nhóm nguồn | Bản ghi |
| --- | ---: |
| Trạm sạc ô tô | 24.695 |
| Trạm sạc xe máy | 540 |
| Tủ đổi pin | 42.264 |
| Showroom ô tô | 352 |
| Showroom xe máy | 786 |
| Tổng | **68.637** |

Sáu bản ghi tọa độ lỗi/đáng ngờ bị loại khỏi ứng viên. Runtime giữ **18.120 ứng viên** sau lọc cho các loại xe hỗ trợ, gồm **17.008 ứng viên ô tô**: 16.657 trạm sạc và 351 showroom. Trạm sạc chỉ được chọn khi snapshot ghi ACTIVE, Public và publish; không hiểu `status=True/1` là đang sạc được.

Tủ đổi pin còn trong snapshot để truy vết nhưng không đưa vào kết quả vì thiếu loại xe/trạng thái phù hợp. Chưa tự suy ra xưởng từ mã `multiple_type`. Tên/địa chỉ/tọa độ lặp không bị tự gộp thành một entity; các điểm cùng tòa nhà/tầng khác nhau có thể cùng xuất hiện.

Gói runtime: [snapshot gzip](../../fixtures/gps/service_points.snapshot.csv.gz), [metadata và SHA-256 nguồn](../../fixtures/gps/service_points.snapshot.metadata.json), [hướng dẫn tái tạo/rollback](../../fixtures/gps/README.md). Không sao chép CRM/Salesforce, hotline, URL hoặc object nhúng vào snapshot. Hai CSV gốc không bị sửa.

```bash
python3 scripts/eda_gps_catalog.py \
  --input-dir /home/palm/Desktop/vin_ai20k/data_gps \
  --output-dir data/gps --runtime-dir fixtures/gps
```

`GPS_CATALOG_MODE=demo` chọn rõ fixture demo để test/rollback. Snapshot lỗi/checksum sai/mode sai trả 503; không fallback âm thầm. Ngày nhập là 15/10/2026; ngày export/cập nhật nguồn vẫn chưa biết, mọi bản ghi UNVERIFIED.

## Kiểm chứng

| Nhóm | Kết quả |
| --- | --- |
| Frontend lint | PASS, không warning/error ở lượt cuối |
| Frontend Node tests | **58 PASS** |
| TypeScript | PASS |
| Backend location | **26 PASS** |
| Backend location API regression | **1 PASS**, 15 deselected |
| Backend contextual nearby/catalog/privacy | **44 PASS** |
| Production frontend build | PASS |
| Backend regression mở rộng | **129 PASS**; gồm API, session/history, safety, ownership và location; có giao nhau với các nhóm trên, không cộng tổng |
| Production E2E | **18/18 PASS**, Chromium + Firefox; server/DB/tài khoản thử cô lập, cổng 18020/13020 |
| Intent eval offline | **18/18 đúng** trên bộ regression cố định: 6 positive, 12 negative; không phải accuracy production |
| Ruff | PASS cho sáu helper/test Python được chọn; không tuyên bố toàn repository sạch Ruff |
| Diff whitespace | PASS trong phạm vi source/test đã chỉnh |

Lệnh kiểm tra chính:

```bash
./scripts/verify-gps.sh
GPS_E2E_BACKEND_PORT=18020 GPS_E2E_FRONTEND_PORT=13020 npm --prefix frontend run test:e2e
```

Verifier chạy đủ 7 nhóm; E2E chạy riêng nên dòng SKIP E2E trong verifier không có nghĩa E2E chưa chạy. Lượt async HTTP trong sandbox bị chờ không tiến triển đã được dừng, các lượt PASS cuối chạy ngoài sandbox. Không tính lượt bị dừng là PASS.

Regression phát hiện test rollback cũ mock `process_chat_message` trong khi câu hỏi đang đi nhánh sales ngay trên baseline. Đã đối chiếu baseline và đổi điểm tiêm lỗi sang `_process_customer_chat` sau draft: vẫn kiểm tra không có message/turn bị commit khi lỗi, không bỏ assert hoặc skip test. Các lỗi selector E2E, TypeScript, tolerance số thực ở Firefox và container MapLibre phát hiện trong quá trình triển khai đã được sửa trước lượt PASS cuối. MapLibre ghi đè positioning theo class, làm container co chiều cao; map gọn hiện dùng positioning inline và test canvas trong viewport cùng đủ 6 marker.

[Intent eval](../evidence/gps_oct15/intent-eval.json), [benchmark catalog](../evidence/gps_oct15/catalog-benchmark.json), [tóm tắt kiểm chứng](../evidence/gps_oct15/verification-summary.json). Benchmark một lượt tại tâm tham chiếu TP.HCM: cold load **0,721 s**, warm query **26,61 ms**, trả 5 điểm; không phải SLA hoặc đo cải thiện so với UI cũ.

### Ảnh giao diện đã xem

- [Popup desktop](../evidence/gps_oct15/popup-1440.png), [popup 375 px](../evidence/gps_oct15/popup-375.png).
- [Kết quả desktop](../evidence/gps_oct15/compact-results-1440.png), [kết quả 375 px](../evidence/gps_oct15/compact-results-375.png), [map gọn trên mobile](../evidence/gps_oct15/compact-map-mobile.png).

E2E kiểm tra không cuộn ngang ở 375/768/1440 px, CTA đầu trong viewport, map mặc định đóng và canvas có mặt trong viewport sau khi mở. Kiểm tra canvas/worker không chứng minh raster map tải đủ địa vật trên mọi mạng.

Áp dụng skill `ui-ux`, giữ nền sáng, màu nhấn blue-800/#1E40AF và font hiện có ở `frontend/src/app/globals.css`; không thêm dark mode. Nút/card mới ở `NearbyResults.tsx`, popup tái dùng `LocationConsentCard.tsx`, map tái dùng `ServiceMapPanel.tsx`. Probe đã chạy ở 375/1440 px; còn finding UI nền ở header/footer, control cũ và chữ tương phản thấp, nên không tuyên bố toàn giao diện đạt checklist. Nút tìm gần đây đã được tăng vùng bấm và nút “Tin mới” không che kết quả GPS.

## Tệp thay đổi trong đợt triển khai

| Nhóm | Tệp |
| --- | --- |
| Backend/action | `src/api/customer.py`, `src/models/schemas.py`, `src/services/nearby_intent.py`, `prompts/nearby_intent_prompt.md` |
| Catalog/tool | `src/services/service_point_catalog.py`, `src/services/location_service.py`, `src/agents/tools/vinfast_tools.py`, `fixtures/gps/{service_points.snapshot.csv.gz,service_points.snapshot.metadata.json,README.md}` |
| Frontend | `frontend/src/features/chat/{types.ts,api/chatApi.ts,hooks/useChat.ts}`, `components/{CustomerChatContainer,LocationConsentCard,NearbyResults,ChatFeed,ServiceMapPanel}.tsx`, `constants/manualAreas.ts`, `utils/distance.ts` |
| Frontend tests | `frontend/playwright.config.ts`, `frontend/tests/{location-consent-flow,location-runtime,manual-map-config}.test.cjs`, `frontend/tests/e2e/{gps-real,gps-mocked,gps-map-layout}.spec.ts` |
| Python tests | `tests/test_api/{test_contextual_nearby,test_nearby_service_points,test_service_point_catalog,test_chat_remediation}.py`, `tests/test_agents/test_location_and_memory.py` |
| Công cụ | `scripts/eda_gps_catalog.py`, `scripts/gps-e2e-server.py`, `scripts/verify-gps.sh` |
| Tài liệu/artifact | `docs/gps_plans/{user-guide,contextual-nearby-workflow-plan,gps-data-eda-2026-10-15,gps-feature-report-latest-version,update_gps_Oct_15}.md`, `data/gps/README.md`, `docs/evidence/gps_oct15/*` |

Các thay đổi GPS cũ khác và hooks/logging đã có trong worktree trước task không được coi là thay đổi mới do báo cáo này thực hiện. Artifact staging `data/gps` vẫn bị Git ignore; runtime dùng gói đóng trong `fixtures/gps`.

## Giới hạn còn lại

1. CSV là snapshot, chưa rõ ngày export; ACTIVE không chứng minh trạm đang mở/còn cổng trống. Boutramsacox chỉ sàng lọc, không chứng minh mọi tọa độ/địa chỉ đúng. Chưa có công suất, đầu nối, tương thích từng mẫu xe hoặc mức phí đáng tin cậy.
--> dự kiến bổ sung status, số lượng cho tramsac

2. Không có dữ liệu road distance/ETA để huấn luyện mô hình dự đoán. Website hiển thị đường chim bay; quãng đường thực do dịch vụ Google Maps bên ngoài xử lý. Chưa vẽ tuyến đường trong web.
3. Xưởng và tủ đổi pin cần thêm mapping/metadata được xác nhận trước khi dùng. Huế dùng một điểm showroom trong nguồn làm điểm tham chiếu, không phải centroid hành chính hoặc vị trí khách.
4. LLM fallback có schema/allowlist, gate confidence 0,9 và test mock mức tin cậy; chưa đánh giá provider online hoặc hiệu chỉnh threshold trên dữ liệu hội thoại lớn. Bộ case offline không chứng minh mọi cách diễn đạt đều nhận diện đúng.
5. E2E dùng geolocation giả lập và tài khoản giả; chưa thử GPS phần cứng, quyền hệ điều hành trên mọi thiết bị hoặc mở ứng dụng Google Maps thật trên mọi nền tảng. Link/href đã được kiểm tra, không coi đó là bằng chứng điều hướng ngoài web end-to-end.
6. Chưa triển khai production, chưa chạy toàn bộ pytest/backend lint toàn repository . Trạng thái bàn giao Git xem lịch sử nhánh `feature/ai-khoi`. Các finding UI nền ngoài workflow GPS được giữ để review riêng.
