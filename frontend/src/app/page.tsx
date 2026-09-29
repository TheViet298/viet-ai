import Link from "next/link";
import {
  MessageSquare,
  ShieldCheck,
  Zap,
  CheckCircle2,
  Clock,
  Car,
  FileText,
  AlertTriangle,
} from "lucide-react";

export default function Home() {
  return (
    <div className="max-w-6xl mx-auto px-4 py-10 sm:px-6 lg:px-8">
      {/* Hero Section */}
      <div className="text-center space-y-4 max-w-3xl mx-auto">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-50 border border-blue-200 text-blue-700 text-xs font-medium">
          <Zap className="w-3.5 h-3.5" /> Hệ Thống AI Agent Tiếp Nhận Đa Kênh Cho Xe Điện VinFast
        </div>
        <h1 className="text-4xl font-extrabold tracking-tight text-slate-900 sm:text-5xl">
          VinFast <span className="text-blue-700">ServiceFlow AI</span>
        </h1>
        <p className="text-base sm:text-lg text-slate-600">
          Tự động phân loại 4 nhóm Intent, làm rõ dữ kiện kỹ thuật (không PII),
          tra cứu nguồn chính thức có trích dẫn và tổng hợp Case Brief chuẩn hóa cho nhân viên dịch vụ.
        </p>
      </div>

      {/* Main Entry Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-12">
        {/* Card 1: Customer Chat */}
        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm hover:shadow-md transition-all flex flex-col justify-between">
          <div className="space-y-4">
            <div className="w-12 h-12 rounded-xl bg-blue-100 text-blue-700 flex items-center justify-center font-bold">
              <MessageSquare className="w-6 h-6" />
            </div>
            <div>
              <span className="text-xs font-semibold uppercase tracking-wider text-blue-600">
                Giao Diện Khách Hàng (SCR-01 & SCR-02)
              </span>
              <h2 className="text-xl font-bold text-slate-900 mt-1">
                Trợ Lý Trực Tuyến & Báo Sự Cố
              </h2>
            </div>
            <p className="text-sm text-slate-600 leading-relaxed">
              Dành cho chủ xe VinFast (VF3, VF5, VF8, v.v.): Gửi câu hỏi về sạc pin, bảo dưỡng,
              nhận phản hồi FAQ có dẫn nguồn chính thức hoặc tự động làm rõ dữ kiện khi gặp sự cố.
            </p>
            <ul className="text-xs text-slate-600 space-y-2 pt-2">
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                Làm rõ tối đa 2 lượt khi thiếu thông tin (Mã lỗi, Trụ sạc)
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                Trích dẫn link nguồn công khai từ vinfastauto.com
              </li>
              <li className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-rose-500 shrink-0" />
                Banner cảnh báo khẩn cấp cho tình huống nguy hiểm
              </li>
            </ul>
          </div>

          <div className="pt-6 mt-4 border-t border-slate-100">
            <Link
              href="/chat"
              className="inline-flex items-center justify-center w-full px-5 py-3 rounded-xl bg-blue-600 text-white font-medium hover:bg-blue-700 shadow-md shadow-blue-500/20 transition-all text-sm gap-2"
            >
              <MessageSquare className="w-4 h-4" /> Mở Giao Diện Khách Hàng
            </Link>
          </div>
        </div>

        {/* Card 2: Staff Console */}
        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm hover:shadow-md transition-all flex flex-col justify-between">
          <div className="space-y-4">
            <div className="w-12 h-12 rounded-xl bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <div>
              <span className="text-xs font-semibold uppercase tracking-wider text-emerald-600">
                Giao Diện Nhân Viên (SCR-04 HITL)
              </span>
              <h2 className="text-xl font-bold text-slate-900 mt-1">
                Bàn Điều Phối & Phê Duyệt Ticket
              </h2>
            </div>
            <p className="text-sm text-slate-600 leading-relaxed">
              Dành cho Cố vấn Dịch vụ / Reviewer: Xem danh sách Ticket Queue theo độ ưu tiên,
              kiểm tra Case Brief do AI tổng hợp, chỉnh sửa và bấm Duyệt/Chuyển tiếp (HITL).
            </p>
            <ul className="text-xs text-slate-600 space-y-2 pt-2">
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                Hàng đợi phân tầng theo Priority: Critical $\to$ High $\to$ Medium
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                Case Brief chuẩn hóa: Tóm tắt, captured fields, suggested action
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                Quyền Human-in-the-Loop: Approve, Edit Brief, Reroute, Close
              </li>
            </ul>
          </div>

          <div className="pt-6 mt-4 border-t border-slate-100">
            <Link
              href="/console"
              className="inline-flex items-center justify-center w-full px-5 py-3 rounded-xl bg-slate-900 text-white font-medium hover:bg-slate-800 shadow-md shadow-slate-900/20 transition-all text-sm gap-2"
            >
              <ShieldCheck className="w-4 h-4" /> Mở Bàn Điều Phối (Console)
            </Link>
          </div>
        </div>
      </div>

      {/* Feature Highlights Banner */}
      <div className="mt-12 bg-blue-900 text-white rounded-2xl p-6 sm:p-8 shadow-lg">
        <h3 className="text-lg font-bold">Quy chuẩn Bảo mật & Thiết kế MVP:</h3>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 mt-4 text-xs sm:text-sm text-blue-100">
          <div className="flex items-start gap-3">
            <Car className="w-5 h-5 text-blue-300 shrink-0 mt-0.5" />
            <div>
              <strong className="text-white block">Tuân thủ No-PII</strong>
              Sử dụng profile giả lập (`CUST_MOCK_xx`, `VF-SF-xxxxx`), không lưu CCCD hay SĐT thật.
            </div>
          </div>
          <div className="flex items-start gap-3">
            <FileText className="w-5 h-5 text-blue-300 shrink-0 mt-0.5" />
            <div>
              <strong className="text-white block">Trích dẫn Nguồn kiểm chứng</strong>
              Mọi câu trả lời FAQ đều có link xác thực `SRC-APP-001`, ngăn chặn triệt để ảo giác (Hallucination).
            </div>
          </div>
          <div className="flex items-start gap-3">
            <Clock className="w-5 h-5 text-blue-300 shrink-0 mt-0.5" />
            <div>
              <strong className="text-white block">State Machine Thống nhất</strong>
              Chuẩn hóa vòng đời ticket: New $\to$ Needs Info $\to$ Staff Reviewing $\to$ In Progress $\to$ Resolved.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
