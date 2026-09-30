import Link from "next/link";
import { ScanLine, PhoneCall, ShieldCheck, FileCheck, BatteryCharging, Wrench, AlertTriangle } from "lucide-react";

export function Footer() {
  return (
    <footer className="border-t border-[#E2E8F0] bg-white text-[#64748B]">
      {/* Top Banner: Hotline */}
      <div className="border-b border-[#E2E8F0] bg-[#F6F7F9] px-4 py-2.5">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-2.5 text-[12px] sm:flex-row sm:px-6 lg:px-8">
          <div className="flex items-center gap-2 text-[#0F172A]">
            <span className="flex h-2 w-2 rounded-full bg-[#10B981] animate-pulse" />
            <span className="font-semibold text-[#0F172A]">Hotline hỗ trợ kỹ thuật & Cứu hộ khẩn cấp 24/7:</span>
            <span className="text-[#64748B]">Áp dụng cho xe điện VinFast toàn quốc</span>
          </div>
          <a
            href="tel:1900232389"
            className="inline-flex items-center gap-1.5 rounded-[10px] bg-[#DC2626] hover:bg-[#B91C1C] px-3 py-1 font-semibold text-white shadow-[0_1px_2px_rgba(0,0,0,0.04)] text-[12px] transition"
          >
            <PhoneCall className="h-3.5 w-3.5" /> 1900-232389
          </a>
        </div>
      </div>

      {/* Main Footer Links */}
      <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-5">
          {/* Brand Col */}
          <div className="lg:col-span-2">
            <Link href="/" className="inline-flex items-center gap-2 group">
              <div className="flex h-8 w-8 items-center justify-center rounded-[10px] bg-[#1E40AF] text-[#10B981] shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
                <ScanLine className="h-4 w-4 text-white" />
              </div>
              <span className="text-[16px] font-bold tracking-tight text-[#0F172A] font-display">
                ServiceFlow <span className="text-[#1E40AF]">AI</span>
              </span>
            </Link>
            <p className="mt-2.5 max-w-sm text-[13px] leading-relaxed text-[#64748B]">
              Hệ thống AI Agent tiếp nhận sự cố xe điện thông minh, phân tích tín hiệu thị giác từ táp-lô, tra cứu cẩm nang kỹ thuật chính thức và hỗ trợ điều phối nhân viên dịch vụ.
            </p>

            <div className="mt-3 flex items-center gap-1.5 text-[11px] font-medium text-[#64748B]">
              <ShieldCheck className="h-3.5 w-3.5 text-[#10B981]" />
              <span>Tuân thủ No-PII: Không lưu trữ CCCD, biển số thật hay dữ liệu cá nhân.</span>
            </div>
          </div>

          {/* Col 2: Nhóm sự cố */}
          <div>
            <h3 className="text-[11px] font-semibold uppercase tracking-wider text-[#0F172A]">
              Nhóm sự cố phổ biến
            </h3>
            <ul className="mt-2.5 space-y-1.5 text-[13px]">
              <li>
                <Link href="/chat" className="inline-flex items-center gap-1.5 hover:text-[#1E40AF] transition">
                  <BatteryCharging className="h-3.5 w-3.5 text-[#10B981]" /> Pin & Trụ sạc
                </Link>
              </li>
              <li>
                <Link href="/chat" className="inline-flex items-center gap-1.5 hover:text-[#1E40AF] transition">
                  <AlertTriangle className="h-3.5 w-3.5 text-[#D97706]" /> Đèn cảnh báo táp-lô
                </Link>
              </li>
              <li>
                <Link href="/chat" className="inline-flex items-center gap-1.5 hover:text-[#1E40AF] transition">
                  <Wrench className="h-3.5 w-3.5 text-[#0D9488]" /> Động cơ & Vận hành
                </Link>
              </li>
              <li>
                <Link href="/chat" className="inline-flex items-center gap-1.5 hover:text-[#1E40AF] transition">
                  <FileCheck className="h-3.5 w-3.5 text-[#1E40AF]" /> Bảo dưỡng định kỳ
                </Link>
              </li>
            </ul>
          </div>

          {/* Col 3: Điều hướng */}
          <div>
            <h3 className="text-[11px] font-semibold uppercase tracking-wider text-[#0F172A]">
              Hệ thống dịch vụ
            </h3>
            <ul className="mt-2.5 space-y-1.5 text-[13px]">
              <li>
                <Link href="/" className="hover:text-[#1E40AF] transition">
                  Trang chủ tiếp nhận
                </Link>
              </li>
              <li>
                <Link href="/chat" className="hover:text-[#1E40AF] transition">
                  Trợ lý Chatbot AI
                </Link>
              </li>
              <li>
                <Link href="/track-case" className="hover:text-[#1E40AF] transition">
                  Tra cứu hồ sơ sự cố
                </Link>
              </li>
              <li>
                <Link href="/console" className="inline-flex items-center gap-1 hover:text-[#1E40AF] transition">
                  Bàn điều phối KTV <span className="rounded-full bg-[#6D5BD0]/10 px-1.5 py-0.2 text-[10px] font-bold text-[#6D5BD0]">Staff</span>
                </Link>
              </li>
              <li>
                <Link href="/login" className="hover:text-[#1E40AF] transition">
                  Đăng nhập hệ thống
                </Link>
              </li>
            </ul>
          </div>

          {/* Col 4: Cam kết kỹ thuật */}
          <div>
            <h3 className="text-[11px] font-semibold uppercase tracking-wider text-[#0F172A]">
              Tiêu chuẩn kỹ thuật
            </h3>
            <ul className="mt-2.5 space-y-1.5 text-[12px] text-[#64748B]">
              <li className="flex items-start gap-1.5">
                <span className="font-semibold text-[#0F172A]">RAG Verified:</span>
                <span>Trích dẫn nguồn cẩm nang chính xác.</span>
              </li>
              <li className="flex items-start gap-1.5">
                <span className="font-semibold text-[#0F172A]">HITL Policy:</span>
                <span>Nhân viên xác nhận trước khi điều phối xưởng.</span>
              </li>
              <li className="flex items-start gap-1.5">
                <span className="font-semibold text-[#0F172A]">Vision OCR:</span>
                <span>Đọc nhận định sơ bộ đèn táp-lô.</span>
              </li>
            </ul>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="mt-8 border-t border-[#E2E8F0] pt-4 flex flex-col sm:flex-row items-center justify-between gap-3 text-[12px] text-[#64748B]">
          <p>© 2026 VinFast ServiceFlow AI (VFO2O-18) — AI20K Build Phase Cohort 4.</p>
          <div className="flex items-center gap-3 text-[11px]">
            <span>FastAPI + LangGraph</span>
            <span>•</span>
            <span>Next.js 14 App Router</span>
            <span>•</span>
            <span className="text-[#10B981] font-semibold">Ready for Demo</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
