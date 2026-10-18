"use client";
import { useLocale } from "@/features/shared/context/LocaleContext";
import { parseServerTimestamp } from "@/lib/utils";
import { VehicleInfoCard } from "./VehicleInfoCard";
import { VehicleComparison } from "./VehicleComparison";

import { useMemo, Children, isValidElement, useEffect, useState } from "react";
import Link from "next/link";
import { ExternalLink, FileText, Check } from "lucide-react";
import ReactMarkdown, { defaultUrlTransform } from "react-markdown";
import remarkGfm from "remark-gfm";
import { ChatMessage } from "../types";
import { ClarificationChips } from "./ClarificationChips";

interface ChatMessageItemProps {
  message: ChatMessage;
  isLastMessage: boolean;
  showCaseBadge?: boolean;
  onSelectReply: (reply: string) => void;
}

export function ChatMessageItem({
  message,
  isLastMessage,
  showCaseBadge = false,
  onSelectReply,
}: ChatMessageItemProps) {
  const { t, language } = useLocale(message.language || "vi");
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  const timestamp = message.timestamp ? parseServerTimestamp(message.timestamp) : null;
  const displayTime = mounted && timestamp && Number.isFinite(timestamp.getTime())
    ? timestamp.toLocaleTimeString(language === "en" ? "en-US" : "vi-VN", { hour: "2-digit", minute: "2-digit" })
    : "";
  const isCustomer = message.sender === "CUSTOMER";
  const hasVehicleCards = !isCustomer && Boolean(message.vehicle_cards?.length);
  const isComparison = hasVehicleCards && message.vehicle_comparison && message.vehicle_cards?.length === 2;

  // Chuẩn hóa ký tự bullet point, tách dòng nếu bị dồn và lọc emoji đầu mục
  const normalizedContent = useMemo(() => {
    if (!message.content) return "";
    let text = message.content.replace(/\\n/g, "\n");

    // 1. Xóa các mã nguồn học thuật thô lọt vào text (vd: [SRC-006], [SRC-001], [1], [2])
    text = text.replace(/\s*\[(?:SRC-[A-Za-z0-9_-]+|\d+)\]/g, "");

    // 2. Chuẩn hóa đại từ xưng hô theo chuẩn VinFast CSKH (giữ nguyên Quý khách)
    text = text.replace(/khách\s+hàng\s+đã\s+dừng\s+đỗ/gi, "Quý khách đã dừng đỗ");
    text = text.replace(/Khách\s+hàng\s+đã\s+dừng\s+đỗ/g, "Quý khách đã dừng đỗ");

    // 2b. Tách các cụm trạng thái sự cố bị dính trên 1 dòng
    text = text.replace(
      /(?:sự cố [^:\n]+:\s*)?Tình trạng:\s*([^(\n]+?)\s*\(Mức pin:\s*([^)]+)\)\s*Trạng thái:\s*([^\n.]+)/gi,
      (_match, p1, p2, p3) => {
        const cleanP3 = p3.replace(/khách\s+hàng\s+đã\s+dừng\s+đỗ/gi, "Quý khách đã dừng đỗ");
        return `\n\n- **Tình trạng:** ${p1.trim()}\n- **Mức pin:** ${p2.trim()}\n- **Trạng thái:** ${cleanP3.trim()}\n\n`;
      }
    );
    text = text.replace(/([^\n])\n(Tình trạng:|Mức pin:|Trạng thái:)/gi, "$1\n\n- $2");

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
    <div lang={language} className={`flex flex-col ${isCustomer ? "items-end" : "items-start"} space-y-1.5`}>
      {/* Sender Label & Timestamp */}
      <div className="flex items-center gap-1.5 px-1 text-[11px] text-slate-400 font-medium">
        <span>{isCustomer ? t("Bạn") : t("Trợ lý VinFast")}</span>
        <span>·</span>
        <time dateTime={message.timestamp || undefined}>{displayTime}</time>
      </div>

      {hasVehicleCards && (
        <>
          {isComparison ? <VehicleComparison language={language} cards={message.vehicle_cards!} /> : <div className="grid w-full max-w-[596px] grid-cols-1 gap-2 sm:grid-cols-2">
            {message.vehicle_cards!.map(card => <VehicleInfoCard language={language} key={`${card.model}-${card.variant || card.name}`} card={card} />)}
          </div>}
          {!isComparison && isLastMessage && message.suggested_replies?.length ? (
            <div className="grid w-full max-w-[596px] grid-cols-1 gap-2 py-2 sm:grid-cols-2">
              {message.suggested_replies.map(reply => <button key={reply} type="button" onClick={() => onSelectReply(reply)}
                className="min-h-11 w-full max-w-[294px] rounded-xl border border-slate-200 bg-white px-4 py-2 text-left text-sm text-slate-800 hover:bg-slate-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600">{reply}</button>)}
            </div>
          ) : null}
        </>
      )}

      {/* ─────────────────────────────────────────────────────────────
          CẤP 1: BONG BÓNG DUY NHẤT (MỘT TIN NHẮN CHỈ MỘT BOX)
          - Khách: Xanh đặc
          - AI: Xám nhạt, KHÔNG VIỀN (Độ sâu bằng khác biệt màu nền)
      ───────────────────────────────────────────────────────────── */}
      <div
        className={`max-w-[88%] sm:max-w-[76%] rounded-2xl p-3 sm:p-3.5 text-[13px] leading-[1.5] transition-all ${isCustomer
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
            {message.content && <div className="whitespace-pre-wrap leading-[1.5]">{message.content}</div>}
          </div>
        ) : (
          <div className="chat-markdown-body text-[13px] leading-[1.5] text-slate-800">
            <ReactMarkdown
              urlTransform={(url) => /^tel:\+?\d+$/.test(url) ? url : defaultUrlTransform(url)}
              remarkPlugins={[remarkGfm]}
              allowedElements={[
                "p",
                "h3",
                "h4",
                "strong",
                "em",
                "ul",
                "ol",
                "li",
                "a",
                "code",
                "span",
                "br",
                "table",
                "thead",
                "tbody",
                "tr",
                "th",
                "td",
              ]}
              unwrapDisallowed={true}
              components={{
                h3: ({ children }) => (
                  <h3 className="text-[14px] font-bold text-slate-900 mt-0.5 mb-1 tracking-tight">
                    {children}
                  </h3>
                ),
                h4: ({ children }) => (
                  <h4 className="text-[13px] font-semibold text-slate-800 mt-2 mb-1">
                    {children}
                  </h4>
                ),
                table: ({ children }) => (
                  <div className="my-2.5 w-full overflow-x-auto rounded-xl border border-slate-200/90 bg-white/70 shadow-xs">
                    <table className="w-full min-w-[360px] sm:min-w-[420px] text-left text-[12px] sm:text-[12.5px] border-collapse">
                      {children}
                    </table>
                  </div>
                ),
                thead: ({ children }) => (
                  <thead className="bg-slate-200/70 text-slate-900 font-semibold border-b border-slate-200">
                    {children}
                  </thead>
                ),
                tbody: ({ children }) => (
                  <tbody className="divide-y divide-slate-200/80 bg-white/50">
                    {children}
                  </tbody>
                ),
                tr: ({ children }) => (
                  <tr className="hover:bg-slate-100/50 transition-colors">
                    {children}
                  </tr>
                ),
                th: ({ children }) => (
                  <th className="px-3 py-2 text-slate-900 font-semibold border-r border-slate-200/70 last:border-r-0 whitespace-nowrap">
                    {children}
                  </th>
                ),
                td: ({ children }) => (
                  <td className="px-3 py-2 text-slate-700 border-r border-slate-200/70 last:border-r-0 leading-relaxed">
                    {children}
                  </td>
                ),
                p: ({ children }) => {
                  const childArray = Children.toArray(children);
                  if (childArray.length === 1 && isValidElement(childArray[0])) {
                    const el = childArray[0];
                    if (el.type === "em" || (el.props as any)?.node?.tagName === "em") {
                      return (
                        <p className="mt-0.5 mb-2 text-[12px] text-slate-500 italic leading-[1.5]">
                          {children}
                        </p>
                      );
                    }
                    if (el.type === "strong" || (el.props as any)?.node?.tagName === "strong") {
                      return (
                        <p className="mt-2.5 mb-1 text-[13px] font-semibold text-slate-900 leading-[1.5]">
                          {children}
                        </p>
                      );
                    }
                  }
                  return <p className="mb-2 last:mb-0 leading-[1.5] text-slate-800">{children}</p>;
                },
                strong: ({ children }) => (
                  <strong className="font-semibold text-slate-900">{children}</strong>
                ),
                em: ({ children }) => (
                  <em className="italic text-slate-500 text-[12px] font-normal inline">
                    {children}
                  </em>
                ),
                ul: ({ children }) => (
                  <ul className="mb-2 space-y-1 list-disc pl-[18px] leading-[1.5] marker:text-slate-400">
                    {children}
                  </ul>
                ),
                ol: ({ children }) => (
                  <ol className="mb-2 space-y-1 list-decimal pl-[18px] leading-[1.5] marker:text-slate-400">
                    {children}
                  </ol>
                ),
                li: ({ children }) => (
                  <li className="pl-0.5 leading-[1.5] text-slate-800 [&>p]:m-0 [&>p]:inline">
                    {children}
                  </li>
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
        {message.safe_guidance && !normalizedContent.replace(/\s+/g, " ").includes(message.safe_guidance.replace(/\s+/g, " ").trim()) && (
          <div className="mt-2 pt-1.5 border-t border-slate-200/60 text-[12px] text-amber-950 font-medium">
            <strong>{t("Chỉ dẫn:")}{" "}</strong>
            <span>{message.safe_guidance}</span>
          </div>
        )}

        {/* ─────────────────────────────────────────────────────────────
            CẤP 2: NGUỒN TÀI LIỆU (KHÔNG CÓ KHUNG TO)
        ───────────────────────────────────────────────────────────── */}
        {message.citations && message.citations.length > 0 && (
          <div className="mt-2 pt-1 flex flex-wrap items-center gap-2 text-[11px] text-slate-500">
            {message.citations.map((cite, i) => (
              <a
                key={i}
                href={cite.url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 hover:text-[#1E40AF] font-medium max-w-full group"
                title={cite.title}
              >
                <FileText className="w-3 h-3 text-[#1E40AF] shrink-0 group-hover:scale-110 transition-transform" />
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
          - CHỈ HIỆN 1 LẦN DUY NHẤT sau tin AI xác nhận tạo ca
      ───────────────────────────────────────────────────────────── */}
      {showCaseBadge && message.case_id && (
        <div className="my-1 py-0.5 px-1 text-[11.5px] text-slate-500 flex items-center gap-1.5 self-center animate-fadeIn">
          <span className="w-4 h-4 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center shrink-0">
            <Check className="w-2.5 h-2.5" />
          </span>
          <span>
            {t("Đã tiếp nhận")}{" "}<strong className="font-mono text-slate-800">{message.case_id}</strong>
          </span>
          <span>·</span>
          <Link
            href={`/track-case?case_id=${encodeURIComponent(message.case_id)}`}
            className="text-[#1E40AF] font-semibold hover:underline"
          >
            {t("Xem tiến trình ›")}</Link>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          CẤP 4: GỢI Ý TRẢ LỜI NHANH
          - CHỈ HIỆN DƯỚI TIN NHẮN CUỐI CÙNG (Tối đa 4 chip cho lời chào hoặc 2-3 chip sự cố)
          - Tự động biến mất sau khi khách gửi tin nhắn mới
      ───────────────────────────────────────────────────────────── */}
      {!hasVehicleCards && isLastMessage && message.suggested_replies && message.suggested_replies.length > 0 && (
        <ClarificationChips
          chips={message.suggested_replies.slice(0, 4)}
          onSelectChip={onSelectReply}
        />
      )}
    </div>
  );
}
