# Bộ Dữ Liệu Nhận Diện Ảnh Cảnh Báo Táp-lô Cho Chatbot (VinFast EV Dashboard Warning Dataset)

> **Đường dẫn dataset:** `dataset/img_warning_taplo/`  
> **Nhánh phát triển:** `feature/dataset-img-warning-taplo` (target PR: `develop`)  
> **Ngày thiết lập:** 04/10/2026  
> **Tài liệu căn cứ:** `docs/plans/2026-10-04-dashboard-warning-vision.md` (Gate G2 / PR #21)

---

## 1. Mục tiêu và Phạm vi Dataset

Bộ dữ liệu này được thiết kế để phục vụ tính năng **nhận diện và giải thích ảnh đèn/biểu tượng cảnh báo táp-lô** (Dashboard Cluster & Central Display Warning Signs) cho chatbot hỗ trợ khách hàng ô tô điện VinFast.

### Mục tiêu kỹ thuật
1. **Phân loại triệu chứng thị giác (Visual Symptoms):** Đọc biểu tượng, màu sắc đèn (đỏ, vàng, xanh, trắng), trạng thái (sáng liên tục, nhấp nháy), và thông điệp chữ (text/code) hiển thị trên táp-lô/màn hình giải trí trung tâm.
2. **Gắn nhãn mức độ nghiêm trọng (Severity Labeling):** Chuẩn hóa mức độ rủi ro an toàn kỹ thuật theo 5 cấp độ (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `UNKNOWN`), từ đó kích hoạt hành động xử lý an toàn và luồng điều hướng của chatbot.
3. **Phản hồi hướng dẫn an toàn chuẩn mực:** Cung cấp thông điệp phản hồi từng bước cho người lái (đỗ xe an toàn, kiểm tra lốp, gọi hotline cứu hộ, đặt lịch xưởng dịch vụ).
4. **Đối chiếu nguồn sổ tay chính thức:** Mỗi cảnh báo gắn liền với nguồn tài liệu VinFast chính hãng đã kiểm chứng, không suy diễn thiếu căn cứ.

---

## 2. Nguồn và Danh mục Ảnh Đã Khảo Sát

Căn cứ theo mục **2. Nguồn và ảnh đã tìm được** trong kế hoạch `2026-10-04-dashboard-warning-vision.md`:

### 2.1. Nguồn tài liệu chính hãng
| Tên nguồn | URL | Giá trị sử dụng | Giới hạn |
|---|---|---|---|
| Danh mục ô tô điện VinFast | <https://vinfastauto.com/vn_vi/san-pham> | Kiểm kê danh mục mẫu xe chính thức (EV cá nhân & dịch vụ) | Không phải danh mục mã lỗi |
| Cổng sổ tay ô tô VinFast | <https://vinfastauto.com/vn_vi/tai-lieu-o-to> | Điểm bắt đầu tra cứu sổ tay người dùng chính thức theo mẫu/đời xe | Cần chọn đúng phiên bản phần mềm/đời xe |
| Bài về đèn táp-lô | <https://vinfastauto.com/vn_vi/y-nghia-cua-cac-loai-den-bao-o-to> | Khảo sát thuật ngữ chuẩn tiếng Việt và hình ảnh chung | Bài viết cũ gồm cả xe xăng, không áp dụng toàn bộ cho EV |
| Cảnh báo TPMS VF e34 | <https://vinfastauto.com/vn_vi/canh-bao-ap-suat-lop-tren-vf-e34> | Bảng ký hiệu cảnh báo TPMS gắn riêng cho dòng VF e34 | Chỉ bao gồm hệ thống TPMS |
| Đèn cảnh báo trên VF e34 | <https://vinfastauto.com/vn_vi/den-canh-bao-tren-vf-e34> | Danh mục 16 loại đèn cảnh báo thường gặp trên VF e34 | Nguồn tham chiếu thuật ngữ |
| Hệ thống TPMS VinFast VF 8 | <https://vinfastauto.com/vn_vi/he-thong-giam-sat-ap-suat-lop-o-to-vinfast-vf-8> | Bảng mô tả hoạt động và cảnh báo TPMS trên VF 8 | Cần đối chiếu với sổ tay xe thực tế |

### 2.2. Danh mục ảnh tham chiếu đã xác định trong kế hoạch
| STT | Tên ảnh / Mô tả | URL ảnh gốc | Định dạng / Kích thước | Ứng dụng |
|---|---|---|---|---|
| 1 | Cụm màn hình táp-lô hiển thị lỗi TPMS VF e34 | `https://static-cms-prod.vinfastauto.com/ky-hieu-canh-bao-loi-ap-suat-lop-tren-vf-e34_1652457282.jpg` | JPG (ảnh thực tế xe) | Benchmark cụm màn hình hiển thị 4 bánh và thông số áp suất |
| 2 | Biểu tượng cảnh báo áp suất lốp thấp | `https://static-cms-prod.vinfastauto.com/ap-suat-lop-1_1652627856.png` | PNG (biểu tượng icon) | Benchmark nhận diện icon đèn TPMS vàng có dấu chấm than |
| 3 | Biểu tượng lỗi cảm biến áp suất lốp | `https://static-cms-prod.vinfastauto.com/ap-suat-lop-5_1652627955.png` | PNG (biểu tượng icon) | Benchmark nhận diện lỗi truyền tín hiệu cảm biến |

> **Chính sách bản quyền & quyền sử dụng:** Các URL trên được lưu trữ làm tham chiếu nguồn xác thực (source reference). Bộ dữ liệu tuân thủ nguyên tắc không tải bừa bãi dữ liệu chưa cấp phép vào repo công khai; tập ảnh benchmark thực tế sẽ dùng ảnh khách hàng đã ẩn danh và có thỏa thuận cấp phép.

---

## 3. Danh Sách Mẫu Xe Tuyển Chọn

Dựa trên khảo sát độ phủ dữ liệu tại mục **3. Danh sách mẫu xe và cảnh báo**:

1. **VinFast VF e34 (Mẫu trọng tâm - C-SUV EV):**
   - Xe điện thương mại đầu tiên của VinFast tại Việt Nam.
   - Có bài hướng dẫn chính thức riêng biệt từ VinFast về hệ thống TPMS và danh mục 16 đèn cảnh báo táp-lô.
   - Màn hình thông tin lái (Cluster Display) 7 inch hiển thị trực quan thông số từng bánh xe.
2. **VinFast VF 8 (Mẫu mở rộng 1 - D-SUV EV):**
   - Mẫu xe điện toàn cầu chủ lực của VinFast.
   - Có cổng sổ tay hướng dẫn người dùng chính hãng chi tiết và bài viết kỹ thuật TPMS chính thức.
   - Táp-lô hiển thị qua màn hình trung tâm 15.6 inch và màn hình HUD kính lái.
3. **VinFast VF 5 Plus (Mẫu mở rộng 2 - A-SUV EV):**
   - Dòng xe điện đô thị phổ biến bậc nhất hiện nay tại Việt Nam.
   - Có sổ tay hướng dẫn sử dụng tiếng Việt chính thức tại cổng tài liệu ô tô VinFast.
   - Cụm màn hình công-tơ-mét 7 inch độc lập hiển thị đèn và thông số TPMS.

Các mẫu xe còn lại (VF 3, VF 6, VF 7, VF 9, Minio Green, v.v.) hiện chưa có ma trận đối chiếu sổ tay đầy đủ; hệ thống chatbot sẽ phân loại về `UNKNOWN` kèm chuyển tiếp Staff Review thay vì suy đoán tự động.

---

## 4. Danh Sách Cảnh Báo & Chuẩn Hóa Nhãn Nghiêm Trọng (Severity)

### 4.1. Khung phân loại mức độ nghiêm trọng (Severity Hierarchy)
* `CRITICAL` (**Khẩn cấp - Đỏ**): Nguy cơ tai nạn hoặc hỏng hóc nặng ngay tức thì. Chatbot lập tức phát cảnh báo khẩn cấp, hướng dẫn dừng xe nơi an toàn, cung cấp hotline cứu hộ 24/7 (1900 23 23 89) và kích hoạt case ưu tiên cao (Staff Review).
* `HIGH` (**Cần hỗ trợ sớm - Cam/Đỏ**): Sự cố kỹ thuật quan trọng ảnh hưởng trực tiếp đến khả năng vận hành hoặc giảm độ an toàn (ví dụ: rò rỉ áp suất lốp nhanh, rùa vàng giới hạn công suất, lỗi pin cao áp). Chatbot hướng dẫn các bước xử lý ban đầu và điều hướng đến xưởng dịch vụ gần nhất.
* `MEDIUM` (**Cần kiểm tra - Vàng/Hổ phách**): Hệ thống xe vẫn chạy được nhưng một tính năng hoặc thông số đang bất thường (áp suất lốp thấp/cao, nhiệt độ lốp cao, lỗi cảm biến TPMS, lỗi ABS). Chatbot hướng dẫn kiểm tra và điều chỉnh.
* `LOW` (**Thông tin bảo dưỡng - Vàng/Trắng**): Cảnh báo mang tính thông báo bảo dưỡng (pin cảm biến yếu, đến hạn bảo dưỡng định kỳ, nhắc nhở dây an toàn).
* `UNKNOWN` (**Chưa xác định**): Ảnh mờ, lóa, góc chụp che khuất hoặc không đủ căn cứ đối chiếu. Chatbot hướng dẫn chụp lại tối đa 2 lần hoặc chuyển nhân viên hỗ trợ; tuyệt đối **không tự ý hạ về LOW**.
* `INFO` (**Chỉ báo hoạt động - Xanh lá/Xanh dương/Trắng**): Đèn báo tính năng đang hoạt động bình thường (Ready mode, Auto Hold, Đèn chiếu sáng).

### 4.2. Danh mục 7 nhóm cảnh báo TPMS trọng tâm (Tire Pressure Monitoring System)
Theo phân tích chuyên sâu tại mục 3 của tài liệu kế hoạch:

| STT | Triệu chứng (`symptom_key`) | Màu sắc & Hành vi đèn | Mức độ (`severity`) | Nguy cơ an toàn | Khuyến nghị an toàn cho người dùng |
|---|---|---|---|---|---|
| 1 | `rapid_leak` (Rò rỉ áp suất nhanh) | Vàng/Đỏ; Đèn TPMS sáng liên tục hoặc cảnh báo pop-up | `HIGH` | Thủng lốp do dị vật, mất lái khi chạy tốc độ cao | Giữ chắc vô lăng, giảm ga từ từ, không phanh gấp, tấp vào lề an toàn, bật đèn cảnh báo nguy hiểm (hazard), thay lốp phụ hoặc gọi cứu hộ. |
| 2 | `low_pressure` (Áp suất lốp thấp) | Đèn TPMS vàng; Sáng liên tục | `MEDIUM` | Tăng ma sát, tiêu hao nhiều điện năng, mòn mép lốp | Kiểm tra lốp bằng đồng hồ đo; bơm thêm hơi theo đúng áp suất tiêu chuẩn dán tại khung cửa lái (B-pillar). |
| 3 | `over_pressure` (Áp suất quá cao) | Đèn TPMS vàng / Cảnh báo màn hình | `MEDIUM` | Lốp căng cứng, giảm độ bám đường, nguy cơ nổ lốp khi chạy nhanh trời nắng | Để lốp nguội bớt, kiểm tra và xả bớt khí về mức tiêu chuẩn. Tuyệt đối không xả khi lốp đang quá nóng. |
| 4 | `high_temperature` (Nhiệt độ lốp cao) | Đèn TPMS vàng / Icon nhiệt độ lốp | `MEDIUM` (nâng lên `HIGH` nếu đường cao tốc) | Giãn nở khí đột ngột, phân rã cao su, nguy cơ nổ lốp | Dừng xe nơi bóng mát nghỉ ngơi, để lốp hạ nhiệt tự nhiên. Không tạt nước lạnh lên bề mặt lốp. |
| 5 | `sensor_fault` (Lỗi cảm biến lốp) | Đèn TPMS nhấp nháy 1 phút rồi sáng liên tục | `MEDIUM` | Không giám sát được áp suất lốp thời gian thực | Kiểm tra áp suất lốp thủ công bằng đồng hồ cơ; đặt lịch hẹn kiểm tra/thay cảm biến tại xưởng VinFast. |
| 6 | `sensor_battery_low` (Pin cảm biến thấp) | Cảnh báo chữ trên màn hình trung tâm | `LOW` | Cảm biến sắp ngừng hoạt động do hết pin | Lên lịch hẹn dịch vụ bảo dưỡng VinFast để thay thế pin hoặc cụm cảm biến lốp. |
| 7 | `tpms_system_error` (Lỗi hệ thống theo dõi) | Đèn TPMS nhấp nháy rồi sáng liên tục kèm thông báo hệ thống | `MEDIUM` | Mất toàn bộ chức năng cảnh báo áp suất 4 bánh | Khởi động lại xe để kiểm tra; nếu đèn không tắt, mang xe đến xưởng VinFast để quét mã lỗi ECU. |

### 4.3. Các cảnh báo táp-lô mở rộng trên EV VinFast
Bên cạnh TPMS, bộ dữ liệu bao gồm các cảnh báo hệ thống xe điện cốt lõi:
- **Lỗi hệ thống phanh (Brake System Warning - Đỏ):** `CRITICAL` — Mất áp lực phanh hoặc mức dầu phanh cạn; dừng xe ngay lập tức.
- **Biểu tượng rùa vàng (Turtle Mode / Limited Power - Vàng):** `HIGH` (kèm ngữ cảnh nguy hiểm nâng lên `CRITICAL`) — Giới hạn công suất do pin yếu nghiêm trọng hoặc quá nhiệt mô-tơ.
- **Lỗi hệ thống pin cao áp (HV Battery Fault - Đỏ/Vàng):** `HIGH` / `CRITICAL` — Nguy cơ ngắt nguồn động lực cao áp.
- **Lỗi trợ lực lái điện (EPS Warning - Vàng/Đỏ):** `HIGH` — Vô lăng nặng, khó chuyển hướng.
- **Cảnh báo túi khí (SRS Airbag Warning - Đỏ):** `MEDIUM` — Hệ thống túi khí có thể không kích hoạt khi va chạm.
- **Cảnh báo hệ thống ABS / Cân bằng điện tử ESC (Vàng):** `MEDIUM` — Hệ thống chống bó cứng phanh không khả dụng.
- **Cảnh báo mở cửa / nắp capo / cốp sau (Đỏ/Vàng):** `MEDIUM` — Cửa chưa đóng chặt khi xe di chuyển.

---

## 5. Đối Chiếu và Tương Thích Với Nhánh `develop`

Căn cứ nội dung mục **7. Đối chiếu develop** trong kế hoạch:

1. **Tuân thủ ADR-004 (`docs/decisions/ADR-004-web-first-auth-and-image-triage.md`):**  
   Kết quả nhận diện ảnh chỉ đóng vai trò **bằng chứng sơ bộ** hỗ trợ người dùng, không khẳng định xe hoàn toàn an toàn hoặc kết luận thay cho kỹ thuật viên xưởng.
2. **Khắc phục nhận diện theo tên file (`src/api/customer.py`):**  
   Triệt để loại bỏ logic cũ dựa vào regex tên tệp. Dataset cung cấp các thuộc tính thị giác thật (`visual_features`: màu sắc, hình dạng, vị trí cụm táp-lô, văn bản OCR đi kèm) để kiểm thử mô hình Vision đọc pixel.
3. **Tương thích cấu hình backend (`src/config.py`, `src/services/llm.py`):**  
   Cấu trúc dữ liệu đầu ra JSON tương thích trực tiếp với structured output schema của Google Gemini (`gemini-3.5-flash` / `gemini-3.8-flash`).
4. **Không mặc định mẫu xe `VF8`:**  
   Schema dữ liệu bắt buộc có trường `vehicle_model`. Khi người dùng gửi ảnh mà chưa rõ dòng xe, hệ thống chatbot bắt buộc phải hỏi xác nhận thay vì tự gán mặc định.
5. **Quy tắc an toàn Hard Safety (`docs/architecture/triage-and-hitl-rules.md`):**  
   Nếu người dùng mô tả có khói, cháy, mất phanh, tai nạn hoặc tình huống khẩn cấp, quy tắc an toàn lập tức trả về `CRITICAL` ngay trước khi chờ xử lý ảnh.
6. **Xử lý ảnh khó và giới hạn lượt hỏi:**  
   Khi ảnh mờ hoặc không nhận diện được (`UNKNOWN`), chatbot chỉ hỏi làm rõ tối đa 2 lượt trước khi tự động chuyển giao cho nhân viên tư vấn (`Staff Review`).

---

## 6. Cấu Trúc Các File Trong Dataset

```
dataset/img_warning_taplo/
├── README.md                      # Tài liệu đặc tả và hướng dẫn tổng quan (file hiện tại)
├── tpms_dataset.json              # Dữ liệu chuyên sâu 7 nhóm cảnh báo TPMS cho VF e34, VF 8, VF 5 Plus
├── dashboard_warnings_full.json   # Dữ liệu đầy đủ tất cả các đèn cảnh báo táp-lô xe điện VinFast
├── dataset_labels.csv             # Bản ghi phẳng dạng CSV phục vụ bảng tính, EDA và ML pipeline
├── verify_dataset.py              # Script Python kiểm thử tính toàn vẹn và hợp lệ của dataset
└── images/
    ├── image_catalog.json         # Danh mục ảnh tham chiếu, URL chính hãng, metadata kỹ thuật
    └── README.md                  # Hướng dẫn thu thập, gán nhãn ảnh và bảo mật PII
```

---

## 7. Hướng Dẫn Sử Dụng và Kiểm Thử Dataset

Để kiểm tra tính hợp lệ và toàn vẹn của dataset:
```bash
python dataset/img_warning_taplo/verify_dataset.py
```
Script sẽ kiểm tra:
- Cú pháp JSON chuẩn xác.
- Tính duy nhất của các mã định danh (`id`).
- Đầy đủ các trường bắt buộc và enum `severity` hợp lệ.
- Độ phủ đầy đủ 7 nhóm triệu chứng TPMS trên các dòng xe tuyển chọn.
