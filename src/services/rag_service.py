import os
import re
import chromadb
from typing import Any

CHROMA_DIR = r"d:\142.AI20K\P-142\data\chroma"
COLLECTION_NAME = "vinfast_knowledge_base"
DEFAULT_SIMILARITY_THRESHOLD = 0.70  # Ngưỡng cosine/L2 distance theo ADR-003 & Rule 2.4

KNOWN_MODELS = ["VF 3", "VF 5", "VF 6", "VF 7", "VF 8", "VF 9", "VF e34"]

class RAGService:
    def __init__(self, chroma_dir: str = CHROMA_DIR, collection_name: str = COLLECTION_NAME):
        self.chroma_dir = chroma_dir
        self.collection_name = collection_name
        self.client = chromadb.PersistentClient(path=self.chroma_dir)
        self.collection = self.client.get_collection(name=self.collection_name)

    def retrieve(self, query: str, top_k: int = 3, threshold: float = DEFAULT_SIMILARITY_THRESHOLD) -> dict[str, Any]:
        """
        Truy vấn tài liệu từ ChromaDB kết hợp Model-Aware Filtering và Rule 2.4.
        """
        query_lower = query.lower()

        # Nhận diện dòng xe cụ thể nếu người dùng hỏi đích danh model
        detected_model = None
        for m in KNOWN_MODELS:
            # Match "vf 7", "vf7", etc.
            pattern = r'\b' + re.escape(m.lower()).replace(r'\ ', r'\s*') + r'\b'
            if re.search(pattern, query_lower):
                detected_model = m
                break

        docs = []
        metas = []
        dists = []
        chunk_ids = []

        # 1. Nếu có model cụ thể -> Truy vấn ưu tiên catalog/tài liệu của model đó
        if detected_model:
            try:
                model_res = self.collection.query(
                    query_texts=[query],
                    n_results=top_k,
                    where={"applicable_models": detected_model}
                )
                if model_res and model_res.get("documents") and model_res["documents"][0]:
                    docs.extend(model_res["documents"][0])
                    metas.extend(model_res["metadatas"][0])
                    dists.extend(model_res["distances"][0])
                    chunk_ids.extend(model_res["ids"][0])
            except Exception:
                pass

        # 2. Truy vấn ngữ nghĩa chung (Toàn bộ database)
        general_res = self.collection.query(
            query_texts=[query],
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )

        gen_docs = general_res["documents"][0] if general_res.get("documents") else []
        gen_metas = general_res["metadatas"][0] if general_res.get("metadatas") else []
        gen_dists = general_res["distances"][0] if general_res.get("distances") else []
        gen_cids = general_res["ids"][0] if general_res.get("ids") else []

        # Ghép và lọc trùng lặp
        seen_cids = set(chunk_ids)
        for d, m, dist, cid in zip(gen_docs, gen_metas, gen_dists, gen_cids):
            if cid not in seen_cids:
                seen_cids.add(cid)
                docs.append(d)
                metas.append(m)
                dists.append(dist)
                chunk_ids.append(cid)

        best_distance = min(dists) if dists else 999.0

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
            if idx <= top_k:
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
