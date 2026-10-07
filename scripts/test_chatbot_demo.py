import asyncio
import sys
import json

sys.stdout.reconfigure(encoding='utf-8')

import os

# Ensure P-142 is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agents.chatbot_agent import process_chat_message

TEST_PROMPTS = [
    ("1. Tra cứu chính sách bảo hành (RAG + Citation)", "Thời hạn bảo hành pin xe VinFast VF 8 là bao lâu?"),
    ("2. Tình huống nguy hiểm khẩn cấp (Hard Safety)", "Cứu tôi với, xe đang chạy dưới gầm bốc khói và có mùi khét!"),
    ("3. Thao tác trên App VinFast (Hướng dẫn dịch vụ)", "Làm thế nào để đặt lịch bảo dưỡng xe trên ứng dụng VinFast?"),
    ("4. Câu hỏi ngoài phạm vi không có nguồn (Rule 2.4 Fallback)", "Giá vé máy bay Vietnam Airlines đi Đà Nẵng là bao nhiêu?")
]

async def main():
    print("=" * 70)
    print("🤖 KIỂM THỬ CHATBOT AGENT DEMO (CORE AI SLICE)")
    print("=" * 70)

    for title, prompt in TEST_PROMPTS:
        print(f"\n👉 [KỊCH BẢN]: {title}")
        print(f"👤 Khách hỏi: \"{prompt}\"")
        
        response = await process_chat_message(prompt)
        
        print(f"🤖 Bot trả lời:\n{response['reply']}")
        print(f"   * Intent: {response['intent']}")
        print(f"   * Priority: {response['priority']}")
        print(f"   * Cần Staff Review: {response['needs_staff_review']}")
        print(f"   * Kích hoạt An toàn: {response['is_safety_trigger']}")
        if response['citations']:
            print("   * Trích dẫn nguồn (Citations):")
            for c in response['citations']:
                print(f"     - [{c['source_id']}] {c['title']} ({c['url']})")
        print("-" * 70)

if __name__ == "__main__":
    asyncio.run(main())
