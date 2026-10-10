---
name: branch-audit-template
description: Mẫu kiểm tra branch và khả năng tích hợp với branch đích khi người dùng yêu cầu audit Git hoặc hỏi về conflict.
---

# Branch audit template

Kiểm tra trên các ref hiện có ở local. Kết quả không xác nhận trạng thái hiện tại trên GitHub.

## Đầu vào

- Branch đích: `main`; so sánh với `origin/main` đang có ở local. Nếu người dùng chỉ định branch khác, dùng branch đó.
- Phạm vi: chỉ kiểm tra local, không fetch. Ghi rõ commit và thời điểm cập nhật của remote ref nếu xác định được; nếu không xác định được, nói rõ điều đó.
- Thao tác được phép: các lệnh Git đọc trạng thái và lịch sử như `status`, `branch`, `rev-parse`, `log`, `diff`, `rev-list`, `merge-base`; preview merge trong bản sao tạm mà không đổi checkout gốc.
- Khi nào cần hỏi: thiếu branch đích hoặc cần dữ liệu remote mới để kết luận; trước `pull`, `merge`, `push`, tạo PR, xóa branch hay sửa file nếu chưa được người dùng ủy quyền.

## Trình tự

1. Áp dụng `AGENTS.md` và giới hạn Git của repo. Báo branch, upstream và `git status --short --branch` trước thao tác Git.
2. Xác định branch đích và ghi rõ hai commit được so sánh. Không fetch trong phạm vi skill này. Nếu dùng `origin/main`, nêu rõ đây là remote ref lưu tại local và có thể đã cũ.
3. Dùng `git rev-list --left-right --count <target>...HEAD` để đếm commit riêng mỗi phía. Dùng `git diff --name-only <target>...HEAD` để xem file thuộc thay đổi của branch hiện tại; không coi danh sách này là bằng chứng conflict. Nếu cần tìm file cả hai phía cùng sửa, so sánh mỗi phía với merge base.
4. Preview merge hai commit trong bản sao tạm, không đổi branch hoặc worktree gốc. Ghi rõ phương pháp, hai commit đầu vào và kết quả Git trả về. Nếu không preview được, báo `chưa xác định` thay vì suy đoán conflict.
5. Khi worktree có thay đổi chưa commit, tuân thủ `AGENTS.md`; không tự merge, reset, stash hoặc chuyển branch.

## Mẫu trả lời

- Branch hiện tại / upstream: `[giá trị trực tiếp]`
- Worktree: `[sạch hoặc tóm tắt thay đổi]`
- Branch đích / ref / commit / độ mới của ref: `[giá trị trực tiếp; nêu nếu chưa xác minh GitHub]`
- Quan hệ commit: `[kết quả]`
- File cùng thay đổi: `[danh sách hoặc không có]`
- Conflict được Git xác nhận: `[kết quả và phương pháp; hoặc chưa xác định]`
- Bước tiếp theo: `[đề xuất trong phạm vi]`

Không lưu kết quả audit vào skill: trạng thái Git thay đổi theo thời gian.
