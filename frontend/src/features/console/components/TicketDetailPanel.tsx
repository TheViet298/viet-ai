"use client";

import { useState, useEffect, useRef } from "react";
import {
  ShieldCheck,
  Sparkles,
  Edit3,
  Check,
  X,
  Clock,
  Send,
  CheckCircle2,
  AlertCircle,
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
import {
  TicketItem,
  TicketStatus,
  StaffActionType,
  TicketDetail,
  VIETNAMESE_STATUS_MAP,
  VIETNAMESE_PRIORITY_MAP,
} from "../types";
import { ROUTING_DEPARTMENTS } from "./StaffConsoleShell";
import { getTicketDetail, submitStaffAction } from "../api/consoleApi";
import { useAuth } from "@/features/shared";

interface TicketDetailPanelProps {
  ticket: TicketItem;
  onActionComplete?: (message: string) => void;
  onStatusUpdate?: (ticketId: string, newStatus: TicketStatus) => void;
}

// Fallback dataset chi tiết tương ứng với các Ticket ID mẫu
const DETAILED_TICKETS_MAP: Record<string, TicketDetail> = {
  "CASE-20260924-001": {
    case: {
      id: "CASE-20260924-001",
      mock_customer_id: "VF-CUST-001",
      customer_name: "Nguyễn Văn Tuấn",
      customer_phone: "0912345678",
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
      mock_customer_id: "VF-CUST-099",
      customer_name: "Lê Minh Trí",
      customer_phone: "0934567890",
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
      mock_customer_id: "VF-CUST-002",
      customer_name: "Trần Thị Mai",
      customer_phone: "0987654321",
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
      mock_customer_id: "VF-CUST-015",
      customer_name: "Phạm Hồng Phúc",
      customer_phone: "0901234567",
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
      mock_customer_id: "VF-CUST-023",
      customer_name: "Hoàng Gia Bảo",
      customer_phone: "0918765432",
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

// Helper làm sạch tiêu đề sự cố, loại bỏ tiền tố giật gân lặp lại
export function cleanTicketHeadline(raw?: string): string {
  if (!raw) return "Yêu cầu kiểm tra sự cố";
  return raw
    .replace(/^(SỰ CỐ NGUY HIỂM KHẨN CẤP|SỰ CỐ NGUY HIỂM|CẢNH BÁO KHẨN CẤP|KHẨN CẤP|SỰ CỐ KHẨN CẤP)\s*:\s*/gi, "")
    .trim();
}

export function TicketDetailPanel({
  ticket,
  onActionComplete,
  onStatusUpdate,
}: TicketDetailPanelProps) {
  const { user } = useAuth();
  // Detail Sub-tabs: 3 tabs
  const [detailTab, setDetailTab] = useState<"brief" | "chat" | "dispatch">("brief");

  // Local state for editing Case Brief
  const [isEditingBrief, setIsEditingBrief] = useState(false);
  const [editedSummary, setEditedSummary] = useState("");
  const [notes, setNotes] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [copiedId, setCopiedId] = useState(false);

  // Accordion state for workshop suggested action
  const [isProposalOpen, setIsProposalOpen] = useState(true);

  // Routing selection state
  const [selectedDept, setSelectedDept] = useState("Charging Operations");
  const [expandedOtherDeptId, setExpandedOtherDeptId] = useState<string | null>(null);

  // Active detail data
  const [ticketDetail, setTicketDetail] = useState<TicketDetail>(() => {
    return (
      DETAILED_TICKETS_MAP[ticket.id] || {
        case: {
          id: ticket.id,
          mock_customer_id: ticket.mock_customer_id,
          customer_name: ticket.customer_name,
          customer_phone: ticket.customer_phone,
          vehicle_code_mock: ticket.vehicle_code_mock,
          vehicle_model: ticket.vehicle_model,
          intent: ticket.intent,
          priority: ticket.priority,
          status: ticket.status,
          safety_status: ticket.safety_status,
          safety_acknowledged_at: ticket.safety_acknowledged_at,
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

  // Calculate AI Recommended Routing Department & Rationale
  const recommendedDept = (() => {
    if (ticket.priority === "CRITICAL") {
      return ROUTING_DEPARTMENTS.find((d) => d.id === "emergency_demo") || ROUTING_DEPARTMENTS[4];
    }
    if (ticket.intent === "Charging/Battery") {
      return ROUTING_DEPARTMENTS.find((d) => d.id === "charging_ops") || ROUTING_DEPARTMENTS[0];
    }
    if (ticket.intent === "Complaint/Feedback" || ticket.intent === "Complaint") {
      return ROUTING_DEPARTMENTS.find((d) => d.id === "customer_care") || ROUTING_DEPARTMENTS[2];
    }
    if (ticket.intent === "Sales/General Info" || ticket.intent === "Sales") {
      return ROUTING_DEPARTMENTS.find((d) => d.id === "sales_advisor") || ROUTING_DEPARTMENTS[3];
    }
    return ROUTING_DEPARTMENTS.find((d) => d.id === "service_center") || ROUTING_DEPARTMENTS[1];
  })();

  const aiRationale = (() => {
    if (ticket.priority === "CRITICAL") {
      return "Sự cố khẩn cấp trên tuyến cao tốc, cần đội phản ứng nhanh 24/7 kích hoạt xe cứu hộ.";
    }
    if (ticket.intent === "Charging/Battery") {
      return "Lỗi handshake cổng sạc DC CC01, cần chuyên viên trạm sạc kiểm tra module từ xa.";
    }
    if (ticket.intent === "Complaint/Feedback" || ticket.intent === "Complaint") {
      return "Phản ánh dịch vụ cần chuyên viên CSKH liên hệ xử lý trực tiếp.";
    }
    return "Cảnh báo đèn táp-lô cần kỹ thuật viên xưởng kết nối cổng OBD-II kiểm tra.";
  })();

  // Ref cuộn panel chi tiết về đỉnh khi đổi case
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  // When ticket prop changes, sync detail & default selected dept
  useEffect(() => {
    scrollContainerRef.current?.scrollTo({ top: 0, behavior: "smooth" });

    let isMounted = true;
    const fetchLiveDetail = async () => {
      try {
        const res = await getTicketDetail(ticket.id);
        if (isMounted && res && res.success && res.data) {
          setTicketDetail(res.data);
          setEditedSummary(res.data.case_brief?.summary || "");
          return;
        }
      } catch {
        // Fallback to local map if offline
      }

      if (isMounted) {
        const existing = DETAILED_TICKETS_MAP[ticket.id];
        if (existing) {
          setTicketDetail(existing);
          setEditedSummary(existing.case_brief.summary);
        } else {
          setTicketDetail({
            case: {
              id: ticket.id,
              mock_customer_id: ticket.mock_customer_id,
              customer_name: ticket.customer_name,
              customer_phone: ticket.customer_phone,
              vehicle_code_mock: ticket.vehicle_code_mock,
              vehicle_model: ticket.vehicle_model,
              intent: ticket.intent,
              priority: ticket.priority,
              status: ticket.status,
              safety_status: ticket.safety_status,
              safety_acknowledged_at: ticket.safety_acknowledged_at,
            },
            case_brief: {
              summary: ticket.issue_summary || `Hồ sơ sự cố tiếp nhận cho xe ${ticket.vehicle_model}. Yêu cầu kiểm tra kỹ thuật và điều phối xưởng.`,
              captured_fields: {
                vehicle_model: ticket.vehicle_model,
                station_location: "Đang cập nhật",
                error_code: ticket.error_code_short || "Chưa ghi nhận mã lỗi",
                current_soc: "Đang xác minh",
              },
              suggested_action: ticket.suggested_action || "Kiểm tra triệu chứng thực tế và liên hệ chủ xe.",
              confidence_score: ticket.confidence_score || 0.85,
            },
            conversation_history: [
              {
                sender: "CUSTOMER",
                content: ticket.issue_summary || `Yêu cầu hỗ trợ kỹ thuật cho xe ${ticket.vehicle_model}.`,
                created_at: ticket.created_at,
              },
              {
                sender: "AGENT",
                content: `Hệ thống tiếp nhận hồ sơ ${ticket.id} và chuyển tới Cố vấn Dịch vụ.`,
                created_at: ticket.created_at,
              },
            ],
          });
          setEditedSummary(ticket.issue_summary || `Hồ sơ sự cố tiếp nhận cho xe ${ticket.vehicle_model}.`);
        }
      }
    };

    fetchLiveDetail();
    setIsEditingBrief(false);
    setSelectedDept(recommendedDept.name);
    setExpandedOtherDeptId(null);

    return () => {
      isMounted = false;
    };
  }, [ticket.id, ticket, recommendedDept.name]);

  const handleCopyId = () => {
    navigator.clipboard.writeText(ticket.id);
    setCopiedId(true);
    setTimeout(() => setCopiedId(false), 2000);
  };

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
        staff_id: user?.name || user?.email || "Cố vấn Dịch vụ VinFast",
        updated_status: targetStatus,
        notes: notes || undefined,
      });
      const refreshed = await getTicketDetail(ticket.id);
      if (refreshed && refreshed.success && refreshed.data) {
        setTicketDetail(refreshed.data);
      }
    } catch {
      // Demo fallback
    } finally {
      setIsSubmitting(false);
      onStatusUpdate?.(ticket.id, targetStatus);
      onActionComplete?.(`Đã thực hiện: ${actionName} cho hồ sơ ${ticket.id}!`);
    }
  };

  const isCritical = ticket.priority === "CRITICAL";
  const otherDepts = ROUTING_DEPARTMENTS.filter((d) => d.id !== recommendedDept.id);

  // Structured key-value parameter rows với bóc tách chuẩn xác từ captured_fields
  const captured = ticketDetail.case_brief.captured_fields || {};

  // 1. Dòng xe
  const resolvedModel = captured.vehicle_model || ticket.vehicle_model || "VF8";

  // 2. Vị trí
  const resolvedLocation =
    ticketDetail.location?.location_label ||
    captured.station_location ||
    captured.location_label ||
    (ticketDetail.location?.latitude
      ? `${ticketDetail.location.latitude.toFixed(4)}° N, ${ticketDetail.location.longitude?.toFixed(4)}° E`
      : "Đang xác minh tọa độ");

  // 3. Pin (SoC): Đọc đa dạng key soc, current_soc, battery_percentage
  const rawSoc = captured.current_soc ?? captured.soc ?? captured.battery_percentage;
  let resolvedSoc = "Chưa rõ";
  if (rawSoc !== undefined && rawSoc !== null && rawSoc !== "") {
    resolvedSoc = String(rawSoc).trim();
    if (/^\d+$/.test(resolvedSoc)) {
      resolvedSoc = `${resolvedSoc}%`;
    }
  }

  // 4. Mã lỗi / Cảnh báo: Đọc error_code, warning_symbol, visual_signals
  const rawWarning =
    captured.warning_symbol ||
    captured.visual_signals ||
    captured.error_code ||
    ticket.error_code_short;
  let resolvedWarning = "Chưa ghi nhận mã lỗi";
  let isWarningAlert = false;

  if (rawWarning) {
    const warnStr = String(rawWarning);
    if (/rùa|turtle/i.test(warnStr)) {
      resolvedWarning = "Rùa vàng (giảm công suất)";
      isWarningAlert = true;
    } else {
      resolvedWarning = warnStr;
      if (/CC01|BMS|LIMIT/i.test(warnStr)) {
        isWarningAlert = true;
      }
    }
  }

  // 5. GPS Sharing
  const isGpsShared = Boolean(
    ticketDetail.location?.share_with_staff ||
    ticket.has_location_consent ||
    captured.location_consent ||
    captured.gps_coordinates
  );

  // 6. Safety check: Safety status & safety acknowledged at
  const safetyStatus = ticketDetail.case.safety_status || ticket.safety_status;
  const safetyAckTime = ticketDetail.case.safety_acknowledged_at || ticket.safety_acknowledged_at;
  const isSafetyConfirmed =
    safetyStatus === "customer_reported_safe" ||
    safetyStatus === "safe" ||
    Boolean(safetyAckTime);

  const parameterRows = [
    {
      label: "Dòng xe",
      value: resolvedModel,
      isWarning: false,
      isAlert: false,
    },
    {
      label: "Vị trí",
      value: resolvedLocation,
      isWarning: resolvedLocation.includes("Đang xác minh") || resolvedLocation.includes("Chưa"),
      isAlert: false,
    },
    {
      label: "Dung lượng pin (SoC)",
      value: resolvedSoc,
      isWarning: resolvedSoc === "Chưa rõ" || resolvedSoc.includes("< 10%"),
      isAlert: false,
    },
    {
      label: "Cảnh báo / Mã lỗi",
      value: resolvedWarning,
      isWarning: resolvedWarning.includes("Chưa"),
      isAlert: isWarningAlert,
    },
    {
      label: "Chia sẻ vị trí GPS",
      value: isGpsShared ? "Đã bật chia sẻ GPS" : "Chưa bật chia sẻ vị trí",
      isWarning: !isGpsShared,
      isAlert: false,
    },
  ];

  if (captured.charger_id) {
    parameterRows.push({
      label: "Trụ sạc / Cổng kết nối",
      value: captured.charger_id,
      isWarning: false,
      isAlert: false,
    });
  }

  // Tiêu đề ngắn gọn 1 dòng cho Header (đã loại bỏ tiền tố giật gân)
  const displayHeaderTitle = cleanTicketHeadline(
    ticket.issue_summary && ticket.issue_summary !== "Yêu cầu kiểm tra sự cố"
      ? ticket.issue_summary
      : ticketDetail.case_brief.summary
      ? ticketDetail.case_brief.summary.split(".")[0]
      : `Hồ sơ sự cố xe ${ticket.vehicle_model}`
  );

  // Formatted Safety Time
  let formattedSafetyTime = "";
  if (safetyAckTime) {
    try {
      formattedSafetyTime = new Date(safetyAckTime).toLocaleTimeString("vi-VN", {
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      formattedSafetyTime = "";
    }
  }

  return (
    <div
      key={ticket.id}
      className="bg-white rounded-2xl shadow-[0_1px_3px_rgba(0,0,0,0.06)] flex flex-col h-[calc(100vh-140px)] overflow-hidden transition-opacity duration-150 animate-in fade-in"
    >
      {/* ─────────────────────────────────────────────────────────────
          1. STICKY DETAIL HEADER: 1 DÒNG SÚC TÍCH, NÚT THEO TRẠNG THÁI
      ───────────────────────────────────────────────────────────── */}
      <div className="sticky top-0 z-20 bg-white/95 backdrop-blur-sm border-b border-slate-100 p-4 space-y-2.5 shrink-0 shadow-2xs">
        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
          {/* Main Case Title & Subtitle */}
          <div className="space-y-1 min-w-0 flex-1">
            <h2
              className="text-[17px] sm:text-[18px] font-bold text-slate-900 leading-snug truncate"
              title={displayHeaderTitle}
            >
              {displayHeaderTitle}
            </h2>

            {/* Subtitle: 001 · CASE-20260924-001 · VF8 · Khách: CUST · Trạng thái */}
            <div className="flex items-center gap-2 text-[12px] text-slate-500 flex-wrap">
              <span className="font-semibold text-slate-800 font-mono">
                {ticket.id.replace(/^CASE-\d+-/i, "")}
              </span>
              <span>·</span>
              <button
                type="button"
                onClick={handleCopyId}
                className="font-mono text-slate-600 bg-slate-100 hover:bg-slate-200 px-1.5 py-0.5 rounded inline-flex items-center gap-1 transition text-[11px]"
                title="Sao chép toàn bộ mã hồ sơ"
              >
                <span>{ticket.id}</span>
                {copiedId ? (
                  <Check className="w-3 h-3 text-emerald-600" />
                ) : (
                  <span className="text-[9px] text-slate-400">copy</span>
                )}
              </button>
              <span>·</span>
              <span className="font-medium text-slate-700">{ticket.vehicle_model}</span>
              {ticket.vehicle_source === "inferred" && (
                <span className="text-[10px] bg-amber-50 text-amber-700 border border-amber-300 px-1.5 py-0.5 rounded font-medium">
                  Cần xác minh
                </span>
              )}
              <span>·</span>
              <span>
                Khách:{" "}
                <strong className="text-slate-700">
                  {ticket.customer_name ? (
                    <>
                      <span>{ticket.customer_name}</span>{" "}
                      <span className="font-mono text-[11px] text-slate-500 font-normal">
                        ({ticket.mock_customer_id})
                      </span>
                    </>
                  ) : (
                    <span className="font-mono">{ticket.mock_customer_id}</span>
                  )}
                </strong>
              </span>
              <span>·</span>
              <span className="inline-flex items-center gap-1.5 font-medium">
                <span
                  className={`w-2 h-2 rounded-full ${
                    isCritical
                      ? "bg-red-500 animate-pulse"
                      : ticket.priority === "HIGH"
                      ? "bg-amber-500"
                      : "bg-blue-500"
                  }`}
                />
                <span className="text-slate-700 font-medium">
                  {VIETNAMESE_STATUS_MAP[ticket.status] || ticket.status}
                </span>
              </span>
            </div>
          </div>

          {/* Quick Action Buttons: Thiết kế theo đúng trạng thái hồ sơ (Chỉ 1 nút nổi bật) */}
          <div className="flex items-center gap-2 shrink-0 pt-0.5">
            {/* TRƯỜNG HỢP 1: Chờ duyệt (Staff Reviewing / New) */}
            {(ticket.status === "Staff Reviewing" || ticket.status === "New") && (
              <>
                {/* NÚT CHÍNH NỔI BẬT: Duyệt & Điều phối */}
                <button
                  type="button"
                  disabled={isSubmitting}
                  onClick={() =>
                    executeStaffAction(
                      "Duyệt phương án & chuyển xưởng",
                      "APPROVE",
                      "In Progress"
                    )
                  }
                  className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-[#1E40AF] hover:bg-[#1D4ED8] text-white text-[12.5px] font-semibold transition shadow-xs active:scale-[0.98] disabled:opacity-50"
                >
                  {isSubmitting ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <CheckCircle2 className="w-3.5 h-3.5" />
                  )}
                  <span>Duyệt & Điều phối</span>
                </button>

                {/* NÚT PHỤ 1: Cần thêm tin */}
                <button
                  type="button"
                  disabled={isSubmitting}
                  onClick={() =>
                    executeStaffAction(
                      "Yêu cầu thêm thông tin",
                      "REQUEST_INFO",
                      "Needs Information"
                    )
                  }
                  className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-xl border border-slate-200 bg-white hover:bg-amber-50 hover:text-amber-700 text-slate-700 text-[12px] font-medium transition active:scale-[0.98] disabled:opacity-50"
                  title="Yêu cầu khách hàng bổ sung thêm dữ kiện"
                >
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
                  <span className="hidden sm:inline">Cần thêm tin</span>
                </button>

                {/* NÚT PHỤ 2: Sửa brief */}
                <button
                  type="button"
                  onClick={() => setIsEditingBrief(true)}
                  className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-[12px] font-medium transition active:scale-[0.98]"
                  title="Chỉnh sửa tóm tắt Case Brief"
                >
                  <Edit3 className="w-3.5 h-3.5 text-slate-500" />
                  <span className="hidden sm:inline">Sửa brief</span>
                </button>
              </>
            )}

            {/* TRƯỜNG HỢP 2: Cần thêm tin (Needs Information) */}
            {ticket.status === "Needs Information" && (
              <>
                {/* NÚT CHÍNH NỔI BẬT: Nhắc khách */}
                <button
                  type="button"
                  disabled={isSubmitting}
                  onClick={() =>
                    executeStaffAction(
                      "Gửi tin nhắn nhắc khách bổ sung thông tin",
                      "REQUEST_INFO",
                      "Needs Information"
                    )
                  }
                  className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-amber-600 hover:bg-amber-700 text-white text-[12.5px] font-semibold transition shadow-xs active:scale-[0.98] disabled:opacity-50"
                >
                  {isSubmitting ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Send className="w-3.5 h-3.5" />
                  )}
                  <span>Nhắc khách</span>
                </button>

                {/* NÚT PHỤ: Duyệt khi đã đủ */}
                <button
                  type="button"
                  disabled={isSubmitting}
                  onClick={() =>
                    executeStaffAction(
                      "Thông tin đã đủ - Duyệt điều phối",
                      "APPROVE",
                      "In Progress"
                    )
                  }
                  className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-xl border border-slate-200 bg-white hover:bg-blue-50 hover:text-[#1E40AF] text-slate-700 text-[12px] font-medium transition active:scale-[0.98] disabled:opacity-50"
                  title="Duyệt ca khi khách đã cung cấp đủ dữ liệu"
                >
                  <CheckCircle2 className="w-3.5 h-3.5 text-[#1E40AF]" />
                  <span className="hidden sm:inline">Duyệt khi đã đủ</span>
                </button>
              </>
            )}

            {/* TRƯỜNG HỢP 3: Đang xử lý (In Progress) */}
            {ticket.status === "In Progress" && (
              <>
                {/* NÚT CHÍNH NỔI BẬT: Giải quyết */}
                <button
                  type="button"
                  disabled={isSubmitting}
                  onClick={() =>
                    executeStaffAction(
                      "Hoàn tất giải quyết (Resolved)",
                      "RESOLVE",
                      "Resolved"
                    )
                  }
                  className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-[12.5px] font-semibold transition shadow-xs active:scale-[0.98] disabled:opacity-50"
                >
                  {isSubmitting ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Check className="w-3.5 h-3.5" />
                  )}
                  <span>Giải quyết</span>
                </button>

                {/* NÚT PHỤ: Điều phối lại */}
                <button
                  type="button"
                  onClick={() => setDetailTab("dispatch")}
                  className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-[12px] font-medium transition active:scale-[0.98]"
                  title="Chuyển sang tab điều phối xưởng"
                >
                  <GitBranch className="w-3.5 h-3.5 text-slate-500" />
                  <span className="hidden sm:inline">Điều phối lại</span>
                </button>
              </>
            )}

            {/* TRƯỜNG HỢP 4: Đã giải quyết (Resolved) */}
            {ticket.status === "Resolved" && (
              <>
                <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-700 text-[12px] font-semibold">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>Đã giải quyết</span>
                </div>
                <button
                  type="button"
                  disabled={isSubmitting}
                  onClick={() =>
                    executeStaffAction("Đóng hồ sơ (Closed)", "CLOSE", "Closed")
                  }
                  className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-xl border border-slate-200 bg-white hover:bg-slate-100 text-slate-700 text-[12px] font-medium transition active:scale-[0.98] disabled:opacity-50"
                  title="Đóng lưu trữ hồ sơ"
                >
                  <X className="w-3.5 h-3.5 text-slate-500" />
                  <span className="hidden sm:inline">Đóng hồ sơ</span>
                </button>
                <button
                  type="button"
                  disabled={isSubmitting}
                  onClick={() =>
                    executeStaffAction("Mở lại hồ sơ (Reopened)", "REOPEN", "Reopened")
                  }
                  className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-xl border border-slate-200 bg-white hover:bg-amber-50 hover:text-amber-700 text-slate-700 text-[12px] font-medium transition active:scale-[0.98] disabled:opacity-50"
                  title="Mở lại hồ sơ nếu khách cần hỗ trợ thêm"
                >
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
                  <span className="hidden sm:inline">Mở lại</span>
                </button>
              </>
            )}

            {/* TRƯỜNG HỢP 5: Đã đóng (Closed) */}
            {ticket.status === "Closed" && (
              <>
                <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-100 border border-slate-200 text-slate-600 text-[12px] font-semibold">
                  <Check className="w-3.5 h-3.5 text-slate-500" />
                  <span>Hồ sơ đã đóng</span>
                </div>
                <button
                  type="button"
                  disabled={isSubmitting}
                  onClick={() =>
                    executeStaffAction("Mở lại hồ sơ (Reopened)", "REOPEN", "Reopened")
                  }
                  className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-xl border border-slate-200 bg-white hover:bg-amber-50 hover:text-amber-700 text-slate-700 text-[12px] font-medium transition active:scale-[0.98] disabled:opacity-50"
                >
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
                  <span className="hidden sm:inline">Mở lại hồ sơ</span>
                </button>
              </>
            )}
          </div>
        </div>

        {/* ─────────────────────────────────────────────────────────────
            BANNER AN TOÀN NỔI BẬT: ĐẶT Ở ĐẦU DETAIL KHI DUYỆT
        ───────────────────────────────────────────────────────────── */}
        {isSafetyConfirmed ? (
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-[12px] font-medium">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>
              <strong>Khách đã xác nhận an toàn</strong>
              {formattedSafetyTime ? ` lúc ${formattedSafetyTime}` : ""} (đã dừng đỗ an toàn, bật hazard)
            </span>
          </div>
        ) : isCritical ? (
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-red-50 border border-red-200 text-red-800 text-[12px] font-medium animate-pulse">
            <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
            <span>
              <strong>Khách chưa xác nhận an toàn!</strong> Cần ưu tiên gọi hotline hoặc nhắc khách kích hoạt hướng dẫn an toàn.
            </span>
          </div>
        ) : null}

        {/* ─────────────────────────────────────────────────────────────
            SUB-TABS NAVIGATION (Sentence case, clean tabs)
        ───────────────────────────────────────────────────────────── */}
        <div className="flex items-center gap-1.5 pt-1">
          <button
            type="button"
            onClick={() => setDetailTab("brief")}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px] font-medium transition ${detailTab === "brief"
                ? "bg-[#EFF3FC] text-[#1E40AF] font-semibold"
                : "text-slate-500 hover:bg-slate-100 hover:text-slate-800"
              }`}
          >
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Hồ sơ sự cố</span>
          </button>

          <button
            type="button"
            onClick={() => setDetailTab("chat")}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px] font-medium transition ${detailTab === "chat"
                ? "bg-[#EFF3FC] text-[#1E40AF] font-semibold"
                : "text-slate-500 hover:bg-slate-100 hover:text-slate-800"
              }`}
          >
            <MessageSquare className="w-3.5 h-3.5" />
            <span>Nhật ký hội thoại</span>
            <span className="px-1.5 py-0.2 rounded-full bg-slate-200 text-slate-700 text-[10px]">
              {ticketDetail.conversation_history.length}
            </span>
          </button>

          <button
            type="button"
            onClick={() => setDetailTab("dispatch")}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px] font-medium transition ${detailTab === "dispatch"
                ? "bg-[#EFF3FC] text-[#1E40AF] font-semibold"
                : "text-slate-500 hover:bg-slate-100 hover:text-slate-800"
              }`}
          >
            <GitBranch className="w-3.5 h-3.5" />
            <span>Điều phối xưởng</span>
          </button>
        </div>
      </div>

      {/* ─────────────────────────────────────────────────────────────
          2. SCROLLABLE TAB CONTENT AREA
      ───────────────────────────────────────────────────────────── */}
      <div ref={scrollContainerRef} className="flex-1 overflow-y-auto p-4 sm:p-5 space-y-4">
        {/* =========================================================
            SUB-TAB 1: CASE BRIEF & TECHNICAL FIELDS
        ========================================================= */}
        {detailTab === "brief" && (
          <div className="space-y-4">
            {/* Tóm tắt sự cố bởi AI - Nền phẳng, sentence case */}
            <div className="rounded-xl bg-slate-50/80 p-3.5 space-y-2 group">
              <div className="flex items-center justify-between text-[12px]">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-slate-800 flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5 text-[#1E40AF]" />
                    Tóm tắt sự cố bởi AI
                  </span>
                  {ticketDetail.case_brief.is_edited_by_staff && (
                    <span className="text-[10px] text-[#059669] bg-[#ECFDF5] px-2 py-0.5 rounded-full font-medium">
                      Đã hiệu chỉnh
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  <span className="text-[11px] text-slate-500">
                    Độ tin cậy: <strong className="text-emerald-700 font-semibold">{Math.round((ticketDetail.case_brief.confidence_score || 0.85) * 100)}%</strong>
                  </span>

                  {!isEditingBrief && (
                    <button
                      type="button"
                      onClick={() => setIsEditingBrief(true)}
                      className="opacity-70 group-hover:opacity-100 inline-flex items-center gap-1 text-[11px] font-medium text-[#1E40AF] hover:underline transition"
                    >
                      <Edit3 className="w-3 h-3" />
                      <span>Sửa</span>
                    </button>
                  )}
                </div>
              </div>

              {isEditingBrief ? (
                <div className="space-y-2 pt-1">
                  <textarea
                    value={editedSummary}
                    onChange={(e) => setEditedSummary(e.target.value)}
                    rows={3}
                    className="w-full text-[13px] p-2.5 rounded-lg border border-slate-300 bg-white text-slate-900 leading-relaxed focus:outline-none focus:ring-2 focus:ring-[#1E40AF]/20"
                    placeholder="Chỉnh sửa nội dung tóm tắt sự cố..."
                  />
                  <div className="flex justify-end gap-2">
                    <button
                      type="button"
                      onClick={handleCancelBrief}
                      className="px-2.5 py-1 rounded-lg text-[12px] font-medium text-slate-600 hover:bg-slate-200"
                    >
                      Hủy
                    </button>
                    <button
                      type="button"
                      onClick={handleSaveBrief}
                      className="px-3 py-1 rounded-lg bg-[#1E40AF] text-white text-[12px] font-medium hover:bg-[#1D4ED8]"
                    >
                      Lưu
                    </button>
                  </div>
                </div>
              ) : (
                <p className="text-[13px] text-slate-800 leading-relaxed">
                  {ticketDetail.case_brief.summary}
                </p>
              )}
            </div>

            {/* ─────────────────────────────────────────────────────────────
                THAM SỐ BÓC TÁCH: BỎ Ô, DÙNG DANH SÁCH KEY-VALUE
                Giá trị đặt sát nhãn, chỉ tô nổi mục thiếu/cần xác minh (màu vàng cam/đỏ)
            ───────────────────────────────────────────────────────────── */}
            <div className="space-y-1.5 pt-1">
              <div className="flex items-center justify-between px-1">
                <span className="text-[12.5px] font-semibold text-slate-900">
                  Dữ kiện kỹ thuật bóc tách
                </span>
                <span className="text-[11px] text-slate-400">
                  Trích xuất tự động từ hội thoại
                </span>
              </div>

              <div className="rounded-xl border border-slate-100 divide-y divide-slate-100 overflow-hidden bg-white text-[13px]">
                {parameterRows.map((row, idx) => (
                  <div
                    key={idx}
                    className="flex items-center py-2.5 px-3.5 hover:bg-slate-50/50 transition gap-3"
                  >
                    <span className="text-slate-500 text-[12.5px] w-36 sm:w-44 shrink-0 font-normal">
                      {row.label}
                    </span>
                    <span
                      className={`font-medium flex-1 text-left flex items-center gap-1.5 ${
                        row.isAlert
                          ? "text-red-600 font-semibold"
                          : row.isWarning
                          ? "text-amber-600 font-semibold"
                          : "text-slate-900"
                      }`}
                    >
                      {row.isAlert && <AlertCircle className="w-3.5 h-3.5 text-red-500 shrink-0" />}
                      {row.isWarning && !row.isAlert && (
                        <AlertTriangle className="w-3.5 h-3.5 text-amber-500 shrink-0" />
                      )}
                      <span>{row.value}</span>
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* ─────────────────────────────────────────────────────────────
                PHƯƠNG ÁN ĐỀ XUẤT CHO XƯỞNG: ACCORDION ĐÓNG SẴN
                Tóm tắt 1 dòng khi đóng, mở/đóng 150-200ms ease-out với mũi tên xoay
            ───────────────────────────────────────────────────────────── */}
            <div className="pt-1">
              <div className="rounded-xl border border-slate-100 bg-slate-50/60 overflow-hidden transition-all duration-200">
                {/* Accordion Header (Click to toggle) */}
                <button
                  type="button"
                  onClick={() => setIsProposalOpen(!isProposalOpen)}
                  className="w-full p-3 flex items-center justify-between text-left gap-3 hover:bg-slate-100/60 transition"
                >
                  <div className="flex items-center gap-2 min-w-0 flex-1">
                    <Sparkles className="w-4 h-4 text-[#1E40AF] shrink-0" />
                    <span className="text-[12.5px] font-semibold text-slate-900 shrink-0">
                      Phương án đề xuất cho xưởng:
                    </span>
                    {/* Tóm tắt 1 dòng khi đóng */}
                    <span className="text-[12px] text-slate-500 truncate font-normal">
                      {ticketDetail.case_brief.suggested_action}
                    </span>
                  </div>

                  <ChevronRight
                    className={`w-4 h-4 text-slate-400 shrink-0 transition-transform duration-200 ease-out ${isProposalOpen ? "rotate-90 text-[#1E40AF]" : ""
                      }`}
                  />
                </button>

                {/* Accordion Content */}
                {isProposalOpen && (
                  <div className="p-3.5 pt-0 border-t border-slate-100 space-y-2.5 animate-fadeIn">
                    <p className="text-[13px] text-slate-800 leading-relaxed font-normal bg-white p-3 rounded-lg border border-slate-100">
                      {ticketDetail.case_brief.suggested_action}
                    </p>
                    <div className="flex justify-end">
                      <button
                        type="button"
                        onClick={() => {
                          setNotes(
                            (prev) =>
                              (prev ? prev + "\n" : "") +
                              `[Phương án đề xuất]: ${ticketDetail.case_brief.suggested_action}`
                          );
                          setDetailTab("dispatch");
                          onActionComplete?.("Đã sao chép phương án vào Ghi chú điều phối!");
                        }}
                        className="text-[11.5px] font-medium text-[#1E40AF] hover:underline"
                      >
                        Chèn vào ghi chú điều phối →
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* =========================================================
            SUB-TAB 2: CONVERSATION TIMELINE
        ========================================================= */}
        {detailTab === "chat" && (
          <div className="space-y-3">
            <div className="flex items-center justify-between text-[12px] text-slate-500 px-1">
              <span>Nhật ký trao đổi với khách hàng</span>
              <span>Được đồng bộ tự động</span>
            </div>

            <div className="space-y-2.5">
              {ticketDetail.conversation_history.map((msg, idx) => {
                const isCust = msg.sender === "CUSTOMER";
                const isStaff = msg.sender === "STAFF";

                return (
                  <div
                    key={idx}
                    className={`p-3 rounded-xl text-[13px] space-y-1 transition ${isCust
                        ? "bg-[#EFF3FC] ml-4 sm:ml-8"
                        : isStaff
                          ? "bg-[#F3E8FF] mr-4 sm:mr-8"
                          : "bg-slate-50 mr-4 sm:mr-8"
                      }`}
                  >
                    <div className="flex items-center justify-between text-[11px]">
                      <span className="flex items-center gap-1.5 font-medium">
                        {isCust ? (
                          <span className="text-[#1E40AF] flex items-center gap-1">
                            <User className="w-3.5 h-3.5" /> Khách hàng
                          </span>
                        ) : isStaff ? (
                          <span className="text-[#7E22CE] flex items-center gap-1">
                            <ShieldCheck className="w-3.5 h-3.5" /> Cố vấn dịch vụ
                          </span>
                        ) : (
                          <span className="text-[#059669] flex items-center gap-1">
                            <Bot className="w-3.5 h-3.5" /> AI Agent
                          </span>
                        )}
                      </span>
                      <span className="text-[10px] text-slate-400 font-mono">
                        {new Date(msg.created_at).toLocaleTimeString("vi-VN", {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </span>
                    </div>

                    <p className="text-slate-800 leading-relaxed font-normal">
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
            Hiện 1 nhóm AI đề xuất ở trên cùng kèm lý do 1 dòng.
            Các nhóm khác thu gọn thành danh sách tên.
        ========================================================= */}
        {detailTab === "dispatch" && (
          <div className="space-y-4">
            {/* Top Recommended Group by AI */}
            <div className="space-y-1.5">
              <span className="text-[12.5px] font-semibold text-slate-900 block px-1">
                Bộ phận đề xuất bởi AI
              </span>

              <div
                onClick={() => setSelectedDept(recommendedDept.name)}
                className={`cursor-pointer p-3.5 rounded-xl border transition-all ${selectedDept === recommendedDept.name
                    ? "bg-[#EFF3FC]/70 border-[#1E40AF] ring-1 ring-[#1E40AF]"
                    : "bg-slate-50 border-slate-200 hover:bg-slate-100"
                  }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-[#1E40AF]" />
                    <span className="text-[13.5px] font-bold text-slate-900">
                      {recommendedDept.name}
                    </span>
                    <span className="text-[10px] px-2 py-0.5 rounded-full font-semibold bg-blue-100 text-[#1E40AF]">
                      {recommendedDept.badge}
                    </span>
                  </div>
                  <span className="text-[11px] text-slate-500 font-mono">
                    Phụ trách: {recommendedDept.lead.split("(")[0].trim()}
                  </span>
                </div>

                {/* 1-line Rationale */}
                <p className="text-[12px] text-[#1E3A8A] mt-2 font-medium bg-white/70 p-2 rounded-lg border border-blue-100">
                  💡 Lý do đề xuất: {aiRationale}
                </p>
              </div>
            </div>

            {/* Other Departments: Collapsed List */}
            <div className="space-y-1.5 pt-1">
              <span className="text-[12px] text-slate-500 font-medium block px-1">
                Hoặc chọn nhóm bộ phận khác:
              </span>

              <div className="rounded-xl border border-slate-100 divide-y divide-slate-100 overflow-hidden bg-white">
                {otherDepts.map((dept) => {
                  const isSelected = selectedDept === dept.name;
                  const isExpanded = expandedOtherDeptId === dept.id;

                  return (
                    <div key={dept.id} className="transition">
                      <div
                        onClick={() => {
                          setSelectedDept(dept.name);
                          setExpandedOtherDeptId(isExpanded ? null : dept.id);
                        }}
                        className={`cursor-pointer p-3 flex items-center justify-between hover:bg-slate-50 transition ${isSelected ? "bg-[#EFF3FC]/40" : ""
                          }`}
                      >
                        <div className="flex items-center gap-2.5">
                          <input
                            type="radio"
                            name="routingDept"
                            checked={isSelected}
                            onChange={() => {
                              setSelectedDept(dept.name);
                            }}
                            className="text-[#1E40AF] focus:ring-[#1E40AF]"
                          />
                          <span
                            className={`text-[13px] ${isSelected ? "font-bold text-[#1E40AF]" : "font-medium text-slate-800"
                              }`}
                          >
                            {dept.name}
                          </span>
                          <span className={`text-[10px] px-2 py-0.5 rounded-full font-semibold ${dept.color}`}>
                            {dept.badge}
                          </span>
                        </div>

                        <div className="flex items-center gap-3">
                          <span className="text-[11px] text-slate-400 font-mono hidden sm:inline">
                            {dept.lead.split("(")[0].trim()}
                          </span>
                          <ChevronRight
                            className={`w-3.5 h-3.5 text-slate-400 transition-transform duration-200 ${isExpanded ? "rotate-90" : ""
                              }`}
                          />
                        </div>
                      </div>

                      {/* Expanded description on click or select */}
                      {isExpanded && (
                        <div className="px-9 pb-3 text-[12px] text-slate-600 space-y-1 bg-slate-50/50 animate-fadeIn">
                          <p>{dept.description}</p>
                          <p className="text-[11px] text-slate-400 font-mono">
                            Người phụ trách: {dept.lead}
                          </p>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Notes Textarea */}
            <div className="space-y-1.5 pt-1">
              <label
                htmlFor="dispatch-notes-input"
                className="block text-[12px] font-semibold text-slate-700"
              >
                Ghi chú điều phối gửi xưởng (tùy chọn):
              </label>
              <textarea
                id="dispatch-notes-input"
                rows={2}
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="VD: Chuẩn bị máy chẩn đoán CAN-bus, trạm Metropolis cử KTV kiểm tra trụ P02..."
                className="w-full text-[13px] p-2.5 rounded-xl border border-slate-200 bg-slate-50 focus:bg-white text-slate-900 focus:outline-none focus:ring-2 focus:ring-[#1E40AF]/20"
              />
            </div>

            {/* Dispatch confirmation button */}
            <div className="pt-2 border-t border-slate-100 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
              <span className="text-[12px] text-slate-500">
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
                className="inline-flex items-center justify-center gap-1.5 px-4 py-2 rounded-xl bg-[#1E40AF] hover:bg-[#1D4ED8] text-white text-[12.5px] font-semibold transition shadow-xs disabled:opacity-50"
              >
                {isSubmitting ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Send className="w-3.5 h-3.5" />
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
