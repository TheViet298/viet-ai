"use client";

import { useState, useEffect, useRef } from "react";
import {
  ShieldCheck,
  Sparkles,
  Edit3,
  Check,
  X,
  Send,
  CheckCircle2,
  AlertCircle,
  AlertTriangle,
  Bot,
  User,
  Loader2,
  GitBranch,
  ChevronRight,
  MessageSquare,
} from "lucide-react";
import {
  TicketItem,
  TicketStatus,
  StaffActionType,
  TicketDetail,
  VIETNAMESE_STATUS_MAP,
} from "../types";
import { ROUTING_DEPARTMENTS } from "./StaffConsoleShell";
import { getTicketDetail, submitStaffAction } from "../api/consoleApi";
import { useAuth } from "@/features/shared";
import { useLocale } from "@/features/shared/context/LocaleContext";
import { toCustomerWarningText } from "@/features/shared/utils/customerWarningText";

interface TicketDetailPanelProps {
  ticket: TicketItem;
  onActionComplete?: (message: string) => void;
  onStatusUpdate?: (ticketId: string, newStatus: TicketStatus) => void;
}

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
  const { t, language } = useLocale();
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

  const [ticketDetail, setTicketDetail] = useState<TicketDetail | null>(null);
  const [detailError, setDetailError] = useState(false);
  const [actionError, setActionError] = useState<'failed' | 'refresh' | null>(null);
  const [reloadCount, setReloadCount] = useState(0);

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

  const aiRationale = t('Đề xuất theo mức ưu tiên và nhóm yêu cầu của hồ sơ; cần kiểm tra dữ kiện trước khi điều phối.');

  // Ref cuộn panel chi tiết về đỉnh khi đổi case
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const requestVersion = useRef(0);

  // When ticket prop changes, sync detail & default selected dept
  useEffect(() => {
    requestVersion.current += 1;
    scrollContainerRef.current?.scrollTo({ top: 0, behavior: "smooth" });

    let isMounted = true;
    setTicketDetail(null);
    setDetailError(false);
    setActionError(null);
    setIsSubmitting(false);
    const fetchLiveDetail = async () => {
      try {
        const res = await getTicketDetail(ticket.id);
        if (!res?.success || !res.data || res.data.case.id !== ticket.id) throw new Error('Invalid case detail');
        if (isMounted) {
          setTicketDetail(res.data);
          setEditedSummary(res.data.case_brief?.summary || '');
        }
      } catch {
        if (isMounted) setDetailError(true);
      }
    };

    fetchLiveDetail();
    setIsEditingBrief(false);
    setSelectedDept(recommendedDept.name);
    setExpandedOtherDeptId(null);

    return () => {
      isMounted = false;
      requestVersion.current += 1;
    };
  }, [ticket.id, ticket, recommendedDept.name, reloadCount]);

  if (!ticketDetail || ticketDetail.case.id !== ticket.id) {
    return <div className="rounded-2xl bg-white p-5" role={detailError ? 'alert' : 'status'}>
      <p>{t(detailError ? 'Không thể tải chi tiết hồ sơ. Vui lòng thử lại.' : 'Đang tải chi tiết hồ sơ...')}</p>
      {detailError && <button type="button" onClick={() => setReloadCount(value => value + 1)}>{t('Thử lại')}</button>}
    </div>;
  }

  const handleCopyId = () => {
    navigator.clipboard.writeText(ticket.id);
    setCopiedId(true);
    setTimeout(() => setCopiedId(false), 2000);
  };

  const handleSaveBrief = async () => {
    await executeStaffAction(t('Lưu tóm tắt hồ sơ'), 'EDIT_BRIEF', ticketDetail.case.status, editedSummary);
  };

  const handleCancelBrief = () => {
    setEditedSummary(ticketDetail.case_brief.summary);
    setIsEditingBrief(false);
  };

  const executeStaffAction = async (
    actionName: string,
    actionType: StaffActionType,
    targetStatus: TicketStatus,
    summary?: string
  ) => {
    setIsSubmitting(true);
    setActionError(null);
    let saved = false;
    const version = requestVersion.current;
    try {
      const receipt = await submitStaffAction(ticket.id, {
        action: actionType,
        staff_id: user?.name || user?.email || "Cố vấn Dịch vụ VinFast",
        updated_status: targetStatus,
        notes: notes || undefined,
        ...(summary !== undefined ? {edited_brief: {summary}} : {}),
      });
      if (version !== requestVersion.current) return;
      if (!receipt?.success || receipt.data?.success !== true || receipt.data.case_id !== ticket.id) {
        throw new Error('Action not confirmed');
      }
      saved = true;
      if (summary !== undefined) {
        setTicketDetail(prev => prev ? {...prev, case_brief: {...prev.case_brief, summary, is_edited_by_staff: true}} : prev);
        setIsEditingBrief(false);
      } else {
        setTicketDetail(prev => prev ? {...prev, case: {...prev.case, status: targetStatus}} : prev);
        onStatusUpdate?.(ticket.id, targetStatus);
      }
      onActionComplete?.(t('Đã thực hiện: {action} cho hồ sơ {id}!').replace('{action}', actionName).replace('{id}', ticket.id));
      const refreshed = await getTicketDetail(ticket.id);
      if (version !== requestVersion.current) return;
      if (!refreshed?.success || !refreshed.data || refreshed.data.case.id !== ticket.id) throw new Error('Invalid case detail');
      setTicketDetail(refreshed.data);
    } catch {
      if (version === requestVersion.current) setActionError(saved ? 'refresh' : 'failed');
    } finally {
      if (version === requestVersion.current) setIsSubmitting(false);
    }
  };

  const isCritical = ticket.priority === "CRITICAL";
  const otherDepts = ROUTING_DEPARTMENTS.filter((d) => d.id !== recommendedDept.id);

  // Structured key-value parameter rows với bóc tách chuẩn xác từ captured_fields
  const captured = ticketDetail.case_brief.captured_fields || {};

  // 1. Dòng xe
  const resolvedModel = String(captured.vehicle_model || ticket.vehicle_model || "VF8");

  // 2. Vị trí
  const resolvedLocation = String(
    ticketDetail.location?.location_label ||
    captured.station_location ||
    captured.location_label ||
    (ticketDetail.location?.latitude
      ? `${ticketDetail.location.latitude.toFixed(4)}° N, ${ticketDetail.location.longitude?.toFixed(4)}° E`
      : t("Đang xác minh tọa độ"));

  // 3. Pin (SoC): Đọc đa dạng key soc, current_soc, battery_percentage
  const rawSoc = captured.current_soc ?? captured.soc ?? captured.battery_percentage;
  let resolvedSoc = t("Chưa rõ");
  if (rawSoc !== undefined && rawSoc !== null && rawSoc !== "") {
    resolvedSoc = String(rawSoc).trim();
    if (/^\d+$/.test(resolvedSoc)) {
      resolvedSoc = `${resolvedSoc}%`;
    }
  }

  // 4. Mã lỗi / Cảnh báo: Đọc error_code, warning_symbol, visual_signals
  const rawWarning =
    toCustomerWarningText(captured) ||
    captured.error_code ||
    ticket.error_code_short;
  let resolvedWarning = t("Chưa ghi nhận mã lỗi");
  let isWarningAlert = false;

  if (rawWarning) {
    const warnStr = String(rawWarning);
    if (/rùa|turtle/i.test(warnStr)) {
      resolvedWarning = t("Rùa vàng (giảm công suất)");
      isWarningAlert = true;
    } else {
      resolvedWarning = t(warnStr);
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
      label: t("Dòng xe"),
      value: resolvedModel,
      isWarning: false,
      isAlert: false,
    },
    {
      label: t("Vị trí"),
      value: resolvedLocation,
      isWarning: resolvedLocation === t('Đang xác minh tọa độ') || resolvedLocation.includes('Đang xác minh') || resolvedLocation.includes('Chưa'),
      isAlert: false,
    },
    {
      label: t("Dung lượng pin (SoC)"),
      value: resolvedSoc,
      isWarning: resolvedSoc === t('Chưa rõ') || resolvedSoc.includes("< 10%"),
      isAlert: false,
    },
    {
      label: t("Cảnh báo / Mã lỗi"),
      value: resolvedWarning,
      isWarning: resolvedWarning === t('Chưa ghi nhận mã lỗi') || resolvedWarning.includes('Chưa'),
      isAlert: isWarningAlert,
    },
    {
      label: t("Chia sẻ vị trí GPS"),
      value: isGpsShared ? t("Đã bật chia sẻ GPS") : t("Chưa bật chia sẻ vị trí"),
      isWarning: !isGpsShared,
      isAlert: false,
    },
  ];

  if (captured.charger_id) {
    parameterRows.push({
      label: t("Trụ sạc / Cổng kết nối"),
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
      : t('Hồ sơ sự cố xe {model}').replace('{model}', ticket.vehicle_model)
  );

  // Formatted Safety Time
  let formattedSafetyTime = "";
  if (safetyAckTime) {
    try {
      formattedSafetyTime = new Date(safetyAckTime).toLocaleTimeString(language === 'en' ? 'en-GB' : 'vi-VN', {
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
      {actionError && <div role="alert" className="border-b border-red-200 bg-red-50 p-3 text-sm text-red-800">
        <p>{t(actionError === 'refresh' ? 'Thao tác đã lưu nhưng chưa tải được cập nhật hồ sơ. Vui lòng tải lại.' : 'Không thể lưu thao tác. Trạng thái chưa được thay đổi. Vui lòng thử lại.')}</p>
        {actionError === 'refresh' && <button type="button" onClick={() => setReloadCount(value => value + 1)}>{t('Thử lại')}</button>}
      </div>}
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
                title={t("Sao chép toàn bộ mã hồ sơ")}
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
                  {t("Cần xác minh")}
                </span>
              )}
              <span>·</span>
              <span>
                {t("Khách:")}{" "}
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
                  {t(VIETNAMESE_STATUS_MAP[ticket.status] || ticket.status)}
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
                      t("Duyệt phương án & chuyển xưởng"),
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
                  <span>{t("Duyệt & Điều phối")}</span>
                </button>

                {/* NÚT PHỤ 1: Cần thêm tin */}
                <button
                  type="button"
                  disabled={isSubmitting}
                  onClick={() =>
                    executeStaffAction(
                      t("Yêu cầu thêm thông tin"),
                      "REQUEST_INFO",
                      "Needs Information"
                    )
                  }
                  className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-xl border border-slate-200 bg-white hover:bg-amber-50 hover:text-amber-700 text-slate-700 text-[12px] font-medium transition active:scale-[0.98] disabled:opacity-50"
                  title={t("Yêu cầu khách hàng bổ sung thêm dữ kiện")}
                >
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
                  <span className="hidden sm:inline">{t("Cần thêm tin")}</span>
                </button>

                {/* NÚT PHỤ 2: Sửa brief */}
                <button
                  type="button"
                  onClick={() => setIsEditingBrief(true)}
                  className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-[12px] font-medium transition active:scale-[0.98]"
                  title={t("Chỉnh sửa tóm tắt Case Brief")}
                >
                  <Edit3 className="w-3.5 h-3.5 text-slate-500" />
                  <span className="hidden sm:inline">{t("Sửa brief")}</span>
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
                      t("Gửi tin nhắn nhắc khách bổ sung thông tin"),
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
                  <span>{t("Nhắc khách")}</span>
                </button>

                {/* NÚT PHỤ: Duyệt khi đã đủ */}
                <button
                  type="button"
                  disabled={isSubmitting}
                  onClick={() =>
                    executeStaffAction(
                      t("Thông tin đã đủ - Duyệt điều phối"),
                      "APPROVE",
                      "In Progress"
                    )
                  }
                  className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-xl border border-slate-200 bg-white hover:bg-blue-50 hover:text-[#1E40AF] text-slate-700 text-[12px] font-medium transition active:scale-[0.98] disabled:opacity-50"
                  title={t("Duyệt ca khi khách đã cung cấp đủ dữ liệu")}
                >
                  <CheckCircle2 className="w-3.5 h-3.5 text-[#1E40AF]" />
                  <span className="hidden sm:inline">{t("Duyệt khi đã đủ")}</span>
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
                      t("Hoàn tất giải quyết (Resolved)"),
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
                  <span>{t("Giải quyết")}</span>
                </button>

                {/* NÚT PHỤ: Điều phối lại */}
                <button
                  type="button"
                  onClick={() => setDetailTab("dispatch")}
                  className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-[12px] font-medium transition active:scale-[0.98]"
                  title={t("Chuyển sang tab điều phối xưởng")}
                >
                  <GitBranch className="w-3.5 h-3.5 text-slate-500" />
                  <span className="hidden sm:inline">{t("Điều phối lại")}</span>
                </button>
              </>
            )}

            {/* TRƯỜNG HỢP 4: Đã giải quyết (Resolved) */}
            {ticket.status === "Resolved" && (
              <>
                <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-700 text-[12px] font-semibold">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>{t("Đã giải quyết")}</span>
                </div>
                <button
                  type="button"
                  disabled={isSubmitting}
                  onClick={() =>
                    executeStaffAction(t("Đóng hồ sơ (Closed)"), "CLOSE", "Closed")
                  }
                  className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-xl border border-slate-200 bg-white hover:bg-slate-100 text-slate-700 text-[12px] font-medium transition active:scale-[0.98] disabled:opacity-50"
                  title={t("Đóng lưu trữ hồ sơ")}
                >
                  <X className="w-3.5 h-3.5 text-slate-500" />
                  <span className="hidden sm:inline">{t("Đóng hồ sơ")}</span>
                </button>
                <button
                  type="button"
                  disabled={isSubmitting}
                  onClick={() =>
                    executeStaffAction(t("Mở lại hồ sơ (Reopened)"), "REOPEN", "Reopened")
                  }
                  className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-xl border border-slate-200 bg-white hover:bg-amber-50 hover:text-amber-700 text-slate-700 text-[12px] font-medium transition active:scale-[0.98] disabled:opacity-50"
                  title={t("Mở lại hồ sơ nếu khách cần hỗ trợ thêm")}
                >
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
                  <span className="hidden sm:inline">{t("Mở lại")}</span>
                </button>
              </>
            )}

            {/* TRƯỜNG HỢP 5: Đã đóng (Closed) */}
            {ticket.status === "Closed" && (
              <>
                <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-100 border border-slate-200 text-slate-600 text-[12px] font-semibold">
                  <Check className="w-3.5 h-3.5 text-slate-500" />
                  <span>{t("Hồ sơ đã đóng")}</span>
                </div>
                <button
                  type="button"
                  disabled={isSubmitting}
                  onClick={() =>
                    executeStaffAction(t("Mở lại hồ sơ (Reopened)"), "REOPEN", "Reopened")
                  }
                  className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-xl border border-slate-200 bg-white hover:bg-amber-50 hover:text-amber-700 text-slate-700 text-[12px] font-medium transition active:scale-[0.98] disabled:opacity-50"
                >
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
                  <span className="hidden sm:inline">{t("Mở lại hồ sơ")}</span>
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
              <strong>{t("Khách đã xác nhận an toàn")}</strong>
              {formattedSafetyTime ? t(' lúc {time}').replace('{time}', formattedSafetyTime) : ""} {t("(đã dừng đỗ an toàn, bật hazard)")}
            </span>
          </div>
        ) : isCritical ? (
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-red-50 border border-red-200 text-red-800 text-[12px] font-medium animate-pulse">
            <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
            <span>
              <strong>{t("Khách chưa xác nhận an toàn!")}</strong> {t("Cần ưu tiên gọi hotline hoặc nhắc khách kích hoạt hướng dẫn an toàn.")}
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
            <span>{t("Hồ sơ sự cố")}</span>
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
            <span>{t("Nhật ký hội thoại")}</span>
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
            <span>{t("Điều phối xưởng")}</span>
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
                    {t("Tóm tắt sự cố bởi AI")}
                  </span>
                  {ticketDetail.case_brief.is_edited_by_staff && (
                    <span className="text-[10px] text-[#059669] bg-[#ECFDF5] px-2 py-0.5 rounded-full font-medium">
                      {t("Đã hiệu chỉnh")}
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  <span className="text-[11px] text-slate-500">
                    {t("Độ tin cậy:")} <strong className="text-emerald-700 font-semibold">{Math.round((ticketDetail.case_brief.confidence_score || 0.85) * 100)}%</strong>
                  </span>

                  {!isEditingBrief && (
                    <button
                      type="button"
                      onClick={() => setIsEditingBrief(true)}
                      className="inline-flex items-center gap-1 text-[11px] font-medium text-[#1E40AF] hover:underline transition"
                    >
                      <Edit3 className="w-3 h-3" />
                      <span>{t("Sửa")}</span>
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
                    placeholder={t("Chỉnh sửa nội dung tóm tắt sự cố...")}
                  />
                  <div className="flex justify-end gap-2">
                    <button
                      type="button"
                      onClick={handleCancelBrief}
                      className="px-2.5 py-1 rounded-lg text-[12px] font-medium text-slate-600 hover:bg-slate-200"
                    >
                      {t("Hủy")}
                    </button>
                    <button
                      type="button"
                      onClick={handleSaveBrief}
                      disabled={isSubmitting}
                      className="px-3 py-1 rounded-lg bg-[#1E40AF] text-white text-[12px] font-medium hover:bg-[#1D4ED8]"
                    >
                      {t("Lưu")}
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
                  {t("Dữ kiện kỹ thuật bóc tách")}
                </span>
                <span className="text-[11px] text-slate-400">
                  {t("Trích xuất tự động từ hội thoại")}
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
                          ? "text-amber-700 font-semibold"
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
                      {t("Phương án đề xuất cho xưởng:")}
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
                              t('[Phương án đề xuất]: {proposal}').replace('{proposal}', ticketDetail.case_brief.suggested_action)
                          );
                          setDetailTab("dispatch");
                          onActionComplete?.(t("Đã sao chép phương án vào Ghi chú điều phối!"));
                        }}
                        className="text-[11.5px] font-medium text-[#1E40AF] hover:underline"
                      >
                        {t("Chèn vào ghi chú điều phối →")}
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
              <span>{t("Nhật ký trao đổi với khách hàng")}</span>
              <span>{t("Được đồng bộ tự động")}</span>
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
                            <User className="w-3.5 h-3.5" /> {t("Khách hàng")}
                          </span>
                        ) : isStaff ? (
                          <span className="text-[#7E22CE] flex items-center gap-1">
                            <ShieldCheck className="w-3.5 h-3.5" /> {t("Cố vấn dịch vụ")}
                          </span>
                        ) : (
                          <span className="text-[#059669] flex items-center gap-1">
                            <Bot className="w-3.5 h-3.5" /> AI Agent
                          </span>
                        )}
                      </span>
                      <span className="text-[10px] text-slate-400 font-mono">
                        {new Date(msg.created_at).toLocaleTimeString(language === 'en' ? 'en-GB' : 'vi-VN', {
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
                {t("Bộ phận đề xuất bởi AI")}
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
                      {t(recommendedDept.name)}
                    </span>
                    <span className="text-[10px] px-2 py-0.5 rounded-full font-semibold bg-blue-100 text-[#1E40AF]">
                      {t(recommendedDept.badge)}
                    </span>
                  </div>
                  <span className="text-[11px] text-slate-500 font-mono">
                    {t("Phụ trách:")} {recommendedDept.lead.split("(")[0].trim()}
                  </span>
                </div>

                {/* 1-line Rationale */}
                <p className="text-[12px] text-[#1E3A8A] mt-2 font-medium bg-white/70 p-2 rounded-lg border border-blue-100">
                  {t("💡 Lý do đề xuất:")} {aiRationale}
                </p>
              </div>
            </div>

            {/* Other Departments: Collapsed List */}
            <div className="space-y-1.5 pt-1">
              <span className="text-[12px] text-slate-500 font-medium block px-1">
                {t("Hoặc chọn nhóm bộ phận khác:")}
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
                            {t(dept.name)}
                          </span>
                          <span className={`text-[10px] px-2 py-0.5 rounded-full font-semibold ${dept.color}`}>
                            {t(dept.badge)}
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
                          <p>{t(dept.description)}</p>
                          <p className="text-[11px] text-slate-400 font-mono">
                            {t("Người phụ trách:")} {t(dept.lead)}
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
                {t("Ghi chú điều phối gửi xưởng (tùy chọn):")}
              </label>
              <textarea
                id="dispatch-notes-input"
                rows={2}
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder={t("VD: Chuẩn bị máy chẩn đoán CAN-bus, trạm Metropolis cử KTV kiểm tra trụ P02...")}
                className="w-full text-[13px] p-2.5 rounded-xl border border-slate-200 bg-slate-50 focus:bg-white text-slate-900 focus:outline-none focus:ring-2 focus:ring-[#1E40AF]/20"
              />
            </div>

            {/* Dispatch confirmation button */}
            <div className="pt-2 border-t border-slate-100 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
              <span className="text-[12px] text-slate-500">
                {t("Nhóm đích:")} <strong className="text-[#1E40AF]">{t(selectedDept)}</strong>
              </span>

              <button
                type="button"
                disabled={isSubmitting}
                onClick={() =>
                  executeStaffAction(
                    t('Điều phối sang {department}').replace('{department}', t(selectedDept)),
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
                <span>{t("Xác nhận chuyển nhóm tiếp nhận")}</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
