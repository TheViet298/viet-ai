"use client";

import { useState, useEffect, useRef } from "react";
import { ChatMessage } from "../types";
import { sendChatMessage, getCaseStatus, acknowledgeCaseSafety, getSessionHistory } from "../api/chatApi";

function getAuthOwner(): string {
  if (typeof window === "undefined") return "guest";
  try {
    const auth = localStorage.getItem("vf_serviceflow_auth");
    if (auth) {
      const parsed = JSON.parse(auth);
      if (parsed?.id) return `user_${parsed.id}`;
    }
    const token = localStorage.getItem("vf_access_token");
    if (token) return `token_${token.slice(-8)}`;
  } catch {}
  return "guest";
}

function storageKey(kind = "case") {
  return typeof window === "undefined" ? null : `vf_chat_${kind}:${getAuthOwner()}`;
}

function storedCaseId(): string | null {
  try { const key = storageKey(); return key ? localStorage.getItem(key) : null; } catch { return null; }
}

export interface ChatUserContext {
  userName?: string;
  vehicleModel?: string;
  caseId?: string | null;
}

export function getSalutation(fullName?: string): { title: string; shortName: string; pronoun: string } {
  if (!fullName || !fullName.trim() || ["guest", "khách", "khách hàng", "anh/chị"].includes(fullName.trim().toLowerCase())) {
    return { title: "", shortName: "", pronoun: "Quý khách" };
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
  return { title: "", shortName, pronoun: "Quý khách" };
}

export function createWelcomeMessage(context?: ChatUserContext | string, timestamp = ""): ChatMessage {
  const ctx: ChatUserContext =
    typeof context === "string" ? { userName: context } : context || {};
  const { userName, caseId } = ctx;
  const { title, shortName, pronoun } = getSalutation(userName);

  let content: string;
  if (shortName && !["guest", "khách", "khách hàng", "anh/chị"].includes(shortName.toLowerCase())) {
    const greetingStart = title ? `Chào ${title} ${shortName}!` : `Chào ${shortName}!`;
    if (caseId) {
      content = `${greetingStart} Hồ sơ ${caseId} đang được kỹ thuật viên kiểm tra. Em giúp gì thêm được cho ${pronoun} hôm nay ạ?`;
    } else {
      content = `${greetingStart} Em là Trợ lý VFServ. Em có thể hỗ trợ gì cho ${pronoun} hôm nay ạ?`;
    }
  } else {
    // Khách vãng lai (Guest)
    if (caseId) {
      content = `Chào Quý khách! Hồ sơ ${caseId} đang được kỹ thuật viên kiểm tra. Quý khách cần em hỗ trợ thêm thông tin gì không ạ?`;
    } else {
      content = `Chào Quý khách! Em là Trợ lý VFServ. Em có thể hỗ trợ gì cho Quý khách hôm nay ạ?`;
    }
  }

  return {
    id: "welcome-1",
    sender: "AGENT",
    content,
    timestamp,
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
  const [sessionId, setSessionId] = useState(() => `sess_vf_${Math.random().toString(36).substring(2, 9)}`);
  const [currentCaseId, setCurrentCaseId] = useState<string | null>(() => ctx.caseId || null);
  const [storageRestored, setStorageRestored] = useState(false);
  const [criticalBanner, setCriticalBanner] = useState(false);
  const [criticalBannerDismissed, setCriticalBannerDismissed] = useState(false);
  const [sessionHasCritical, setSessionHasCritical] = useState(false);
  const [requestLocation, setRequestLocation] = useState(false);
  const [safetyPending, setSafetyPending] = useState(false);
  const [safetyError, setSafetyError] = useState<string | null>(null);
  const [incidentVersion, setIncidentVersion] = useState<number | null>(null);
  const safetyRef = useRef({ caseId: currentCaseId, version: 0, acknowledged: false, epoch: 0 });
  const failedRequest = useRef<{ key: string; id: string; caseId: string | null } | null>(null);
  const conversationGeneration = useRef(0);
  const initialCaseId = useRef(ctx.caseId);

  const applySafety = (input: { case_id?: string | null; incident_version?: number | null; safety_status?: string; emergency_context?: { case_id: string; incident_version: number; safety_status: string } | null }) => {
    const data = input.emergency_context || input;
    const version = data.incident_version || 0;
    if (data.case_id !== safetyRef.current.caseId) safetyRef.current = { ...safetyRef.current, caseId: data.case_id || null, version: 0, acknowledged: false };
    if (version < safetyRef.current.version) return false;
    const acknowledged = data.safety_status === "customer_reported_safe" || (version === safetyRef.current.version && safetyRef.current.acknowledged);
    safetyRef.current.version = version;
    safetyRef.current.acknowledged = acknowledged;
    setIncidentVersion(data.incident_version || null);
    setCriticalBannerDismissed(acknowledged);
    return true;
  };

  useEffect(() => {
    const caseId = initialCaseId.current;
    const savedCase = storedCaseId();
    if (!caseId) setCurrentCaseId(savedCase);
    if (!caseId || caseId === savedCase) {
      try {
        const key = storageKey("session");
        const savedSession = key ? localStorage.getItem(key) : null;
        if (savedSession && /^sess_vf_[a-z0-9_-]+$/.test(savedSession) && savedSession.length <= 64) {
          setSessionId(savedSession);
          void (async () => {
            try {
              const hist = await getSessionHistory(savedSession);
              if (hist?.success && hist?.data?.messages && hist.data.messages.length > 0) {
                const mapped: ChatMessage[] = hist.data.messages.map((m) => ({
                  id: m.id,
                  sender: m.sender === "CUSTOMER" ? "CUSTOMER" : "AGENT",
                  content: m.content,
                  timestamp: m.timestamp,
                  response_type: m.response_type,
                  citations: m.citations,
                  suggested_replies: m.suggested_replies,
                  safe_guidance: m.safe_guidance,
                  case_id: m.case_id,
                  priority: m.priority,
                }));
                setMessages(mapped);
                if (hist.data.case_id && !caseId) {
                  setCurrentCaseId(hist.data.case_id);
                }
              }
            } catch { /* Continue with default welcome message when storage/api unavailable. */ }
          })();
        }
      } catch { /* Continue with a fresh session when storage is unavailable. */ }
    }
    setStorageRestored(true);
  }, []);

  useEffect(() => {
    if (!storageRestored) return;
    try { const key = storageKey("session"); if (key) localStorage.setItem(key, sessionId); } catch {}
  }, [sessionId, storageRestored]);

  useEffect(() => {
    if (!storageRestored) return;
    try { const key = storageKey(); if (key) { if (currentCaseId) localStorage.setItem(key, currentCaseId); else localStorage.removeItem(key); } } catch {}
    if (!currentCaseId) return;
    let cancelled = false;
    const refresh = async () => {
      const epoch = safetyRef.current.epoch;
      try {
        const response = await getCaseStatus(currentCaseId);
        if (cancelled || epoch !== safetyRef.current.epoch || !response.success) return;
        if (!applySafety(response.data)) return;
        const active = !["Closed", "Resolved"].includes(response.data.status);
        const critical = Boolean(response.data.emergency_context || (active && response.data.priority === "CRITICAL"));
        setCriticalBanner(critical);
        setSessionHasCritical(critical);
      } catch { /* Retain the last confirmed state while offline. */ }
    };
    void refresh();
    const timer = setInterval(refresh, 10000);
    const onFocus = () => { void refresh(); };
    window.addEventListener("focus", onFocus);
    return () => { cancelled = true; clearInterval(timer); window.removeEventListener("focus", onFocus); };
  }, [currentCaseId, storageRestored]);

  useEffect(() => {
    setMessages((prev) => {
      if (prev.length === 1 && prev[0].id === "welcome-1") {
        return [createWelcomeMessage({ userName: ctx.userName, caseId: ctx.caseId }, prev[0].timestamp || new Date().toISOString())];
      }
      return prev;
    });
  }, [ctx.userName, ctx.caseId]);

  const resetChat = () => {
    ++conversationGeneration.current;
    setMessages([createWelcomeMessage(ctx, new Date().toISOString())]);
    setInput("");
    setLoading(false);
    setCurrentCaseId(null);
    setCriticalBanner(false);
    setCriticalBannerDismissed(false);
    setSessionHasCritical(false);
    setRequestLocation(false);
    setSessionId(`sess_vf_${Math.random().toString(36).substring(2, 9)}`);
    safetyRef.current = { caseId: null, version: 0, acknowledged: false, epoch: safetyRef.current.epoch + 1 };
    failedRequest.current = null;
    setIncidentVersion(null);
    setSafetyError(null);
    setSafetyPending(false);
  };

  const updateMessageChips = (messageId: string, newChips: string[]) => {
    setMessages((prev) =>
      prev.map((msg) => (msg.id === messageId ? { ...msg, suggested_replies: newChips } : msg))
    );
  };

  const dismissCriticalBanner = async () => {
    const safetyCaseId = safetyRef.current.caseId;
    if (!safetyCaseId || !incidentVersion || safetyPending) return;
    const epoch = ++safetyRef.current.epoch;
    setSafetyPending(true);
    setSafetyError(null);
    try {
      const response = await acknowledgeCaseSafety(safetyCaseId, incidentVersion);
      if (!response.success || !response.data) throw new Error("No acknowledgement");
      if (epoch === safetyRef.current.epoch) {
        ++safetyRef.current.epoch;
        applySafety(response.data);
      }
    } catch {
      if (epoch === safetyRef.current.epoch) setSafetyError("Chưa lưu được xác nhận an toàn. Anh/chị vui lòng thử lại.");
    } finally { setSafetyPending(false); }
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

    ++safetyRef.current.epoch;
    const generation = conversationGeneration.current;
    const requestKey = JSON.stringify([sessionId, textToSend, attachmentIds || []]);
    const retry = failedRequest.current?.key === requestKey ? failedRequest.current : null;
    const request = retry || { key: requestKey, id: crypto.randomUUID(), caseId: currentCaseId };
    failedRequest.current = request;

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
    setRequestLocation(false);
    // 2. Kích hoạt trạng thái AI đang suy nghĩ
    setLoading(true);

    const startTime = Date.now();

    try {
      const response = await sendChatMessage({
        requestId: request.id,
        sessionId,
        message: textToSend,
        caseId: request.caseId,
        attachmentIds: attachmentIds,
        clientContext: {
          mock_customer_id: "CUST_MOCK_01",
          customer_name: ctx.userName,
        },
      });

      // Đảm bảo có một khoảng delay tự nhiên (~400ms) để người dùng thấy AI đang phân tích
      const elapsed = Date.now() - startTime;
      if (elapsed < 400) {
        await new Promise((resolve) => setTimeout(resolve, 400 - elapsed));
      }
      if (generation !== conversationGeneration.current) return;

      if (!response.success || !response.data) {
        throw new Error("Chat API returned no usable response");
      }

      if (response.success && response.data) {
        const data = response.data;
        ++safetyRef.current.epoch;
        failedRequest.current = null;
        applySafety(data);
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
        } else {
          setCriticalBanner(false);
          setSessionHasCritical(false);
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
    } catch (err: unknown) {
      if (generation !== conversationGeneration.current) return;
      let errorContent = "Chưa nhận được phản hồi từ hệ thống. Anh/chị vui lòng gửi lại câu hỏi sau ít phút. Lượt gửi này chưa xác nhận tạo hồ sơ hoặc thông báo cứu hộ.";
      if (err && typeof err === "object" && "message" in err && typeof err.message === "string") {
        try {
          const match = err.message.match(/Chat API error \(\d+\): (.*)/);
          if (match && match[1]) {
            const parsed = JSON.parse(match[1]);
            if (parsed.detail) {
              errorContent = parsed.detail;
            }
          }
        } catch {
          // Keep default message if parsing fails
        }
      }
      const errorMsg: ChatMessage = {
        id: `error_${Date.now()}`,
        sender: "AGENT",
        content: errorContent,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      if (generation === conversationGeneration.current) setLoading(false);
    }
  };

  return {
    messages,
    input,
    setInput,
    loading,
    sessionId,
    currentCaseId,
    criticalBanner,
    setCriticalBanner,
    criticalBannerDismissed,
    dismissCriticalBanner,
    restoreCriticalBanner,
    safetyPending,
    safetyError,
    canAcknowledgeSafety: Boolean(currentCaseId && incidentVersion),
    sessionHasCritical,
    requestLocation,
    sendMessage,
    resetChat,
    updateMessageChips,
  };
}
