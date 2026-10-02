"use client";

import { useState } from "react";
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
} from "lucide-react";
import { useAuth } from "@/features/shared";
import { useTickets, TicketItem } from "../hooks/useTickets";
import { TicketStatus } from "../types";
import { TicketDetailPanel } from "./TicketDetailPanel";

export type ConsoleTab =
  | "queue"
  | "overview"
  | "history"
  | "routing"
  | "knowledge"
  | "preview"
  | "profile";

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
    color: "bg-[#EFF3FC] text-[#1E40AF] border-[#1E40AF]/20",
  },
  {
    id: "service_center",
    name: "Service Center",
    badge: "Xưởng Dịch Vụ",
    intent: "Service/Incident",
    description: "Xử lý cảnh báo táp-lô, rùa vàng, lỗi 12V, lỗi điều hòa, đặt hẹn bảo dưỡng và kiểm tra OBD-II.",
    lead: "Trần Đình Triển (Cố vấn Dịch vụ)",
    activeTickets: 3,
    color: "bg-[#FEF3C7] text-[#D97706] border-[#D97706]/20",
  },
  {
    id: "customer_care",
    name: "Customer Care",
    badge: "Chăm Sóc Khách Hàng",
    intent: "Complaint/Feedback",
    description: "Tiếp nhận khiếu nại thái độ phục vụ, xe xăng chiếm chỗ sạc, trừ tiền trùng hoặc lỗi ứng dụng.",
    lead: "Nguyễn Mai Anh (CSKH)",
    activeTickets: 1,
    color: "bg-[#F3E8FF] text-[#7E22CE] border-[#7E22CE]/20",
  },
  {
    id: "sales_advisor",
    name: "Sales Advisor",
    badge: "Tư Vấn Bán Hàng",
    intent: "Sales/General Info",
    description: "Tiếp nhận nhu cầu lái thử, tư vấn thông số kỹ thuật xe VF 3 đến VF 9, giá lăn bánh và đặt cọc.",
    lead: "Phạm Quốc Hưng (Showroom Times City)",
    activeTickets: 0,
    color: "bg-[#ECFDF5] text-[#065F46] border-[#065F46]/20",
  },
  {
    id: "emergency_demo",
    name: "Emergency Support Demo",
    badge: "Cứu Hộ Khẩn Cấp",
    intent: "Critical Safety",
    description: "Đội điều phối cứu hộ giao thông 24/7 cho các ca cháy nổ, mất phanh, rùa vàng cao tốc (Hotline 1900-232389).",
    lead: "Đội phản ứng nhanh Cao Tốc VinFast",
    activeTickets: 1,
    color: "bg-[#FEF2F2] text-[#DC2626] border-[#DC2626]/20",
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

  // Customer Preview demo chat session
  const [previewChatInput, setPreviewChatInput] = useState("");
  const [previewMessages, setPreviewMessages] = useState<Array<{ sender: "user" | "bot"; text: string }>>([
    {
      sender: "bot",
      text: "Dạ VinFast xin chào anh/chị! Em có thể hỗ trợ kiểm tra thông số kỹ thuật xe, biểu phí sạc hoặc tiếp nhận sự cố nào ạ?",
    },
  ]);

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

  const currentActiveTicket =
    activeQueueTickets.find((t) => t.id === selectedTicketId) || activeQueueTickets[0] || null;

  const handleSendPreviewMessage = (e: React.FormEvent) => {
    e.preventDefault();
    if (!previewChatInput.trim()) return;
    const userMsg = previewChatInput.trim();
    setPreviewMessages((prev) => [...prev, { sender: "user", text: userMsg }]);
    setPreviewChatInput("");

    setTimeout(() => {
      setPreviewMessages((prev) => [
        ...prev,
        {
          sender: "bot",
          text: `[Chế độ Demo Preview] Đã nhận tín hiệu từ phiên thử nghiệm: "${userMsg}". AI Agent sẽ thực hiện bóc tách intent và citation RAG chính xác.`,
        },
      ]);
    }, 600);
  };

  // Filtered History list
  const filteredHistory = SAMPLE_CASE_HISTORY.filter((item) => {
    if (historyStatusFilter !== "ALL" && item.status !== historyStatusFilter) return false;
    if (historyIntentFilter !== "ALL" && item.intent !== historyIntentFilter) return false;
    return true;
  });

  return (
    <div className="min-h-screen bg-[#F8FAFC] flex flex-col antialiased text-[#0F172A]">
      {/* ─────────────────────────────────────────────────────────────
          1. STAFF CONSOLE TOPBAR (Riêng biệt, không dùng Navbar chung)
      ───────────────────────────────────────────────────────────── */}
      <header className="sticky top-0 z-40 bg-white border-b border-[#E2E8F0] shadow-xs">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-14">
            {/* Left: Brand + Badge */}
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-xl bg-[#1E40AF] flex items-center justify-center text-white shadow-sm">
                <ScanLine className="w-4 h-4 text-white" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-bold text-[15px] tracking-tight text-[#0F172A]">
                    ServiceFlow <span className="text-[#1E40AF]">AI</span>
                  </span>
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-[#EFF3FC] text-[#1E40AF] border border-[#1E40AF]/20">
                    Staff Portal
                  </span>
                </div>
                <div className="text-[10px] text-[#64748B] font-mono">
                  Bàn Điều Phối & Kỹ Thuật Viên Xưởng
                </div>
              </div>
            </div>

            {/* Middle: API Status & Shift */}
            <div className="hidden md:flex items-center gap-4 text-[12px] text-[#64748B]">
              <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[#F1F5F9] border border-[#E2E8F0]">
                <span className={`w-2 h-2 rounded-full ${isLiveApi ? "bg-[#10B981] animate-pulse" : "bg-[#94A3B8]"}`} />
                <span>{isLiveApi ? "Live REST API (8000)" : "Offline Seed Mode"}</span>
              </span>
              <span className="text-[12px] text-[#475569]">
                Cơ sở: <strong className="text-[#0F172A]">VinFast Times City</strong>
              </span>
            </div>

            {/* Right: Quick Customer Preview button & Staff Profile */}
            <div className="flex items-center gap-2.5">
              <button
                type="button"
                onClick={() => setActiveTab("preview")}
                className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-[#E2E8F0] bg-[#F8FAFC] hover:bg-[#F1F5F9] text-[12px] font-medium text-[#475569] transition"
              >
                <Eye className="w-3.5 h-3.5 text-[#1E40AF]" />
                <span>Customer Preview</span>
              </button>

              <div className="flex items-center gap-2 pl-2 border-l border-[#E2E8F0]">
                <div className="w-7 h-7 rounded-full bg-[#1E40AF] text-white flex items-center justify-center text-[12px] font-bold">
                  {user?.name?.charAt(0) || "Q"}
                </div>
                <div className="hidden lg:flex flex-col text-left">
                  <span className="text-[12px] font-semibold leading-tight text-[#0F172A]">
                    {user?.name || "Lê Hoàng Quân"}
                  </span>
                  <span className="text-[10px] text-[#64748B] font-mono">Cố vấn KTV</span>
                </div>

                <button
                  type="button"
                  onClick={logout}
                  className="rounded-lg p-1.5 text-[#64748B] hover:bg-[#FEE2E2] hover:text-[#DC2626] transition"
                  title="Đăng xuất tài khoản Staff"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>

          {/* ─────────────────────────────────────────────────────────────
              2. SUB-NAVIGATION TABS (7 Phân hệ nghiệp vụ chuẩn hóa)
          ───────────────────────────────────────────────────────────── */}
          <nav className="flex items-center space-x-1 overflow-x-auto border-t border-[#F1F5F9] py-1.5 scrollbar-none">
            {[
              { id: "queue", label: "Hàng đợi xử lý", icon: Inbox, count: activeQueueTickets.length },
              { id: "overview", label: "Tổng quan", icon: LayoutDashboard },
              { id: "history", label: "Lịch sử case", icon: History, count: SAMPLE_CASE_HISTORY.length },
              { id: "routing", label: "Bộ phận / Routing", icon: GitBranch, count: 5 },
              { id: "knowledge", label: "Knowledge Hub", icon: BookOpen, count: 7 },
              { id: "preview", label: "Customer Preview", icon: Eye },
              { id: "profile", label: "Hồ sơ Staff", icon: User },
            ].map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as ConsoleTab)}
                  className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[13px] font-medium transition-all whitespace-nowrap ${
                    isActive
                      ? "bg-[#1E40AF] text-white font-semibold shadow-xs"
                      : "text-[#64748B] hover:bg-[#F1F5F9] hover:text-[#0F172A]"
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                  <span>{tab.label}</span>
                  {tab.count !== undefined && (
                    <span
                      className={`px-1.5 py-0.2 rounded-full text-[10px] font-bold ${
                        isActive
                          ? "bg-white/20 text-white"
                          : "bg-[#E2E8F0] text-[#475569]"
                      }`}
                    >
                      {tab.count}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>
        </div>
      </header>

      {/* ─────────────────────────────────────────────────────────────
          3. MAIN CONSOLE CONTENT CONTAINER
      ───────────────────────────────────────────────────────────── */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-5">
        {/* =========================================================
            TAB 1: HÀNG ĐỢI XỬ LÝ (QUEUE - MÀN MỞ ĐẦU CHÍNH)
        ========================================================= */}
        {activeTab === "queue" && (
          <div className="space-y-4">
            {/* Top Control Bar with Quick Filters */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 bg-white border border-[#E2E8F0] rounded-2xl p-4 shadow-xs">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-[#EFF3FC] text-[#1E40AF] flex items-center justify-center font-bold shrink-0">
                  <Inbox className="w-4 h-4" />
                </div>
                <div>
                  <h1 className="text-xl font-semibold text-[#0F172A] leading-tight">
                    Hàng Đợi Xử Lý Hồ Sơ (Active Queue)
                  </h1>
                  <p className="text-xs text-[#64748B] mt-0.5">
                    Tập trung các hồ sơ cần hành động: Critical, Staff Reviewing, Needs Information, In Progress.
                  </p>
                </div>
              </div>

              {/* Filter controls & Search */}
              <div className="flex items-center gap-2 flex-wrap">
                <div className="relative">
                  <Search className="w-3.5 h-3.5 text-[#94A3B8] absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Tìm mã case, xe, lỗi..."
                    className="text-[12px] pl-8 pr-7 py-1.5 rounded-xl border border-[#E2E8F0] bg-[#F8FAFC] text-[#0F172A] focus:bg-white focus:outline-none focus:ring-2 focus:ring-[#1E40AF]/20"
                  />
                  {searchQuery && (
                    <button
                      type="button"
                      onClick={() => setSearchQuery("")}
                      className="absolute right-2 top-1/2 -translate-y-1/2 text-[#94A3B8] hover:text-[#0F172A]"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>

                {/* Quick Filter Pills */}
                <div className="flex items-center gap-1 bg-[#F1F5F9] p-1 rounded-xl text-[11px] font-medium">
                  {[
                    { id: "ALL", label: "Tất cả" },
                    { id: "CRITICAL", label: "Critical" },
                    { id: "Staff Reviewing", label: "Chờ duyệt" },
                    { id: "Needs Information", label: "Cần tin" },
                    { id: "In Progress", label: "Đang xử lý" },
                  ].map((pill) => (
                    <button
                      key={pill.id}
                      type="button"
                      onClick={() => setQueueQuickFilter(pill.id)}
                      className={`px-2.5 py-1 rounded-lg transition ${
                        queueQuickFilter === pill.id
                          ? "bg-white text-[#0F172A] font-semibold shadow-xs"
                          : "text-[#64748B] hover:text-[#0F172A]"
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
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium bg-white border border-[#E2E8F0] rounded-xl hover:bg-[#F8FAFC] text-[#475569] shadow-xs"
                >
                  <RefreshCw className={`w-3.5 h-3.5 text-[#64748B] ${loading ? "animate-spin text-[#1E40AF]" : ""}`} />
                  <span className="hidden sm:inline">Làm mới</span>
                </button>
              </div>
            </div>

            {/* Notification when action completed */}
            {routingConfirmedNotice && (
              <div className="p-3 bg-[#ECFDF5] border border-[#10B981]/30 rounded-xl text-[#065F46] text-[13px] font-medium flex items-center gap-2 animate-in fade-in">
                <Check className="w-4 h-4 text-[#10B981]" />
                <span>{routingConfirmedNotice}</span>
              </div>
            )}

            {/* Master-Detail Split Layout */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
              {/* CỘT TRÁI (5 Cols / 42%): Danh sách Hàng Đợi */}
              <div className="lg:col-span-5 flex flex-col space-y-2.5">
                <div className="flex items-center justify-between text-[12px] px-1 text-[#64748B]">
                  <span>
                    Hồ sơ phù hợp: <strong className="text-[#0F172A]">{activeQueueTickets.length}</strong>
                  </span>
                  <span>Ưu tiên Critical lên đầu</span>
                </div>

                <div className="space-y-2.5 h-[calc(100vh-220px)] overflow-y-auto pr-1.5 scrollbar-thin">
                  {activeQueueTickets.length === 0 ? (
                    <div className="bg-white border border-[#E2E8F0] rounded-2xl p-8 text-center text-[#64748B]">
                      <Inbox className="w-8 h-8 mx-auto text-[#CBD5E1] mb-2" />
                      <p className="text-[13px] font-semibold text-[#0F172A]">Hàng đợi hiện đang trống</p>
                      <p className="text-[12px] mt-1">Không có hồ sơ nào khớp với bộ lọc hiện tại.</p>
                    </div>
                  ) : (
                    activeQueueTickets.map((ticket) => {
                      const isSelected = (currentActiveTicket?.id || "") === ticket.id;
                      const isCritical = ticket.priority === "CRITICAL";
                      const isHigh = ticket.priority === "HIGH";

                      return (
                        <div
                          key={ticket.id}
                          onClick={() => setSelectedTicketId(ticket.id)}
                          className={`cursor-pointer rounded-2xl p-3.5 border transition-all ${
                            isSelected
                              ? "bg-white border-[#1E40AF] ring-2 ring-[#1E40AF]/15 shadow-sm"
                              : isCritical
                              ? "bg-[#FEF2F2]/30 border-l-[4px] border-l-[#DC2626] border-[#DC2626]/20 hover:bg-[#FEF2F2]/60"
                              : isHigh
                              ? "bg-white border-l-[4px] border-l-[#D97706] border-[#E2E8F0] hover:border-[#CBD5E1] shadow-xs"
                              : "bg-white border-l-[4px] border-l-[#2563EB] border-[#E2E8F0] hover:border-[#CBD5E1] shadow-xs"
                          }`}
                        >
                          <div className="flex items-center justify-between gap-2">
                            <span className="font-mono text-[12px] font-bold text-[#0F172A] flex items-center gap-1.5">
                              {isCritical && <Flame className="w-3.5 h-3.5 text-[#DC2626] shrink-0" />}
                              {ticket.id}
                            </span>
                            <div className="flex items-center gap-1.5">
                              <span
                                className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                                  isCritical
                                    ? "bg-[#DC2626] text-white"
                                    : isHigh
                                    ? "bg-[#FFFBEB] text-[#D97706] border border-[#D97706]/30"
                                    : "bg-[#EFF3FC] text-[#1E40AF]"
                                }`}
                              >
                                {ticket.priority}
                              </span>
                              <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-[#F1F5F9] text-[#475569]">
                                {ticket.status}
                              </span>
                            </div>
                          </div>

                          <div className="mt-1.5 text-[13px] font-medium text-[#0F172A] line-clamp-1">
                            {ticket.issue_summary || "Yêu cầu kiểm tra sự cố"}
                          </div>

                          <div className="mt-2 pt-2 border-t border-[#F1F5F9] flex items-center justify-between text-[11px] text-[#64748B]">
                            <div className="flex items-center gap-2">
                              <span className="flex items-center gap-1 font-semibold text-[#0F172A]">
                                <Car className="w-3 h-3 text-[#1E40AF]" />
                                {ticket.vehicle_model}
                              </span>
                              {ticket.has_location_consent && (
                                <span className="px-1.5 py-0.2 rounded text-[9px] font-bold bg-[#EFF3FC] text-[#1E40AF] flex items-center gap-0.5">
                                  <MapPin className="w-2.5 h-2.5" /> GPS
                                </span>
                              )}
                              {ticket.error_code_short && (
                                <span className="px-1.5 py-0.2 rounded text-[9px] font-mono font-bold bg-[#FEF2F2] text-[#DC2626]">
                                  {ticket.error_code_short}
                                </span>
                              )}
                            </div>
                            <span className="font-mono text-[10px]">
                              {new Date(ticket.created_at).toLocaleTimeString("vi-VN", {
                                hour: "2-digit",
                                minute: "2-digit",
                              })}
                            </span>
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>
              </div>

              {/* CỘT PHẢI (7 Cols / 58%): TicketDetailPanel Chi Tiết & Triage */}
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
                  <div className="bg-white border border-[#E2E8F0] rounded-2xl p-12 text-center text-[#64748B] h-[calc(100vh-220px)] flex flex-col items-center justify-center">
                    <Inbox className="w-10 h-10 text-[#CBD5E1] mb-2" />
                    <p className="text-[14px] font-semibold text-[#0F172A]">Chưa chọn hồ sơ nào</p>
                    <p className="text-[12px] mt-1 text-[#64748B]">
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
              <h1 className="text-xl font-semibold text-[#0F172A]">Tổng Quan Ca Trực (Dashboard Summary)</h1>
              <p className="text-xs text-[#64748B] mt-0.5">Số liệu thống kê hồ sơ sự cố tiếp nhận trong ngày hôm nay.</p>
            </div>

            {/* KPI 4 Cards */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="bg-white border border-[#E2E8F0] rounded-2xl p-4 shadow-xs">
                <span className="text-[11px] font-bold uppercase tracking-wider text-[#64748B]">Tổng ca trực</span>
                <div className="text-2xl font-bold text-[#0F172A] mt-2">{stats.total}</div>
                <div className="text-[11px] text-[#64748B] mt-1">Đã đồng bộ thời gian thực</div>
              </div>

              <div className="bg-white border border-[#DC2626]/20 rounded-2xl p-4 shadow-xs bg-[#FEF2F2]/30">
                <span className="text-[11px] font-bold uppercase tracking-wider text-[#DC2626] flex items-center gap-1">
                  <Flame className="w-3.5 h-3.5 text-[#DC2626]" /> Ca khẩn cấp (Critical)
                </span>
                <div className="text-2xl font-bold text-[#DC2626] mt-2">{stats.critical}</div>
                <div className="text-[11px] text-[#DC2626] mt-1">Ưu tiên cứu hộ cao tốc</div>
              </div>

              <div className="bg-white border border-[#D97706]/20 rounded-2xl p-4 shadow-xs bg-[#FFFBEB]/30">
                <span className="text-[11px] font-bold uppercase tracking-wider text-[#D97706]">Chờ duyệt (Reviewing)</span>
                <div className="text-2xl font-bold text-[#D97706] mt-2">{stats.reviewing}</div>
                <div className="text-[11px] text-[#D97706] mt-1">Cần chuyên viên xác nhận</div>
              </div>

              <div className="bg-white border border-[#10B981]/20 rounded-2xl p-4 shadow-xs bg-[#ECFDF5]/30">
                <span className="text-[11px] font-bold uppercase tracking-wider text-[#059669]">Đã giải quyết (Resolved)</span>
                <div className="text-2xl font-bold text-[#059669] mt-2">{stats.resolved}</div>
                <div className="text-[11px] text-[#059669] mt-1">Hoàn thành ca hôm nay</div>
              </div>
            </div>

            {/* Phân bố Intent & Cảnh báo */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
              <div className="bg-white border border-[#E2E8F0] rounded-2xl p-5 shadow-xs space-y-4">
                <h3 className="text-[14px] font-semibold text-[#0F172A]">Phân bố theo Nhóm Sự Cố (Intent)</h3>
                <div className="space-y-3 text-[13px]">
                  <div>
                    <div className="flex justify-between font-medium">
                      <span>Sạc & Pin (Charging/Battery)</span>
                      <span className="font-mono">55%</span>
                    </div>
                    <div className="w-full h-2 rounded-full bg-[#F1F5F9] mt-1 overflow-hidden">
                      <div className="h-full bg-[#1E40AF] rounded-full w-[55%]" />
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between font-medium">
                      <span>Kỹ thuật & Cảnh báo táp-lô (Service/Incident)</span>
                      <span className="font-mono">30%</span>
                    </div>
                    <div className="w-full h-2 rounded-full bg-[#F1F5F9] mt-1 overflow-hidden">
                      <div className="h-full bg-[#D97706] rounded-full w-[30%]" />
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between font-medium">
                      <span>Khiếu nại & Phản hồi (Complaint)</span>
                      <span className="font-mono">10%</span>
                    </div>
                    <div className="w-full h-2 rounded-full bg-[#F1F5F9] mt-1 overflow-hidden">
                      <div className="h-full bg-[#7E22CE] rounded-full w-[10%]" />
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between font-medium">
                      <span>Tư vấn xe & Bán hàng (Sales/FAQ)</span>
                      <span className="font-mono">5%</span>
                    </div>
                    <div className="w-full h-2 rounded-full bg-[#F1F5F9] mt-1 overflow-hidden">
                      <div className="h-full bg-[#059669] rounded-full w-[5%]" />
                    </div>
                  </div>
                </div>
              </div>

              <div className="bg-white border border-[#E2E8F0] rounded-2xl p-5 shadow-xs space-y-3">
                <h3 className="text-[14px] font-semibold text-[#0F172A]">Nguyên tắc Bàn Giao Ca Trực</h3>
                <ul className="text-[13px] text-[#475569] space-y-2 list-disc pl-4 leading-relaxed">
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
              <h1 className="text-xl font-semibold text-[#0F172A]">Lịch Sử Hồ Sơ Sự Cố (Case History & Audit)</h1>
              <p className="text-xs text-[#64748B] mt-0.5">
                Tra cứu các hồ sơ đã giải quyết, đóng hoặc mở lại; phục vụ bàn giao ca trực và kiểm tra chất lượng AI.
              </p>
            </div>

            {/* Filter Bar with Styled Pills */}
            <div className="flex flex-wrap items-center justify-between gap-3 bg-white border border-[#E2E8F0] rounded-2xl p-4 shadow-xs">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-[12px] font-semibold text-[#64748B]">Trạng thái:</span>
                <div className="flex items-center gap-1 bg-[#F1F5F9] p-1 rounded-xl text-[11px] font-medium">
                  {["ALL", "Resolved", "Closed", "Reopened"].map((st) => (
                    <button
                      key={st}
                      type="button"
                      onClick={() => setHistoryStatusFilter(st)}
                      className={`px-2.5 py-1 rounded-lg transition ${
                        historyStatusFilter === st
                          ? "bg-white text-[#0F172A] font-semibold shadow-xs"
                          : "text-[#64748B] hover:text-[#0F172A]"
                      }`}
                    >
                      {st === "ALL" ? "Tất cả" : st}
                    </button>
                  ))}
                </div>
              </div>

              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-[12px] font-semibold text-[#64748B]">Ý định:</span>
                <div className="flex items-center gap-1 bg-[#F1F5F9] p-1 rounded-xl text-[11px] font-medium">
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
                      className={`px-2.5 py-1 rounded-lg transition ${
                        historyIntentFilter === it.id
                          ? "bg-white text-[#0F172A] font-semibold shadow-xs"
                          : "text-[#64748B] hover:text-[#0F172A]"
                      }`}
                    >
                      {it.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* History Table */}
            <div className="bg-white border border-[#E2E8F0] rounded-2xl overflow-hidden shadow-xs">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-[13px]">
                  <thead className="bg-[#F8FAFC] border-b border-[#E2E8F0] text-[11px] font-bold uppercase tracking-wider text-[#64748B]">
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
                  <tbody className="divide-y divide-[#F1F5F9]">
                    {filteredHistory.map((item) => (
                      <tr key={item.id} className="hover:bg-[#F8FAFC] transition">
                        <td className="py-3.5 px-4 font-mono font-bold text-[#0F172A]">{item.id}</td>
                        <td className="py-3.5 px-4">
                          <div className="font-semibold text-[#0F172A]">{item.intent}</div>
                          <div className="text-[11px] text-[#64748B]">{item.vehicleModel}</div>
                        </td>
                        <td className="py-3.5 px-4">
                          <span
                            className={`px-2.5 py-0.5 rounded-full text-[11px] font-bold uppercase ${
                              item.status === "Closed"
                                ? "bg-[#ECFDF5] text-[#059669] border border-[#10B981]/20"
                                : item.status === "Reopened"
                                ? "bg-[#FEF2F2] text-[#DC2626] border border-[#DC2626]/20"
                                : "bg-[#EFF3FC] text-[#1E40AF] border border-[#1E40AF]/20"
                            }`}
                          >
                            {item.status}
                          </span>
                        </td>
                        <td className="py-3.5 px-4 text-[12px] font-medium text-[#475569]">{item.routedTo}</td>
                        <td className="py-3.5 px-4 text-[12px]">
                          {item.customerConfirmed ? (
                            <span className="text-[#059669] font-medium flex items-center gap-1">
                              <CheckCircle2 className="w-3.5 h-3.5" /> Đã xác nhận
                            </span>
                          ) : item.status === "Reopened" ? (
                            <span className="text-[#DC2626] font-medium">Báo chưa giải quyết</span>
                          ) : (
                            <span className="text-[#64748B]">Chưa xác nhận</span>
                          )}
                        </td>
                        <td className="py-3.5 px-4 text-[12px] text-[#64748B] font-mono">{item.resolvedAt}</td>
                        <td className="py-3.5 px-4 text-right">
                          <button
                            type="button"
                            onClick={() => setReviewingHistoryCase(item)}
                            className="inline-flex items-center gap-1 px-3 py-1.5 rounded-xl bg-white border border-[#E2E8F0] hover:bg-[#F8FAFC] text-[#1E40AF] text-[12px] font-semibold transition shadow-xs"
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
                <div className="bg-white border border-[#E2E8F0] rounded-3xl max-w-2xl w-full p-6 shadow-2xl space-y-4 max-h-[90vh] overflow-y-auto animate-in zoom-in-95">
                  <div className="flex items-center justify-between pb-3 border-b border-[#E2E8F0]">
                    <div>
                      <div className="font-mono text-lg font-bold text-[#0F172A]">{reviewingHistoryCase.id}</div>
                      <div className="text-[12px] text-[#64748B]">Hồ sơ lưu trữ kiểm định chất lượng AI & Bàn giao</div>
                    </div>
                    <button
                      type="button"
                      onClick={() => setReviewingHistoryCase(null)}
                      className="p-1.5 text-[#64748B] hover:text-[#0F172A] rounded-lg hover:bg-[#F1F5F9]"
                    >
                      <X className="w-5 h-5" />
                    </button>
                  </div>

                  <div className="space-y-3 text-[13px]">
                    <div className="p-3.5 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0]">
                      <div className="text-[11px] font-bold uppercase text-[#1E40AF] mb-1">Case Brief Ban Đầu (AI Trích Xuất)</div>
                      <p className="text-[#0F172A] font-medium leading-relaxed">{reviewingHistoryCase.briefSummary}</p>
                    </div>

                    {reviewingHistoryCase.hasLocationConsent && (
                      <div className="p-3 rounded-xl bg-[#EFF3FC] border border-[#1E40AF]/20 text-[12px] flex items-center gap-2">
                        <MapPin className="w-4 h-4 text-[#1E40AF] shrink-0" />
                        <span>Vị trí khách chia sẻ: <strong>{reviewingHistoryCase.locationName}</strong></span>
                      </div>
                    )}

                    <div className="p-3.5 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0]">
                      <div className="text-[11px] font-bold uppercase text-[#475569] mb-1">Ghi Chú Kỹ Thuật (Staff Update)</div>
                      <p className="text-[#475569] leading-relaxed">{reviewingHistoryCase.staffUpdateNotes}</p>
                    </div>

                    {reviewingHistoryCase.customerFeedbackScore && (
                      <div className="p-3.5 rounded-xl bg-[#ECFDF5] border border-[#10B981]/20">
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
                      <div className="p-3.5 rounded-xl bg-[#FEF2F2] border border-[#DC2626]/20">
                        <div className="text-[11px] font-bold uppercase text-[#DC2626] mb-1">Lý do khách mở lại (Reopened)</div>
                        <p className="text-[12px] text-[#DC2626] font-medium">{reviewingHistoryCase.reopenReason}</p>
                      </div>
                    )}
                  </div>

                  <div className="pt-3 border-t border-[#E2E8F0] flex justify-end">
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
              <h1 className="text-xl font-semibold text-[#0F172A]">Danh Mục Bộ Phận Tiếp Nhận (Routing Directory P0)</h1>
              <p className="text-xs text-[#64748B] mt-0.5">
                Cấu hình phân luồng điều phối tự động và thủ công. Không can thiệp sang CRM bên ngoài ở bản MVP.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {ROUTING_DEPARTMENTS.map((dept) => (
                <div key={dept.id} className="bg-white border border-[#E2E8F0] rounded-2xl p-5 shadow-xs flex flex-col justify-between space-y-4">
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-bold uppercase ${dept.color}`}>
                        {dept.badge}
                      </span>
                      <span className="text-[11px] font-mono text-[#64748B]">
                        {dept.activeTickets} ca active
                      </span>
                    </div>

                    <h3 className="text-[15px] font-semibold text-[#0F172A]">{dept.name}</h3>
                    <p className="text-[12px] text-[#64748B] leading-relaxed">{dept.description}</p>
                  </div>

                  <div className="pt-3 border-t border-[#F1F5F9] text-[11px] text-[#475569] space-y-1">
                    <div><strong>Intent tiếp nhận:</strong> <code className="text-[#1E40AF]">{dept.intent}</code></div>
                    <div><strong>Phụ trách chính:</strong> {dept.lead}</div>
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
            <div>
              <h1 className="text-xl font-semibold text-[#0F172A]">Knowledge Hub Nội Bộ (RAG Knowledge Sources)</h1>
              <p className="text-xs text-[#64748B] mt-0.5">
                Cơ sở tri thức 7 nguồn chính thống được kiểm chứng mà AI Agent sử dụng để trích dẫn URL cho khách hàng.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {[
                { id: "SRC-001", title: "Chính sách Bảo hành Ô tô Điện VinFast", url: "https://vinfastauto.com/vn_vi/chinh-sach-bao-hanh-xe-dien", scope: "VF 8 (10 năm/200.000km, pin mua đứt không giới hạn km)" },
                { id: "SRC-002", title: "Hướng dẫn sử dụng Ứng dụng VinFast", url: "https://vinfastauto.com/vn_vi/huong-dan-su-dung-ung-dung-vinfast", scope: "Đặt lịch xưởng, theo dõi dung lượng pin" },
                { id: "SRC-003", title: "Thông tin Cứu hộ Khẩn cấp & Cứu hộ Pin 24/7", url: "https://vinfastauto.com/vn_vi/dich-vu-cuu-ho-24-7", scope: "Hotline 1900-232389, cứu hộ pin lưu động" },
                { id: "SRC-004", title: "Biểu phí & Chính sách Sạc tại Trạm Công cộng", url: "https://vinfastauto.com/vn_vi/chinh-sach-bieu-phi-sac-xe-dien", scope: "Đơn giá kWh, phí chiếm trụ 1.000đ/phút sau 10 phút" },
                { id: "SRC-005", title: "Cẩm nang Bảo dưỡng Định kỳ 12.000 km", url: "https://vinfastauto.com/vn_vi/lich-bao-duong-dinh-ky-xe-dien", scope: "6 hạng mục kiểm tra tiêu chuẩn pack pin, phanh, gầm" },
                { id: "SRC-006", title: "Danh mục Sản phẩm & Chính sách Bán hàng", url: "https://vinfastauto.com/vn_vi/cac-dong-xe-o-to", scope: "Dải xe điện VF 3, VF 5, VF 6, VF 7, VF 8, VF 9" },
                { id: "SRC-007", title: "Thông số Kỹ thuật Chi tiết Catalog", url: "https://vinfastauto.com/vn_vi/thong-so-ky-thuat-o-to-dien", scope: "VF 7 Plus 349HP AWD vs Eco 201HP FWD, kích thước VF 9" },
              ].map((item) => (
                <div key={item.id} className="bg-white border border-[#E2E8F0] rounded-2xl p-4 shadow-xs space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-[11px] font-bold bg-[#EFF3FC] text-[#1E40AF] px-2 py-0.5 rounded-md border border-[#1E40AF]/20">
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
                  <h4 className="text-[14px] font-semibold text-[#0F172A]">{item.title}</h4>
                  <p className="text-[12px] text-[#64748B]"><strong>Phạm vi trích dẫn:</strong> {item.scope}</p>
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
                <h1 className="text-xl font-semibold text-[#0F172A]">Chế Độ Xem Trước Trải Nghiệm Khách (Customer Preview)</h1>
                <p className="text-xs text-[#64748B] mt-0.5">
                  Thử nghiệm tương tác với trợ lý AI bằng session demo riêng biệt; không lẫn case thật của khách hàng.
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

            {/* Khung Demo Chat Preview */}
            <div className="max-w-2xl mx-auto bg-white border border-[#E2E8F0] rounded-3xl shadow-md overflow-hidden flex flex-col h-[520px]">
              {/* Preview header */}
              <div className="bg-[#1E40AF] text-white p-4 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center font-bold">AI</div>
                  <div>
                    <div className="text-[13px] font-bold">Trợ Lý Dịch Vụ VinFast (Preview)</div>
                    <div className="text-[10px] text-white/80">Phiên demo thử nghiệm nội bộ</div>
                  </div>
                </div>
                <span className="px-2 py-0.5 rounded-full bg-white/20 text-[10px] font-mono">STAFF_PREVIEW_SESSION</span>
              </div>

              {/* Message Feed */}
              <div className="flex-1 p-4 overflow-y-auto space-y-3 bg-[#F8FAFC]">
                {previewMessages.map((msg, idx) => (
                  <div
                    key={idx}
                    className={`flex ${msg.sender === "user" ? "justify-end" : "justify-start"}`}
                  >
                    <div
                      className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-[13px] leading-relaxed ${
                        msg.sender === "user"
                          ? "bg-[#1E40AF] text-white"
                          : "bg-white border border-[#E2E8F0] text-[#0F172A] shadow-xs"
                      }`}
                    >
                      {msg.text}
                    </div>
                  </div>
                ))}
              </div>

              {/* Input Bar */}
              <form onSubmit={handleSendPreviewMessage} className="p-3 bg-white border-t border-[#E2E8F0] flex gap-2">
                <input
                  type="text"
                  value={previewChatInput}
                  onChange={(e) => setPreviewChatInput(e.target.value)}
                  placeholder="Gõ thử câu hỏi như một khách hàng (ví dụ: tư vấn sạc xe VF8, lỗi rùa vàng)..."
                  className="flex-1 text-[13px] px-3.5 py-2 rounded-xl border border-[#E2E8F0] bg-[#F8FAFC] focus:outline-none focus:ring-2 focus:ring-[#1E40AF]/20"
                />
                <button
                  type="submit"
                  className="px-4 py-2 bg-[#1E40AF] hover:bg-[#1D4ED8] text-white text-[12px] font-semibold rounded-xl transition"
                >
                  Gửi thử
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
              <h1 className="text-xl font-semibold text-[#0F172A]">Hồ Sơ Kỹ Thuật Viên (Staff Profile)</h1>
              <p className="text-xs text-[#64748B] mt-0.5">Thông tin ca trực và phân quyền tiếp nhận sự cố.</p>
            </div>

            <div className="bg-white border border-[#E2E8F0] rounded-3xl p-6 shadow-xs space-y-5">
              <div className="flex items-center gap-4">
                <div className="w-14 h-14 rounded-2xl bg-[#1E40AF] text-white flex items-center justify-center text-xl font-bold">
                  {user?.name?.charAt(0) || "Q"}
                </div>
                <div>
                  <h2 className="text-base font-bold text-[#0F172A]">{user?.name || "Lê Hoàng Quân"}</h2>
                  <div className="text-[12px] text-[#1E40AF] font-semibold">Cố vấn Dịch vụ / Kỹ thuật viên Bậc 4</div>
                  <div className="text-[11px] text-[#64748B] font-mono mt-0.5">Mã nhân viên: STAFF-VF-0891</div>
                </div>
              </div>

              <div className="space-y-3 pt-3 border-t border-[#F1F5F9] text-[13px]">
                <div className="flex justify-between py-1">
                  <span className="text-[#64748B]">Xưởng làm việc:</span>
                  <span className="font-semibold text-[#0F172A]">VinFast Times City (Hà Nội)</span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-[#64748B]">Ca trực hôm nay:</span>
                  <span className="font-semibold text-[#0F172A]">Ca sáng (08:00 - 17:00)</span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-[#64748B]">Quyền hạn HITL:</span>
                  <span className="px-2 py-0.5 rounded-full bg-[#ECFDF5] text-[#059669] text-[11px] font-bold">
                    Duyệt Brief / Reroute / Resolve
                  </span>
                </div>
              </div>

              <div className="pt-4 border-t border-[#E2E8F0] flex justify-end">
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
  );
}
