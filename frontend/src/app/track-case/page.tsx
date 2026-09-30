"use client";

import { useState } from "react";
import Link from "next/link";
import {
  Search,
  CheckCircle2,
  Clock,
  Car,
  ShieldCheck,
  ArrowRight,
  PhoneCall,
  Sparkles,
  FileText,
  Loader2,
  RotateCcw,
  Star,
  Check,
} from "lucide-react";
import {
  getCaseStatus,
  getCustomerCases,
  reopenCustomerCase,
  submitCustomerFeedback,
} from "@/features/chat/api/chatApi";
import { CustomerCaseItem } from "@/features/chat/types";

interface TrackedCase {
  id: string;
  vehicleModel: string;
  vehicleCode: string;
  status: "Staff Reviewing" | "Needs Information" | "In Progress" | "Resolved" | "Closed" | "Reopened";
  priority: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  createdAt: string;
  issueSummary: string;
  suggestedAction: string;
  reviewerNotes?: string;
}

const SAMPLE_CASES: Record<string, TrackedCase> = {
  "VF-SF-8921": {
    id: "VF-SF-8921",
    vehicleModel: "VinFast VF8",
    vehicleCode: "VF8-PLUS-2023",
    status: "Staff Reviewing",
    priority: "HIGH",
    createdAt: "30/09/2026 16:40",
    issueSummary: "Trụ sạc nhanh DC VinFast tại Vincom cắm súng vào xe nhưng đèn trụ báo đỏ, xe không nhận điện.",
    suggestedAction: "Kiểm tra chốt khóa súng sạc cơ khí, hướng dẫn khách mở khóa khẩn cấp bằng dây giật cốp sau hoặc điều kỹ thuật viên trạm sạc kiểm tra trụ.",
    reviewerNotes: "Chuyên viên Lê Hoàng Quân đang xác minh tín hiệu trụ DC với đội vận hành trạm.",
  },
  "VF-SF-3412": {
    id: "VF-SF-3412",
    vehicleModel: "VinFast VF5",
    vehicleCode: "VF5-PLUS-2024",
    status: "Needs Information",
    priority: "MEDIUM",
    createdAt: "30/09/2026 15:15",
    issueSummary: "Xe hiện biểu tượng con rùa màu vàng trên màn hình táp-lô, xe bị giới hạn công suất.",
    suggestedAction: "Yêu cầu khách kiểm tra mức dung lượng pin SoC hiện tại và nhiệt độ môi trường ngoài trời.",
    reviewerNotes: "Đã gửi yêu cầu: Khách vui lòng gửi thêm ảnh chụp % pin hiện tại trên màn hình.",
  },
  "VF-SF-1109": {
    id: "VF-SF-1109",
    vehicleModel: "VinFast VF9",
    vehicleCode: "VF9-ECO-2023",
    status: "In Progress",
    priority: "CRITICAL",
    createdAt: "30/09/2026 14:00",
    issueSummary: "Báo động nhiệt độ pin cao trên cao tốc khi đang di chuyển với tốc độ 90km/h.",
    suggestedAction: "Hướng dẫn khách tấp xe vào làn khẩn cấp, bật đèn hazard, rời khỏi xe sau hộ lan và điều xe cứu hộ cao tốc ngay lập tức.",
    reviewerNotes: "Đội cứu hộ lưu động VinFast Expressway Team đang trên đường tới vị trí km45.",
  },
  "VF-SF-5541": {
    id: "VF-SF-5541",
    vehicleModel: "VinFast VF e34",
    vehicleCode: "VFe34-2022",
    status: "Resolved",
    priority: "MEDIUM",
    createdAt: "29/09/2026 10:20",
    issueSummary: "Đặt hẹn bảo dưỡng định kỳ cấp 12.000km và kiểm tra phần mềm FRS.",
    suggestedAction: "Đặt lịch thành công tại Xưởng dịch vụ VinFast Times City 09:00 ngày mai.",
    reviewerNotes: "Đã xác nhận tiếp nhận xe, hoàn tất thủ tục check-in trước.",
  },
};

export default function TrackCasePage() {
  const [searchId, setSearchId] = useState("CASE-20260924-001");
  const [currentCase, setCurrentCase] = useState<TrackedCase | null>(SAMPLE_CASES["VF-SF-8921"]);
  const [searched, setSearched] = useState(true);
  const [loading, setLoading] = useState(false);

  const [userCases, setUserCases] = useState<CustomerCaseItem[]>([]);
  const [feedbackRating, setFeedbackRating] = useState<number>(5);
  const [feedbackComment, setFeedbackComment] = useState<string>("");
  const [feedbackSubmitted, setFeedbackSubmitted] = useState<boolean>(false);
  const [isSubmittingFeedback, setIsSubmittingFeedback] = useState<boolean>(false);
  const [reopenLoading, setReopenLoading] = useState<boolean>(false);
  const [actionNotice, setActionNotice] = useState<string | null>(null);

  // Load danh sách hồ sơ của user từ backend
  useState(() => {
    if (typeof window !== "undefined") {
      getCustomerCases()
        .then((res) => {
          if (res?.success && res.data?.cases) {
            setUserCases(res.data.cases);
          }
        })
        .catch(() => {});
    }
  });

  const handleSearch = async (e?: React.FormEvent, customId?: string) => {
    if (e) e.preventDefault();
    const clean = (customId || searchId).trim().toUpperCase();
    if (!clean) return;

    setLoading(true);
    setActionNotice(null);
    setFeedbackSubmitted(false);

    try {
      const res = await getCaseStatus(clean);
      if (res && res.success && res.data) {
        const d = res.data;
        setCurrentCase({
          id: d.case_id || clean,
          vehicleModel: d.vehicle_model ? `VinFast ${d.vehicle_model}` : "VinFast VF8",
          vehicleCode: d.vehicle_code_mock || "VF-SF-00231",
          status: (d.status as TrackedCase["status"]) || "Staff Reviewing",
          priority: (d.priority as TrackedCase["priority"]) || "HIGH",
          createdAt: d.created_at ? new Date(d.created_at).toLocaleString("vi-VN") : "Gần đây",
          issueSummary: d.summary || "Hồ sơ sự cố tiếp nhận qua hệ thống VinFast ServiceFlow AI.",
          suggestedAction: d.suggested_action || "Đang được xử lý bởi Cố vấn Dịch vụ.",
          reviewerNotes: d.reviewer_notes || "Hồ sơ đang trong quy trình xử lý theo tiêu chuẩn xưởng.",
        });
        setSearched(true);
        setLoading(false);
        return;
      }
    } catch {
      // Fallback to sample cases
    } finally {
      setLoading(false);
    }

    if (SAMPLE_CASES[clean]) {
      setCurrentCase(SAMPLE_CASES[clean]);
    } else {
      setCurrentCase({
        id: clean || "VF-SF-MOCK",
        vehicleModel: "VinFast VF8",
        vehicleCode: "VF8-DEMO",
        status: "Staff Reviewing",
        priority: "MEDIUM",
        createdAt: "Vừa xong",
        issueSummary: "Hồ sơ sự cố vừa được tạo qua AI Agent và đang chờ chuyên viên dịch vụ tiếp nhận.",
        suggestedAction: "Chuyên viên sẽ phản hồi phương án xử lý trong vòng 5-10 phút.",
        reviewerNotes: "Đang xếp hàng đợi xử lý tại Bàn điều phối.",
      });
    }
    setSearched(true);
  };

  const handleReopen = async (caseId: string) => {
    setReopenLoading(true);
    setActionNotice(null);
    try {
      const res = await reopenCustomerCase(caseId);
      if (res?.success) {
        setActionNotice("Hồ sơ đã được mở lại thành công (Trạng thái: Reopened)!");
        setCurrentCase((prev) => (prev ? { ...prev, status: "Reopened" } : null));
      }
    } catch (err: any) {
      setActionNotice("Lưu ý: " + (err?.message || "Không thể mở lại hồ sơ lúc này."));
    } finally {
      setReopenLoading(false);
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

  const getStatusStep = (status: TrackedCase["status"]) => {
    switch (status) {
      case "Staff Reviewing":
        return 1;
      case "Needs Information":
        return 2;
      case "In Progress":
        return 3;
      case "Resolved":
        return 4;
      default:
        return 1;
    }
  };

  const getStatusBadge = (status: TrackedCase["status"]) => {
    switch (status) {
      case "Staff Reviewing":
        return "bg-[#6D5BD0]/10 text-[#6D5BD0] border-[#6D5BD0]/30";
      case "Needs Information":
        return "bg-[#FFFBEB] text-[#D97706] border-[#D97706]/40";
      case "In Progress":
        return "bg-[#EFF3FC] text-[#1E40AF] border-[#1E40AF]/30";
      case "Resolved":
        return "bg-[#ECFDF5] text-[#10B981] border-[#10B981]/30";
    }
  };

  return (
    <div className="min-h-screen bg-[#F6F7F9] py-8 px-4 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-4xl">
        {/* Header */}
        <div className="text-center mb-6">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-[#0D9488]">
            SCR-03 • Theo dõi tiến trình
          </span>
          <h1 className="mt-1 text-2xl sm:text-[28px] font-bold text-[#0F172A] leading-tight">
            Tra cứu trạng thái hồ sơ sự cố
          </h1>
          <p className="mt-1.5 text-[13px] text-[#64748B] max-w-lg mx-auto leading-relaxed">
            Nhập mã hồ sơ do AI Agent cấp (dạng <span className="font-mono font-semibold text-[#0F172A]">VF-SF-xxxx</span>) để theo dõi các bước xử lý từ chuyên viên kỹ thuật VinFast.
          </p>
        </div>

        {/* Search Input Box - Card 16px, shadow rất nhẹ */}
        <div className="rounded-2xl border border-[#E2E8F0] bg-white p-4 shadow-[0_1px_2px_rgba(0,0,0,0.04)] mb-5">
          <form onSubmit={handleSearch} className="flex flex-col sm:flex-row items-center gap-2.5">
            <div className="relative flex-1 w-full">
              <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-[#64748B]">
                <Search className="h-4 w-4" />
              </div>
              <input
                type="text"
                value={searchId}
                onChange={(e) => setSearchId(e.target.value)}
                placeholder="Nhập mã hồ sơ (Ví dụ: VF-SF-8921, VF-SF-3412...)"
                className="w-full rounded-[10px] border border-[#E2E8F0] bg-[#F6F7F9] py-2 pl-9 pr-3 text-[13px] text-[#0F172A] placeholder-[#64748B] focus:border-[#1E40AF] focus:bg-white focus:outline-none font-mono font-medium uppercase"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full sm:w-auto flex items-center justify-center gap-1.5 rounded-[10px] bg-[#1E40AF] hover:bg-[#1E3A8A] px-5 py-2 text-[13px] font-semibold text-white shadow-[0_1px_2px_rgba(0,0,0,0.04)] transition shrink-0 disabled:opacity-60"
            >
              {loading ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  <span>Đang tra cứu...</span>
                </>
              ) : (
                <>
                  <span>Tra cứu</span>
                  <ArrowRight className="h-3.5 w-3.5" />
                </>
              )}
            </button>
          </form>

          {/* Quick sample chips & User Live Cases */}
          <div className="mt-3 flex flex-col gap-2 pt-2.5 border-t border-[#E2E8F0]">
            {userCases.length > 0 && (
              <div className="flex items-center gap-1.5 flex-wrap text-[12px] text-[#0F172A]">
                <span className="text-[11px] font-bold uppercase tracking-wider text-[#10B981] flex items-center gap-1">
                  <Check className="h-3 w-3" /> Hồ sơ của bạn:
                </span>
                {userCases.map((uc) => (
                  <button
                    key={uc.id}
                    type="button"
                    onClick={() => {
                      setSearchId(uc.id);
                      handleSearch(undefined, uc.id);
                    }}
                    className="rounded-full bg-[#ECFDF5] px-2.5 py-0.5 font-mono text-[11px] font-semibold text-[#065F46] hover:bg-[#D1FAE5] transition border border-[#10B981]/30"
                  >
                    {uc.id} ({uc.status})
                  </button>
                ))}
              </div>
            )}

            <div className="flex items-center gap-1.5 flex-wrap text-[12px] text-[#64748B]">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-[#64748B]">Mẫu thử demo:</span>
              {Object.keys(SAMPLE_CASES).map((k) => (
                <button
                  key={k}
                  type="button"
                  onClick={() => {
                    setSearchId(k);
                    setCurrentCase(SAMPLE_CASES[k]);
                    setSearched(true);
                  }}
                  className="rounded-full bg-[#F6F7F9] px-2.5 py-0.5 font-mono text-[11px] font-medium text-[#1E40AF] hover:bg-[#EFF3FC] transition border border-[#E2E8F0]"
                >
                  {k} ({SAMPLE_CASES[k].status})
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Action Notice Alert */}
        {actionNotice && (
          <div className="mb-4 rounded-xl border border-[#10B981]/30 bg-[#ECFDF5] p-3 text-[13px] font-medium text-[#065F46] flex items-center justify-between shadow-sm">
            <span>{actionNotice}</span>
            <button
              type="button"
              onClick={() => setActionNotice(null)}
              className="text-[#065F46] hover:text-[#047857] text-[12px] font-bold ml-2"
            >
              ✕
            </button>
          </div>
        )}

        {/* Case Details Card - Card 16px, shadow rất nhẹ */}
        {searched && currentCase && (
          <div className="space-y-4">
            {/* Status Progress Stepper */}
            <div className="rounded-2xl border border-[#E2E8F0] bg-white p-5 shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-5 border-b border-[#E2E8F0]">
                <div>
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-mono text-[18px] font-bold text-[#0F172A]">
                      {currentCase.id}
                    </span>
                    <span className={`rounded-full px-2.5 py-0.5 text-[11px] font-semibold border ${getStatusBadge(currentCase.status)}`}>
                      {currentCase.status}
                    </span>
                    <span className="rounded-full bg-[#F6F7F9] px-2 py-0.5 text-[11px] font-medium text-[#64748B] border border-[#E2E8F0]">
                      Ưu tiên: {currentCase.priority}
                    </span>
                  </div>
                  <div className="mt-1.5 flex items-center gap-3 text-[12px] text-[#64748B]">
                    <span className="flex items-center gap-1 font-medium text-[#0F172A]">
                      <Car className="h-3.5 w-3.5 text-[#1E40AF]" />
                      {currentCase.vehicleModel} ({currentCase.vehicleCode})
                    </span>
                    <span>•</span>
                    <span className="flex items-center gap-1">
                      <Clock className="h-3.5 w-3.5" /> {currentCase.createdAt}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {(currentCase.status === "Resolved" || currentCase.status === "Closed") && (
                    <button
                      type="button"
                      disabled={reopenLoading}
                      onClick={() => handleReopen(currentCase.id)}
                      className="inline-flex items-center gap-1.5 rounded-[10px] border border-[#D97706]/40 bg-[#FFFBEB] px-3 py-1.5 text-[12px] font-semibold text-[#D97706] hover:bg-[#FEF3C7] transition"
                    >
                      <RotateCcw className="h-3.5 w-3.5" />
                      <span>{reopenLoading ? "Đang mở lại..." : "Yêu cầu mở lại"}</span>
                    </button>
                  )}

                  <Link
                    href="/chat"
                    className="inline-flex items-center gap-1.5 rounded-[10px] border border-[#E2E8F0] bg-[#F6F7F9] px-3 py-1.5 text-[12px] font-medium text-[#0D9488] hover:border-[#0D9488] hover:bg-white transition"
                  >
                    <FileText className="h-3.5 w-3.5" />
                    <span>Mở chat về case này</span>
                  </Link>
                </div>
              </div>

              {/* 4 Step Progress Bar */}
              <div className="mt-5">
                <div className="grid grid-cols-4 gap-2 text-center">
                  {[
                    { step: 1, title: "Tiếp nhận hồ sơ", desc: "Tạo Case Brief" },
                    { step: 2, title: "Làm rõ bối cảnh", desc: "Hỏi thêm dữ kiện" },
                    { step: 3, title: "Xử lý & Điều phối", desc: "Kỹ thuật xem xét" },
                    { step: 4, title: "Giải quyết xong", desc: "Xác nhận kết quả" },
                  ].map((s) => {
                    const activeStep = getStatusStep(currentCase.status);
                    const isPassed = activeStep >= s.step;
                    const isCurrent = activeStep === s.step;
                    return (
                      <div key={s.step} className="flex flex-col items-center">
                        <div
                          className={`flex h-7 w-7 items-center justify-center rounded-full text-[11px] font-bold transition ${
                            isPassed
                              ? "bg-[#10B981] text-white"
                              : "bg-[#E2E8F0] text-[#64748B]"
                          } ${isCurrent ? "ring-2 ring-[#10B981]/30" : ""}`}
                        >
                          {isPassed ? <CheckCircle2 className="h-3.5 w-3.5" /> : s.step}
                        </div>
                        <span className={`mt-1.5 font-semibold text-[11px] ${isPassed ? "text-[#0F172A]" : "text-[#64748B]"}`}>
                          {s.title}
                        </span>
                        <span className="hidden sm:inline text-[10px] text-[#64748B]">
                          {s.desc}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* Technical Brief & Action Plan */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Left: Tóm tắt sự cố */}
              <div className="rounded-2xl border border-[#E2E8F0] bg-white p-4 shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
                <h3 className="text-[11px] font-semibold uppercase tracking-wider text-[#64748B] flex items-center gap-1.5 mb-2">
                  <FileText className="h-3.5 w-3.5 text-[#1E40AF]" />
                  Dấu hiệu ghi nhận từ khách hàng
                </h3>
                <p className="text-[13px] leading-relaxed text-[#0F172A] bg-[#F6F7F9] p-3 rounded-xl border border-[#E2E8F0]">
                  {currentCase.issueSummary}
                </p>

                <div className="mt-3 flex items-center gap-1.5 text-[11px] text-[#64748B]">
                  <ShieldCheck className="h-3.5 w-3.5 text-[#10B981] shrink-0" />
                  <span>Dữ liệu đã được bóc tách và mã hóa No-PII an toàn.</span>
                </div>
              </div>

              {/* Right: Ghi chú của chuyên viên */}
              <div className="rounded-2xl border border-[#E2E8F0] bg-white p-4 shadow-[0_1px_2px_rgba(0,0,0,0.04)] flex flex-col justify-between">
                <div>
                  <h3 className="text-[11px] font-semibold uppercase tracking-wider text-[#64748B] flex items-center gap-1.5 mb-2">
                    <Sparkles className="h-3.5 w-3.5 text-[#0D9488]" />
                    Phương án từ Kỹ thuật viên
                  </h3>
                  <div className="text-[13px] leading-relaxed text-[#0F172A] bg-[#EFF3FC] p-3 rounded-xl border border-[#1E40AF]/20">
                    <strong className="block font-semibold text-[#1E40AF] mb-0.5">Khuyến nghị xử lý:</strong>
                    {currentCase.suggestedAction}
                  </div>

                  {currentCase.reviewerNotes && (
                    <div className="mt-2.5 p-2.5 rounded-xl bg-[#F0FDFA] border border-[#0D9488]/30 text-[12px] text-[#0F172A]">
                      <strong className="block font-semibold text-[#0D9488] mb-0.5">Ghi chú Staff:</strong>
                      {currentCase.reviewerNotes}
                    </div>
                  )}
                </div>

                <div className="mt-3 pt-2.5 border-t border-[#E2E8F0] flex items-center justify-between text-[12px]">
                  <span className="text-[#64748B]">Cần cứu hộ gấp?</span>
                  <a
                    href="tel:1900232389"
                    className="inline-flex items-center gap-1 font-semibold text-[#DC2626] hover:underline"
                  >
                    <PhoneCall className="h-3 w-3" /> Gọi 1900-232389
                  </a>
                </div>
              </div>
            </div>

            {/* Feedback Section (hiển thị khi hồ sơ đã giải quyết hoặc đóng) */}
            {(currentCase.status === "Resolved" || currentCase.status === "Closed") && (
              <div className="rounded-2xl border border-[#10B981]/30 bg-white p-5 shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
                <h3 className="text-[14px] font-bold text-[#0F172A] flex items-center gap-2">
                  <Star className="h-4 w-4 text-[#F59E0B] fill-[#F59E0B]" />
                  Đánh giá chất lượng hỗ trợ
                </h3>
                <p className="mt-1 text-[12px] text-[#64748B]">
                  Ý kiến của anh/chị giúp VinFast ServiceFlow AI và đội ngũ kỹ thuật nâng cao chất lượng phục vụ.
                </p>

                {feedbackSubmitted ? (
                  <div className="mt-3 rounded-xl bg-[#ECFDF5] p-3 text-[13px] font-semibold text-[#065F46] flex items-center gap-2">
                    <Check className="h-4 w-4 text-[#10B981]" />
                    Đã ghi nhận đánh giá của bạn. Trân trọng cảm ơn!
                  </div>
                ) : (
                  <div className="mt-3 space-y-3">
                    <div className="flex items-center gap-1">
                      {[1, 2, 3, 4, 5].map((star) => (
                        <button
                          key={star}
                          type="button"
                          onClick={() => setFeedbackRating(star)}
                          className="p-1 text-[#F59E0B] hover:scale-110 transition"
                        >
                          <Star
                            className={`h-6 w-6 ${
                              star <= feedbackRating ? "fill-[#F59E0B]" : "text-[#E2E8F0]"
                            }`}
                          />
                        </button>
                      ))}
                      <span className="ml-2 text-[12px] font-bold text-[#0F172A]">
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
                      placeholder="Nhận xét bổ sung về tốc độ và chất lượng hỗ trợ (tùy chọn)..."
                      rows={2}
                      className="w-full rounded-xl border border-[#E2E8F0] p-2.5 text-[12px] text-[#0F172A] focus:border-[#1E40AF] focus:outline-none"
                    />

                    <button
                      type="button"
                      disabled={isSubmittingFeedback}
                      onClick={() => handleSubmitFeedback(currentCase.id)}
                      className="rounded-[10px] bg-[#10B981] hover:bg-[#059669] px-4 py-1.5 text-[12px] font-bold text-white transition disabled:opacity-60"
                    >
                      {isSubmittingFeedback ? "Đang gửi..." : "Gửi đánh giá"}
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
