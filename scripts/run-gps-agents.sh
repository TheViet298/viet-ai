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
  2>"$run_dir/plan.stderr" ||
  die "Antigravity lập kế hoạch thất bại; xem $run_dir/plan.stderr"

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
  2>"$run_dir/codex.stderr" ||
  die "Codex triển khai thất bại; xem $run_dir/codex.stderr"

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
  2>"$run_dir/review.stderr" ||
  die "Antigravity rà soát thất bại; xem $run_dir/review.stderr"

jq '.structured_output' "$run_dir/review.json"

jq -e '.status == "SUCCESS" and .structured_output.verdict == "pass"' \
  "$run_dir/review.json" >/dev/null ||
  die "Rà soát chưa đạt; xem $run_dir/review.json và $run_dir/review.stderr"

echo "=== Kết quả cần bạn xem ==="
git status --short --branch
echo "Kế hoạch: $plan"
echo "Nhật ký và báo cáo: $run_dir"
echo "Xem diff, thử trên trình duyệt/điện thoại, rồi quyết định commit."
