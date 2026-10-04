"use client";

import { useMemo } from "react";
import Link from "next/link";
import { ExternalLink, FileText, Check } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ChatMessage } from "../types";
import { ClarificationChips } from "./ClarificationChips";

interface ChatMessageItemProps {
  message: ChatMessage;
  isLastMessage: boolean;
  onSelectReply: (reply: string) => void;
}

export function ChatMessageItem({
  message,
  isLastMessage,
  onSelectReply,
}: ChatMessageItemProps) {
  const isCustomer = message.sender === "CUSTOMER";

  // Chuẩn hóa ký tự bullet point, tách dòng nếu bị dồn và lọc emoji đầu mục
  const normalizedContent = useMemo(() => {
    if (!message.content) return "";
    let text = message.content;

    // 1. Xóa các mã nguồn học thuật thô lọt vào text (vd: [SRC-006], [SRC-001], [1], [2])
    text = text.replace(/\s*\[(?:SRC-[A-Za-z0-9_-]+|\d+)\]/g, "");

    // 2. Chuẩn hóa đại từ xưng hô thân thiện, loại bỏ xưng 'Quý khách' khách khí
    text = text.replace(/\bquý\s+khách\b/gi, "anh/chị");
    text = text.replace(/(^|[.!?]\s+)(anh\/chị)/g, (_m, p1, p2) => p1 + "Anh/chị");

    // 3. Tách các mục bị dồn trên 1 dòng có emoji + bold (vd: "🚗 **VF 3**: ... 🚙 **VF 5 Plus**: ...")
    text = text.replace(/(?:^|\n|[.!?]\s+)[\p{Emoji_Presentation}\p{Extended_Pictographic}]\s*(\*\*[^*]+\*\*)/gu, "\n\n- $1");

    // 4. Xóa emoji ở đầu các mục danh sách (vd: "- 🚗 **VF 3**" hoặc "1. 🚗 **VF 3**")
    text = text.replace(/^([ \t]*[-*]|\d+\.)\s*[\p{Emoji_Presentation}\p{Extended_Pictographic}]\s*/gmu, "$1 ");

    // 5. Chuẩn hóa bullet point unicode (•, ●, ▪, ▫) thành markdown (- )
    text = text.replace(/^[ \t]*[•●▪▫]\s*/gm, "- ");

    // 6. Nếu dòng bắt đầu bằng emoji đơn thuần ở đầu dòng thì chuyển thành gạch đầu dòng
    text = text.replace(/^[ \t]*[\p{Emoji_Presentation}\p{Extended_Pictographic}]\s*/gmu, "- ");

    // 7. Đảm bảo trước danh sách gạch đầu dòng luôn có dòng trống để Markdown parser nhận diện đúng thẻ <ul>
    text = text.replace(/([^\n])\n(- |\d+\. )/g, "$1\n\n$2");

    return text.trim();
  }, [message.content]);

  return (
    <div className={`flex flex-col ${isCustomer ? "items-end" : "items-start"} space-y-1.5`}>
      {/* Sender Label & Timestamp */}
      <div className="flex items-center gap-1.5 px-1 text-[11px] text-slate-400 font-medium">
        <span>{isCustomer ? "Bạn" : "Trợ lý VinFast"}</span>
        <span>·</span>
        <span>{new Date().toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" })}</span>
      </div>

      {/* ─────────────────────────────────────────────────────────────
          CẤP 1: BONG BÓNG DUY NHẤT (MỘT TIN NHẮN CHỈ MỘT BOX)
          - Khách: Xanh đặc
          - AI: Xám nhạt, KHÔNG VIỀN (Độ sâu bằng khác biệt màu nền)
      ───────────────────────────────────────────────────────────── */}
      <div
        className={`max-w-[88%] sm:max-w-[76%] rounded-2xl p-3 sm:p-3.5 text-[13px] leading-relaxed transition-all ${isCustomer
            ? "bg-[#1E40AF] text-white rounded-tr-xs"
            : "bg-slate-100 text-slate-800 rounded-tl-xs"
          }`}
      >
        {isCustomer ? (
          <div className="space-y-2">
            {message.image && (
              // Local preview belongs to this message and survives clearing the input.
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={message.image.src}
                alt={`Ảnh đã gửi: ${message.image.name}`}
                className="block max-h-[360px] w-auto max-w-full rounded-xl object-contain"
              />
            )}
            {message.content && <div className="whitespace-pre-wrap leading-relaxed">{message.content}</div>}
          </div>
        ) : (
          <div className="chat-markdown-body text-[13px] leading-relaxed text-slate-800">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              allowedElements={[
                "p",
                "strong",
                "em",
                "ul",
                "ol",
                "li",
                "a",
                "code",
                "span",
                "br",
              ]}
              unwrapDisallowed={true}
              components={{
                p: ({ children }) => <p className="mb-2 last:mb-0 leading-relaxed">{children}</p>,
                strong: ({ children }) => (
                  <strong className="font-semibold text-slate-900">{children}</strong>
                ),
                em: ({ children }) => <em className="italic">{children}</em>,
                ul: ({ children }) => (
                  <ul className="my-2 space-y-1.5 list-disc pl-[18px] leading-relaxed marker:text-slate-400">
                    {children}
                  </ul>
                ),
                ol: ({ children }) => (
                  <ol className="my-2 space-y-1.5 list-decimal pl-[18px] leading-relaxed marker:text-slate-400">
                    {children}
                  </ol>
                ),
                li: ({ children }) => (
                  <li className="pl-0.5 my-1.5 leading-relaxed text-slate-800">{children}</li>
                ),
                a: ({ href, children }) => (
                  <a
                    href={href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[#1E40AF] underline hover:text-blue-800 font-medium inline-flex items-center gap-0.5"
                  >
                    {children}
                  </a>
                ),
                code: ({ children }) => (
                  <code className="px-1.5 py-0.5 bg-slate-200/80 text-slate-800 rounded font-mono text-[12px]">
                    {children}
                  </code>
                ),
              }}
            >
              {normalizedContent}
            </ReactMarkdown>
          </div>
        )}

        {/* Chỉ dẫn an toàn: gộp trực tiếp vào bong bóng dạng chữ đậm, KHÔNG TẠO HỘP VÀNG */}
        {message.safe_guidance && message.priority !== "CRITICAL" && (
          <div className="mt-2 pt-1.5 border-t border-slate-200/60 text-[12px] text-amber-950 font-medium">
            <strong>Chỉ dẫn: </strong>
            <span>{message.safe_guidance}</span>
          </div>
        )}

        {/* ─────────────────────────────────────────────────────────────
            CẤP 2: NGUỒN TÀI LIỆU (KHÔNG CÓ KHUNG TO)
        ───────────────────────────────────────────────────────────── */}
        {message.citations && message.citations.length > 0 && (
          <div className="mt-2 pt-1 flex items-center gap-1.5 text-[11px] text-slate-500">
            {message.citations.slice(0, 1).map((cite, i) => (
              <a
                key={i}
                href={cite.url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 hover:text-[#1E40AF] font-medium truncate"
                title={cite.title}
              >
                <FileText className="w-3 h-3 text-[#1E40AF] shrink-0" />
                <span className="truncate max-w-[200px] sm:max-w-[260px]">
                  {cite.title.replace(/—.*$/, "").trim()}
                </span>
                <ExternalLink className="w-2.5 h-2.5 opacity-60 shrink-0" />
              </a>
            ))}
          </div>
        )}
      </div>

      {/* ─────────────────────────────────────────────────────────────
          CẤP 3: TRẠNG THÁI HỆ THỐNG ("ĐÃ TIẾP NHẬN CA")
          - 1 dòng nhỏ giữa khung chat, KHÔNG NỀN, KHÔNG BONG BÓNG
      ───────────────────────────────────────────────────────────── */}
      {message.case_id && (
        <div className="my-1 py-0.5 px-1 text-[11.5px] text-slate-500 flex items-center gap-1.5 self-center animate-fadeIn">
          <span className="w-4 h-4 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center shrink-0">
            <Check className="w-2.5 h-2.5" />
          </span>
          <span>
            Đã tiếp nhận <strong className="font-mono text-slate-800">{message.case_id}</strong>
          </span>
          <span>·</span>
          <Link
            href="/track-case"
            className="text-[#1E40AF] font-semibold hover:underline"
          >
            Xem tiến trình ›
          </Link>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          CẤP 4: GỢI Ý TRẢ LỜI NHANH
          - CHỈ HIỆN DƯỚI TIN NHẮN CUỐI CÙNG (Tối đa 4 chip cho lời chào hoặc 2-3 chip sự cố)
          - Tự động biến mất sau khi khách gửi tin nhắn mới
      ───────────────────────────────────────────────────────────── */}
      {isLastMessage && message.suggested_replies && message.suggested_replies.length > 0 && (
        <ClarificationChips
          chips={message.suggested_replies.slice(0, 4)}
          onSelectChip={onSelectReply}
        />
      )}
    </div>
  );
}
