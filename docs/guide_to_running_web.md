# Hướng Dẫn Khởi Chạy Website VinFast ServiceFlow AI

Tài liệu hướng dẫn chi tiết các bước thiết lập và khởi chạy toàn bộ hệ thống gồm **Backend (FastAPI)** và **Frontend (Next.js)** trên hệ điều hành Windows.

---

## 1. Yêu cầu Tiên quyết (Prerequisites)

* **Python:** 3.11+ (môi trường ảo đã cài đặt tại `.venv`)
* **Node.js:** v18+ (Node v24.20.0 và npm 11.19.0 cài đặt tại `C:\Program Files\nodejs`)
* **Cấu hình môi trường:**
  * File `.env` tại thư mục gốc dự án.
  * File `frontend/.env.local` chứa cấu hình API Backend:
    ```env
    NEXT_PUBLIC_API_URL=http://localhost:8000
    ```

---

## 2. Bước 1: Khởi chạy Backend (FastAPI Server)

Mở một cửa sổ **PowerShell** tại thư mục gốc `K:\vinai\P-142`:

```powershell
# Cách 1: Kích hoạt môi trường ảo rồi chạy Uvicorn
.venv\Scripts\Activate.ps1
uvicorn src.main:app --reload --port 8000

# Cách 2: Chạy trực tiếp qua binary trong .venv (không cần activate)
.venv\Scripts\uvicorn.exe src.main:app --reload --port 8000
```

* **API Backend:** `http://localhost:8000`
* **Tài liệu Swagger UI tương tác:** `http://localhost:8000/docs`
* **Health Check Endpoint:** `http://localhost:8000/health` (trả về `{"status": "ok", ...}`)

---

## 3. Bước 2: Khởi chạy Frontend (Next.js Web Hub)

Mở một cửa sổ **PowerShell thứ hai** tại thư mục gốc `K:\vinai\P-142`:

```powershell
# 1. Bổ sung Node.js vào biến môi trường PATH (phòng trường hợp terminal chưa nhận diện lệnh node/npm)
$env:PATH = "C:\Program Files\nodejs;" + $env:PATH

# 2. Di chuyển vào thư mục frontend
cd frontend

# 3. Khởi chạy máy chủ phát triển
npm run dev
```

* **Địa chỉ Web Hub:** `http://localhost:3000`

---

## 4. Bước 3: Danh mục Đường dẫn Truy cập

Sau khi cả hai dịch vụ đã khởi động thành công:

| Giao diện / Chức năng | Đường dẫn URL | Mô tả |
| :--- | :--- | :--- |
| **Trang chủ & Tra cứu kiến thức** | [http://localhost:3000](http://localhost:3000) | Giao diện công khai, danh mục bài viết hỗ trợ & chính sách |
| **Khung Chat Khách hàng** | [http://localhost:3000/chat](http://localhost:3000/chat) | Trợ lý AI tiếp nhận yêu cầu, phân loại sự cố & hỏi làm rõ |
| **Bàn làm việc Cố vấn (Staff Console)** | [http://localhost:3000/console](http://localhost:3000/console) | Hàng đợi ticket, duyệt Case Brief, điều phối & chốt case |
| **Theo dõi tiến độ (Track Case)** | [http://localhost:3000/track-case](http://localhost:3000/track-case) | Tra cứu trạng thái xử lý hồ sơ theo mã định danh case |
| **Đăng nhập / Đăng ký demo** | [http://localhost:3000/login](http://localhost:3000/login) | Xác thực số điện thoại OTP cho khách hàng & cố vấn |
| **FastAPI Swagger Docs** | [http://localhost:8000/docs](http://localhost:8000/docs) | Danh mục toàn bộ API endpoints của hệ thống |

---

## 5. Tiện ích: Khởi chạy Nhanh 1 Lệnh (One-Click Launch)

Bạn có thể mở một cửa sổ PowerShell tại `K:\vinai\P-142` và chạy dòng lệnh sau để tự động mở 2 cửa sổ nền cho cả Backend và Frontend:

```powershell
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd K:\vinai\P-142; .venv\Scripts\uvicorn.exe src.main:app --reload --port 8000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd K:\vinai\P-142\frontend; `$env:PATH = 'C:\Program Files\nodejs;' + `$env:PATH; npm run dev"
```

---

## 6. Xử lý Sự cố Thường gặp (Troubleshooting)

1. **Lỗi `'node' is not recognized as an internal or external command`:**
   * Nguyên nhân: Đường dẫn Node.js chưa có trong `PATH` hệ thống.
   * Xử lý: Chạy `$env:PATH = "C:\Program Files\nodejs;" + $env:PATH` trước khi gọi `npm run dev`.
2. **Cổng 8000 hoặc 3000 đang bị chiếm:**
   * Kiểm tra tiến trình đang chiếm cổng:
     ```powershell
     Get-NetTCPConnection -LocalPort 8000, 3000 -ErrorAction SilentlyContinue
     ```
   * Tắt tiến trình cũ hoặc khởi chạy trên cổng khác (ví dụ: `--port 8001` cho FastAPI hoặc `npm run dev -- -p 3001` cho Next.js).

