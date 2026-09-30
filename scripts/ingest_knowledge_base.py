import os
import json
import sys
import chromadb
from chromadb.utils import embedding_functions

sys.stdout.reconfigure(encoding='utf-8')

CHUNKS_PATH = r"d:\142.AI20K\P-142\data\processed\chunks.jsonl"
CHROMA_DIR = r"d:\142.AI20K\P-142\data\chroma"
COLLECTION_NAME = "vinfast_knowledge_base"

os.makedirs(CHROMA_DIR, exist_ok=True)

def ingest_chunks():
    print(f"=== KHỞI TẠO CHROMADB PERSISTENT TẠI: {CHROMA_DIR} ===")
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    
    # Get or create collection
    # Uses default chroma embedding function (all-MiniLM-L6-v2 via onnxruntime)
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"description": "VinFast Official Knowledge Base for RAG MVP 1"}
    )
    
    print(f"Đọc dữ liệu chunks từ {CHUNKS_PATH}...")
    chunks = []
    with open(CHUNKS_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                chunks.append(json.loads(line))
                
    print(f"Tổng số chunks cần nạp: {len(chunks)}")
    
    # Ingest in batches of 200
    batch_size = 200
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        ids = [c["chunk_id"] for c in batch]
        documents = [c["content"] for c in batch]
        
        # Metadata in Chroma must have primitive types (str, int, float, bool)
        metadatas = []
        for c in batch:
            models_str = ",".join(c.get("applicable_models", [])) if isinstance(c.get("applicable_models"), list) else str(c.get("applicable_models"))
            metadatas.append({
                "source_id": c.get("source_id", ""),
                "title": c.get("title", ""),
                "url": c.get("url", ""),
                "source_type": c.get("source_type", ""),
                "verified_at": c.get("verified_at", ""),
                "applicable_models": models_str,
                "section": c.get("section", "")
            })
            
        collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )
        print(f"  -> Đã nạp batch {i // batch_size + 1}/{(len(chunks) + batch_size - 1) // batch_size} ({min(i + batch_size, len(chunks))}/{len(chunks)} chunks)")

    print(f"Hoàn thành nạp {collection.count()} chunks vào collection '{COLLECTION_NAME}'!")
    return client, collection

def query_knowledge_base(query_text: str, n_results: int = 3, threshold_distance: float = 1.2):
    """
    Query knowledge base and enforce Section 2.4 rules:
    - If relevant source exists -> Return citation with source_id, url, chunk_id, section.
    - If distance exceeds threshold or no source -> Flag as NO_SOURCE and recommend Staff Review.
    """
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    collection = client.get_collection(name=COLLECTION_NAME)
    
    print(f"\n[QUERY]: '{query_text}'")
    results = collection.query(
        query_texts=[query_text],
        n_results=n_results,
        include=["documents", "metadatas", "distances"]
    )
    
    docs = results["documents"][0]
    metas = results["metadatas"][0]
    dists = results["distances"][0]
    
    best_dist = dists[0] if dists else 999.0
    print(f"  Khoảng cách vector gần nhất (Cosine/L2 distance): {best_dist:.4f}")
    
    if best_dist > threshold_distance:
        print("  => KẾT QUẢ: [NO_SOURCE / THIẾU NGUỒN CHÍNH THỨC]")
        print("  => HÀNH ĐỘNG: Tuân thủ Mục 2.4 - Từ chối trả lời suy đoán, chuyển tiếp Staff Review.")
        return {
            "status": "NO_SOURCE",
            "action": "STAFF_REVIEW",
            "message": "Không tìm thấy tài liệu chính thức của VinFast xác nhận thông tin này. Đề xuất chuyển câu hỏi cho chuyên viên dịch vụ kiểm tra."
        }
    else:
        print(f"  => KẾT QUẢ: Tìm thấy {len(docs)} tài liệu phù hợp (Đạt chuẩn trích dẫn Mục 2.3 & 2.4):")
        citations = []
        for idx, (doc, meta, dist) in enumerate(zip(docs, metas, dists), 1):
            print(f"    [{idx}] Nguồn: {meta['source_id']} - {meta['title']} | Mục: {meta['section']}")
            print(f"        URL: {meta['url']}")
            print(f"        Chunk ID: {results['ids'][0][idx-1]}")
            print(f"        Khoảng cách: {dist:.4f}")
            print(f"        Nội dung: {doc[:150]}...\n")
            citations.append({
                "source_id": meta["source_id"],
                "chunk_id": results['ids'][0][idx-1],
                "title": meta["title"],
                "url": meta["url"],
                "section": meta["section"],
                "content_snippet": doc[:200]
            })
        return {
            "status": "SUCCESS",
            "citations": citations
        }

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--query":
        q = sys.argv[2] if len(sys.argv) > 2 else "Bảo hành xe VF 8 bao nhiêu năm?"
        query_knowledge_base(q)
    else:
        ingest_chunks()
        print("\n=== KIỂM THỬ TRÍCH DẪN & NGUYÊN TẮC 2.4 ===")
        # Test 1: Câu hỏi có nguồn chính thức (Bảo hành VF 8)
        query_knowledge_base("Thời hạn bảo hành pin xe VinFast VF 8 là bao lâu?", n_results=2)
        # Test 2: Câu hỏi có nguồn chính thức (Cứu hộ pin)
        query_knowledge_base("Cách yêu cầu dịch vụ cứu hộ pin ô tô điện VinFast 24/7", n_results=2)
        # Test 3: Câu hỏi không có trong nguồn / suy đoán
        query_knowledge_base("Cách hack động cơ hoặc bẻ khóa phần mềm VinFast", n_results=2, threshold_distance=0.85)
