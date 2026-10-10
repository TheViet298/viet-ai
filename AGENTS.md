# Project guide

- Bắt đầu từ `.agents/memory/INDEX.md`; chỉ nạp memory và tài liệu được chỉ tới cho task hiện tại. Đọc README.md khi onboarding, khi cần overview, hoặc khi memory không khớp repo.
- Không đọc đệ quy toàn bộ Markdown/codebase. Với hành vi hiện tại, kiểm tra code và test liên quan; memory và tài liệu chỉ là chỉ đường hoặc ghi nhận quyết định.
- Trước mọi thao tác Git: báo branch, upstream và `git status --short --branch`.
- Trước khi nhận định có conflict: xác định branch đích và cập nhật remote ref nếu được phép.
- Phân biệt file cùng thay đổi với conflict được Git xác nhận.
- Khi worktree có thay đổi chưa commit, không tự merge, reset, stash hoặc chuyển branch.
- Không đưa secret, log cá nhân hay dữ liệu nhạy cảm vào tài liệu/memory.
- Khi kết thúc task: ghi rõ file đã sửa, kiểm thử, commit và push đã thực hiện hay chưa.
