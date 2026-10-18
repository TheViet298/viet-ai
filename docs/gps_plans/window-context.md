# Context chuyển cửa sổ — GPS

> **Cập nhật 13/10/2026:** Người dùng đã yêu cầu tiếp tục; bản vá GPS đã hoàn thiện và full verify qua. Antigravity review bản sửa findings PASS; review bổ sung bounding box/hotline bị timeout, phần này đã được coordinator kiểm thử độc lập. Xem [completion-report.md](completion-report.md) để biết tệp sửa, kiểm thử và giới hạn hiện tại. Chưa stage/commit/push hoặc deploy. Phần bên dưới là snapshot bàn giao ngày 12/10, giữ làm lịch sử; không còn mô tả trạng thái dừng hiện tại.

## Trạng thái dừng

Người dùng yêu cầu dừng task và tạo context chuyển cửa sổ. Việc triển khai đã dừng; server Next.js kiểm thử và các phiên Chrome/agent do task này khởi chạy đã kết thúc. Chỉ tiếp tục khi người dùng yêu cầu.

- Branch: `feature/ai-khoi`.
- Upstream: `origin/feature/ai-khoi`.
- HEAD khi dừng: `28f70b68af296174fd14ccd0de381f8b9462b6e0`.
- Bản vá GPS bên dưới chưa stage, commit hoặc push. Không triển khai production.
- Giữ nguyên worktree; không reset, stash, switch hay chạy lại pipeline yêu cầu checkout sạch.

## Mục tiêu và tài liệu

Triển khai GPS theo `docs/gps_plans/location-feature.md` và `docs/gps_plans/agent-workflow.md`, phối hợp với Antigravity. Tham khảo `setup_multi_agent_plan.md` và bản quyết định triển khai `docs/gps_plans/gps-agent-implementation-plan.md`.

Ràng buộc: chỉ lấy vị trí sau khi cho phép; có nhập/chọn địa điểm thủ công; không lưu lịch sử tọa độ mặc định; không tạo API key hoặc deploy production.

## Bản vá hiện có

- Dùng `watchPosition`, có stop/cleanup và bỏ qua callback đến muộn; đồng bộ vị trí case theo ngưỡng 150m/30 giây.
- Thêm nút “Tìm điểm gần đây”, consent, dừng chia sẻ và fallback thủ công.
- Thay bản đồ iframe bằng MapLibre, danh mục điểm dịch vụ, marker, vùng độ chính xác, chỉ đường và vị trí tham chiếu thủ công.
- Thêm API demo GET `/api/v1/customer/service-points/nearby`, kiểm tra tham số, tính khoảng cách Haversine; không ghi DB. Bán kính frontend hiện là 50km.
- Thêm middleware xóa query string khỏi ASGI scope trước lúc Uvicorn ghi access log cho endpoint nearby. Handler vẫn đọc tham số bình thường. Reverse proxy bên ngoài cần cấu hình log riêng.
- Cài `maplibre-gl` `^6.14.0`. npm báo 13 audit vulnerabilities; chưa điều tra nguồn hoặc xử lý.

### Tệp đã sửa

```text
frontend/package-lock.json
frontend/package.json
frontend/src/app/layout.tsx
frontend/src/features/chat/api/chatApi.ts
frontend/src/features/chat/components/CustomerChatContainer.tsx
frontend/src/features/chat/components/LocationConsentCard.tsx
frontend/src/features/chat/components/ServiceMapPanel.tsx
frontend/src/features/chat/constants.ts
frontend/src/features/chat/constants/servicePoints.ts
frontend/src/features/chat/types.ts
frontend/tests/location-consent-flow.test.cjs
src/api/customer.py
src/main.py
src/models/schemas.py
```

### Tệp mới, chưa track

```text
docs/gps_plans/gps-agent-implementation-plan.md
docs/gps_plans/window-context.md
frontend/src/features/chat/utils/locationTracking.ts
src/services/location_privacy.py
tests/test_api/test_location_log_privacy.py
tests/test_api/test_nearby_service_points.py
```

## Lỗi cần sửa trước

Browser thực tế báo:

```text
Error: Worker failed to load. Check that the worker URL is correct.
```

MapLibre 6 ESM cần cấu hình worker URL khi bundle bằng Next/Webpack. Code hiện dynamic import MapLibre nhưng chưa gọi `setWorkerUrl`. Chưa áp dụng bản sửa.

Tài liệu chính thức đã đọc:

- https://maplibre.org/maplibre-gl-js/docs/
- https://maplibre.org/maplibre-gl-js/docs/guides/v5-to-v6-migration-guide/

Ví dụ tài liệu, cần kiểm chứng với cách import hiện tại và Next 14:

```ts
import { Map, setWorkerUrl } from 'maplibre-gl';
setWorkerUrl(new URL('maplibre-gl/dist/maplibre-gl-worker.mjs', import.meta.url).toString());
```

Đặt trước khi tạo map đầu tiên; kiểm tra cả worker và shared dependency trong build/browser.

Các điểm còn lại:

- `ServiceMapPanel.tsx` còn 5 cảnh báo exhaustive-deps: dependency `center` và biểu thức `Boolean(center)`. Cần ổn định dependency mà không tạo lại map mỗi lần GPS cập nhật.
- Canvas quan sát được cao 300px, panel cao hơn; cần kiểm tra resize/layout sau khi worker hoạt động.
- Kiểm tra UX bản đồ sau khi rút gọn panel, timeout GPS, hiển thị lỗi đồng bộ server và trường hợp case tạo sau khi đã có tọa độ.
- Chưa kiểm thử đầy đủ đổi danh mục, manual fallback, request race và bản build.
- Chưa chạy full verify hoặc final review với Antigravity.

## Bằng chứng kiểm thử

Coordinator đã chạy sau các sửa cuối:

```bash
.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_api/test_nearby_service_points.py tests/test_api/test_location_log_privacy.py
# 3 passed in 0.31s
npm --prefix frontend run lint
# exit 0, còn 5 hooks warnings
./frontend/node_modules/.bin/tsc --noEmit --project frontend/tsconfig.json
# exit 0
```

Codex implementation trước đó báo 10 frontend GPS/tracking tests pass, 2 nearby API tests pass và diff check pass; chưa chạy lại toàn bộ các kiểm tra này sau mọi sửa của coordinator.

Chrome headless với geolocation giả xác nhận: không watch trước consent; consent tạo 1 watch; cảnh báo accuracy 850m hiện; stop gọi clearWatch; callback muộn bị bỏ qua; canvas bị gỡ sau stop. **Bản đồ thực tế chưa render đúng vì lỗi worker**, dù DOM có canvas/marker. Đây chưa phải bằng chứng tính năng hoàn tất.

`scripts/verify-gps.sh` chưa chạy trên bản vá hiện tại.

## Phối hợp agent và artifacts tạm

- Đã chạy `./scripts/run-gps-agents.sh --max-repairs 1 --agent-timeout 600 --verify-timeout 900`.
- Antigravity lập kế hoạch nhưng trả blocked vì hỏi lại quyết định thuộc scope đã được cho phép. Coordinator tiếp tục với 4 danh mục, split view, vị trí tham chiếu thủ công và MapLibre.
- Codex triển khai qua runner tạm; còn chờ Antigravity review code/kết quả kiểm thử.
- Plan artifacts: `/tmp/gps-agents-a_vvezyj/plan.stdout`, `/tmp/gps-agents-a_vvezyj/result.json`.
- Implementation artifacts: `/tmp/gps-implementation-zy_u_tmv/implementation.result.json`.
- Runner: `/tmp/continue-gps-implementation.py`.
- Browser harness: `/tmp/gps-browser-check.py`.
- Screenshot cuối đã xem: `/tmp/gps-browser-j6e18gla/gps.png` (map trống).

Các tệp `/tmp` có thể biến mất. Không chép raw agent logs, hội thoại hoặc thông tin nhạy cảm vào repo.

## Trình tự tiếp tục khi được yêu cầu

1. Đọc hướng dẫn repo và context này; kiểm tra lại branch/upstream/status và diff thực tế.
2. Sửa worker MapLibre trên bản vá hiện có, rồi xác nhận browser render đúng.
3. Xử lý dependency warnings, kích thước bản đồ và các lỗi lifecycle còn lại.
4. Chạy test trọng tâm rồi `scripts/verify-gps.sh`; chỉ mở rộng kiểm thử để giải quyết rủi ro còn cụ thể.
5. Gửi diff và kết quả cho Antigravity review, xử lý findings trong phạm vi GPS. Không chạy lại workflow từ đầu trên worktree bẩn.
6. Báo tệp sửa, kiểm thử, giới hạn và trạng thái commit/push rõ ràng.

Prompt gợi ý cho cửa sổ mới (chưa thực thi):

> Đọc AGENTS.md, .agents/memory/INDEX.md và docs/gps_plans/window-context.md. Tiếp tục bản vá GPS hiện có theo docs/gps_plans/location-feature.md; sửa MapLibre worker trước, chạy kiểm thử và tự làm việc với Antigravity. Giữ worktree hiện có; không khởi động lại workflow yêu cầu checkout sạch.
