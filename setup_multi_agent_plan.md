Được. Sau vòng thử trong VS Code, bạn nên tự động hóa theo chuỗi **Antigravity lập kế hoạch → Codex viết mã → chạy kiểm thử → Antigravity rà soát**. Mỗi bước lưu kết quả và chỉ chạy bước kế tiếp khi bước trước thành công. Hai CLI hỗ trợ kiểu chạy này: Antigravity dùng `agy -p` và JSON output; Codex dùng `codex exec` và JSONL output. [Antigravity headless](https://antigravity.google/docs/cli/headless/), [Codex non-interactive](https://learn.chatgpt.com/docs/non-interactive-mode)

Dưới đây là bản thiết lập cho Linux. Nó **không tự commit, push hoặc deploy**.

## Bước 1: kiểm tra công cụ và đăng nhập

Trong terminal VS Code:

```bash
command -v agy codex git jq
agy --version
codex --version
```

Nếu thiếu `jq`, trên Ubuntu/Debian cài bằng `sudo apt install jq`. Chạy `agy` và `codex` tương tác ít nhất một lần để hoàn tất đăng nhập. Lượt chạy headless của Antigravity cần thông tin đăng nhập đã lưu; nếu chưa có, nó báo lỗi thay vì mở quy trình đăng nhập tương tác. [Antigravity installation and auth](https://antigravity.google/docs/cli/install/), [Antigravity headless](https://antigravity.google/docs/cli/headless/)

Trước khi cho agent sửa repo, xem nhánh và trạng thái:

```bash
git branch --show-current
git rev-parse --abbrev-ref --symbolic-full-name '@{upstream}'
git status --short --branch
```

Nếu đang có thay đổi chưa commit từ vòng VS Code vừa rồi, hãy hoàn tất hoặc đặt chúng vào một checkout riêng theo cách bạn chọn **trước khi chạy script dưới đây**. Script sẽ dừng khi checkout không sạch; nó không stash, reset hoặc chuyển nhánh.

## Bước 2: tạo lệnh kiểm thử riêng của dự án

Tạo `scripts/verify-gps.sh`. Ví dụ **chỉ dành cho dự án Node có các script tương ứng**:

```bash
#!/usr/bin/env bash
set -euo pipefail

npm run lint
npm test
npm run build
```

Sau đó:

```bash
chmod +x scripts/verify-gps.sh
./scripts/verify-gps.sh
```

Hãy sửa ba lệnh cho đúng `package.json` của dự án. Nếu một lệnh chưa tồn tại, đừng giữ nguyên ví dụ. Chạy bước này một lần trước khi tự động hóa để biết trạng thái kiểm thử ban đầu.

## Bước 3: tạo script điều phối

Tạo `scripts/run-gps-agents.sh` với nội dung sau:

```bash
#!/usr/bin/env bash
set -Eeuo pipefail

die() {
  echo "DỪNG: $*" >&2
  exit 1
}

command -v agy >/dev/null || die "Chưa tìm thấy agy"
command -v codex >/dev/null || die "Chưa tìm thấy codex"
command -v jq >/dev/null || die "Chưa tìm thấy jq"
[[ -f AGENTS.md ]] || die "Hãy chạy script từ thư mục gốc của repo"
[[ -x scripts/verify-gps.sh ]] || die "Thiếu scripts/verify-gps.sh hoặc chưa chmod +x"

echo "=== Git preflight ==="
echo "Branch: $(git branch --show-current)"
echo "Upstream: $(git rev-parse --abbrev-ref --symbolic-full-name '@{upstream}' 2>/dev/null || echo 'chưa đặt')"
git status --short --branch

[[ -z "$(git status --porcelain)" ]] ||
  die "Checkout có thay đổi. Giữ nguyên chúng và chạy trên checkout sạch."

stamp="$(date +%Y%m%d-%H%M%S)"
run_dir="$(mktemp -d "${TMPDIR:-/tmp}/gps-agents.XXXXXX")"
mkdir -p docs/plans
plan="docs/plans/gps-cli-plan-${stamp}.md"

echo "Nhật ký: $run_dir"
echo "Kế hoạch: $plan"

plan_prompt="$(cat <<'PROMPT'
Đọc AGENTS.md và chỉ các tệp mã/kiểm thử liên quan đến vị trí, địa điểm
gần người dùng và chỉ đường. Lập kế hoạch có thể thực hiện cho tính năng GPS
trên web. Phải bao gồm: luồng xin quyền vị trí, cách nhập vị trí thủ công,
xử lý timeout/độ chính xác thấp, nguồn địa điểm, cách tính tuyến, bảo vệ dữ
liệu vị trí, tệp dự kiến sửa và các kiểm thử. Nêu rõ giả định và việc còn
thiếu. Chỉ lập kế hoạch; không sửa mã, không commit hoặc push.
PROMPT
)"

echo "=== 1/4 Antigravity lập kế hoạch ==="
agy --mode=plan \
  -p "$plan_prompt" \
  --output-format json \
  --print-timeout 15m \
  >"$run_dir/plan.json" \
  2>"$run_dir/plan.stderr"

jq -e '.status == "SUCCESS" and ((.response // "") | length > 100)' \
  "$run_dir/plan.json" >/dev/null ||
  die "Antigravity không trả về kế hoạch thành công; xem $run_dir/plan.stderr"

jq -r '.response' "$run_dir/plan.json" >"$plan"

echo "=== 2/4 Codex triển khai ==="
codex exec \
  --sandbox workspace-write \
  --json \
  "Đọc AGENTS.md và $plan. Đối chiếu kế hoạch với mã hiện có rồi triển khai \
tính năng trong phạm vi kế hoạch. Chạy kiểm thử liên quan. Nếu thiếu quyết định \
quan trọng thì báo rõ và dừng phần phụ thuộc. Giữ nguyên công việc không liên \
quan. Không commit, push hoặc deploy. Cuối cùng báo tệp đã sửa, kiểm thử và \
giới hạn còn lại." \
  >"$run_dir/codex.jsonl" \
  2>"$run_dir/codex.stderr"

jq -es '
  any(.[]; .type == "turn.completed") and
  all(.[]; .type != "turn.failed" and .type != "error")
' "$run_dir/codex.jsonl" >/dev/null ||
  die "Codex chưa hoàn tất thành công; xem $run_dir/codex.stderr"

echo "=== 3/4 Kiểm thử độc lập ==="
scripts/verify-gps.sh >"$run_dir/verify.log" 2>&1 ||
  die "Kiểm thử thất bại; xem $run_dir/verify.log"

git diff --check ||
  die "Diff có lỗi khoảng trắng hoặc bản vá; hãy kiểm tra lại"

cat >"$run_dir/review.schema.json" <<'JSON'
{
  "type": "object",
  "properties": {
    "verdict": {"type": "string", "enum": ["pass", "fail"]},
    "findings": {"type": "array", "items": {"type": "string"}}
  },
  "required": ["verdict", "findings"],
  "additionalProperties": false
}
JSON

echo "=== 4/4 Antigravity rà soát ==="
agy --mode=plan \
  -p "Đọc AGENTS.md, $plan và mã hiện tại. Rà soát tính năng GPS vừa triển khai. \
Kiểm tra đặc biệt: xin quyền trước khi đọc vị trí, phương án nhập thủ công, \
tọa độ lỗi/timeout, dữ liệu vị trí có bị lưu hoặc ghi log ngoài ý muốn, \
địa điểm và tuyến đường có đúng nguồn. Chỉ đánh giá, không sửa mã. \
Trả verdict=fail nếu có lỗi cần sửa; findings phải nêu tệp và vấn đề cụ thể." \
  --output-format json \
  --json-schema "$run_dir/review.schema.json" \
  --print-timeout 15m \
  >"$run_dir/review.json" \
  2>"$run_dir/review.stderr"

jq '.structured_output' "$run_dir/review.json"

jq -e '.status == "SUCCESS" and .structured_output.verdict == "pass"' \
  "$run_dir/review.json" >/dev/null ||
  die "Rà soát chưa đạt; xem $run_dir/review.json và $run_dir/review.stderr"

echo "=== Kết quả cần bạn xem ==="
git status --short --branch
echo "Kế hoạch: $plan"
echo "Nhật ký và báo cáo: $run_dir"
echo "Xem diff, thử trên trình duyệt/điện thoại, rồi quyết định commit."
```

Cho phép chạy:

```bash
chmod +x scripts/run-gps-agents.sh
```

**Lưu ý:** Đây là mẫu để bạn tạo trong repo của mình; tôi chưa chạy nó với mã của bạn. Các đường dẫn `scripts/` và lệnh kiểm thử có thể cần chỉnh theo cấu trúc dự án.

## Bước 4: chạy một lượt

Từ thư mục gốc repo:

```bash
./scripts/run-gps-agents.sh
```

Khi script kết thúc, xem:

```bash
git status --short --branch
git diff --stat
git diff
```

Kế hoạch được lưu trong `docs/plans/`; JSON, thông báo lỗi và log kiểm thử được lưu trong thư mục tạm mà script in ra. Nếu bước rà soát báo `fail`, đọc các `findings`, cho Codex sửa đúng các lỗi đó rồi chạy lại kiểm thử. **Đừng chạy lại toàn bộ script trên checkout đang có thay đổi**, vì nó được thiết kế để bắt đầu một nhiệm vụ mới từ trạng thái sạch.

## Bước 5: cấu hình quyền và xử lý lỗi thường gặp

- **Antigravity báo `SUCCESS` nhưng không chạy được công cụ:** headless có thể từ chối mềm một công cụ cần phê duyệt và vẫn thoát với mã `0`. Kiểm tra `plan.stderr` hoặc `review.stderr`. Nếu thực sự cần lệnh terminal, cấp quyền có phạm vi hẹp trong `~/.gemini/antigravity-cli/settings.json`; không dùng `--dangerously-skip-permissions` để mở toàn bộ quyền. [Tài liệu quyền headless](https://antigravity.google/docs/cli/headless/)
- **Codex không cài được package hoặc không truy cập mạng:** `workspace-write` chỉ cho phép sửa trong workspace theo chính sách sandbox. Cho agent báo dependency cần cài, cài hoặc duyệt quyền theo môi trường của bạn, rồi chạy tiếp. Tránh chuyển sang `danger-full-access` chỉ để vượt qua một lỗi chưa xác định. [Tài liệu Codex exec](https://learn.chatgpt.com/docs/non-interactive-mode)
- **Review báo đạt nhưng luồng GPS vẫn sai:** `verdict` là đánh giá của agent, không thay thế kiểm thử trên thiết bị thật. Thử ít nhất: cho phép vị trí, từ chối, vị trí không chính xác, mất mạng, không có địa điểm gần, đổi điểm đến và dừng theo dõi.
- **Log chứa tọa độ thật:** dùng tọa độ giả lập trong prompt và test; đừng ghi tọa độ người dùng thật vào tệp kế hoạch, báo cáo agent hoặc log lâu dài.

Sau khi một vài lượt chạy ổn định, bạn mới nên thêm **một vòng sửa tự động có giới hạn**: nếu review `fail`, chuyển `findings` cho Codex, chạy `verify-gps.sh` lần nữa, rồi Antigravity review lại. Giới hạn ở một vòng sửa và dừng khi vẫn không đạt để tránh hai agent lặp vô hạn.

**Trạng thái:**  chỉ cung cấp hướng dẫn và script mẫu; chưa sửa tệp, chưa chạy kiểm thử, chưa commit hoặc push trong repo