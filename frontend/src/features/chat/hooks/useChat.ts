"use client";

import { useState, useEffect } from "react";
import { ChatMessage, VehicleModel } from "../types";
import { sendChatMessage } from "../api/chatApi";
import { checkHardEmergency } from "../constants";

export interface ChatUserContext {
  userName?: string;
  vehicleModel?: string;
  caseId?: string | null;
}

export function getSalutation(fullName?: string): { title: string; shortName: string; pronoun: string } {
  if (!fullName || !fullName.trim()) {
    return { title: "", shortName: "", pronoun: "bạn" };
  }
  const parts = fullName.trim().split(/\s+/);
  const shortName = parts[parts.length - 1];
  const lower = fullName.toLowerCase();
  const isFemale =
    lower.includes("thị") ||
    ["hoa", "lan", "mai", "hương", "trang", "linh", "ngọc", "thảo", "hằng", "nhung", "yến", "my", "vy"].includes(shortName.toLowerCase());
  const isMale =
    lower.includes("văn") ||
    ["an", "bình", "cường", "dũng", "hùng", "long", "minh", "nam", "phúc", "quân", "tuấn", "việt"].includes(shortName.toLowerCase());

  if (isFemale) {
    return { title: "chị", shortName, pronoun: "chị" };
  }
  if (isMale) {
    return { title: "anh", shortName, pronoun: "anh" };
  }
  return { title: "", shortName, pronoun: "bạn" };
}

export function createWelcomeMessage(context?: ChatUserContext | string): ChatMessage {
  const ctx: ChatUserContext =
    typeof context === "string" ? { userName: context } : context || {};
  const { userName, vehicleModel, caseId } = ctx;
  const { title, shortName, pronoun } = getSalutation(userName);

  let content: string;
  if (shortName) {
    const greetingStart = title ? `Chào ${title} ${shortName}!` : `Chào ${shortName}!`;
    if (caseId) {
      content = `${greetingStart} Hồ sơ ${caseId} đang được kỹ thuật viên kiểm tra. Em giúp gì thêm được cho ${pronoun} hôm nay ạ?`;
    } else if (vehicleModel) {
      content = `${greetingStart} Em giúp gì được cho ${pronoun} về chiếc ${vehicleModel} hôm nay ạ?`;
    } else {
      content = `${greetingStart} Em là Trợ lý VF Serv. Em có thể hỗ trợ gì cho ${pronoun} hôm nay ạ?`;
    }
  } else {
    // Khách vãng lai (Guest)
    if (caseId) {
      content = `Chào bạn! Hồ sơ ${caseId} đang được kỹ thuật viên kiểm tra. Bạn cần em hỗ trợ thêm thông tin gì không ạ?`;
    } else {
      content = `Chào bạn! Em là Trợ lý VF Serv. Em có thể hỗ trợ gì cho bạn hôm nay ạ?`;
    }
  }

  return {
    id: "welcome-1",
    sender: "AGENT",
    content,
    timestamp: new Date().toISOString(),
    suggested_replies: [
      "Tư vấn xe",
      "Trạm sạc & ứng dụng",
      "Bảo hành & bảo dưỡng",
      "Báo sự cố kỹ thuật",
    ],
  };
}

export const INITIAL_WELCOME_MESSAGE: ChatMessage = createWelcomeMessage();

export function useChat(context?: ChatUserContext | string) {
  const ctx: ChatUserContext =
    typeof context === "string" ? { userName: context } : context || {};
  const [messages, setMessages] = useState<ChatMessage[]>(() => [createWelcomeMessage(ctx)]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [selectedModel, setSelectedModel] = useState<VehicleModel>(
    (ctx.vehicleModel as VehicleModel) || "VF8"
  );
  const [sessionId, setSessionId] = useState(() => `sess_vf_${Math.random().toString(36).substring(2, 9)}`);
  const [currentCaseId, setCurrentCaseId] = useState<string | null>(ctx.caseId || null);
  const [criticalBanner, setCriticalBanner] = useState(false);
  const [criticalBannerDismissed, setCriticalBannerDismissed] = useState(false);
  const [sessionHasCritical, setSessionHasCritical] = useState(false);
  const [requestLocation, setRequestLocation] = useState(false);

  useEffect(() => {
    setMessages((prev) => {
      if (prev.length === 1 && prev[0].id === "welcome-1") {
        return [createWelcomeMessage(ctx)];
      }
      return prev;
    });
  }, [ctx.userName, ctx.vehicleModel, ctx.caseId]);

  const resetChat = () => {
    setMessages([createWelcomeMessage(ctx)]);
    setInput("");
    setLoading(false);
    setCurrentCaseId(null);
    setCriticalBanner(false);
    setCriticalBannerDismissed(false);
    setSessionHasCritical(false);
    setRequestLocation(false);
    setSessionId(`sess_vf_${Math.random().toString(36).substring(2, 9)}`);
  };

  const updateMessageChips = (messageId: string, newChips: string[]) => {
    setMessages((prev) =>
      prev.map((msg) => (msg.id === messageId ? { ...msg, suggested_replies: newChips } : msg))
    );
  };

  const dismissCriticalBanner = () => {
    setCriticalBannerDismissed(true);
  };

  const restoreCriticalBanner = () => {
    setCriticalBannerDismissed(false);
  };

  const sendMessage = async (
    messageText?: string,
    attachmentIds?: string[],
    image?: { src: string; name: string; caption: string },
  ) => {
    const textToSend = messageText || input.trim();
    if (!textToSend || loading) return;

    // Sử dụng bộ từ khóa nguy hiểm đồng bộ 100% với Backend (guardrails.py)
    // để banner hiện tức thì trước khi backend trả lời (tránh lag giật tâm lý khách hàng).
    const isHardEmergency = checkHardEmergency(textToSend);
    if (isHardEmergency) {
      setCriticalBanner(true);
      setCriticalBannerDismissed(false);
    }

    const userMsg: ChatMessage = {
      id: `usr_${Date.now()}`,
      sender: "CUSTOMER",
      content: image ? image.caption : textToSend,
      timestamp: new Date().toISOString(),
      attachment_ids: attachmentIds,
      image: image ? { src: image.src, name: image.name } : undefined,
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
          customer_name: ctx.userName,
        },
      });

      // Đảm bảo có một khoảng delay tự nhiên (~400ms) để người dùng thấy AI đang phân tích
      const elapsed = Date.now() - startTime;
      if (elapsed < 400) {
        await new Promise((resolve) => setTimeout(resolve, 400 - elapsed));
      }

      if (!response.success || !response.data) {
        throw new Error("Chat API returned no usable response");
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

        // Banner khẩn cấp gắn với trạng thái hồ sơ / phiên làm việc:
        // Nếu trong phiên có sự cố CRITICAL (hoặc show_emergency_banner từ backend), banner không tự tắt
        const isServerCritical = Boolean(data.show_emergency_banner || data.priority === "CRITICAL");
        if (isServerCritical) {
          setSessionHasCritical(true);
          setCriticalBanner(true);
        } else if (sessionHasCritical) {
          setCriticalBanner(true);
        } else {
          setCriticalBanner(false);
        }

        // Backend trả về cờ request_location rõ ràng:
        if (data.request_location !== undefined) {
          setRequestLocation(Boolean(data.request_location));
        } else if (isServerCritical) {
          setRequestLocation(true);
        }

        // 3. AI trả lời xuất hiện sau khi suy nghĩ xong
        setMessages((prev) => [...prev, agentMsg]);
      }
    } catch {
      const errorMsg: ChatMessage = {
        id: `error_${Date.now()}`,
        sender: "AGENT",
        content: "Chưa nhận được phản hồi từ hệ thống. Anh/chị vui lòng gửi lại câu hỏi sau ít phút. Lượt gửi này chưa xác nhận tạo hồ sơ hoặc thông báo cứu hộ.",
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMsg]);
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
    criticalBannerDismissed,
    dismissCriticalBanner,
    restoreCriticalBanner,
    sessionHasCritical,
    requestLocation,
    sendMessage,
    resetChat,
    updateMessageChips,
  };
}
