"use client";

import { useState, useEffect } from "react";
import {
  ShieldCheck,
  Sparkles,
  Edit3,
  Check,
  X,
  Clock,
  Send,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Car,
  MapPin,
  Bot,
  User,
  Loader2,
  GitBranch,
  ShieldAlert,
  ChevronRight,
  Flame,
  FileText,
  MessageSquare,
} from "lucide-react";
import { TicketItem, TicketStatus, StaffActionType, TicketDetail } from "../types";
import { ROUTING_DEPARTMENTS } from "./StaffConsoleShell";
import { getTicketDetail, submitStaffAction } from "../api/consoleApi";

interface TicketDetailPanelProps {
  ticket: TicketItem;
  onActionComplete?: (message: string) => void;
  onStatusUpdate?: (ticketId: string, newStatus: TicketStatus) => void;
}

// Mock dataset chi tiết tương ứng với 5 Ticket ID
const DETAILED_TICKETS_MAP: Record<string, TicketDetail> = {
  "CASE-20260924-001": {
    case: {
      id: "CASE-20260924-001",
      mock_customer_id: "CUST_MOCK_01",
      vehicle_code_mock: "VF-SF-00231",
      vehicle_model: "VF8",
      intent: "Charging/Battery",
      priority: "HIGH",
      status: "Staff Reviewing",
    },
    case_brief: {
      summary:
        "Xe VF8 không nhận sạc DC tại trạm Vincom Metropolis. Màn hình xe báo mã lỗi CC01 và đèn trụ P02 nháy đỏ. Khách hàng đã cắm thử lại 2 lần không được.",
      captured_fields: {
        vehicle_model: "VinFast VF8 Plus",
        station_location: "Vincom Metropolis Liễu Giai, Ba Đình, HN",
        charger_id: "VN-CS-HN042-P02 (DC 250kW)",
        error_code: "CC01 (Handshake BMS Timeout)",
        current_soc: "18% SoC",
        location_consent: "Đã cấp quyền (Tọa độ: 21.0315° N, 105.8155° E)",
      },
      suggested_action:
        "Kiểm tra tín hiệu handshake giao tiếp trụ P02 từ xa hoặc cử nhân viên trạm khởi động lại module giao thức trụ sạc.",
      confidence_score: 0.92,
      is_edited_by_staff: false,
    },
    conversation_history: [
      {
        sender: "CUSTOMER",
        content: "Xe VF8 của tôi không nhận sạc ở trạm Metropolis, trụ báo đèn đỏ.",
        created_at: "2026-09-24T08:30:10Z",
      },
      {
        sender: "AGENT",
        content:
          "Dạ em ghi nhận xe VF8 đang không nhận sạc tại trạm Metropolis. Màn hình xe có hiển thị mã lỗi (ví dụ: CC01, BMS_012) hoặc anh/chị có mã trụ sạc không ạ?",
        created_at: "2026-09-24T08:30:15Z",
      },
      {
        sender: "CUSTOMER",
        content: "Mã lỗi trên màn hình là CC01, tôi cắm trụ P02, pin còn 18%.",
        created_at: "2026-09-24T08:30:45Z",
      },
      {
        sender: "AGENT",
        content:
          "Hệ thống đã ghi nhận đầy đủ dữ kiện kỹ thuật và tạo hồ sơ hỗ trợ CASE-20260924-001. Hồ sơ đã chuyển đến chuyên viên dịch vụ để xử lý.",
        created_at: "2026-09-24T08:30:50Z",
      },
    ],
  },
  "CASE-20260924-002": {
    case: {
      id: "CASE-20260924-002",
      mock_customer_id: "CUST_MOCK_99",
      vehicle_code_mock: "VF-SF-99120",
      vehicle_model: "VF8",
      intent: "Service/Incident",
      priority: "CRITICAL",
      status: "Staff Reviewing",
    },
    case_brief: {
      summary:
        "Xe VF8 gặp cảnh báo Rùa Vàng và mất trợ lực lái nhẹ trên cao tốc Long Thành - Dầu Giây. Xe hiện đang tấp vào làn khẩn cấp, tài xế bật đèn hazard.",
      captured_fields: {
        vehicle_model: "VinFast VF8 Eco",
        station_location: "Km 24+500 Cao Tốc Long Thành - Dầu Giây",
        error_code: "TURTLE_WARN + EPS_LIMIT_04",
        current_soc: "34% SoC",
        location_consent: "Đã cấp quyền định vị khẩn cấp GPS",
        safe_status: "Đang dừng an toàn làn khẩn cấp",
      },
      suggested_action:
        "Kích hoạt quy trình Cứu hộ Khẩn cấp 24/7. Hướng dẫn tài xế đứng sau rào hộ lan an toàn và cử xe cứu hộ gần nhất.",
      confidence_score: 0.98,
      is_edited_by_staff: false,
    },
    conversation_history: [
      {
        sender: "CUSTOMER",
        content: "Cứu tôi với, xe tôi đang chạy trên cao tốc Long Thành thì hiện rùa vàng, tay lái thấy nặng hơn!",
        created_at: "2026-09-24T08:35:05Z",
      },
      {
        sender: "AGENT",
        content:
          "Anh/chị hãy bình tĩnh, bật ngay đèn cảnh báo khẩn cấp (hazard) và tấp xe vào làn khẩn cấp bên phải. Anh/chị và người trên xe đã ra sau hộ lan an toàn chưa ạ?",
        created_at: "2026-09-24T08:35:12Z",
      },
      {
        sender: "CUSTOMER",
        content: "Tôi vừa tấp vào lề rồi, mọi người đã xuống xe đứng sau rào chắn. Km 24 cao tốc.",
        created_at: "2026-09-24T08:35:35Z",
      },
      {
        sender: "AGENT",
        content:
          "Hồ sơ khẩn cấp CRITICAL CASE-20260924-002 đã được tạo lập và chuyển trực tiếp tới Đội Phản Ứng Nhanh Cứu Hộ VinFast 24/7.",
        created_at: "2026-09-24T08:35:42Z",
      },
    ],
  },
  "CASE-20260924-003": {
    case: {
      id: "CASE-20260924-003",
      mock_customer_id: "CUST_MOCK_02",
      vehicle_code_mock: "VF-SF-00445",
      vehicle_model: "VF5",
      intent: "Service/Incident",
      priority: "MEDIUM",
      status: "Needs Information",
    },
    case_brief: {
      summary:
        "Xe VF5 hiện biểu tượng rùa vàng trên cụm đồng hồ táp-lô khi đang di chuyển trong đô thị. Cần xác minh dung lượng pin SoC và chụp ảnh đèn cảnh báo.",
      captured_fields: {
        vehicle_model: "VinFast VF5 Plus",
        station_location: "Đường Nguyễn Trãi, Thanh Xuân, HN",
        error_code: "Chưa rõ mã DTC cụ thể",
        current_soc: "Ước tính < 10%",
        location_consent: "Chưa bật chia sẻ vị trí",
      },
      suggested_action:
        "Gửi tin nhắn yêu cầu khách chụp ảnh táp-lô và kiểm tra dung lượng pin còn lại trên ứng dụng VinFast.",
      confidence_score: 0.65,
      is_edited_by_staff: false,
    },
    conversation_history: [
      {
        sender: "CUSTOMER",
        content: "Màn hình xe VF5 của tôi tự nhiên hiện con rùa màu vàng là sao vậy em?",
        created_at: "2026-09-24T08:40:02Z",
      },
      {
        sender: "AGENT",
        content:
          "Dạ biểu tượng rùa vàng là chế độ giới hạn công suất để bảo vệ xe (thường do pin dưới 10% hoặc nhiệt độ pin). Hiện pin xe anh/chị còn bao nhiêu % ạ?",
        created_at: "2026-09-24T08:40:15Z",
      },
      {
        sender: "CUSTOMER",
        content: "Để tôi xem lại đã, hình như vạch đỏ sắp hết.",
        created_at: "2026-09-24T08:40:40Z",
      },
    ],
  },
  "CASE-20260924-004": {
    case: {
      id: "CASE-20260924-004",
      mock_customer_id: "CUST_MOCK_15",
      vehicle_code_mock: "VF-SF-00789",
      vehicle_model: "VF9",
      intent: "Charging/Battery",
      priority: "LOW",
      status: "In Progress",
    },
    case_brief: {
      summary:
        "Khách phản ánh sạc xe VF9 tại nhà bằng bộ sạc AC treo tường 7.4kW tự động ngắt sau khoảng 2 tiếng sạc.",
      captured_fields: {
        vehicle_model: "VinFast VF9 Plus",
        station_location: "Biệt thự Vinhomes Riverside, Long Biên, HN",
        charger_id: "Bộ sạc Wallbox VinFast 7.4kW",
        error_code: "AC_THERMAL_CUTOFF",
        current_soc: "62% SoC",
        location_consent: "Đã xác nhận địa chỉ nhà",
      },
      suggested_action:
        "Tư vấn kiểm tra aptomat nguồn và thông gió phòng kỹ thuật; hẹn kỹ thuật viên lưu động kiểm tra nhiệt độ dây nguồn.",
      confidence_score: 0.88,
      is_edited_by_staff: false,
    },
    conversation_history: [
      {
        sender: "CUSTOMER",
        content: "Bộ sạc tại nhà 7.4kW của tôi sạc xe VF9 được 2 tiếng thì tự ngắt, sờ vào dây thấy khá ấm.",
        created_at: "2026-09-24T07:15:10Z",
      },
      {
        sender: "AGENT",
        content:
          "Dạ hiện tượng dây sạc ấm và tự ngắt có thể do cơ chế ngắt nhiệt an toàn (Thermal Cutoff) khi nguồn điện gia đình bị quá tải. Kỹ thuật viên sẽ hỗ trợ kiểm tra thông số.",
        created_at: "2026-09-24T07:15:25Z",
      },
    ],
  },
  "CASE-20260924-005": {
    case: {
      id: "CASE-20260924-005",
      mock_customer_id: "CUST_MOCK_23",
      vehicle_code_mock: "VF-SF-00612",
      vehicle_model: "VF6",
      intent: "Service/Incident",
      priority: "HIGH",
      status: "Resolved",
    },
    case_brief: {
      summary:
        "Cảnh báo áp suất lốp (TPMS) bánh sau bên phụ giảm dưới 2.0 bar sau khi xe đi qua đoạn đường gồ ghề.",
      captured_fields: {
        vehicle_model: "VinFast VF6 Plus",
        station_location: "Khu vực Cầu Giấy, Hà Nội",
        error_code: "TPMS_LOW_PRESSURE_RR",
        current_soc: "78% SoC",
        location_consent: "Đã xác nhận vị trí xưởng VinFast",
      },
      suggested_action:
        "Khách đã ghé xưởng VinFast Trần Duy Hưng bơm lốp lên 2.4 bar tiêu chuẩn và cân bằng động. Đã đóng ca.",
      confidence_score: 0.94,
      is_edited_by_staff: true,
    },
    conversation_history: [
      {
        sender: "CUSTOMER",
        content: "Lốp xe VF6 của tôi báo tụt áp suất còn 1.8 bar, có cần vào xưởng ngay không?",
        created_at: "2026-09-24T06:45:10Z",
      },
      {
        sender: "AGENT",
        content:
          "Dạ áp suất tiêu chuẩn cho VF6 là 2.3 - 2.4 bar. Áp suất 1.8 bar có nguy cơ hỏng lốp, em đã định vị xưởng VinFast Trần Duy Hưng cách anh/chị 1.2km để hỗ trợ ngay.",
        created_at: "2026-09-24T06:45:20Z",
      },
    ],
  },
};

export function TicketDetailPanel({
  ticket,
  onActionComplete,
  onStatusUpdate,
}: TicketDetailPanelProps) {
  // Detail Sub-tabs: 3 tabs
  const [detailTab, setDetailTab] = useState<"brief" | "chat" | "dispatch">("brief");

  // Local state for editing Case Brief
  const [isEditingBrief, setIsEditingBrief] = useState(false);
  const [editedSummary, setEditedSummary] = useState("");
  const [notes, setNotes] = useState("");
  const [selectedDept, setSelectedDept] = useState("Charging Operations");
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Active detail data
  const [ticketDetail, setTicketDetail] = useState<TicketDetail>(() => {
    return (
      DETAILED_TICKETS_MAP[ticket.id] || {
        case: {
          id: ticket.id,
          mock_customer_id: ticket.mock_customer_id,
          vehicle_code_mock: ticket.vehicle_code_mock,
          vehicle_model: ticket.vehicle_model,
          intent: ticket.intent,
          priority: ticket.priority,
          status: ticket.status,
        },
        case_brief: {
          summary: `Hồ sơ sự cố tiếp nhận cho xe ${ticket.vehicle_model}. Yêu cầu kiểm tra kỹ thuật và điều phối xưởng dịch vụ.`,
          captured_fields: {
            vehicle_model: ticket.vehicle_model,
            station_location: "Đang cập nhật",
            error_code: "Chưa ghi nhận mã lỗi",
            current_soc: "Đang xác minh",
          },
          suggested_action: "Kiểm tra triệu chứng thực tế và liên hệ chủ xe.",
          confidence_score: ticket.confidence_score || 0.85,
        },
        conversation_history: [
          {
            sender: "CUSTOMER",
            content: `Yêu cầu hỗ trợ kỹ thuật cho xe ${ticket.vehicle_model}.`,
            created_at: ticket.created_at,
          },
          {
            sender: "AGENT",
            content: `Hệ thống tiếp nhận hồ sơ ${ticket.id} và chuyển tới Cố vấn Dịch vụ.`,
            created_at: ticket.created_at,
          },
        ],
      }
    );
  });

  // When ticket prop changes, sync detail
  useEffect(() => {
    const existing = DETAILED_TICKETS_MAP[ticket.id];
    if (existing) {
      setTicketDetail(existing);
      setEditedSummary(existing.case_brief.summary);
    } else {
      setTicketDetail({
        case: {
          id: ticket.id,
          mock_customer_id: ticket.mock_customer_id,
          vehicle_code_mock: ticket.vehicle_code_mock,
          vehicle_model: ticket.vehicle_model,
          intent: ticket.intent,
          priority: ticket.priority,
          status: ticket.status,
        },
        case_brief: {
          summary: `Hồ sơ sự cố tiếp nhận cho xe ${ticket.vehicle_model}. Yêu cầu kiểm tra kỹ thuật và điều phối xưởng.`,
          captured_fields: {
            vehicle_model: ticket.vehicle_model,
            station_location: "Đang cập nhật",
            error_code: "Chưa ghi nhận mã lỗi",
            current_soc: "Đang xác minh",
          },
          suggested_action: "Kiểm tra triệu chứng thực tế và liên hệ chủ xe.",
          confidence_score: ticket.confidence_score || 0.85,
        },
        conversation_history: [
          {
            sender: "CUSTOMER",
            content: `Yêu cầu hỗ trợ kỹ thuật cho xe ${ticket.vehicle_model}.`,
            created_at: ticket.created_at,
          },
          {
            sender: "AGENT",
            content: `Hệ thống tiếp nhận hồ sơ ${ticket.id} và chuyển tới Cố vấn Dịch vụ.`,
            created_at: ticket.created_at,
          },
        ],
      });
      setEditedSummary(`Hồ sơ sự cố tiếp nhận cho xe ${ticket.vehicle_model}.`);
    }
    setIsEditingBrief(false);
  }, [ticket.id]);

  const handleSaveBrief = () => {
    setTicketDetail((prev) => ({
      ...prev,
      case_brief: {
        ...prev.case_brief,
        summary: editedSummary,
        is_edited_by_staff: true,
      },
    }));
    setIsEditingBrief(false);
    onActionComplete?.(`Đã lưu tóm tắt Case Brief mới cho hồ sơ ${ticket.id}!`);
  };

  const handleCancelBrief = () => {
    setEditedSummary(ticketDetail.case_brief.summary);
    setIsEditingBrief(false);
  };

  const executeStaffAction = async (
    actionName: string,
    actionType: StaffActionType,
    targetStatus: TicketStatus
  ) => {
    setIsSubmitting(true);
    try {
      await submitStaffAction(ticket.id, {
        action: actionType,
        staff_id: "STAFF_LE_HOANG_QUAN",
        updated_status: targetStatus,
        notes: notes || undefined,
      });
    } catch {
      // Demo fallback
    } finally {
      setIsSubmitting(false);
      onStatusUpdate?.(ticket.id, targetStatus);
      onActionComplete?.(`Đã thực hiện: ${actionName} cho hồ sơ ${ticket.id}!`);
    }
  };

  const isCritical = ticket.priority === "CRITICAL";

  return (
    <div className="bg-white border border-[#E2E8F0] rounded-2xl shadow-xs flex flex-col h-[calc(100vh-175px)] overflow-hidden">
      {/* ─────────────────────────────────────────────────────────────
          1. STICKY DETAIL HEADER (Tối đa text-xl, phân cấp rõ ràng)
      ───────────────────────────────────────────────────────────── */}
      <div className="p-4 border-b border-[#E2E8F0] bg-white space-y-3 shrink-0">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-mono text-base sm:text-lg font-bold text-[#0F172A] flex items-center gap-1.5">
                {isCritical && <Flame className="w-4 h-4 text-[#DC2626]" />}
                {ticket.id}
              </span>
              <span
                className={`px-2 py-0.5 rounded-full text-[11px] font-bold uppercase tracking-wider ${
                  isCritical
                    ? "bg-[#FEF2F2] text-[#DC2626] border border-[#DC2626]/30"
                    : ticket.priority === "HIGH"
                    ? "bg-[#FFFBEB] text-[#D97706] border border-[#D97706]/30"
                    : "bg-[#EFF3FC] text-[#1E40AF] border border-[#1E40AF]/20"
                }`}
              >
                {ticket.priority}
              </span>
              <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-[#F1F5F9] text-[#475569] border border-[#E2E8F0]">
                {ticket.status}
              </span>
            </div>

            <div className="flex items-center gap-2 text-[12px] text-[#64748B] mt-1 flex-wrap">
              <span className="flex items-center gap-1 font-semibold text-[#0F172A]">
                <Car className="w-3.5 h-3.5 text-[#1E40AF]" />
                {ticket.vehicle_model}
              </span>
              <span>•</span>
              <span>
                Khách: <strong className="font-mono text-[#0F172A]">{ticket.mock_customer_id}</strong>
              </span>
              <span>•</span>
              <span>
                Ý định: <strong className="text-[#0F172A]">{ticket.intent}</strong>
              </span>
            </div>
          </div>

          {/* Quick Action Buttons on Top Bar */}
          <div className="flex items-center gap-2 shrink-0">
            <button
              type="button"
              disabled={isSubmitting}
              onClick={() =>
                executeStaffAction(
                  "Duyệt Phương Án & Chuyển Xưởng",
                  "APPROVE",
                  "In Progress"
                )
              }
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#1E40AF] hover:bg-[#1D4ED8] text-white text-[12px] font-semibold transition shadow-xs disabled:opacity-50"
            >
              {isSubmitting ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <CheckCircle2 className="w-3.5 h-3.5" />
              )}
              <span>Duyệt & Điều Phối</span>
            </button>

            <button
              type="button"
              disabled={isSubmitting}
              onClick={() =>
                executeStaffAction(
                  "Yêu Cầu Thêm Thông Tin",
                  "REQUEST_INFO",
                  "Needs Information"
                )
              }
              className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-xl border border-[#E2E8F0] bg-white hover:bg-[#F8FAFC] text-[#475569] text-[12px] font-medium transition disabled:opacity-50"
            >
              <AlertTriangle className="w-3.5 h-3.5 text-[#D97706]" />
              <span className="hidden sm:inline">Cần thêm tin</span>
            </button>

            <button
              type="button"
              disabled={isSubmitting}
              onClick={() =>
                executeStaffAction("Hoàn tất giải quyết (Resolved)", "RESOLVE", "Resolved")
              }
              className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-xl bg-[#ECFDF5] hover:bg-[#D1FAE5] text-[#059669] text-[12px] font-semibold transition border border-[#10B981]/20 disabled:opacity-50"
            >
              <Check className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Giải quyết</span>
            </button>
          </div>
        </div>

        {/* ─────────────────────────────────────────────────────────────
            2. SUB-TABS NAVIGATION (Pills phân định 3 khu vực nội dung)
        ───────────────────────────────────────────────────────────── */}
        <div className="flex items-center gap-1.5 border-t border-[#F1F5F9] pt-2.5">
          <button
            type="button"
            onClick={() => setDetailTab("brief")}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px] font-semibold transition ${
              detailTab === "brief"
                ? "bg-[#EFF3FC] text-[#1E40AF] border border-[#1E40AF]/20"
                : "text-[#64748B] hover:bg-[#F1F5F9] hover:text-[#0F172A]"
            }`}
          >
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Hồ sơ sự cố (Case Brief)</span>
          </button>

          <button
            type="button"
            onClick={() => setDetailTab("chat")}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px] font-semibold transition ${
              detailTab === "chat"
                ? "bg-[#EFF3FC] text-[#1E40AF] border border-[#1E40AF]/20"
                : "text-[#64748B] hover:bg-[#F1F5F9] hover:text-[#0F172A]"
            }`}
          >
            <MessageSquare className="w-3.5 h-3.5" />
            <span>Nhật ký hội thoại</span>
            <span className="px-1.5 py-0.2 rounded-full bg-[#E2E8F0] text-[#475569] text-[10px]">
              {ticketDetail.conversation_history.length}
            </span>
          </button>

          <button
            type="button"
            onClick={() => setDetailTab("dispatch")}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px] font-semibold transition ${
              detailTab === "dispatch"
                ? "bg-[#EFF3FC] text-[#1E40AF] border border-[#1E40AF]/20"
                : "text-[#64748B] hover:bg-[#F1F5F9] hover:text-[#0F172A]"
            }`}
          >
            <GitBranch className="w-3.5 h-3.5" />
            <span>Điều phối xưởng & Ghi chú</span>
          </button>
        </div>
      </div>

      {/* ─────────────────────────────────────────────────────────────
          3. SCROLLABLE TAB CONTENT AREA
      ───────────────────────────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto p-4 sm:p-5 space-y-4">
        {/* =========================================================
            SUB-TAB 1: CASE BRIEF & TECHNICAL FIELDS
        ========================================================= */}
        {detailTab === "brief" && (
          <div className="space-y-4">
            {/* AI Summary Card */}
            <div className="rounded-2xl border border-[#E2E8F0] bg-[#F8FAFC] p-4 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-[#1E40AF] flex items-center gap-1">
                    <Sparkles className="w-3.5 h-3.5" /> AI Case Brief (Chuẩn Hóa)
                  </span>
                  {ticketDetail.case_brief.is_edited_by_staff && (
                    <span className="text-[10px] font-semibold text-[#059669] bg-[#ECFDF5] px-2 py-0.5 rounded-full border border-[#10B981]/20">
                      Staff đã hiệu chỉnh
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  <span className="text-[11px] text-[#059669] font-medium bg-[#ECFDF5] px-2.5 py-0.5 rounded-full border border-[#10B981]/20">
                    Độ tin cậy: {Math.round((ticketDetail.case_brief.confidence_score || 0.85) * 100)}%
                  </span>

                  {!isEditingBrief && (
                    <button
                      type="button"
                      onClick={() => setIsEditingBrief(true)}
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] font-semibold text-[#1E40AF] hover:bg-[#EFF3FC] border border-[#1E40AF]/20 transition"
                    >
                      <Edit3 className="w-3 h-3" />
                      <span>Sửa Brief</span>
                    </button>
                  )}
                </div>
              </div>

              {isEditingBrief ? (
                <div className="space-y-2.5">
                  <textarea
                    value={editedSummary}
                    onChange={(e) => setEditedSummary(e.target.value)}
                    rows={3}
                    className="w-full text-[13px] p-3 rounded-xl border border-[#CBD5E1] bg-white text-[#0F172A] leading-relaxed focus:outline-none focus:ring-2 focus:ring-[#1E40AF]/20"
                    placeholder="Chỉnh sửa nội dung tóm tắt sự cố..."
                  />
                  <div className="flex justify-end gap-2">
                    <button
                      type="button"
                      onClick={handleCancelBrief}
                      className="px-3 py-1.5 rounded-lg border border-[#E2E8F0] bg-white text-[12px] font-semibold text-[#64748B] hover:bg-[#F8FAFC]"
                    >
                      Hủy
                    </button>
                    <button
                      type="button"
                      onClick={handleSaveBrief}
                      className="px-3 py-1.5 rounded-lg bg-[#059669] hover:bg-[#047857] text-white text-[12px] font-semibold"
                    >
                      Lưu thay đổi
                    </button>
                  </div>
                </div>
              ) : (
                <p className="text-[13px] text-[#0F172A] leading-relaxed font-medium">
                  {ticketDetail.case_brief.summary}
                </p>
              )}
            </div>

            {/* Extracted Technical Fields Grid */}
            <div className="space-y-2">
              <span className="text-[11px] font-bold uppercase tracking-wider text-[#64748B]">
                Dữ kiện kỹ thuật bóc tách (Extracted Parameters)
              </span>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
                {Object.entries(ticketDetail.case_brief.captured_fields || {}).map(([key, val]) => {
                  const isDtc = key === "error_code";
                  const isLocation = key.includes("location");

                  return (
                    <div
                      key={key}
                      className={`p-3 rounded-xl border text-[12px] transition ${
                        isDtc
                          ? "bg-[#FEF2F2]/60 border-[#DC2626]/30 text-[#991B1B]"
                          : isLocation
                          ? "bg-[#EFF3FC]/50 border-[#1E40AF]/20 text-[#1E40AF]"
                          : "bg-white border-[#E2E8F0] text-[#0F172A]"
                      }`}
                    >
                      <div className="flex items-center justify-between text-[#64748B] text-[10px] uppercase font-mono">
                        <span>{key.replace(/_/g, " ")}</span>
                        {isLocation && <MapPin className="w-3 h-3 text-[#1E40AF]" />}
                      </div>
                      <div className="font-semibold mt-1 text-[13px] truncate" title={String(val)}>
                        {String(val)}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Suggested Action Alert Box */}
            <div className="rounded-2xl border border-[#1E40AF]/20 bg-[#EFF3FC] p-4 flex items-start gap-3 shadow-xs">
              <div className="w-8 h-8 rounded-xl bg-white text-[#1E40AF] flex items-center justify-center shrink-0 shadow-xs">
                <Sparkles className="w-4 h-4" />
              </div>
              <div className="space-y-1 min-w-0">
                <span className="text-[11px] font-bold uppercase tracking-wider text-[#1E40AF]">
                  Phương Án Đề Xuất Cho Xưởng Dịch Vụ
                </span>
                <p className="text-[13px] text-[#1E3A8A] font-medium leading-relaxed">
                  {ticketDetail.case_brief.suggested_action}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* =========================================================
            SUB-TAB 2: CONVERSATION TIMELINE
        ========================================================= */}
        {detailTab === "chat" && (
          <div className="space-y-3">
            <div className="flex items-center justify-between text-[12px] text-[#64748B] px-1">
              <span>Nhật ký trao đổi giữa Khách hàng và Trợ lý AI</span>
              <span>Được đồng bộ tự động</span>
            </div>

            <div className="space-y-3">
              {ticketDetail.conversation_history.map((msg, idx) => {
                const isCust = msg.sender === "CUSTOMER";
                const isStaff = msg.sender === "STAFF";

                return (
                  <div
                    key={idx}
                    className={`p-3.5 rounded-2xl text-[13px] space-y-1.5 transition ${
                      isCust
                        ? "bg-[#EFF3FC] border border-[#1E40AF]/20 ml-4 sm:ml-8"
                        : isStaff
                        ? "bg-[#F3E8FF] border border-[#7E22CE]/20 mr-4 sm:mr-8"
                        : "bg-white border border-[#E2E8F0] mr-4 sm:mr-8 shadow-xs"
                    }`}
                  >
                    <div className="flex items-center justify-between text-[11px]">
                      <span className="flex items-center gap-1.5 font-bold">
                        {isCust ? (
                          <span className="text-[#1E40AF] flex items-center gap-1">
                            <User className="w-3.5 h-3.5" /> Khách hàng
                          </span>
                        ) : isStaff ? (
                          <span className="text-[#7E22CE] flex items-center gap-1">
                            <ShieldCheck className="w-3.5 h-3.5" /> Cố vấn Dịch vụ
                          </span>
                        ) : (
                          <span className="text-[#059669] flex items-center gap-1">
                            <Bot className="w-3.5 h-3.5" /> AI Agent tiếp nhận
                          </span>
                        )}
                      </span>
                      <span className="text-[10px] text-[#94A3B8] font-mono">
                        {new Date(msg.created_at).toLocaleTimeString("vi-VN", {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </span>
                    </div>

                    <p className="text-[#0F172A] leading-relaxed pl-5 font-normal">
                      {msg.content}
                    </p>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* =========================================================
            SUB-TAB 3: ROUTING & DISPATCHER ACTIONS
        ========================================================= */}
        {detailTab === "dispatch" && (
          <div className="space-y-4">
            <div className="space-y-2">
              <span className="text-[11px] font-bold uppercase tracking-wider text-[#64748B]">
                Chọn bộ phận chuyên trách tiếp nhận (5 Nhóm P0 Chuẩn Hóa)
              </span>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                {ROUTING_DEPARTMENTS.map((dept) => {
                  const isSelected = selectedDept === dept.name;

                  return (
                    <div
                      key={dept.id}
                      onClick={() => setSelectedDept(dept.name)}
                      className={`cursor-pointer p-3.5 rounded-xl border transition-all ${
                        isSelected
                          ? "bg-[#EFF3FC] border-[#1E40AF] ring-2 ring-[#1E40AF]/15 shadow-xs"
                          : "bg-white border-[#E2E8F0] hover:border-[#CBD5E1]"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-[13px] font-bold text-[#0F172A]">
                          {dept.name}
                        </span>
                        <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold ${dept.color}`}>
                          {dept.badge}
                        </span>
                      </div>
                      <p className="text-[11px] text-[#64748B] mt-1 line-clamp-2">
                        {dept.description}
                      </p>
                      <div className="text-[10px] text-[#475569] mt-2 font-mono">
                        Phụ trách: {dept.lead}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Notes Textarea */}
            <div className="space-y-1.5">
              <label
                htmlFor="dispatch-notes-input"
                className="block text-[11px] font-bold uppercase tracking-wider text-[#64748B]"
              >
                Ghi chú điều phối nội bộ / Chỉ dẫn kỹ thuật viên xưởng:
              </label>
              <textarea
                id="dispatch-notes-input"
                rows={2}
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="VD: Chuẩn bị máy chẩn đoán giao thức CAN-bus, trạm Metropolis cử nhân viên bảo trì kiểm tra trụ P02..."
                className="w-full text-[13px] p-3 rounded-xl border border-[#CBD5E1] bg-[#F8FAFC] focus:bg-white text-[#0F172A] focus:outline-none focus:ring-2 focus:ring-[#1E40AF]/20"
              />
            </div>

            {/* Dispatch confirmation button */}
            <div className="pt-2 border-t border-[#E2E8F0] flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
              <span className="text-[12px] text-[#64748B]">
                Nhóm đích: <strong className="text-[#1E40AF]">{selectedDept}</strong>
              </span>

              <button
                type="button"
                disabled={isSubmitting}
                onClick={() =>
                  executeStaffAction(
                    `Điều phối sang ${selectedDept}`,
                    "REROUTE",
                    "In Progress"
                  )
                }
                className="inline-flex items-center justify-center gap-1.5 px-4 py-2.5 rounded-xl bg-[#1E40AF] hover:bg-[#1D4ED8] text-white text-[13px] font-semibold transition shadow-xs disabled:opacity-50"
              >
                {isSubmitting ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Send className="w-4 h-4" />
                )}
                <span>Xác nhận chuyển nhóm tiếp nhận</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
