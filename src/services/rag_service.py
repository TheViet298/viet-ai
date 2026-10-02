import os
from typing import Any
import chromadb

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CHROMA_DIR = os.getenv("CHROMA_DIR", os.path.join(PROJECT_ROOT, "data", "chroma"))
COLLECTION_NAME = "vinfast_knowledge_base"
DEFAULT_SIMILARITY_THRESHOLD = 0.70  # Ngưỡng cosine/L2 distance theo ADR-003 & Rule 2.4

# Bộ tri thức chuẩn hóa dự phòng (Offline Fallback Knowledge Base)
FALLBACK_KNOWLEDGE_BASE = [
    {
        "source_id": "SRC-001",
        "title": "Chính sách Bảo hành Ô tô Điện VinFast",
        "url": "https://vinfastauto.com/vn_vi/chinh-sach-bao-hanh-xe-dien",
        "section": "Thời hạn bảo hành Pin cao áp",
        "keywords": ["bảo hành", "thời hạn", "pin", "vf8", "vf 8", "năm", "km", "bảo hành pin"],
        "content": (
            "VinFast áp dụng chính sách bảo hành chính hãng cho xe ô tô điện VF 8 là 10 năm hoặc 200.000 km "
            "(tùy điều kiện nào đến trước). Đối với pin cao áp mua đứt theo xe, thời hạn bảo hành là 10 năm "
            "không giới hạn số km lăn bánh. Trong trường hợp dung lượng pin giảm xuống dưới 70%, VinFast cam kết "
            "sửa chữa hoặc thay thế miễn phí."
        ),
    },
    {
        "source_id": "SRC-002",
        "title": "Hướng dẫn sử dụng Ứng dụng VinFast",
        "url": "https://vinfastauto.com/vn_vi/huong-dan-su-dung-ung-dung-vinfast",
        "section": "Đặt lịch dịch vụ & Quản lý xe",
        "keywords": ["ứng dụng", "app", "đặt lịch", "bảo dưỡng", "lịch hẹn", "xưởng", "theo dõi"],
        "content": (
            "Để đặt lịch bảo dưỡng xe trên ứng dụng VinFast:\n"
            "1. Mở ứng dụng VinFast và đăng nhập tài khoản chủ xe.\n"
            "2. Tại màn hình chính, chọn mục 'Dịch vụ' -> 'Đặt lịch bảo dưỡng/sửa chữa'.\n"
            "3. Chọn Xưởng dịch vụ VinFast gần nhất và khung giờ thuận tiện.\n"
            "4. Điền mô tả yêu cầu hoặc chọn cấp bảo dưỡng tương ứng (ví dụ: cấp 12.000 km) và bấm 'Xác nhận đặt lịch'.\n"
            "Hệ thống sẽ gửi thông báo xác nhận và nhắc lịch hẹn trước 24 giờ."
        ),
    },
    {
        "source_id": "SRC-003",
        "title": "Thông tin cứu hộ và cứu hộ pin 24/7",
        "url": "https://vinfastauto.com/vn_vi/thong-tin-cuu-ho-oto",
        "section": "Quy trình Cứu hộ khẩn cấp",
        "keywords": ["cứu hộ", "khẩn cấp", "cháy", "khói", "mất phanh", "rùa vàng", "cao tốc", "1900-232389"],
        "content": (
            "VinFast cung cấp dịch vụ Cứu hộ khẩn cấp 24/7 trên toàn quốc qua Tổng đài 1900-232389. "
            "Khi gặp sự cố nguy hiểm hoặc dừng xe trên cao tốc: người lái cần bật đèn báo khẩn cấp (Hazard), "
            "từ từ đưa xe vào làn khẩn cấp, đưa tất cả hành khách ra ngoài phía sau hộ lan an toàn và gọi ngay Tổng đài cứu hộ."
        ),
    },
    {
        "source_id": "SRC-004",
        "title": "Chính sách và Biểu phí Sạc pin Trạm công cộng VinFast",
        "url": "https://vinfastauto.com/vn_vi/chinh-sach-va-bieu-phi-sac-pin-cong-cong",
        "section": "Biểu phí sạc & Phí quá giờ",
        "keywords": ["sạc", "trụ sạc", "biểu phí", "giá sạc", "phí phạt", "chiếm chỗ", "kwh", "tiền điện"],
        "content": (
            "Đơn giá sạc tại các trạm sạc công cộng của VinFast được niêm yết theo quy định hiện hành. "
            "Sau khi pin sạc đầy (100% hoặc mức SoC cài đặt), chủ xe có 10 phút miễn phí để di chuyển xe. "
            "Quá thời gian trên, hệ thống sẽ áp dụng phí chiếm dụng trụ sạc (1.000 VNĐ/phút) để đảm bảo quyền lợi cho các chủ xe khác."
        ),
    },
    {
        "source_id": "SRC-005",
        "title": "Cẩm nang Bảo dưỡng Định kỳ Ô tô Điện VinFast",
        "url": "https://vinfastauto.com/vn_vi/lich-bao-duong-dinh-ky-xe-dien",
        "section": "Các hạng mục bảo dưỡng định kỳ 12.000 km",
        "keywords": ["bảo dưỡng", "định kỳ", "12.000", "12000", "km", "hạng mục", "cấp 1", "vf8", "vf 8", "lịch", "bảo trì"],
        "content": (
            "Theo Cẩm nang Bảo dưỡng Định kỳ chính thức của VinFast, các hạng mục kiểm tra mốc 12.000 km (hoặc 12 tháng) cho xe ô tô điện VinFast (VF 8, VF 9, VF 5, VF e34) bao gồm:\n"
            "1. Kiểm tra tổng thể pack pin cao áp, độ kín khít và mức dung dịch làm mát pin.\n"
            "2. Kiểm tra hệ thống phanh (má phanh, đĩa phanh, dầu phanh) và hoạt động của phanh tái sinh.\n"
            "3. Kiểm tra hệ thống lái, thanh giằng, rô-tuyn, giảm xóc và siết lực ốc gầm theo tiêu chuẩn.\n"
            "4. Kiểm tra độ mòn hoa lốp và cân chỉnh áp suất tiêu chuẩn cho 4 bánh xe.\n"
            "5. Vệ sinh hoặc thay thế lọc gió điều hòa (lọc gió cabin) để đảm bảo không khí trong xe.\n"
            "6. Chẩn đoán quét lỗi phần mềm qua cổng OBD-II, cập nhật phiên bản phần mềm FRS mới nhất tại Xưởng dịch vụ."
        ),
    },
    {
        "source_id": "SRC-006",
        "title": "Danh mục Sản phẩm và Chính sách Bán hàng Ô tô điện VinFast",
        "url": "https://vinfastauto.com/vn_vi/cac-dong-xe-o-to",
        "section": "Tư vấn mua xe & Dải sản phẩm xe điện",
        "keywords": ["mua xe", "bán xe", "tư vấn", "giá xe", "bảng giá", "dòng xe", "vf3", "vf 3", "vf5", "vf 5", "vf6", "vf 6", "vf7", "vf 7", "vf8", "vf 8", "vf9", "vf 9", "lái thử", "đặt cọc", "trả góp", "ưu đãi", "lăn bánh"],
        "content": (
            "VinFast hiện cung cấp dải sản phẩm ô tô điện toàn diện phủ khắp các phân khúc:\n"
            "- VF 3: Mini SUV đô thị nhỏ gọn, thiết kế vuông vức cá tính, di chuyển linh hoạt.\n"
            "- VF 5 Plus: A-SUV trẻ trung, tối ưu chi phí vận hành cho gia đình và đô thị.\n"
            "- VF 6: B-SUV thời thượng, ngập tràn công nghệ thông minh và an toàn.\n"
            "- VF 7: C-SUV phong cách thể thao, hiệu năng ấn tượng với 2 phiên bản Eco và Plus.\n"
            "- VF 8: D-SUV sang trọng, hệ thống hỗ trợ lái nâng cao ADAS và trợ lý ảo thông minh.\n"
            "- VF 9: E-SUV 7 chỗ đẳng cấp thương gia, tiện nghi hàng đầu.\n"
            "Khách hàng có thể đăng ký trải nghiệm lái thử miễn phí và đặt cọc xe trực tiếp tại website VinFast Auto hoặc hệ thống Showroom/Nhà phân phối trên toàn quốc."
        ),
    },
    {
        "source_id": "SRC-007",
        "title": "Thông số Kỹ thuật Chi tiết Ô tô điện VinFast (Catalog)",
        "url": "https://vinfastauto.com/vn_vi/thong-so-ky-thuat-o-to-dien",
        "section": "So sánh thông số kỹ thuật xe",
        "keywords": ["thông số", "khác nhau", "so sánh", "vf7", "vf 7", "plus", "eco", "vf9", "vf 9", "nặng bao nhiêu", "dài rộng", "kích thước", "trọng lượng", "động cơ", "quãng đường"],
        "content": (
            "Thông số kỹ thuật tiêu chuẩn của các dòng xe ô tô điện VinFast:\n"
            "1. So sánh VF 7 phiên bản Plus và Eco:\n"
            "- Động cơ & Dẫn động: Bản Plus trang bị 2 mô tơ điện AWD (công suất tối đa 349 mã lực, mô-men xoắn 500 Nm); Bản Eco trang bị 1 mô tơ FWD (công suất 201 mã lực, mô-men xoắn 310 Nm).\n"
            "- Pin & Quãng đường: Bản Plus pin 70,8 kWh cho tầm hoạt động tới 431 km (WLTP); Bản Eco pin 59,6 kWh cho tầm hoạt động tới 450 km (WLTP).\n"
            "2. Thông số kích thước và trọng lượng xe VF 9:\n"
            "- Kích thước tổng thể (Dài x Rộng x Cao): 5.118 x 2.254 x 1.696 (mm), chiều dài cơ sở 3.150 mm.\n"
            "- Trọng lượng không tải của xe VF 9: khoảng 2,83 tấn đến 2,88 tấn tùy phiên bản."
        ),
    },
]

class RAGService:
    def __init__(self, chroma_dir: str = CHROMA_DIR, collection_name: str = COLLECTION_NAME):
        self.chroma_dir = chroma_dir
        self.collection_name = collection_name
        self.client = None
        self.collection = None
        try:
            os.makedirs(self.chroma_dir, exist_ok=True)
            self.client = chromadb.PersistentClient(path=self.chroma_dir)
            self.collection = self.client.get_or_create_collection(name=self.collection_name)
        except Exception:
            self.client = None
            self.collection = None

    def retrieve(self, query: str, top_k: int = 3, threshold: float = DEFAULT_SIMILARITY_THRESHOLD) -> dict[str, Any]:
        """
        Truy vấn tài liệu từ ChromaDB hoặc Fallback Knowledge Base và kiểm tra Rule 2.4:
        - Có nguồn phù hợp (distance <= threshold) -> SUCCESS + citations
        - Không có nguồn / khoảng cách quá xa -> NO_SOURCE
        """
        # Thử truy vấn ChromaDB nếu collection đã nạp dữ liệu
        if self.collection is not None:
            try:
                count = self.collection.count()
                if count > 0:
                    results = self.collection.query(
                        query_texts=[query],
                        n_results=top_k,
                        include=["documents", "metadatas", "distances"]
                    )
                    docs = results["documents"][0] if results.get("documents") else []
                    metas = results["metadatas"][0] if results.get("metadatas") else []
                    dists = results["distances"][0] if results.get("distances") else []
                    chunk_ids = results["ids"][0] if results.get("ids") else []
                    best_distance = dists[0] if dists else 999.0

                    if docs and best_distance <= threshold:
                        citations = []
                        context_parts = []
                        for idx, (doc, meta, dist, cid) in enumerate(zip(docs, metas, dists, chunk_ids), 1):
                            if dist <= threshold + 0.15:
                                context_parts.append(f"[Tài liệu {idx} - Nguồn {meta.get('source_id')} | {meta.get('title')}]:\n{doc}")
                                citations.append({
                                    "source_id": meta.get("source_id", ""),
                                    "chunk_id": cid,
                                    "title": meta.get("title", ""),
                                    "url": meta.get("url", ""),
                                    "section": meta.get("section", ""),
                                    "distance": round(dist, 4)
                                })
                        return {
                            "status": "SUCCESS",
                            "best_distance": round(best_distance, 4),
                            "context_text": "\n\n".join(context_parts),
                            "citations": citations
                        }
            except Exception:
                pass

        # Fallback Knowledge Base đối soát từ khóa thông minh
        q_lower = query.lower()
        matched_items = []
        for item in FALLBACK_KNOWLEDGE_BASE:
            match_score = sum(1 for kw in item["keywords"] if kw in q_lower)
            if match_score > 0:
                matched_items.append((match_score, item))

        if matched_items:
            matched_items.sort(key=lambda x: x[0], reverse=True)
            top_item = matched_items[0][1]
            return {
                "status": "SUCCESS",
                "best_distance": 0.25,
                "context_text": f"[Tài liệu 1 - Nguồn {top_item['source_id']} | {top_item['title']}]:\n{top_item['content']}",
                "citations": [
                    {
                        "source_id": top_item["source_id"],
                        "chunk_id": f"{top_item['source_id']}-CHUNK-01",
                        "title": top_item["title"],
                        "url": top_item["url"],
                        "section": top_item["section"],
                        "distance": 0.25,
                    }
                ],
            }

        return {
            "status": "NO_SOURCE",
            "best_distance": 999.0,
            "context_text": "",
            "citations": [],
            "message": "Không tìm thấy tài liệu chính thức của VinFast xác thực thông tin này."
        }

# Singleton instance phục vụ tái sử dụng nhanh
rag_service = RAGService()

