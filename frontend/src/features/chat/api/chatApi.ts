import { ApiResponse, ChatResponseData, ClientContext } from "../types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function sendChatMessage(params: {
  sessionId: string;
  message: string;
  caseId?: string | null;
  clientContext?: ClientContext;
}): Promise<ApiResponse<ChatResponseData>> {
  const res = await fetch(`${BASE_URL}/api/v1/customer/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      session_id: params.sessionId,
      case_id: params.caseId || null,
      message: params.message,
      client_context: params.clientContext || {
        mock_customer_id: "CUST_MOCK_DEMO",
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

export async function getCaseStatus(caseId: string) {
  const res = await fetch(`${BASE_URL}/api/v1/customer/cases/${caseId}/status`);
  if (!res.ok) {
    throw new Error(`Failed to fetch case status: ${res.statusText}`);
  }
  return res.json();
}
