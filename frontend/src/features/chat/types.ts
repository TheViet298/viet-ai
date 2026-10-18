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

export interface NearbyAction {
  type: "FIND_NEARBY";
  request_id: string;
  turn_id: string;
  category: "ALL" | ServicePointSeed["type"];
  vehicle_type: "CAR" | "TWO_WHEELER";
  area_text?: string | null;
  requires_location: boolean;
  reason: string;
  limit: 5;
}

export interface VehicleCard {
  battery_capacity?: string | null;
  fast_charge_time?: string | null;
  variant?: string | null;
  specs_source_url?: string | null;
  test_drive_url?: string | null;
  rolling_cost_url?: string | null;
  model: string;
  name: string;
  image_url: string;
  specs: { label: string; value: string }[];
  price_label: string;
  source_url: string;
  verified_at: string;
}

export interface ChatResponseData {
  language?: "vi" | "en";
  nearby_action?: NearbyAction | null;
  vehicle_comparison?: boolean;
  vehicle_cards?: VehicleCard[];
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
  language?: "vi" | "en";
  vehicle_comparison?: boolean;
  vehicle_cards?: VehicleCard[];
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

export interface ChatSessionItem {
  session_id: string;
  title: string;
  last_message?: string | null;
  created_at: string;
  updated_at: string;
  message_count: number;
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
  source?: string;
  updatedAt?: string | null;
  verificationStatus?: "UNVERIFIED" | "SNAPSHOT" | "VERIFIED";
  hotline: string;
  distanceKm?: number;
  coords: { lat: number; lng: number };
}

export interface ServicePointApiItem {
  id: string;
  name: string;
  category: "workshop" | "charging_station" | "showroom" | string;
  category_slug?: string | null;
  address: string;
  province?: string | null;
  phone?: string | null;
  hotline_service?: string | null;
  hours?: string | null;
  operating_hours?: string | null;
  is_car_compatible?: boolean;
  services_offered?: string[];
  dong_son?: boolean;
  booking_url?: string | null;
  distance_km?: number | null;
  distance_from_area_km?: number | null;
  note?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  is_out_of_area?: boolean;
}

export interface ServicePointsApiResponse {
  case_id: string;
  intent?: string;
  recommended_points: ServicePointApiItem[];
  needs_location: boolean;
  no_points_nearby?: boolean;
  is_out_of_area?: boolean;
  message?: string | null;
  last_updated_label?: string | null;
  rescue_hotline?: string | null;
  area_reference?: {
    label: string;
    level: "district" | "province";
  } | null;
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
