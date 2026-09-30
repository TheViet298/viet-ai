export type VehicleModel = "VF3" | "VF5" | "VF6" | "VF7" | "VF8" | "VF9" | "e34";

export interface ClientContext {
  mock_customer_id?: string;
  vehicle_model?: VehicleModel | string;
  vehicle_code_mock?: string;
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
  response_type: ChatResponseType;
  message: string;
  case_id?: string | null;
  clarification_turn?: number;
  max_clarification_turns?: number;
  suggested_replies?: string[];
  citations?: Citation[];
  safe_guidance?: string;
  priority?: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  status?: string;
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
  detected_signals?: Record<string, any> | null;
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
  content: string;
  source_url: string;
  verified_at: string;
}
