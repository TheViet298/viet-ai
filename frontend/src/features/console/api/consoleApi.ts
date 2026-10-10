import { ApiResponse } from "@/types/chat";
import {
  StaffActionPayload,
  TicketDetail,
  TicketItem,
  TicketPriority,
  TicketStatus,
} from "../types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function getStaffAuthHeaders(): Promise<Record<string, string>> {
  if (typeof window === "undefined") return {};
  const token = localStorage.getItem("vf_access_token") || localStorage.getItem("vf_staff_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function getTicketQueue(params?: {
  status?: TicketStatus | string;
  priority?: TicketPriority | string;
}): Promise<ApiResponse<{ items: TicketItem[]; total: number }>> {
  const query = new URLSearchParams();
  if (params?.status && params.status !== "ALL") query.append("status", params.status);
  if (params?.priority && params.priority !== "ALL") query.append("priority", params.priority);

  const authHeaders = await getStaffAuthHeaders();
  const res = await fetch(`${BASE_URL}/api/v1/staff/tickets?${query.toString()}`, {
    headers: { ...authHeaders },
  });
  if (!res.ok) {
    throw new Error(`Staff API error (${res.status}): ${res.statusText}`);
  }
  return res.json();
}

export async function getTicketDetail(
  caseId: string
): Promise<ApiResponse<TicketDetail>> {
  const authHeaders = await getStaffAuthHeaders();
  const res = await fetch(`${BASE_URL}/api/v1/staff/tickets/${caseId}`, {
    headers: { ...authHeaders },
  });
  if (!res.ok) {
    throw new Error(`Staff API error (${res.status}): ${res.statusText}`);
  }
  return res.json();
}

export async function submitStaffAction(
  caseId: string,
  payload: StaffActionPayload
): Promise<ApiResponse<{ success: boolean; case_id: string }>> {
  const authHeaders = await getStaffAuthHeaders();
  const res = await fetch(`${BASE_URL}/api/v1/staff/tickets/${caseId}/actions`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders,
    },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    throw new Error(`Staff action failed: ${res.statusText}`);
  }
  return res.json();
}
