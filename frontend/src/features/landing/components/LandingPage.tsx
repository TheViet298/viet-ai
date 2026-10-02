"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ArrowRight,
  BatteryCharging,
  Camera,
  Car,
  CheckCircle2,
  ChevronRight,
  Clock,
  FileCheck,
  ImagePlus,
  Mic,
  PhoneCall,
  ScanLine,
  Search,
  ShieldCheck,
  Sparkles,
  Wrench,
  X,
  BookOpen,
  ExternalLink,
} from "lucide-react";
import { getPublicArticles } from "@/features/chat/api/chatApi";
import { ArticleItem } from "@/features/chat/types";

const VEHICLE_OPTIONS = [
  "VinFast VF8",
  "VinFast VF5",
  "VinFast VF3",
  "VinFast VF6",
  "VinFast VF7",
  "VinFast VF9",
  "VinFast VF e34",
];

const QUICK_PROMPTS = [
  {
    icon: BatteryCharging,
    text: "Sạc trụ VinFast không vào điện trên xe VF8",
    query: "Trụ sạc VinFast cắm súng vào xe VF8 nhưng đèn báo đỏ và không nhận điện.",
  },
  {
    icon: Sparkles,
    text: "Màn hình táp-lô hiện biểu tượng rùa vàng",
    query: "Xe tôi hiện biểu tượng con rùa màu vàng trên màn hình táp-lô, xe chạy chậm.",
  },
  {
    icon: Wrench,
    text: "Cần số kẹt không sang được số D trên VF5",
    query: "Xe VF5 khởi động nhưng đạp phanh không gạt sang được số D để di chuyển.",
  },
  {
    icon: FileCheck,
    text: "Lịch bảo dưỡng định kỳ 12.000km xe điện",
    query: "Xe điện VinFast chạy được 12.000km cần bảo dưỡng và kiểm tra những hạng mục nào?",
  },
];

const CATEGORIES = [
  {
    icon: BatteryCharging,
    title: "Pin & Trụ sạc",
    desc: "Cổng sạc kẹt, trụ báo lỗi, sạc ngắt quãng hoặc tư vấn công suất sạc.",
    query: "Sự cố liên quan đến pin và trụ sạc xe điện VinFast.",
  },
  {
    icon: Camera,
    title: "Đèn cảnh báo táp-lô",
    desc: "Gửi ảnh táp-lô khi hiện biểu tượng lạ chưa rõ mã lỗi để AI đọc tín hiệu.",
    query: "Màn hình xe hiện đèn cảnh báo lạ cần hỗ trợ nhận diện.",
  },
  {
    icon: Wrench,
    title: "Động cơ & Vận hành",
    desc: "Không vào được số D/R, kẹt phanh tay điện tử, mất trợ lực lái, máy lạnh yếu.",
    query: "Xe gặp vấn đề khi vận hành hoặc không khởi động được.",
  },
  {
    icon: ShieldCheck,
    title: "Dịch vụ & Cứu hộ",
    desc: "Hướng dẫn bảo dưỡng định kỳ, điều phối cứu hộ pin lưu động 24/7.",
    query: "Cần hỗ trợ lịch xưởng dịch vụ hoặc hướng dẫn cứu hộ xe.",
  },
];

const STEPS = [
  {
    num: "01",
    title: "Gửi mô tả hoặc ảnh",
    desc: "Nhập dấu hiệu bằng ngôn ngữ tự nhiên hoặc tải ảnh chụp táp-lô xe.",
  },
  {
    num: "02",
    title: "AI nhận diện & làm rõ",
    desc: "Trợ lý hỏi 1-2 câu bối cảnh nhanh, đối chiếu cẩm nang VinFast chính thức.",
  },
  {
    num: "03",
    title: "Tạo Case Brief chuẩn",
    desc: "Chuẩn hóa dữ kiện kỹ thuật, phân loại mức độ ưu tiên theo chuẩn an toàn.",
  },
  {
    num: "04",
    title: "Chuyên viên xác nhận",
    desc: "Kỹ thuật viên kiểm tra, duyệt phương án và điều phối xưởng dịch vụ.",
  },
];

const TRUST_POINTS = [
  {
    title: "Tuân thủ No-PII",
    desc: "Không lưu trữ số CCCD, biển số thật hay giấy tờ cá nhân. Bảo vệ quyền riêng tư tuyệt đối.",
    icon: ShieldCheck,
  },
  {
    title: "Nguồn cẩm nang kiểm chứng",
    desc: "Mọi câu trả lời đều trích dẫn trực tiếp từ tài liệu kỹ thuật VinFast, không bịa đặt.",
    icon: CheckCircle2,
  },
  {
    title: "Thị giác máy tính (Vision)",
    desc: "Nhận diện sơ bộ đèn báo táp-lô qua ảnh để hỏi đúng trọng tâm kỹ thuật.",
    icon: Camera,
  },
  {
    title: "Human-in-the-Loop",
    desc: "Trường hợp kỹ thuật luôn có chuyên viên dịch vụ xem xét và phê duyệt trước khi điều phối.",
    icon: Wrench,
  },
  {
    title: "Hotline cứu hộ 24/7",
    desc: "Tích hợp đường dây nóng 1900-232389 xử lý tức thời mọi tình huống khẩn cấp.",
    icon: PhoneCall,
  },
];

export function LandingPage() {
  const router = useRouter();
  const [prompt, setPrompt] = useState("");
  const [selectedModel, setSelectedModel] = useState("VinFast VF8");
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [imageName, setImageName] = useState<string | null>(null);
  const [articles, setArticles] = useState<ArticleItem[]>([]);

  useState(() => {
    if (typeof window !== "undefined") {
      getPublicArticles()
        .then((res) => {
          if (res?.success && res.data?.articles) {
            setArticles(res.data.articles);
          }
        })
        .catch(() => {});
    }
  });

  const handleImageSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setImageName(file.name);
      const reader = new FileReader();
      reader.onload = () => setImagePreview(String(reader.result));
      reader.readAsDataURL(file);
    }
  };

  const handleClearImage = () => {
    setImagePreview(null);
    setImageName(null);
  };

  const handleSubmit = (overrideQuery?: string) => {
    const textToSend =
      overrideQuery ||
      prompt.trim() ||
      (imagePreview ? "Tôi gửi ảnh táp-lô cảnh báo, nhờ trợ lý nhận diện sơ bộ." : "");
    if (!textToSend && !imagePreview) return;

    try {
      sessionStorage.setItem("vf_initial_prompt", textToSend);
      sessionStorage.setItem("vf_initial_model", selectedModel);
      if (imagePreview) {
        sessionStorage.setItem("vf_initial_image", imagePreview);
        sessionStorage.setItem("vf_initial_image_name", imageName || "anh_canh_bao.jpg");
      }
    } catch {}

    const queryParams = new URLSearchParams();
    if (textToSend) queryParams.set("prompt", textToSend);
    queryParams.set("model", selectedModel.replace("VinFast ", ""));
    router.push(`/chat?${queryParams.toString()}`);
  };

  return (
    <div className="bg-[#F6F7F9] text-[#0F172A] min-h-screen">
      {/* ─────────────────────────────────────────────────────────
          1. HERO SECTION (THIẾT KẾ TINH TẾ THEO MẪU MỚI)
      ───────────────────────────────────────────────────────── */}
      <section className="pt-10 pb-16 md:pt-14 md:pb-20">
        <div className="mx-auto max-w-4xl px-4 sm:px-6 lg:px-8 text-center">
          {/* Mascot & Speech Bubble */}
          <div className="inline-flex flex-col items-center justify-center mb-5">
            <div className="relative inline-flex items-center gap-3">
              {/* Mascot Avatar - bo tròn 16px, shadow rất nhẹ */}
              <div className="relative flex h-14 w-14 sm:h-16 sm:w-16 items-center justify-center rounded-2xl bg-[#1E40AF] text-white shadow-[0_1px_2px_rgba(0,0,0,0.04)] border border-[#1E40AF]/20">
                <ScanLine className="h-7 w-7 text-white" />
                <span className="absolute -bottom-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-[#10B981] text-white text-[9px] font-bold">
                  ✓
                </span>
              </div>

              {/* Speech bubble bo tròn pill */}
              <div className="rounded-full border border-[#E2E8F0] bg-white px-3.5 py-1.5 text-[12px] font-medium text-[#0F172A] shadow-[0_1px_2px_rgba(0,0,0,0.04)] flex items-center gap-2">
                <span className="h-2 w-2 rounded-full bg-[#10B981] animate-pulse" />
                <span>Cần hỗ trợ sự cố xe, cứ gửi tin nhắn cho mình nhé</span>
              </div>
            </div>
          </div>

          {/* Heading 32px bold */}
          <h1 className="text-[28px] sm:text-[32px] font-bold tracking-tight text-[#0F172A] leading-tight">
            Xe của bạn đang gặp <span className="text-[#1E40AF]">vấn đề gì?</span>
          </h1>
          <p className="mx-auto mt-2 max-w-xl text-[13px] sm:text-[14px] leading-relaxed text-[#64748B]">
            ServiceFlow AI tiếp nhận mô tả bằng ngôn ngữ tự nhiên, đọc tín hiệu từ ảnh táp-lô và kết nối nhân viên kỹ thuật VinFast nhanh chóng.
          </p>

          {/* Central Floating Prompt Box - Bo góc 16px (card), shadow rất nhẹ */}
          <div className="mx-auto mt-6 max-w-2xl rounded-2xl border border-[#E2E8F0] bg-white p-4 shadow-[0_1px_2px_rgba(0,0,0,0.04)] text-left transition-colors focus-within:border-[#1E40AF]">
            {/* Attachment preview if selected */}
            {imagePreview && (
              <div className="mb-3 flex items-center justify-between rounded-xl border border-[#0D9488]/30 bg-[#F0FDFA] p-2 text-[12px]">
                <div className="flex items-center gap-2">
                  <img src={imagePreview} alt="Preview" className="h-10 w-14 rounded-lg object-cover" />
                  <div>
                    <p className="font-semibold text-[#0F172A] truncate max-w-[220px]">{imageName}</p>
                    <p className="text-[11px] text-[#64748B]">Ảnh táp-lô đã sẵn sàng gửi để AI nhận diện sơ bộ</p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={handleClearImage}
                  className="rounded-lg p-1 text-[#64748B] hover:bg-white hover:text-[#DC2626] transition"
                  title="Xóa ảnh"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            )}

            {/* Input textarea - Body 13-14px */}
            <textarea
              rows={2}
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSubmit();
                }
              }}
              placeholder="Mô tả dấu hiệu xe: ví dụ trụ sạc báo lỗi không vào điện, táp-lô hiện rùa vàng, kẹt cần số..."
              className="w-full resize-none border-none bg-transparent p-1 text-[13px] sm:text-[14px] text-[#0F172A] placeholder-[#64748B] focus:outline-none leading-relaxed"
            />

            {/* Bottom Toolbar: Upload button, Model dropdown, Submit button */}
            <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-[#E2E8F0] pt-3">
              <div className="flex items-center gap-2 flex-wrap">
                {/* Upload Image button - bo góc 10px */}
                <label
                  className="inline-flex cursor-pointer items-center gap-1.5 rounded-[10px] border border-[#E2E8F0] bg-[#F6F7F9] px-2.5 py-1.5 text-[12px] font-medium text-[#0F172A] hover:bg-white hover:border-[#1E40AF] transition"
                  title="Tải ảnh táp-lô hoặc trụ sạc"
                >
                  <ImagePlus className="h-4 w-4 text-[#0D9488]" />
                  <span className="hidden sm:inline">Tải ảnh táp-lô</span>
                  <input
                    type="file"
                    accept="image/*"
                    onChange={handleImageSelect}
                    className="sr-only"
                  />
                </label>

                {/* Model dropdown - bo góc 10px */}
                <div className="flex items-center gap-1.5 rounded-[10px] border border-[#E2E8F0] bg-[#F6F7F9] px-2.5 py-1.5 text-[12px]">
                  <Car className="h-3.5 w-3.5 text-[#1E40AF] shrink-0" />
                  <select
                    value={selectedModel}
                    onChange={(e) => setSelectedModel(e.target.value)}
                    className="bg-transparent font-medium text-[#0F172A] focus:outline-none text-[12px] cursor-pointer"
                  >
                    {VEHICLE_OPTIONS.map((m) => (
                      <option key={m} value={m}>
                        {m}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Action Submit - bo góc 10px, Deep Indigo Blue #1E40AF */}
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => handleSubmit()}
                  className="inline-flex items-center gap-1.5 rounded-[10px] bg-[#1E40AF] hover:bg-[#1E3A8A] px-4 py-1.5 text-[13px] font-semibold text-white shadow-[0_1px_2px_rgba(0,0,0,0.04)] transition"
                >
                  <span>Gửi yêu cầu</span>
                  <ArrowRight className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          </div>

          {/* Prompt Chips - Bo tròn hết cỡ (pill) */}
          <div className="mt-5 text-left max-w-2xl mx-auto">
            <div className="text-[11px] font-semibold uppercase tracking-wider text-[#64748B] mb-2 flex items-center gap-1">
              <Sparkles className="h-3.5 w-3.5 text-[#0D9488]" />
              <span>Gợi ý câu hỏi thử:</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {QUICK_PROMPTS.map((qp, idx) => {
                const Icon = qp.icon;
                return (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => handleSubmit(qp.query)}
                    className="inline-flex items-center gap-2 rounded-full border border-[#E2E8F0] bg-white px-3.5 py-1.5 text-[12px] text-[#0F172A] shadow-[0_1px_2px_rgba(0,0,0,0.04)] hover:border-[#1E40AF] hover:bg-[#EFF3FC] hover:text-[#1E40AF] transition"
                  >
                    <Icon className="h-3.5 w-3.5 text-[#0D9488] shrink-0" />
                    <span>{qp.text}</span>
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      </section>

      {/* ─────────────────────────────────────────────────────────
          2. PHÂN LOẠI NHU CẦU — 4 NHÓM SỰ CỐ CHÍNH (Card 16px, Spacing 16-24px)
      ───────────────────────────────────────────────────────── */}
      <section className="border-t border-[#E2E8F0] bg-white py-12 lg:py-16">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
          <div className="text-left md:text-center max-w-xl mx-auto mb-8">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-[#0D9488]">
              Nhóm sự cố phổ biến
            </span>
            <h2 className="mt-1 text-2xl font-bold tracking-tight text-[#0F172A]">
              Bắt đầu từ nhu cầu của bạn
            </h2>
            <p className="mt-1 text-[13px] text-[#64748B]">
              Chọn nhóm sự cố để AI khoanh vùng dữ liệu kỹ thuật và đưa ra hướng dẫn chuẩn xác.
            </p>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {CATEGORIES.map((cat, idx) => {
              const Icon = cat.icon;
              return (
                <div
                  key={idx}
                  onClick={() => handleSubmit(cat.query)}
                  className="group cursor-pointer rounded-2xl border border-[#E2E8F0] bg-[#F6F7F9] p-5 shadow-[0_1px_2px_rgba(0,0,0,0.04)] hover:border-[#1E40AF] hover:bg-white transition flex flex-col justify-between"
                >
                  <div>
                    <div className="flex h-10 w-10 items-center justify-center rounded-[10px] bg-[#EFF3FC] text-[#1E40AF] mb-4">
                      <Icon className="h-5 w-5" />
                    </div>
                    <h3 className="text-[15px] font-bold text-[#0F172A] group-hover:text-[#1E40AF] transition">
                      {cat.title}
                    </h3>
                    <p className="mt-1.5 text-[13px] leading-relaxed text-[#64748B]">
                      {cat.desc}
                    </p>
                  </div>
                  <div className="mt-5 flex items-center gap-1 text-[12px] font-semibold text-[#1E40AF]">
                    <span>Mô tả sự cố</span>
                    <ArrowRight className="h-3 w-3 transition group-hover:translate-x-1" />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* ─────────────────────────────────────────────────────────
          3. QUY TRÌNH 4 BƯỚC — ĐƠN GIẢN TỪ ĐẦU ĐẾN CUỐI (Card 16px)
      ───────────────────────────────────────────────────────── */}
      <section className="border-t border-[#E2E8F0] bg-[#F6F7F9] py-12 lg:py-16">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 gap-8 lg:grid-cols-12 items-center">
            {/* Left title */}
            <div className="lg:col-span-4">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-[#0D9488]">
                Đơn giản từ đầu đến cuối
              </span>
              <h2 className="mt-1 text-2xl sm:text-[28px] font-bold tracking-tight text-[#0F172A] leading-tight">
                Tiếp nhận sự cố trong 4 bước
              </h2>
              <p className="mt-2 text-[13px] leading-relaxed text-[#64748B]">
                Từ dấu hiệu xe ban đầu đến lịch hẹn xưởng kỹ thuật, mọi bước đều minh bạch, rõ ràng và có sự phê duyệt của chuyên viên kỹ thuật.
              </p>
              <div className="mt-6">
                <Link
                  href="/chat"
                  className="inline-flex items-center gap-1.5 rounded-[10px] bg-[#1E40AF] hover:bg-[#1E3A8A] px-4 py-2 text-[13px] font-semibold text-white shadow-[0_1px_2px_rgba(0,0,0,0.04)] transition"
                >
                  Bắt đầu yêu cầu ngay <ArrowRight className="h-3.5 w-3.5" />
                </Link>
              </div>
            </div>

            {/* Right 4 steps grid */}
            <div className="lg:col-span-8 grid grid-cols-1 sm:grid-cols-2 gap-4">
              {STEPS.map((step) => (
                <div
                  key={step.num}
                  className="rounded-2xl border border-[#E2E8F0] bg-white p-5 shadow-[0_1px_2px_rgba(0,0,0,0.04)]"
                >
                  <span className="font-mono text-[12px] font-bold text-[#1E40AF]">
                    {step.num}
                  </span>
                  <h3 className="mt-2 text-[15px] font-bold text-[#0F172A]">
                    {step.title}
                  </h3>
                  <p className="mt-1 text-[13px] leading-relaxed text-[#64748B]">
                    {step.desc}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ─────────────────────────────────────────────────────────
          KNOWLEDGE HUB: CẨM NANG & CHÍNH SÁCH KIỂM CHỨNG
      ───────────────────────────────────────────────────────── */}
      {articles.length > 0 && (
        <section className="border-t border-[#E2E8F0] bg-[#F6F7F9] py-12 lg:py-16">
          <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
            <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-8">
              <div>
                <span className="text-[11px] font-semibold uppercase tracking-wider text-[#10B981] flex items-center gap-1.5">
                  <BookOpen className="h-3.5 w-3.5" /> Nguồn chính thức VinFast
                </span>
                <h2 className="mt-1 text-2xl font-bold tracking-tight text-[#0F172A]">
                  Cẩm nang kỹ thuật & Chính sách đã kiểm chứng
                </h2>
                <p className="mt-1 text-[13px] text-[#64748B]">
                  Dữ liệu kiến thức đối chiếu chuẩn hóa mà AI Agent sử dụng để phản hồi khách hàng.
                </p>
              </div>
              <Link
                href="/chat"
                className="inline-flex items-center gap-1 text-[13px] font-semibold text-[#1E40AF] hover:underline"
              >
                Hỏi Agent về các bài viết này <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {articles.map((art) => (
                <div
                  key={art.id}
                  className="rounded-2xl border border-[#E2E8F0] bg-white p-5 shadow-[0_1px_2px_rgba(0,0,0,0.04)] flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-center justify-between gap-2 mb-2">
                      <span className="rounded-full bg-[#EFF3FC] px-2.5 py-0.5 text-[11px] font-semibold text-[#1E40AF]">
                        {art.category}
                      </span>
                      <span className="font-mono text-[11px] text-[#64748B]">
                        {art.id}
                      </span>
                    </div>
                    <h3 className="text-[15px] font-bold text-[#0F172A]">
                      {art.title}
                    </h3>
                    <p className="mt-2 text-[13px] leading-relaxed text-[#64748B]">
                      {art.summary}
                    </p>
                  </div>

                  <div className="mt-4 pt-3 border-t border-[#E2E8F0] flex items-center justify-between text-[12px]">
                    <span className="text-[#64748B] text-[11px]">
                      Kiểm chứng: {art.verified_at}
                    </span>
                    <a
                      href={art.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 font-semibold text-[#0D9488] hover:underline"
                    >
                      <span>Xem nguồn gốc</span>
                      <ExternalLink className="h-3 w-3" />
                    </a>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* ─────────────────────────────────────────────────────────
          4. CAM KẾT TIN CẬY & AN TOÀN NO-PII
      ───────────────────────────────────────────────────────── */}
      <section className="border-t border-[#E2E8F0] bg-white py-12 lg:py-16">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-xl mx-auto mb-8">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-[#0D9488]">
              Vì sao chọn ServiceFlow AI
            </span>
            <h2 className="mt-1 text-2xl font-bold tracking-tight text-[#0F172A]">
              Tiếp nhận chuẩn xác, an toàn No-PII
            </h2>
            <p className="mt-1 text-[13px] text-[#64748B]">
              Trợ lý AI đồng hành cùng chuyên viên kỹ thuật VinFast để mang đến phương án an tâm nhất.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
            {TRUST_POINTS.map((tp, idx) => {
              const Icon = tp.icon;
              return (
                <div
                  key={idx}
                  className="rounded-2xl border border-[#E2E8F0] bg-[#F6F7F9] p-4 text-left shadow-[0_1px_2px_rgba(0,0,0,0.04)]"
                >
                  <div className="flex h-9 w-9 items-center justify-center rounded-[10px] bg-[#ECFDF5] text-[#10B981] mb-3">
                    <Icon className="h-4 w-4" />
                  </div>
                  <h3 className="text-[13px] font-bold text-[#0F172A]">
                    {tp.title}
                  </h3>
                  <p className="mt-1 text-[12px] leading-normal text-[#64748B]">
                    {tp.desc}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      </section>
    </div>
  );
}
