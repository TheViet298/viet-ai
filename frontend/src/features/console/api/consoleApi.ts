import { ApiResponse } from "@/types/chat";
import {
  StaffActionPayload,
  TicketDetail,
  TicketItem,
  TicketPriority,
  TicketStatus,
} from "../types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function getTicketQueue(params?: {
  status?: TicketStatus | string;
  priority?: TicketPriority | string;
}): Promise<ApiResponse<{ items: TicketItem[]; total: number }>> {
  const query = new URLSearchParams();
  if (params?.status && params.status !== "ALL") query.append("status", params.status);
  if (params?.priority && params.priority !== "ALL") query.append("priority", params.priority);

  const res = await fetch(`${BASE_URL}/api/v1/staff/tickets?${query.toString()}`);
  if (!res.ok) {
    throw new Error(`Staff API error (${res.status}): ${res.statusText}`);
  }
  return res.json();
}

export async function getTicketDetail(
  caseId: string
): Promise<ApiResponse<TicketDetail>> {
  const res = await fetch(`${BASE_URL}/api/v1/staff/tickets/${caseId}`);
  if (!res.ok) {
    throw new Error(`Staff API error (${res.status}): ${res.statusText}`);
  }
  return res.json();
}

export async function submitStaffAction(
  caseId: string,
  payload: StaffActionPayload
): Promise<ApiResponse<{ success: boolean; case_id: string }>> {
  const res = await fetch(`${BASE_URL}/api/v1/staff/tickets/${caseId}/actions`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    throw new Error(`Staff action failed: ${res.statusText}`);
  }
  return res.json();
}
