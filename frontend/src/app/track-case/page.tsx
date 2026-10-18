"use client";
import { useLocale } from "@/features/shared/context/LocaleContext";

import { useState, useEffect, useMemo } from "react";
import Link from "next/link";
import { toCustomerWarningText } from "@/features/shared/utils/customerWarningText";
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
  ChevronDown,
  ChevronUp,
  BookOpen,
  Navigation,
  ThumbsUp,
  ShieldCheck,
  Loader2,
  ShieldAlert,
  ArrowRight,
} from "lucide-react";
import {
  getCaseDetail,
  getCustomerCases,
  reopenCustomerCase,
  submitCustomerFeedback,
  confirmCustomerCase,
  submitSafetyAcknowledgement,
  getCaseServicePoints,
  submitCustomerLocation,
} from "@/features/chat/api/chatApi";
import {
  CustomerCaseItem,
  ServicePointsApiResponse,
  ServicePointApiItem,
} from "@/features/chat/types";
import { VietmapMiniMap } from "@/features/chat/components/VietmapMiniMap";
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
  | "New"
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
  locationShared?: boolean;
  chargerId?: string;
  errorCode?: string;
  warningSymbol?: string;
  currentSoc?: string;
  safetyStatus?: string;
  incidentVersion?: number;
  locationConsent?: "GRANTED" | "DENIED" | "MANUAL" | "PENDING";
  manualLocation?: string;
  missingFields?: string[];
  capturedFields?: Record<string, unknown>;
  customerUpdate?: {
    resolvedAt?: string;
    staffName: string;
    resolutionSummary: string;
    nextStepGuidance: string;
    customerConfirmed?: boolean;
  };
  chatSnippet?: Array<{ sender: "CUSTOMER" | "AGENT" | "STAFF"; text: string; time: string }>;
  suggestedServicePoints?: ServicePointApiItem[];
}

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
    "id": "topic-01",
    "category": "CHARGING",
    "categoryLabel": "Sạc & Pin",
    "title": "Trụ sạc báo lỗi hoặc không bắt đầu sạc",
    "symptoms": [
      "Mã lỗi hoặc thông báo hiển thị trên trụ sạc",
      "Trạng thái sạc hiển thị trên xe"
    ],
    "preparation": [
      "Cung cấp dòng xe, đời xe và mã trụ nếu có",
      "Mô tả thông báo hoặc gửi ảnh khi có thể thực hiện an toàn"
    ],
    "suggestedPrompt": "Xe của tôi không bắt đầu sạc. Tôi cần hỗ trợ kiểm tra thông báo trên xe và trụ sạc.",
    "citationTitle": "Trang chính thức về sạc công cộng VinFast",
    "citationUrl": "https://vinfastauto.com/vn_vi/chinh-sach-va-bieu-phi-sac-pin-cong-cong"
  },
  {
    "id": "topic-02",
    "category": "DASHBOARD",
    "categoryLabel": "Cảnh báo táp-lô",
    "title": "Biểu tượng Con Rùa Vàng (Turtle Warning)",
    "symptoms": [
      "Biểu tượng hoặc thông báo xuất hiện trên màn hình người lái",
      "Thay đổi vận hành do người lái quan sát"
    ],
    "preparation": [
      "Cung cấp dòng xe, đời xe và nội dung cảnh báo",
      "Tra cứu sổ tay đúng dòng xe và đời xe; liên hệ hỗ trợ nếu cần"
    ],
    "suggestedPrompt": "Xe của tôi hiện biểu tượng rùa vàng. Tôi cần tra cứu hướng dẫn đúng dòng xe và đời xe.",
    "citationTitle": "Chọn sổ tay sử dụng chính thức theo dòng xe",
    "citationUrl": "https://om.vinfastauto.com/vi_vn/"
  },
  {
    "id": "topic-03",
    "category": "WALLBOX",
    "categoryLabel": "Sạc tại nhà",
    "title": "Bộ sạc tại nhà không hoạt động như mong đợi",
    "symptoms": [
      "Thông báo trên bộ sạc hoặc ứng dụng",
      "Thời điểm sạc bị gián đoạn do người dùng ghi nhận"
    ],
    "preparation": [
      "Cung cấp loại bộ sạc và nội dung thông báo nếu có",
      "Liên hệ đơn vị hỗ trợ bộ sạc để nhận hướng dẫn phù hợp"
    ],
    "suggestedPrompt": "Bộ sạc tại nhà của tôi bị gián đoạn. Tôi cần hỗ trợ theo loại bộ sạc và thông báo đang hiển thị.",
    "citationTitle": "Hướng dẫn ứng dụng VinFast trên trang chính thức",
    "citationUrl": "https://vinfastauto.com/vn_vi/huong-dan-su-dung-ung-dung-vinfast"
  },
  {
    "id": "topic-04",
    "category": "TIRE",
    "categoryLabel": "Lốp xe & Khung gầm",
    "title": "Cảnh báo áp suất lốp (TPMS)",
    "symptoms": [
      "Nội dung cảnh báo lốp hiển thị trên xe",
      "Chỉ số áp suất đang hiển thị nếu có"
    ],
    "preparation": [
      "Cung cấp dòng xe, đời xe và vị trí bánh xe có cảnh báo",
      "Đối chiếu sổ tay đúng xe hoặc liên hệ xưởng dịch vụ để được hướng dẫn"
    ],
    "suggestedPrompt": "Xe của tôi có cảnh báo áp suất lốp. Tôi cần hướng dẫn đúng dòng xe và hỗ trợ từ xưởng dịch vụ.",
    "citationTitle": "Trang dịch vụ bảo dưỡng VinFast",
    "citationUrl": "https://vinfastauto.com/vn_vi/dich-vu-bao-duong-oto"
  }
];

export default function TrackCasePage() {
  const { t, language } = useLocale();
  const { user, role } = useAuth();

  // Tabs: "Yêu cầu của tôi" vs "Tình huống thường gặp"
  const [activeTab, setActiveTab] = useState<"my_cases" | "curated_topics">("my_cases");

  // Active selected case - Loads dynamically from customer cases or search
  const [selectedCaseId, setSelectedCaseId] = useState<string>("");
  const [currentCase, setCurrentCase] = useState<TrackedCase | null>(null);

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
  const [selectedFeedbackTags, setSelectedFeedbackTags] = useState<string[]>([]);
  const [feedbackSubmitted, setFeedbackSubmitted] = useState<boolean>(false);
  const [isSubmittingFeedback, setIsSubmittingFeedback] = useState<boolean>(false);
  const [isFeedbackDismissed, setIsFeedbackDismissed] = useState<boolean>(false);

  // Curated Topics Tab: Search & Filter & Accordion
  const [topicSearch, setTopicSearch] = useState<string>("");
  const [topicCategory, setTopicCategory] = useState<string>("ALL");
  const [expandedTopicId, setExpandedTopicId] = useState<string | null>("topic-01");

  const [actionNotice, setActionNotice] = useState<string | null>(null);
  const [caseLoadError, setCaseLoadError] = useState<string | null>(null);
  const [isConfirmingSafety, setIsConfirmingSafety] = useState<boolean>(false);

  // Real Service Points from /cases/{id}/service-points (BƯỚC 4)
  const [servicePointsData, setServicePointsData] = useState<ServicePointsApiResponse | null>(null);
  const [isRequestingLocation, setIsRequestingLocation] = useState<boolean>(false);
  const [clientUserCoord, setClientUserCoord] = useState<{ lat: number; lng: number } | null>(null);

  const handleShareLocation = () => {
    if (typeof window === "undefined" || !navigator.geolocation) {
      setActionNotice("Trình duyệt không hỗ trợ định vị GPS trực tiếp.");
      return;
    }
    setIsRequestingLocation(true);
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const lat = pos.coords.latitude;
        const lng = pos.coords.longitude;
        setClientUserCoord({ lat, lng });
        if (selectedCaseId) {
          try {
            await submitCustomerLocation({
              case_id: selectedCaseId,
              status: "CONSENTED",
              source: "BROWSER_GPS",
              location_label: "Vị trí GPS từ trình duyệt",
              latitude: lat,
              longitude: lng,
              precision: "EXACT",
              share_with_staff: true,
            });
            const updated = await getCaseServicePoints(selectedCaseId);
            if (updated?.success && updated.data) {
              setServicePointsData(updated.data);
            }
          } catch {
            // Lỗi cập nhật backend không chặn hiển thị tọa độ trên bản đồ client
          }
        }
        setIsRequestingLocation(false);
      },
      () => {
        setIsRequestingLocation(false);
        setActionNotice("Không nhận được quyền vị trí GPS. Hệ thống gợi ý theo khu vực.");
      },
      { timeout: 10000, enableHighAccuracy: true }
    );
  };

  const handleCopyId = (idToCopy: string) => {
    navigator.clipboard.writeText(idToCopy);
    setCopiedId(true);
    setTimeout(() => setCopiedId(false), 2000);
  };

  // Case switch handler: Fetch full case details from GET /api/v1/customer/cases/{case_id}
  const handleSelectCase = async (caseId: string) => {
    setSelectedCaseId(caseId);
    setActionNotice(null);
    setCaseLoadError(null);
    setFeedbackSubmitted(false);
    setConfirmStatus("IDLE");
    setShowAllChat(false);

    setSearchLoading(true);
    try {
      const [res, spRes] = await Promise.all([
        getCaseDetail(caseId),
        getCaseServicePoints(caseId).catch(() => null),
      ]);

      if (spRes?.success && spRes.data) {
        setServicePointsData(spRes.data);
      } else {
        setServicePointsData(null);
      }

      if (res?.success && res.data) {
        const d = res.data;
        const c = d.case;
        const brief = d.case_brief;
        const captured = brief?.captured_fields || {};
        const loc = d.location;

        // 1. Vehicle model - Never default to VF8
        const rawModel = String(c.vehicle_model || captured.vehicle_model || "");
        const cleanModel = rawModel
          ? rawModel.toUpperCase().startsWith("VF")
            ? rawModel.toUpperCase().replace(/\s+/g, "")
            : `VF${rawModel}`
          : t("Đang xác minh");

        // 2. Battery SoC & Warning light
        const rawSoc = captured.current_soc ?? captured.soc ?? null;
        const socDisplay =
          rawSoc !== null && rawSoc !== undefined
            ? `${String(rawSoc).replace(/%$/, "")}%`
            : t("Đang xác minh");

        const warningLight = toCustomerWarningText(captured);
        const rawErrorCode = captured.error_code ? String(captured.error_code) : null;

        const isTurtle =
          /rùa|turtle/i.test(String(warningLight)) ||
          /rùa|turtle/i.test(String(rawErrorCode)) ||
          /rùa/i.test(brief?.summary || "") ||
          /rùa/i.test(c.summary || "");

        // 3. Issue Summary
        let summary = brief?.summary || c.summary || "";
        if (!summary || summary === "Hồ sơ sự cố tiếp nhận qua hệ thống VinFast ServiceFlow AI.") {
          if (isTurtle) {
            summary = `${cleanModel !== t("Đang xác minh") ? cleanModel + " · " : ""}Cảnh báo rùa vàng, xe giảm công suất`;
          } else if (warningLight) {
            summary = `${cleanModel !== t("Đang xác minh") ? cleanModel + " · " : ""}Cảnh báo ${warningLight}`;
          } else {
            summary = `${cleanModel !== t("Đang xác minh") ? cleanModel + " · " : ""}Hồ sơ hỗ trợ kỹ thuật`;
          }
        }

        // 4. Conversation History snippet mapping
        const convSnippet = (d.conversation_history || []).map((msg) => ({
          sender: (msg.sender === "CUSTOMER"
            ? "CUSTOMER"
            : msg.sender === "STAFF"
              ? "STAFF"
              : "AGENT") as "CUSTOMER" | "AGENT" | "STAFF",
          text: msg.content,
          time: msg.created_at
            ? new Date(msg.created_at).toLocaleTimeString("vi-VN", {
                hour: "2-digit",
                minute: "2-digit",
              })
            : "",
        }));

        // 5. Location
        const hasRealLocation = loc && loc.share_with_staff && loc.location_label;
        const locationLabel = hasRealLocation
          ? loc.location_label!
          : undefined;

        // 6. Safety Status & Incident Version
        const safetyStatus = String(c.safety_status || captured.safety_status || "unconfirmed");
        const incidentVersion = c.incident_version ?? 1;

        // 7. Last Staff Update
        const lastStaffUpdate = (d.updates || [])
          .filter((u) => u.author_type === "STAFF" || u.author_type === "SYSTEM")
          .slice(-1)[0];

        setCurrentCase({
          id: c.id || caseId,
          vehicleModel: cleanModel,
          vehicleCode: c.vehicle_code_mock || "VF-SF-00231",
          status: (c.status as TrackedCase["status"]) || "New",
          priority: (c.priority as TrackedCase["priority"]) || "HIGH",
          createdAt: c.created_at
            ? new Date(c.created_at).toLocaleTimeString("vi-VN", {
                hour: "2-digit",
                minute: "2-digit",
              }) +
              " " +
              new Date(c.created_at).toLocaleDateString("vi-VN")
            : "Hôm nay",
          issueSummary: summary,
          suggestedAction:
            brief?.suggested_action || "",
          reviewerNotes:
            lastStaffUpdate?.customer_message ||
            t("Chưa có cập nhật từ chuyên viên."),
          assignedTo: undefined,
          stationLocation: locationLabel,
          locationShared: Boolean(hasRealLocation),
          currentSoc: socDisplay,
          errorCode: rawErrorCode || undefined,
          warningSymbol: isTurtle
            ? "Rùa vàng (giảm công suất)"
            : warningLight || undefined,
          safetyStatus: safetyStatus,
          incidentVersion: incidentVersion,
          chatSnippet: convSnippet.length > 0 ? convSnippet : undefined,
          suggestedServicePoints: spRes?.data?.recommended_points || [],
          customerUpdate:
            ["Resolved", "Closed"].includes(c.status) && lastStaffUpdate?.status_after_update === "Resolved"
              ? {
                  resolvedAt: lastStaffUpdate.created_at
                    ? new Date(lastStaffUpdate.created_at).toLocaleTimeString("vi-VN", {
                        hour: "2-digit",
                        minute: "2-digit",
                      })
                    : undefined,
                  staffName: "Cố vấn Dịch vụ VinFast",
                  resolutionSummary:
                    lastStaffUpdate.customer_message || t("Chuyên viên đã cập nhật trạng thái xử lý. Vui lòng kiểm tra lại tình trạng xe."),
                  nextStepGuidance:
                    lastStaffUpdate.next_step ||
                    t("Vui lòng xác nhận kết quả xử lý hoặc yêu cầu kiểm tra bổ sung."),
                }
              : undefined,
        });
      } else {
        const errMsg = typeof res?.error === "string" ? res.error : (res?.error as any)?.message || t("Không tìm thấy dữ liệu hồ sơ");
        throw new Error(errMsg);
      }
    } catch (err: unknown) {
      setCaseLoadError(
        err instanceof Error ? err.message : t("Không tải được chi tiết hồ sơ. Vui lòng thử lại.")
      );
    } finally {
      setSearchLoading(false);
    }
  };

  // RBAC & URL Search Params: Lấy ca thực từ backend hoặc query param
  useEffect(() => {
    const params = typeof window !== "undefined" ? new URLSearchParams(window.location.search) : null;
    const queryCaseId = params?.get("case_id");
    if (queryCaseId) {
      handleSelectCase(queryCaseId);
    }
  }, []);

  useEffect(() => {
    if (role === "CUSTOMER") {
      getCustomerCases()
        .then((res) => {
          if (res?.success && res.data?.cases && res.data.cases.length > 0) {
            setUserCases(res.data.cases);
            const params = typeof window !== "undefined" ? new URLSearchParams(window.location.search) : null;
            if (!params?.get("case_id")) {
              handleSelectCase(res.data.cases[0].id);
            }
          }
        })
        .catch(() => { });
    }
  }, [role]);

  const handleConfirmSafety = async () => {
    if (!currentCase) return;
    setIsConfirmingSafety(true);
    try {
      const receipt = await submitSafetyAcknowledgement(currentCase.id, {
        incident_version: currentCase.incidentVersion || 1,
      });
      if (!receipt.success || receipt.data.safety_status !== "customer_reported_safe") throw new Error("Safety not saved");
      setCurrentCase({
        ...currentCase,
        safetyStatus: "customer_reported_safe",
      });
      setActionNotice(t("Đã ghi nhận vị trí an toàn của Quý khách. Đội ngũ kỹ thuật đang tiếp tục hỗ trợ."));
    } catch (err: unknown) {
      setActionNotice(t("Không thể xác nhận an toàn: ") + (err instanceof Error ? err.message : t("Lỗi kết nối")));
    } finally {
      setIsConfirmingSafety(false);
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
  const handleConfirmResolved = async () => {
    if (!currentCase) return;
    setIsSubmittingConfirm(true);
    setActionNotice(null);
    try {
      const receipt = await confirmCustomerCase(currentCase.id, {
        confirmation: "RESOLVED_CONFIRMED",
      });
      if (!receipt.success) throw new Error(receipt.error || "Máy chủ chưa ghi nhận xác nhận.");
      setConfirmStatus("RESOLVED_CONFIRMED");
      setCurrentCase({ ...currentCase, status: "Closed" });
      setActionNotice(t("Cảm ơn Quý khách đã xác nhận! Hồ sơ đã được hoàn tất. Vui lòng dành 30 giây đánh giá chất lượng phục vụ."));
    } catch (err: unknown) {
      setActionNotice("Lưu ý: " + (err instanceof Error ? err.message : t("Chưa lưu được xác nhận. Hồ sơ chưa thay đổi; vui lòng thử lại.")));
    } finally {
      setIsSubmittingConfirm(false);
    }
  };

  const handleReopenSubmit = async () => {
    if (!currentCase) return;
    setIsSubmittingConfirm(true);
    setActionNotice(null);
    try {
      const receipt = await reopenCustomerCase(currentCase.id);
      if (!receipt.success || receipt.data.status !== "Reopened") throw new Error("Reopen not saved");
      setConfirmStatus("REOPEN_REQUESTED");
      setCurrentCase({
        ...currentCase,
        status: "Reopened",
        customerUpdate: undefined,
        reviewerNotes: reopenReason
          ? `${t("Khách yêu cầu mở lại:")} "${reopenReason}"`
          : t("Khách phản ánh sự cố chưa được khắc phục triệt để."),
      });
      setActionNotice(t("Hồ sơ đã được chuyển lại cho Cố vấn Dịch vụ để kiểm tra bổ sung!"));
    } catch (err: unknown) {
      setActionNotice("Lưu ý: " + (err instanceof Error ? err.message : t("Không thể mở lại hồ sơ lúc này.")));
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
        reason_tags: feedbackRating <= 2 ? selectedFeedbackTags : [],
      });
      if (res?.success) {
        setFeedbackSubmitted(true);
        setActionNotice(t("Cảm ơn anh/chị đã gửi đánh giá chất lượng dịch vụ!"));
      }
    } catch (err: unknown) {
      setActionNotice("Lưu ý: " + (err instanceof Error ? err.message : t("Lỗi khi gửi đánh giá.")));
    } finally {
      setIsSubmittingFeedback(false);
    }
  };

  // Stepper calculations
  const getStatusStep = (status: TrackedCase["status"]) => {
    switch (status) {
      case "Staff Reviewing":
        return 2;
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

  const getStatusLabel = (status: string) => {
    switch (status) {
      case "New":
        return language === "en" ? "Awaiting review" : "Chờ tiếp nhận";
      case "Staff Reviewing":
        return t("Đang xác minh");
      case "Needs Information":
        return t("Cần làm rõ tin");
      case "In Progress":
        return t("Đang xử lý");
      case "Reopened":
        return t("Đã mở lại");
      case "Resolved":
        return t("Đã xử lý xong");
      case "Closed":
        return t("Đã hoàn tất");
      default:
        return status;
    }
  };

  // Next Step Prominent Guidance Message
  const getNextStepInfo = (c: TrackedCase) => {
    if (["Resolved", "Closed"].includes(c.status) && c.customerUpdate?.nextStepGuidance) {
      return {
        highlight: c.customerUpdate.nextStepGuidance,
        badge: t("Chỉ dẫn từ Cố vấn"),
        isAlert: false,
      };
    }
    if (c.status === "Staff Reviewing") {
      return {
        highlight: t("Chuyên viên dịch vụ đang phân tích dữ liệu sự cố. Khi có cập nhật, thông tin sẽ hiển thị tại đây."),
        badge: t("Bước tiếp theo"),
        isAlert: false,
      };
    }
    if (c.status === "Needs Information") {
      return {
        highlight: t("Vui lòng mở Trợ lý Chat gửi ảnh táp-lô hoặc xác nhận vị trí hỗ trợ."),
        badge: t("Cần thông tin"),
        isAlert: true,
      };
    }
    if (c.status === "In Progress") {
      return {
        highlight: c.suggestedAction || t("Kỹ thuật viên đang trong quá trình kiểm tra xử lý thực địa."),
        badge: t("Bước tiếp theo"),
        isAlert: false,
      };
    }
    if (c.status === "New" || c.status === "Reopened") {
      return {highlight: t(c.status === "New" ? t("Hồ sơ đã được ghi nhận và đang chờ tiếp nhận. Vui lòng theo dõi cập nhật tại đây.") : t("Hồ sơ đã được mở lại và đang chờ kiểm tra bổ sung.")), badge: t("Bước tiếp theo"), isAlert: false};
    }
    if (c.status !== "Resolved" && c.status !== "Closed") {
      return {highlight: t("Chưa có chỉ dẫn tiếp theo được xác nhận. Vui lòng theo dõi cập nhật hồ sơ."), badge: t("Bước tiếp theo"), isAlert: false};
    }
    return {
      highlight: t("Hồ sơ đã được xử lý hoàn tất. Chúc anh/chị vạn dặm bình an!"),
      badge: t("Hoàn tất"),
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
                  {t("Yêu cầu của tôi")}</h1>
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold bg-blue-50 text-[#1E40AF] border border-blue-200/60">
                  {role === "GUEST" ? "Guest" : t("Thời gian thực")}
                </span>
              </div>
              <p className="text-[12.5px] text-slate-500 mt-0.5">
                {t("Theo dõi tiến trình xử lý sự cố xe và hỗ trợ kỹ thuật trực tiếp từ VinFast.")}</p>
            </div>
          </div>

          {/* Header Controls: Sub-Tabs & Case Switcher Dropdown */}
          <div className="flex flex-wrap items-center gap-2.5">
            {/* 2 Tabs: Yêu cầu của tôi vs Tình huống thường gặp */}
            <div className="inline-flex items-center p-0.5 bg-slate-200/70 rounded-xl text-[12px] font-medium">
              <button
                type="button"
                onClick={() => setActiveTab("my_cases")}
                className={`px-3 py-1.5 rounded-lg transition flex items-center gap-1.5 ${activeTab === "my_cases"
                  ? "bg-white text-[#1E40AF] font-bold shadow-2xs"
                  : "text-slate-600 hover:text-slate-900"
                  }`}
              >
                <Clock className="w-3.5 h-3.5" />
                <span>{t("Hồ sơ xe")}</span>
              </button>

              <button
                type="button"
                onClick={() => setActiveTab("curated_topics")}
                className={`px-3 py-1.5 rounded-lg transition flex items-center gap-1.5 ${activeTab === "curated_topics"
                  ? "bg-white text-[#1E40AF] font-bold shadow-2xs"
                  : "text-slate-600 hover:text-slate-900"
                  }`}
              >
                <BookOpen className="w-3.5 h-3.5" />
                <span>{t("Tình huống thường gặp")}</span>
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
                      className="appearance-none bg-white border border-slate-200 rounded-xl py-1.5 pl-3 pr-8 text-[12px] font-semibold text-slate-800 shadow-2xs hover:border-slate-300 focus:outline-none focus:ring-2 focus:ring-[#1E40AF]/20 cursor-pointer max-w-[280px] sm:max-w-[340px] truncate"
                    >
                      {userCases && userCases.length > 0 ? (
                        <>
                          {userCases.map((uc) => {
                            const shortId = uc.id.length > 18 ? uc.id.slice(0, 15) + "..." : uc.id;
                            const model = uc.vehicle_model
                              ? (uc.vehicle_model.toUpperCase().startsWith("VF")
                                ? uc.vehicle_model.toUpperCase()
                                : `VF ${uc.vehicle_model}`)
                              : "VF";
                            const statusVn = getStatusLabel(uc.status);
                            return (
                              <option key={uc.id} value={uc.id}>
                                {model} · {statusVn} ({shortId})
                              </option>
                            );
                          })}
                          {selectedCaseId && !userCases.some((uc) => uc.id === selectedCaseId) && (
                            <option value={selectedCaseId}>
                              {currentCase?.vehicleModel || "VF"} · {getStatusLabel(currentCase?.status || "Staff Reviewing")} ({selectedCaseId.length > 18 ? selectedCaseId.slice(0, 15) + "..." : selectedCaseId})
                            </option>
                          )}
                        </>
                      ) : (
                        <>
                          {selectedCaseId ? (
                            <option value={selectedCaseId}>
                              {currentCase?.vehicleModel || "VF"} · {getStatusLabel(currentCase?.status || "Staff Reviewing")} ({selectedCaseId.length > 18 ? selectedCaseId.slice(0, 15) + "..." : selectedCaseId})
                            </option>
                          ) : (
                            <option value="">{t("Chưa có hồ sơ xe")}</option>
                          )}
                        </>
                      )}
                    </select>
                    <ChevronDown className="w-3.5 h-3.5 text-slate-400 absolute right-2.5 pointer-events-none" />

                    <button
                      type="button"
                      onClick={() => setIsSearchingCustom(true)}
                      className="ml-1.5 p-1.5 rounded-lg border border-slate-200 bg-white text-slate-500 hover:text-slate-800 hover:bg-slate-50 shadow-2xs transition"
                      title={t("Tìm mã hồ sơ khác")}
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
                      placeholder={t("Mã hồ sơ (VD: CASE-001)...")}
                      className="w-40 bg-white border border-slate-300 rounded-xl px-2.5 py-1 text-[12px] font-mono font-medium text-slate-900 focus:outline-none focus:ring-2 focus:ring-[#1E40AF]/20"
                      autoFocus
                    />
                    <button
                      type="submit"
                      disabled={searchLoading}
                      className="px-2.5 py-1 rounded-xl bg-[#1E40AF] text-white text-[12px] font-semibold hover:bg-[#1D4ED8]"
                    >
                      {searchLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : t("Tìm")}
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
                {t("Chưa đăng nhập")}</span>
              <h2 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
                {t("Đăng nhập để theo dõi hồ sơ xe")}</h2>
              <p className="text-[13px] text-slate-500 max-w-lg mx-auto leading-relaxed">
                {t("Để đảm bảo an toàn và bảo mật thông tin phương tiện, vui lòng đăng nhập tài khoản chủ xe để theo dõi tiến trình xử lý sự cố và cập nhật từ xưởng dịch vụ.")}</p>
            </div>

            {/* 3 tính năng của Customer */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-left pt-1">
              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/70 text-[12px] space-y-1">
                <CheckCircle2 className="w-4 h-4 text-[#1E40AF]" />
                <strong className="block text-slate-900 font-semibold">{t("Tiến độ 4 bước")}</strong>
                <span className="text-slate-500 text-[11.5px] leading-snug block">{t("Cập nhật trạng thái thời gian thực từ xưởng dịch vụ")}</span>
              </div>
              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/70 text-[12px] space-y-1">
                <MessageSquare className="w-4 h-4 text-[#1E40AF]" />
                <strong className="block text-slate-900 font-semibold">{t("Chỉ dẫn kỹ thuật")}</strong>
                <span className="text-slate-500 text-[11.5px] leading-snug block">{t("Trao đổi và nhận hướng dẫn xử lý từ Cố vấn dịch vụ")}</span>
              </div>
              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/70 text-[12px] space-y-1">
                <RotateCcw className="w-4 h-4 text-[#1E40AF]" />
                <strong className="block text-slate-900 font-semibold">{t("Nghiệm thu xe")}</strong>
                <span className="text-slate-500 text-[11.5px] leading-snug block">{t("Xác nhận hoàn tất hoặc mở lại hồ sơ (Reopen) khi cần")}</span>
              </div>
            </div>

            {/* 2 CTA Buttons */}
            <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
              <Link
                href="/login"
                className="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-xl bg-[#1E40AF] hover:bg-[#1D4ED8] px-5 py-2.5 text-[13px] font-semibold text-white shadow-2xs transition active:scale-[0.98]"
              >
                <span>{t("Đăng nhập tài khoản Khách hàng")}</span>
                <ArrowRight className="w-4 h-4" />
              </Link>

              <button
                type="button"
                onClick={() => setActiveTab("curated_topics")}
                className="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 px-4 py-2.5 text-[13px] font-semibold text-slate-700 transition"
              >
                <BookOpen className="w-4 h-4 text-slate-500" />
                <span>{t("Xem Tình huống thường gặp")}</span>
              </button>
            </div>
          </div>
        )}

        {/* Chế độ CUSTOMER: Khi chưa có hồ sơ nào */}
        {activeTab === "my_cases" && role !== "GUEST" && !currentCase && !searchLoading && (
          <div className="bg-white rounded-3xl border border-slate-200/90 shadow-sm p-8 sm:p-12 text-center max-w-xl mx-auto my-6 animate-fadeIn space-y-5">
            <div className="w-16 h-16 rounded-2xl bg-blue-50 border border-blue-200 flex items-center justify-center mx-auto text-[#1E40AF]">
              <Car className="w-8 h-8" />
            </div>
            <div className="space-y-2">
              <h2 className="text-xl font-bold text-slate-900 tracking-tight">
                {t("Chưa có hồ sơ sự cố nào")}</h2>
              <p className="text-[13px] text-slate-500 max-w-md mx-auto leading-relaxed">
                {t("Tài khoản của bạn hiện chưa ghi nhận sự cố xe nào đang xử lý. Bạn có thể trò chuyện với Trợ lý AI để yêu cầu hỗ trợ kỹ thuật hoặc tra cứu bằng mã hồ sơ cụ thể.")}</p>
            </div>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
              <Link
                href="/chat"
                className="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-xl bg-[#1E40AF] hover:bg-[#1D4ED8] px-5 py-2.5 text-[13px] font-semibold text-white shadow-2xs transition"
              >
                <MessageSquare className="w-4 h-4" />
                <span>{t("Phản ánh sự cố xe với AI")}</span>
              </Link>
              <button
                type="button"
                onClick={() => setIsSearchingCustom(true)}
                className="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-xl bg-slate-100 hover:bg-slate-200 px-5 py-2.5 text-[13px] font-medium text-slate-700 transition"
              >
                <Search className="w-4 h-4" />
                <span>{t("Tra cứu mã hồ sơ")}</span>
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
              {/* Thông báo lỗi khi không tải được hồ sơ */}
              {caseLoadError && (
                <div className="bg-red-50 border border-red-200 rounded-2xl p-4 sm:p-5 text-red-900 space-y-3 animate-fadeIn">
                  <div className="flex items-center gap-2">
                    <AlertCircle className="w-5 h-5 text-red-600 shrink-0" />
                    <h3 className="font-bold text-[14px]">{t("Không tải được chi tiết hồ sơ")}</h3>
                  </div>
                  <p className="text-[12.5px] text-red-800 leading-relaxed">
                    {caseLoadError}
                  </p>
                  <button
                    type="button"
                    onClick={() => handleSelectCase(selectedCaseId)}
                    className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-red-600 hover:bg-red-700 text-white text-[12px] font-semibold transition"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                    <span>{t("Thử lại")}</span>
                  </button>
                </div>
              )}

              {/* KHỐI NHẮC XÁC NHẬN AN TOÀN (Ưu tiên cao - khi safety_status = unconfirmed trên ca khẩn cấp) */}
              {(currentCase.priority === "CRITICAL" || currentCase.priority === "HIGH") &&
                currentCase.status !== "Closed" &&
                currentCase.status !== "Resolved" &&
                currentCase.safetyStatus === "unconfirmed" && (
                <div className="rounded-2xl border-2 border-amber-400 bg-amber-50/90 p-4 sm:p-5 shadow-sm space-y-3 animate-fadeIn">
                  <div className="flex items-start gap-3">
                    <div className="w-10 h-10 rounded-xl bg-amber-500 text-white flex items-center justify-center shrink-0 shadow-xs">
                      <ShieldAlert className="w-5 h-5 animate-pulse" />
                    </div>
                    <div className="flex-1 space-y-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <h3 className="text-[14.5px] font-bold text-amber-950">
                          {t("Anh/chị đã ở nơi an toàn chưa?")}</h3>
                        <span className="text-[11px] font-bold uppercase tracking-wider bg-amber-200 text-amber-900 px-2 py-0.5 rounded-full">
                          {t("Khẩn cấp an toàn")}</span>
                      </div>
                      <p className="text-[12.5px] text-amber-900/90 leading-relaxed">
                        {t("Ưu tiên tới khu vực an toàn nếu có thể và gọi hotline cứu hộ.")}
                      </p>
                    </div>
                  </div>

                  <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-end gap-2.5 pt-1 border-t border-amber-200/80">
                    <a
                      href="tel:1900232389"
                      className="inline-flex items-center justify-center gap-1.5 px-3.5 py-2 rounded-xl bg-white border border-amber-300 text-amber-900 text-[12px] font-semibold hover:bg-amber-100/50 transition"
                    >
                      <PhoneCall className="w-3.5 h-3.5 text-red-600" />
                      <span>{t("Gọi cứu hộ 1900-232389")}</span>
                    </a>
                    <button
                      type="button"
                      disabled={isConfirmingSafety}
                      onClick={handleConfirmSafety}
                      className="inline-flex items-center justify-center gap-1.5 px-4 py-2 rounded-xl bg-amber-600 hover:bg-amber-700 active:scale-[0.98] text-white text-[12.5px] font-bold shadow-xs transition disabled:opacity-60"
                    >
                      {isConfirmingSafety ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <ShieldCheck className="w-4 h-4" />
                      )}
                      <span>{t("Tôi đã ở vị trí an toàn")}</span>
                    </button>
                  </div>
                </div>
              )}

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
                          title={t("Sao chép mã hồ sơ")}
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
                          {t("Cứu hộ khẩn")}</span>
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
                        { step: 1, title: t("Tiếp nhận"), sub: t("Ghi nhận ca") },
                        { step: 2, title: t("Xác minh"), sub: t("Làm rõ dữ kiện") },
                        { step: 3, title: t("Xử lý"), sub: t("Kỹ thuật / Xưởng") },
                        { step: 4, title: t("Hoàn tất"), sub: t("Nghiệm thu ca") },
                      ].map((s) => {
                        const isPassed = currentStep > s.step;
                        const isCurrent = currentStep === s.step;

                        return (
                          <div key={s.step} className="flex flex-col items-center">
                            <div
                              className={`flex h-7 w-7 sm:h-8 sm:w-8 items-center justify-center rounded-full text-[11.5px] font-bold transition-all ${isPassed
                                ? "bg-emerald-500 text-white shadow-2xs"
                                : isCurrent
                                  ? "bg-[#1E40AF] text-white ring-4 ring-blue-100 shadow-2xs"
                                  : "bg-white text-slate-400 border border-slate-200"
                                }`}
                            >
                              {isPassed ? <Check className="h-4 w-4" /> : s.step}
                            </div>

                            <span
                              className={`mt-1.5 font-semibold text-[11.5px] sm:text-[12px] leading-tight ${isCurrent ? "text-[#1E40AF]" : isPassed ? "text-slate-800" : "text-slate-400"
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
                      className={`rounded-xl p-3.5 text-[13px] border flex items-start gap-2.5 transition ${nextStepData.isAlert
                        ? "bg-red-50/90 border-red-200 text-red-900"
                        : "bg-blue-50/90 border-blue-200/80 text-blue-950"
                        }`}
                    >
                      <Sparkles
                        className={`w-4 h-4 shrink-0 mt-0.5 ${nextStepData.isAlert ? "text-red-600" : "text-[#1E40AF]"
                          }`}
                      />
                      <div className="flex-1 space-y-0.5">
                        <div className="flex items-center gap-1.5">
                          <span
                            className={`font-bold text-[12px] uppercase tracking-wide px-1.5 py-0.2 rounded ${nextStepData.isAlert
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
                {["Resolved", "Closed"].includes(currentCase.status) && currentCase.customerUpdate && (
                  <div className="p-4 sm:p-5 border-t border-slate-100 bg-emerald-50/30 space-y-3">
                    <div className="flex items-center justify-between text-[12px]">
                      <span className="font-bold text-emerald-900 flex items-center gap-1.5">
                        <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                        {t("Kết quả giải quyết từ Cố vấn Dịch vụ")}</span>
                      <span className="text-[11px] text-emerald-700 font-mono">
                        {currentCase.customerUpdate.resolvedAt}
                      </span>
                    </div>

                    <div className="bg-white p-3.5 rounded-xl border border-emerald-200/80 shadow-2xs space-y-2 text-[12.5px]">
                      <p className="text-slate-800 leading-relaxed">
                        {currentCase.customerUpdate.resolutionSummary}
                      </p>
                      <div className="pt-2 border-t border-slate-100 text-[12px] text-slate-600 flex items-start gap-1.5">
                        <strong className="text-emerald-800 shrink-0">{t("Chỉ dẫn tiếp theo:")}</strong>
                        <span>
                          {currentCase.customerUpdate.nextStepGuidance?.toLowerCase().includes(t("khách hàng xác nhận"))
                            ? t("Quý khách vui lòng kiểm tra lại tình trạng xe và chọn xác nhận bên dưới nếu sự cố đã được khắc phục hoàn toàn.")
                            : currentCase.customerUpdate.nextStepGuidance}
                        </span>
                      </div>
                    </div>

                    {/* NÚT XÁC NHẬN CỦA KHÁCH HÀNG (ADR-005) */}
                    {confirmStatus === "IDLE" && currentCase.status === "Resolved" && (
                      <div className="pt-1 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2.5 bg-white p-3 rounded-xl border border-emerald-200">
                        <span className="text-[12px] text-slate-700 font-medium">
                          {t("Anh/chị đã hài lòng với kết quả xử lý của kỹ thuật viên chưa?")}</span>

                        <div className="flex items-center gap-2 shrink-0">
                          <button
                            type="button"
                            disabled={isSubmittingConfirm}
                            onClick={handleConfirmResolved}
                            className="inline-flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-[12px] font-semibold transition active:scale-[0.98] disabled:opacity-50"
                          >
                            <ThumbsUp className="w-3.5 h-3.5" />
                            <span>{t("Đã được hỗ trợ")}</span>
                          </button>

                          <button
                            type="button"
                            disabled={isSubmittingConfirm}
                            onClick={() => setConfirmStatus("REOPEN_REQUESTED")}
                            className="inline-flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-xl border border-amber-300 bg-amber-50 hover:bg-amber-100 text-amber-800 text-[12px] font-semibold transition active:scale-[0.98] disabled:opacity-50"
                          >
                            <RotateCcw className="w-3.5 h-3.5" />
                            <span>{t("Vẫn chưa giải quyết")}</span>
                          </button>
                        </div>
                      </div>
                    )}

                    {/* Form mở lại ca nếu bấm "Vẫn chưa giải quyết" */}
                    {confirmStatus === "REOPEN_REQUESTED" && currentCase.status !== "Reopened" && (
                      <div className="bg-white p-3.5 rounded-xl border border-amber-200 space-y-2 animate-fadeIn">
                        <label className="block text-[12px] font-semibold text-amber-900">
                          {t("Vui lòng cho biết vấn đề xe chưa khắc phục để Cố vấn kiểm tra lại:")}</label>
                        <textarea
                          rows={2}
                          value={reopenReason}
                          onChange={(e) => setReopenReason(e.target.value)}
                          placeholder={t("VD: Đèn cảnh báo vẫn còn sáng lại khi xe di chuyển...")}
                          className="w-full text-[12px] p-2.5 rounded-lg border border-amber-300 bg-white text-slate-900 focus:outline-none focus:ring-2 focus:ring-amber-400"
                        />
                        <div className="flex justify-end gap-2">
                          <button
                            type="button"
                            onClick={() => setConfirmStatus("IDLE")}
                            className="px-3 py-1 rounded-lg text-[12px] text-slate-600 hover:bg-slate-100"
                          >
                            {t("Hủy")}</button>
                          <button
                            type="button"
                            disabled={isSubmittingConfirm}
                            onClick={handleReopenSubmit}
                            className="px-3 py-1 rounded-lg bg-amber-600 hover:bg-amber-700 text-white text-[12px] font-semibold"
                          >
                            {isSubmittingConfirm ? t("Đang gửi...") : t("Gửi yêu cầu kiểm tra lại")}
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
                        {t("Cập nhật trao đổi gần nhất")}</span>

                      {currentCase.chatSnippet.length > 2 && (
                        <button
                          type="button"
                          onClick={() => setShowAllChat(!showAllChat)}
                          className="text-[11.5px] text-[#1E40AF] hover:underline font-medium inline-flex items-center gap-0.5"
                        >
                          <span>{showAllChat ? t("Thu gọn trao đổi") : `Xem toàn bộ trao đổi (${currentCase.chatSnippet.length})`}</span>
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
                            className={`px-1.5 py-0.2 rounded text-[10px] font-bold font-mono shrink-0 mt-0.5 ${msg.sender === "CUSTOMER"
                              ? "bg-blue-100 text-[#1E40AF]"
                              : msg.sender === "STAFF"
                                ? "bg-purple-100 text-purple-700"
                                : "bg-emerald-100 text-emerald-800"
                              }`}
                          >
                            {msg.sender === "CUSTOMER" ? t("BẠN") : msg.sender === "STAFF" ? "KTV" : "AI"}
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
                    <span>{t("Tiếp tục trao đổi trong Trợ lý Chat")}</span>
                  </Link>
                </div>

                {/* 7. ĐÁNH GIÁ 5 SAO KHI CA HOÀN TẤT */}
                {(currentCase.status === "Closed" || confirmStatus === "RESOLVED_CONFIRMED") && !isFeedbackDismissed && (
                  <div className="p-4 sm:p-5 bg-slate-50/70 border-t border-slate-100 space-y-3 animate-fadeIn">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Star className="h-4 w-4 text-amber-500 fill-amber-500" />
                        <h3 className="text-[13px] font-bold text-slate-900">
                          {t("Đánh giá chất lượng hỗ trợ")}</h3>
                      </div>
                      <button
                        type="button"
                        onClick={() => setIsFeedbackDismissed(true)}
                        className="text-[11px] text-slate-400 hover:text-slate-600 transition"
                      >
                        {t("Đóng")}</button>
                    </div>

                    {feedbackSubmitted ? (
                      <div className="rounded-xl bg-emerald-50 border border-emerald-200 p-2.5 text-[12.5px] font-semibold text-emerald-800 flex items-center gap-2">
                        <Check className="h-4 w-4 text-emerald-600" />
                        {t("Đã ghi nhận đánh giá của anh/chị. Cảm ơn anh/chị đã đóng góp ý kiến!")}</div>
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
                                className={`h-5 w-5 ${star <= feedbackRating
                                  ? "fill-amber-400 text-amber-400"
                                  : "text-slate-300"
                                  }`}
                              />
                            </button>
                          ))}
                          <span className="ml-2 text-[12px] font-semibold text-slate-700">
                            {feedbackRating === 5
                              ? t("Rất hài lòng")
                              : feedbackRating === 4
                                ? t("Hài lòng")
                                : feedbackRating === 3
                                  ? t("Bình thường")
                                  : t("Chưa hài lòng")}
                          </span>
                        </div>

                        {/* Tag lý do nhanh khi chấm 1 đến 2 sao */}
                        {feedbackRating <= 2 && (
                          <div className="p-2.5 rounded-xl bg-amber-50/80 border border-amber-200/80 space-y-1.5">
                            <span className="text-[11px] text-amber-800 font-semibold block">
                              {t("Lý do chưa hài lòng (chọn nhanh):")}</span>
                            <div className="flex flex-wrap gap-1.5">
                              {[t("Chờ hỗ trợ lâu"), t("Lỗi xe chưa hết"), t("Hướng dẫn khó hiểu"), t("Thái độ chưa tốt")].map((tag) => {
                                const isSelected = selectedFeedbackTags.includes(tag);
                                return (
                                  <button
                                    key={tag}
                                    type="button"
                                    onClick={() => {
                                      setSelectedFeedbackTags((prev) =>
                                        isSelected ? prev.filter((t) => t !== tag) : [...prev, tag]
                                      );
                                    }}
                                    className={`px-2 py-0.5 rounded-lg text-[11px] font-medium transition ${
                                      isSelected
                                        ? "bg-amber-600 text-white font-semibold shadow-xs"
                                        : "bg-white text-amber-900 border border-amber-200 hover:bg-amber-100"
                                    }`}
                                  >
                                    {isSelected ? "✓ " : "+ "}
                                    {tag}
                                  </button>
                                );
                              })}
                            </div>
                          </div>
                        )}

                        <textarea
                          value={feedbackComment}
                          onChange={(e) => setFeedbackComment(e.target.value)}
                          placeholder={t("Ý kiến đóng góp thêm về tốc độ và chất lượng phục vụ (tùy chọn)...")}
                          rows={2}
                          className="w-full rounded-xl border border-slate-200 bg-white p-2.5 text-[12px] text-slate-900 focus:border-[#1E40AF] focus:outline-none"
                        />

                        <div className="flex items-center justify-end gap-2 pt-0.5">
                          <button
                            type="button"
                            onClick={() => setIsFeedbackDismissed(true)}
                            className="px-3 py-1.5 rounded-xl text-[12px] font-medium text-slate-500 hover:text-slate-800 hover:bg-slate-100 transition"
                          >
                            {t("Để sau")}</button>
                          <button
                            type="button"
                            disabled={isSubmittingFeedback}
                            onClick={() => handleSubmitFeedback(currentCase.id)}
                            className="rounded-xl bg-emerald-600 hover:bg-emerald-700 px-4 py-1.5 text-[12px] font-semibold text-white transition disabled:opacity-60"
                          >
                            {isSubmittingFeedback ? t("Đang gửi...") : t("Gửi đánh giá")}
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
              {/* =======================================================
                  RESCUE HOTLINE: HIỂN THỊ ĐẦU TIÊN, NỔI BẬT NẾU SỰ CỐ NẶNG
              ======================================================= */}
              {servicePointsData?.rescue_hotline && (
                <div className="rounded-2xl border-2 border-red-500 bg-red-50 p-4 shadow-sm space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <PhoneCall className="w-5 h-5 text-red-600 animate-pulse" />
                      <span className="text-[12.5px] font-bold text-red-900 uppercase tracking-wide">
                        Hotline Cứu hộ Khẩn cấp 24/7
                      </span>
                    </div>
                    <span className="px-2 py-0.5 rounded-full bg-red-600 text-white text-[10px] font-bold tracking-wider">
                      ƯU TIÊN
                    </span>
                  </div>

                  <p className="text-[12px] text-red-800 leading-relaxed">
                    Hồ sơ được xác định thuộc tình trạng cần cứu hộ khẩn cấp hoặc không thể di chuyển an toàn. Vui lòng bấm gọi ngay để điều xe cứu hộ:
                  </p>

                  <a
                    href={`tel:${servicePointsData.rescue_hotline.replace(/[^0-9]/g, "")}`}
                    className="flex items-center justify-center gap-2 w-full py-2.5 px-4 rounded-xl bg-red-600 hover:bg-red-700 text-white font-bold text-[13.5px] shadow-sm transition active:scale-[0.98]"
                  >
                    <PhoneCall className="w-4 h-4" />
                    <span>☎ {servicePointsData.rescue_hotline}</span>
                  </a>
                </div>
              )}

              {/* Card 1: Thông Tin Xe & Dữ Kiện Kỹ Thuật (Key-Value Sát Nhau) */}
              <div className="bg-white rounded-2xl shadow-xs border border-slate-200/80 p-4 sm:p-5 space-y-3">
                <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
                  <h3 className="text-[13.5px] font-bold text-slate-900 flex items-center gap-1.5">
                    <Car className="w-4 h-4 text-[#1E40AF]" />
                    <span>{t("Thông tin xe & Dữ kiện")}</span>
                  </h3>
                  <span className="text-[11px] font-mono text-slate-400">
                    {currentCase.vehicleCode}
                  </span>
                </div>

                {/* Key-Value Pairs đặt sát nhau, không kéo ngang tạo khoảng trống */}
                <div className="space-y-2 text-[12.5px]">
                  <div className="flex items-center justify-between py-1 border-b border-slate-50">
                    <span className="text-slate-500">{t("Dòng xe:")}</span>
                    <span className="font-semibold text-slate-900">{currentCase.vehicleModel}</span>
                  </div>

                  <div className="flex items-center justify-between py-1 border-b border-slate-50">
                    <span className="text-slate-500">{t("Mức pin (SoC):")}</span>
                    <span
                      className={`font-semibold ${String(currentCase.currentSoc).includes("< 10%") ||
                        String(currentCase.currentSoc).includes("18%")
                        ? "text-amber-600"
                        : "text-slate-900"
                        }`}
                    >
                      {currentCase.currentSoc || t("Đang xác minh")}
                    </span>
                  </div>

                  <div className="flex items-center justify-between py-1 border-b border-slate-50">
                    <span className="text-slate-500">{t("Cảnh báo / Hiện tượng:")}</span>
                    {currentCase.warningSymbol ? (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded font-semibold text-[11.5px] bg-amber-50 text-amber-800 border border-amber-200">
                        <AlertCircle className="w-3.5 h-3.5 text-amber-600" />
                        <span>{currentCase.warningSymbol}</span>
                      </span>
                    ) : currentCase.errorCode ? (
                      <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded font-mono font-bold text-[11.5px] bg-red-50 text-red-700 border border-red-200">
                        <AlertCircle className="w-3 h-3 text-red-600" />
                        {currentCase.errorCode}
                      </span>
                    ) : (
                      <span className="text-slate-500 font-medium">{t("Bình thường")}</span>
                    )}
                  </div>

                  {currentCase.errorCode && currentCase.warningSymbol && (
                    <div className="flex items-center justify-between py-1 border-b border-slate-50">
                      <span className="text-slate-500">{t("Mã lỗi hệ thống:")}</span>
                      <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded font-mono font-bold text-[11px] bg-red-50 text-red-700 border border-red-200">
                        <AlertCircle className="w-3 h-3 text-red-600" />
                        {currentCase.errorCode}
                      </span>
                    </div>
                  )}

                  {currentCase.chargerId && (
                    <div className="flex items-center justify-between py-1 border-b border-slate-50">
                      <span className="text-slate-500">{t("Trụ sạc:")}</span>
                      <span className="font-medium text-slate-800 text-right truncate max-w-[170px]">
                        {currentCase.chargerId}
                      </span>
                    </div>
                  )}

                  {/* Mục phụ cho vào "Xem thêm" */}
                  {showTechDetails && (
                    <div className="pt-1.5 space-y-2 text-[12px] text-slate-600 bg-slate-50/70 p-2.5 rounded-xl border border-slate-100 animate-fadeIn">
                      <div className="flex items-center justify-between">
                        <span>{t("Chia sẻ GPS:")}</span>
                        <span className="font-medium">
                          {currentCase.locationConsent === "GRANTED" || currentCase.locationShared
                            ? t("Đã cấp quyền")
                            : currentCase.locationConsent === "MANUAL"
                              ? t("Nhập thủ công")
                              : t("Chưa bật")}
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span>{t("Chuyên viên phụ trách:")}</span>
                        <span className="font-medium text-slate-800 truncate max-w-[150px]">
                          {currentCase.assignedTo || t("Đội hỗ trợ VinFast")}
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span>{t("Thời gian tạo:")}</span>
                        <span className="font-mono text-slate-500">{currentCase.createdAt}</span>
                      </div>
                    </div>
                  )}

                  <button
                    type="button"
                    onClick={() => setShowTechDetails(!showTechDetails)}
                    className="w-full text-center text-[11.5px] text-[#1E40AF] hover:underline font-medium pt-1 block"
                  >
                    {showTechDetails ? t("Thu gọn thông số ▲") : t("Xem thêm thông số phụ ▼")}
                  </button>
                </div>
              </div>

              {/* =======================================================
                  Card 2: ĐIỂM DỊCH VỤ VINFAST ĐỀ XUẤT + BẢN ĐỒ VIETMAP
              ======================================================= */}
              <div className="bg-white rounded-2xl shadow-xs border border-slate-200/80 p-4 sm:p-5 space-y-3">
                <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
                  <h3 className="text-[13.5px] font-bold text-slate-900 flex items-center gap-1.5">
                    <MapPin className="w-4 h-4 text-[#1E40AF]" />
                    <span>Điểm hỗ trợ VinFast</span>
                  </h3>
                  <div className="flex items-center gap-1.5">
                    {servicePointsData?.needs_location ? (
                      <span className="text-[11px] px-2 py-0.5 rounded-full font-semibold text-amber-700 bg-amber-50 border border-amber-200/80">
                        Gợi ý theo khu vực
                      </span>
                    ) : (
                      <span className="text-[11px] px-2 py-0.5 rounded-full font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200/80">
                        Đã xác định vị trí
                      </span>
                    )}
                  </div>
                </div>

                {/* Nút chia sẻ vị trí khi needs_location = true và chưa chia sẻ thành công */}
                {servicePointsData?.needs_location && !servicePointsData?.no_points_nearby && (
                  <div className="p-2.5 rounded-xl bg-blue-50/70 border border-blue-100 flex items-center justify-between gap-2">
                    <p className="text-[11.5px] text-blue-900 leading-snug">
                      Chưa có GPS chính xác. Bấm để tìm điểm gần nhất theo vị trí thực tế của bạn.
                    </p>
                    <button
                      type="button"
                      onClick={handleShareLocation}
                      disabled={isRequestingLocation}
                      className="shrink-0 px-2.5 py-1 rounded-lg bg-[#1E40AF] hover:bg-blue-700 text-white text-[11px] font-semibold transition flex items-center gap-1 disabled:opacity-50"
                    >
                      {isRequestingLocation ? (
                        <>
                          <Loader2 className="w-3 h-3 animate-spin" />
                          <span>Đang lấy...</span>
                        </>
                      ) : (
                        <>
                          <Navigation className="w-3 h-3" />
                          <span>Chia sẻ vị trí</span>
                        </>
                      )}
                    </button>
                  </div>
                )}

                {/* Nhãn ngày thu thập dữ liệu */}
                <div className="text-[11px] text-slate-400">
                  Trạng thái tại ngày thu thập:{" "}
                  <span className="font-medium text-slate-600">
                    {servicePointsData?.last_updated_label || "Tháng 10/2026"}
                  </span>
                </div>

                {/* Mini Map Vietmap (Tự động ẩn nếu thiếu key, card vẫn hiện) */}
                <VietmapMiniMap
                  points={servicePointsData?.recommended_points || []}
                  userLocation={clientUserCoord}
                  lastUpdatedLabel={servicePointsData?.last_updated_label || undefined}
                />

                {/* Danh sách các card điểm dịch vụ */}
                <div className="space-y-3 pt-1">
                  {(servicePointsData?.recommended_points || []).length === 0 ? (
                    servicePointsData?.no_points_nearby ? (
                      <div className="p-3.5 rounded-xl bg-amber-50 border border-amber-200/80 text-amber-900 text-[12px] space-y-2 text-center">
                        <p className="font-semibold leading-relaxed">
                          {servicePointsData.message || "Chưa có điểm dịch vụ trong 150 km quanh vị trí của Quý khách; vui lòng gọi hotline"}
                        </p>
                        <a
                          href="tel:1900232389"
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-700 text-white font-bold text-[11.5px] transition"
                        >
                          <PhoneCall className="w-3.5 h-3.5" />
                          <span>Hotline VinFast: 1900-232389</span>
                        </a>
                      </div>
                    ) : currentCase?.locationShared && currentCase?.stationLocation ? (
                      <div className="space-y-2 text-[12.5px]">
                        <div>
                          <h4 className="font-semibold text-slate-900 leading-snug">
                            {currentCase.stationLocation}
                          </h4>
                          <p className="text-[11.5px] text-slate-500 mt-0.5 leading-relaxed">
                            {t("Vị trí đã được chia sẻ và xác minh từ thiết bị.")}
                          </p>
                        </div>
                        <div className="pt-2 flex items-center justify-end">
                          <a
                            href={`https://maps.google.com/?q=${encodeURIComponent(currentCase.stationLocation)}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 px-3 py-1.5 rounded-xl bg-blue-50 text-[#1E40AF] hover:bg-blue-100 text-[11.5px] font-semibold transition"
                          >
                            <Navigation className="w-3 h-3" />
                            <span>{t("Chỉ đường")}</span>
                          </a>
                        </div>
                      </div>
                    ) : (
                      <p className="text-[12px] text-slate-500 py-2 text-center">
                        {servicePointsData?.message || "Đang tìm kiếm các điểm dịch vụ phù hợp trong khu vực..."}
                      </p>
                    )
                  ) : (
                    (servicePointsData?.recommended_points || []).map((point, idx) => {
                      const isWorkshop = point.category === "workshop";
                      const isCharging = point.category === "charging_station";
                      const isGsm = point.category_slug === "service_gsm";
                      const hasDongSon = point.dong_son || point.services_offered?.includes("dong_son");

                      // Link chỉ đường bằng tọa độ đích nếu có
                      const directionsHref =
                        point.latitude && point.longitude
                          ? `https://www.google.com/maps/dir/?api=1&destination=${point.latitude},${point.longitude}`
                          : `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(point.address)}`;

                      return (
                        <div
                          key={point.id || idx}
                          className="p-3 rounded-xl border border-slate-200/90 hover:border-blue-300 bg-slate-50/60 hover:bg-white transition space-y-2 text-[12px]"
                        >
                          {/* Header điểm: Tên + Badges */}
                          <div className="flex items-start justify-between gap-2">
                            <div>
                              <h4 className="font-semibold text-slate-900 leading-snug">
                                {idx + 1}. {point.name}
                              </h4>
                              <p className="text-[11.5px] text-slate-500 mt-0.5 leading-relaxed">
                                {point.address}
                              </p>
                            </div>
                            <div className="flex flex-col items-end gap-1 shrink-0">
                              {isWorkshop && (
                                <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-blue-800">
                                  Xưởng 2S
                                </span>
                              )}
                              {isCharging && (
                                <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800">
                                  Trạm sạc
                                </span>
                              )}
                              {hasDongSon && (
                                <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-purple-100 text-purple-800">
                                  Đồng sơn
                                </span>
                              )}
                              {isGsm && (
                                <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800">
                                  Taxi GSM
                                </span>
                              )}
                            </div>
                          </div>

                          {/* Thông tin đặc thù từng loại điểm */}
                          {isCharging && (
                            <div className="text-[11.5px] text-slate-500 italic">
                              ⚡ Chưa công bố công suất
                            </div>
                          )}

                          {isWorkshop && (
                            <div className="space-y-1 text-[11.5px] text-slate-600">
                              <div>
                                <span className="text-slate-400">Giờ mở cửa:</span>{" "}
                                <span className="font-medium text-slate-700">
                                  {point.operating_hours || point.hours || "08:00 - 18:00"}
                                </span>
                              </div>
                              {point.hotline_service && (
                                <div>
                                  <span className="text-slate-400">Hotline xưởng:</span>{" "}
                                  <a
                                    href={`tel:${point.hotline_service.replace(/[^0-9]/g, "")}`}
                                    className="font-semibold text-blue-700 hover:underline"
                                  >
                                    ☎ {point.hotline_service}
                                  </a>
                                </div>
                              )}
                            </div>
                          )}

                          {/* Ghi chú lưu ý (GSM / Đồng sơn) */}
                          {point.note && (
                            <div className="p-2 rounded-lg bg-amber-50/80 border border-amber-200/70 text-[11px] text-amber-900 leading-snug">
                              ⚠ {point.note}
                            </div>
                          )}

                          {/* Khoảng cách + Nút Chỉ đường & Đặt lịch */}
                          <div className="pt-1.5 flex flex-wrap items-center justify-between gap-1 border-t border-slate-100">
                            {(() => {
                              if (point.distance_km != null) {
                                return (
                                  <span className="text-[11px] text-slate-500 font-mono">
                                    Cách Quý khách: {point.distance_km} km
                                  </span>
                                );
                              }
                              if (point.distance_from_area_km != null) {
                                const areaLabel = servicePointsData?.area_reference?.label || "khu vực";
                                const roundedKm = Math.round(point.distance_from_area_km);
                                const nStr = roundedKm < 5 ? "dưới 5 km" : `${roundedKm} km`;
                                return (
                                  <span className="text-[11px] text-slate-500 font-mono">
                                    Khoảng {nStr} từ {areaLabel} (đường chim bay, không phải khoảng cách từ vị trí của Quý khách)
                                  </span>
                                );
                              }
                              return <span />;
                            })()}

                            <div className="flex items-center gap-1.5">
                              {point.booking_url && (
                                <a
                                  href={point.booking_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-emerald-50 text-emerald-700 hover:bg-emerald-100 text-[11px] font-semibold transition"
                                >
                                  <span>Đặt lịch</span>
                                </a>
                              )}
                              <a
                                href={directionsHref}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-blue-50 text-[#1E40AF] hover:bg-blue-100 text-[11px] font-semibold transition"
                              >
                                <Navigation className="w-3 h-3" />
                                <span>Chỉ đường</span>
                              </a>
                            </div>
                          </div>
                        </div>
                      );
                    })
                  )}

                </div>
              </div>

              {/* Card 3: Hotline Khẩn Cấp VinFast chung */}
              <div className="rounded-2xl border border-slate-200/80 bg-slate-50/70 p-4 space-y-2">
                <div className="flex items-center gap-2">
                  <PhoneCall className="w-4 h-4 text-red-600" />
                  <span className="text-[12px] font-bold text-red-900 uppercase tracking-wide">
                    {t("Hỗ trợ khẩn cấp 24/7")}
                  </span>
                </div>

                <p className="text-[12px] text-slate-600">
                  {t("Nếu xe gặp sự cố nguy hiểm trên đường hoặc cần cứu hộ khẩn cấp:")}
                </p>

                <a
                  href="tel:1900232389"
                  className="block w-full text-center py-2 px-3 rounded-xl bg-slate-800 hover:bg-slate-900 text-white font-bold text-[12.5px] transition"
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
                    placeholder={t("Tìm theo triệu chứng, mã lỗi (VD: CC01, rùa vàng, lốp xe, sạc nhà)...")}
                    className="w-full pl-9 pr-3 py-2 rounded-xl bg-slate-50 border border-slate-200 text-[12.5px] text-slate-900 focus:outline-none focus:bg-white focus:border-[#1E40AF]"
                  />
                </div>

                <div className="text-[11.5px] text-slate-500 shrink-0">
                  {t("Nguồn:")}<strong className="text-slate-700">{t("Tài liệu chính thức VinFast")}</strong>
                </div>
              </div>

              {/* Chips Lọc Nhóm Tình Huống */}
              <div className="flex items-center gap-1.5 flex-wrap pt-1 border-t border-slate-100">
                {[
                  { id: "ALL", label: t("Tất cả") },
                  { id: "CHARGING", label: t("Sạc & Pin") },
                  { id: "DASHBOARD", label: t("Cảnh báo táp-lô") },
                  { id: "WALLBOX", label: t("Sạc tại nhà") },
                  { id: "TIRE", label: t("Lốp & Khung gầm") },
                ].map((c) => (
                  <button
                    key={c.id}
                    type="button"
                    onClick={() => setTopicCategory(c.id)}
                    className={`px-3 py-1 rounded-lg text-[12px] font-medium transition ${topicCategory === c.id
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
                          {t(topic.categoryLabel)}
                        </span>
                        <h3 className="text-[13.5px] font-bold text-slate-900 truncate">
                          {t(topic.title)}
                        </h3>
                      </div>

                      <ChevronDown
                        className={`w-4 h-4 text-slate-400 shrink-0 transition-transform duration-200 ${isOpen ? "rotate-180 text-[#1E40AF]" : ""
                          }`}
                      />
                    </button>

                    {/* Nội dung chi tiết chỉ mở ra khi bấm (150-200ms ease) */}
                    {isOpen && (
                      <div className="p-4 sm:p-5 border-t border-slate-100 bg-slate-50/40 space-y-4 animate-fadeIn">
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-[12.5px]">
                          <div className="space-y-1.5">
                            <span className="font-bold text-slate-800 block text-[12px]">
                              {t("Dấu hiệu nhận biết:")}</span>
                            <ul className="space-y-1 list-disc pl-4 text-slate-600">
                              {topic.symptoms.map((s, i) => (
                                <li key={i}>{t(s)}</li>
                              ))}
                            </ul>
                          </div>

                          <div className="space-y-1.5">
                            <span className="font-bold text-slate-800 block text-[12px]">
                              {t("Dữ kiện nên chuẩn bị:")}</span>
                            <ul className="space-y-1 list-disc pl-4 text-slate-600">
                              {topic.preparation.map((p, i) => (
                                <li key={i}>{t(p)}</li>
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
                            <span>{t(topic.citationTitle)}</span>
                          </a>

                          {/* Nút Hỏi AI chỉ xuất hiện trong phần mở ra */}
                          <Link
                            href={`/chat?prompt=${encodeURIComponent(t(topic.suggestedPrompt))}`}
                            className="inline-flex items-center justify-center gap-1.5 px-4 py-2 rounded-xl bg-[#1E40AF] hover:bg-[#1D4ED8] text-white text-[12px] font-semibold transition shadow-2xs active:scale-[0.98]"
                          >
                            <Sparkles className="w-3.5 h-3.5" />
                            <span>{t("Hỏi Trợ lý Agent về tình huống này")}</span>
                          </Link>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}

              {filteredTopics.length === 0 && (
                <div className="bg-white rounded-2xl p-8 text-center text-slate-500 border border-slate-200/80">
                  <p className="text-[13px]">{t("Không tìm thấy tình huống nào phù hợp với từ khóa.")}</p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
