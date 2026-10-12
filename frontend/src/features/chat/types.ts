export type VehicleModel = "VF3" | "VF5" | "VF6" | "VF7" | "VF8" | "VF9" | "e34";

export interface ClientContext {
  mock_customer_id?: string;
  vehicle_model?: VehicleModel | string;
  vehicle_code_mock?: string;
  customer_name?: string;
}

export interface Citation {
  source_id: string;
  title: string;
  url: string;
  verified_at?: string;
  status_code?: number;
  applicable_models?: string[];
  source_type?: string;
  relevant_snippet?: string;
}

export type ChatResponseType = "CLARIFICATION" | "FAQ_ANSWER" | "CASE_CREATED";

export interface ChatResponseData {
  emergency_context?: { case_id: string; incident_version: number; safety_status: string } | null;
  safety_status?: "unconfirmed" | "customer_reported_safe";
  safety_acknowledged_at?: string | null;
  incident_version?: number | null;
  response_type: ChatResponseType;
  message: string;
  response?: string;
  intent?: string;
  case_id?: string | null;
  clarification_turn?: number;
  max_clarification_turns?: number;
  suggested_replies?: string[];
  citations?: Citation[];
  safe_guidance?: string;
  priority?: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  status?: string;
  show_emergency_banner?: boolean;
  request_location?: boolean;
}

export interface ApiResponse<T> {
  success: boolean;
  data: T;
  error: string | null;
  meta?: {
    timestamp: string;
  };
}

export interface ChatMessage {
  id: string;
  sender: "CUSTOMER" | "AGENT" | "SYSTEM";
  content: string;
  timestamp: string;
  response_type?: ChatResponseType;
  citations?: Citation[];
  suggested_replies?: string[];
  safe_guidance?: string;
  case_id?: string | null;
  priority?: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  attachment_ids?: string[];
  image?: { src: string; name: string };
}

export interface QuickPrompt {
  label: string;
  model: VehicleModel;
  text: string;
}

export interface AttachmentOut {
  attachment_id: string;
  storage_key: string;
  mime_type: string;
  analysis_status: string;
  ocr_text?: string | null;
  detected_signals?: { image_kind?: string; analysis_error?: string; [key: string]: unknown } | null;
  vision_confidence?: number | null;
  created_at: string;
}

export interface CustomerCaseItem {
  id: string;
  vehicle_model: string;
  vehicle_code_mock?: string;
  intent: string;
  priority: string;
  status: string;
  summary?: string | null;
  created_at: string;
  updated_at?: string | null;
}

export interface ArticleItem {
  id: string;
  title: string;
  category: string;
  summary: string;
  content?: string;
  source_url: string;
  url?: string;
  verified_at: string;
  applicable_models?: string[];
}

export interface ServicePointSeed {
  id: string;
  name: string;
  type: "SERVICE_WORKSHOP" | "CHARGING_STATION" | "SHOWROOM" | "OTHER";
  address: string;
  distance?: string;
  demo?: boolean;
  hotline: string;
  coords: { lat: number; lng: number };
}

export interface UserLocationState {
  status: "CONSENTED" | "MANUAL" | "NOT_SHARED" | "PENDING";
  source: "BROWSER_GPS" | "USER_TEXT" | "MAP_PICKER";
  label: string;
  coords?: { lat: number; lng: number };
  accuracy?: number;
  isTracking?: boolean;
  errorCode?: "PERMISSION_DENIED" | "POSITION_UNAVAILABLE" | "TIMEOUT" | "ACCURACY_LOW" | "UNSUPPORTED";
  errorMessage?: string;
}

export interface CaseLocationPayload {
  case_id: string;
  status: "CONSENTED" | "MANUAL" | "NOT_SHARED";
  source: "BROWSER_GPS" | "USER_TEXT" | "MAP_PICKER";
  location_label: string;
  latitude?: number | null;
  longitude?: number | null;
  precision?: "APPROXIMATE" | "EXACT";
  share_with_staff: boolean;
}

export interface CaseLocationOut extends CaseLocationPayload {
  precision: "APPROXIMATE" | "EXACT";
  latitude: number | null;
  longitude: number | null;
  created_at: string;
}

export interface CustomerCaseDetailData {
  case: CustomerCaseItem & {
    safety_status?: string;
    safety_guidance?: string;
    incident_version?: number;
  };
  case_brief?: {
    summary?: string;
    captured_fields?: Record<string, unknown>;
    suggested_action?: string;
    confidence_score?: number;
    is_edited_by_staff?: boolean;
  } | null;
  location?: {
    case_id: string;
    status: string;
    source: string;
    location_label?: string | null;
    latitude?: number | null;
    longitude?: number | null;
    precision?: string | null;
    share_with_staff?: boolean;
    created_at?: string;
  } | null;
  updates?: Array<{
    id: string;
    case_id: string;
    author_type: string;
    status_after_update: string;
    customer_message?: string;
    next_step?: string;
    awaiting_customer_confirmation?: boolean;
    created_at: string;
  }>;
  attachments?: AttachmentOut[];
  conversation_history?: Array<{
    sender: "CUSTOMER" | "AGENT" | "STAFF" | "SYSTEM";
    content: string;
    created_at: string;
  }>;
}

