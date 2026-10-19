# Bổ sung dữ liệu từ trang VF3 và VF7 — 19/10/2026

## Nguồn và cách lấy

Hai URL người dùng cung cấp:

- https://vinfastauto.com/vn_vi/dat-coc-xe-dien-vf7
- https://vinfastauto.com/vn_vi/dat-coc-xe-dien-vf3

Đã đọc phần nội dung sản phẩm qua công cụ web. Playwright GET trực tiếp HTML trả403, nên không sử dụng body403 làm dữ liệu. Hai brochure được liên kết ngay trong hai trang tải được HTTP200 bằng Playwright; đã render và đọc trực quan VF7 trang12–13 và VF3 trang9.

Artifact gốc cục bộ: `data/acquired/vf3-vf7-product-2026-10-19/`. SHA256, URL, trạng thái và phương pháp được lưu trong `fixtures/knowledge/source_reviews/vf3-vf7-product-2026-10-19.json`. Không tự cập nhật ngày phê duyệt URL cũ từ ngày tải tài liệu. Các nguồn không xác định đời xe riêng.

## Đã thu thập

| Phạm vi | Dữ liệu |
|---|---|
| VF3 ngoại thất | 7 phối màu ở mức dòng xe; phân biệt mái trắng của Summer Yellow với phối mái đen trên dòng khác |
| VF3 thông số chung | Kích thước, chiều dài cơ sở, khoảng sáng gầm, bán kính/đường kính quay đầu, mô men xoắn, công suất, dung lượng khả dụng, loại pin, NEDC, DC tối đa, ghế, màn hình, túi khí, HSA/ABS/cảm biến sau |
| VF3 Plus | Brochure ghi riêng gương chỉnh/gập điện, camera lùi, ốp la-zăng là các tính năng nâng cao; không suy diễn danh sách này thành thao tác sửa xe hoặc bảo đảm kích hoạt hiện tại |
| VF7 phiên bản | Eco/FWD, Plus/FWD, Plus AWD; pin, NEDC, công suất, mô men xoắn, AC/DC tối đa, thời gian sạc, la-zăng, màn hình và túi khí |
| VF7 gói màu | Eco/Plus tiêu chuẩn và nâng cao, kèm ánh xạ nội thất trong brochure; không tự chuyển bảng Plus sang AWD |
| Giá | Đối chiếu lại các giá công bố theo Eco/Plus; giá Plus AWD vẫn null |

Bảng màu VF3 gồm Infinity Blanc, Zenith Grey, Solar Ruby, Summer Yellow Body–Infinity Blanc Roof, Sky Blue–Infinity Blanc Roof, Rose Pink–Infinity Blanc Roof và Urban Mint.

Brochure VF7 trang12 chia Eco/Plus tiêu chuẩn: Jet Black, Solar Ruby, Infinity Blanc, Zenith Grey. Eco/Plus nâng cao: Urban Mint. Các cặp nội thất có điều kiện được lưu riêng trong JSON, không biến thành mọi nội thất đều ghép được với mọi ngoại thất.

## Đã đưa vào đường trả lời hiện có

- Màu VF3: câu trả lời có nguồn và giữ caveat cấp dòng xe, chưa có ánh xạ Eco/Plus/đời xe/tồn kho.
- Màu VF7: bổ sung thông tin gói tiêu chuẩn/nâng cao từ brochure; giữ trạng thái partial khi chưa có gói cụ thể hoặc chưa xác nhận phạm vi riêng.
- Thời gian sạc VF7: Eco 25, Plus 28, Plus AWD 37 phút, đều là thời gian nạp nhanh nhất công bố trong bảng brochure từ 10%–70%. Ghi đúng cột từng phiên bản trong canonical `vehicle_facts.json`; không dùng28 phút của Plus cho AWD. Điều kiện sử dụng thực tế có thể làm thời gian khác.

Các thông số bổ sung còn lại đã được lưu cấu trúc để phục vụ nhập liệu/đối chiếu; đợt này không xây hoặc chuyển active vector index và không thêm bộ intent mới cho từng thông số. Không coi việc thu thập là bằng chứng rằng mọi câu hỏi về các trường đó đã được kiểm thử qua UI.

Đã loại giá trị 25 phút cũ khỏi trường thẻ Plus/AWD; mỗi thẻ chỉ còn một trường thời gian sạc, giữ thứ tự hiển thị cũ.

## Các điểm không gộp nhầm

- Brochure VF7 cũ ghi quãng đường Plus/AWD “cập nhật sau”; giữ số NEDC trên trang hiện tại, không ghi đè bằng placeholder cũ.
- 7,2 kW là công suất AC tối đa trên trang;7,4 kW trong brochure là phụ kiện sạc tại nhà, không thay thế nhau.
- 9 m là đường kính quay đầu VF3;4,5 m là bán kính, không phải hai dữ liệu mâu thuẫn.
- 18,64 kWh của VF3 được xác nhận ở mức dòng xe và có đơn vị từ brochure. Hai trang/brochure chưa có bảng dung lượng tách riêng Eco/Plus; canonical capacity của từng trim vẫn null.
- Chưa có tồn kho đại lý, ngày giao xe, giá riêng VF7 Plus AWD, ánh xạ màu Plus AWD hoặc đời xe cụ thể. Hai trang sản phẩm không thay thế sổ bảo dưỡng theo đời xe.

## Kiểm thử

- 8 ca dữ liệu mới: đã quan sát RED trước bổ sung, GREEN sau bổ sung. Ba kiểm tra thời gian được làm chặt thêm để bắt trường cũ bị lặp; RED trước loại bỏ và GREEN sau loại bỏ.
- 83 test tập trung pass, gồm dữ liệu mới,14 câu cũ, bản tiếng Anh và giới hạn phạm vi. Log: `.test-runs/vf37-targeted-final.log`.
- Backend đầy đủ sau sửa cuối: **2189 passed,49 skipped,9 warnings,6 subtests passed**, exit0 trong249,24 giây. Log: `.test-runs/vf37-full-final.log`.
- 5 kiểm tra API trực tiếp pass, không bật provider: ba thời gian VF7 bằng tiếng Việt, AWD37 bằng tiếng Anh và màu VF3 Plus bằng tiếng Anh. Kết quả thực tế: `eval/results/vf3-vf7-product-2026-10-19/api-smoke.json`.
- Holdout giữ nguyên:40/40 pass (30 answerable,10 boundary).
- Bộ14 câu qua API với provider: lượt đầu VI14/14, EN13/14; câu hỏi quãng đường VF8 gặp lỗi trình bày/dịch, ngoài phần dữ liệu thay đổi. Chạy lại nguyên14 câu EN đạt14/14. Giữ cả log lỗi và lần lặp; không coi đó là bằng chứng provider luôn ổn định. Logs: `.test-runs/vf37-contract.log`, `.test-runs/vf37-en-repeat.log`.
- Rà độc lập bảng PDF và dữ liệu: không phát hiện lỗi high/medium. Frontend UI/E2E không chạy lại trong đợt bổ sung dữ liệu này.

Nhánh cục bộ: `codex/vf3-vf7-data`. Không thay đổi cấu hình provider hoặc database thật; gate PostgreSQL vẫn BLOCKED. Không triển khai môi trường chạy thật trong lượt thu thập này.
