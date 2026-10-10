# Báo cáo kết quả kiểm chứng Langfuse Cloud cho hệ thống P-142

## 1. Kết quả tổng hợp

Lượt kiểm chứng đạt **10/10 ca**, với 10 root trace, 7 generation và 136 observation đã được lưu trên Langfuse Cloud. Tổng usage là **7.971 token**; chi phí Langfuse ghi nhận là **0,00127475 USD**.

| Thông tin | Kết quả |
|---|---|
| Dự án | VinFast ServiceFlow AI (P-142) |
| Project Cloud | VFServ |
| Run ID | `p142-20261009T153831-bcfd92` |
| Thời gian kiểm chứng | 22:38:37–22:39:14 ngày 09/10/2026, Asia/Saigon |
| Phiên bản mã nguồn | `ecd5c97` |
| Ma trận đã chạy | 10 PASS, 0 FAIL, 0 BLOCKED |
| Root trace | 10: tám chat và hai upload |
| Generation | 7 |
| Observation | 136, đều đã kết thúc |
| Token đầu vào | 7.410 |
| Token đầu ra | 561, bao gồm reasoning |
| Tổng token | 7.971 |
| Chi phí ghi nhận | 0,00127475 USD |
| Generation thiếu usage hoặc chi phí | 0 |
| Kiểm thử project | 561 test và 6 subtest đạt |
| Liên kết dữ liệu local với Cloud | 38 sự kiện local nối với tám trace chat |

Số liệu trong báo cáo thuộc run cuối nêu trên. Hai lượt kiểm chứng đã tạo tổng cộng 20 root ứng dụng; các span smoke cũ nằm ngoài bảng kết quả này.

## 2. Kết quả từng ca kiểm chứng

| Ca | Tình huống và tiêu chí đã kiểm tra | HTTP | Kết quả | Generation | Input | Output | Tổng token | Chi phí USD | Trace |
|---|---|---:|---|---:|---:|---:|---:|---:|---|
| LF-01 | Chat thường; generation thực kết thúc, outcome parsed | 200 | PASS | 1 | 786 | 70 | 856 | 0.00015990 | [Mở trace](https://cloud.langfuse.com/project/cmuzofl6c02a5ad0ixpvdmca1/traces/4002c33f196c1c77c3fc45d552ebdb5b) |
| LF-02 | RAG có nguồn; retrieval thật, parsed và citations | 200 | PASS | 1 | 1158 | 108 | 1266 | 0.00023850 | [Mở trace](https://cloud.langfuse.com/project/cmuzofl6c02a5ad0ixpvdmca1/traces/35f3d0faa66490c403ca9e3e6f16edb4) |
| LF-03 | RAG thiếu nguồn; is_no_source=true, không citation | 200 | PASS | 0 | 0 | 0 | 0 | 0.00000000 | [Mở trace](https://cloud.langfuse.com/project/cmuzofl6c02a5ad0ixpvdmca1/traces/883e87603e14130eafc44241fc14ad8c) |
| LF-04 | Lượt 1: ghi session, xe VF8 và turn=1 | 200 | PASS | 1 | 786 | 49 | 835 | 0.00014730 | [Mở trace](https://cloud.langfuse.com/project/cmuzofl6c02a5ad0ixpvdmca1/traces/fa7f30f72a79810352a300f9ca4737d1) |
| LF-05 | Lượt 2: cùng session, giữ VF8 và turn=2 | 200 | PASS | 1 | 855 | 68 | 923 | 0.00016905 | [Mở trace](https://cloud.langfuse.com/project/cmuzofl6c02a5ad0ixpvdmca1/traces/97040255c820a6e52731fe3e60f7024a) |
| LF-06 | Exterior tổng hợp; Vision thực, ANALYZED, không analysis_error | 200 | PASS | 1 | 1477 | 41 | 1518 | 0.00016820 | [Mở trace](https://cloud.langfuse.com/project/cmuzofl6c02a5ad0ixpvdmca1/traces/31f2f34e029e6764cd600631d42ea1ba) |
| LF-07 | Dashboard tổng hợp; Vision thực, ANALYZED, cảnh báo low_pressure | 200 | PASS | 1 | 1568 | 170 | 1738 | 0.00024180 | [Mở trace](https://cloud.langfuse.com/project/cmuzofl6c02a5ad0ixpvdmca1/traces/a3cac3c457c927768bf83c37da858afe) |
| LF-08 | Khẩn cấp; is_safety_trigger=true, priority=CRITICAL | 200 | PASS | 0 | 0 | 0 | 0 | 0.00000000 | [Mở trace](https://cloud.langfuse.com/project/cmuzofl6c02a5ad0ixpvdmca1/traces/f5595e5f814bc0979e33bc299755cc83) |
| LF-09 | Timeout chủ động; fallback và llm.outcome=timeout | 200 | PASS | 0 | 0 | 0 | 0 | 0.00000000 | [Mở trace](https://cloud.langfuse.com/project/cmuzofl6c02a5ad0ixpvdmca1/traces/44a64a43c3e4a3d22511d456eb3baf87) |
| LF-10 | Chat thực; parsed, root kết thúc và đọc được sau shutdown | 200 | PASS | 1 | 780 | 55 | 835 | 0.00015000 | [Mở trace](https://cloud.langfuse.com/project/cmuzofl6c02a5ad0ixpvdmca1/traces/fee3491642ece0760ea3700bbf782163) |
| Tổng | 10 root, 136 observation | 10 × 200 | 10 PASS, 0 FAIL, 0 BLOCKED | 7 | 7410 | 561 | 7971 | 0.00127475 | |

LF-02 trả lời có trích dẫn từ bộ tài liệu SRC-002. LF-03 ghi nhận thiếu nguồn và không tạo citation. LF-04/LF-05 dùng cùng session, giữ thông tin xe VF8 qua hai lượt. LF-08 trả phản hồi an toàn với mức ưu tiên CRITICAL.

LF-06/LF-07 gọi Vision thực trên ảnh tổng hợp. Dashboard được phân tích với cảnh báo `low_pressure`; kết quả này xác nhận đường xử lý ảnh, chưa đánh giá độ chính xác trên ảnh xe thực.

LF-09 là lỗi timeout chủ động trong môi trường kiểm thử. Ứng dụng trả fallback và Cloud lưu `llm.outcome=timeout`; ca này không gọi provider thật và không có generation giả. LF-10 có generation thành công, root đã kết thúc và vẫn đọc được sau shutdown.

## 3. Kết quả token và chi phí

| Model trên Cloud | Generation | Input | Output | Tổng token | Chi phí USD |
|---|---:|---:|---:|---:|---:|
| gpt-4o-mini-2024-07-18 | 5 | 4365 | 350 | 4715 | 0.00086475 |
| gpt-6-luna | 2 | 3045 | 211 | 3256 | 0.00041000 |
| Tổng | 7 | 7410 | 561 | 7971 | 0.00127475 |

LF-07 ghi nhận 1.568 input token, 85 output token thường và 85 reasoning token. Tổng output là 170, tổng usage là 1.738 token, chi phí là 0,00024180 USD. Reasoning đã nằm trong tổng output và không được cộng lại vào tổng usage.

Các ca LF-03, LF-08 và LF-09 không có lời gọi mô hình, nên generation, token và chi phí mô hình bằng 0. Bảy generation còn lại đều có usage, model ID và chi phí trên Cloud.

Chi phí trên là số Langfuse tính theo model được ánh xạ trong project, chưa đối chiếu hóa đơn provider, khoản credit hoặc chi phí hạ tầng. UI có thể làm tròn số nhỏ thành `$0.00`; bảng kết quả giữ giá trị đầy đủ từ dữ liệu Cloud.

## 4. Hình ảnh bằng chứng

Bốn ảnh dưới đây thuộc run `p142-20261009T153831-bcfd92`, chụp toàn viewport 1453 × 994 px với sidebar thu gọn. Ảnh giữ nguyên nội dung hiển thị trên Cloud.

### 4.1. Danh sách 10 root trace

Bảng có Total 10, gồm tám request chat và hai request upload trong environment `p142-validation`.

![10 root trace của run cuối](https://github.com/user-attachments/assets/4b5ab78f-2654-4fe1-97ce-3e35b50001db)

### 4.2. Bảy generation với model, token và chi phí

Cloud hiển thị năm generation ChatOpenAI và hai generation Vision, kèm input/output/total token và chi phí từng lời gọi.

![7 generation, model, token và chi phí](https://github.com/user-attachments/assets/831c0cb0-de49-4f86-a8f1-34178cadd069)

### 4.3. Vision dashboard và token reasoning

Trace có `vision.dashboard` và `attachment.persist` dưới cùng root. Usage breakdown xác nhận 1.568 input token, 170 output token và tổng 1.738 token.

![Cây Vision và phân tách token](https://github.com/user-attachments/assets/65848d66-f707-40f8-8c8f-41d7b91833c1)

### 4.4. Phản hồi fallback của ca timeout

Ảnh thể hiện nhánh `llm.outcome` và phản hồi fallback của LF-09. Giá trị `outcome=timeout` được ghi trong JSON observation tương ứng.

![Timeout chủ động và fallback](https://github.com/user-attachments/assets/fca3251b-4103-4840-8f25-8d7cd81d1532)

## 5. Kết quả kiểm thử và bằng chứng đối chiếu

Bộ kiểm thử đạt **561 test và 6 subtest**, có bốn cảnh báo DeprecationWarning từ cấu hình Alembic thiếu `path_separator`. Các kiểm tra unit/integration xác nhận hành vi mã; ma trận 10 ca có bằng chứng ứng dụng và dữ liệu đọc lại trên Cloud.

| Bằng chứng | Nội dung |
|---|---|
| Manifest | Run ID, phiên bản mã nguồn, thời gian và số liệu tổng hợp |
| Kết quả từng ca | Phản hồi, trạng thái PASS/FAIL/BLOCKED, usage, chi phí và trace URL |
| Observation đã lọc | 136 observation của run cuối |
| Log kiểm thử | Kết quả 561 test và 6 subtest |

Phạm vi kết luận là 10 ca đã chạy. Ma trận 44 ca chưa được kiểm chứng đầy đủ; memory compaction, tải đồng thời, sự cố Google live, prompt rollback và chất lượng tư vấn/nhận diện trên dữ liệu có nhãn chưa có kết quả trong đợt này. Bằng chứng shutdown không bao gồm kill cưỡng bức hoặc mất điện.
