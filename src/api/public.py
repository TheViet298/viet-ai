from fastapi import APIRouter

from src.models.schemas import (
    ApiResponse,
    ArticleItem,
    PublicArticlesData,
    PublicSupportInsightsData,
    SupportInsightItem,
)

router = APIRouter(prefix="/public", tags=["public"])

# Danh sách bài viết Knowledge Hub công khai từ nguồn chính thức đã kiểm chứng
VERIFIED_ARTICLES: list[ArticleItem] = [
    ArticleItem(
        id="ART-001",
        title="Quy chuẩn sạc DC & Dịch vụ pin xe điện VinFast",
        category="Sạc & Pin",
        summary="Hướng dẫn kiểm tra súng sạc, trình tự khóa ngàm tiếp xúc và cách khắc phục khi trụ sạc báo đèn đỏ giao tiếp (Mã CC01).",
        content=(
            "Quy chuẩn sạc nhanh DC VinFast yêu cầu cắm súng chắc chắn, nghe tiếng ngàm khóa trước khi khởi động phiên sạc qua ứng dụng. "
            "Khi trụ báo lỗi CC01 (lỗi giao tiếp BMS), rút súng sạc, chờ 30 giây và cắm lại dứt khoát."
        ),
        source_url="https://vinfastauto.com/vn_vi/dich-vu-pin-oto-dien",
        verified_at="2026-09-30",
        applicable_models=["VF3", "VF5", "VF6", "VF7", "VF8", "VF9"],
    ),
    ArticleItem(
        id="ART-002",
        title="Sổ tay vận hành & Ý nghĩa biểu tượng cảnh báo táp-lô",
        category="Vận hành",
        summary="Chế độ bảo vệ pin cao áp khi dung lượng còn dưới 10% hoặc nhiệt độ hệ thống pin tăng cao. Hướng dẫn di chuyển an toàn khi hiện rùa vàng.",
        content=(
            "Biểu tượng Con Rùa Vàng xuất hiện khi pin dưới 10% hoặc hệ thống quản lý nhiệt pin kích hoạt chế độ an toàn. "
            "Xe sẽ bị giới hạn công suất để kéo dài quãng đường di chuyển tới điểm sạc gần nhất."
        ),
        source_url="https://om.vinfastauto.com/vi_vn/detail?car=VF8&year=2026",
        verified_at="2026-09-30",
        applicable_models=["VF3", "VF5", "VF6", "VF7", "VF8", "VF9"],
    ),
    ArticleItem(
        id="ART-003",
        title="Quy trình và lịch bảo dưỡng định kỳ xe điện VinFast",
        category="Bảo dưỡng",
        summary="Các hạng mục bắt buộc mốc 12.000km: kiểm tra nước làm mát pin, đo độ mòn má phanh, cập nhật phần mềm ECU và cân bằng động lốp.",
        content=(
            "Bảo dưỡng định kỳ 12.000km hoặc 12 tháng tại xưởng dịch vụ chính hãng VinFast giúp duy trì tuổi thọ pin "
            "và đảm bảo xe vận hành ổn định trong suốt chu kỳ sử dụng."
        ),
        source_url="https://vinfastauto.com/vn_vi/dich-vu-bao-duong-oto",
        verified_at="2026-09-30",
        applicable_models=["VF3", "VF5", "VF6", "VF7", "VF8", "VF9"],
    ),
    ArticleItem(
        id="ART-004",
        title="Thông tin cứu hộ khẩn cấp 24/7 & Cứu hộ pin lưu động",
        category="Cứu hộ",
        summary="Quy chuẩn điều phối xe cẩu cứu hộ trên cao tốc toàn quốc và dịch vụ sạc pin lưu động 24/7 qua tổng đài 1900-232389.",
        content=(
            "Dịch vụ cứu hộ VinFast hoạt động 24/7 trên toàn quốc, hỗ trợ cẩu kéo miễn phí đối với xe gặp sự cố kỹ thuật trong thời gian bảo hành "
            "và cung cấp giải pháp sạc pin lưu động tại hiện trường."
        ),
        source_url="https://vinfastauto.com/vn_vi/thong-tin-cuu-ho-oto",
        verified_at="2026-09-30",
        applicable_models=["Tất cả dòng xe"],
    ),
    ArticleItem(
        id="ART-005",
        title="Chính sách bảo hành xe ô tô điện VinFast",
        category="Bảo hành",
        summary="Chế độ bảo hành 10 năm hoặc 200.000 km cho xe và pin cao áp theo tiêu chuẩn VinFast toàn cầu.",
        content=(
            "VinFast áp dụng chính sách bảo hành dẫn đầu thị trường: 10 năm hoặc 200.000 km đối với các dòng xe VF e34, VF 7, VF 8, VF 9 "
            "và cam kết thay thế/sửa chữa pack pin miễn phí khi dung lượng pin giảm dưới 70%."
        ),
        source_url="https://vinfastauto.com/vn_vi/chinh-sach-bao-hanh-oto",
        verified_at="2026-09-30",
        applicable_models=["VF3", "VF5", "VF6", "VF7", "VF8", "VF9"],
    ),
    ArticleItem(
        id="ART-006",
        title="Hướng dẫn sử dụng ứng dụng VinFast",
        category="Ứng dụng",
        summary="Cách theo dõi dung lượng pin (SoC), kiểm tra lịch sử sạc, tìm trạm sạc gần nhất và đặt hẹn bảo dưỡng trực tiếp trên ứng dụng.",
        content=(
            "Ứng dụng VinFast cho phép chủ xe quản lý toàn diện thông tin phương tiện: hiển thị trạng thái pin theo thời gian thực (SoC), "
            "tìm trạm sạc gần nhất, thanh toán phí sạc tự động và đặt hẹn dịch vụ tại xưởng."
        ),
        source_url="https://vinfastauto.com/vn_vi/huong-dan-su-dung-ung-dung-vinfast",
        verified_at="2026-09-30",
        applicable_models=["Tất cả dòng xe"],
    ),
    ArticleItem(
        id="ART-007",
        title="Chính sách Bảo vệ Dữ liệu và An toàn Thông tin Khách hàng (No-PII)",
        category="Chính sách",
        summary="Cam kết không thu thập dữ liệu cá nhân nhạy cảm thật, chỉ xử lý mã định danh giả lập.",
        content=(
            "Hệ thống Trợ lý Dịch vụ VinFast ServiceFlow AI cam kết tuân thủ nghiêm ngặt nguyên tắc No-PII. "
            "Khách hàng được khuyến nghị không gửi các thông tin định danh cá nhân thật (CCCD, Họ tên đầy đủ, SĐT cá nhân, "
            "Biển số xe thật, Số khung VIN hoặc ảnh khuôn mặt) trong các phiên hội thoại và ảnh đính kèm."
        ),
        source_url="https://vinfastauto.com/vn_vi/chinh-sach-bao-mat-thong-tin",
        verified_at="2026-09-30",
    ),
]

# Thư viện tình huống thường gặp đã biên soạn/ẩn danh theo api-contract.md 2.3 & ADR-005
# Không sử dụng raw ticket/chat của khách hàng
SUPPORT_INSIGHTS: list[SupportInsightItem] = [
    SupportInsightItem(
        id="INS-001",
        title="Trụ sạc báo lỗi kết nối CC01 tại trạm sạc công cộng",
        category="CHARGING",
        vehicle_models=["VF8", "VF9", "VF7", "VF6", "VF5", "e34"],
        symptom="Cắm súng sạc nhưng trụ nhấp nháy đèn đỏ, màn hình xe báo lỗi CC01 và không thể bắt đầu phiên sạc.",
        recommended_action="Rút súng sạc, đợi 30 giây, nâng chắc tay súng sạc vuông góc với cổng sạc và ấn chặt cho đến khi nghe tiếng ngàm khóa. Nếu tiếp tục lỗi, chuyển sang trụ sạc khác gần nhất.",
        hotline_support="1900-232389 (Phím 1)",
    ),
    SupportInsightItem(
        id="INS-002",
        title="Biểu tượng rùa vàng hiển thị và xe giảm công suất trên đường",
        category="OPERATING",
        vehicle_models=["VF3", "VF5", "VF6", "VF7", "VF8", "VF9", "e34"],
        symptom="Đèn cảnh báo rùa vàng bật sáng trên màn hình ODO, xe bị giới hạn tốc độ và mất công suất tăng tốc.",
        recommended_action="Bật ngay đèn Hazard, từ từ tấp vào làn dừng khẩn cấp an toàn. Tắt máy khóa xe khoảng 5 phút để hệ thống BMS tái thiết lập, sau đó khởi động lại.",
        hotline_support="1900-232389 (Phím 1 - Cứu hộ khẩn cấp 24/7)",
    ),
    SupportInsightItem(
        id="INS-003",
        title="Bộ sạc di động tại nhà báo đèn đỏ lỗi tiếp địa (Ground Error)",
        category="BATTERY",
        vehicle_models=["VF3", "VF5", "VF6", "VF7", "VF8", "VF9", "e34"],
        symptom="Bộ sạc 2.2kW / 3.5kW cắm vào ổ điện gia đình nhưng đèn Fault đỏ nháy liên tục, không nạp điện.",
        recommended_action="Kiểm tra hệ thống tiếp địa của ổ cắm dân dụng. Tránh cắm chung với ổ chia chịu tải kém và đảm bảo dây dẫn có tiết diện từ 2.5mm² trở lên.",
        hotline_support="1900-232389",
    ),
    SupportInsightItem(
        id="INS-004",
        title="Ứng dụng VinFast không đồng bộ phần trăm pin (SoC) theo thời gian thực",
        category="SOFTWARE",
        vehicle_models=["VF3", "VF5", "VF6", "VF7", "VF8", "VF9", "e34"],
        symptom="Ứng dụng điện thoại hiển thị số liệu sạc hoặc vị trí xe cũ so với thực tế.",
        recommended_action="Kiểm tra tín hiệu sóng 4G/eSIM trên màn hình xe. Kéo màn hình ứng dụng từ trên xuống (Pull-to-refresh) hoặc đăng xuất và đăng nhập lại tài khoản trên ứng dụng.",
        hotline_support="1900-232389",
    ),
    SupportInsightItem(
        id="INS-005",
        title="Tối ưu hóa thời gian sạc pin trong điều kiện thời tiết nắng nóng",
        category="BATTERY",
        vehicle_models=["VF6", "VF7", "VF8", "VF9"],
        symptom="Tốc độ sạc nhanh DC giảm xuống khi nhiệt độ ngoài trời cao trên 38°C.",
        recommended_action="Hệ thống quản lý nhiệt pin tự động giảm dòng để bảo vệ tuổi thọ cell pin. Khuyến nghị đỗ xe tại bóng râm hoặc bật tính năng làm mát trước khoang pin trước khi sạc DC.",
        hotline_support="1900-232389",
    ),
]


@router.get("/articles", response_model=ApiResponse[PublicArticlesData])
def get_public_articles():
    """
    Lấy danh sách bài viết Knowledge Hub công khai (Landing/FAQ/Policy) theo api-contract.md Mục 1.1.
    Cho phép Guest truy cập không cần đăng nhập.
    """
    return ApiResponse(
        success=True,
        data=PublicArticlesData(
            articles=VERIFIED_ARTICLES,
            total=len(VERIFIED_ARTICLES),
        ),
        error=None,
    )


@router.get("/support-insights", response_model=ApiResponse[PublicSupportInsightsData])
def get_public_support_insights():
    """
    Thư viện tình huống thường gặp đã biên soạn/ẩn danh theo api-contract.md 2.3 & ADR-005.
    Không trả raw case của khách hàng khác. Cho phép Guest truy cập công khai.
    """
    return ApiResponse(
        success=True,
        data=PublicSupportInsightsData(
            items=SUPPORT_INSIGHTS,
            total=len(SUPPORT_INSIGHTS),
        ),
        error=None,
    )
