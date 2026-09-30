"use client";

import { useState } from "react";
import { ChatMessage, VehicleModel } from "../types";
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
  const [sessionId] = useState(() => `sess_vf_${Math.random().toString(36).substring(2, 9)}`);
  const [currentCaseId, setCurrentCaseId] = useState<string | null>(null);
  const [criticalBanner, setCriticalBanner] = useState(false);

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

    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

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

        setMessages((prev) => [...prev, agentMsg]);
      }
    } catch {
      // Mock fallback response for smooth testing before backend is started
      const fallbackMsg: ChatMessage = {
        id: `mock_${Date.now()}`,
        sender: "AGENT",
        content: `Dạ em đã ghi nhận thông tin sự cố của xe ${selectedModel}. Hệ thống đang kết nối đến máy chủ trung tâm để phân loại và làm rõ.`,
        timestamp: new Date().toISOString(),
        suggested_replies: [
          "Mã lỗi CC01, trụ P02",
          "Đèn trụ nháy đỏ",
          "Xe dừng hẳn, an toàn",
        ],
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
  };
}
