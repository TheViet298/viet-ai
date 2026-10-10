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

import { cleanTicketHeadline } from "./TicketDetailPanel";

export type ConsoleTab =
  | "queue"
  | "overview"
  | "history"
  | "routing"
  | "knowledge"
  | "preview"
  | "profile";

// Helper tính thời gian chờ tương đối: "chờ 12 phút", "chờ 2 giờ", "chờ 3 ngày"
export function getRelativeWaitTime(dateStr?: string): string {
  if (!dateStr) return "chờ --";
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return "chờ --";
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    if (diffMs < 0) return "vừa xong";
    const diffMins = Math.floor(diffMs / (1000 * 60));
    if (diffMins < 1) return "vừa xong";
    if (diffMins < 60) return `chờ ${diffMins} phút`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `chờ ${diffHours} giờ`;
    const diffDays = Math.floor(diffHours / 24);
    return `chờ ${diffDays} ngày`;
  } catch {
    return "chờ --";
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

// Headline ngắn gọn 1 dòng cho Card Queue
function getShortHeadline(ticket: TicketItem): string {
  const title = getTicketDisplayTitle(ticket);
  const cleaned = cleanTicketHeadline(title);
  if (/rùa|turtle/i.test(cleaned)) {
    return "Rùa vàng, giảm công suất";
  }
  if (/CC01/i.test(cleaned)) {
    return "Lỗi handshake sạc DC CC01";
  }
  if (/áp suất lốp|TPMS/i.test(cleaned)) {
    return "Cảnh báo áp suất lốp TPMS";
  }
  if (/bộ sạc tại nhà|wallbox/i.test(cleaned)) {
    return "Sạc Wallbox tự ngắt sau 2h";
  }
  return cleaned;
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
  customerFeedbackTags?: string[];
  reopenReason?: string;
  isAutoClosed?: boolean;
  staffUpdateNotes: string;
}

export const SAMPLE_CASE_HISTORY: HistoricalCase[] = [];

export function StaffConsoleShell() {
  const { user, logout } = useAuth();
  const [activeTab, setActiveTab] = useState<ConsoleTab>("queue");

  // Sidebar collapsible state: default expanded (w-64)
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

  // Tickets state từ hook useTickets
  const {
    tickets,
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
  const [historySearchQuery, setHistorySearchQuery] = useState("");

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

  // Chọn case đồng thời cập nhật URL mà không reload trang (/console?case=...)
  const handleSelectTicket = useCallback((ticketId: string) => {
    setSelectedTicketId(ticketId);
    if (typeof window !== "undefined") {
      const url = new URL(window.location.href);
      url.searchParams.set("case", ticketId);
      window.history.pushState({ caseId: ticketId }, "", url.toString());
    }
  }, []);

  // Undo Action State
  const [undoToast, setUndoToast] = useState<{
    ticketId: string;
    prevStatus: TicketStatus;
    newStatus: TicketStatus;
  } | null>(null);

  const handleStatusUpdate = (ticketId: string, newStatus: TicketStatus) => {
    const prevStatus =
      localTicketStatuses[ticketId] ||
      ticketsWithLocalStatus.find((t) => t.id === ticketId)?.status ||
      "Staff Reviewing";
    setLocalTicketStatuses((prev) => ({ ...prev, [ticketId]: newStatus }));

    // Tự động nhảy sang case tiếp theo trong hàng đợi khi Duyệt/Giải quyết
    const currentIndex = activeQueueTickets.findIndex((t) => t.id === ticketId);
    const remaining = activeQueueTickets.filter((t) => t.id !== ticketId);
    const nextTicket =
      remaining[currentIndex] || remaining[currentIndex - 1] || remaining[0] || null;
    if (
      nextTicket &&
      (newStatus === "In Progress" || newStatus === "Resolved" || newStatus === "Closed")
    ) {
      handleSelectTicket(nextTicket.id);
    }

    // Hiện toast có nút Hoàn tác
    setUndoToast({
      ticketId,
      prevStatus,
      newStatus,
    });
  };

  const handleUndo = () => {
    if (!undoToast) return;
    setLocalTicketStatuses((prev) => ({
      ...prev,
      [undoToast.ticketId]: undoToast.prevStatus,
    }));
    handleSelectTicket(undoToast.ticketId);
    setRoutingConfirmedNotice(
      `Đã hoàn tác: Ca ${undoToast.ticketId} trở về trạng thái ${
        VIETNAMESE_STATUS_MAP[undoToast.prevStatus] || undoToast.prevStatus
      }`
    );
    setUndoToast(null);
  };

  // 1. Toàn bộ tickets trong DB kèm local status (dùng cho tổng thể, badge sidebar, routing, lịch sử)
  const allTicketsWithLocalStatus = useMemo(() => {
    return tickets.map((t) => ({
      ...t,
      status: localTicketStatuses[t.id] || t.status,
    }));
  }, [tickets, localTicketStatuses]);

  // 2. Danh sách tickets đang hiển thị trong Hàng đợi (đã áp dụng bộ lọc và từ khóa tìm kiếm của Queue)
  const ticketsWithLocalStatus = useMemo(() => {
    return filteredTickets.map((t) => ({
      ...t,
      status: localTicketStatuses[t.id] || t.status,
    }));
  }, [filteredTickets, localTicketStatuses]);

  // Tổng số ca đang hoạt động trong toàn hệ thống (không bị giảm khi gõ tìm kiếm)
  const totalActiveQueueCount = useMemo(() => {
    return allTicketsWithLocalStatus.filter(
      (t) => t.status !== "Resolved" && t.status !== "Closed"
    ).length;
  }, [allTicketsWithLocalStatus]);

  // Thống kê số lượng theo từng tab lọc trong Hàng đợi
  const queueStats = useMemo(() => {
    const unclosed = allTicketsWithLocalStatus.filter(
      (t) => t.status !== "Resolved" && t.status !== "Closed"
    );
    return {
      all: unclosed.length,
      critical: unclosed.filter((t) => t.priority === "CRITICAL").length,
      reviewing: unclosed.filter(
        (t) => t.status === "Staff Reviewing" || t.status === "New"
      ).length,
      needsInfo: unclosed.filter((t) => t.status === "Needs Information").length,
      inProgress: unclosed.filter((t) => t.status === "In Progress").length,
    };
  }, [allTicketsWithLocalStatus]);

  // Trọng số ưu tiên
  const priorityWeight: Record<string, number> = {
    CRITICAL: 4,
    HIGH: 3,
    MEDIUM: 2,
    LOW: 1,
  };

  // Lọc và sắp xếp hàng đợi xử lý: Ưu tiên trước, sau đó tới thời gian chờ
  const activeQueueTickets = useMemo(() => {
    return ticketsWithLocalStatus
      .filter((t) => {
        // 1. Luôn loại trừ các case đã Giải quyết (Resolved) hoặc Đã đóng (Closed) khỏi Hàng đợi cần xử lý
        if (t.status === "Resolved" || t.status === "Closed") return false;

        // 2. Lọc nhanh theo pill filter được chọn
        if (queueQuickFilter === "CRITICAL") return t.priority === "CRITICAL";
        if (queueQuickFilter === "Staff Reviewing")
          return t.status === "Staff Reviewing" || t.status === "New";
        if (queueQuickFilter === "Needs Information")
          return t.status === "Needs Information";
        if (queueQuickFilter === "In Progress") return t.status === "In Progress";

        // 3. Mặc định ("ALL" của Hàng đợi): Hiển thị tất cả các ca đang hoạt động cần KTV can thiệp
        return (
          t.status === "Staff Reviewing" ||
          t.status === "Needs Information" ||
          t.status === "In Progress" ||
          t.status === "New" ||
          t.status === "Reopened"
        );
      })
      .sort((a, b) => {
        // Sắp xếp mặc định: Mức ưu tiên (CRITICAL > HIGH > MEDIUM > LOW)
        const weightA = priorityWeight[a.priority] || 1;
        const weightB = priorityWeight[b.priority] || 1;
        if (weightB !== weightA) {
          return weightB - weightA;
        }
        // Cùng mức ưu tiên: ca có thời gian chờ lâu nhất (created_at xa hơn) lên trước
        return new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
      });
  }, [ticketsWithLocalStatus, queueQuickFilter]);

  const currentActiveTicket =
    activeQueueTickets.find((t) => t.id === selectedTicketId) || activeQueueTickets[0] || null;

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

  // Dynamic Intent Distribution derived from allTicketsWithLocalStatus
  const intentDistribution = useMemo(() => {
    const total = allTicketsWithLocalStatus.length;
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

    allTicketsWithLocalStatus.forEach((t) => {
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
  }, [allTicketsWithLocalStatus]);

  // Dynamic Routing Departments active count derived from allTicketsWithLocalStatus
  const liveRoutingDepartments = useMemo(() => {
    const active = allTicketsWithLocalStatus.filter(
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
  }, [allTicketsWithLocalStatus]);

  // Dynamic Case History: Live resolved/closed cases from DB + sample archive
  const realCaseHistory = useMemo(() => {
    const fromDb = allTicketsWithLocalStatus
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

        const isAuto = Boolean(t.is_auto_closed);
        return {
          id: t.id,
          intent: t.intent,
          status: (t.status === "Resolved" || t.status === "Closed" || t.status === "Reopened" ? t.status : "Resolved") as "Resolved" | "Closed" | "Reopened",
          routedTo: routed,
          customerConfirmed: Boolean(t.customer_feedback_score) || (t.status === "Closed" && !isAuto),
          isAutoClosed: isAuto,
          resolvedAt: formattedTime,
          staffName: user?.name || "Kỹ thuật viên VinFast",
          vehicleModel: t.vehicle_model || "VinFast",
          vehicleCode: t.vehicle_code_mock || t.vehicle_model,
          briefSummary: t.issue_summary || getTicketDisplayTitle(t),
          hasLocationConsent: Boolean(t.has_location_consent),
          locationName: t.has_location_consent ? "Tọa độ GPS đã xác thực" : undefined,
          customerFeedbackScore: t.customer_feedback_score ?? undefined,
          customerFeedbackComment: t.customer_feedback_comment ?? undefined,
          customerFeedbackTags: t.customer_feedback_tags || [],
          staffUpdateNotes: t.suggested_action || "Đã kiểm tra kỹ thuật và hoàn tất xử lý theo quy chuẩn VinFast.",
        } as HistoricalCase;
      });

    return fromDb;
  }, [allTicketsWithLocalStatus, user?.name]);

  // Filtered History list
  const filteredHistory = realCaseHistory.filter((item) => {
    if (historyStatusFilter !== "ALL" && item.status !== historyStatusFilter) return false;
    if (historyIntentFilter !== "ALL" && item.intent !== historyIntentFilter) return false;
    if (historySearchQuery.trim()) {
      const q = historySearchQuery.trim().toLowerCase();
      const matchId = item.id.toLowerCase().includes(q);
      const matchVehicle = item.vehicleModel.toLowerCase().includes(q) || (item.vehicleCode && item.vehicleCode.toLowerCase().includes(q));
      const matchSummary = item.briefSummary.toLowerCase().includes(q);
      const matchIntent = item.intent.toLowerCase().includes(q);
      const matchNotes = item.staffUpdateNotes.toLowerCase().includes(q);
      const matchLocation = item.locationName?.toLowerCase().includes(q);
      const matchStaff = item.staffName?.toLowerCase().includes(q);
      if (!matchId && !matchVehicle && !matchSummary && !matchIntent && !matchNotes && !matchLocation && !matchStaff) {
        return false;
      }
    }
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
    { id: "queue", label: "Hàng đợi xử lý", icon: Inbox, count: totalActiveQueueCount },
    { id: "overview", label: "Tổng quan ca trực", icon: LayoutDashboard },
    { id: "history", label: "Lịch sử hồ sơ", icon: History, count: realCaseHistory.length },
    { id: "routing", label: "Bộ phận / Routing", icon: GitBranch, count: liveRoutingDepartments.reduce((acc, d) => acc + d.activeTickets, 0) },
    { id: "knowledge", label: "Knowledge Hub", icon: BookOpen, count: knowledgeArticles.length || 7 },
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
                {user?.name?.charAt(0) || "V"}
              </div>
              {!isSidebarCollapsed && (
                <div className="min-w-0 flex-1 truncate">
                  <div className="text-[12px] font-semibold text-white truncate">
                    {user?.name || "Cố vấn Dịch vụ VinFast"}
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

                {/* Quick Filter Pills với số đếm động & Refresh Button */}
                <div className="flex items-center gap-2 flex-wrap">
                  <div className="flex items-center gap-1 bg-slate-200/50 p-1 rounded-xl text-[11px] font-medium">
                    {[
                      { id: "ALL", label: `Tất cả (${queueStats.all})` },
                      { id: "CRITICAL", label: `🔥 Khẩn cấp (${queueStats.critical})` },
                      { id: "Staff Reviewing", label: `Chờ duyệt (${queueStats.reviewing})` },
                      { id: "Needs Information", label: `Cần thêm tin (${queueStats.needsInfo})` },
                      { id: "In Progress", label: `Đang xử lý (${queueStats.inProgress})` },
                    ].map((pill) => (
                      <button
                        key={pill.id}
                        type="button"
                        onClick={() => setQueueQuickFilter(pill.id)}
                        className={`px-2.5 py-1 rounded-lg transition ${
                          queueQuickFilter === pill.id
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
                    <RefreshCw
                      className={`w-3.5 h-3.5 text-slate-500 ${
                        loading ? "animate-spin text-[#1E40AF]" : ""
                      }`}
                    />
                    <span className="hidden sm:inline">Làm mới</span>
                  </button>
                </div>
              </div>

              {/* Toast thông báo hành động có nút Hoàn tác */}
              {undoToast && (
                <div className="p-3 bg-slate-900 text-white rounded-xl text-[13px] font-medium flex items-center justify-between shadow-lg animate-in fade-in">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span>
                      Đã cập nhật hồ sơ{" "}
                      <strong className="font-mono text-emerald-300">
                        {undoToast.ticketId}
                      </strong>{" "}
                      sang{" "}
                      <strong>
                        {VIETNAMESE_STATUS_MAP[undoToast.newStatus] || undoToast.newStatus}
                      </strong>
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={handleUndo}
                    className="px-3 py-1 rounded-lg bg-white/20 hover:bg-white/30 text-white font-semibold text-[12px] transition active:scale-[0.98]"
                  >
                    Hoàn tác
                  </button>
                </div>
              )}

              {/* Action notification toast */}
              {routingConfirmedNotice && !undoToast && (
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
                      Hồ sơ trong hàng đợi:{" "}
                      <strong className="text-slate-900">{activeQueueTickets.length}</strong>
                    </span>
                    <span className="text-slate-400">Dùng phím ↑ ↓ (hoặc J/K) để duyệt</span>
                  </div>

                  <div className="bg-white rounded-2xl shadow-[0_1px_3px_rgba(0,0,0,0.05)] overflow-hidden divide-y divide-slate-100 h-[calc(100vh-140px)] overflow-y-auto scrollbar-thin">
                    {activeQueueTickets.length === 0 ? (
                      <div className="p-8 text-center text-slate-500 space-y-3">
                        <Inbox className="w-8 h-8 mx-auto text-slate-300" />
                        <div>
                          <p className="text-[13px] font-semibold text-slate-900">
                            {searchQuery.trim()
                              ? `Không tìm thấy ca "${searchQuery.trim()}" trong hàng đợi`
                              : "Hàng đợi xử lý hiện đang trống"}
                          </p>
                          <p className="text-[12px] text-slate-500 mt-1 max-w-xs mx-auto">
                            {searchQuery.trim()
                              ? "Hồ sơ này có thể đã được KTV giải quyết (Resolved) hoặc đã đóng (Closed)."
                              : "Hiện không có hồ sơ nào cần xử lý với bộ lọc hiện tại."}
                          </p>
                        </div>
                        {searchQuery.trim() && (
                          <div className="flex flex-col sm:flex-row items-center justify-center gap-2 pt-1">
                            <button
                              type="button"
                              onClick={() => {
                                setHistorySearchQuery(searchQuery.trim());
                                setActiveTab("history");
                              }}
                              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#1E40AF] hover:bg-[#1D4ED8] text-white text-[12px] font-semibold transition shadow-xs"
                            >
                              <Search className="w-3.5 h-3.5" />
                              <span>Tìm trong Lịch sử hồ sơ</span>
                            </button>
                            <button
                              type="button"
                              onClick={() => setSearchQuery("")}
                              className="px-3 py-1.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-[12px] font-medium transition"
                            >
                              Xóa từ khóa
                            </button>
                          </div>
                        )}
                      </div>
                    ) : (
                      activeQueueTickets.map((ticket) => {
                        const isSelected = (currentActiveTicket?.id || "") === ticket.id;
                        const isCritical = ticket.priority === "CRITICAL";
                        const isHigh = ticket.priority === "HIGH";
                        const isMedium = ticket.priority === "MEDIUM";

                        const headline = getShortHeadline(ticket);
                        const waitTime = getRelativeWaitTime(ticket.created_at);
                        const isSafetyConfirmed =
                          ticket.safety_status === "safe" ||
                          ticket.safety_status === "customer_reported_safe" ||
                          Boolean(ticket.safety_acknowledged_at);

                        return (
                          <div
                            id={`ticket-item-${ticket.id}`}
                            key={ticket.id}
                            onClick={() => handleSelectTicket(ticket.id)}
                            className={`group cursor-pointer p-3.5 transition-all border-l-4 ${
                              isSelected
                                ? "bg-[#EFF3FC] border-l-[#1E40AF] shadow-2xs"
                                : isCritical
                                ? "bg-white border-l-red-500 hover:bg-slate-50/80"
                                : isHigh
                                ? "bg-white border-l-amber-500 hover:bg-slate-50/80"
                                : isMedium
                                ? "bg-white border-l-blue-400 hover:bg-slate-50/80"
                                : "bg-white border-l-transparent hover:border-l-slate-200 hover:bg-slate-50/80"
                            }`}
                          >
                            {/* Dòng 1: Tên khách · Xe | Bên phải: "chờ 12 phút" */}
                            <div className="flex items-center justify-between gap-2 text-[12.5px]">
                              <div className="flex items-center gap-1.5 truncate">
                                <span
                                  className={`truncate ${
                                    isSelected
                                      ? "font-bold text-[#1E40AF]"
                                      : "font-semibold text-slate-900"
                                  }`}
                                >
                                  {ticket.customer_name || ticket.mock_customer_id}
                                </span>
                                <span className="text-slate-400">·</span>
                                <span className="font-medium text-slate-600 shrink-0">
                                  {ticket.vehicle_model}
                                </span>
                              </div>

                              <span className="text-[11px] text-slate-400 font-sans shrink-0 font-medium">
                                {waitTime}
                              </span>
                            </div>

                            {/* Dòng 2: Headline ngắn 1 dòng (bỏ tiền tố giật gân) */}
                            <p
                              className={`mt-1 text-[13px] leading-snug truncate ${
                                isSelected
                                  ? "font-semibold text-slate-900"
                                  : "font-normal text-slate-700 group-hover:text-slate-900"
                              }`}
                              title={headline}
                            >
                              {headline}
                            </p>

                            {/* Dòng 3: Chip ưu tiên, thiếu tin, GPS, đã an toàn */}
                            <div className="mt-2 flex items-center gap-1.5 flex-wrap">
                              {/* Chip Mở lại ca (Reopened) */}
                              {ticket.status === "Reopened" && (
                                <span className="px-1.5 py-0.5 rounded text-[10.5px] font-bold text-purple-700 bg-purple-100 border border-purple-300">
                                  ↺ Mở lại ca
                                </span>
                              )}

                              {/* Chip Ưu tiên */}
                              {isCritical ? (
                                <span className="px-1.5 py-0.5 rounded text-[10.5px] font-bold text-red-600 bg-red-50">
                                  Khẩn cấp
                                </span>
                              ) : isHigh ? (
                                <span className="px-1.5 py-0.5 rounded text-[10.5px] font-semibold text-amber-700 bg-amber-50">
                                  Ưu tiên cao
                                </span>
                              ) : isMedium ? (
                                <span className="px-1.5 py-0.5 rounded text-[10.5px] font-medium text-blue-700 bg-blue-50">
                                  Trung bình
                                </span>
                              ) : (
                                <span className="px-1.5 py-0.5 rounded text-[10.5px] font-medium text-slate-600 bg-slate-100">
                                  Thấp
                                </span>
                              )}

                              {/* Chip Thiếu thông tin */}
                              {(ticket.missing_info_flag ||
                                ticket.status === "Needs Information") && (
                                <span className="px-1.5 py-0.5 rounded text-[10.5px] font-semibold text-amber-800 bg-amber-100/80">
                                  Thiếu thông tin
                                </span>
                              )}

                              {/* Chip GPS */}
                              {ticket.has_location_consent && (
                                <span className="px-1.5 py-0.5 rounded text-[10.5px] font-medium text-[#1E40AF] bg-blue-50">
                                  GPS
                                </span>
                              )}

                              {/* Chip Khách đã an toàn */}
                              {isSafetyConfirmed && (
                                <span className="px-1.5 py-0.5 rounded text-[10.5px] font-semibold text-emerald-700 bg-emerald-50">
                                  ✓ Đã an toàn
                                </span>
                              )}
                            </div>
                          </div>
                        );
                      })
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

              {/* Filter Bar with Quick Search and Styled Pills */}
              <div className="bg-white rounded-2xl p-4 shadow-[0_1px_3px_rgba(0,0,0,0.05)] space-y-3">
                {/* Search Bar Row */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="relative flex-1 max-w-md">
                    <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                    <input
                      type="text"
                      value={historySearchQuery}
                      onChange={(e) => setHistorySearchQuery(e.target.value)}
                      placeholder="Tìm nhanh mã case (ví dụ CASE-...), dòng xe, sự cố, KTV..."
                      className="w-full text-[12px] pl-9 pr-8 py-2 rounded-xl bg-slate-50 border border-slate-200/80 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-[#1E40AF]/20 focus:bg-white transition"
                    />
                    {historySearchQuery && (
                      <button
                        type="button"
                        onClick={() => setHistorySearchQuery("")}
                        className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 p-0.5"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                  <div className="text-[12px] text-slate-500 font-medium">
                    Tìm thấy <strong className="text-slate-900">{filteredHistory.length}</strong> hồ sơ
                  </div>
                </div>

                {/* Filter Pills Row */}
                <div className="flex flex-wrap items-center justify-between gap-3 pt-2.5 border-t border-slate-100">
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
                      {filteredHistory.length === 0 ? (
                        <tr>
                          <td colSpan={7} className="py-12 text-center text-slate-400">
                            Không tìm thấy hồ sơ nào khớp với bộ lọc hoặc từ khóa tìm kiếm.
                          </td>
                        </tr>
                      ) : (
                        filteredHistory.map((item) => (
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
                              {item.isAutoClosed ? (
                                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-semibold bg-slate-100 text-slate-600 border border-slate-200">
                                  ⏱ Tự động đóng (72h)
                                </span>
                              ) : item.customerConfirmed ? (
                                <div className="flex flex-col">
                                  <span className="text-[#059669] font-medium flex items-center gap-1">
                                    <CheckCircle2 className="w-3.5 h-3.5" /> Đã xác nhận
                                  </span>
                                  {item.customerFeedbackScore && (
                                    <span className="text-[11px] text-amber-600 font-semibold mt-0.5 flex items-center gap-0.5">
                                      <Star className="w-3 h-3 fill-amber-500 text-amber-500 inline" />
                                      {item.customerFeedbackScore}/5 sao
                                    </span>
                                  )}
                                </div>
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
                        ))
                      )}
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
                        <div className="p-3.5 rounded-xl bg-[#ECFDF5] space-y-1.5">
                          <div className="flex items-center gap-1 text-[#D97706]">
                            {[...Array(reviewingHistoryCase.customerFeedbackScore)].map((_, i) => (
                              <Star key={i} className="w-4 h-4 fill-current" />
                            ))}
                            <span className="text-[12px] font-bold text-[#065F46] ml-2">Đánh giá của khách hàng</span>
                          </div>
                          {reviewingHistoryCase.customerFeedbackTags && reviewingHistoryCase.customerFeedbackTags.length > 0 && (
                            <div className="flex flex-wrap gap-1.5 pt-1">
                              {reviewingHistoryCase.customerFeedbackTags.map((tag) => (
                                <span key={tag} className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-amber-100 text-amber-800 border border-amber-200">
                                  {tag}
                                </span>
                              ))}
                            </div>
                          )}
                          {reviewingHistoryCase.customerFeedbackComment && (
                            <p className="text-[12px] text-[#065F46] italic">"{reviewingHistoryCase.customerFeedbackComment}"</p>
                          )}
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
                    { id: "SRC-001", title: "Chính sách Bảo hành Ô tô Điện VinFast", url: "https://vinfastauto.com/vn_vi/chinh-sach-bao-hanh-oto", scope: "VF 8 (10 năm/200.000km, pin mua đứt không giới hạn km)" },
                    { id: "SRC-002", title: "Hướng dẫn sử dụng Ứng dụng VinFast", url: "https://vinfastauto.com/vn_vi/huong-dan-su-dung-ung-dung-vinfast", scope: "Đặt lịch xưởng, theo dõi dung lượng pin" },
                    { id: "SRC-003", title: "Thông tin Cứu hộ Khẩn cấp & Cứu hộ Pin 24/7", url: "https://vinfastauto.com/vn_vi/thong-tin-cuu-ho-oto", scope: "Hotline 1900-232389, cứu hộ pin lưu động" },
                    { id: "SRC-004", title: "Biểu phí & Chính sách Sạc tại Trạm Công cộng", url: "https://vinfastauto.com/vn_vi/chinh-sach-va-bieu-phi-sac-pin-cong-cong", scope: "Đơn giá kWh, phí chiếm trụ 1.000đ/phút sau 10 phút" },
                    { id: "SRC-005", title: "Cẩm nang Bảo dưỡng Định kỳ 12.000 km", url: "https://vinfastauto.com/vn_vi/dich-vu-bao-duong-oto", scope: "6 hạng mục kiểm tra tiêu chuẩn pack pin, phanh, gầm" },
                    { id: "SRC-006", title: "Danh mục Sản phẩm & Chính sách Bán hàng", url: "https://vinfastauto.com/vn_vi/", scope: "Dải xe điện VF 3, VF 5, VF 6, VF 7, VF 8, VF 9" },
                    { id: "SRC-007", title: "Sổ tay Hướng dẫn Sử dụng VF 8", url: "https://om.vinfastauto.com/vi_vn/detail?car=VF8&year=2026", scope: "Sổ tay điện tử hướng dẫn chi tiết vận hành VF 8" },
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
                    {user?.name?.charAt(0) || "V"}
                  </div>
                  <div>
                    <h2 className="text-base font-bold text-slate-900">{user?.name || "Cố vấn Dịch vụ VinFast"}</h2>
                    <div className="text-[12px] text-[#1E40AF] font-semibold">
                      {user?.role === "STAFF" ? "Cố vấn Dịch vụ / Kỹ thuật viên Tiếp nhận HITL" : (user?.role || "Kỹ thuật viên Bậc 4")}
                    </div>
                    <div className="text-[11px] text-slate-400 font-mono mt-0.5">
                      Mã nhân viên: {user?.id || "STAFF_001"} &bull; {user?.email || "staff@vinfast.vn"}
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
