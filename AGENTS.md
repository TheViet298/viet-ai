# Project guide

- Start from `.agents/memory/INDEX.md`; only load the memory and documents specifically relevant to the current task. Read `README.md` during onboarding, when an overview is needed, or when the memory does not match the repository.
- Do not recursively read the entire Markdown/codebase. For the current behavior, inspect only the relevant code and tests; memory and documentation should serve only as guidance or to record decisions.
- Before any Git operation, report the branch, upstream, and `git status --short --branch`.
- Before concluding that there is a conflict, identify the target branch and update the remote refs if permitted.
- Distinguish between files changed together and conflicts confirmed by Git.
- When the worktree has uncommitted changes, do not merge, reset, stash, or switch branches on your own.
- Do not add secrets, personal logs, or sensitive data to documentation or memory.
- At the end of the task, clearly record which files were modified, what tests were run, and whether commit and push were completed.

---

- Mục tiêu: thêm vị trí hiện tại để tìm địa điểm gần người dùng và chỉ đường.

- Chỉ lấy vị trí sau khi người dùng chọn cho phép.

- Luôn có cách nhập/chọn địa điểm thủ công nếu họ từ chối quyền.

- Không lưu lịch sử tọa độ mặc định.

- Mỗi thay đổi phải nêu tệp đã sửa, cách kiểm thử và giới hạn còn lại.

- Không tự triển khai production hoặc tạo khóa API.
