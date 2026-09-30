import logging
import chromadb
from typing import Any

from chromadb.errors import NotFoundError
from src.config import get_settings

CHROMA_DIR = get_settings().chroma_persist_dir
logger = logging.getLogger(__name__)
COLLECTION_NAME = "vinfast_knowledge_base"
DEFAULT_SIMILARITY_THRESHOLD = 0.70  # Ngưỡng cosine/L2 distance theo ADR-003 & Rule 2.4

class RAGService:
    def __init__(self, chroma_dir: str = CHROMA_DIR, collection_name: str = COLLECTION_NAME):
        self.chroma_dir = chroma_dir
        self.collection_name = collection_name
        # Initialize on retrieval so missing knowledge data does not block startup.
        self.client = None
        self.collection = None

    def retrieve(self, query: str, top_k: int = 3, threshold: float = DEFAULT_SIMILARITY_THRESHOLD) -> dict[str, Any]:
        """
        Truy vấn tài liệu từ ChromaDB và kiểm tra Rule 2.4:
        - Có nguồn phù hợp (distance <= threshold) -> SUCCESS + citations
        - Không có nguồn / khoảng cách quá xa -> NO_SOURCE
        """
        if self.collection is None:
            if self.client is None:
                self.client = chromadb.PersistentClient(path=self.chroma_dir)
            try:
                self.collection = self.client.get_collection(name=self.collection_name)
            except NotFoundError:
                logger.info("Knowledge collection %s has not been loaded", self.collection_name)
                return {
                    "status": "NO_SOURCE", "best_distance": 999.0,
                    "context_text": "", "citations": [],
                    "message": "Chưa có dữ liệu nguồn chính thức được nạp vào knowledge base.",
                }

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

        # Kiểm tra ngưỡng Rule 2.4
        if not docs or best_distance > threshold:
            return {
                "status": "NO_SOURCE",
                "best_distance": round(best_distance, 4),
                "context_text": "",
                "citations": [],
                "message": "Không tìm thấy tài liệu chính thức của VinFast xác thực thông tin này."
            }

        citations = []
        context_parts = []

        for idx, (doc, meta, dist, cid) in enumerate(zip(docs, metas, dists, chunk_ids), 1):
            if dist <= threshold + 0.15:  # Lấy các chunk có độ liên quan tốt
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

# Singleton instance phục vụ tái sử dụng nhanh
rag_service = RAGService()
