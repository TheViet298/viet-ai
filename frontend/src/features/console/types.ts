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
  | "Sales/General Info"
  | "Complaint"
  | "Complaint/Feedback";

export interface CaseBrief {
  summary: string;
  captured_fields: Record<string, unknown>;
  suggested_action: string;
  confidence_score: number;
  is_edited_by_staff?: boolean;
}

export interface TicketItem {
  id: string;
  mock_customer_id: string;
  customer_name?: string;
  customer_phone?: string;
  vehicle_model: string;
  vehicle_code_mock?: string;
  intent: TicketIntent;
  priority: TicketPriority;
  status: TicketStatus;
  missing_info_flag: boolean;
  created_at: string;
  confidence_score: number;
  issue_summary?: string;
  suggested_action?: string;
  has_location_consent?: boolean;
  error_code_short?: string;
  safety_status?: string;
  safety_acknowledged_at?: string | null;
  customer_feedback_score?: number | null;
  customer_feedback_comment?: string | null;
  customer_feedback_tags?: string[];
  is_auto_closed?: boolean;
}

export interface TicketDetail {
  case: {
    id: string;
    mock_customer_id: string;
    customer_name?: string;
    customer_phone?: string;
    vehicle_code_mock?: string;
    vehicle_model: string;
    intent: TicketIntent;
    priority: TicketPriority;
    status: TicketStatus;
    safety_status?: string;
    safety_acknowledged_at?: string | null;
    safety_guidance?: string;
  };
  case_brief: CaseBrief;
  conversation_history: Array<{
    sender: "CUSTOMER" | "AGENT" | "STAFF" | "SYSTEM";
    content: string;
    created_at: string;
  }>;
  location?: {
    location_label?: string | null;
    share_with_staff?: boolean;
    status?: string;
    source?: string;
    latitude?: number | null;
    longitude?: number | null;
  } | null;
}

export type StaffActionType =
  | "APPROVE"
  | "EDIT_BRIEF"
  | "REROUTE"
  | "CLOSE"
  | "REOPEN"
  | "RESOLVE"
  | "REQUEST_INFO";

export interface StaffActionPayload {
  action: StaffActionType;
  staff_id: string;
  updated_status?: TicketStatus;
  edited_brief?: Partial<CaseBrief> | null;
  notes?: string;
}

export const VIETNAMESE_STATUS_MAP: Record<string, string> = {
  "New": "Mới tiếp nhận",
  "Staff Reviewing": "Chờ duyệt",
  "Needs Information": "Cần thêm tin",
  "In Progress": "Đang xử lý",
  "Resolved": "Đã xử lý",
  "Closed": "Đã đóng",
  "Reopened": "Mở lại",
};

export const VIETNAMESE_PRIORITY_MAP: Record<string, string> = {
  "CRITICAL": "Khẩn cấp",
  "HIGH": "Ưu tiên cao",
  "MEDIUM": "Tiêu chuẩn",
  "LOW": "Thấp",
};
