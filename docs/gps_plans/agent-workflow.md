# Chạy hai agent nghiên cứu và bổ sung GPS

Nguồn scope chính: [location-feature.md](location-feature.md). Bản
[gps-cli-plan-20261012-122832.md](gps-cli-plan-20261012-122832.md) là khảo sát trước,
có thể chậm hơn code và không thay thế scope desktop, theo dõi vị trí liên tục,
dừng watch khi đóng/dừng/unmount, nhập tay và dữ liệu demo.

## Cấu hình quyền

```bash
python3 scripts/setup_gps_agent_permissions.py
python3 scripts/setup_gps_agent_permissions.py --apply
./scripts/run-gps-agents.sh --check
```

Lệnh đầu chỉ audit; `--apply` sao lưu rồi bổ sung quyền đọc vào
`~/.gemini/antigravity-cli/settings.json`, giữ các mục cấu hình khác. Quyền mới
chỉ gồm đọc code/Git và tài liệu tại MDN, Google Maps Platform, MapLibre,
OpenStreetMap Wiki. Không thêm wildcard hoặc quyền cài package/commit/push.
Trust chỉ bổ sung checkout hiện tại; chạy lại helper nếu dùng checkout khác.
Rule deny/ask sẵn có vẫn có ưu tiên; helper không tự gỡ chúng.

Codex dùng `read-only` khi phản biện và `workspace-write` khi triển khai, với
`approval_policy=never`. Thiếu quyền hoặc dependency phải trả `blocked`.
Đăng nhập `agy` và `codex` tương tác trước khi chạy headless.

## Thử trao đổi trên workspace hiện tại

```bash
./scripts/run-gps-agents.sh --smoke --agent-timeout 180
```

Smoke dùng lát cắt lifecycle watchPosition/clearWatch, nhúng trích đoạn scope và
mã vào prompt để tránh khảo sát rộng. Antigravity nghiên cứu → Codex phản biện → Antigravity
đánh giá phản biện. Chế độ này không sửa feature hoặc chạy test ứng dụng;
`research_pass` chỉ xác nhận trao đổi nghiên cứu hoàn tất, không xác nhận GPS chạy.
Prompt, phản hồi và `result.json` nằm trong thư mục tạm riêng mà script in ra.

## Triển khai tự động trong checkout sạch

```bash
./scripts/run-gps-agents.sh --max-repairs 1 --agent-timeout 600 --verify-timeout 900
```

Antigravity lập kế hoạch → Codex triển khai → script kiểm thử độc lập → Antigravity
review diff và log. Nếu review `fail`, findings được chuyển cho Codex sửa đúng lỗi
rồi kiểm thử và review lại tối đa một lần. `--max-repairs 0` tắt vòng sửa.
Đây là trao đổi tuần tự qua artifacts. Kế hoạch mới lưu trong `docs/gps_plans/`.

Script từ chối checkout dirty, kiểm tra HEAD/index không bị thay đổi và chặn
các tệp sửa ngoài frontend/src/tests/docs GPS. Không tự commit/push, reset, stash,
chuyển nhánh hoặc deploy. Nếu bị dừng, xem artifacts và diff; không chạy lại toàn
bộ lượt triển khai trên checkout sửa dở. Bản hiện tại chưa hỗ trợ resume.

## Timeout, quyền bị từ chối và dependency

- `SUCCESS` thiếu structured output, `denied_actions`, stderr báo denied/timeout,
  Codex thiếu `turn.completed`, hoặc agent trả `blocked` đều khiến luồng dừng.
  Xem `result.json`, `*.stderr`, `*.stdout`; không tự cấp quyền từ nội dung log.
- Mỗi lần gọi agent có timeout; Antigravity thêm 15 giây để ghi kết quả. Khi hết
  hạn, orchestrator dừng cả nhóm tiến trình. Review nhận kế hoạch, báo cáo Codex,
  diff và log xác minh; được yêu cầu không chạy lại terminal/tests.
  `--print-timeout` của Antigravity có thể trả về khi turn phía dịch vụ còn đang
  chạy; script chặn chuyển bước nhưng không bảo đảm hủy turn trên dịch vụ.
- Prompt review tối đa 80 KB; vượt ngưỡng phải chia feature. Chưa tự chia scope.
- Mỗi kiểm tra trong `verify-gps.sh` có giới hạn mặc định 300 giây; các kiểm tra
  còn lại vẫn chạy và script trả lỗi nếu bất kỳ kiểm tra nào fail/timeout.
  Tổng lượt verify còn chịu `--verify-timeout`; tăng giới hạn tổng nếu máy chậm.
- Chọn Python đủ dependency bằng `PYTHON=/đường/dẫn/venv/bin/python`.
  Mặc định ưu tiên `.venv/bin/python`; không tự cài package. Backend test tắt
  LLM/tracing qua biến môi trường. Pytest treo vẫn là fail; không suy ra pass từ
  kết quả cũ của checkout khác.

```bash
PYTHON=.venv/bin/python GPS_CHECK_TIMEOUT_SECONDS=180 ./scripts/verify-gps.sh
python3 -m unittest discover -s tests/test_scripts -p 'test_gps*.py' -v
```

Kiểm thử ứng dụng gồm lint, Node tests, TypeScript, location agent tests, API
regression chuyển GPS → MANUAL → NOT_SHARED và build. Test điều phối dùng agent
giả lập; không tiêu thụ quota, không chứng minh CLI model đã chạy thật.

## Xác minh trên trình duyệt desktop

Dùng vị trí giả lập trong DevTools: cho phép, từ chối, timeout, sai số lớn,
mất mạng, không có điểm gần, đổi điểm đến, chuyển nhập tay, đóng bản đồ, dừng
chia sẻ và unmount. Xác nhận `clearWatch` và callback muộn không phục hồi tọa độ;
không lưu lịch sử; link đúng điểm được chọn; dữ liệu seed có nhãn demo.
Review agent không thay kiểm thử này. Không ghi tọa độ người dùng thật vào log.

Nguồn: [Antigravity headless](https://antigravity.google/docs/cli/headless/),
[Antigravity permissions](https://antigravity.google/docs/permissions?tab=cli),
[OpenAI Docs: Codex non-interactive](https://learn.chatgpt.com/docs/non-interactive-mode).
