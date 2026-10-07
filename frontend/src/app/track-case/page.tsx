"use client";

import { useState, useEffect, useMemo } from "react";
import Link from "next/link";
import {
  Search,
  CheckCircle2,
  Clock,
  Car,
  PhoneCall,
  Sparkles,
  RotateCcw,
  Star,
  Check,
  Copy,
  CheckCheck,
  AlertCircle,
  MessageSquare,
  MapPin,
  ExternalLink,
  ChevronRight,
  ChevronDown,
  ChevronUp,
  BookOpen,
  Navigation,
  ThumbsUp,
  Filter,
  ShieldCheck,
  Loader2,
  Wrench,
  BatteryCharging,
  Info,
  ShieldAlert,
  ArrowRight,
  Lock,
} from "lucide-react";
import {
  getCaseStatus,
  getCustomerCases,
  reopenCustomerCase,
  submitCustomerFeedback,
} from "@/features/chat/api/chatApi";
import { CustomerCaseItem } from "@/features/chat/types";
import { useAuth } from "@/features/shared";

// =============================================================================
// TYPES & DATA STRUCTURES (ADR-005, screen-spec.md Section 3, 5.4, 5.5, CUS-04)
// =============================================================================

export interface ServicePointSeed {
  id: string;
  name: string;
  type: "SERVICE_WORKSHOP" | "CHARGING_STATION" | "EXPRESSWAY_RESCUE";
  address: string;
  distance: string;
  hotline: string;
  coords: { lat: number; lng: number };
}

export interface TrackedCase {
  id: string;
  vehicleModel: string;
  vehicleCode: string;
  status:
    | "Staff Reviewing"
    | "Needs Information"
    | "In Progress"
    | "Resolved"
    | "Closed"
    | "Reopened";
  priority: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  createdAt: string;
  issueSummary: string;
  suggestedAction: string;
  reviewerNotes?: string;
  assignedTo?: string;
  stationLocation?: string;
  chargerId?: string;
  errorCode?: string;
  currentSoc?: string;
  locationConsent?: "GRANTED" | "DENIED" | "MANUAL" | "PENDING";
  manualLocation?: string;
  customerUpdate?: {
    resolvedAt?: string;
    staffName: string;
    resolutionSummary: string;
    nextStepGuidance: string;
    customerConfirmed?: boolean;
  };
  chatSnippet?: Array<{ sender: "CUSTOMER" | "AGENT" | "STAFF"; text: string; time: string }>;
  suggestedServicePoints?: ServicePointSeed[];
}

const SEED_SERVICE_POINTS: ServicePointSeed[] = [
  {
    id: "sp-01",
    name: "Xưởng Dịch vụ VinFast Times City",
    type: "SERVICE_WORKSHOP",
    address: "Tầng B2, Vincom Mega Mall Times City, Hai Bà Trưng, Hà Nội",
    distance: "1.2 km",
    hotline: "1900-232389",
    coords: { lat: 20.9951, lng: 105.8675 },
  },
  {
    id: "sp-02",
    name: "Xưởng Dịch vụ VinFast Trần Duy Hưng",
    type: "SERVICE_WORKSHOP",
    address: "Số 1 Trần Duy Hưng, Trung Hòa, Cầu Giấy, Hà Nội",
    distance: "3.5 km",
    hotline: "1900-232389",
    coords: { lat: 21.0094, lng: 105.7981 },
  },
  {
    id: "sp-03",
    name: "Trạm sạc Siêu Nhanh Vincom Metropolis (250kW)",
    type: "CHARGING_STATION",
    address: "29 Liễu Giai, Ngọc Khánh, Ba Đình, Hà Nội",
    distance: "2.8 km",
    hotline: "1900-232389",
    coords: { lat: 21.0315, lng: 105.8155 },
  },
  {
    id: "sp-04",
    name: "Đội Cứu hộ Phản ứng nhanh Cao Tốc Long Thành",
    type: "EXPRESSWAY_RESCUE",
    address: "Trạm điều hành nút giao Km 20, Cao tốc Long Thành - Dầu Giây",
    distance: "4.5 km",
    hotline: "1900-232389",
    coords: { lat: 10.7821, lng: 106.8423 },
  },
];

interface CuratedTopic {
  id: string;
  category: "CHARGING" | "DASHBOARD" | "WALLBOX" | "TIRE";
  categoryLabel: string;
  title: string;
  symptoms: string[];
  preparation: string[];
  suggestedPrompt: string;
  citationTitle: string;
  citationUrl: string;
}

const CURATED_TOPICS: CuratedTopic[] = [
  {
    id: "topic-01",
    category: "CHARGING",
    categoryLabel: "Sạc & Pin",
    title: "Trụ sạc báo đèn đỏ hoặc lỗi bắt tay BMS (Mã CC01 / 0x41)",
    symptoms: [
      "Cắm súng sạc nhưng màn hình xe không đếm giờ sạc",
      "Đèn LED trên đầu súng hoặc trụ sạc nháy đỏ liên tục",
      "Màn hình xe báo 'Communication Timeout with Charger'",
    ],
    preparation: [
      "Ghi nhận mã số trụ (ví dụ: P02, Trụ số 3)",
      "Kiểm tra mức pin còn lại (% SoC) trên táp-lô",
      "Chụp ảnh màn hình báo lỗi gửi vào Trợ lý Chat",
    ],
    suggestedPrompt: "Xe VF8 của tôi cắm sạc trụ P02 tại Vincom Metropolis báo lỗi CC01 đèn đỏ.",
    citationTitle: "Cẩm nang hướng dẫn sạc DC VinFast - Mục 4.2 Lỗi kết nối BMS",
    citationUrl: "https://vinfastauto.com/vn_vi/chinh-sach-va-bieu-phi-sac-pin-cong-cong",
  },
  {
    id: "topic-02",
    category: "DASHBOARD",
    categoryLabel: "Cảnh báo táp-lô",
    title: "Biểu tượng Con Rùa Vàng (Turtle Warning) & Giới hạn công suất",
    symptoms: [
      "Xuất hiện biểu tượng con rùa màu vàng trên màn hình người lái",
      "Xe tăng tốc chậm, tốc độ tối đa bị giới hạn dưới 40-50 km/h",
      "Pin xe dưới 10% hoặc nhiệt độ hệ thống pin quá cao",
    ],
    preparation: [
      "Bật đèn hazard và tấp xe vào làn đường an toàn bên phải",
      "Kiểm tra nhiệt độ động cơ/pin trên màn hình trung tâm",
      "Không cố gắng đạp thốc ga trên đường dốc",
    ],
    suggestedPrompt: "Xe VF5 của tôi hiện biểu tượng rùa vàng trên đường Nguyễn Trãi, pin còn dưới 10%.",
    citationTitle: "Sổ tay an toàn vận hành xe điện VinFast - Chương 6 Đèn chỉ báo táp-lô",
    citationUrl: "https://vinfastauto.com/vn_vi/chinh-sach-bao-hanh-va-cuu-ho-xe-dien",
  },
  {
    id: "topic-03",
    category: "WALLBOX",
    categoryLabel: "Sạc tại nhà",
    title: "Bộ sạc treo tường 7.4kW / 11kW tự ngắt sau 1-2 tiếng sạc",
    symptoms: [
      "Bộ sạc gia đình đang sạc bình thường thì đèn chuyển màu vàng cam",
      "Sờ vào thân dây sạc hoặc phích cắm thấy nóng ấm",
      "Aptomat (CB) nhánh sạc trong tủ điện gia đình bị nhảy",
    ],
    preparation: [
      "Kiểm tra thông gió khu vực lắp đặt bộ sạc",
      "Không dùng chung đường điện sạc với thiết bị tiêu thụ công suất lớn",
      "Hẹn kỹ thuật viên lưu động kiểm tra nhiệt độ dây nguồn",
    ],
    suggestedPrompt: "Bộ sạc tại nhà 7.4kW sạc xe VF9 được 2 tiếng thì tự động ngắt nguồn.",
    citationTitle: "Quy chuẩn lắp đặt và vận hành bộ sạc tại nhà VinFast Wallbox",
    citationUrl: "https://vinfastauto.com/vn_vi/huong-dan-su-dung-ung-dung-vinfast",
  },
  {
    id: "topic-04",
    category: "TIRE",
    categoryLabel: "Lốp xe & Khung gầm",
    title: "Cảnh báo áp suất lốp TPMS tụt dưới mức tiêu chuẩn (2.0 bar)",
    symptoms: [
      "Đèn cảnh báo lốp màu vàng sáng kèm âm thanh cảnh báo khi khởi động",
      "Màn hình xe hiển thị bánh xe màu đỏ/cam kèm chỉ số áp suất",
      "Cảm giác tay lái bị kéo lệch nhẹ về một phía",
    ],
    preparation: [
      "Quan sát bề mặt lốp xem có dính đinh hoặc dị vật",
      "Kiểm tra áp suất tiêu chuẩn ghi ở khung cửa ghế lái (thường là 2.3 - 2.4 bar)",
      "Định vị xưởng dịch vụ hoặc trạm sạc có máy bơm lốp gần nhất",
    ],
    suggestedPrompt: "Lốp xe VF6 báo tụt áp suất còn 1.8 bar, cần tìm xưởng VinFast gần nhất.",
    citationTitle: "Quy chuẩn bảo dưỡng lốp và cân bằng động xe điện VinFast",
    citationUrl: "https://vinfastauto.com/vn_vi/chinh-sach-bao-hanh-va-cuu-ho-xe-dien",
  },
];

const SAMPLE_CASES: Record<string, TrackedCase> = {
  "CASE-20260924-001": {
    id: "CASE-20260924-001",
    vehicleModel: "VF8 Plus",
    vehicleCode: "VF-SF-00231",
    status: "Staff Reviewing",
    priority: "HIGH",
    createdAt: "15:30 24/09/2026",
    issueSummary: "Trụ P02 Vincom Metropolis lỗi CC01 không sạc được DC",
    suggestedAction:
      "Kiểm tra tín hiệu handshake giao tiếp trụ P02 từ xa hoặc cử nhân viên trạm khởi động lại module giao thức trụ sạc.",
    reviewerNotes:
      "Cố vấn Lê Hoàng Quân đang phối hợp cùng Đội Vận Hành Trạm Sạc để ping kiểm tra cổng giao tiếp.",
    assignedTo: "Vũ Hoàng Long (Charging Ops)",
    stationLocation: "Vincom Metropolis Liễu Giai, Ba Đình, HN",
    chargerId: "Trụ P02 (DC 250kW)",
    errorCode: "CC01",
    currentSoc: "18%",
    locationConsent: "GRANTED",
    chatSnippet: [
      { sender: "CUSTOMER", text: "Xe VF8 của tôi không nhận sạc ở trạm Metropolis, trụ báo đèn đỏ.", time: "15:30" },
      { sender: "AGENT", text: "Dạ em đã ghi nhận xe VF8 lỗi cổng sạc trụ P02 và tạo hồ sơ hỗ trợ CASE-20260924-001.", time: "15:31" },
      { sender: "STAFF", text: "Kỹ thuật viên trạm đang kiểm tra module điều khiển trụ P02, anh/chị vui lòng chờ ít phút.", time: "15:35" },
    ],
    suggestedServicePoints: [SEED_SERVICE_POINTS[2], SEED_SERVICE_POINTS[1]],
  },
  "CASE-20260924-002": {
    id: "CASE-20260924-002",
    vehicleModel: "VF8 Eco",
    vehicleCode: "VF-SF-99120",
    status: "In Progress",
    priority: "CRITICAL",
    createdAt: "15:35 24/09/2026",
    issueSummary: "Cảnh báo rùa vàng & mất trợ lực lái nhẹ trên cao tốc Long Thành - Dầu Giây",
    suggestedAction:
      "Kích hoạt quy trình Cứu hộ Khẩn cấp 24/7. Hướng dẫn tài xế đứng sau rào hộ lan an toàn và cử xe cứu hộ gần nhất.",
    reviewerNotes:
      "Đội phản ứng nhanh Cao Tốc VinFast đã điều xe cẩu cứu hộ xuất phát từ nút giao Km 20.",
    assignedTo: "Đội Cứu hộ Cao Tốc Long Thành",
    stationLocation: "Km 24+500 Cao Tốc Long Thành - Dầu Giây",
    errorCode: "TURTLE_WARN",
    currentSoc: "34%",
    locationConsent: "GRANTED",
    chatSnippet: [
      { sender: "CUSTOMER", text: "Cứu tôi với, xe tôi đang chạy trên cao tốc Long Thành thì hiện rùa vàng, tay lái nặng hơn!", time: "15:35" },
      { sender: "AGENT", text: "Anh/chị hãy bình tĩnh, bật ngay đèn hazard và tấp xe vào làn khẩn cấp. Mọi người đã ra sau hộ lan an toàn chưa ạ?", time: "15:35" },
      { sender: "CUSTOMER", text: "Tôi vừa tấp vào lề rồi, mọi người đã xuống xe đứng sau rào chắn. Km 24 cao tốc.", time: "15:36" },
      { sender: "STAFF", text: "Đội cứu hộ cao tốc đã tiếp nhận tọa độ GPS khẩn cấp và đang di chuyển đến vị trí của anh/chị.", time: "15:37" },
    ],
    suggestedServicePoints: [SEED_SERVICE_POINTS[3]],
  },
  "CASE-20260924-003": {
    id: "CASE-20260924-003",
    vehicleModel: "VF5 Plus",
    vehicleCode: "VF-SF-00445",
    status: "Needs Information",
    priority: "MEDIUM",
    createdAt: "15:40 24/09/2026",
    issueSummary: "Đèn cảnh báo rùa vàng do dung lượng pin dưới 10% khi đang đi phố",
    suggestedAction:
      "Gửi tin nhắn yêu cầu khách chụp ảnh táp-lô và kiểm tra dung lượng pin còn lại trên ứng dụng VinFast.",
    reviewerNotes:
      "Đang chờ khách chụp lại ảnh đồng hồ táp-lô để xác nhận biểu tượng pin trước khi điều phối xưởng.",
    assignedTo: "Trần Đình Triển (Service Center)",
    stationLocation: "Đường Nguyễn Trãi, Thanh Xuân, HN",
    errorCode: "TURTLE_WARN",
    currentSoc: "< 10%",
    locationConsent: "PENDING",
    chatSnippet: [
      { sender: "CUSTOMER", text: "Màn hình xe VF5 của tôi tự nhiên hiện con rùa màu vàng là sao vậy em?", time: "15:40" },
      { sender: "AGENT", text: "Dạ biểu tượng rùa vàng là chế độ giới hạn công suất bảo vệ pin. Anh/chị kiểm tra vạch pin còn bao nhiêu % ạ?", time: "15:40" },
    ],
    suggestedServicePoints: [SEED_SERVICE_POINTS[1], SEED_SERVICE_POINTS[0]],
  },
  "CASE-20260924-004": {
    id: "CASE-20260924-004",
    vehicleModel: "VF9 Plus",
    vehicleCode: "VF-SF-00789",
    status: "In Progress",
    priority: "LOW",
    createdAt: "14:15 24/09/2026",
    issueSummary: "Bộ sạc tại nhà 7.4kW tự động ngắt sau 2 tiếng sạc ban đêm",
    suggestedAction:
      "Tư vấn kiểm tra aptomat nguồn và thông gió phòng kỹ thuật; hẹn kỹ thuật viên lưu động kiểm tra nhiệt độ dây nguồn.",
    reviewerNotes:
      "Đã lên lịch kỹ thuật viên lưu động ghé kiểm tra tiếp địa và đường dây vào 10:00 ngày mai.",
    assignedTo: "Vũ Hoàng Long (Charging Ops)",
    stationLocation: "Vinhomes Riverside, Long Biên, HN",
    chargerId: "Bộ sạc Wallbox 7.4kW",
    errorCode: "AC_THERMAL",
    currentSoc: "62%",
    locationConsent: "GRANTED",
    chatSnippet: [
      { sender: "CUSTOMER", text: "Bộ sạc tại nhà 7.4kW của tôi sạc được 2 tiếng thì tự ngắt, dây hơi ấm.", time: "14:15" },
      { sender: "STAFF", text: "Em đã phân công kỹ thuật viên lưu động ghé kiểm tra aptomat và đường dây vào sáng mai ạ.", time: "14:20" },
    ],
    suggestedServicePoints: [SEED_SERVICE_POINTS[0]],
  },
  "CASE-20260924-005": {
    id: "CASE-20260924-005",
    vehicleModel: "VF6 Plus",
    vehicleCode: "VF-SF-00612",
    status: "Resolved",
    priority: "HIGH",
    createdAt: "06:45 24/09/2026",
    issueSummary: "Cảnh báo áp suất lốp TPMS bánh sau bên phụ giảm dưới 2.0 bar",
    suggestedAction:
      "Khách đã ghé xưởng VinFast Trần Duy Hưng bơm lốp lên 2.4 bar tiêu chuẩn và cân bằng động.",
    reviewerNotes:
      "Khách đã hoàn tất nghiệm thu và hài lòng với chất lượng phục vụ.",
    assignedTo: "Trần Đình Triển (Cố vấn Dịch vụ)",
    stationLocation: "VinFast Trần Duy Hưng, Cầu Giấy, HN",
    errorCode: "TPMS_LOW",
    currentSoc: "78%",
    locationConsent: "GRANTED",
    customerUpdate: {
      resolvedAt: "08:15 24/09/2026",
      staffName: "Trần Đình Triển (Cố vấn Dịch vụ)",
      resolutionSummary:
        "Kỹ thuật viên xưởng Trần Duy Hưng đã kiểm tra lốp, vá lỗ đinh vi mô mặt gai và bơm khí Nitơ đạt chuẩn 2.4 bar.",
      nextStepGuidance:
        "Anh/chị có thể an tâm tiếp tục hành trình. Khuyến nghị kiểm tra lại áp suất lạnh sau 1 tuần.",
      customerConfirmed: false,
    },
    chatSnippet: [
      { sender: "CUSTOMER", text: "Lốp xe VF6 của tôi báo tụt còn 1.8 bar, có cần vào xưởng ngay không?", time: "06:45" },
      { sender: "STAFF", text: "Dạ xưởng Trần Duy Hưng cách anh 1.2km đã sẵn sàng cầu nâng hỗ trợ anh ngay ạ.", time: "06:47" },
      { sender: "STAFF", text: "Xe đã hoàn tất xử lý lốp và cân bằng động thành công!", time: "08:15" },
    ],
    suggestedServicePoints: [SEED_SERVICE_POINTS[1]],
  },
};

export default function TrackCasePage() {
  const { user, role, loginAs } = useAuth();

  // Tabs: "Yêu cầu của tôi" vs "Tình huống thường gặp"
  const [activeTab, setActiveTab] = useState<"my_cases" | "curated_topics">("my_cases");

  // Active selected case - Defaults immediately to the latest active case without needing manual search
  const [selectedCaseId, setSelectedCaseId] = useState<string>("CASE-20260924-001");
  const [currentCase, setCurrentCase] = useState<TrackedCase | null>(
    SAMPLE_CASES["CASE-20260924-001"]
  );

  // Quick search box toggle
  const [isSearchingCustom, setIsSearchingCustom] = useState<boolean>(false);
  const [customSearchId, setCustomSearchId] = useState<string>("");
  const [searchLoading, setSearchLoading] = useState<boolean>(false);
  const [copiedId, setCopiedId] = useState<boolean>(false);

  // Progressive Disclosure: Chat Snippet (default 1-2 messages)
  const [showAllChat, setShowAllChat] = useState<boolean>(false);

  // Progressive Disclosure: Tech Specs Detail Accordion
  const [showTechDetails, setShowTechDetails] = useState<boolean>(false);

  // Real cases from backend
  const [userCases, setUserCases] = useState<CustomerCaseItem[]>([]);

  // Customer Confirmation state (ADR-005)
  const [confirmStatus, setConfirmStatus] = useState<"IDLE" | "RESOLVED_CONFIRMED" | "REOPEN_REQUESTED">("IDLE");
  const [reopenReason, setReopenReason] = useState<string>("");
  const [isSubmittingConfirm, setIsSubmittingConfirm] = useState<boolean>(false);

  // Feedback state
  const [feedbackRating, setFeedbackRating] = useState<number>(5);
  const [feedbackComment, setFeedbackComment] = useState<string>("");
  const [feedbackSubmitted, setFeedbackSubmitted] = useState<boolean>(false);
  const [isSubmittingFeedback, setIsSubmittingFeedback] = useState<boolean>(false);

  // Location Consent state
  const [locationConsentChoice, setLocationConsentChoice] = useState<"GRANTED" | "MANUAL" | "SKIPPED" | null>(null);
  const [manualLocationInput, setManualLocationInput] = useState<string>("");

  // Curated Topics Tab: Search & Filter & Accordion
  const [topicSearch, setTopicSearch] = useState<string>("");
  const [topicCategory, setTopicCategory] = useState<string>("ALL");
  const [expandedTopicId, setExpandedTopicId] = useState<string | null>("topic-01");

  const [actionNotice, setActionNotice] = useState<string | null>(null);

  // RBAC: Chỉ truy xuất hồ sơ thực từ backend khi vai trò là CUSTOMER
  useEffect(() => {
    if (role === "CUSTOMER") {
      getCustomerCases()
        .then((res) => {
          if (res?.success && res.data?.cases && res.data.cases.length > 0) {
            setUserCases(res.data.cases);
          }
        })
        .catch(() => {});
    }
  }, [role]);

  const handleCopyId = (idToCopy: string) => {
    navigator.clipboard.writeText(idToCopy);
    setCopiedId(true);
    setTimeout(() => setCopiedId(false), 2000);
  };

  // Case switch handler
  const handleSelectCase = async (caseId: string) => {
    setSelectedCaseId(caseId);
    setActionNotice(null);
    setFeedbackSubmitted(false);
    setConfirmStatus("IDLE");
    setShowAllChat(false);

    if (SAMPLE_CASES[caseId]) {
      setCurrentCase(SAMPLE_CASES[caseId]);
      return;
    }

    // Try fetching from backend
    setSearchLoading(true);
    try {
      const res = await getCaseStatus(caseId);
      if (res?.success && res.data) {
        const d = res.data;
        setCurrentCase({
          id: d.case_id || caseId,
          vehicleModel: d.vehicle_model ? `VF${d.vehicle_model.replace(/^VF/i, "")}` : "VF8",
          vehicleCode: d.vehicle_code_mock || "VF-SF-00231",
          status: (d.status as TrackedCase["status"]) || "Staff Reviewing",
          priority: (d.priority as TrackedCase["priority"]) || "HIGH",
          createdAt: d.created_at ? new Date(d.created_at).toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" }) + " " + new Date(d.created_at).toLocaleDateString("vi-VN") : "Hôm nay",
          issueSummary: d.summary || "Hồ sơ sự cố tiếp nhận qua hệ thống VinFast ServiceFlow AI.",
          suggestedAction: d.suggested_action || "Đang được xử lý bởi Cố vấn Dịch vụ.",
          reviewerNotes: d.reviewer_notes || "Hồ sơ đang trong quy trình xử lý theo tiêu chuẩn xưởng.",
          assignedTo: "Cố vấn Kỹ thuật VinFast",
          stationLocation: "Trạm sạc / Xưởng dịch vụ VinFast gần nhất",
          suggestedServicePoints: SEED_SERVICE_POINTS.slice(0, 2),
        });
      }
    } catch {
      // Fallback
    } finally {
      setSearchLoading(false);
    }
  };

  const handleCustomSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const clean = customSearchId.trim().toUpperCase();
    if (!clean) return;
    handleSelectCase(clean);
    setIsSearchingCustom(false);
  };

  // Confirmation actions
  const handleConfirmResolved = () => {
    setIsSubmittingConfirm(true);
    setTimeout(() => {
      setIsSubmittingConfirm(false);
      setConfirmStatus("RESOLVED_CONFIRMED");
      if (currentCase) {
        setCurrentCase({ ...currentCase, status: "Closed" });
      }
      setActionNotice("Cảm ơn anh/chị đã xác nhận! Vui lòng dành 30 giây đánh giá chất lượng phục vụ.");
    }, 500);
  };

  const handleReopenSubmit = async () => {
    if (!currentCase) return;
    setIsSubmittingConfirm(true);
    setActionNotice(null);
    try {
      await reopenCustomerCase(currentCase.id);
      setConfirmStatus("REOPEN_REQUESTED");
      setCurrentCase({
        ...currentCase,
        status: "Reopened",
        reviewerNotes: reopenReason
          ? `Khách yêu cầu mở lại: "${reopenReason}". Chuyên viên sẽ liên hệ lại ngay.`
          : "Khách phản ánh sự cố chưa được khắc phục triệt để.",
      });
      setActionNotice("Hồ sơ đã được chuyển lại cho Cố vấn Dịch vụ để kiểm tra bổ sung!");
    } catch (err: any) {
      setActionNotice("Lưu ý: " + (err?.message || "Không thể mở lại hồ sơ lúc này."));
    } finally {
      setIsSubmittingConfirm(false);
    }
  };

  const handleSubmitFeedback = async (caseId: string) => {
    setIsSubmittingFeedback(true);
    setActionNotice(null);
    try {
      const res = await submitCustomerFeedback(caseId, {
        rating: feedbackRating,
        comment: feedbackComment,
      });
      if (res?.success) {
        setFeedbackSubmitted(true);
        setActionNotice("Cảm ơn anh/chị đã gửi đánh giá chất lượng dịch vụ!");
      }
    } catch (err: any) {
      setActionNotice("Lưu ý: " + (err?.message || "Lỗi khi gửi đánh giá."));
    } finally {
      setIsSubmittingFeedback(false);
    }
  };

  // Stepper calculations
  const getStatusStep = (status: TrackedCase["status"]) => {
    switch (status) {
      case "Staff Reviewing":
        return 1;
      case "Needs Information":
        return 2;
      case "In Progress":
      case "Reopened":
        return 3;
      case "Resolved":
      case "Closed":
        return 4;
      default:
        return 1;
    }
  };

  const getStatusBadge = (status: TrackedCase["status"]) => {
    switch (status) {
      case "Staff Reviewing":
        return "bg-blue-50 text-[#1E40AF] border-blue-200";
      case "Needs Information":
        return "bg-amber-50 text-amber-700 border-amber-200";
      case "In Progress":
        return "bg-sky-50 text-sky-700 border-sky-200";
      case "Reopened":
        return "bg-purple-50 text-purple-700 border-purple-200";
      case "Resolved":
      case "Closed":
        return "bg-emerald-50 text-emerald-700 border-emerald-200";
      default:
        return "bg-slate-100 text-slate-700 border-slate-200";
    }
  };

  const getStatusLabel = (status: TrackedCase["status"]) => {
    switch (status) {
      case "Staff Reviewing":
        return "Đang tiếp nhận";
      case "Needs Information":
        return "Cần làm rõ tin";
      case "In Progress":
        return "Đang xử lý";
      case "Reopened":
        return "Đã mở lại";
      case "Resolved":
        return "Đã xử lý xong";
      case "Closed":
        return "Đã hoàn tất";
      default:
        return status;
    }
  };

  // Next Step Prominent Guidance Message
  const getNextStepInfo = (c: TrackedCase) => {
    if (c.customerUpdate?.nextStepGuidance) {
      return {
        highlight: c.customerUpdate.nextStepGuidance,
        badge: "Chỉ dẫn từ Cố vấn",
        isAlert: false,
      };
    }
    if (c.id === "CASE-20260924-001") {
      return {
        highlight: "Kỹ thuật viên trạm đang kiểm tra trụ P02. Dự kiến phản hồi trong ít phút.",
        badge: "Bước tiếp theo",
        isAlert: false,
      };
    }
    if (c.id === "CASE-20260924-002") {
      return {
        highlight: "Đội cứu hộ cao tốc đã xuất phát từ Km 20 và đang di chuyển đến vị trí xe (Km 24+500). Vui lòng đứng an toàn sau hộ lan.",
        badge: "Khẩn cấp 24/7",
        isAlert: true,
      };
    }
    if (c.id === "CASE-20260924-003") {
      return {
        highlight: "Cố vấn dịch vụ cần anh/chị chụp ảnh màn hình táp-lô gửi qua Chat để xác minh biểu tượng pin.",
        badge: "Cần bổ sung ảnh",
        isAlert: true,
      };
    }
    if (c.id === "CASE-20260924-004") {
      return {
        highlight: "Kỹ thuật viên lưu động sẽ liên hệ và ghé kiểm tra aptomat sạc nhà vào 10:00 sáng mai.",
        badge: "Hẹn kỹ thuật viên",
        isAlert: false,
      };
    }
    if (c.id === "CASE-20260924-005") {
      return {
        highlight: "Sự cố đã được xưởng xử lý xong. Anh/chị vui lòng bấm 'Đã được hỗ trợ' để xác nhận và đóng ca.",
        badge: "Chờ xác nhận",
        isAlert: false,
      };
    }
    if (c.status === "Staff Reviewing") {
      return {
        highlight: "Chuyên viên dịch vụ đang phân tích dữ liệu sự cố. Dự kiến phản hồi trong 3–5 phút.",
        badge: "Bước tiếp theo",
        isAlert: false,
      };
    }
    if (c.status === "Needs Information") {
      return {
        highlight: "Vui lòng mở Trợ lý Chat gửi ảnh táp-lô hoặc xác nhận vị trí hỗ trợ.",
        badge: "Cần thông tin",
        isAlert: true,
      };
    }
    if (c.status === "In Progress") {
      return {
        highlight: c.suggestedAction || "Kỹ thuật viên đang trong quá trình kiểm tra xử lý thực địa.",
        badge: "Bước tiếp theo",
        isAlert: false,
      };
    }
    return {
      highlight: "Hồ sơ đã được xử lý hoàn tất. Chúc anh/chị vạn dặm bình an!",
      badge: "Hoàn tất",
      isAlert: false,
    };
  };

  // Filter curated topics
  const filteredTopics = useMemo(() => {
    return CURATED_TOPICS.filter((t) => {
      const matchCat = topicCategory === "ALL" || t.category === topicCategory;
      const matchSearch =
        !topicSearch.trim() ||
        t.title.toLowerCase().includes(topicSearch.toLowerCase()) ||
        t.symptoms.some((s) => s.toLowerCase().includes(topicSearch.toLowerCase())) ||
        t.preparation.some((p) => p.toLowerCase().includes(topicSearch.toLowerCase()));
      return matchCat && matchSearch;
    });
  }, [topicCategory, topicSearch]);

  const currentStep = currentCase ? getStatusStep(currentCase.status) : 1;
  const isCritical = currentCase?.priority === "CRITICAL";
  const nextStepData = currentCase ? getNextStepInfo(currentCase) : null;

  return (
    <div className="min-h-[calc(100vh-80px)] bg-[#F8FAFC] py-5 px-4 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-6xl space-y-4">
        {/* ─────────────────────────────────────────────────────────────
            1. COMPACT PAGE HEADER & CASE SELECTOR (Above-the-fold)
        ───────────────────────────────────────────────────────────── */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-slate-200/80 pb-3.5">
          <div className="flex items-center gap-3">
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
                  Yêu cầu của tôi
                </h1>
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold bg-blue-50 text-[#1E40AF] border border-blue-200/60">
                  {role === "GUEST" ? "Guest" : "Thời gian thực"}
                </span>
              </div>
              <p className="text-[12.5px] text-slate-500 mt-0.5">
                Theo dõi tiến trình xử lý sự cố xe và hỗ trợ kỹ thuật trực tiếp từ VinFast.
              </p>
            </div>
          </div>

          {/* Header Controls: Sub-Tabs & Case Switcher Dropdown */}
          <div className="flex flex-wrap items-center gap-2.5">
            {/* 2 Tabs: Yêu cầu của tôi vs Tình huống thường gặp */}
            <div className="inline-flex items-center p-0.5 bg-slate-200/70 rounded-xl text-[12px] font-medium">
              <button
                type="button"
                onClick={() => setActiveTab("my_cases")}
                className={`px-3 py-1.5 rounded-lg transition flex items-center gap-1.5 ${
                  activeTab === "my_cases"
                    ? "bg-white text-[#1E40AF] font-bold shadow-2xs"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                <Clock className="w-3.5 h-3.5" />
                <span>Hồ sơ xe</span>
              </button>

              <button
                type="button"
                onClick={() => setActiveTab("curated_topics")}
                className={`px-3 py-1.5 rounded-lg transition flex items-center gap-1.5 ${
                  activeTab === "curated_topics"
                    ? "bg-white text-[#1E40AF] font-bold shadow-2xs"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                <BookOpen className="w-3.5 h-3.5" />
                <span>Tình huống thường gặp</span>
              </button>
            </div>

            {/* Case Switcher: Khách đã đăng nhập (CUSTOMER) -> Tự hiện hồ sơ gần nhất & cho phép chuyển nhanh */}
            {activeTab === "my_cases" && role !== "GUEST" && (
              <div className="flex items-center gap-1.5">
                {!isSearchingCustom ? (
                  <div className="relative inline-flex items-center">
                    <select
                      value={selectedCaseId}
                      onChange={(e) => handleSelectCase(e.target.value)}
                      className="appearance-none bg-white border border-slate-200 rounded-xl py-1.5 pl-3 pr-8 text-[12px] font-semibold text-slate-800 shadow-2xs hover:border-slate-300 focus:outline-none focus:ring-2 focus:ring-[#1E40AF]/20 cursor-pointer"
                    >
                      <option value="CASE-20260924-001">001 · Lỗi sạc CC01 (VF8 Plus)</option>
                      <option value="CASE-20260924-002">002 · Cứu hộ cao tốc (VF8 Eco)</option>
                      <option value="CASE-20260924-003">003 · Rùa vàng & Pin (VF5 Plus)</option>
                      <option value="CASE-20260924-004">004 · Sạc tại nhà 7.4kW (VF9 Plus)</option>
                      <option value="CASE-20260924-005">005 · Lỗi áp suất lốp (VF6 Plus)</option>
                      {userCases
                        .filter((uc) => !SAMPLE_CASES[uc.id])
                        .map((uc) => (
                          <option key={uc.id} value={uc.id}>
                            {uc.id} · {uc.status}
                          </option>
                        ))}
                    </select>
                    <ChevronDown className="w-3.5 h-3.5 text-slate-400 absolute right-2.5 pointer-events-none" />

                    <button
                      type="button"
                      onClick={() => setIsSearchingCustom(true)}
                      className="ml-1.5 p-1.5 rounded-lg border border-slate-200 bg-white text-slate-500 hover:text-slate-800 hover:bg-slate-50 shadow-2xs transition"
                      title="Tìm mã hồ sơ khác"
                    >
                      <Search className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ) : (
                  <form onSubmit={handleCustomSearchSubmit} className="flex items-center gap-1">
                    <input
                      type="text"
                      value={customSearchId}
                      onChange={(e) => setCustomSearchId(e.target.value)}
                      placeholder="Mã hồ sơ (VD: CASE-001)..."
                      className="w-40 bg-white border border-slate-300 rounded-xl px-2.5 py-1 text-[12px] font-mono font-medium text-slate-900 focus:outline-none focus:ring-2 focus:ring-[#1E40AF]/20"
                      autoFocus
                    />
                    <button
                      type="submit"
                      disabled={searchLoading}
                      className="px-2.5 py-1 rounded-xl bg-[#1E40AF] text-white text-[12px] font-semibold hover:bg-[#1D4ED8]"
                    >
                      {searchLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : "Tìm"}
                    </button>
                    <button
                      type="button"
                      onClick={() => setIsSearchingCustom(false)}
                      className="px-2 py-1 text-slate-500 hover:text-slate-700 text-[12px]"
                    >
                      ✕
                    </button>
                  </form>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Global Action / Flash Notice */}
        {actionNotice && (
          <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-2.5 text-[12.5px] font-medium text-emerald-800 flex items-center justify-between shadow-2xs animate-fadeIn">
            <span className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
              {actionNotice}
            </span>
            <button
              type="button"
              onClick={() => setActionNotice(null)}
              className="text-emerald-700 hover:text-emerald-950 text-[12px] font-bold ml-2"
            >
              ✕
            </button>
          </div>
        )}

        {/* =============================================================
            TAB 1: YÊU CẦU CỦA TÔI
        ============================================================= */}
        {/* Chế độ GUEST: Hiển thị Auth Gate tuân thủ nghiêm ngặt ADR-005 và RBAC */}
        {activeTab === "my_cases" && role === "GUEST" && (
          <div className="bg-white rounded-3xl border border-slate-200/90 shadow-sm p-6 sm:p-10 text-center max-w-2xl mx-auto my-6 animate-fadeIn space-y-6">
            <div className="w-14 h-14 rounded-2xl bg-blue-50 border border-blue-200 flex items-center justify-center mx-auto text-[#1E40AF]">
              <ShieldAlert className="w-7 h-7" />
            </div>

            <div className="space-y-2">
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-100 text-slate-700 text-[11.5px] font-semibold">
                <Car className="w-3.5 h-3.5 text-[#1E40AF]" />
                Chế độ Guest
              </span>
              <h2 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
                Yêu cầu đăng nhập tài khoản Khách hàng
              </h2>
              <p className="text-[13px] text-slate-500 max-w-lg mx-auto leading-relaxed">
                Theo tiêu chuẩn phân quyền & bảo mật dữ liệu xe (ADR-005), hồ sơ kỹ thuật và tiến trình xử lý sự cố chỉ dành riêng cho Khách hàng sở hữu xe. Bạn có thể tra cứu cẩm nang công khai hoặc đăng nhập để theo dõi hồ sơ.
              </p>
            </div>

            {/* 3 tính năng của Customer */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-left pt-1">
              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/70 text-[12px] space-y-1">
                <CheckCircle2 className="w-4 h-4 text-[#1E40AF]" />
                <strong className="block text-slate-900 font-semibold">Tiến độ 4 bước</strong>
                <span className="text-slate-500 text-[11.5px] leading-snug block">Cập nhật trạng thái thời gian thực từ xưởng dịch vụ</span>
              </div>
              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/70 text-[12px] space-y-1">
                <MessageSquare className="w-4 h-4 text-[#1E40AF]" />
                <strong className="block text-slate-900 font-semibold">Chỉ dẫn kỹ thuật</strong>
                <span className="text-slate-500 text-[11.5px] leading-snug block">Trao đổi và nhận hướng dẫn xử lý từ Cố vấn dịch vụ</span>
              </div>
              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/70 text-[12px] space-y-1">
                <RotateCcw className="w-4 h-4 text-[#1E40AF]" />
                <strong className="block text-slate-900 font-semibold">Nghiệm thu xe</strong>
                <span className="text-slate-500 text-[11.5px] leading-snug block">Xác nhận hoàn tất hoặc mở lại hồ sơ (Reopen) khi cần</span>
              </div>
            </div>

            {/* 2 CTA Buttons */}
            <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
              <button
                type="button"
                onClick={() => loginAs("CUSTOMER")}
                className="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-xl bg-[#1E40AF] hover:bg-[#1D4ED8] px-5 py-2.5 text-[13px] font-semibold text-white shadow-2xs transition active:scale-[0.98]"
              >
                <span>Đăng nhập tài khoản Khách hàng (Demo)</span>
                <ArrowRight className="w-4 h-4" />
              </button>

              <button
                type="button"
                onClick={() => setActiveTab("curated_topics")}
                className="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 px-4 py-2.5 text-[13px] font-semibold text-slate-700 transition"
              >
                <BookOpen className="w-4 h-4 text-slate-500" />
                <span>Xem Tình huống thường gặp</span>
              </button>
            </div>
          </div>
        )}

        {/* Chế độ CUSTOMER: BỐ CỤC 2 CỘT CHUẨN TRÊN DESKTOP */}
        {activeTab === "my_cases" && role !== "GUEST" && currentCase && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start animate-fadeIn">
            {/* ─────────────────────────────────────────────────────────
                CỘT TRÁI (8/12): LUỒNG TIẾN TRÌNH & HÀNH ĐỘNG CHÍNH
            ───────────────────────────────────────────────────────── */}
            <div className="lg:col-span-8 space-y-4">
              {/* Card Tiến Trình Hồ Sơ */}
              <div className="bg-white rounded-2xl shadow-xs border border-slate-200/80 overflow-hidden">
                {/* 1. Tiêu đề hồ sơ + Trạng thái */}
                <div className="p-4 sm:p-5 border-b border-slate-100 space-y-2">
                  <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                    <div className="space-y-1">
                      <h2 className="text-[17px] sm:text-[19px] font-bold text-slate-900 leading-snug">
                        {currentCase.issueSummary}
                      </h2>

                      <div className="flex items-center gap-2 text-[12px] text-slate-500 flex-wrap">
                        <button
                          type="button"
                          onClick={() => handleCopyId(currentCase.id)}
                          className="font-mono text-slate-700 bg-slate-100 hover:bg-slate-200 px-2 py-0.5 rounded-md inline-flex items-center gap-1 transition"
                          title="Sao chép mã hồ sơ"
                        >
                          <span>{currentCase.id}</span>
                          {copiedId ? (
                            <CheckCheck className="w-3 h-3 text-emerald-600" />
                          ) : (
                            <Copy className="w-3 h-3 text-slate-400" />
                          )}
                        </button>
                        <span>·</span>
                        <span className="font-semibold text-slate-700 flex items-center gap-1">
                          <Car className="w-3.5 h-3.5 text-[#1E40AF]" />
                          {currentCase.vehicleModel}
                        </span>
                        <span>·</span>
                        <span className="text-slate-400 flex items-center gap-1">
                          <Clock className="w-3.5 h-3.5" />
                          {currentCase.createdAt}
                        </span>
                      </div>
                    </div>

                    {/* Status Badge */}
                    <div className="flex items-center gap-2 shrink-0">
                      <span
                        className={`rounded-full px-3 py-1 text-[12px] font-semibold border ${getStatusBadge(
                          currentCase.status
                        )}`}
                      >
                        {getStatusLabel(currentCase.status)}
                      </span>

                      {isCritical && (
                        <span className="rounded-full bg-red-50 text-red-700 border border-red-200 px-2.5 py-1 text-[11px] font-bold uppercase tracking-wider animate-pulse">
                          Cứu hộ khẩn
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                {/* 2. Stepper 4 bước với thanh tiến trình liên tục */}
                <div className="p-4 sm:p-5 bg-slate-50/50 space-y-4">
                  <div className="relative pt-1 pb-1">
                    {/* Continuous Track */}
                    <div className="absolute top-[20px] left-[10%] right-[10%] h-[2.5px] bg-slate-200 -z-0" />
                    <div
                      className="absolute top-[20px] left-[10%] h-[2.5px] bg-emerald-500 transition-all duration-300 -z-0"
                      style={{
                        width: `${Math.max(0, Math.min(80, ((currentStep - 1) / 3) * 80))}%`,
                      }}
                    />

                    <div className="relative z-10 grid grid-cols-4 gap-1 text-center">
                      {[
                        { step: 1, title: "Tiếp nhận", sub: "Ghi nhận ca" },
                        { step: 2, title: "Xác minh", sub: "Làm rõ dữ kiện" },
                        { step: 3, title: "Xử lý", sub: "Kỹ thuật / Xưởng" },
                        { step: 4, title: "Hoàn tất", sub: "Nghiệm thu ca" },
                      ].map((s) => {
                        const isPassed = currentStep > s.step;
                        const isCurrent = currentStep === s.step;

                        return (
                          <div key={s.step} className="flex flex-col items-center">
                            <div
                              className={`flex h-7 w-7 sm:h-8 sm:w-8 items-center justify-center rounded-full text-[11.5px] font-bold transition-all ${
                                isPassed
                                  ? "bg-emerald-500 text-white shadow-2xs"
                                  : isCurrent
                                  ? "bg-[#1E40AF] text-white ring-4 ring-blue-100 shadow-2xs"
                                  : "bg-white text-slate-400 border border-slate-200"
                              }`}
                            >
                              {isPassed ? <Check className="h-4 w-4" /> : s.step}
                            </div>

                            <span
                              className={`mt-1.5 font-semibold text-[11.5px] sm:text-[12px] leading-tight ${
                                isCurrent ? "text-[#1E40AF]" : isPassed ? "text-slate-800" : "text-slate-400"
                              }`}
                            >
                              {s.title}
                            </span>
                            <span className="hidden sm:inline text-[10.5px] text-slate-400 mt-0.5">
                              {s.sub}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* 3. ĐIỂM NỔI BẬT: BƯỚC TIẾP THEO (Above-the-fold Immediate Answer) */}
                  {nextStepData && (
                    <div
                      className={`rounded-xl p-3.5 text-[13px] border flex items-start gap-2.5 transition ${
                        nextStepData.isAlert
                          ? "bg-red-50/90 border-red-200 text-red-900"
                          : "bg-blue-50/90 border-blue-200/80 text-blue-950"
                      }`}
                    >
                      <Sparkles
                        className={`w-4 h-4 shrink-0 mt-0.5 ${
                          nextStepData.isAlert ? "text-red-600" : "text-[#1E40AF]"
                        }`}
                      />
                      <div className="flex-1 space-y-0.5">
                        <div className="flex items-center gap-1.5">
                          <span
                            className={`font-bold text-[12px] uppercase tracking-wide px-1.5 py-0.2 rounded ${
                              nextStepData.isAlert
                                ? "bg-red-200 text-red-800"
                                : "bg-blue-200 text-[#1E40AF]"
                            }`}
                          >
                            {nextStepData.badge}
                          </span>
                        </div>
                        <p className="font-medium leading-relaxed pt-0.5">{nextStepData.highlight}</p>
                      </div>
                    </div>
                  )}
                </div>

                {/* 4. CUSTOMER UPDATE TỪ CỐ VẤN DỊCH VỤ (KHI CÓ KẾT QUẢ / NGHIỆM THU - ADR-005) */}
                {currentCase.customerUpdate && (
                  <div className="p-4 sm:p-5 border-t border-slate-100 bg-emerald-50/30 space-y-3">
                    <div className="flex items-center justify-between text-[12px]">
                      <span className="font-bold text-emerald-900 flex items-center gap-1.5">
                        <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                        Kết quả giải quyết từ Cố vấn Dịch vụ
                      </span>
                      <span className="text-[11px] text-emerald-700 font-mono">
                        {currentCase.customerUpdate.resolvedAt}
                      </span>
                    </div>

                    <div className="bg-white p-3.5 rounded-xl border border-emerald-200/80 shadow-2xs space-y-2 text-[12.5px]">
                      <p className="text-slate-800 leading-relaxed">
                        {currentCase.customerUpdate.resolutionSummary}
                      </p>
                      <div className="pt-2 border-t border-slate-100 text-[12px] text-slate-600 flex items-start gap-1.5">
                        <strong className="text-emerald-800 shrink-0">Chỉ dẫn tiếp theo:</strong>
                        <span>{currentCase.customerUpdate.nextStepGuidance}</span>
                      </div>
                    </div>

                    {/* NÚT XÁC NHẬN CỦA KHÁCH HÀNG (ADR-005) */}
                    {confirmStatus === "IDLE" && currentCase.status === "Resolved" && (
                      <div className="pt-1 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2.5 bg-white p-3 rounded-xl border border-emerald-200">
                        <span className="text-[12px] text-slate-700 font-medium">
                          Anh/chị đã hài lòng với kết quả xử lý của kỹ thuật viên chưa?
                        </span>

                        <div className="flex items-center gap-2 shrink-0">
                          <button
                            type="button"
                            disabled={isSubmittingConfirm}
                            onClick={handleConfirmResolved}
                            className="inline-flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-[12px] font-semibold transition active:scale-[0.98] disabled:opacity-50"
                          >
                            <ThumbsUp className="w-3.5 h-3.5" />
                            <span>Đã được hỗ trợ</span>
                          </button>

                          <button
                            type="button"
                            disabled={isSubmittingConfirm}
                            onClick={() => setConfirmStatus("REOPEN_REQUESTED")}
                            className="inline-flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-xl border border-amber-300 bg-amber-50 hover:bg-amber-100 text-amber-800 text-[12px] font-semibold transition active:scale-[0.98] disabled:opacity-50"
                          >
                            <RotateCcw className="w-3.5 h-3.5" />
                            <span>Vẫn chưa giải quyết</span>
                          </button>
                        </div>
                      </div>
                    )}

                    {/* Form mở lại ca nếu bấm "Vẫn chưa giải quyết" */}
                    {confirmStatus === "REOPEN_REQUESTED" && currentCase.status !== "Reopened" && (
                      <div className="bg-white p-3.5 rounded-xl border border-amber-200 space-y-2 animate-fadeIn">
                        <label className="block text-[12px] font-semibold text-amber-900">
                          Vui lòng cho biết vấn đề xe chưa khắc phục để Cố vấn kiểm tra lại:
                        </label>
                        <textarea
                          rows={2}
                          value={reopenReason}
                          onChange={(e) => setReopenReason(e.target.value)}
                          placeholder="VD: Đèn cảnh báo vẫn còn sáng lại khi xe di chuyển..."
                          className="w-full text-[12px] p-2.5 rounded-lg border border-amber-300 bg-white text-slate-900 focus:outline-none focus:ring-2 focus:ring-amber-400"
                        />
                        <div className="flex justify-end gap-2">
                          <button
                            type="button"
                            onClick={() => setConfirmStatus("IDLE")}
                            className="px-3 py-1 rounded-lg text-[12px] text-slate-600 hover:bg-slate-100"
                          >
                            Hủy
                          </button>
                          <button
                            type="button"
                            disabled={isSubmittingConfirm}
                            onClick={handleReopenSubmit}
                            className="px-3 py-1 rounded-lg bg-amber-600 hover:bg-amber-700 text-white text-[12px] font-semibold"
                          >
                            {isSubmittingConfirm ? "Đang gửi..." : "Gửi yêu cầu kiểm tra lại"}
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* 5. CẬP NHẬT GẦN NHẤT & LỊCH SỬ CHAT (CHỈ HIỆN 1-2 TIN GẦN NHẤT) */}
                {currentCase.chatSnippet && currentCase.chatSnippet.length > 0 && (
                  <div className="p-4 sm:p-5 border-t border-slate-100 space-y-2.5">
                    <div className="flex items-center justify-between text-[12px]">
                      <span className="font-semibold text-slate-800 flex items-center gap-1.5">
                        <MessageSquare className="w-3.5 h-3.5 text-[#1E40AF]" />
                        Cập nhật trao đổi gần nhất
                      </span>

                      {currentCase.chatSnippet.length > 2 && (
                        <button
                          type="button"
                          onClick={() => setShowAllChat(!showAllChat)}
                          className="text-[11.5px] text-[#1E40AF] hover:underline font-medium inline-flex items-center gap-0.5"
                        >
                          <span>{showAllChat ? "Thu gọn trao đổi" : `Xem toàn bộ trao đổi (${currentCase.chatSnippet.length})`}</span>
                          {showAllChat ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                        </button>
                      )}
                    </div>

                    <div className="space-y-2 bg-slate-50/80 p-3 rounded-xl border border-slate-200/60">
                      {(showAllChat
                        ? currentCase.chatSnippet
                        : currentCase.chatSnippet.slice(-2)
                      ).map((msg, idx) => (
                        <div key={idx} className="text-[12.5px] flex items-start gap-2">
                          <span
                            className={`px-1.5 py-0.2 rounded text-[10px] font-bold font-mono shrink-0 mt-0.5 ${
                              msg.sender === "CUSTOMER"
                                ? "bg-blue-100 text-[#1E40AF]"
                                : msg.sender === "STAFF"
                                ? "bg-purple-100 text-purple-700"
                                : "bg-emerald-100 text-emerald-800"
                            }`}
                          >
                            {msg.sender === "CUSTOMER" ? "BẠN" : msg.sender === "STAFF" ? "KTV" : "AI"}
                          </span>
                          <p className="text-slate-800 flex-1 leading-relaxed">{msg.text}</p>
                          <span className="text-[10px] text-slate-400 font-mono shrink-0">{msg.time}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* 6. HAI NÚT HÀNH ĐỘNG CHÍNH CỦA KHÁCH Ở CÙNG MỘT HÀNG */}
                <div className="p-4 sm:p-5 border-t border-slate-100 bg-white flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
                  <a
                    href="tel:1900232389"
                    className="inline-flex items-center justify-center gap-1.5 rounded-xl border border-slate-300 hover:border-red-300 bg-white hover:bg-red-50/50 px-4 py-2.5 text-[12.5px] font-semibold text-slate-700 hover:text-red-700 transition"
                  >
                    <PhoneCall className="h-3.5 w-3.5 text-red-600" />
                    <span>Hotline: 1900-232389</span>
                  </a>

                  <Link
                    href="/chat"
                    className="inline-flex items-center justify-center gap-2 rounded-xl bg-[#1E40AF] hover:bg-[#1D4ED8] px-5 py-2.5 text-[13px] font-semibold text-white shadow-xs transition active:scale-[0.98]"
                  >
                    <MessageSquare className="h-4 w-4" />
                    <span>Tiếp tục trao đổi trong Trợ lý Chat</span>
                  </Link>
                </div>

                {/* 7. ĐÁNH GIÁ 5 SAO KHI CA HOÀN TẤT */}
                {(currentCase.status === "Closed" || confirmStatus === "RESOLVED_CONFIRMED") && (
                  <div className="p-4 sm:p-5 bg-slate-50/70 border-t border-slate-100 space-y-3 animate-fadeIn">
                    <div className="flex items-center gap-2">
                      <Star className="h-4 w-4 text-amber-500 fill-amber-500" />
                      <h3 className="text-[13px] font-bold text-slate-900">
                        Đánh giá chất lượng hỗ trợ
                      </h3>
                    </div>

                    {feedbackSubmitted ? (
                      <div className="rounded-xl bg-emerald-50 border border-emerald-200 p-2.5 text-[12.5px] font-semibold text-emerald-800 flex items-center gap-2">
                        <Check className="h-4 w-4 text-emerald-600" />
                        Đã ghi nhận đánh giá của anh/chị. Cảm ơn anh/chị đã đóng góp ý kiến!
                      </div>
                    ) : (
                      <div className="space-y-2.5">
                        <div className="flex items-center gap-1.5">
                          {[1, 2, 3, 4, 5].map((star) => (
                            <button
                              key={star}
                              type="button"
                              onClick={() => setFeedbackRating(star)}
                              className="p-1 text-amber-400 hover:scale-110 transition"
                            >
                              <Star
                                className={`h-5 w-5 ${
                                  star <= feedbackRating
                                    ? "fill-amber-400 text-amber-400"
                                    : "text-slate-300"
                                }`}
                              />
                            </button>
                          ))}
                          <span className="ml-2 text-[12px] font-semibold text-slate-700">
                            {feedbackRating === 5
                              ? "Rất hài lòng"
                              : feedbackRating === 4
                              ? "Hài lòng"
                              : feedbackRating === 3
                              ? "Bình thường"
                              : "Chưa hài lòng"}
                          </span>
                        </div>

                        <textarea
                          value={feedbackComment}
                          onChange={(e) => setFeedbackComment(e.target.value)}
                          placeholder="Ý kiến đóng góp thêm về tốc độ và chất lượng phục vụ (tùy chọn)..."
                          rows={2}
                          className="w-full rounded-xl border border-slate-200 bg-white p-2.5 text-[12px] text-slate-900 focus:border-[#1E40AF] focus:outline-none"
                        />

                        <div className="flex justify-end">
                          <button
                            type="button"
                            disabled={isSubmittingFeedback}
                            onClick={() => handleSubmitFeedback(currentCase.id)}
                            className="rounded-xl bg-emerald-600 hover:bg-emerald-700 px-4 py-1.5 text-[12px] font-semibold text-white transition disabled:opacity-60"
                          >
                            {isSubmittingFeedback ? "Đang gửi..." : "Gửi đánh giá"}
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* ─────────────────────────────────────────────────────────
                CỘT PHẢI (4/12): THÔNG TIN THAM CHIẾU (GỌN GÀNG, SÁT NHAU)
            ───────────────────────────────────────────────────────── */}
            <div className="lg:col-span-4 space-y-4">
              {/* Card 1: Thông Tin Xe & Dữ Kiện Kỹ Thuật (Key-Value Sát Nhau) */}
              <div className="bg-white rounded-2xl shadow-xs border border-slate-200/80 p-4 sm:p-5 space-y-3">
                <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
                  <h3 className="text-[13.5px] font-bold text-slate-900 flex items-center gap-1.5">
                    <Car className="w-4 h-4 text-[#1E40AF]" />
                    <span>Thông tin xe & Dữ kiện</span>
                  </h3>
                  <span className="text-[11px] font-mono text-slate-400">
                    {currentCase.vehicleCode}
                  </span>
                </div>

                {/* Key-Value Pairs đặt sát nhau, không kéo ngang tạo khoảng trống */}
                <div className="space-y-2 text-[12.5px]">
                  <div className="flex items-center justify-between py-1 border-b border-slate-50">
                    <span className="text-slate-500">Dòng xe:</span>
                    <span className="font-semibold text-slate-900">{currentCase.vehicleModel}</span>
                  </div>

                  <div className="flex items-center justify-between py-1 border-b border-slate-50">
                    <span className="text-slate-500">Mức pin (SoC):</span>
                    <span
                      className={`font-semibold ${
                        String(currentCase.currentSoc).includes("< 10%") ||
                        String(currentCase.currentSoc).includes("18%")
                          ? "text-amber-600"
                          : "text-slate-900"
                      }`}
                    >
                      {currentCase.currentSoc || "Đang xác minh"}
                    </span>
                  </div>

                  <div className="flex items-center justify-between py-1 border-b border-slate-50">
                    <span className="text-slate-500">Mã lỗi hệ thống:</span>
                    {currentCase.errorCode ? (
                      <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded font-mono font-bold text-[11.5px] bg-red-50 text-red-700 border border-red-200">
                        <AlertCircle className="w-3 h-3 text-red-600" />
                        {currentCase.errorCode}
                      </span>
                    ) : (
                      <span className="text-slate-400 font-medium">Bình thường</span>
                    )}
                  </div>

                  {currentCase.chargerId && (
                    <div className="flex items-center justify-between py-1 border-b border-slate-50">
                      <span className="text-slate-500">Trụ sạc:</span>
                      <span className="font-medium text-slate-800 text-right truncate max-w-[170px]">
                        {currentCase.chargerId}
                      </span>
                    </div>
                  )}

                  {/* Mục phụ cho vào "Xem thêm" */}
                  {showTechDetails && (
                    <div className="pt-1.5 space-y-2 text-[12px] text-slate-600 bg-slate-50/70 p-2.5 rounded-xl border border-slate-100 animate-fadeIn">
                      <div className="flex items-center justify-between">
                        <span>Chia sẻ GPS:</span>
                        <span className="font-medium">
                          {currentCase.locationConsent === "GRANTED"
                            ? "Đã cấp quyền"
                            : currentCase.locationConsent === "MANUAL"
                            ? "Nhập thủ công"
                            : "Chưa bật"}
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span>Chuyên viên phụ trách:</span>
                        <span className="font-medium text-slate-800 truncate max-w-[150px]">
                          {currentCase.assignedTo || "Đội hỗ trợ VinFast"}
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span>Thời gian tạo:</span>
                        <span className="font-mono text-slate-500">{currentCase.createdAt}</span>
                      </div>
                    </div>
                  )}

                  <button
                    type="button"
                    onClick={() => setShowTechDetails(!showTechDetails)}
                    className="w-full text-center text-[11.5px] text-[#1E40AF] hover:underline font-medium pt-1 block"
                  >
                    {showTechDetails ? "Thu gọn thông số ▲" : "Xem thêm thông số phụ ▼"}
                  </button>
                </div>
              </div>

              {/* Card 2: Trạm & Điểm Dịch Vụ Phụ Trách (Chỉ đường Google Maps) */}
              <div className="bg-white rounded-2xl shadow-xs border border-slate-200/80 p-4 sm:p-5 space-y-3">
                <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
                  <h3 className="text-[13.5px] font-bold text-slate-900 flex items-center gap-1.5">
                    <MapPin className="w-4 h-4 text-[#1E40AF]" />
                    <span>Trạm / Điểm hỗ trợ</span>
                  </h3>
                  <span className="text-[11px] text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full font-semibold">
                    Đã định vị
                  </span>
                </div>

                <div className="space-y-2 text-[12.5px]">
                  <div>
                    <h4 className="font-semibold text-slate-900 leading-snug">
                      {currentCase.stationLocation || "Trạm sạc Vincom Metropolis"}
                    </h4>
                    <p className="text-[11.5px] text-slate-500 mt-0.5 leading-relaxed">
                      {currentCase.suggestedServicePoints?.[0]?.address ||
                        "29 Liễu Giai, Ngọc Khánh, Ba Đình, Hà Nội"}
                    </p>
                  </div>

                  <div className="pt-2 flex items-center justify-between">
                    <span className="text-[11px] text-slate-400 font-mono">
                      Khoảng cách: {currentCase.suggestedServicePoints?.[0]?.distance || "1.2 km"}
                    </span>

                    <a
                      href={`https://maps.google.com/?q=${encodeURIComponent(
                        currentCase.stationLocation || "Vincom Metropolis"
                      )}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 px-3 py-1.5 rounded-xl bg-blue-50 text-[#1E40AF] hover:bg-blue-100 text-[11.5px] font-semibold transition"
                    >
                      <Navigation className="w-3 h-3" />
                      <span>Chỉ đường</span>
                    </a>
                  </div>
                </div>
              </div>

              {/* Card 3: Hotline Khẩn Cấp (Thu gọn duy nhất 1 lần ở cột phải) */}
              <div className="rounded-2xl border border-red-200/80 bg-red-50/50 p-4 space-y-2">
                <div className="flex items-center gap-2">
                  <PhoneCall className="w-4 h-4 text-red-600" />
                  <span className="text-[12px] font-bold text-red-900 uppercase tracking-wide">
                    Hỗ trợ khẩn cấp 24/7
                  </span>
                </div>

                <p className="text-[12px] text-slate-600">
                  Nếu xe gặp sự cố nguy hiểm trên đường hoặc cần cứu hộ khẩn cấp:
                </p>

                <a
                  href="tel:1900232389"
                  className="block w-full text-center py-2 px-3 rounded-xl bg-red-600 hover:bg-red-700 text-white font-bold text-[13px] shadow-2xs transition"
                >
                  ☎ 1900-232389
                </a>
              </div>
            </div>
          </div>
        )}

        {/* =============================================================
            TAB 2: TÌNH HUỐNG THƯỜNG GẶP (ACCORDION GỌN + TÌM KIẾM & LỌC)
        ============================================================= */}
        {activeTab === "curated_topics" && (
          <div className="space-y-4 animate-fadeIn">
            {/* Thanh Tìm Kiếm & Chip Lọc Nhóm */}
            <div className="bg-white p-4 rounded-2xl border border-slate-200/80 shadow-xs space-y-3">
              <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
                <div className="relative flex-1">
                  <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    value={topicSearch}
                    onChange={(e) => setTopicSearch(e.target.value)}
                    placeholder="Tìm theo triệu chứng, mã lỗi (VD: CC01, rùa vàng, lốp xe, sạc nhà)..."
                    className="w-full pl-9 pr-3 py-2 rounded-xl bg-slate-50 border border-slate-200 text-[12.5px] text-slate-900 focus:outline-none focus:bg-white focus:border-[#1E40AF]"
                  />
                </div>

                <div className="text-[11.5px] text-slate-500 shrink-0">
                  Nguồn: <strong className="text-slate-700">Tài liệu chính thức VinFast</strong>
                </div>
              </div>

              {/* Chips Lọc Nhóm Tình Huống */}
              <div className="flex items-center gap-1.5 flex-wrap pt-1 border-t border-slate-100">
                {[
                  { id: "ALL", label: "Tất cả" },
                  { id: "CHARGING", label: "Sạc & Pin" },
                  { id: "DASHBOARD", label: "Cảnh báo táp-lô" },
                  { id: "WALLBOX", label: "Sạc tại nhà" },
                  { id: "TIRE", label: "Lốp & Khung gầm" },
                ].map((c) => (
                  <button
                    key={c.id}
                    type="button"
                    onClick={() => setTopicCategory(c.id)}
                    className={`px-3 py-1 rounded-lg text-[12px] font-medium transition ${
                      topicCategory === c.id
                        ? "bg-[#1E40AF] text-white font-semibold"
                        : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                    }`}
                  >
                    {c.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Danh Sách Accordion (Gọn, 1 Dòng Mở Khi Bấm) */}
            <div className="space-y-2.5">
              {filteredTopics.map((topic) => {
                const isOpen = expandedTopicId === topic.id;

                return (
                  <div
                    key={topic.id}
                    className="bg-white rounded-2xl border border-slate-200/80 shadow-xs overflow-hidden transition"
                  >
                    {/* Header Row: Tiêu đề + Nhãn nhóm + Mũi tên */}
                    <button
                      type="button"
                      onClick={() => setExpandedTopicId(isOpen ? null : topic.id)}
                      className="w-full p-4 text-left flex items-center justify-between gap-3 hover:bg-slate-50/70 transition"
                    >
                      <div className="flex items-center gap-2.5 flex-1 min-w-0">
                        <span className="shrink-0 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-blue-50 text-[#1E40AF] border border-blue-200/60">
                          {topic.categoryLabel}
                        </span>
                        <h3 className="text-[13.5px] font-bold text-slate-900 truncate">
                          {topic.title}
                        </h3>
                      </div>

                      <ChevronDown
                        className={`w-4 h-4 text-slate-400 shrink-0 transition-transform duration-200 ${
                          isOpen ? "rotate-180 text-[#1E40AF]" : ""
                        }`}
                      />
                    </button>

                    {/* Nội dung chi tiết chỉ mở ra khi bấm (150-200ms ease) */}
                    {isOpen && (
                      <div className="p-4 sm:p-5 border-t border-slate-100 bg-slate-50/40 space-y-4 animate-fadeIn">
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-[12.5px]">
                          <div className="space-y-1.5">
                            <span className="font-bold text-slate-800 block text-[12px]">
                              Dấu hiệu nhận biết:
                            </span>
                            <ul className="space-y-1 list-disc pl-4 text-slate-600">
                              {topic.symptoms.map((s, i) => (
                                <li key={i}>{s}</li>
                              ))}
                            </ul>
                          </div>

                          <div className="space-y-1.5">
                            <span className="font-bold text-slate-800 block text-[12px]">
                              Dữ kiện nên chuẩn bị:
                            </span>
                            <ul className="space-y-1 list-disc pl-4 text-slate-600">
                              {topic.preparation.map((p, i) => (
                                <li key={i}>{p}</li>
                              ))}
                            </ul>
                          </div>
                        </div>

                        <div className="pt-3 border-t border-slate-200/70 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
                          <a
                            href={topic.citationUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-[11.5px] text-[#1E40AF] hover:underline flex items-center gap-1 font-medium"
                          >
                            <ExternalLink className="w-3.5 h-3.5" />
                            <span>{topic.citationTitle}</span>
                          </a>

                          {/* Nút Hỏi AI chỉ xuất hiện trong phần mở ra */}
                          <Link
                            href={`/chat?prompt=${encodeURIComponent(topic.suggestedPrompt)}`}
                            className="inline-flex items-center justify-center gap-1.5 px-4 py-2 rounded-xl bg-[#1E40AF] hover:bg-[#1D4ED8] text-white text-[12px] font-semibold transition shadow-2xs active:scale-[0.98]"
                          >
                            <Sparkles className="w-3.5 h-3.5" />
                            <span>Hỏi Trợ lý Agent về tình huống này</span>
                          </Link>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}

              {filteredTopics.length === 0 && (
                <div className="bg-white rounded-2xl p-8 text-center text-slate-500 border border-slate-200/80">
                  <p className="text-[13px]">Không tìm thấy tình huống nào phù hợp với từ khóa.</p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
