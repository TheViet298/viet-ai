# Kiểm tra và chuẩn bị dữ liệu ảnh — 2026-10-04

Nhánh làm việc: `feature/agent-long`. Ảnh gốc: `D:/142.AI20K/images`. Outputs nằm trong `D:/142.AI20K/P-142/data/vision`; ảnh gốc được giữ nguyên.

## 1. Kết luận về bộ VinFast

Bộ gốc đã chia thư mục, nhưng **chưa clean và chưa sẵn sàng cho đánh giá/huấn luyện dòng xe**. Đọc file được không đồng nghĩa nhãn và nội dung phù hợp.

- 350 file: 336 WebP, 14 PNG; tổng 77.348.491 bytes (khoảng 73,8 MiB).
- Cả 350 file decode được. Không tìm thấy trùng byte hoặc trùng pixel hoàn toàn.
- Có 24 ảnh có cạnh ngắn dưới 224px.
- 542 cặp dHash gần nhau ở ngưỡng Hamming ≤5; đây chỉ là các cặp cần đối chiếu, không phải 542 ảnh trùng. Khác màu/crop, bố cục quảng cáo và ảnh cùng ngoại hình có thể cùng hash gần nhau.
- Thư mục gốc: 161 exterior, 27 color, 40 banner, 66 interior, 56 other.
- Kiểm tra trực quan qua 6 contact sheets phát hiện 22 ảnh chỉ là bảng màu hình tròn và 4 ảnh logo/tên xe; có ảnh cận bộ phận, nội thất, overlay tên dòng, nhiều xe và các ảnh quảng cáo/render.
- Nhãn source folder chưa được xác nhận là taxonomy model đúng. Cần đối chiếu các nhóm gần ngoại hình: Herio Green/VF5, Minio Green/VF2 và hai thư mục VF8; không tự gộp/relabel.
- Không có nhãn bbox hư hại hay ground truth “xe nguyên vẹn”. Không thể dùng toàn bộ ảnh này như bộ damage negatives đã xác minh.

## 2. Bản chọn lọc đã tạo

`data/vision/vinfast-reference-clean/images/{source_model}/IMG-xxxx.jpg` có **209 ảnh tham chiếu được chọn**, đã xoay EXIF khi có, chuyển RGB/JPEG, resize tối đa 1600px và bỏ EXIF. Không cắt vùng xe để bịa thêm góc chụp hoặc tăng số ảnh.

141 ảnh không được đưa vào bản chọn lọc; tất cả vẫn còn ở nguồn. Đây là **tập tham chiếu có xe nhìn thấy rõ**, không phải dataset huấn luyện/held-out đã nghiệm thu. Việc chọn nội dung được thực hiện bằng contact sheets; chưa xác nhận ground truth từng mẫu xe với người cung cấp.

| Nhãn thư mục nguồn | Toàn bộ | Chọn làm reference |
|---|---:|---:|
| ecvan | 12 | 9 |
| herio-green | 21 | 15 |
| limo-green | 27 | 15 |
| minio-green | 33 | 21 |
| nerio-green | 3 | 1 |
| vf-mpv7 | 30 | 16 |
| vf-wild | 22 | 7 |
| vf2 | 28 | 19 |
| vf3 | 17 | 14 |
| vf5 | 16 | 9 |
| vf6 | 35 | 17 |
| vf7 | 24 | 15 |
| vf8 | 23 | 14 |
| vf8-the-all-new-2026 | 27 | 20 |
| vf9 | 32 | 17 |
| **Tổng** | **350** | **209** |

Không có e34. Nerio Green chỉ còn một ảnh reference; một số lớp chỉ có 7–9 ảnh. Không nên train toàn bộ 15 nhãn rồi dùng validation chia ngẫu nhiên để tuyên bố đạt. Phần lớn ảnh có vẻ là quảng cáo/render và nhiều biến thể cùng bố cục; model có thể học nền, chữ hoặc màu.

Artifacts:

- `data/vision/audit-20261004/manifest.jsonl`: từng file, dimensions, SHA256 byte/pixel, dHash, flags và nguồn folder.
- `data/vision/audit-20261004/summary.json`: thống kê và cặp gần trùng cần review.
- `data/vision/audit-20261004/contact_sheets/`: 6 trang xem toàn bộ 350 ảnh.
- `data/vision/vinfast-reference-clean/manifest.jsonl`: 209 ảnh được chọn, nguồn và nhãn chưa xác nhận.
- `data/vision/vinfast-reference-clean/review-all.jsonl`: quyết định chọn/loại của toàn bộ 350 ảnh.
- `data/vision/vinfast-reference-clean/preparation-report.json`: số ảnh từng lớp và giới hạn sử dụng.

Chưa chia train/val/test vì thiếu group xe/phiên/nguồn và taxonomy cuối cùng; chia các render khác màu hoặc các crop sang hai split sẽ tạo rò rỉ dữ liệu. 542 cặp gần hash vẫn được giữ để review; không tự xóa chỉ dựa dHash.

## 3. CarDD từ nguồn người dùng cung cấp

Nguồn: [mouen5/CarDD trên Hugging Face](https://huggingface.co/datasets/mouen5/CarDD).

Revision đã khóa: `8e7253288ceb08ef4914bd1dde47b623a2c47a06`.

Đọc metadata thực tế: **2.816 samples**, **6.211 detections**. Bản này xuất theo FiftyOne, có `samples.json`, `metadata.json`, ảnh và masks embedded. Không phải bộ đủ 4.000 ảnh với train/val/test gốc như mô tả chung trên dataset card. Viewer chỉ ghi split train; tags từng sample rỗng, không chứa split validation/test để phục hồi.

| YOLO class ID | Nhãn theo metadata thực | Số bbox trong nguồn |
|---:|---|---:|
| 0 | dent | 1.806 |
| 1 | scratch | 2.560 |
| 2 | crack | 651 |
| 3 | glass shatter | 475 |
| 4 | lamp broken | 494 |
| 5 | tire flat | 225 |

Không đảo thứ tự lamp broken/tire flat theo danh sách mô tả của bài báo; `class-map.json` lấy ID chính xác từ metadata nguồn.

Đầu ra: `data/vision/cardd-yolo-staging/images/mirror_train` và `labels/mirror_train`. Mỗi bbox FiftyOne `[left,top,width,height]` chuẩn hóa được chuyển sang YOLO `[center_x,center_y,width,height]`. Kiểm tra nhãn whitelist, finite coordinates, bbox nằm trong ảnh, decode file và kích thước khớp metadata trước ghi manifest.

**Đã hoàn tất tải và kiểm tra 2.816/2.816 ảnh; xuất 2.816 file nhãn YOLO với 6.211 bbox, không có lỗi decode/dimensions/bbox và không có trùng byte.** Tiến trình kết thúc với exit code 0; số thực được lưu trong `data/vision/cardd-yolo-staging/preparation-report.json`. Không tạo train/val alias hoặc data.yaml làm hai split dùng chung ảnh. Masks gốc giữ trong `cardd-source/samples.json`; bản YOLO này chỉ xuất detection bbox, không xuất segmentation.

Đã xem trực quan preview 12 ảnh đại diện 6 lớp với bbox để kiểm tra căn chỉnh mẫu; không coi đây là review thủ công toàn bộ 6.211 nhãn. Preview ở `data/vision/cardd-source/annotation-preview.jpg`.

Người dùng yêu cầu dùng bản này tạm để chuẩn bị kỹ thuật. Quyền sử dụng từ tác giả CarDD chưa được xác nhận; giữ license gốc trong `data/vision/cardd-source/CarDD_license.pdf`. Đây là bản local chuẩn bị/kiểm tra, không tự suy ra quyền huấn luyện, thương mại hoặc phân phối lại. [License gốc](https://cardd-ustc.github.io/docs/CarDD_license.pdf) yêu cầu có sự cho phép trước của tác giả.

## 4. Những việc còn cần trước khi train

1. Xác nhận danh sách nhãn dòng xe cuối cùng và cách xử lý các tên thương mại/phiên bản gần ngoại hình.
2. Thu thêm ảnh chụp thật, nhiều xe/phiên chụp; có ảnh hãng khác, crop sát, ảnh mờ và mẫu chưa hỗ trợ cho unknown tests.
3. Tạo nhóm gần trùng/nguồn; chia train/validation/test theo nhóm và giữ test thật độc lập.
4. Bổ sung ảnh VinFast hư hại được gán bbox và xe nguyên vẹn đã review để đo khả năng chuyển miền từ CarDD.
5. Hoàn tất quyền sử dụng CarDD và lấy validation/test gốc hoặc thiết kế split nội bộ mới với tên/báo cáo rõ ràng, không gọi là benchmark split gốc.

Với dữ liệu hiện có, có thể dùng 209 reference để thử baseline VLM hoặc chuẩn bị nhãn classifier; chưa đủ bằng chứng để cam kết chất lượng classifier trên ảnh người dùng thực tế.

## 5. Công cụ tái tạo

Dependencies: `requirements-vision-data.txt` (Pillow + requests); chưa cài framework huấn luyện.

```powershell
python scripts/audit_vehicle_images.py --source D:\142.AI20K\images --output data/vision/audit-20261004
python scripts/prepare_vehicle_references.py --audit data/vision/audit-20261004 --output data/vision/vinfast-reference-clean
python scripts/prepare_cardd_hf.py --source data/vision/cardd-source --output data/vision/cardd-yolo-staging --workers 12 --download
python -m unittest discover -s tests -p test_vision_preparation.py -v
```

Script download hỗ trợ tiếp tục các ảnh chưa có, khóa revision, không train hoặc upload dữ liệu đi. Dữ liệu/weights trong `data/` được Git ignore; chỉ commit scripts/tests/docs khi người dùng yêu cầu.

## 6. Baseline tạm v1 dùng trước, bổ sung sau

Theo yêu cầu dùng dữ liệu hiện có trước, đã tạo bản riêng tại `data/vision/baseline-20261004-v1` trên nhánh `feature/agent-long`. Các nguồn và bản staging ở trên được giữ nguyên.

| Tác vụ | Train | Validation nội bộ | Để riêng chờ bổ sung |
|---|---:|---:|---:|
| Nhận dạng mẫu xe VinFast | 167 | 41 | 1 |
| Phát hiện hư hại CarDD | 2.222 | 594 | 0 |

VinFast giữ 14 nhãn thư mục nguồn trong cả train/val. `nerio-green` chỉ có một ảnh nên được giữ ở `vehicles/needs_data`, chưa tham gia baseline classifier. Các tên thương mại và phiên bản chưa được gộp hoặc xác nhận thành taxonomy cuối cùng.

Ảnh trùng hash hoặc có dHash cách nhau không quá 5 bit được gom nhóm liên thông trước khi chia, kể cả khác nhãn xe; seed là 142. VinFast có 131 nhóm, CarDD có 2.811 nhóm. Nhóm VinFast lớn nhất có 72 ảnh: heuristic có thể gom quá rộng các góc render giống nhau, không phải bằng chứng chúng cùng xe/phiên chụp. Không có nhóm được chia sang cả train và validation; vẫn có thể còn ảnh liên quan mà heuristic không phát hiện.

`vehicles/train` và `vehicles/val` dùng cấu trúc thư mục cho classifier. `damage/data.yaml` cùng các danh sách ảnh trỏ đến ảnh/nhãn YOLO ở staging. Đây là split phát triển nội bộ của bản mirror, không phải benchmark CarDD gốc; chưa có test ảnh chụp thật độc lập, chưa huấn luyện hoặc đánh giá model.

Các manifest chứa đường dẫn tuyệt đối của máy hiện tại. Sau khi chuyển dữ liệu lên notebook/cloud, cập nhật đường dẫn trong manifest staging và chạy lại exporter với thư mục output mới:

```powershell
python scripts/prepare_vision_baseline.py --data-root data/vision --output data/vision/baseline-new
python -m unittest discover -s tests -p 'test_vision*.py' -v
```

Exporter không ghi đè split đã có. Bản `baseline-20261004` là bản nháp trước khi tách Nerio Green; dùng bản `baseline-20261004-v1` cho bước tiếp theo. Quyền sử dụng và giới hạn chất lượng của hai nguồn vẫn như các phần trên.
