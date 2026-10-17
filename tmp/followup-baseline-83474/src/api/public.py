from fastapi import APIRouter

from src.models.schemas import (
    ApiResponse,
    ArticleItem,
    PublicArticlesData,
    PublicSupportInsightsData,
    SupportInsightItem,
)

router = APIRouter(prefix="/public", tags=["public"])

# Curated navigation, not universal technical instructions. Model/year/component
# applicability must be checked in the linked document before giving advice.
VERIFIED_ARTICLES: list[ArticleItem] = [
    ArticleItem(id='ART-001', title='Thông tin pin và dịch vụ sạc', category='Sạc & Pin',
                summary='Tra cứu thông tin dịch vụ sạc từ VinFast.',
                content='Xem nguồn chính thức để kiểm tra dịch vụ và điều kiện áp dụng. Mã lỗi trên trụ sạc cần được đối chiếu theo thiết bị và hướng dẫn tương ứng.',
                source_url='https://vinfastauto.com/vn_vi/dich-vu-pin-oto-dien', verified_at='2026-09-30'),
    ArticleItem(id='ART-002', title='Tra cứu sổ tay vận hành', category='Vận hành',
                summary='Chọn đúng dòng xe và đời xe trong sổ tay điện tử.',
                content='Tra cứu hướng dẫn và biểu tượng cảnh báo trong sổ tay đúng dòng xe, đời xe. Không áp dụng hướng dẫn của VF8 cho mọi dòng xe.',
                source_url='https://om.vinfastauto.com/', verified_at='2026-10-16'),
    ArticleItem(id='ART-003', title='Lịch và hạng mục bảo dưỡng', category='Bảo dưỡng',
                summary='Tra cứu lịch bảo dưỡng theo dòng xe.',
                content='Trang dịch vụ có mục lựa chọn dòng xe và lịch bảo dưỡng. Kiểm tra đúng dòng xe và điều kiện sử dụng trước khi áp dụng mốc thời gian hoặc quãng đường.',
                source_url='https://vinfastauto.com/vn_vi/dich-vu-bao-duong-oto', verified_at='2026-10-16'),
    ArticleItem(id='ART-004', title='Thông tin dịch vụ cứu hộ', category='Cứu hộ',
                summary='Tra cứu phạm vi và điều kiện dịch vụ cứu hộ.',
                content='Xem trang cứu hộ chính thức để kiểm tra điều kiện dịch vụ và kênh liên hệ. Phạm vi hỗ trợ và chi phí cần được xác nhận theo tình huống.',
                source_url='https://vinfastauto.com/vn_vi/thong-tin-cuu-ho-oto', verified_at='2026-10-16'),
    ArticleItem(id='ART-005', title='Chính sách bảo hành ô tô', category='Bảo hành',
                summary='Tra cứu bảo hành theo xe, linh kiện và điều kiện áp dụng.',
                content='Thời hạn và điều kiện bảo hành cần đối chiếu theo dòng xe, đời xe và hạng mục: xe, pin cao áp hoặc ắc quy. Không dùng một thời hạn chung cho tất cả dòng xe và linh kiện.',
                source_url='https://vinfastauto.com/vn_vi/chinh-sach-bao-hanh-oto', verified_at='2026-10-16'),
    ArticleItem(id='ART-006', title='Hướng dẫn ứng dụng VinFast', category='Ứng dụng',
                summary='Mở hướng dẫn chính thức cho ứng dụng VinFast.',
                content='Tra cứu hướng dẫn theo chức năng cần sử dụng và phiên bản ứng dụng. Tính năng có thể phụ thuộc cấu hình xe và tài khoản.',
                source_url='https://vinfastauto.com/vn_vi/huong-dan-su-dung-ung-dung-vinfast', verified_at='2026-09-30'),
]

# Unreviewed synthetic troubleshooting recipes have no claim-level evidence.
# Keep the public response shape; publish entries only after evidence review.
SUPPORT_INSIGHTS: list[SupportInsightItem] = []


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
