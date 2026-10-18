# Hướng Dẫn Cài Đặt Môi Trường & Hooks (Linux & Windows)
## Setup Guide: Environment, AI Logging & Git Hooks (Linux & Windows)

Tài liệu này hướng dẫn chi tiết cách thiết lập dự án trên cả **Linux** (Ubuntu/Debian, Fedora, v.v.) và **Windows** (PowerShell), đảm bảo hoạt động đầy đủ hệ thống logging AI tự động, Antigravity Agent, và cơ chế bảo vệ nhánh `feature/ai-khoi`.

---

## 1. Yêu cầu hệ thống (Prerequisites)

### Trên Linux (Ubuntu / Debian / WSL2)
- **Python**: 3.11 trở lên (`python3 --version`)
- **Git**: 2.30 trở lên (`git --version`)
- **Cài đặt các gói cơ bản**:
  ```bash
  sudo apt update
  sudo apt install -y python3 python3-venv python3-pip git dos2unix build-essential
  ```

### Trên Windows
- **Python**: 3.11 trở lên (khuyến nghị tích hợp `py` launcher và tick chọn "Add python.exe to PATH")
- **Git for Windows**: Bao gồm Git Bash (`sh.exe`)
- **PowerShell**: 5.1 trở lên hoặc PowerShell 7+

---

## 2. Clone Repository & Kiểm tra Nhánh

Tất cả các tệp cấu hình hook cho agent và ghi log AI được quản lý **duy nhất** trên nhánh `feature/ai-khoi`.

### Lệnh thực hiện (Dùng chung Linux & Windows):
```bash
# Clone repository
git clone <URL_REPO_GITHUB>
cd P-142

# Chuyển sang đúng branch feature/ai-khoi
git checkout feature/ai-khoi

# Xác nhận nhánh hiện tại
git branch --show-current
# Kết quả phải hiển thị: feature/ai-khoi
```

---

## 3. Cấu hình Line Endings & Quyền Thực Thi (Đặc biệt quan trọng trên Linux)

Nếu repository được checkout từ máy Windows hoặc chứa ký tự xuống dòng CRLF (`\r\n`), các script shell trên Linux sẽ báo lỗi `/usr/bin/env: 'bash\r': No such file or directory`.

### Trên Linux:
Chạy lệnh chuẩn hóa LF và cấp quyền thực thi:
```bash
# Đảm bảo Git không tự động chuyển LF thành CRLF trên Linux
git config core.autocrlf input

# Chuẩn hóa định dạng xuống dòng sang Unix (LF)
dos2unix scripts/*.sh 2>/dev/null || sed -i 's/\r$//' scripts/*.sh scripts/*.py

# Phân quyền thực thi cho các shell scripts
chmod +x scripts/*.sh
chmod +x scripts/_pyrun.sh
```

---

## 4. Thiết lập Môi trường Python (Virtual Environment)

### Trên Linux:
```bash
# 1. Tạo virtual environment
python3 -m venv .venv

# 2. Kích hoạt môi trường
source .venv/bin/activate

# 3. Nâng cấp pip và cài đặt thư viện
pip install --upgrade pip
pip install -r requirements.txt
```

### Trên Windows (PowerShell):
```powershell
# 1. Tạo virtual environment
python -m venv .venv

# 2. Kích hoạt môi trường (nếu gặp lỗi ExecutionPolicy, chạy: Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass)
.venv\Scripts\Activate.ps1

# 3. Nâng cấp pip và cài đặt thư viện
python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

## 5. Cấu hình Biến Môi Trường (`.env`)

Hệ thống ghi log AI yêu cầu endpoint ingest và API key:

### Bước thiết lập:
1. Sao chép từ mẫu:
   - **Linux**: `cp .env.example .env`
   - **Windows**: `Copy-Item .env.example .env`
2. Mở tệp `.env` và xác nhận / điền các giá trị:
   ```env
   # ---- AI Hook Logging ----
   AI_LOG_SERVER=https://ai-logs.note.transformerlabs.ai/api/ingest
   AI_LOG_API_KEY=<dien-api-key-cua-ban>
   AI_LOG_DIR=.ai-log
   ```
3. Tạo thư mục log cục bộ:
   ```bash
   mkdir -p .ai-log && touch .ai-log/.gitkeep
   ```

---

## 6. Thiết lập Git Hooks (Pre-commit & Pre-push)

Do thư mục `.git/hooks/` không được đồng bộ qua Git, mỗi máy mới cần khởi tạo hooks một lần sau khi clone.

Hệ thống sử dụng 2 hooks:
1. **`pre-commit`**: Ngăn chặn commit nhầm các file hook agent / ai-log vào bất kỳ nhánh nào khác ngoài `feature/ai-khoi`.
2. **`pre-push`**: Tự động trích xuất transcript AI và gửi log lên server trước khi đẩy code.

### Lệnh cài đặt tự động (Cài đặt cùng lúc cả Pre-commit và Pre-push):

#### Trên Linux:
```bash
# Cài đặt tự động cả pre-push và pre-commit hooks
bash scripts/setup_hooks.sh

# (Tuỳ chọn) Nếu muốn chạy background watcher cho Codex:
bash scripts/setup_hooks.sh --watch
```

#### Trên Windows (PowerShell):
```powershell
# Cài đặt tự động cả pre-push và pre-commit hooks
powershell -ExecutionPolicy Bypass -File scripts\setup_hooks.ps1

# (Tuỳ chọn) Nếu muốn chạy background watcher cho Codex:
powershell -ExecutionPolicy Bypass -File scripts\setup_hooks.ps1 -Watch
```

---

## 7. Cấu hình Antigravity IDE (Agent Hooks)

- Tệp cấu hình hook của Agent: [`.agents/hooks.json`](file:///k:/vinai/P-142/.agents/hooks.json)
- Lệnh được đăng ký: `bash ../scripts/_pyrun.sh ../scripts/log_antigravity.py --hook`
- **Lưu ý khi mở Antigravity lần đầu**:
  - Giao diện Antigravity IDE sẽ hiển thị popup hỏi: *"Do you trust hook `log-prompt`?"*
  - **Bắt buộc chọn "Allow" / "Trust"** để hook kích hoạt tự động mỗi khi người dùng gửi prompt.
  - Tệp quy tắc [`.agents/rules/git-branch-restriction.md`](file:///k:/vinai/P-142/.agents/rules/git-branch-restriction.md) sẽ tự động nạp vào bộ nhớ agent nhằm đảm bảo agent không bao giờ commit các tệp này sang nhánh khác.

---

## 8. Kiểm Tra & Xác Minh (Verification & Testing)

### 1. Kiểm tra Unit Test của Hệ Thống Log:
- **Linux**:
  ```bash
  python3 -m unittest tests/test_ai_logging.py
  ```
- **Windows**:
  ```powershell
  python -m unittest tests\test_ai_logging.py
  ```

### 2. Kiểm tra Pre-Commit Hook (Quy Tắc Chặn Nhánh):
- **Linux**:
  ```bash
  bash .git/hooks/pre-commit
  # Kiểm tra mã trả về: 0 khi đang ở feature/ai-khoi
  echo $?
  ```
- Thử nghiệm trên nhánh khác (ví dụ `develop`): Nếu stage file trong `.agents/` hoặc `scripts/log_*`, lệnh `git commit` sẽ lập tức bị chặn với thông báo lỗi màu đỏ rõ ràng.

### 3. Kiểm tra Gửi Log Thử Nghiệm (Dry Run):
```bash
# Kiểm tra khả năng kết nối và gửi log không ghi đè
python3 scripts/submit_log.py --dry-run
```

---

## 9. Xử Lý Sự Cố Phổ Biến (Troubleshooting)

| Hiện tượng | Nguyên nhân | Giải pháp |
| :--- | :--- | :--- |
| `bash\r: No such file or directory` | Tệp shell script có ký tự CRLF của Windows | Chạy `sed -i 's/\r$//' scripts/*.sh .git/hooks/*` hoặc cài `dos2unix`. |
| `Permission denied: .git/hooks/pre-commit` | Hook chưa được cấp quyền thực thi trên Linux | Chạy `chmod +x .git/hooks/pre-commit .git/hooks/pre-push`. |
| `No module named fcntl` | Chỉ xảy ra nếu chạy script Linux trên Windows native Python | Code đã tự động chọn `msvcrt` trên Windows và `fcntl` trên Linux. |
| `COMMIT REJECTED BY PRE-COMMIT HOOK` | Đang cố commit tệp restricted khi không ở `feature/ai-khoi` | Chạy `git restore --staged <file>` hoặc chuyển về `git checkout feature/ai-khoi`. |
| Antigravity không tự ghi prompt | Chưa Trust hook khi Antigravity hỏi lần đầu | Mở Antigravity Settings -> Hooks -> Cho phép `log-prompt`. |
