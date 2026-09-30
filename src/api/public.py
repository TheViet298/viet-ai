from fastapi import APIRouter

from src.models.schemas import ApiResponse, ArticleItem, PublicArticlesData

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
