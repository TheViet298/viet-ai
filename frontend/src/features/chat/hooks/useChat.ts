"use client";

import { useState } from "react";
import { ChatMessage, Citation, VehicleModel } from "../types";
import { sendChatMessage } from "../api/chatApi";

export const INITIAL_WELCOME_MESSAGE: ChatMessage = {
  id: "welcome-1",
  sender: "AGENT",
  content:
    "Xin chào anh/chị! Em là Trợ lý Dịch vụ VinFast AI. Em có thể hỗ trợ anh/chị tra cứu hướng dẫn sử dụng, giải đáp về sạc pin/ứng dụng, hoặc tiếp nhận sự cố kỹ thuật của xe.",
  timestamp: new Date().toISOString(),
};

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([INITIAL_WELCOME_MESSAGE]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [selectedModel, setSelectedModel] = useState<VehicleModel>("VF8");
  const [sessionId, setSessionId] = useState(() => `sess_vf_${Math.random().toString(36).substring(2, 9)}`);
  const [currentCaseId, setCurrentCaseId] = useState<string | null>(null);
  const [criticalBanner, setCriticalBanner] = useState(false);

  const resetChat = () => {
    setMessages([INITIAL_WELCOME_MESSAGE]);
    setInput("");
    setLoading(false);
    setCurrentCaseId(null);
    setCriticalBanner(false);
    setSessionId(`sess_vf_${Math.random().toString(36).substring(2, 9)}`);
  };

  const sendMessage = async (messageText?: string, attachmentIds?: string[]) => {
    const textToSend = messageText || input.trim();
    if (!textToSend || loading) return;

    // Check emergency keywords client-side for immediate response
    const isEmergency =
      textToSend.toLowerCase().includes("cao tốc") ||
      textToSend.toLowerCase().includes("mất phanh") ||
      textToSend.toLowerCase().includes("rùa vàng");

    if (isEmergency) {
      setCriticalBanner(true);
    }

    const userMsg: ChatMessage = {
      id: `usr_${Date.now()}`,
      sender: "CUSTOMER",
      content: textToSend,
      timestamp: new Date().toISOString(),
      attachment_ids: attachmentIds,
    };

    // 1. Xuất hiện câu hỏi của User trước
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    // 2. Kích hoạt trạng thái AI đang suy nghĩ
    setLoading(true);

    const startTime = Date.now();

    try {
      const response = await sendChatMessage({
        sessionId,
        message: textToSend,
        caseId: currentCaseId,
        attachmentIds: attachmentIds,
        clientContext: {
          mock_customer_id: "CUST_MOCK_01",
          vehicle_model: selectedModel,
          vehicle_code_mock: `VF-${selectedModel}-8899`,
        },
      });

      // Đảm bảo có một khoảng delay tự nhiên (~400ms) để người dùng thấy AI đang phân tích
      const elapsed = Date.now() - startTime;
      if (elapsed < 400) {
        await new Promise((resolve) => setTimeout(resolve, 400 - elapsed));
      }

      if (response.success && response.data) {
        const data = response.data;
        if (data.case_id) {
          setCurrentCaseId(data.case_id);
        }

        const agentMsg: ChatMessage = {
          id: `agent_${Date.now()}`,
          sender: "AGENT",
          content: data.message,
          timestamp: new Date().toISOString(),
          response_type: data.response_type,
          citations: data.citations,
          suggested_replies: data.suggested_replies,
          safe_guidance: data.safe_guidance,
          case_id: data.case_id,
          priority: data.priority,
        };

        if (data.priority === "CRITICAL") {
          setCriticalBanner(true);
        }

        // 3. AI trả lời xuất hiện sau khi suy nghĩ xong
        setMessages((prev) => [...prev, agentMsg]);
      }
    } catch {
      // Mock fallback response for smooth testing before backend is started
      const elapsed = Date.now() - startTime;
      if (elapsed < 400) {
        await new Promise((resolve) => setTimeout(resolve, 400 - elapsed));
      }

      // Rich fallback response for smooth testing and demonstration
      let fallbackContent = `Dạ em đã ghi nhận thông tin về xe ${selectedModel}. Theo cẩm nang kỹ thuật VinFast, khi gặp tình huống này anh/chị nên kiểm tra kết nối súng sạc và quan sát đèn chỉ báo trên táp-lô.`;
      let fallbackCitations: Citation[] | undefined = undefined;
      let fallbackGuidance: string | undefined = undefined;
      let fallbackReplies = ["Mã lỗi CC01, trụ P02", "Đèn trụ nháy đỏ", "Xe dừng hẳn, an toàn"];

      let isCrit = false;

      if (textToSend.toLowerCase().includes("cao tốc") || textToSend.toLowerCase().includes("mất phanh") || textToSend.toLowerCase().includes("cứu hộ")) {
        isCrit = true;
        setCriticalBanner(true);
        fallbackContent = `Đội cứu hộ phản ứng nhanh 24/7 và Cố vấn VinFast đã được thông báo ở mức ưu tiên cao nhất. Anh/chị hãy bật ngay đèn cảnh báo hazard, rời khỏi xe và đứng sau hộ lan an toàn cao tốc.`;
        fallbackCitations = [
          {
            source_id: "SRC-EMERGENCY-01",
            title: "Quy trình xử lý sự cố khẩn cấp trên đường cao tốc — Sổ tay VinFast",
            url: "https://vinfastauto.com/vn_vi/chinh-sach-bao-hanh-va-cuu-ho-xe-dien",
          },
        ];
        fallbackReplies = ["Đã vào làn an toàn", "Xem bản đồ cứu hộ ›", "Gọi 1900-232389"];
      } else if (textToSend.toLowerCase().includes("bảo dưỡng") || textToSend.toLowerCase().includes("12.000km")) {
        fallbackContent = `Cấp bảo dưỡng 12.000km cho xe ${selectedModel} bao gồm kiểm tra hệ thống pin cao áp, độ mòn phanh và nâng cấp phần mềm ECU. Anh/chị nên đặt hẹn trước để xưởng chuẩn bị sẵn vật tư.`;
        fallbackCitations = [
          {
            source_id: "SRC-MAINT-12K",
            title: "Cẩm nang bảo dưỡng định kỳ xe điện VinFast — Mục 3.1",
            url: "https://vinfastauto.com/vn_vi/chinh-sach-bao-hanh-va-cuu-ho-xe-dien",
          },
        ];
        fallbackReplies = ["Xem danh sách xưởng", "Đặt hẹn xưởng gần nhất", "Chi phí ước tính"];
      } else if (
        textToSend.toLowerCase().includes("sạc") ||
        textToSend.toLowerCase().includes("cc01") ||
        textToSend.toLowerCase().includes("trụ") ||
        textToSend.toLowerCase().includes("không vào điện")
      ) {
        fallbackContent = `Lỗi CC01 thường do súng sạc chưa khớp ngàm hoặc timeout giao tiếp BMS. Anh/chị bấm nút dừng sạc trên màn hình xe (hoặc bấm mở khóa cửa 2 lần) rồi cắm lại súng dứt khoát.`;
        fallbackCitations = [
          {
            source_id: "SRC-DC-CC01",
            title: "Sổ tay sạc nhanh DC VinFast — Mục 4.2 Xử lý mã CC01",
            url: "https://vinfastauto.com/vn_vi/chinh-sach-va-bieu-phi-sac-pin-cong-cong",
          },
        ];
        fallbackReplies = ["Xem bản đồ trạm sạc ›", "Mã lỗi CC01, trụ P02", "Đèn trụ nháy đỏ"];
      } else if (textToSend.toLowerCase().includes("rùa vàng")) {
        isCrit = true;
        setCriticalBanner(true);
        fallbackContent = `Biểu tượng Con Rùa Vàng (Turtle Mode) kích hoạt để bảo vệ pin khi dung lượng dưới 10% hoặc nhiệt độ pin tăng cao. Anh/chị vui lòng giảm tốc độ, tắt bớt điều hòa và di chuyển vào trạm sạc hoặc vị trí an toàn gần nhất.`;
        fallbackCitations = [
          {
            source_id: "SRC-TURTLE-WARN",
            title: "Sổ tay an toàn vận hành xe điện VinFast — Chương 6",
            url: "https://vinfastauto.com/vn_vi/chinh-sach-bao-hanh-va-cuu-ho-xe-dien",
          },
        ];
        fallbackReplies = ["Đã vào làn an toàn", "Xem bản đồ cứu hộ ›", "Tìm trạm sạc gần nhất"];
      }

      // Tạo mã Case ID động theo từng phiên chat thật (không fix cứng ngày tháng cũ)
      const shouldCreateCase =
        textToSend.toLowerCase().includes("sạc") ||
        textToSend.toLowerCase().includes("rùa vàng") ||
        textToSend.toLowerCase().includes("cao tốc") ||
        textToSend.toLowerCase().includes("cứu hộ") ||
        textToSend.toLowerCase().includes("mất phanh");

      let assignedCaseId: string | undefined = undefined;
      if (shouldCreateCase) {
        if (currentCaseId) {
          assignedCaseId = currentCaseId;
        } else {
          const nowStr = new Date().toISOString().slice(0, 10).replace(/-/g, "");
          const rand = Math.floor(100 + Math.random() * 900);
          assignedCaseId = `CASE-${nowStr}-${rand}`;
          setCurrentCaseId(assignedCaseId);
        }
      }

      const fallbackMsg: ChatMessage = {
        id: `mock_${Date.now()}`,
        sender: "AGENT",
        content: fallbackContent,
        timestamp: new Date().toISOString(),
        citations: fallbackCitations,
        safe_guidance: fallbackGuidance,
        suggested_replies: fallbackReplies,
        case_id: assignedCaseId,
        priority: isCrit ? "CRITICAL" : undefined,
      };
      setMessages((prev) => [...prev, fallbackMsg]);
    } finally {
      setLoading(false);
    }
  };

  return {
    messages,
    input,
    setInput,
    loading,
    selectedModel,
    setSelectedModel,
    sessionId,
    currentCaseId,
    criticalBanner,
    setCriticalBanner,
    sendMessage,
    resetChat,
  };
}
