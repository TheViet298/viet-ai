# VinFast ServiceFlow AI — Frontend Web Application

Giao diện người dùng cho hệ thống tiếp nhận & điều phối sự cố xe điện VinFast (Team VFO2O-18), được xây dựng bằng **Next.js 14 (App Router)**, **TypeScript** và **Tailwind CSS**.

---

## 📱 Các Màn Hình Đã Triển Khai (Theo Đặc Tả Design & Wireframes)

1. **Trang Chủ / Portal Hub (`/`)**  
   Giới thiệu hệ thống, các luồng tiếp nhận và liên kết truy cập nhanh.

2. **Trợ Lý Trực Tuyến Khách Hàng (`/chat`) — SCR-01 & SCR-02 & SCR-03**  
   - Khung chat tiếp nhận sự cố, chọn dòng xe (`VF3`, `VF5`, `VF8`,...).
   - Quick Prompts cho các tình huống mẫu (lỗi sạc trụ Metropolis, hướng dẫn đặt lịch bảo dưỡng).
   - Gợi ý lựa chọn nhanh (Clarification Chips) khi AI cần hỏi làm rõ thông tin kỹ thuật.
   - Thẻ hiển thị Trích dẫn nguồn kiểm chứng chính thức (`SRC-APP-001`).
   - Banner cảnh báo khẩn cấp (Emergency Critical Hotline 1900-232389) khi phát hiện nguy hiểm trên cao tốc.

3. **Hàng Đợi Xử Lý Hồ Sơ Sự Cố (`/console`) — SCR-04A**  
   - Dành cho Cố vấn Dịch vụ / Reviewer.
   - Bộ lọc theo Trạng thái (`Staff Reviewing`, `Needs Information`, `In Progress`) và Mức ưu tiên (`CRITICAL`, `HIGH`, `MEDIUM`).
   - Đánh giá điểm tin cậy của AI (AI Confidence Score).

4. **Chi Tiết Hồ Sơ & Điều Phối HITL (`/console/[id]`) — SCR-04B**  
   - Bảng **Case Brief** chuẩn hóa: Tóm tắt sự cố, dữ kiện kỹ thuật đã bóc tách (SOC, mã lỗi, trụ sạc), hành động gợi ý.
   - Cho phép Reviewer chỉnh sửa trực tiếp thông tin Brief.
   - Các nút thao tác Human-in-the-Loop (HITL): Duyệt & Điều phối, Yêu cầu thêm thông tin, Đóng hồ sơ.
   - Toàn bộ lịch sử hội thoại gốc giữa khách hàng và AI Agent.

---

## 🚀 Hướng Dẫn Cài Đặt & Chạy Local

### Yêu cầu
- Đã cài đặt **Node.js** (khuyến nghị bản LTS $\ge$ 18.17 hoặc 20.x).

### Các bước khởi chạy

1. **Di chuyển vào thư mục frontend:**
   ```bash
   cd frontend
   ```

2. **Cài đặt các gói phụ thuộc:**
   ```bash
   npm install
   ```

3. **Chạy server phát triển (Development Server):**
   ```bash
   npm run dev
   ```

4. **Truy cập ứng dụng:**  
   Mở trình duyệt tại [http://localhost:3000](http://localhost:3000).

---

## ⚙️ Biến Môi Trường

Mặc định frontend kết nối tới FastAPI Backend tại `http://localhost:8000`. Bạn có thể thay đổi bằng cách tạo file `.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## 🏛️ Kiến Trúc Thư Mục (Feature-Based Architecture)

Mã nguồn được tổ chức theo chuẩn **Feature-Based (Domain-Driven)** để dễ mở rộng và làm việc nhóm:

```text
src/
├── features/
│   ├── chat/                        # Toàn bộ nghiệp vụ Chat của Khách hàng
│   │   ├── components/              # ChatFeed, ChatInputBar, ClarificationChips, QuickPromptsBar, EmergencyAlertBanner
│   │   ├── hooks/                   # useChat (quản lý state & logic chat)
│   │   ├── api/                     # chatApi (gọi POST /api/v1/customer/chat)
│   │   ├── types.ts                 # Types nội bộ cho chat & citations
│   │   └── index.ts                 # Export CustomerChatContainer
│   ├── console/                     # Toàn bộ nghiệp vụ Bàn Điều Phối (Staff)
│   │   ├── components/              # TicketTable, TicketCard, TicketFilters, CaseBriefCard, HitlActionBar, ConversationTimeline
│   │   ├── hooks/                   # useTickets, useTicketDetail
│   │   ├── api/                     # consoleApi (gọi GET /tickets, POST /actions)
│   │   ├── types.ts                 # Types nội bộ cho tickets & case briefs
│   │   └── index.ts                 # Export TicketQueueContainer, TicketDetailContainer
│   └── shared/                      # Thành phần dùng chung toàn ứng dụng
│       ├── components/              # Navbar
│       └── index.ts
└── app/                             # Next.js App Router (Thin Wrappers)
    ├── layout.tsx                   # Root layout
    ├── page.tsx                     # Landing portal
    ├── chat/page.tsx                # Renders <CustomerChatContainer />
    └── console/
        ├── page.tsx                 # Renders <TicketQueueContainer />
        └── [id]/page.tsx            # Renders <TicketDetailContainer />
```


## Agent branch integration

The web app uses the develop API contracts under `/api/v1/customer` and `/api/v1/staff`, authenticated through `/api/v1/auth/login`. The stateful agent APIs on `feature/agent-long` are available under `/api/v1/agent/customer` and `/api/v1/agent/staff`; these use configured demo tokens and the agent session store. The lightweight agent chat remains at `/api/v1/chat`.
