# Đánh giá baseline CarDD đã train

Nguồn kết quả: `D:/142.AI20K/damage-artifacts.zip`, do người dùng cung cấp. Đã kiểm tra CRC ZIP, hash checkpoint so với evaluation.json và JSON dự đoán theo VisionEvidence; không chạy lại model hoặc validation local.

Đầu ra được giữ ở `data/vision/trained/cardd-damage-baseline-v1`. ZIP gốc giữ nguyên. Checkpoint `weights/best.pt` có SHA256 `f0adf5fbcec8ddaf2cecd78ce5618c7244b484263e34d00002a6e9c765137efa`.

## Kết quả trong artifact

YOLO11n Detection, 40 epochs, batch 16, imgsz 640, seed 142, Tesla T4. Train 2.222 ảnh / validation nội bộ 594 ảnh. Thời gian train và đánh giá theo script khoảng 53,5 phút. Hash dữ liệu `125a26e0224b0023cab60c7f34ef4ff46603451b9f9bf836fa049c33941277b9` khớp preflight local đã kiểm tra ở bước chuẩn bị cloud.

| Metric | Giá trị |
|---|---:|
| Precision | 69,52% |
| Recall | 68,16% |
| mAP50 | 69,53% |
| mAP50–95 | 55,65% |

Các metric này là số báo cáo validation của artifact, không phải accuracy chung hoặc hiệu năng đã đo trên VinFast.

| Loại hư hại | AP50–95 |
|---|---:|
| Móp — dent | 30,10% |
| Xước — scratch | 33,75% |
| Nứt — crack | 10,53% |
| Vỡ kính — glass shatter | 90,00% |
| Vỡ đèn — lamp broken | 72,55% |
| Lốp xẹp — tire flat | 97,00% |

CSV đủ 40 epochs; mAP50–95 trong train validation cao nhất tại epoch 38 (~55,66%). Đánh giá standalone checkpoint best.pt đạt ~55,65%, chênh lệch rất nhỏ. Không suy ra best checkpoint metadata epoch vì chưa đọc nội dung pickle của weights.

## Nhận xét từ biểu đồ

Train và validation loss đều giảm; mAP còn cải thiện về cuối run. Không thấy dấu hiệu validation loss tăng kéo dài trong biểu đồ hiện có, nhưng điều này không chứng minh khả năng tổng quát hóa trên ảnh người dùng thật.

Các điểm yếu chủ yếu là bỏ sót nứt, móp, xước. Trong confusion matrix chuẩn hóa của validation, khoảng 68% crack, 41% dent, 33% scratch rơi vào hàng background tại cấu hình sinh ma trận. Đây không phải tỷ lệ bỏ sót ở mọi confidence threshold. Cột background cũng cho thấy false positive ở scratch/dent; tỷ lệ trong cột này không phải false-positive rate trên xe nguyên vẹn.

Ảnh mẫu 000014 có scratch 0,90, dent 0,66 và tire flat 0,63; bbox hiển thị đúng vùng dự đoán và JSON hợp schema. Đây là một ảnh validation, không phải bằng chứng test độc lập. Ngưỡng 0,25 chưa được hiệu chỉnh và không chuyển confidence thành xác suất hư hại thật.

## Bước tiếp theo

1. Giữ best.pt làm checkpoint baseline để thử inference và adapter; chưa coi là model nghiệm thu.
2. Đánh giá riêng trên ảnh VinFast chụp thật, có hư hại và xe nguyên vẹn được review; báo precision/recall theo lớp và false positive/image.
3. Review lỗi crack/dent/scratch, bổ sung nhãn và ảnh cận cảnh phù hợp. Thử thay đổi training có kiểm soát trên validation, giữ tập test mới độc lập.
4. Hiệu chỉnh confidence theo lớp sau khi có dữ liệu validation phù hợp. Chưa kết luận không hư hại khi không thấy bbox.
5. Hoàn thành baseline nhận dạng dòng xe bằng notebook vehicles, rồi bàn giao hai tác vụ riêng cho AI agent.

OCR không thuộc model này. Nhãn, split nội bộ và quyền sử dụng CarDD giữ các giới hạn đã ghi trong báo cáo dữ liệu.
