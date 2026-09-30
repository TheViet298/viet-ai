# Wireframe Specification & Links

> **Người phụ trách chính:** Việt (UI/UX Lead)  
> **Cập nhật lần cuối:** 2026-09-24  
> **Trạng thái:** In Progress

---

## 1. Thông tin Thiết kế Figma & Phiên bản

* **Figma File URL:** `[Figma Workspace Link - Cập nhật tại đây]`
* **Phiên bản thiết kế:** `v1.0-MVP`
* **Design System / Style:** Dark/Light Mode, Chuẩn màu thương hiệu VinFast (Xanh VinFast Blue `#1E40AF`, Xanh lá sạc pin `#10B981`, Cảnh báo `#EF4444`).

---

## 2. Danh sách Màn hình MVP

| Màn hình # | Tên Màn hình | Đối tượng sử dụng | Mô tả chức năng chính |
| :---: | :--- | :---: | :--- |
| **SCR-01** | **Customer Chat / Intake** | Khách hàng | Khung chat tiếp nhận vấn đề; gửi text và/hoặc ảnh cảnh báo; có Quick Prompts. OCR/Vision chỉ nhận diện dấu hiệu sơ bộ. |
| **SCR-02** | **AI Clarification & Suggestions** | Khách hàng | Giao diện hiển thị câu hỏi làm rõ có kèm các nút bấm lựa chọn nhanh (Mã lỗi, Trụ sạc, Tình trạng xe). |
| **SCR-03** | **Customer Case Status & Brief** | Khách hàng | Màn hình hiển thị Mã Ticket (`CASE-xxx`), Trạng thái tiến độ thời gian thực (Step Tracker), Hướng dẫn an toàn tức thì. |
| **SCR-04** | **Service Agent Console (Staff)** | Nhân viên CSKH/KTV | Gồm 2 Sub-views:<br>• **4A. Ticket Queue:** Lọc danh sách case theo Priority/Status/Intent.<br>• **4B. Ticket Detail:** Xem Case Brief, Chat history, nút Approve / Edit / Reroute / Close. |
| **PUB-01** | **Landing / Knowledge Hub** | Guest | Xem giới thiệu, FAQ, chính sách và link tài liệu VinFast công khai; bấm “Hỏi trợ lý” chuyển Login. |
| **AUTH-01** | **Login / Register** | Customer / Staff | Register chỉ tạo Customer; Staff dùng account seed/invite. |

> Cập nhật cho `SCR-01`: có upload/preview ảnh, trạng thái “AI đang đọc cảnh báo”, cảnh báo không gửi biển số/VIN/khuôn mặt/giấy tờ. `SCR-04B` hiển thị ảnh và OCR/Vision observation trong Ticket Detail.
