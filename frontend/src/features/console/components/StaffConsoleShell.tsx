"use client";

import { useState, useEffect, useCallback, useMemo, useRef } from "react";
import Link from "next/link";
import {
  ScanLine,
  LayoutDashboard,
  Inbox,
  History,
  GitBranch,
  BookOpen,
  Eye,
  User,
  LogOut,
  RefreshCw,
  Search,
  Filter,
  CheckCircle2,
  Clock,
  Flame,
  AlertCircle,
  Car,
  ChevronRight,
  ExternalLink,
  MessageSquare,
  ShieldCheck,
  MapPin,
  Sparkles,
  ArrowRight,
  X,
  Star,
  Check,
  PanelLeftClose,
  PanelLeftOpen,
  Send,
  Loader2,
  Bot,
} from "lucide-react";
import { useAuth, ProductMark } from "@/features/shared";
import { useTickets } from "../hooks/useTickets";
import { TicketItem, TicketStatus, VIETNAMESE_STATUS_MAP, VIETNAMESE_PRIORITY_MAP } from "../types";
import { TicketDetailPanel } from "./TicketDetailPanel";
import { sendChatMessage, getPublicArticles } from "@/features/chat/api/chatApi";
import { ArticleItem } from "@/features/chat/types";

export type ConsoleTab =
  | "queue"
  | "overview"
  | "history"
  | "routing"
  | "knowledge"
  | "preview"
  | "profile";

// Helper phân nhóm ngày cho danh sách Ticket
function getTicketDateLabel(dateStr: string): string {
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return "Khác";
    const now = new Date();

    const isToday =
      d.getDate() === now.getDate() &&
      d.getMonth() === now.getMonth() &&
      d.getFullYear() === now.getFullYear();
    if (isToday) return "Hôm nay";

    const yesterday = new Date(now);
    yesterday.setDate(now.getDate() - 1);
    const isYesterday =
      d.getDate() === yesterday.getDate() &&
      d.getMonth() === yesterday.getMonth() &&
      d.getFullYear() === yesterday.getFullYear();
    if (isYesterday) return "Hôm qua";

    const day = String(d.getDate()).padStart(2, "0");
    const month = String(d.getMonth() + 1).padStart(2, "0");
    return `${day}/${month}/${d.getFullYear()}`;
  } catch {
    return "Khác";
  }
}

// Rút gọn mã case: CASE-20261004-001 -> 001
function getShortTicketId(id: string): string {
  const match = id.match(/(\d{3,4})$/);
  if (match) return match[1];
  return id.replace(/^CASE-/i, "");
}

// Lấy tiêu đề sự cố thật từ tóm tắt AI hoặc fallback theo intent/xe
function getTicketDisplayTitle(ticket: TicketItem): string {
  if (
    ticket.issue_summary &&
    ticket.issue_summary.trim() &&
    ticket.issue_summary !== "Yêu cầu kiểm tra sự cố"
  ) {
    return ticket.issue_summary;
  }
  if (ticket.error_code_short) {
    return `Sự cố lỗi ${ticket.error_code_short} trên xe ${ticket.vehicle_model}`;
  }
  if (ticket.intent === "Charging/Battery") {
    return `Sự cố trạm sạc & pin xe ${ticket.vehicle_model}`;
  }
  if (ticket.intent === "Service/Incident") {
    return `Cảnh báo kỹ thuật vận hành xe ${ticket.vehicle_model}`;
  }
  if (ticket.intent.includes("Complaint")) {
    return `Phản ánh dịch vụ khách hàng xe ${ticket.vehicle_model}`;
  }
  return `Yêu cầu hỗ trợ kỹ thuật xe ${ticket.vehicle_model}`;
}

// 5 Bộ phận Routing chuẩn hóa P0
export const ROUTING_DEPARTMENTS = [
  {
    id: "charging_ops",
    name: "Charging Operations",
    badge: "Sạc & Pin",
    intent: "Charging/Battery",
    description: "Xử lý sự cố sạc tại trạm công cộng, trụ báo lỗi, lỗi giao tiếp BMS/0x41 hoặc kẹt súng sạc.",
    lead: "Vũ Hoàng Long (Trưởng nhóm)",
    activeTickets: 2,
    color: "bg-[#EFF3FC] text-[#1E40AF]",
  },
  {
    id: "service_center",
    name: "Service Center",
    badge: "Xưởng Dịch Vụ",
    intent: "Service/Incident",
    description: "Xử lý cảnh báo táp-lô, rùa vàng, lỗi 12V, lỗi điều hòa, đặt hẹn bảo dưỡng và kiểm tra OBD-II.",
    lead: "Trần Đình Triển (Cố vấn Dịch vụ)",
    activeTickets: 3,
    color: "bg-[#FEF3C7] text-[#D97706]",
  },
  {
    id: "customer_care",
    name: "Customer Care",
    badge: "Chăm Sóc Khách Hàng",
    intent: "Complaint/Feedback",
    description: "Tiếp nhận khiếu nại thái độ phục vụ, xe xăng chiếm chỗ sạc, trừ tiền trùng hoặc lỗi ứng dụng.",
    lead: "Nguyễn Mai Anh (CSKH)",
    activeTickets: 1,
    color: "bg-[#F3E8FF] text-[#7E22CE]",
  },
  {
    id: "sales_advisor",
    name: "Sales Advisor",
    badge: "Tư Vấn Bán Hàng",
    intent: "Sales/General Info",
    description: "Tiếp nhận nhu cầu lái thử, tư vấn thông số kỹ thuật xe VF 3 đến VF 9, giá lăn bánh và đặt cọc.",
    lead: "Phạm Quốc Hưng (Showroom Times City)",
    activeTickets: 0,
    color: "bg-[#ECFDF5] text-[#065F46]",
  },
  {
    id: "emergency_demo",
    name: "Emergency Support Demo",
    badge: "Cứu Hộ Khẩn Cấp",
    intent: "Critical Safety",
    description: "Đội điều phối cứu hộ giao thông 24/7 cho các ca cháy nổ, mất phanh, rùa vàng cao tốc (Hotline 1900-232389).",
    lead: "Đội phản ứng nhanh Cao Tốc VinFast",
    activeTickets: 1,
    color: "bg-[#FEF2F2] text-[#DC2626]",
  },
];

// Sample Lịch sử Case (Audit & Handover)
export interface HistoricalCase {
  id: string;
  intent: string;
  status: "Resolved" | "Closed" | "Reopened";
  routedTo: string;
  customerConfirmed: boolean;
  resolvedAt: string;
  staffName: string;
  vehicleModel: string;
  vehicleCode: string;
  briefSummary: string;
  hasLocationConsent: boolean;
  locationName?: string;
  customerFeedbackScore?: number;
  customerFeedbackComment?: string;
  reopenReason?: string;
  staffUpdateNotes: string;
}

export const SAMPLE_CASE_HISTORY: HistoricalCase[] = [
  {
    id: "CASE-20260924-001",
    intent: "Charging/Battery",
    status: "Closed",
    routedTo: "Charging Operations",
    customerConfirmed: true,
    resolvedAt: "02/10/2026 14:15",
    staffName: "Lê Hoàng Quân",
    vehicleModel: "VinFast VF8",
    vehicleCode: "VF8-PLUS-2023",
    briefSummary: "Trụ số 3 Landmark 81 báo lỗi 0x41 không cấp điện. KTV đã hướng dẫn reset giao thức và xe sạc lại bình thường.",
    hasLocationConsent: true,
    locationName: "Vincom Landmark 81, P.22, Bình Thạnh, TP.HCM",
    customerFeedbackScore: 5,
    customerFeedbackComment: "Hỗ trợ rất nhanh, AI nhận diện đúng mã lỗi táp-lô nên không phải nói lại nhiều.",
    staffUpdateNotes: "Trụ DC 250kW đã khởi động lại firmware, thông số sạc đạt 180kW ổn định.",
  },
  {
    id: "CASE-20260924-002",
    intent: "Service/Incident",
    status: "Resolved",
    routedTo: "Service Center",
    customerConfirmed: false,
    resolvedAt: "02/10/2026 11:30",
    staffName: "Lê Hoàng Quân",
    vehicleModel: "VinFast VF5",
    vehicleCode: "VF5-PLUS-2024",
    briefSummary: "Đèn báo rùa vàng do pin SoC xuống dưới 8%. Đã hướng dẫn khách di chuyển chậm tới trạm sạc gần nhất 500m.",
    hasLocationConsent: true,
    locationName: "Trạm sạc Vincom Metropolis, Liễu Giai, Hà Nội",
    staffUpdateNotes: "Khách đã cắm súng sạc thành công, theo dõi pin tăng lên 25%. Chờ khách xác nhận.",
  },
  {
    id: "CASE-20260923-088",
    intent: "Complaint/Feedback",
    status: "Reopened",
    routedTo: "Customer Care",
    customerConfirmed: false,
    resolvedAt: "01/10/2026 18:20",
    staffName: "Nguyễn Mai Anh",
    vehicleModel: "VinFast VF e34",
    vehicleCode: "VFe34-2022",
    briefSummary: "Khách phản ánh xe xăng chiếm 2 vị trí sạc tại hầm TTTM khiến không thể cắm dây.",
    hasLocationConsent: false,
    reopenReason: "Bảo vệ hầm chưa nhắc nhở xe xăng, khách quay lại vẫn không có chỗ sạc.",
    staffUpdateNotes: "Đã liên hệ ban quản lý tòa nhà cử bảo vệ giải tỏa vị trí sạc.",
  },
  {
    id: "CASE-20260922-045",
    intent: "Sales/General Info",
    status: "Closed",
    routedTo: "Sales Advisor",
    customerConfirmed: true,
    resolvedAt: "30/09/2026 16:45",
    staffName: "Phạm Quốc Hưng",
    vehicleModel: "VinFast VF7",
    vehicleCode: "VF7-ECO-2024",
    briefSummary: "Khách đăng ký lái thử VF7 Plus tại Showroom Times City vào 10:00 thứ Bảy.",
    hasLocationConsent: true,
    locationName: "Showroom VinFast Times City, Hai Bà Trưng, Hà Nội",
    customerFeedbackScore: 5,
    customerFeedbackComment: "Tư vấn rõ ràng thông số 349 mã lực và tầm hoạt động.",
    staffUpdateNotes: "Đã xếp xe lái thử màu Trắng ngọc trai cho khách hàng.",
  },
];

export function StaffConsoleShell() {
  const { user, logout } = useAuth();
  const [activeTab, setActiveTab] = useState<ConsoleTab>("queue");

  // Sidebar collapsible state: default expanded (w-64)
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

  // Tickets state từ hook useTickets
  const {
    filteredTickets,
    statusFilter,
    setStatusFilter,
    priorityFilter,
    setPriorityFilter,
    searchQuery,
    setSearchQuery,
    loading,
    refreshTickets,
    stats,
    isLiveApi,
  } = useTickets();

  // Active selected ticket for Master-Detail view in Queue
  const [selectedTicketId, setSelectedTicketId] = useState<string | null>(null);

  // Local statuses for interactive updates
  const [localTicketStatuses, setLocalTicketStatuses] = useState<Record<string, TicketStatus>>({});

  // Notification when action is completed
  const [routingConfirmedNotice, setRoutingConfirmedNotice] = useState<string | null>(null);

  // Quick Queue Priority/Status Filter Pills
  const [queueQuickFilter, setQueueQuickFilter] = useState<string>("ALL");

  // History tab modal review
  const [reviewingHistoryCase, setReviewingHistoryCase] = useState<HistoricalCase | null>(null);
  const [historyStatusFilter, setHistoryStatusFilter] = useState<string>("ALL");
  const [historyIntentFilter, setHistoryIntentFilter] = useState<string>("ALL");

  // Customer Preview live chat session
  const previewSessionId = useRef<string>("staff_preview_" + Math.random().toString(36).substring(2, 9));
  const [previewChatInput, setPreviewChatInput] = useState("");
  const [isPreviewSending, setIsPreviewSending] = useState(false);
  const [previewMessages, setPreviewMessages] = useState<
    Array<{
      sender: "user" | "bot";
      text: string;
      intent?: string;
      priority?: string;
      citations?: Array<{ title?: string; url?: string; source_id?: string }>;
    }>
  >([
    {
      sender: "bot",
      text: "Dạ VinFast xin chào anh/chị! Em là Trợ lý AI Dịch vụ Khách hàng VinFast. Anh/chị có thể nhập thử câu hỏi về lỗi táp-lô, trụ sạc, hoặc thông số xe để kiểm thử bóc tách Intent và RAG theo thời gian thực.",
    },
  ]);

  // Live Knowledge Hub articles from backend
  const [knowledgeArticles, setKnowledgeArticles] = useState<ArticleItem[]>([]);

  useEffect(() => {
    let isMounted = true;
    getPublicArticles()
      .then((res) => {
        if (isMounted && res?.data?.articles && res.data.articles.length > 0) {
          setKnowledgeArticles(res.data.articles);
        }
      })
      .catch(() => {
        // Fallback to verified catalog
      });
    return () => {
      isMounted = false;
    };
  }, []);

  const handleStatusUpdate = (ticketId: string, newStatus: TicketStatus) => {
    setLocalTicketStatuses((prev) => ({ ...prev, [ticketId]: newStatus }));
  };

  const ticketsWithLocalStatus = filteredTickets.map((t) => ({
    ...t,
    status: localTicketStatuses[t.id] || t.status,
  }));

  // Lọc hàng đợi xử lý: chỉ tập trung các hồ sơ cần can thiệp
  const activeQueueTickets = ticketsWithLocalStatus.filter((t) => {
    if (queueQuickFilter === "CRITICAL") return t.priority === "CRITICAL";
    if (queueQuickFilter === "Staff Reviewing") return t.status === "Staff Reviewing";
    if (queueQuickFilter === "Needs Information") return t.status === "Needs Information";
    if (queueQuickFilter === "In Progress") return t.status === "In Progress";

    return (
      t.status === "Staff Reviewing" ||
      t.status === "Needs Information" ||
      t.status === "In Progress" ||
      t.priority === "CRITICAL"
    );
  });

  // Đồng bộ selectedTicketId từ URL parameter '?case=...' khi trang tải
  useEffect(() => {
    if (typeof window !== "undefined") {
      const p = new URLSearchParams(window.location.search).get("case");
      if (p) {
        setSelectedTicketId(p);
      }
    }
  }, []);

  // Lắng nghe sự kiện Back/Forward của trình duyệt để đổi case tương ứng
  useEffect(() => {
    const handlePopState = () => {
      if (typeof window !== "undefined") {
        const p = new URLSearchParams(window.location.search).get("case");
        if (p) {
          setSelectedTicketId(p);
        }
      }
    };
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  // Chọn case đồng thời cập nhật URL mà không reload trang
  const handleSelectTicket = useCallback((ticketId: string) => {
    setSelectedTicketId(ticketId);
    if (typeof window !== "undefined") {
      const url = new URL(window.location.href);
      url.searchParams.set("case", ticketId);
      window.history.pushState({ caseId: ticketId }, "", url.toString());
    }
  }, []);

  const currentActiveTicket =
    activeQueueTickets.find((t) => t.id === selectedTicketId) || activeQueueTickets[0] || null;

  // Phân nhóm danh sách ticket theo ngày
  const groupedQueueTickets = useMemo(() => {
    const groups: { dateLabel: string; tickets: TicketItem[] }[] = [];
    activeQueueTickets.forEach((t) => {
      const label = getTicketDateLabel(t.created_at);
      let group = groups.find((g) => g.dateLabel === label);
      if (!group) {
        group = { dateLabel: label, tickets: [] };
        groups.push(group);
      }
      group.tickets.push(t);
    });
    return groups;
  }, [activeQueueTickets]);

  // Phím tắt ↑ ↓ (hoặc J/K) để duyệt nhanh qua danh sách case và tự cuộn vào khung nhìn
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (
        target.tagName === "INPUT" ||
        target.tagName === "TEXTAREA" ||
        target.tagName === "SELECT" ||
        target.isContentEditable
      ) {
        return;
      }

      if (activeTab !== "queue" || activeQueueTickets.length === 0) return;

      if (e.key === "ArrowDown" || e.key === "j" || e.key === "J") {
        e.preventDefault();
        const currentIndex = activeQueueTickets.findIndex(
          (t) => t.id === currentActiveTicket?.id
        );
        const nextIndex =
          currentIndex < activeQueueTickets.length - 1 ? currentIndex + 1 : 0;
        const nextTicket = activeQueueTickets[nextIndex];
        if (nextTicket) {
          handleSelectTicket(nextTicket.id);
          const el = document.getElementById(`ticket-item-${nextTicket.id}`);
          el?.scrollIntoView({ block: "nearest", behavior: "smooth" });
        }
      } else if (e.key === "ArrowUp" || e.key === "k" || e.key === "K") {
        e.preventDefault();
        const currentIndex = activeQueueTickets.findIndex(
          (t) => t.id === currentActiveTicket?.id
        );
        const prevIndex =
          currentIndex > 0 ? currentIndex - 1 : activeQueueTickets.length - 1;
        const prevTicket = activeQueueTickets[prevIndex];
        if (prevTicket) {
          handleSelectTicket(prevTicket.id);
          const el = document.getElementById(`ticket-item-${prevTicket.id}`);
          el?.scrollIntoView({ block: "nearest", behavior: "smooth" });
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [activeTab, activeQueueTickets, currentActiveTicket?.id, handleSelectTicket]);

  // Dynamic Intent Distribution derived from ticketsWithLocalStatus
  const intentDistribution = useMemo(() => {
    const total = ticketsWithLocalStatus.length;
    if (total === 0) {
      return [
        { label: "Sạc & Pin (Charging/Battery)", key: "charging", count: 0, percent: 0, color: "bg-[#1E40AF]" },
        { label: "Kỹ thuật & Cảnh báo táp-lô (Service/Incident)", key: "service", count: 0, percent: 0, color: "bg-[#D97706]" },
        { label: "Khiếu nại & Phản hồi (Complaint)", key: "complaint", count: 0, percent: 0, color: "bg-[#7E22CE]" },
        { label: "Tư vấn xe & Bán hàng (Sales/FAQ)", key: "sales", count: 0, percent: 0, color: "bg-[#059669]" },
      ];
    }

    let chargingCount = 0;
    let serviceCount = 0;
    let complaintCount = 0;
    let salesCount = 0;

    ticketsWithLocalStatus.forEach((t) => {
      const it = (t.intent || "").toLowerCase();
      if (it.includes("charging") || it.includes("battery") || it.includes("sạc") || it.includes("pin")) {
        chargingCount++;
      } else if (it.includes("complaint") || it.includes("feedback") || it.includes("khiếu nại")) {
        complaintCount++;
      } else if (it.includes("sales") || it.includes("bán hàng") || it.includes("tư vấn") || it.includes("faq")) {
        salesCount++;
      } else {
        serviceCount++;
      }
    });

    return [
      {
        label: "Sạc & Pin (Charging/Battery)",
        key: "charging",
        count: chargingCount,
        percent: Math.round((chargingCount / total) * 100),
        color: "bg-[#1E40AF]",
      },
      {
        label: "Kỹ thuật & Cảnh báo táp-lô (Service/Incident)",
        key: "service",
        count: serviceCount,
        percent: Math.round((serviceCount / total) * 100),
        color: "bg-[#D97706]",
      },
      {
        label: "Khiếu nại & Phản hồi (Complaint)",
        key: "complaint",
        count: complaintCount,
        percent: Math.round((complaintCount / total) * 100),
        color: "bg-[#7E22CE]",
      },
      {
        label: "Tư vấn xe & Bán hàng (Sales/FAQ)",
        key: "sales",
        count: salesCount,
        percent: Math.round((salesCount / total) * 100),
        color: "bg-[#059669]",
      },
    ];
  }, [ticketsWithLocalStatus]);

  // Dynamic Routing Departments active count derived from ticketsWithLocalStatus
  const liveRoutingDepartments = useMemo(() => {
    const active = ticketsWithLocalStatus.filter(
      (t) => t.status !== "Resolved" && t.status !== "Closed"
    );

    return ROUTING_DEPARTMENTS.map((dept) => {
      let count = 0;
      if (dept.id === "emergency_demo") {
        count = active.filter((t) => t.priority === "CRITICAL").length;
      } else if (dept.id === "charging_ops") {
        count = active.filter((t) => {
          const it = (t.intent || "").toLowerCase();
          return (it.includes("charging") || it.includes("battery") || it.includes("sạc") || it.includes("pin")) && t.priority !== "CRITICAL";
        }).length;
      } else if (dept.id === "customer_care") {
        count = active.filter((t) => {
          const it = (t.intent || "").toLowerCase();
          return (it.includes("complaint") || it.includes("feedback") || it.includes("khiếu nại")) && t.priority !== "CRITICAL";
        }).length;
      } else if (dept.id === "sales_advisor") {
        count = active.filter((t) => {
          const it = (t.intent || "").toLowerCase();
          return (it.includes("sales") || it.includes("bán hàng") || it.includes("tư vấn") || it.includes("faq")) && t.priority !== "CRITICAL";
        }).length;
      } else if (dept.id === "service_center") {
        count = active.filter((t) => {
          const it = (t.intent || "").toLowerCase();
          const isOther = it.includes("charging") || it.includes("battery") || it.includes("complaint") || it.includes("sales");
          return !isOther && t.priority !== "CRITICAL";
        }).length;
      }

      return {
        ...dept,
        activeTickets: count,
      };
    });
  }, [ticketsWithLocalStatus]);

  // Dynamic Case History: Live resolved/closed cases from DB + sample archive
  const realCaseHistory = useMemo(() => {
    const fromDb = ticketsWithLocalStatus
      .filter((t) => t.status === "Resolved" || t.status === "Closed" || t.status === "Reopened")
      .map((t) => {
        let routed = "Service Center";
        const it = (t.intent || "").toLowerCase();
        if (it.includes("charging") || it.includes("battery") || it.includes("sạc") || it.includes("pin")) {
          routed = "Charging Operations";
        } else if (it.includes("complaint") || it.includes("feedback") || it.includes("khiếu nại")) {
          routed = "Customer Care";
        } else if (it.includes("sales") || it.includes("bán hàng")) {
          routed = "Sales Advisor";
        } else if (t.priority === "CRITICAL") {
          routed = "Emergency Support Demo";
        }

        let formattedTime = "Hôm nay";
        try {
          if (t.created_at) {
            const dt = new Date(t.created_at);
            if (!isNaN(dt.getTime())) {
              formattedTime = dt.toLocaleString("vi-VN", {
                day: "2-digit",
                month: "2-digit",
                year: "numeric",
                hour: "2-digit",
                minute: "2-digit",
              });
            }
          }
        } catch {
          // Ignore format error
        }

        return {
          id: t.id,
          intent: t.intent,
          status: (t.status === "Resolved" || t.status === "Closed" || t.status === "Reopened" ? t.status : "Resolved") as "Resolved" | "Closed" | "Reopened",
          routedTo: routed,
          customerConfirmed: t.status === "Closed",
          resolvedAt: formattedTime,
          staffName: user?.name || "Kỹ thuật viên VinFast",
          vehicleModel: t.vehicle_model || "VinFast",
          vehicleCode: t.vehicle_code_mock || t.vehicle_model,
          briefSummary: t.issue_summary || getTicketDisplayTitle(t),
          hasLocationConsent: Boolean(t.has_location_consent),
          locationName: t.has_location_consent ? "Tọa độ GPS đã xác thực" : undefined,
          staffUpdateNotes: t.suggested_action || "Đã kiểm tra kỹ thuật và hoàn tất xử lý theo quy chuẩn VinFast.",
        } as HistoricalCase;
      });

    const dbIds = new Set(fromDb.map((c) => c.id));
    const samples = SAMPLE_CASE_HISTORY.filter((s) => !dbIds.has(s.id));
    return [...fromDb, ...samples];
  }, [ticketsWithLocalStatus, user?.name]);

  // Filtered History list
  const filteredHistory = realCaseHistory.filter((item) => {
    if (historyStatusFilter !== "ALL" && item.status !== historyStatusFilter) return false;
    if (historyIntentFilter !== "ALL" && item.intent !== historyIntentFilter) return false;
    return true;
  });

  const handleSendPreviewMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!previewChatInput.trim() || isPreviewSending) return;
    const userMsg = previewChatInput.trim();
    setPreviewMessages((prev) => [...prev, { sender: "user", text: userMsg }]);
    setPreviewChatInput("");
    setIsPreviewSending(true);

    try {
      const res = await sendChatMessage({
        sessionId: previewSessionId.current,
        message: userMsg,
      });
      if (res && res.data) {
        setPreviewMessages((prev) => [
          ...prev,
          {
            sender: "bot",
            text: res.data.message || res.data.response || "",
            intent: res.data.intent || res.data.response_type || undefined,
            priority: res.data.priority,
            citations: res.data.citations || [],
          },
        ]);
      } else {
        setPreviewMessages((prev) => [
          ...prev,
          {
            sender: "bot",
            text: "Dạ hệ thống AI phản hồi chậm, vui lòng thử lại.",
          },
        ]);
      }
    } catch (err: any) {
      setPreviewMessages((prev) => [
        ...prev,
        {
          sender: "bot",
          text: `[Lỗi kết nối AI]: ${err?.message || "Không thể gọi Chat API"}. Vui lòng đảm bảo backend đang chạy tại port 8000.`,
        },
      ]);
    } finally {
      setIsPreviewSending(false);
    }
  };

  const NAV_ITEMS = [
    { id: "queue", label: "Hàng đợi xử lý", icon: Inbox, count: activeQueueTickets.length },
    { id: "overview", label: "Tổng quan ca trực", icon: LayoutDashboard },
    { id: "history", label: "Lịch sử hồ sơ", icon: History, count: realCaseHistory.length },
    { id: "routing", label: "Bộ phận / Routing", icon: GitBranch, count: liveRoutingDepartments.reduce((acc, d) => acc + d.activeTickets, 0) },
    { id: "knowledge", label: "Knowledge Hub", icon: BookOpen, count: knowledgeArticles.length || 7 },
    { id: "preview", label: "Customer Preview", icon: Eye },
    { id: "profile", label: "Hồ sơ Staff", icon: User },
  ];

  const currentTabItem = NAV_ITEMS.find((t) => t.id === activeTab) || NAV_ITEMS[0];

  return (
    <div className="min-h-screen bg-[#F8FAFC] flex antialiased text-slate-900">
      {/* ─────────────────────────────────────────────────────────────
          1. SIDEBAR CỘT TRÁI (Nền xanh than tối VinFast #0F172A, Thu gọn thông minh)
      ───────────────────────────────────────────────────────────── */}
      <aside
        className={`sticky top-0 h-screen shrink-0 bg-[#0F172A] text-slate-200 z-40 transition-all duration-300 ease-in-out flex flex-col justify-between ${isSidebarCollapsed ? "w-16" : "w-64"
          }`}
      >
        {/* Top Brand & Collapse Toggle */}
        <div className="h-14 flex items-center justify-between px-3.5 border-b border-slate-800 shrink-0">
          <div className="flex items-center gap-2.5 overflow-hidden">
            <div className="w-8 h-8 rounded-xl bg-[#1E40AF] flex items-center justify-center text-white shrink-0 shadow-sm">
              <ProductMark className="w-4 h-4 text-white" />
            </div>
            {!isSidebarCollapsed && (
              <div className="min-w-0 flex-1 truncate transition-opacity duration-200">
                <div className="font-bold text-[15px] tracking-tight text-white flex items-center gap-1 font-display">
                  VF <span className="text-[#60A5FA]">Serv</span>
                </div>
                <div className="text-[10px] text-slate-400 font-mono uppercase tracking-wider">
                  Staff Console
                </div>
              </div>
            )}
          </div>

          <button
            type="button"
            onClick={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition shrink-0"
            title={isSidebarCollapsed ? "Mở rộng sidebar (w-64)" : "Thu gọn sidebar (w-16)"}
          >
            {isSidebarCollapsed ? (
              <PanelLeftOpen className="w-4 h-4" />
            ) : (
              <PanelLeftClose className="w-4 h-4" />
            )}
          </button>
        </div>

        {/* Navigation list */}
        <nav className="flex-1 py-3 px-2 space-y-1 overflow-y-auto scrollbar-none">
          {NAV_ITEMS.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id as ConsoleTab)}
                title={isSidebarCollapsed ? tab.label : undefined}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-[13px] font-medium transition-all ${isActive
                  ? "bg-[#1E40AF] text-white font-semibold shadow-xs"
                  : "text-slate-300 hover:bg-slate-800/80 hover:text-white"
                  }`}
              >
                <Icon className="w-4 h-4 shrink-0" />
                {!isSidebarCollapsed && (
                  <span className="truncate flex-1 text-left">{tab.label}</span>
                )}
                {!isSidebarCollapsed && tab.count !== undefined && (
                  <span
                    className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${isActive ? "bg-white/20 text-white" : "bg-slate-800 text-slate-300"
                      }`}
                  >
                    {tab.count}
                  </span>
                )}
                {isSidebarCollapsed && tab.count !== undefined && (
                  <span className="w-1.5 h-1.5 rounded-full bg-[#60A5FA] ml-auto" />
                )}
              </button>
            );
          })}
        </nav>

        {/* Footer Profile */}
        <div className="p-3 border-t border-slate-800 bg-[#0B1120] shrink-0">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2.5 overflow-hidden">
              <div className="w-8 h-8 rounded-full bg-[#1E40AF] text-white flex items-center justify-center text-xs font-bold shrink-0">
                {user?.name?.charAt(0) || "Q"}
              </div>
              {!isSidebarCollapsed && (
                <div className="min-w-0 flex-1 truncate">
                  <div className="text-[12px] font-semibold text-white truncate">
                    {user?.name || "Lê Hoàng Quân"}
                  </div>
                  <div className="text-[10px] text-slate-400 font-mono truncate">
                    Cố vấn KTV Bậc 4
                  </div>
                </div>
              )}
            </div>

            {!isSidebarCollapsed && (
              <button
                type="button"
                onClick={logout}
                className="p-1.5 text-slate-400 hover:text-[#EF4444] hover:bg-slate-800 rounded-lg transition"
                title="Đăng xuất tài khoản Staff"
              >
                <LogOut className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
      </aside>

      {/* ─────────────────────────────────────────────────────────────
          2. MAIN CONTENT CANVAS (Topbar h-12 mỏng nhẹ, nền xám dịu mắt, Card nổi)
      ───────────────────────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col min-w-0 h-screen overflow-y-auto">
        {/* Sticky Featherlight Topbar h-12 with Backdrop Blur */}
        <header className="sticky top-0 z-30 h-12 px-6 flex items-center justify-between bg-[#F8FAFC]/85 backdrop-blur-md border-b border-slate-200/60 shrink-0">
          <div className="flex items-center gap-2 text-[12px] text-slate-500">
            <span className="text-slate-400 font-medium">Bàn Điều Phối</span>
            <span>/</span>
            <span className="font-semibold text-slate-900">{currentTabItem.label}</span>
          </div>

          <div className="flex items-center gap-3.5 text-[12px]">
            <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-white shadow-2xs border border-slate-200/50 text-slate-600">
              <span className={`w-2 h-2 rounded-full ${isLiveApi ? "bg-emerald-500 animate-pulse" : "bg-slate-400"}`} />
              <span className="text-[11px] font-medium">{isLiveApi ? "Hệ thống trực tuyến" : "Chế độ mẫu"}</span>
            </div>
            <span className="hidden md:inline text-[11px] text-slate-500">
              Cơ sở: <strong className="text-slate-800 font-medium">VinFast Times City</strong>
            </span>
            <button
              type="button"
              onClick={() => setActiveTab("preview")}
              className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-white hover:bg-slate-100 text-slate-700 text-[11px] font-medium shadow-2xs transition"
            >
              <Eye className="w-3.5 h-3.5 text-[#1E40AF]" />
              <span>Customer Preview</span>
            </button>
          </div>
        </header>

        {/* Main Work Area Container */}
        <main className="flex-1 p-5 max-w-7xl w-full mx-auto">
          {/* =========================================================
              TAB 1: HÀNG ĐỢI XỬ LÝ (QUEUE) - INLINE SINGLE-ROW TOOLBAR
          ========================================================= */}
          {activeTab === "queue" && (
            <div className="space-y-4">
              {/* Single-Row Inline Toolbar (KHÔNG đóng hộp viền xám to tướng) */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
                {/* Search input nhỏ gọn */}
                <div className="relative w-full sm:w-72">
                  <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Tìm mã case, xe, lỗi..."
                    className="w-full text-[12px] pl-8 pr-7 py-1.5 rounded-xl bg-white shadow-2xs text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-[#1E40AF]/20"
                  />
                  {searchQuery && (
                    <button
                      type="button"
                      onClick={() => setSearchQuery("")}
                      className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-700"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>

                {/* Quick Filter Pills & Refresh Button */}
                <div className="flex items-center gap-2 flex-wrap">
                  <div className="flex items-center gap-1 bg-slate-200/50 p-1 rounded-xl text-[11px] font-medium">
                    {[
                      { id: "ALL", label: "Tất cả" },
                      { id: "CRITICAL", label: "🔥 Khẩn cấp" },
                      { id: "Staff Reviewing", label: "Chờ duyệt" },
                      { id: "Needs Information", label: "Cần tin" },
                      { id: "In Progress", label: "Đang xử lý" },
                    ].map((pill) => (
                      <button
                        key={pill.id}
                        type="button"
                        onClick={() => setQueueQuickFilter(pill.id)}
                        className={`px-2.5 py-1 rounded-lg transition ${queueQuickFilter === pill.id
                          ? "bg-white text-slate-900 font-semibold shadow-xs"
                          : "text-slate-600 hover:text-slate-900"
                          }`}
                      >
                        {pill.label}
                      </button>
                    ))}
                  </div>

                  <button
                    type="button"
                    onClick={() => refreshTickets()}
                    disabled={loading}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white hover:bg-slate-50 text-slate-700 text-[12px] font-medium shadow-2xs transition"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 text-slate-500 ${loading ? "animate-spin text-[#1E40AF]" : ""}`} />
                    <span className="hidden sm:inline">Làm mới</span>
                  </button>
                </div>
              </div>

              {/* Action notification toast */}
              {routingConfirmedNotice && (
                <div className="p-3 bg-[#ECFDF5] rounded-xl text-[#065F46] text-[13px] font-medium flex items-center gap-2 shadow-2xs animate-in fade-in">
                  <Check className="w-4 h-4 text-[#10B981]" />
                  <span>{routingConfirmedNotice}</span>
                </div>
              )}

              {/* Master-Detail Split Layout */}
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
                {/* CỘT TRÁI (5 Cols / 40%): Danh sách Card trắng nổi, KHÔNG bọc viền xám thừa */}
                <div className="lg:col-span-5 flex flex-col space-y-2.5">
                  <div className="flex items-center justify-between text-[11px] px-1 text-slate-500 font-medium">
                    <span>
                      Hồ sơ đang mở: <strong className="text-slate-900">{activeQueueTickets.length}</strong>
                    </span>
                    <span className="text-slate-400">Dùng phím ↑ ↓ (hoặc J/K) để duyệt</span>
                  </div>

                  <div className="bg-white rounded-2xl shadow-[0_1px_3px_rgba(0,0,0,0.05)] overflow-hidden divide-y divide-slate-100 h-[calc(100vh-140px)] overflow-y-auto scrollbar-thin">
                    {activeQueueTickets.length === 0 ? (
                      <div className="p-8 text-center text-slate-500">
                        <Inbox className="w-8 h-8 mx-auto text-slate-300 mb-2" />
                        <p className="text-[13px] font-semibold text-slate-900">Hàng đợi hiện đang trống</p>
                        <p className="text-[12px] mt-1">Không có hồ sơ nào khớp với bộ lọc hiện tại.</p>
                      </div>
                    ) : (
                      groupedQueueTickets.map((group) => (
                        <div key={group.dateLabel} className="divide-y divide-slate-100">
                          {/* Dòng tiêu đề nhỏ phân nhóm ngày */}
                          <div className="sticky top-0 z-10 bg-slate-50/95 backdrop-blur-xs px-3.5 py-1.5 border-y border-slate-100/90 flex items-center justify-between text-[11px] font-semibold text-slate-600 uppercase tracking-wide">
                            <span>{group.dateLabel}</span>
                            <span className="text-[10px] font-normal text-slate-400 lowercase">{group.tickets.length} hồ sơ</span>
                          </div>

                          {group.tickets.map((ticket) => {
                            const isSelected = (currentActiveTicket?.id || "") === ticket.id;
                            const isCritical = ticket.priority === "CRITICAL";
                            const isHigh = ticket.priority === "HIGH";

                            const shortId = getShortTicketId(ticket.id);
                            const title = getTicketDisplayTitle(ticket);
                            const formattedTime = new Date(ticket.created_at).toLocaleTimeString("vi-VN", {
                              hour: "2-digit",
                              minute: "2-digit",
                            });

                            return (
                              <div
                                id={`ticket-item-${ticket.id}`}
                                key={ticket.id}
                                onClick={() => handleSelectTicket(ticket.id)}
                                className={`group cursor-pointer p-3.5 transition-all border-l-[3.5px] ${isSelected
                                  ? "bg-[#EFF3FC] border-l-[#1E40AF] shadow-2xs"
                                  : isCritical
                                    ? "bg-white border-l-red-500 hover:bg-slate-50/80"
                                    : isHigh
                                      ? "bg-white border-l-amber-500 hover:bg-slate-50/80"
                                      : ticket.priority === "MEDIUM"
                                        ? "bg-white border-l-blue-400 hover:bg-slate-50/80"
                                        : "bg-white border-l-transparent hover:border-l-slate-200 hover:bg-slate-50/80"
                                  }`}
                              >
                                {/* Dòng 1: Tiêu đề sự cố thật từ AI brief + nhãn mức độ/trạng thái duy nhất */}
                                <div className="flex items-center justify-between gap-2">
                                  <h3
                                    className={`text-[13.5px] truncate leading-tight flex-1 ${isSelected
                                      ? "font-bold text-[#1E40AF]"
                                      : "font-semibold text-slate-900 group-hover:text-[#1E40AF]"
                                      }`}
                                  >
                                    {title}
                                  </h3>

                                  {/* Gom thành một dấu hiệu duy nhất mỗi dòng ở góc phải */}
                                  <div className="shrink-0 flex items-center gap-1 font-sans">
                                    {isCritical ? (
                                      <span className="px-1.5 py-0.5 rounded text-[10.5px] font-bold text-red-600 bg-red-50 tracking-wide">
                                        Khẩn cấp
                                      </span>
                                    ) : isHigh ? (
                                      <span className="px-1.5 py-0.5 rounded text-[10.5px] font-semibold text-amber-700 bg-amber-50">
                                        Ưu tiên
                                      </span>
                                    ) : (
                                      <span className="text-[11px] text-slate-500 font-medium">
                                        {VIETNAMESE_STATUS_MAP[ticket.status] || ticket.status}
                                      </span>
                                    )}
                                  </div>
                                </div>

                                {/* Dòng 2: Mã case rút gọn, dòng xe, giờ: 001 · VF8 · 07:29 */}
                                <div className="mt-1.5 text-[12px] text-slate-500 flex items-center justify-between font-mono">
                                  <div className="flex items-center gap-1.5">
                                    <span className={`font-semibold ${isSelected ? "text-[#1E40AF]" : "text-slate-700"}`}>
                                      {shortId}
                                    </span>
                                    <span>·</span>
                                    <span className="font-sans font-medium text-slate-600">{ticket.vehicle_model}</span>
                                    <span>·</span>
                                    <span className="text-slate-400">{formattedTime}</span>
                                  </div>

                                  {/* Thông tin phụ hiển thị nhẹ nhàng: Mã lỗi hoặc GPS */}
                                  <div className="flex items-center gap-1 font-sans">
                                    {ticket.error_code_short && (
                                      <span className="px-1.5 py-0.2 rounded bg-slate-100 text-slate-700 font-mono text-[10px]">
                                        {ticket.error_code_short}
                                      </span>
                                    )}
                                    {ticket.has_location_consent && (
                                      <span className="px-1 py-0.2 rounded bg-blue-50 text-[#1E40AF] text-[10px] font-medium">
                                        GPS
                                      </span>
                                    )}
                                  </div>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      ))
                    )}
                  </div>
                </div>

                {/* CỘT PHẢI (7 Cols / 60%): TicketDetailPanel Chi Tiết & Triage */}
                <div className="lg:col-span-7">
                  {currentActiveTicket ? (
                    <TicketDetailPanel
                      ticket={currentActiveTicket}
                      onActionComplete={(msg) => {
                        setRoutingConfirmedNotice(msg);
                        setTimeout(() => setRoutingConfirmedNotice(null), 3500);
                      }}
                      onStatusUpdate={(id, newStatus) => {
                        handleStatusUpdate(id, newStatus);
                      }}
                    />
                  ) : (
                    <div className="bg-white rounded-2xl p-12 text-center text-slate-500 h-[calc(100vh-140px)] flex flex-col items-center justify-center shadow-[0_1px_3px_rgba(0,0,0,0.05)]">
                      <Inbox className="w-10 h-10 text-slate-300 mb-2" />
                      <p className="text-[14px] font-semibold text-slate-900">Chưa chọn hồ sơ nào</p>
                      <p className="text-[12px] mt-1 text-slate-500">
                        Chọn một hồ sơ từ danh sách bên trái để xem Case Brief và điều phối.
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* =========================================================
              TAB 2: TỔNG QUAN (OVERVIEW DASHBOARD)
          ========================================================= */}
          {activeTab === "overview" && (
            <div className="space-y-6">
              <div>
                <h1 className="text-xl font-semibold text-slate-900">Tổng Quan Ca Trực (Dashboard Summary)</h1>
                <p className="text-xs text-slate-500 mt-0.5">Số liệu thống kê hồ sơ sự cố tiếp nhận trong ngày hôm nay.</p>
              </div>

              {/* KPI 4 Cards */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="bg-white rounded-2xl p-4 shadow-[0_1px_3px_rgba(0,0,0,0.05)]">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">Tổng ca trực</span>
                  <div className="text-2xl font-bold text-slate-900 mt-2">{stats.total}</div>
                  <div className="text-[11px] text-slate-400 mt-1">Đã đồng bộ thời gian thực</div>
                </div>

                <div className="bg-white rounded-2xl p-4 shadow-[0_1px_3px_rgba(0,0,0,0.05)] bg-[#FEF2F2]/40">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-[#DC2626] flex items-center gap-1">
                    <Flame className="w-3.5 h-3.5 text-[#DC2626]" /> Ca khẩn cấp (Critical)
                  </span>
                  <div className="text-2xl font-bold text-[#DC2626] mt-2">{stats.critical}</div>
                  <div className="text-[11px] text-[#DC2626] mt-1">Ưu tiên cứu hộ cao tốc</div>
                </div>

                <div className="bg-white rounded-2xl p-4 shadow-[0_1px_3px_rgba(0,0,0,0.05)] bg-[#FFFBEB]/40">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-[#D97706]">Chờ duyệt (Reviewing)</span>
                  <div className="text-2xl font-bold text-[#D97706] mt-2">{stats.reviewing}</div>
                  <div className="text-[11px] text-[#D97706] mt-1">Cần chuyên viên xác nhận</div>
                </div>

                <div className="bg-white rounded-2xl p-4 shadow-[0_1px_3px_rgba(0,0,0,0.05)] bg-[#ECFDF5]/40">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-[#059669]">Đã giải quyết (Resolved)</span>
                  <div className="text-2xl font-bold text-[#059669] mt-2">{stats.resolved}</div>
                  <div className="text-[11px] text-[#059669] mt-1">Hoàn thành ca hôm nay</div>
                </div>
              </div>

              {/* Phân bố Intent & Cảnh báo */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                <div className="bg-white rounded-2xl p-5 shadow-[0_1px_3px_rgba(0,0,0,0.05)] space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-[14px] font-semibold text-slate-900">Phân bố theo Nhóm Sự Cố (Intent)</h3>
                    <span className="text-[11px] font-mono text-slate-400">Thời gian thực</span>
                  </div>
                  <div className="space-y-3 text-[13px]">
                    {intentDistribution.map((item) => (
                      <div key={item.key}>
                        <div className="flex justify-between font-medium">
                          <span>{item.label}</span>
                          <span className="font-mono text-slate-700">{item.count} hồ sơ ({item.percent}%)</span>
                        </div>
                        <div className="w-full h-2 rounded-full bg-slate-100 mt-1 overflow-hidden">
                          <div
                            className={`h-full ${item.color} rounded-full transition-all duration-500`}
                            style={{ width: `${item.percent}%` }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="bg-white rounded-2xl p-5 shadow-[0_1px_3px_rgba(0,0,0,0.05)] space-y-3">
                  <h3 className="text-[14px] font-semibold text-slate-900">Nguyên tắc Bàn Giao Ca Trực</h3>
                  <ul className="text-[13px] text-slate-600 space-y-2 list-disc pl-4 leading-relaxed">
                    <li>Không để tồn đọng ca <strong>CRITICAL</strong> qua ca trực mà không có kỹ thuật viên tiếp nhận.</li>
                    <li>Mọi ca <strong>Resolved</strong> phải kèm thông báo Customer Update rõ ràng cho chủ xe.</li>
                    <li>Nếu khách bấm <strong>Vẫn chưa giải quyết</strong>, ticket tự động quay lại Queue với cờ <code>Reopened</code>.</li>
                    <li>Hồ sơ sau 24h khách không phản hồi sẽ tự động chuyển sang <code>Closed</code>.</li>
                  </ul>
                </div>
              </div>
            </div>
          )}

          {/* =========================================================
              TAB 3: LỊCH SỬ CASE (CASE HISTORY - BÀN GIAO & AUDIT)
          ========================================================= */}
          {activeTab === "history" && (
            <div className="space-y-4">
              <div>
                <h1 className="text-xl font-semibold text-slate-900">Lịch Sử Hồ Sơ Sự Cố (Case History & Audit)</h1>
                <p className="text-xs text-slate-500 mt-0.5">
                  Tra cứu các hồ sơ đã giải quyết, đóng hoặc mở lại; phục vụ bàn giao ca trực và kiểm tra chất lượng AI.
                </p>
              </div>

              {/* Filter Bar with Styled Pills */}
              <div className="flex flex-wrap items-center justify-between gap-3 bg-white rounded-2xl p-4 shadow-[0_1px_3px_rgba(0,0,0,0.05)]">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-[12px] font-semibold text-slate-500">Trạng thái:</span>
                  <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl text-[11px] font-medium">
                    {["ALL", "Resolved", "Closed", "Reopened"].map((st) => (
                      <button
                        key={st}
                        type="button"
                        onClick={() => setHistoryStatusFilter(st)}
                        className={`px-2.5 py-1 rounded-lg transition ${historyStatusFilter === st
                          ? "bg-white text-slate-900 font-semibold shadow-xs"
                          : "text-slate-600 hover:text-slate-900"
                          }`}
                      >
                        {st === "ALL" ? "Tất cả" : st}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-[12px] font-semibold text-slate-500">Ý định:</span>
                  <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl text-[11px] font-medium">
                    {[
                      { id: "ALL", label: "Tất cả" },
                      { id: "Charging/Battery", label: "Sạc & Pin" },
                      { id: "Service/Incident", label: "Kỹ thuật" },
                      { id: "Complaint/Feedback", label: "Khiếu nại" },
                      { id: "Sales/General Info", label: "Bán hàng" },
                    ].map((it) => (
                      <button
                        key={it.id}
                        type="button"
                        onClick={() => setHistoryIntentFilter(it.id)}
                        className={`px-2.5 py-1 rounded-lg transition ${historyIntentFilter === it.id
                          ? "bg-white text-slate-900 font-semibold shadow-xs"
                          : "text-slate-600 hover:text-slate-900"
                          }`}
                      >
                        {it.label}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              {/* History Table */}
              <div className="bg-white rounded-2xl overflow-hidden shadow-[0_1px_3px_rgba(0,0,0,0.05)]">
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-[13px]">
                    <thead className="bg-slate-50 border-b border-slate-100 text-[11px] font-bold uppercase tracking-wider text-slate-500">
                      <tr>
                        <th className="py-3 px-4">Mã Case</th>
                        <th className="py-3 px-4">Phân loại & Xe</th>
                        <th className="py-3 px-4">Trạng thái</th>
                        <th className="py-3 px-4">Đã Route</th>
                        <th className="py-3 px-4">Khách xác nhận</th>
                        <th className="py-3 px-4">Thời điểm</th>
                        <th className="py-3 px-4 text-right">Thao tác</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {filteredHistory.map((item) => (
                        <tr key={item.id} className="hover:bg-slate-50/70 transition">
                          <td className="py-3.5 px-4 font-mono font-bold text-slate-900">{item.id}</td>
                          <td className="py-3.5 px-4">
                            <div className="font-semibold text-slate-900">{item.intent}</div>
                            <div className="text-[11px] text-slate-500">{item.vehicleModel}</div>
                          </td>
                          <td className="py-3.5 px-4">
                            <span
                              className={`px-2.5 py-0.5 rounded-full text-[11px] font-bold uppercase ${item.status === "Closed"
                                ? "bg-[#ECFDF5] text-[#059669]"
                                : item.status === "Reopened"
                                  ? "bg-[#FEF2F2] text-[#DC2626]"
                                  : "bg-[#EFF3FC] text-[#1E40AF]"
                                }`}
                            >
                              {item.status}
                            </span>
                          </td>
                          <td className="py-3.5 px-4 text-[12px] font-medium text-slate-700">{item.routedTo}</td>
                          <td className="py-3.5 px-4 text-[12px]">
                            {item.customerConfirmed ? (
                              <span className="text-[#059669] font-medium flex items-center gap-1">
                                <CheckCircle2 className="w-3.5 h-3.5" /> Đã xác nhận
                              </span>
                            ) : item.status === "Reopened" ? (
                              <span className="text-[#DC2626] font-medium">Báo chưa giải quyết</span>
                            ) : (
                              <span className="text-slate-400">Chưa xác nhận</span>
                            )}
                          </td>
                          <td className="py-3.5 px-4 text-[12px] text-slate-500 font-mono">{item.resolvedAt}</td>
                          <td className="py-3.5 px-4 text-right">
                            <button
                              type="button"
                              onClick={() => setReviewingHistoryCase(item)}
                              className="inline-flex items-center gap-1 px-3 py-1.5 rounded-xl bg-slate-50 hover:bg-slate-100 text-[#1E40AF] text-[12px] font-semibold transition"
                            >
                              Xem lại hồ sơ
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Modal Xem lại Hồ sơ (Audit Trail Detail) */}
              {reviewingHistoryCase && (
                <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4">
                  <div className="bg-white rounded-3xl max-w-2xl w-full p-6 shadow-2xl space-y-4 max-h-[90vh] overflow-y-auto animate-in zoom-in-95">
                    <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                      <div>
                        <div className="font-mono text-lg font-bold text-slate-900">{reviewingHistoryCase.id}</div>
                        <div className="text-[12px] text-slate-500">Hồ sơ lưu trữ kiểm định chất lượng AI & Bàn giao</div>
                      </div>
                      <button
                        type="button"
                        onClick={() => setReviewingHistoryCase(null)}
                        className="p-1.5 text-slate-400 hover:text-slate-900 rounded-lg hover:bg-slate-100"
                      >
                        <X className="w-5 h-5" />
                      </button>
                    </div>

                    <div className="space-y-3 text-[13px]">
                      <div className="p-3.5 rounded-xl bg-slate-50">
                        <div className="text-[11px] font-bold uppercase text-[#1E40AF] mb-1">Case Brief Ban Đầu (AI Trích Xuất)</div>
                        <p className="text-slate-900 font-medium leading-relaxed">{reviewingHistoryCase.briefSummary}</p>
                      </div>

                      {reviewingHistoryCase.hasLocationConsent && (
                        <div className="p-3 rounded-xl bg-[#EFF3FC] text-[12px] flex items-center gap-2">
                          <MapPin className="w-4 h-4 text-[#1E40AF] shrink-0" />
                          <span>Vị trí khách chia sẻ: <strong>{reviewingHistoryCase.locationName}</strong></span>
                        </div>
                      )}

                      <div className="p-3.5 rounded-xl bg-slate-50">
                        <div className="text-[11px] font-bold uppercase text-slate-500 mb-1">Ghi Chú Kỹ Thuật (Staff Update)</div>
                        <p className="text-slate-700 leading-relaxed">{reviewingHistoryCase.staffUpdateNotes}</p>
                      </div>

                      {reviewingHistoryCase.customerFeedbackScore && (
                        <div className="p-3.5 rounded-xl bg-[#ECFDF5]">
                          <div className="flex items-center gap-1 text-[#D97706] mb-1">
                            {[...Array(reviewingHistoryCase.customerFeedbackScore)].map((_, i) => (
                              <Star key={i} className="w-4 h-4 fill-current" />
                            ))}
                            <span className="text-[12px] font-bold text-[#065F46] ml-2">Đánh giá của khách hàng</span>
                          </div>
                          <p className="text-[12px] text-[#065F46] italic">"{reviewingHistoryCase.customerFeedbackComment}"</p>
                        </div>
                      )}

                      {reviewingHistoryCase.reopenReason && (
                        <div className="p-3.5 rounded-xl bg-[#FEF2F2]">
                          <div className="text-[11px] font-bold uppercase text-[#DC2626] mb-1">Lý do khách mở lại (Reopened)</div>
                          <p className="text-[12px] text-[#DC2626] font-medium">{reviewingHistoryCase.reopenReason}</p>
                        </div>
                      )}
                    </div>

                    <div className="pt-3 border-t border-slate-100 flex items-center justify-between">
                      <button
                        type="button"
                        onClick={() => {
                          handleSelectTicket(reviewingHistoryCase.id);
                          setActiveTab("queue");
                          setReviewingHistoryCase(null);
                        }}
                        className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-slate-100 hover:bg-slate-200 text-slate-800 text-[12px] font-semibold rounded-xl transition"
                      >
                        <Inbox className="w-3.5 h-3.5 text-[#1E40AF]" />
                        <span>Mở chi tiết trong Hàng đợi</span>
                      </button>
                      <button
                        type="button"
                        onClick={() => setReviewingHistoryCase(null)}
                        className="px-4 py-2 bg-[#1E40AF] hover:bg-[#1D4ED8] text-white text-[12px] font-semibold rounded-xl transition"
                      >
                        Đóng cửa sổ
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* =========================================================
              TAB 4: BỘ PHẬN / ROUTING (5 NHÓM P0 CẤU HÌNH)
          ========================================================= */}
          {activeTab === "routing" && (
            <div className="space-y-6">
              <div>
                <h1 className="text-xl font-semibold text-slate-900">Danh Mục Bộ Phận Tiếp Nhận (Routing Directory P0)</h1>
                <p className="text-xs text-slate-500 mt-0.5">
                  Cấu hình phân luồng điều phối tự động và thủ công. Không can thiệp sang CRM bên ngoài ở bản MVP.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {liveRoutingDepartments.map((dept) => (
                  <div key={dept.id} className="bg-white rounded-2xl p-5 shadow-[0_1px_3px_rgba(0,0,0,0.05)] flex flex-col justify-between space-y-4">
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-bold uppercase ${dept.color}`}>
                          {dept.badge}
                        </span>
                        <span className="text-[11px] font-mono text-slate-500">
                          {dept.activeTickets} ca active
                        </span>
                      </div>

                      <h3 className="text-[15px] font-semibold text-slate-900">{dept.name}</h3>
                      <p className="text-[12px] text-slate-600 leading-relaxed">{dept.description}</p>
                    </div>

                    <div className="pt-3 border-t border-slate-100 text-[11px] text-slate-600 space-y-1">
                      <div><strong>Intent tiếp nhận:</strong> <code className="text-[#1E40AF]">{dept.intent}</code></div>
                      <div><strong>Phụ trách chính:</strong> {dept.lead}</div>
                      <button
                        type="button"
                        onClick={() => {
                          if (dept.id === "emergency_demo") {
                            setQueueQuickFilter("CRITICAL");
                          } else {
                            setSearchQuery(dept.name);
                          }
                          setActiveTab("queue");
                        }}
                        className="w-full mt-2.5 py-1.5 text-center text-[12px] font-semibold text-[#1E40AF] bg-[#EFF3FC] hover:bg-[#DBEAFE] rounded-xl transition"
                      >
                        Xem {dept.activeTickets} ca trong hàng đợi &rarr;
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* =========================================================
              TAB 5: KNOWLEDGE HUB (TÀI LIỆU NỘI BỘ & CITATION)
          ========================================================= */}
          {activeTab === "knowledge" && (
            <div className="space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div>
                  <h1 className="text-xl font-semibold text-slate-900">Knowledge Hub Nội Bộ (RAG Knowledge Sources)</h1>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Cơ sở tri thức nguồn chính thống được kiểm chứng mà AI Agent sử dụng để trích dẫn URL cho khách hàng.
                  </p>
                </div>
                <span className="text-[11px] font-mono px-2.5 py-1 rounded-full bg-slate-100 text-slate-600 self-start">
                  {knowledgeArticles.length > 0 ? `${knowledgeArticles.length} bài viết (Đồng bộ API)` : "7 nguồn xác thực"}
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {(knowledgeArticles.length > 0
                  ? knowledgeArticles.map((item) => ({
                    id: item.id,
                    title: item.title,
                    url: item.source_url || item.url || "#",
                    scope: item.summary || item.category,
                  }))
                  : [
                    { id: "SRC-001", title: "Chính sách Bảo hành Ô tô Điện VinFast", url: "https://vinfastauto.com/vn_vi/chinh-sach-bao-hanh-xe-dien", scope: "VF 8 (10 năm/200.000km, pin mua đứt không giới hạn km)" },
                    { id: "SRC-002", title: "Hướng dẫn sử dụng Ứng dụng VinFast", url: "https://vinfastauto.com/vn_vi/huong-dan-su-dung-ung-dung-vinfast", scope: "Đặt lịch xưởng, theo dõi dung lượng pin" },
                    { id: "SRC-003", title: "Thông tin Cứu hộ Khẩn cấp & Cứu hộ Pin 24/7", url: "https://vinfastauto.com/vn_vi/dich-vu-cuu-ho-24-7", scope: "Hotline 1900-232389, cứu hộ pin lưu động" },
                    { id: "SRC-004", title: "Biểu phí & Chính sách Sạc tại Trạm Công cộng", url: "https://vinfastauto.com/vn_vi/chinh-sach-bieu-phi-sac-xe-dien", scope: "Đơn giá kWh, phí chiếm trụ 1.000đ/phút sau 10 phút" },
                    { id: "SRC-005", title: "Cẩm nang Bảo dưỡng Định kỳ 12.000 km", url: "https://vinfastauto.com/vn_vi/lich-bao-duong-dinh-ky-xe-dien", scope: "6 hạng mục kiểm tra tiêu chuẩn pack pin, phanh, gầm" },
                    { id: "SRC-006", title: "Danh mục Sản phẩm & Chính sách Bán hàng", url: "https://vinfastauto.com/vn_vi/cac-dong-xe-o-to", scope: "Dải xe điện VF 3, VF 5, VF 6, VF 7, VF 8, VF 9" },
                    { id: "SRC-007", title: "Thông số Kỹ thuật Chi tiết Catalog", url: "https://vinfastauto.com/vn_vi/thong-so-ky-thuat-o-to-dien", scope: "VF 7 Plus 349HP AWD vs Eco 201HP FWD, kích thước VF 9" },
                  ]
                ).map((item) => (
                  <div key={item.id} className="bg-white rounded-2xl p-4 shadow-[0_1px_3px_rgba(0,0,0,0.05)] space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-[11px] font-bold bg-[#EFF3FC] text-[#1E40AF] px-2 py-0.5 rounded-md">
                        {item.id}
                      </span>
                      <a
                        href={item.url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-[11px] text-[#1E40AF] font-medium inline-flex items-center gap-1 hover:underline"
                      >
                        Nguồn chính thức <ExternalLink className="w-3 h-3" />
                      </a>
                    </div>
                    <h4 className="text-[14px] font-semibold text-slate-900">{item.title}</h4>
                    <p className="text-[12px] text-slate-500"><strong>Phạm vi trích dẫn:</strong> {item.scope}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* =========================================================
              TAB 6: CUSTOMER PREVIEW (XEM TRƯỚC GIAO DIỆN KHÁCH)
          ========================================================= */}
          {activeTab === "preview" && (
            <div className="space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                  <h1 className="text-xl font-semibold text-slate-900">Kiểm Thử Trực Tiếp Trợ Lý AI (Customer Live Preview)</h1>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Tương tác trực tiếp với Backend AI Agent (/api/v1/customer/chat) để kiểm tra luồng RAG, bóc tách Intent và mức ưu tiên trong môi trường an toàn.
                  </p>
                </div>

                <Link
                  href="/chat"
                  target="_blank"
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-[#1E40AF] text-white text-[12px] font-semibold hover:bg-[#1D4ED8] transition shadow-xs self-start"
                >
                  <span>Mở tab chat thật (/chat)</span>
                  <ExternalLink className="w-3.5 h-3.5" />
                </Link>
              </div>

              {/* Khung Live Chat Preview */}
              <div className="max-w-2xl mx-auto bg-white rounded-3xl shadow-sm overflow-hidden flex flex-col h-[560px] border border-slate-100">
                {/* Preview header */}
                <div className="bg-[#1E40AF] text-white p-4 flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <div className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center font-bold">
                      <Bot className="w-4 h-4 text-white" />
                    </div>
                    <div>
                      <div className="text-[13px] font-bold">Trợ Lý Dịch Vụ VinFast (Live AI Turn)</div>
                      <div className="text-[10px] text-white/80">Kết nối trực tiếp backend LangGraph</div>
                    </div>
                  </div>
                  <span className="px-2 py-0.5 rounded-full bg-white/20 text-[10px] font-mono">LIVE_AGENT_SESSION</span>
                </div>

                {/* Message Feed */}
                <div className="flex-1 p-4 overflow-y-auto space-y-3 bg-slate-50">
                  {previewMessages.map((msg, idx) => (
                    <div
                      key={idx}
                      className={`flex ${msg.sender === "user" ? "justify-end" : "justify-start"}`}
                    >
                      <div
                        className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-[13px] leading-relaxed ${msg.sender === "user"
                          ? "bg-[#1E40AF] text-white"
                          : "bg-white text-slate-900 shadow-2xs border border-slate-100"
                          }`}
                      >
                        <div className="whitespace-pre-line">{msg.text}</div>

                        {/* Intent & Priority Chips */}
                        {msg.sender === "bot" && (msg.intent || msg.priority) && (
                          <div className="mt-2 pt-2 border-t border-slate-100 flex flex-wrap items-center gap-1.5 text-[10px]">
                            {msg.intent && (
                              <span className="px-2 py-0.5 rounded-md bg-[#EFF3FC] text-[#1E40AF] font-bold">
                                Intent: {msg.intent}
                              </span>
                            )}
                            {msg.priority && (
                              <span
                                className={`px-2 py-0.5 rounded-md font-bold ${msg.priority === "CRITICAL"
                                  ? "bg-red-100 text-red-700"
                                  : msg.priority === "HIGH"
                                    ? "bg-amber-100 text-amber-800"
                                    : "bg-slate-100 text-slate-700"
                                  }`}
                              >
                                {msg.priority}
                              </span>
                            )}
                          </div>
                        )}

                        {/* RAG Citations */}
                        {msg.sender === "bot" && msg.citations && msg.citations.length > 0 && (
                          <div className="mt-2 pt-2 border-t border-slate-100 text-[11px] text-slate-600 space-y-1">
                            <div className="font-semibold text-slate-700 flex items-center gap-1">
                              <Sparkles className="w-3 h-3 text-[#1E40AF]" /> Trích dẫn RAG xác thực:
                            </div>
                            {msg.citations.map((c, i) => (
                              <a
                                key={i}
                                href={c.url || "#"}
                                target="_blank"
                                rel="noreferrer"
                                className="text-[#1E40AF] hover:underline flex items-center gap-1 truncate font-medium"
                              >
                                &bull; {c.title || c.url || c.source_id}
                                <ExternalLink className="w-2.5 h-2.5 shrink-0" />
                              </a>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}

                  {isPreviewSending && (
                    <div className="flex justify-start">
                      <div className="bg-white rounded-2xl px-4 py-2.5 text-[13px] text-slate-500 shadow-2xs border border-slate-100 flex items-center gap-2">
                        <Loader2 className="w-4 h-4 animate-spin text-[#1E40AF]" />
                        <span>AI Agent đang bóc tách intent & tra cứu RAG...</span>
                      </div>
                    </div>
                  )}
                </div>

                {/* Input Bar */}
                <form onSubmit={handleSendPreviewMessage} className="p-3 bg-white border-t border-slate-100 flex gap-2">
                  <input
                    type="text"
                    value={previewChatInput}
                    disabled={isPreviewSending}
                    onChange={(e) => setPreviewChatInput(e.target.value)}
                    placeholder="Gõ thử câu hỏi như một khách hàng (ví dụ: 'Xe VF8 báo rùa vàng', 'Phí sạc quá giờ tính sao?')..."
                    className="flex-1 text-[13px] px-3.5 py-2 rounded-xl bg-slate-50 focus:bg-white text-slate-900 focus:outline-none focus:ring-2 focus:ring-[#1E40AF]/20 disabled:opacity-60"
                  />
                  <button
                    type="submit"
                    disabled={isPreviewSending || !previewChatInput.trim()}
                    className="px-4 py-2 bg-[#1E40AF] hover:bg-[#1D4ED8] disabled:bg-slate-300 text-white text-[12px] font-semibold rounded-xl transition flex items-center gap-1.5"
                  >
                    {isPreviewSending ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <Send className="w-3.5 h-3.5" />
                    )}
                    <span>Gửi</span>
                  </button>
                </form>
              </div>
            </div>
          )}

          {/* =========================================================
              TAB 7: HỒ SƠ STAFF (STAFF PROFILE & CA TRỰC)
          ========================================================= */}
          {activeTab === "profile" && (
            <div className="max-w-xl mx-auto space-y-6">
              <div>
                <h1 className="text-xl font-semibold text-slate-900">Hồ Sơ Kỹ Thuật Viên (Staff Profile)</h1>
                <p className="text-xs text-slate-500 mt-0.5">Thông tin tài khoản xác thực và phân quyền xử lý ca trực HITL.</p>
              </div>

              <div className="bg-white rounded-3xl p-6 shadow-[0_1px_3px_rgba(0,0,0,0.05)] space-y-5">
                <div className="flex items-center gap-4">
                  <div className="w-14 h-14 rounded-2xl bg-[#1E40AF] text-white flex items-center justify-center text-xl font-bold shadow-xs">
                    {user?.name?.charAt(0) || "Q"}
                  </div>
                  <div>
                    <h2 className="text-base font-bold text-slate-900">{user?.name || "Lê Hoàng Quân"}</h2>
                    <div className="text-[12px] text-[#1E40AF] font-semibold">
                      {user?.role === "STAFF" ? "Cố vấn Dịch vụ / Kỹ thuật viên Tiếp nhận HITL" : (user?.role || "Kỹ thuật viên Bậc 4")}
                    </div>
                    <div className="text-[11px] text-slate-400 font-mono mt-0.5">
                      Mã nhân viên: {user?.id || "STAFF-VF-0891"} &bull; {user?.email || "quan.lh@vinfast.vn"}
                    </div>
                  </div>
                </div>

                <div className="space-y-3 pt-3 border-t border-slate-100 text-[13px]">
                  <div className="flex justify-between py-1">
                    <span className="text-slate-500">Xưởng trực thuộc:</span>
                    <span className="font-semibold text-slate-900">VinFast Times City (Hà Nội)</span>
                  </div>
                  <div className="flex justify-between py-1">
                    <span className="text-slate-500">Trạng thái ca trực:</span>
                    <span className="inline-flex items-center gap-1.5 font-semibold text-emerald-600">
                      <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                      Đang trực tuyến (Active Shift)
                    </span>
                  </div>
                  <div className="flex justify-between py-1">
                    <span className="text-slate-500">Quyền hạn HITL:</span>
                    <span className="px-2 py-0.5 rounded-full bg-[#ECFDF5] text-[#059669] text-[11px] font-bold">
                      Duyệt Brief / Reroute / Gửi Cập Nhật / Đóng Hồ Sơ
                    </span>
                  </div>
                  <div className="flex justify-between py-1">
                    <span className="text-slate-500">Tổng ca giải quyết hôm nay:</span>
                    <span className="font-mono font-bold text-[#1E40AF]">{stats.resolved} hồ sơ</span>
                  </div>
                </div>

                <div className="pt-4 border-t border-slate-100 flex justify-end">
                  <button
                    type="button"
                    onClick={logout}
                    className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-[#FEF2F2] hover:bg-[#FEE2E2] text-[#DC2626] text-[12px] font-semibold transition"
                  >
                    <LogOut className="w-4 h-4" />
                    <span>Đăng xuất tài khoản Staff</span>
                  </button>
                </div>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
