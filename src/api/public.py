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
        title="Hướng dẫn sử dụng Ứng dụng VinFast",
        category="Ứng dụng & Tiện ích",
        summary="Cách theo dõi dung lượng pin, kiểm tra lịch sử sạc và đặt lịch bảo dưỡng trực tiếp trên ứng dụng.",
        content=(
            "Ứng dụng VinFast cho phép chủ xe quản lý toàn diện thông tin phương tiện. "
            "Các tính năng nổi bật gồm: hiển thị trạng thái sạc theo thời gian thực (SoC), "
            "tìm kiếm và đặt chỗ trụ sạc công cộng gần nhất, thanh toán phí sạc tự động và đặt hẹn dịch vụ tại xưởng."
        ),
        source_url="https://vinfastauto.com/vn_vi/huong-dan-su-dung-ung-dung-vinfast",
        verified_at="2026-09-24",
    ),
    ArticleItem(
        id="ART-002",
        title="Chính sách và Biểu phí Sạc pin Trạm công cộng VinFast",
        category="Sạc & Trạm sạc",
        summary="Thông tin đơn giá sạc công cộng, hình thức thanh toán và quy định phí phạt chiếm chỗ sau khi sạc đầy.",
        content=(
            "VinFast áp dụng biểu phí sạc điện chuẩn hóa tại tất cả các trạm sạc công cộng trên toàn quốc. "
            "Khách hàng vui lòng rút súng sạc và di chuyển xe trong vòng 10 phút sau khi sạc đầy hoặc đạt mức pin cài đặt "
            "để nhường chỗ cho các xe tiếp theo, tránh phát sinh phí chiếm dụng trụ sạc theo quy định."
        ),
        source_url="https://vinfastauto.com/vn_vi/chinh-sach-va-bieu-phi-sac-pin-cong-cong",
        verified_at="2026-09-24",
    ),
    ArticleItem(
        id="ART-003",
        title="Quy định Bảo hành và Cứu hộ Khẩn cấp Pin xe điện VinFast",
        category="Bảo hành & Cứu hộ",
        summary="Hướng dẫn an toàn khi gặp sự cố dừng xe, đèn cảnh báo rùa vàng và cách liên hệ cứu hộ 24/7.",
        content=(
            "Khi xe xuất hiện đèn cảnh báo rùa vàng kèm hiện tượng giảm công suất trên đường, người lái cần: "
            "bật đèn cảnh báo nguy hiểm (Hazard), từ từ tấp xe vào làn dừng khẩn cấp an toàn, tắt máy và liên hệ "
            "ngay Hotline Cứu hộ 24/7 của VinFast qua số 1900-232389 để được hỗ trợ chuyên nghiệp."
        ),
        source_url="https://vinfastauto.com/vn_vi/chinh-sach-bao-hanh-va-cuu-ho-xe-dien",
        verified_at="2026-09-24",
    ),
    ArticleItem(
        id="ART-004",
        title="Chính sách Bảo vệ Dữ liệu và An toàn Thông tin Khách hàng (No-PII)",
        category="Chính sách & An toàn",
        summary="Cam kết không thu thập dữ liệu cá nhân nhạy cảm thật, chỉ xử lý mã định danh giả lập.",
        content=(
            "Hệ thống Trợ lý Dịch vụ VinFast ServiceFlow AI cam kết tuân thủ nghiêm ngặt nguyên tắc No-PII. "
            "Khách hàng được khuyến nghị không gửi các thông tin định danh cá nhân thật (CCCD, Họ tên đầy đủ, SĐT cá nhân, "
            "Biển số xe thật, Số khung VIN hoặc ảnh khuôn mặt) trong các phiên hội thoại và ảnh đính kèm."
        ),
        source_url="https://vinfastauto.com/vn_vi/chinh-sach-bao-mat-thong-tin",
        verified_at="2026-09-24",
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
