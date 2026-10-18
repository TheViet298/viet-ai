# Khắc phục giới hạn GPS — bằng chứng cập nhật 14/10/2026

## Phạm vi và phân công

Triển khai theo [limitations-remediation-plan.md](limitations-remediation-plan.md). Các agent làm cùng checkout, mỗi tệp có một người sở hữu; coordinator tích hợp sau khi agent bàn giao. Không merge/switch/reset/stash hoặc sửa phần hook/logging đang làm riêng.

| Người phụ trách | Phần độc lập | Quyền sửa chính |
| --- | --- | --- |
| Agent hydration/E2E; agent browser tiếp tục kiểm chứng | P0 hydration, production E2E, cấu hình Chromium/Firefox | ChatMessageItem, useChat, package/lock, Playwright config, test E2E, runner server |
| Agent manual/map | P1 nhập tay phần A, tile config, metadata frontend | LocationConsentCard, ServiceMapPanel, constants/manualAreas, constants/servicePoints, utils/mapTileProvider, manual-map tests |
| Agent backend catalog | P2 tách danh mục, adapter/schema riêng, backend tests | customer route, service_point_catalog, canonical fixture, catalog/nearby tests |
| Coordinator | API/proxy, privacy, types/API mapping, build isolation, review fixes, kiểm chứng và báo cáo | AuthContext, chatApi, types, Next/Docker/proxy config, privacy middleware/tests, verifier, tài liệu |

## Kết quả triển khai

- Giờ tin nhắn lấy từ timestamp của tin nhắn; render trước mount không định dạng theo múi giờ. Lời chào khởi tạo không đọc đồng hồ; timestamp được bổ sung sau mount. Không dùng `suppressHydrationWarning` để che lỗi.
- Playwright chạy production build ở `.next-gps-e2e`, TypeScript config riêng và lock ngăn hai runner E2E dùng cùng checkout. Backend chạy ở cwd/DB tạm, không đọc `.env` của repository, tắt LLM/tracing và dùng tài khoản giả tạo qua auth hiện có. Đã sửa deadlock teardown do signal handler gọi wait lồng nhau: handler chỉ báo dừng, vòng chạy chính thực hiện wait/kill có giới hạn. Hai lượt lifecycle xác nhận SIGTERM exit 0, child được reap và DB tạm bị xóa.
- E2E thật đi qua login UI, tạo case, GPS trước/sau case, GPS → MANUAL → NOT_SHARED, đọc lại dữ liệu lưu, reload chat và chặn cả đọc/cập nhật case của khách khác. Nhóm giả lập tách riêng: timeout, callback GPS muộn, nearby API mất mạng và response category cũ.
- Danh mục khu vực hỗ trợ alias/tìm kiếm, chỉ exact match sau chuẩn hóa mới có tâm tham chiếu. Địa chỉ mơ hồ/không biết không tạo khoảng cách giả; chữ nhập tay vẫn được chấp nhận và không thành GPS.
- Nearby dùng adapter/schema/danh mục demo riêng, không đổi fixture của agent. Response có source, ngày revision, demo, verification status; catalog sai trả 503. Không chấp nhận nguồn/ID/tên/địa chỉ trắng, tọa độ sai hoặc demo được đánh VERIFIED. Test xác nhận backend/frontend fallback đồng nhất.
- Tile URL/attribution là cấu hình build-time `NEXT_PUBLIC_MAP_TILE_URL` và `NEXT_PUBLIC_MAP_TILE_ATTRIBUTION`. Custom raster URL phải HTTPS, đủ z/x/y, không chứa user/password và có attribution. Cấu hình lỗi giữ fallback danh sách. Chưa chọn nhà cung cấp production.
- Browser mặc định gọi cùng origin `/api/v1`; Next rewrite dùng `API_PROXY_TARGET` phía server. Docker frontend trỏ tới hostname backend nội bộ, thay cho localhost của máy người dùng.
- Profile Nginx HTTPS thử nghiệm ghi method/path/status, bỏ query/body/header khỏi access log và tắt error log có nguy cơ ghi nguyên URI. Middleware ứng dụng bảo vệ cả URL nearby có dấu `/` cuối trước 307/200/422/503. Host header giữ cổng TLS để redirect đúng.

## Tệp thuộc đợt triển khai

Các tệp dưới đây gồm triển khai đã hiện diện trong commit `e6b9d9d` và phần sửa tiếp trong phiên này. Không bao gồm các tệp hook/logging của công việc khác.

| Nhóm | Tệp |
| --- | --- |
| Hydration | `frontend/src/features/chat/components/ChatMessageItem.tsx`, `frontend/src/features/chat/hooks/useChat.ts`, `frontend/tests/chat-hydration.test.cjs`, `frontend/tests/critical-guidance.test.cjs` |
| E2E/build isolation | `frontend/package.json`, `frontend/package-lock.json`, `frontend/playwright.config.ts`, `frontend/tests/e2e/gps-real.spec.ts`, `frontend/tests/e2e/gps-mocked.spec.ts`, `scripts/gps-e2e-server.py`, `frontend/tsconfig.json`, `frontend/tsconfig.e2e.json`, `frontend/.gitignore` |
| Manual/map | `frontend/src/features/chat/components/LocationConsentCard.tsx`, `frontend/src/features/chat/components/ServiceMapPanel.tsx`, `frontend/src/features/chat/constants/manualAreas.ts`, `frontend/src/features/chat/constants/servicePoints.ts`, `frontend/src/features/chat/utils/mapTileProvider.ts`, `frontend/tests/manual-map-config.test.cjs` |
| Catalog | `src/api/customer.py`, `src/services/service_point_catalog.py`, `fixtures/nearby_service_points.demo.json`, `tests/test_api/test_service_point_catalog.py`, `tests/test_api/test_nearby_service_points.py` |
| API/proxy/privacy | `frontend/src/features/chat/api/chatApi.ts`, `frontend/src/features/chat/types.ts`, `frontend/src/features/shared/context/AuthContext.tsx`, `frontend/next.config.js`, `frontend/Dockerfile`, `docker-compose.yml`, `docker-compose.gps-https.yml`, `infra/gps-https/nginx.conf`, `src/services/location_privacy.py`, `tests/test_api/test_location_log_privacy.py`, `frontend/tests/customer-location-api.test.cjs`, `scripts/check-gps-https.py` |
| Verification/tài liệu | `scripts/verify-gps.sh`, `docs/gps_plans/limitations-remediation-plan.md`, `docs/gps_plans/completion-report.md`, `docs/gps_plans/https-test-environment.md`, báo cáo này |

## Kiểm thử và bằng chứng

`./scripts/verify-gps.sh` trên mã cuối: **exit 0**, đủ bảy nhóm:

| Nhóm | Kết quả |
| --- | --- |
| Frontend lint | PASS, không lỗi/cảnh báo |
| Frontend Node tests | **58 passed** |
| TypeScript | PASS |
| Backend location/memory/extraction | **26 passed** |
| Backend location API regression | **1 passed**, 15 deselected theo lựa chọn sẵn có |
| Backend nearby/catalog/privacy | **21 passed** |
| Next.js production build | PASS |

`python3 -m unittest discover -s tests/test_scripts -p 'test_gps*.py' -v`: **14 passed**. `bash -n scripts/verify-gps.sh`: PASS. Verifier có tùy chọn `GPS_RUN_E2E=1`; lượt trên để mặc định SKIP browser, rồi chạy E2E riêng để phân biệt bằng chứng. Lượt đầu trong sandbox có test harness thiếu hook mock và async backend bị treo; mock đã cập nhật giữ nguyên safety assertions, toàn bộ verifier chạy lại ngoài sandbox mới được tính PASS.

Production browser E2E: `npm --prefix frontend run test:e2e -- --project=chromium --project=firefox`: **14 passed**, exit 0 trong lượt cuối với runner đã sửa teardown và thư mục mới. Mỗi browser có 2 ca backend thật, 1 ca hydration qua hai múi giờ/chuyển phút, 4 ca giả lập lỗi/race. Cả hai TypeScript config giữ nguyên checksum sau build.

| Browser/OS | Backend thật | Hydration | Giả lập lỗi/race | Trạng thái |
| --- | --- | --- | --- | --- |
| Chromium headless/Linux | 2 PASS | 1 PASS | 4 PASS | 7/7 |
| Firefox headless/Linux | 2 PASS | 1 PASS | 4 PASS | 7/7 |
| Chromium/Firefox desktop có UI; thiết bị thật | Chưa chạy | Chưa chạy | Chưa chạy | Chưa xác minh |

Coordinator đã mở và xem ảnh cuối: map có danh sách, markers, controls, attribution và directions; manual form 375 px dùng được và test xác nhận không tràn ngang document. **Raster basemap chưa xác minh**: ảnh nền xám và network JSON xác nhận Chromium `net::ERR_NAME_NOT_RESOLVED`, Firefox `NS_ERROR_UNKNOWN_HOST` khi tải host tile OSM. Không tính lỗi DNS này thành PASS tile rendering.

Artifact tạm:

- `/tmp/gps-remediation-verify-current.log`, `/tmp/gps-remediation-script-tests-current.log`, `/tmp/gps-e2e-teardown-final.log`.
- `/tmp/gps-runner-lifecycle-final.log`: hai lượt shutdown/teardown PASS. `/tmp/gps-e2e-processes-final.json`: `[]`, không còn process E2E server sau lượt cuối.
- `/tmp/p142-gps-playwright-results/`: `gps-map-desktop.png`, `manual-form-mobile.png`, `manual-mobile.png`, `basemap-network.json` theo browser/test.
- `/tmp/gps-https-backend.log`, `/tmp/gps-https-frontend.log`, `/tmp/p142-gps-proxy-log/`; TLS/browser smoke harness chỉ ở `/tmp`.

HTTPS cục bộ đã kiểm chứng bằng certificate thử nghiệm có SAN localhost, probe tin cậy CA được chỉ định:

- Nearby 200, validation 422, trailing-slash 307 rồi 200; login/register 200; chat/worker 200; backend dừng trả 502.
- Access log Uvicorn được bật; scan log ứng dụng và proxy không thấy hai sentinel tọa độ giả trong cả success/error/redirect/upstream failure. Tracing bị tắt; không có bằng chứng cho tracing ngoài profile.
- Chromium HTTPS smoke: login UI, GPS giả lập, worker/canvas; không có request HTTP hoặc console mixed content. Browser context bỏ kiểm tra certificate thử nghiệm; đây không phải kiểm thử consent trên thiết bị thật với CA đã trust toàn hệ điều hành.
- `nginx -t`: PASS. Probe chạy lại bằng `scripts/check-gps-https.py`; hướng dẫn ở [https-test-environment.md](https-test-environment.md).

Review chéo của sub-agent tìm ra hai lỗi catalog/redirect privacy đã sửa; reviewer khác không tìm thấy lỗi chặn bổ sung. Hai lượt Antigravity có giới hạn 45 giây đều timeout, **chưa có verdict**; không tính PASS và không lặp vô hạn. Artifact ở `/tmp/gps-remediation-reviews/`.

## Phần chưa xác minh hoặc chưa triển khai

- Chưa kiểm thử Chromium/Firefox có giao diện trên các OS, GPS phần cứng, hộp thoại Allow/Block thật, mạng dây/Wi-Fi hoặc HTTPS từ máy khác với certificate được trust.
- Raster tile chưa hiển thị trong ảnh cuối do DNS host OSM lỗi ở cả Chromium và Firefox. Canvas/worker/markers đã xác minh; raster/provider cần chạy lại khi mạng hoạt động hoặc có provider phù hợp.
- Browser E2E chưa bao phủ mọi ngưỡng throttle và mọi biến thể unmount/navigation; các handler/effect được kiểm tra riêng trong Node runtime tests. Không suy ra browser coverage đầy đủ từ unit tests.
- Geocoding phần B chờ chọn nguồn, điều khoản/chi phí/quyền dữ liệu. Chưa tích hợp dịch vụ ngoài, chưa lưu tọa độ nhập tay như GPS hoặc lịch sử địa chỉ.
- Dữ liệu danh mục vẫn demo/UNVERIFIED; chưa có nguồn được phép dùng cho vận hành, trạng thái trụ trống/bận, booking hoặc điều phối. Tile production và proxy/tracing bên ngoài profile chưa audit.
- Chưa có Antigravity verdict sau timeout. Không bảo đảm độ chính xác GPS desktop.

## Git và tài nguyên

Khi tiếp tục, HEAD đã là `e6b9d9d` trên `feature/ai-khoi`, upstream `origin/feature/ai-khoi`. Phiên này không stage/commit/push; không fetch nên trạng thái remote chỉ dựa trên ref local, không khẳng định remote hiện tại. Các tệp logging/hook thay đổi riêng được giữ nguyên.

Commit có sẵn đã track output `.next-e2e`; đã restore riêng các artifact do lượt này sinh về trạng thái ban đầu, không thay source hoặc phần sửa của người dùng. Runner cuối dùng `.next-gps-e2e`, được `git check-ignore` xác nhận; `.next-e2e` không còn diff. `git diff --check` trên các tệp task: PASS. Phiên tiếp tục sửa 17 tệp tracked và thêm 3 tệp mới (`tsconfig.e2e.json`, `check-gps-https.py`, báo cáo này); danh sách theo nhóm ở trên cũng bao gồm triển khai đã có trong `e6b9d9d`.

Không deploy production hoặc tạo API key. Playwright/browser binaries và image Nginx được cài để kiểm thử; TLS private key thử nghiệm ở `/tmp`, không trong repository. Tài nguyên server/proxy do task khởi chạy được dừng sau kiểm thử; artifact/log/ảnh chỉ chứa dữ liệu giả và nằm ngoài repository. Dependency/browser binaries và image cache được giữ để chạy lại.

## Cập nhật phạm vi browser

Theo yêu cầu người dùng, cấu hình mặc định chỉ chạy Chromium và Firefox (14 tests). Lệnh cài browser trong hướng dẫn chỉ cài hai browser này. Các giới hạn thiết bị thật và raster tile ở trên vẫn còn.

Tệp sửa trong lần thu gọn phạm vi: `frontend/playwright.config.ts` và sáu tài liệu `docs/gps_plans/{limitations-remediation-plan,remediation-verification-report,https-test-environment,gps-agent-implementation-plan,location-feature,completion-report}.md`. Không sửa source UI hoặc dependency dùng chung. Không commit/push.

Kiểm tra sau khi thu gọn: `npm --prefix frontend run test:e2e -- --list` liệt kê đúng 14 tests, chỉ hai project Chromium/Firefox. Lượt chạy mặc định mới dừng ở preflight vì backend đang dùng cổng 18000; không dừng server có sẵn và không tính lượt này là PASS. Muốn chạy lại, dừng phiên thử thủ công rồi chạy `npm --prefix frontend run test:e2e`.

## Ghi nhận bổ sung từ thử thủ công của người dùng

Các tính năng cơ bản đã hoạt động. Tuy nhiên, bản đồ trong web chưa hiển thị chi tiết địa vật/đường phố/tuyến đường, chủ yếu chỉ thấy chấm xanh đỏ và chưa phân biệt rõ điểm đến/vị trí hiện tại. Link mở map ngoài hoạt động; chưa có dẫn đường vẽ trực tiếp trong web. Phản hồi AI sau khi chọn showroom còn cứng. Phạm vi bàn giao/hướng dẫn dành cho user đã đăng nhập; đồng bộ case bắt buộc auth. Địa điểm VinFast vẫn là dữ liệu giả lập, chưa có danh mục thực tế được xác minh.

Đề xuất UI tiếp theo: tự fit cửa sổ khi zoom bằng Ctrl +/-, tránh cắt/che nội dung; bổ sung nhận diện rõ vị trí hiện tại/điểm đến. Chưa triển khai các đề xuất này trong PR. Xem [hướng dẫn dùng GPS](user-guide.md).

## Bàn giao PR — 14/10/2026

Đã tạo [PR #37](https://github.com/AI20K-Build-Phase-Cohort-4/P-142/pull/37), nguồn `feature/gps-desktop-pr`, đích `main`, commit `d019aff`, từ checkout cô lập `/tmp/p142-gps-pr-isolated` dựa trên main mới nhất `8e3a016`. PR gồm 52 tệp GPS liên quan, có [hướng dẫn sử dụng](https://github.com/AI20K-Build-Phase-Cohort-4/P-142/blob/feature/gps-desktop-pr/docs/gps_plans/user-guide.md); không mang hook/logging, dataset, demo riêng hoặc cache build. Commit/push đã hoàn tất trên branch PR; không commit các thay đổi đang sửa tại worktree gốc.

Kiểm thử trên checkout PR: verifier đủ 7 nhóm PASS (55 frontend tests; 48 backend tests theo phạm vi; lint frontend có cảnh báo nền, TypeScript/build PASS); E2E Chromium/Firefox 14/14 PASS ở cổng 18010/13010, giữ nguyên web thủ công. Ruff toàn repository còn 186 finding ngoài các tệp Python được chọn, full pytest chưa chạy. Các giới hạn bản đồ/AI/dữ liệu và đề xuất UI fit khi zoom được ghi rõ trong PR; chưa triển khai đề xuất UI hoặc merge main.

## Cập nhật workflow theo context — 15/10/2026

Bản mới chỉ xin vị trí khi khách yêu cầu tìm địa điểm, dùng snapshot CSV và trả top 5 với nút chỉ đường Google Maps; map thu gọn mặc định. Chi tiết triển khai/kiểm chứng: [update_gps_Oct_15.md](update_gps_Oct_15.md). Cách dùng: [user-guide.md](user-guide.md).
