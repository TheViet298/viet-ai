import {
  ApiResponse,
  ArticleItem,
  AttachmentOut,
  ChatResponseData,
  CaseLocationOut,
  CaseLocationPayload,
  Citation,
  ClientContext,
  CustomerCaseDetailData,
  CustomerCaseItem,
  VehicleCard,
} from "../types";

const BASE_URL = (process.env.NEXT_PUBLIC_API_URL || "").replace(/\/$/, "");

export async function getCustomerAuthHeaders(): Promise<Record<string, string>> {
  if (typeof window === "undefined") return {};
  const token = localStorage.getItem("vf_access_token") || localStorage.getItem("vf_customer_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

const locationUpdateQueue = new Map<string, Promise<unknown>>();

export function submitCustomerLocation(payload: CaseLocationPayload): Promise<ApiResponse<CaseLocationOut>> {
  const previous = locationUpdateQueue.get(payload.case_id) ?? Promise.resolve();
  const request = previous.catch(() => undefined).then(async () => {
    const authHeaders = await getCustomerAuthHeaders();
    if (!authHeaders.Authorization) throw new Error("Vui lòng đăng nhập để chia sẻ vị trí với hồ sơ.");

    // A later "Bỏ qua" request must clear coordinates after an earlier GPS request.
    const body = payload.status === "NOT_SHARED"
      ? { ...payload, location_label: payload.location_label.trim() || "Không chia sẻ", latitude: null, longitude: null, share_with_staff: false }
      : payload;
    const res = await fetch(`${BASE_URL}/api/v1/customer/location`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      throw new Error(`Không thể cập nhật vị trí hồ sơ (${res.status}).`);
    }
    return res.json() as Promise<ApiResponse<CaseLocationOut>>;
  });
  locationUpdateQueue.set(payload.case_id, request);
  void request.finally(() => {
    if (locationUpdateQueue.get(payload.case_id) === request) locationUpdateQueue.delete(payload.case_id);
  }).catch(() => undefined);
  return request;
}

/**
 * Tải ảnh táp-lô hoặc trụ sạc lên máy chủ để phân tích sơ bộ qua OCR/Vision (ADR-004)
 */
export async function uploadAttachment(file: File, imageKind: "auto" | "dashboard" | "exterior" = "auto"): Promise<ApiResponse<AttachmentOut>> {
  const authHeaders = await getCustomerAuthHeaders();
  if (!authHeaders.Authorization) throw new Error("Vui lòng đăng nhập để tải ảnh.");
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
  requestId?: string;
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
    // Backend turn budget is 20 seconds; leave room for transport and persistence.
    signal: typeof AbortSignal !== "undefined" && typeof AbortSignal.timeout === "function" ? AbortSignal.timeout(30000) : undefined,
    body: JSON.stringify({
      request_id: params.requestId,
      session_id: params.sessionId,
      ...(!authHeaders.Authorization ? { guest_session_id: params.sessionId } : {}),
      case_id: params.caseId || null,
      message: params.message,
      attachment_ids: params.attachmentIds || [],
      client_context: params.clientContext || {},
      guest_session_id: params.sessionId,
    }),
  });

  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`Chat API error (${res.status}): ${errorText}`);
  }

  return res.json();
}

/**
 * Lấy lịch sử hội thoại của phiên chat (multi-topic chat remediation)
 */
export async function getSessionHistory(sessionId: string): Promise<ApiResponse<{
  session_id: string;
  case_id: string | null;
  messages: Array<{
    id: string;
    sender: "CUSTOMER" | "AGENT" | "STAFF" | "SYSTEM";
    content: string;
    timestamp: string;
    response_type?: "CLARIFICATION" | "FAQ_ANSWER" | "CASE_CREATED";
    citations?: Citation[];
    vehicle_cards?: VehicleCard[];
    vehicle_comparison?: boolean;
    suggested_replies?: string[];
    safe_guidance?: string;
    case_id?: string | null;
    priority?: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  }>;
  total: number;
}>> {
  const authHeaders = await getCustomerAuthHeaders();
  const res = await fetch(`${BASE_URL}/api/v1/customer/sessions/${sessionId}/history`, {
    headers: {
      ...authHeaders,
    },
  });
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`Failed to fetch session history (${res.status}): ${errorText}`);
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
 * Lấy chi tiết hồ sơ sự cố bao gồm brief, vị trí, timeline, và lịch sử trao đổi (api-contract.md Mục 2.3)
 */
export async function getCaseDetail(caseId: string): Promise<ApiResponse<CustomerCaseDetailData>> {
  const authHeaders = await getCustomerAuthHeaders();
  const res = await fetch(`${BASE_URL}/api/v1/customer/cases/${caseId}`, {
    headers: {
      ...authHeaders,
    },
  });
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`Failed to fetch case detail (${res.status}): ${errorText}`);
  }
  return res.json();
}

export async function acknowledgeCaseSafety(caseId: string, incidentVersion: number) {
  const authHeaders = await getCustomerAuthHeaders();
  const res = await fetch(`${BASE_URL}/api/v1/customer/cases/${caseId}/safety-acknowledgement`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders },
    body: JSON.stringify({ incident_version: incidentVersion }),
  });
  if (!res.ok) throw new Error(`Safety acknowledgement failed (${res.status})`);
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
 * Khách hàng xác nhận kết quả xử lý (RESOLVED_CONFIRMED hoặc STILL_UNRESOLVED)
 */
export async function confirmCustomerCaseResolution(
  caseId: string,
  payload: { confirmation: "RESOLVED_CONFIRMED" | "STILL_UNRESOLVED"; feedback_note?: string }
): Promise<ApiResponse<{ success: boolean; case_id: string; status: string; message: string }>> {
  const authHeaders = await getCustomerAuthHeaders();
  const res = await fetch(`${BASE_URL}/api/v1/customer/cases/${caseId}/confirmation`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders,
    },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`Failed to confirm resolution: ${errorText}`);
  }
  return res.json();
}

/**
 * Khách hàng gửi đánh giá và nhận xét chất lượng xử lý
 */
export async function submitCustomerFeedback(
  caseId: string,
  payload: { rating: number; comment?: string; reason_tags?: string[] }
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

/**
 * Khách hàng xác nhận kết quả ca đã xử lý hoặc yêu cầu hỗ trợ tiếp (ADR-005)
 */
export async function confirmCustomerCase(
  caseId: string,
  payload: {
    confirmation: "RESOLVED_CONFIRMED" | "STILL_UNRESOLVED";
    feedback_note?: string;
  }
): Promise<ApiResponse<{ success: boolean; case_id: string; status: string }>> {
  const authHeaders = await getCustomerAuthHeaders();
  const res = await fetch(`${BASE_URL}/api/v1/customer/cases/${caseId}/confirmation`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders,
    },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`Failed to confirm case: ${errorText}`);
  }
  return res.json();
}

/**
 * Khách hàng xác nhận đã an toàn (ADR-005)
 */
export async function submitSafetyAcknowledgement(
  caseId: string,
  payload: { incident_version: number }
): Promise<ApiResponse<{ success: boolean; case_id: string; safety_status: string }>> {
  const authHeaders = await getCustomerAuthHeaders();
  const res = await fetch(`${BASE_URL}/api/v1/customer/cases/${caseId}/safety-acknowledgement`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders,
    },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`Failed to acknowledge safety: ${errorText}`);
  }
  return res.json();
}


export async function getNearbyServicePoints(coord: { lat: number; lng: number }, category: string, signal?: AbortSignal, options?: { vehicleType?: "CAR" | "TWO_WHEELER"; radiusKm?: number }) {
  const query = new URLSearchParams({ lat: String(coord.lat), lng: String(coord.lng), category, radius_km: String(options?.radiusKm ?? 50), limit: "5", vehicle_type: options?.vehicleType ?? "CAR" });
  const res = await fetch(`${BASE_URL}/api/v1/customer/service-points/nearby?${query}`, { signal });
  if (!res.ok) throw new Error(`Không thể tải điểm dịch vụ (${res.status}).`);
  const body = await res.json();
  return (body.data.points as Array<{ id: string; name: string; category: string; address: string; latitude: number; longitude: number; distance_km?: number; hotline: string; demo?: boolean; source?: string; updated_at?: string; verification_status?: "UNVERIFIED" | "VERIFIED" }>).map((point) => ({
    id: point.id, name: point.name, type: point.category as import("../types").ServicePointSeed["type"], address: point.address, hotline: point.hotline ?? "", distanceKm: point.distance_km, coords: { lat: point.latitude, lng: point.longitude },
    demo: point.demo !== false, source: point.source, updatedAt: point.updated_at ?? null,
    verificationStatus: point.verification_status === "VERIFIED" && point.demo === false ? "VERIFIED" as const : "UNVERIFIED" as const,
  }));
}
