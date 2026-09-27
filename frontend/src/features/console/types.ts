export type TicketStatus =
  | "New"
  | "Needs Information"
  | "Staff Reviewing"
  | "In Progress"
  | "Resolved"
  | "Closed"
  | "Reopened";

export type TicketPriority = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export type TicketIntent =
  | "Charging/Battery"
  | "Service/Incident"
  | "Sales"
  | "Complaint";

export interface CaseBrief {
  summary: string;
  captured_fields: Record<string, any>;
  suggested_action: string;
  confidence_score: number;
  is_edited_by_staff?: boolean;
}

export interface TicketItem {
  id: string;
  mock_customer_id: string;
  vehicle_model: string;
  vehicle_code_mock?: string;
  intent: TicketIntent;
  priority: TicketPriority;
  status: TicketStatus;
  missing_info_flag: boolean;
  created_at: string;
  confidence_score: number;
}

export interface TicketDetail {
  case: {
    id: string;
    mock_customer_id: string;
    vehicle_code_mock?: string;
    vehicle_model: string;
    intent: TicketIntent;
    priority: TicketPriority;
    status: TicketStatus;
  };
  case_brief: CaseBrief;
  conversation_history: Array<{
    sender: "CUSTOMER" | "AGENT" | "STAFF" | "SYSTEM";
    content: string;
    created_at: string;
  }>;
}

export type StaffActionType =
  | "APPROVE"
  | "EDIT_BRIEF"
  | "REROUTE"
  | "CLOSE"
  | "REOPEN"
  | "REQUEST_INFO";

export interface StaffActionPayload {
  action: StaffActionType;
  staff_id: string;
  updated_status?: TicketStatus;
  edited_brief?: Partial<CaseBrief> | null;
  notes?: string;
}
