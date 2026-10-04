import {
  ApiResponse,
  ArticleItem,
  AttachmentOut,
  ChatResponseData,
  ClientContext,
  CustomerCaseItem,
} from "../types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function getCustomerAuthHeaders(): Promise<Record<string, string>> {
  if (typeof window === "undefined") return {};
  let token = localStorage.getItem("vf_customer_token");
  if (!token) {
    try {
      const res = await fetch(`${BASE_URL}/api/v1/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: "customer@vinfast.vn",
          password: "customer123",
        }),
      });
      if (res.ok) {
        const json = await res.json();
        token = json?.data?.token;
        if (token) localStorage.setItem("vf_customer_token", token);
      }
    } catch {
      // Offline fallback
    }
  }
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/**
 * Tải ảnh táp-lô hoặc trụ sạc lên máy chủ để phân tích sơ bộ qua OCR/Vision (ADR-004)
 */
export async function uploadAttachment(file: File, imageKind: "auto" | "dashboard" | "exterior" = "auto"): Promise<ApiResponse<AttachmentOut>> {
  const authHeaders = await getCustomerAuthHeaders();
  const formData = new FormData();
  formData.append("file", file);
  formData.append("image_kind", imageKind);

  const res = await fetch(`${BASE_URL}/api/v1/customer/attachments`, {
    method: "POST",
    headers: {
      ...authHeaders,
    },
    body: formData,
  });

  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`Upload attachment error (${res.status}): ${errorText}`);
  }

  return res.json();
}

/**
 * Gửi tin nhắn chat từ khách hàng, hỗ trợ kèm mã định danh ảnh đã tải
 */
export async function sendChatMessage(params: {
  sessionId: string;
  message: string;
  caseId?: string | null;
  attachmentIds?: string[];
  clientContext?: ClientContext;
}): Promise<ApiResponse<ChatResponseData>> {
  const authHeaders = await getCustomerAuthHeaders();
  const res = await fetch(`${BASE_URL}/api/v1/customer/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders,
    },
    body: JSON.stringify({
      session_id: params.sessionId,
      case_id: params.caseId || null,
      message: params.message,
      attachment_ids: params.attachmentIds || [],
      client_context: params.clientContext || {
        mock_customer_id: "CUST_MOCK_01",
        vehicle_model: "VF8",
        vehicle_code_mock: "VF-SF-00231",
      },
    }),
  });

  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`Chat API error (${res.status}): ${errorText}`);
  }

  return res.json();
}

/**
 * Tra cứu trạng thái hồ sơ theo mã Case ID (api-contract.md Mục 2.2)
 */
export async function getCaseStatus(caseId: string) {
  const authHeaders = await getCustomerAuthHeaders();
  const res = await fetch(`${BASE_URL}/api/v1/customer/cases/${caseId}/status`, {
    headers: {
      ...authHeaders,
    },
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch case status: ${res.statusText}`);
  }
  return res.json();
}

/**
 * Lấy danh sách hồ sơ của khách hàng đang đăng nhập (api-contract.md Mục 2.3)
 */
export async function getCustomerCases(): Promise<ApiResponse<{ cases: CustomerCaseItem[]; total: number }>> {
  const authHeaders = await getCustomerAuthHeaders();
  const res = await fetch(`${BASE_URL}/api/v1/customer/cases`, {
    headers: {
      ...authHeaders,
    },
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch customer cases: ${res.statusText}`);
  }
  return res.json();
}

/**
 * Mở lại hồ sơ đã hoàn tất hoặc đóng (Reopen Case)
 */
export async function reopenCustomerCase(caseId: string): Promise<ApiResponse<{ success: boolean; case_id: string; status: string }>> {
  const authHeaders = await getCustomerAuthHeaders();
  const res = await fetch(`${BASE_URL}/api/v1/customer/cases/${caseId}/reopen`, {
    method: "POST",
    headers: {
      ...authHeaders,
    },
  });
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`Failed to reopen case: ${errorText}`);
  }
  return res.json();
}

/**
 * Khách hàng gửi đánh giá và nhận xét chất lượng xử lý
 */
export async function submitCustomerFeedback(
  caseId: string,
  payload: { rating: number; comment?: string }
): Promise<ApiResponse<{ success: boolean; feedback_id: string; case_id: string }>> {
  const authHeaders = await getCustomerAuthHeaders();
  const res = await fetch(`${BASE_URL}/api/v1/customer/cases/${caseId}/feedback`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders,
    },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`Failed to submit feedback: ${errorText}`);
  }
  return res.json();
}

/**
 * Lấy danh sách bài viết kiến thức & chính sách công khai (Public Knowledge Hub)
 */
export async function getPublicArticles(): Promise<ApiResponse<{ articles: ArticleItem[]; total: number }>> {
  const res = await fetch(`${BASE_URL}/api/v1/public/articles`);
  if (!res.ok) {
    throw new Error(`Failed to fetch public articles: ${res.statusText}`);
  }
  return res.json();
}

/**
 * Gửi tin nhắn trực tiếp đến AI RAG Chatbot Agent (/api/v1/chat từ nhánh develop)
 */
export async function sendDirectAiChat(message: string): Promise<{
  response: string;
  analysis?: string;
  intent?: string;
  priority?: string;
  needs_staff_review?: boolean;
  is_safety_trigger?: boolean;
  citations?: Array<{ source_id: string; title: string; url: string; section?: string }>;
}> {
  const res = await fetch(`${BASE_URL}/api/v1/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ message }),
  });
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`AI Chat error (${res.status}): ${errorText}`);
  }
  return res.json();
}

/**
 * Kiểm tra trạng thái sẵn sàng của AI Agent & Knowledge Base (/api/v1/status từ nhánh develop)
 */
export async function getAiSystemStatus(): Promise<{
  status: string;
  agent: string;
  knowledge_base: string;
  safety_guardrails: string;
}> {
  const res = await fetch(`${BASE_URL}/api/v1/status`);
  if (!res.ok) {
    throw new Error(`Failed to fetch AI status: ${res.statusText}`);
  }
  return res.json();
}


