import os
import json
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

RAW_DIR = r"d:\142.AI20K\P-142\data\raw"
PROCESSED_DIR = r"d:\142.AI20K\P-142\data\processed"
CARS_JSONL = r"d:\142.AI20K\P-142\eval\datasets\cars.jsonl"
OUTPUT_CHUNKS = os.path.join(PROCESSED_DIR, "chunks.jsonl")

os.makedirs(PROCESSED_DIR, exist_ok=True)

TARGET_CHUNK_SIZE = 500
OVERLAP = 80

def split_text_into_chunks(text: str, target_size: int = TARGET_CHUNK_SIZE, overlap: int = OVERLAP):
    """
    Split text into chunks of roughly target_size characters with overlap,
    preferring splits at sentence or newline boundaries.
    """
    text = text.strip()
    if not text:
        return []
    if len(text) <= target_size + 100:
        return [text]

    chunks = []
    start = 0
    total_len = len(text)

    while start < total_len:
        end = min(start + target_size, total_len)
        
        if end < total_len:
            # Look for suitable split point (newline, period, question mark, semicolon)
            split_window = text[max(start + target_size - 100, start): min(start + target_size + 50, total_len)]
            best_split = -1
            
            for sep in ['\n\n', '\n', '. ', '.\n', '; ', ' - ']:
                pos = split_window.rfind(sep)
                if pos != -1:
                    best_split = max(start + target_size - 100, start) + pos + len(sep)
                    break
            
            if best_split != -1 and best_split > start:
                end = best_split

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end >= total_len:
            break
            
        start = max(start + 1, end - overlap)

    return chunks

def parse_markdown_sections(text: str):
    """
    Parse a document into structured sections based on Markdown headers (#, ##, ###).
    """
    lines = text.split('\n')
    sections = []
    current_title = "Tổng quan"
    current_lines = []

    for line in lines:
        header_match = re.match(r'^(#{1,3})\s+(.+)$', line)
        if header_match:
            if current_lines:
                sec_text = '\n'.join(current_lines).strip()
                if sec_text:
                    sections.append((current_title, sec_text))
            current_title = header_match.group(2).strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        sec_text = '\n'.join(current_lines).strip()
        if sec_text:
            sections.append((current_title, sec_text))

    return sections

def process_raw_sources():
    all_chunks = []
    
    # Process SRC-001 through SRC-008
    for src_num in range(1, 9):
        src_id = f"SRC-{src_num:03d}"
        txt_path = os.path.join(RAW_DIR, f"{src_id}.txt")
        meta_path = os.path.join(RAW_DIR, f"{src_id}_meta.json")
        
        if not os.path.exists(txt_path) or not os.path.exists(meta_path):
            print(f"Bỏ qua {src_id} vì không tìm thấy file.")
            continue
            
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
            
        with open(txt_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        sections = parse_markdown_sections(content)
        chunk_idx = 1
        
        for sec_name, sec_text in sections:
            # If section text is reasonably short, keep as single chunk
            if len(sec_text) <= TARGET_CHUNK_SIZE + 100:
                raw_chunks = [sec_text]
            else:
                raw_chunks = split_text_into_chunks(sec_text, TARGET_CHUNK_SIZE, OVERLAP)
                
            for rc in raw_chunks:
                # Format chunk entry according to Section 2.3
                chunk_obj = {
                    "source_id": src_id,
                    "chunk_id": f"{src_id}-{chunk_idx:04d}",
                    "title": meta.get("title", ""),
                    "url": meta.get("url", ""),
                    "source_type": meta.get("source_type", "official_source"),
                    "verified_at": meta.get("verified_at", "2026-09-30"),
                    "applicable_models": meta.get("applicable_models", ["All"]),
                    "section": sec_name,
                    "content": rc
                }
                all_chunks.append(chunk_obj)
                chunk_idx += 1
                
        print(f"[{src_id}] Đã tạo {chunk_idx - 1} chunks từ '{meta.get('title')}'.")
        
    return all_chunks

def process_cars_jsonl():
    """
    Process cars.jsonl as SRC-009 (official_catalog specifications).
    """
    if not os.path.exists(CARS_JSONL):
        print("cars.jsonl không tồn tại, bỏ qua.")
        return []
        
    chunks = []
    src_id = "SRC-009"
    chunk_idx = 1
    
    with open(CARS_JSONL, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            car = json.loads(line)
            name = car.get("name", "Unknown Model")
            url = car.get("url", "https://vinfastauto.com/vn_vi")
            
            # 1. Chunk Overview / Card
            card = car.get("card", {})
            overview_parts = [f"Mẫu xe: {name}"]
            if card.get("price"):
                overview_parts.append(f"- Giá bán công bố: {card.get('price')}")
            if card.get("range"):
                overview_parts.append(f"- Quãng đường di chuyển (WLTP/NEDC): {card.get('range')}")
            if card.get("charging"):
                overview_parts.append(f"- Thời gian sạc: {card.get('charging')}")
            if card.get("seat"):
                overview_parts.append(f"- Số chỗ ngồi: {card.get('seat')}")
            if card.get("segment"):
                overview_parts.append(f"- Phân khúc xe: {card.get('segment')}")
            if card.get("tagline"):
                overview_parts.append(f"- Thông điệp: {card.get('tagline')}")
                
            overview_text = "\n".join(overview_parts)
            chunks.append({
                "source_id": src_id,
                "chunk_id": f"{src_id}-{chunk_idx:04d}",
                "title": f"Thông số tổng quan mẫu xe VinFast {name}",
                "url": url,
                "source_type": "official_catalog",
                "verified_at": "2026-09-30",
                "applicable_models": [name],
                "section": f"Tổng quan {name}",
                "content": overview_text
            })
            chunk_idx += 1
            
            # 2. Chunk Versions & Specs
            versions = car.get("versions", {})
            ver_items = []
            if isinstance(versions, dict):
                for v_name, v_data in versions.items():
                    ver_items.append((v_name, v_data if isinstance(v_data, dict) else {}))
            elif isinstance(versions, list):
                for item in versions:
                    if isinstance(item, dict):
                        ver_items.append((item.get("name", "Tiêu chuẩn"), item))
                    elif isinstance(item, str):
                        ver_items.append((item, {}))

            for v_name, v_data in ver_items:
                spec_lines = [f"Thông số chi tiết VinFast {name} - Phiên bản {v_name}:"]
                for k, v in v_data.items():
                    if k not in ["name", "raw_specs"]:
                        spec_lines.append(f"- {k}: {v}")
                
                # Raw specs if any
                raw_specs = v_data.get("raw_specs", {})
                if isinstance(raw_specs, dict) and raw_specs:
                    spec_lines.append("Chi tiết trang bị:")
                    for sk, sv in raw_specs.items():
                        spec_lines.append(f"  + {sk}: {sv}")
                        
                spec_text = "\n".join(spec_lines)
                spec_chunks = split_text_into_chunks(spec_text, TARGET_CHUNK_SIZE, OVERLAP)
                for sc in spec_chunks:
                    chunks.append({
                        "source_id": src_id,
                        "chunk_id": f"{src_id}-{chunk_idx:04d}",
                        "title": f"Thông số kỹ thuật VinFast {name} {v_name}",
                        "url": url,
                        "source_type": "official_catalog",
                        "verified_at": "2026-09-30",
                        "applicable_models": [name],
                        "section": f"Thông số kỹ thuật {name} {v_name}",
                        "content": sc
                    })
                    chunk_idx += 1
                    
            # 3. Chunk Highlights / Features
            highlights = car.get("highlights", [])
            if highlights:
                hl_lines = [f"Đặc điểm nổi bật của VinFast {name}:"]
                for hl in highlights:
                    if isinstance(hl, dict):
                        h_title = hl.get("title", "")
                        h_desc = hl.get("desc", "")
                        hl_lines.append(f"- {h_title}: {h_desc}")
                    elif isinstance(hl, str):
                        hl_lines.append(f"- {hl}")
                hl_text = "\n".join(hl_lines)
                hl_chunks = split_text_into_chunks(hl_text, TARGET_CHUNK_SIZE, OVERLAP)
                for hc in hl_chunks:
                    chunks.append({
                        "source_id": src_id,
                        "chunk_id": f"{src_id}-{chunk_idx:04d}",
                        "title": f"Tính năng & Điểm nổi bật VinFast {name}",
                        "url": url,
                        "source_type": "official_catalog",
                        "verified_at": "2026-09-30",
                        "applicable_models": [name],
                        "section": f"Điểm nổi bật {name}",
                        "content": hc
                    })
                    chunk_idx += 1

    print(f"[{src_id}] Đã tạo {chunk_idx - 1} chunks từ catalog xe thương mại (cars.jsonl).")
    return chunks

def main():
    print("=== BẮT ĐẦU CHUNKING CHUẨN HÓA KNOWLEDGE BASE (MỤC 2.3) ===")
    chunks = process_raw_sources()
    catalog_chunks = process_cars_jsonl()
    all_chunks = chunks + catalog_chunks
    
    print(f"Tổng số chunks đã tạo: {len(all_chunks)}")
    
    with open(OUTPUT_CHUNKS, "w", encoding="utf-8") as f:
        for c in all_chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
            
    print(f"Đã lưu thành công vào: {OUTPUT_CHUNKS}")
    
    # Save a copy in workspace
    local_output_dir = r"d:\Downloads\New folder\data\processed"
    os.makedirs(local_output_dir, exist_ok=True)
    local_output_chunks = os.path.join(local_output_dir, "chunks.jsonl")
    with open(local_output_chunks, "w", encoding="utf-8") as f:
        for c in all_chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    print(f"Đã lưu bản sao vào: {local_output_chunks}")

if __name__ == "__main__":
    main()
