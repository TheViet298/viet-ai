# Kế hoạch tích hợp GPS và review PR

1. Kiểm tra branch/upstream/worktree; sao lưu thay đổi và đối chiếu checksum.
2. Fetch feature/ai-khoi, feature/agent-long và main; báo commit mới và phạm vi diff.
3. Cập nhật Khoi trong bản sao riêng, giữ hooks/logging local ngoài phạm vi.
4. Merge thử Long; giải quyết từng đoạn conflict, giữ NearbyAction và hợp đồng API GPS.
5. Kiểm tra consent, nhập tay, GPS one-shot, hủy callback/request cũ, top 5 theo loại xe, map/chỉ đường và chia sẻ case riêng.
6. Chạy lint, TypeScript, build, frontend/backend regression và E2E; lưu báo cáo trung thực.
7. Tạo hai PR draft theo template repo bằng tiếng Việt; đính kèm kế hoạch, báo cáo và danh sách file.
8. Người review quyết định phạm vi toàn nhánh hay chỉ GPS; kiểm tra docs/guide, quyền dùng snapshot và các thay đổi ngoài GPS. Chỉ merge khi được chấp thuận và CI bắt buộc đạt.

## Tài liệu đọc theo thứ tự

- REVIEW.md: kết quả tích hợp, so sánh GPS, file và kiểm thử.
- vs-long-files.txt và vs-main-files.txt: phạm vi thực tế với từng đích.
- ../contextual-nearby-workflow-plan.md: thiết kế workflow chi tiết.
- ../update_gps_Oct_15.md: báo cáo triển khai GPS.
- ../gps-feature-report-latest-version.md: báo cáo tính năng.
- ../user-guide.md: hướng dẫn sử dụng.

## Quyết định cần con người

- Chấp nhận toàn bộ lịch sử ngoài GPS hay tách một PR giới hạn GPS?
- Chấp nhận normalization hỏi lại trước bước nearby và giữ fallback RAG của Khoi?
- Chấp nhận reset vị trí/kết quả khi đổi tài khoản; xử lý vị trí đã chia sẻ vào case vẫn theo consent/revoke hiện hành.
- Xác nhận quyền dùng và độ mới snapshot trước production; UNVERIFIED không phải trạng thái hoạt động thời gian thực.
- Review Technical Book nếu diff có docs/guide/**; kiểm tra CI và các giới hạn test.
