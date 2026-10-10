"use client";

import { useState, useEffect, useMemo, useRef } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ArrowRight,
  BatteryCharging,
  Camera,
  Car,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  FileCheck,
  FileText,
  ImagePlus,
  PhoneCall,
  ScanLine,
  ShieldCheck,
  Sparkles,
  Wrench,
  X,
  BookOpen,
  ExternalLink,
  MessageSquare,
  AlertTriangle,
  Clock,
} from "lucide-react";
import { getPublicArticles, getCustomerCases } from "@/features/chat/api/chatApi";
import { ArticleItem, CustomerCaseItem } from "@/features/chat/types";
import { useAuth } from "@/features/shared/context/AuthContext";

// =============================================================================
// DATA CONSTANTS & FALLBACKS
// =============================================================================

const PLACEHOLDER_EXAMPLES = [
  "Trụ sạc báo đỏ lỗi CC01, không vào điện...",
  "Lịch bảo dưỡng 12.000km xe VF8 gồm những gì?",
  "Cách đặt lịch sạc hoặc tìm trạm qua ứng dụng VinFast?",
  "Màn hình xe hiện biểu tượng con rùa vàng, bị giới hạn công suất...",
];

const QUICK_PROMPTS = [
  {
    label: "Sạc không vào điện (CC01)",
    text: "Trụ sạc VinFast cắm súng vào xe nhưng đèn báo đỏ lỗi CC01 và không nhận điện.",
    model: "VF8",
    category: "Sự cố",
    icon: "⚠",
  },
  {
    label: "Táp-lô hiện rùa vàng",
    text: "Xe tôi hiện biểu tượng con rùa màu vàng trên màn hình táp-lô, xe bị giới hạn công suất.",
    model: "VF5",
    category: "Sự cố",
    icon: "⚠",
  },
  {
    label: "Lịch bảo dưỡng 12.000km",
    text: "Xe điện VinFast chạy được 12.000km cần bảo dưỡng và kiểm tra những hạng mục nào?",
    model: "VF8",
    category: "Bảo dưỡng",
    icon: "🔧",
  },
  {
    label: "Tìm trạm sạc gần tôi",
    text: "Tìm trạm sạc xe điện VinFast gần vị trí của tôi nhất.",
    model: "VF8",
    category: "Tra cứu",
    icon: "⚡",
  },
  {
    label: "Cách dùng app VinFast",
    text: "Hướng dẫn cách kết nối và đặt lịch sạc qua ứng dụng VinFast trên điện thoại.",
    model: "VF8",
    category: "Hướng dẫn",
    icon: "📱",
  },
];

// 4 Nhóm sự cố dạng Thẻ Ngang Nhỏ (Horizontal Cards)
const ISSUE_CATEGORIES = [
  {
    id: "charging",
    title: "Pin & Trụ sạc",
    desc: "Cổng sạc kẹt, trụ báo đỏ CC01, ngắt nguồn hoặc sạc chậm",
    icon: BatteryCharging,
    query: "Trụ sạc VinFast báo đèn đỏ lỗi CC01 không sạc được điện.",
    model: "VinFast VF8",
  },
  {
    id: "dashboard",
    title: "Đèn cảnh báo táp-lô",
    desc: "Biểu tượng con rùa vàng, áp suất lốp TPMS, cảnh báo bình 12V",
    icon: Camera,
    query: "Màn hình xe hiện biểu tượng con rùa vàng và đèn cảnh báo lạ.",
    model: "VinFast VF5",
  },
  {
    id: "powertrain",
    title: "Động cơ & Cần số",
    desc: "Kẹt cần số D/R, mất trợ lực lái, xe không di chuyển được",
    icon: Wrench,
    query: "Xe đã khởi động nhưng không gạt sang được số D để di chuyển.",
    model: "VinFast VF5",
  },
  {
    id: "service",
    title: "Bảo dưỡng & Cứu hộ",
    desc: "Lịch bảo dưỡng 12.000km, cứu hộ pin lưu động, kiểm tra định kỳ",
    icon: ShieldCheck,
    query: "Cần tra cứu lịch bảo dưỡng định kỳ 12.000km và đặt hẹn dịch vụ.",
    model: "VinFast VF8",
  },
];

// Cẩm nang kiến thức chính thức (Fallback cho Knowledge Hub nếu backend offline)
// Đồng bộ 100% với danh mục nguồn chính thức tại docs/data-sources.md
const FALLBACK_ARTICLES: ArticleItem[] = [
  {
    id: "KB-CHG-01",
    title: "Quy chuẩn sạc DC & Dịch vụ pin xe điện VinFast",
    category: "Sạc & Pin",
    summary:
      "Hướng dẫn kiểm tra súng sạc, trình tự khóa ngàm tiếp xúc và cách khắc phục khi trụ sạc báo đèn đỏ giao tiếp (Mã CC01).",
    source_url: "https://vinfastauto.com/vn_vi/dich-vu-pin-oto-dien",
    verified_at: "30/09/2026",
    applicable_models: ["VF3", "VF5", "VF6", "VF7", "VF8", "VF9"],
  },
  {
    id: "KB-DASH-02",
    title: "Sổ tay vận hành & Ý nghĩa biểu tượng cảnh báo táp-lô",
    category: "Vận hành",
    summary:
      "Chế độ bảo vệ pin cao áp khi dung lượng còn dưới 10% hoặc nhiệt độ hệ thống pin tăng cao. Hướng dẫn di chuyển an toàn khi hiện rùa vàng.",
    source_url: "https://om.vinfastauto.com/vi_vn/detail?car=VF8&year=2026",
    verified_at: "30/09/2026",
    applicable_models: ["VF3", "VF5", "VF6", "VF7", "VF8", "VF9"],
  },
  {
    id: "KB-MAINT-03",
    title: "Quy trình và lịch bảo dưỡng định kỳ xe điện VinFast",
    category: "Bảo dưỡng",
    summary:
      "Các hạng mục bắt buộc mốc 12.000km: kiểm tra nước làm mát pin, đo độ mòn má phanh, cập nhật phần mềm ECU và cân bằng động lốp.",
    source_url: "https://vinfastauto.com/vn_vi/dich-vu-bao-duong-oto",
    verified_at: "30/09/2026",
    applicable_models: ["VF3", "VF5", "VF6", "VF7", "VF8", "VF9"],
  },
  {
    id: "KB-RESCUE-04",
    title: "Thông tin cứu hộ khẩn cấp 24/7 & Cứu hộ pin lưu động",
    category: "Cứu hộ",
    summary:
      "Quy chuẩn điều phối xe cẩu cứu hộ trên cao tốc toàn quốc và dịch vụ sạc pin lưu động 24/7 qua tổng đài 1900-232389.",
    source_url: "https://vinfastauto.com/vn_vi/thong-tin-cuu-ho-oto",
    verified_at: "30/09/2026",
    applicable_models: ["Tất cả dòng xe"],
  },
  {
    id: "KB-WARR-05",
    title: "Chính sách bảo hành xe ô tô điện VinFast",
    category: "Bảo hành",
    summary:
      "Chính sách bảo hành 10 năm hoặc 200.000 km cho xe và pin cao áp. Cam kết thay thế pack pin khi dung lượng dưới 70%.",
    source_url: "https://vinfastauto.com/vn_vi/chinh-sach-bao-hanh-oto",
    verified_at: "30/09/2026",
    applicable_models: ["VF3", "VF5", "VF6", "VF7", "VF8", "VF9"],
  },
  {
    id: "KB-APP-06",
    title: "Hướng dẫn sử dụng ứng dụng VinFast",
    category: "Ứng dụng",
    summary:
      "Cách theo dõi dung lượng pin (SoC), kiểm tra lịch sử sạc, tìm trạm sạc gần nhất và đặt hẹn bảo dưỡng trực tiếp trên ứng dụng.",
    source_url: "https://vinfastauto.com/vn_vi/huong-dan-su-dung-ung-dung-vinfast",
    verified_at: "30/09/2026",
    applicable_models: ["Tất cả dòng xe"],
  },
];

export function LandingPage() {
  const router = useRouter();
  const { user, role } = useAuth();
  const [prompt, setPrompt] = useState("");
  const [selectedModel, setSelectedModel] = useState("");
  const [placeholderIndex, setPlaceholderIndex] = useState(0);
  const [isPromptFocused, setIsPromptFocused] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [imageName, setImageName] = useState<string | null>(null);

  // Articles state with fallbacks
  const [articles, setArticles] = useState<ArticleItem[]>(FALLBACK_ARTICLES);
  const [selectedArticleCategory, setSelectedArticleCategory] = useState<string>("ALL");

  // Active cases of user (CHỈ dành cho CUSTOMER đã đăng nhập - ADR-005, RBAC)
  const [activeUserCase, setActiveUserCase] = useState<CustomerCaseItem | null>(null);
  const [openCasesCount, setOpenCasesCount] = useState<number>(0);
  // Mặc định là dạng thu gọn (pill); đọc trạng thái từ sessionStorage nếu có
  const [isCaseBubbleExpanded, setIsCaseBubbleExpanded] = useState(false);
  // Hiệu ứng trượt vào sau 300ms sau khi trang tải xong (không xuất hiện cùng lúc với hero)
  const [isBubbleMounted, setIsBubbleMounted] = useState(false);

  // Scroll indicator state
  const [hasScrolled, setHasScrolled] = useState(false);

  // Đồng bộ dòng xe mặc định theo hồ sơ tài khoản (Customer: xe của họ; Guest: để trống)
  useEffect(() => {
    if (role === "CUSTOMER" && user) {
      const model = user.vehicleModel ? `VinFast ${user.vehicleModel.replace("VinFast ", "")}` : "VinFast VF8";
      setSelectedModel(model);
    } else {
      setSelectedModel("");
    }
  }, [role, user]);

  // Xoay vòng placeholder mô tả sau mỗi 3.8s, dừng xoay khi người dùng đang focus hoặc đã gõ chữ
  useEffect(() => {
    if (isPromptFocused || prompt.trim().length > 0) return;
    const timer = setInterval(() => {
      setPlaceholderIndex((prev) => (prev + 1) % PLACEHOLDER_EXAMPLES.length);
    }, 3800);
    return () => clearInterval(timer);
  }, [isPromptFocused, prompt]);

  // Đọc sessionStorage và hẹn giờ trượt vào 300ms sau khi trang tải xong
  useEffect(() => {
    if (typeof window !== "undefined") {
      const saved = sessionStorage.getItem("sf_case_bubble_expanded");
      if (saved === "true") {
        setIsCaseBubbleExpanded(true);
      }
    }
    const timer = setTimeout(() => {
      setIsBubbleMounted(true);
    }, 300);
    return () => clearTimeout(timer);
  }, []);

  const handleCollapseBubble = () => {
    setIsCaseBubbleExpanded(false);
    if (typeof window !== "undefined") {
      sessionStorage.setItem("sf_case_bubble_expanded", "false");
    }
  };

  const handleExpandBubble = () => {
    setIsCaseBubbleExpanded(true);
    if (typeof window !== "undefined") {
      sessionStorage.setItem("sf_case_bubble_expanded", "true");
    }
  };

  // Ngôn ngữ hướng khách hàng cho trạng thái tiến trình (thay vì "Đang xử lý" chung chung)
  const friendlyStatus = useMemo(() => {
    if (!activeUserCase) return "";
    const summaryLower = (activeUserCase.summary || "").toLowerCase();

    // Bước kiểm tra thiết bị / hiện trường cụ thể
    if (summaryLower.includes("p02")) {
      return "Kỹ thuật viên đang kiểm tra trụ P02";
    }
    if (summaryLower.includes("trụ") || summaryLower.includes("sạc") || summaryLower.includes("cc01")) {
      return "Kỹ thuật viên đang kiểm tra trụ sạc";
    }
    if (summaryLower.includes("pin") || summaryLower.includes("rùa vàng")) {
      return "Kỹ thuật viên đang chẩn đoán pin";
    }
    const s = (activeUserCase.status || "").toUpperCase();
    if (s === "ASSIGNED" || s === "STAFF REVIEWING") {
      return "Cố vấn dịch vụ đang tiếp nhận";
    }
    if (s === "IN PROGRESS" || s === "DISPATCHED") {
      return "Kỹ thuật viên đang xử lý sự cố";
    }
    if (s === "NEEDS INFORMATION" || s === "NEEDS_INFORMATION" || s === "WAITING_CONFIRMATION") {
      return "Chờ bạn bổ sung thông tin xe";
    }
    if (s === "RESOLVED" || s === "ĐÃ GIẢI QUYẾT") {
      return "Chờ bạn xác nhận nghiệm thu xe";
    }
    if (s === "PENDING") {
      return "Đang điều phối kỹ thuật viên";
    }
    return "Kỹ thuật viên đang kiểm tra";
  }, [activeUserCase]);

  // Cấu hình hiển thị bong bóng phản ánh trạng thái thực (Needs Info / In Progress / Resolved / Closed)
  const bubbleConfig = useMemo(() => {
    if (!activeUserCase) return null;
    const rawStatus = (activeUserCase.status || "").trim();
    const upper = rawStatus.toUpperCase();

    // Closed: Ẩn hoàn toàn
    if (upper === "CLOSED" || upper === "ĐÃ ĐÓNG" || upper === "CANCELLED") {
      return null;
    }

    // 1. Needs Information: Nổi bật nhất (màu cam, chấm đỏ nhấp nháy, vì đang chờ khách)
    if (
      upper === "NEEDS INFORMATION" ||
      upper === "NEEDS_INFORMATION" ||
      upper === "WAITING_CONFIRMATION" ||
      upper === "CHỜ BỔ SUNG"
    ) {
      return {
        type: "NEEDS_INFO" as const,
        badgeText: "Cần bổ sung thông tin",
        subtitle: "Kỹ thuật viên đang chờ dữ kiện từ bạn",
        cardClass: "border-amber-300 bg-amber-50/95 hover:border-amber-500",
        pillClass: "border-amber-300 bg-amber-50/95 hover:border-amber-500 text-amber-900",
        mobileClass: "border-amber-300 bg-amber-50/95",
        dotPing: "bg-red-400",
        dotBg: "bg-red-500",
        badgeBg: "bg-amber-200 text-amber-900 border-amber-300",
        ctaText: "Bổ sung",
        ctaColor: "text-amber-700 group-hover:text-amber-900",
        pillText: "Cần bổ sung thông tin",
      };
    }

    // 2. Resolved (chờ nghiệm thu): Nhắc nhẹ “Xác nhận hoàn tất” (xanh lá / emerald)
    if (upper === "RESOLVED" || upper === "ĐÃ GIẢI QUYẾT" || upper === "HOÀN TẤT") {
      return {
        type: "RESOLVED" as const,
        badgeText: "Đã xử lý xong",
        subtitle: "Nhắc nhẹ: Xác nhận hoàn tất",
        cardClass: "border-emerald-300 bg-emerald-50/95 hover:border-emerald-500",
        pillClass: "border-emerald-300 bg-emerald-50/95 hover:border-emerald-500 text-emerald-900",
        mobileClass: "border-emerald-300 bg-emerald-50/95",
        dotPing: "bg-emerald-400",
        dotBg: "bg-emerald-600",
        badgeBg: "bg-emerald-100 text-emerald-800 border-emerald-200",
        ctaText: "Nghiệm thu",
        ctaColor: "text-emerald-700 group-hover:text-emerald-900",
        pillText: "Xác nhận hoàn tất",
      };
    }

    // 3. In Progress (và Staff Reviewing, Assigned): Bình thường, màu xanh
    return {
      type: "IN_PROGRESS" as const,
      badgeText: "Hồ sơ đang xử lý",
      subtitle: friendlyStatus || "Kỹ thuật viên đang kiểm tra",
      cardClass: "border-blue-200/90 bg-white/95 hover:border-[#1E40AF]",
      pillClass: "border-blue-200/90 bg-white/95 hover:border-[#1E40AF] text-slate-800",
      mobileClass: "border-blue-200/80 bg-white/95",
      dotPing: "bg-blue-400",
      dotBg: "bg-[#1E40AF]",
      badgeBg: "bg-blue-100 text-[#1E40AF]",
      ctaText: "Xem",
      ctaColor: "text-[#1E40AF]",
      pillText: `${openCasesCount > 1 ? openCasesCount : 1} hồ sơ đang xử lý`,
    };
  }, [activeUserCase, friendlyStatus, openCasesCount]);

  // Kiểm tra có cập nhật mới từ nhân viên kỹ thuật hay không (hiện chấm đỏ nhỏ)
  const hasStaffUpdate = useMemo(() => {
    if (!activeUserCase) return false;
    return Boolean(
      activeUserCase.updated_at && activeUserCase.updated_at !== activeUserCase.created_at
    );
  }, [activeUserCase]);

  // Fetch articles & customer case status
  useEffect(() => {
    getPublicArticles()
      .then((res) => {
        if (res?.success && res.data?.articles && res.data.articles.length > 0) {
          setArticles(res.data.articles);
        }
      })
      .catch(() => {});

    // RBAC: Chỉ truy xuất và hiển thị hồ sơ cá nhân khi vai trò là CUSTOMER đã đăng nhập (Guest không có thẻ này)
    if (role === "CUSTOMER" && user) {
      getCustomerCases()
        .then((res) => {
          if (res?.success && res.data?.cases && res.data.cases.length > 0) {
            // Closed cases ẩn hoàn toàn, còn Resolved cần khách nghiệm thu nên vẫn hiển thị
            const isClosedCase = (status: string) => {
              const s = (status || "").toUpperCase();
              return s === "CLOSED" || s === "ĐÃ ĐÓNG" || s === "CANCELLED";
            };
            const openCases = res.data.cases.filter((c) => !isClosedCase(c.status));
            setOpenCasesCount(openCases.length);
            if (openCases.length > 0) {
              // Ưu tiên: Needs Information > Resolved > In Progress
              const needsInfoCase = openCases.find((c) => {
                const s = (c.status || "").toUpperCase();
                return s === "NEEDS INFORMATION" || s === "NEEDS_INFORMATION" || s === "WAITING_CONFIRMATION";
              });
              const resolvedCase = openCases.find((c) => {
                const s = (c.status || "").toUpperCase();
                return s === "RESOLVED" || s === "ĐÃ GIẢI QUYẾT";
              });
              const ongoing = needsInfoCase || resolvedCase || openCases[0];
              setActiveUserCase(ongoing);
            } else {
              setActiveUserCase(null);
            }
          } else {
            setActiveUserCase(null);
            setOpenCasesCount(0);
          }
        })
        .catch(() => {
          setActiveUserCase(null);
          setOpenCasesCount(0);
        });
    } else {
      setActiveUserCase(null);
      setOpenCasesCount(0);
    }
  }, [role, user]);

  // Scroll listener for hero indicator arrow
  useEffect(() => {
    const handleScroll = () => {
      setHasScrolled(window.scrollY > 40);
    };
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  // IntersectionObserver for reveal animations
  useEffect(() => {
    if (typeof window === "undefined") return;
    const elements = document.querySelectorAll(".reveal");
    const observer = new IntersectionObserver(
      (entries, obs) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("in");
            obs.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.08, rootMargin: "0px 0px -30px 0px" }
    );
    elements.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, [articles]);

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

  const handleSubmit = (overrideQuery?: string, overrideModel?: string) => {
    const targetModel = overrideModel || (selectedModel ? selectedModel : "VinFast VF8");
    const activePlaceholder = PLACEHOLDER_EXAMPLES[placeholderIndex] || "Trụ sạc báo đèn đỏ không nhận súng sạc thì xử lý sao?";
    const textToSend =
      overrideQuery ||
      prompt.trim() ||
      (imagePreview ? "Tôi gửi ảnh táp-lô cảnh báo, nhờ Trợ lý AI nhận diện sơ bộ." : activePlaceholder);
    if (!textToSend && !imagePreview) return;

    try {
      sessionStorage.setItem("vf_initial_prompt", textToSend);
      sessionStorage.setItem("vf_initial_model", targetModel);
      if (imagePreview) {
        sessionStorage.setItem("vf_initial_image", imagePreview);
        sessionStorage.setItem("vf_initial_image_name", imageName || "anh_canh_bao.jpg");
      }
    } catch {}

    const queryParams = new URLSearchParams();
    if (textToSend) queryParams.set("prompt", textToSend);
    queryParams.set("model", targetModel.replace("VinFast ", ""));
    router.push(`/chat?${queryParams.toString()}`);
  };

  // Filtered articles
  const filteredArticles = useMemo(() => {
    if (selectedArticleCategory === "ALL") return articles;
    const cat = selectedArticleCategory.toLowerCase();
    return articles.filter((a) => {
      const aCat = a.category.toLowerCase();
      if (cat === "sạc & pin") return aCat.includes("sạc") || aCat.includes("pin");
      return aCat.includes(cat);
    });
  }, [articles, selectedArticleCategory]);

  return (
    <div className="bg-[#F8FAFC] text-slate-900 min-h-screen">
      {/* ─────────────────────────────────────────────────────────
          1. HERO SECTION (TINH TẾ, RÕ HÀNH ĐỘNG, CÓ HOTLINE VÀ SCROLL HINT)
      ───────────────────────────────────────────────────────── */}
      <section className="pt-8 pb-12 md:pt-12 md:pb-16 relative">
        <div className="mx-auto max-w-4xl px-4 sm:px-6 lg:px-8 text-center space-y-4">
          {/* Badge & Mini Greeting theo Role */}
          {role === "CUSTOMER" && user ? (
            <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-white border border-slate-200 shadow-2xs text-[12px] font-medium text-slate-700 animate-fadeIn">
              <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
              <span>
                Xin chào <strong className="text-slate-900">{user.name}</strong> • Chủ xe {user.vehicleModel || "VinFast EV"}
              </span>
            </div>
          ) : (
            <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-white border border-slate-200 shadow-2xs text-[12px] font-medium text-slate-600 animate-fadeIn">
              <span className="h-2 w-2 rounded-full bg-blue-500" />
              <span>Trợ lý Dịch vụ Khách hàng VinFast 24/7</span>
              <span className="text-slate-300">·</span>
              <Link href="/login" className="text-[#1E40AF] font-bold hover:underline">
                Đăng nhập chủ xe ›
              </Link>
            </div>
          )}

          {/* Heading trung tính hơn, thân thiện và bao quát cả 3 nhóm khách */}
          <h1 className="text-3xl sm:text-[38px] font-bold tracking-tight text-slate-900 leading-tight">
            Bạn cần <span className="text-[#1E40AF]">hỗ trợ gì</span> về xe điện?
          </h1>

          <p className="mx-auto max-w-xl text-[13.5px] sm:text-[14px] leading-relaxed text-slate-500">
            Hỏi về sạc, bảo dưỡng, ứng dụng, hoặc báo sự cố xe. Có thể gửi kèm ảnh táp-lô để AI nhận diện sơ bộ.
          </p>

          {/* Floating Prompt Box */}
          <div
            onClick={() => textareaRef.current?.focus()}
            className="mx-auto max-w-2xl rounded-2xl border border-slate-200/90 bg-white p-4 shadow-sm text-left transition-all focus-within:border-[#1E40AF] focus-within:ring-2 focus-within:ring-[#1E40AF]/15 cursor-text"
          >
            {/* Attachment preview if selected */}
            {imagePreview && (
              <div
                onClick={(e) => e.stopPropagation()}
                className="mb-3 flex items-center justify-between rounded-xl border border-blue-200 bg-blue-50/60 p-2 text-[12px] animate-fadeIn cursor-default"
              >
                <div className="flex items-center gap-2 min-w-0">
                  <img src={imagePreview} alt="Preview" className="h-10 w-14 rounded-lg object-cover border border-blue-200 shrink-0" />
                  <div className="min-w-0">
                    <p className="font-semibold text-slate-900 truncate max-w-[200px] sm:max-w-xs">{imageName}</p>
                    <p className="text-[11px] text-[#1E40AF]">Ảnh táp-lô đã sẵn sàng để AI nhận diện sơ bộ</p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={handleClearImage}
                  className="rounded-lg p-1 text-slate-400 hover:bg-white hover:text-red-600 transition"
                  title="Xóa ảnh"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            )}

            {/* Input textarea with rotating placeholder */}
            <textarea
              ref={textareaRef}
              rows={2}
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onFocus={() => setIsPromptFocused(true)}
              onBlur={() => setIsPromptFocused(false)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSubmit();
                }
              }}
              placeholder={PLACEHOLDER_EXAMPLES[placeholderIndex]}
              className="w-full resize-none border-0 border-none bg-transparent p-1 text-[13px] sm:text-[14px] text-slate-900 placeholder-slate-400 outline-none focus:outline-none focus:ring-0 focus-visible:outline-none focus-visible:ring-0 shadow-none leading-relaxed transition-all"
            />

            {/* Bottom Toolbar: Upload button, Submit button */}
            <div
              onClick={(e) => e.stopPropagation()}
              className="mt-2.5 flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 pt-3 cursor-default"
            >
              <div className="flex items-center gap-2 flex-wrap">
                {/* Upload Image button */}
                <label
                  className="inline-flex cursor-pointer items-center gap-1.5 rounded-xl border border-slate-200 bg-slate-50 px-3 py-1.5 text-[12px] font-medium text-slate-700 hover:bg-white hover:border-[#1E40AF] transition shadow-2xs"
                  title="Tải ảnh"
                >
                  <ImagePlus className="h-4 w-4 text-[#1E40AF]" />
                  <span className="hidden sm:inline">Tải ảnh</span>
                  <input
                    type="file"
                    accept="image/*"
                    onChange={handleImageSelect}
                    className="sr-only"
                  />
                </label>
              </div>

              {/* Action Submit: Đổi 'Gửi yêu cầu' thành 'Hỏi trợ lý' */}
              <button
                type="button"
                onClick={() => handleSubmit()}
                className="inline-flex items-center gap-1.5 rounded-xl bg-[#1E40AF] hover:bg-[#1D4ED8] px-4 py-2 text-[12.5px] font-semibold text-white shadow-2xs transition active:scale-[0.98]"
              >
                <span>Hỏi trợ lý</span>
                <ArrowRight className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>

          {/* Quick Prompt Chips: Cân bằng cả Sự cố, Bảo dưỡng, Tra cứu, Hướng dẫn app */}
          <div className="text-left max-w-2xl mx-auto pt-1">
            <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-slate-400 mb-2">
              <Sparkles className="h-3.5 w-3.5 text-[#1E40AF]" />
              <span>Gợi ý theo nhu cầu:</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {QUICK_PROMPTS.map((qp, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => handleSubmit(qp.text, qp.model)}
                  className="inline-flex items-center gap-1.5 rounded-full border border-slate-200/90 bg-white px-3 py-1.5 text-[11.5px] font-medium text-slate-700 shadow-2xs hover:border-blue-300 hover:bg-blue-50/70 hover:text-[#1E40AF] transition active:scale-[0.98]"
                >
                  <span className="text-[12px] opacity-80">{qp.icon}</span>
                  <span>{qp.label}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Hotline khẩn cấp ngay dưới Hero */}
          <div className="pt-2 text-[12px] text-slate-500 flex items-center justify-center gap-2 flex-wrap">
            <span>Khẩn cấp trên đường?</span>
            <a
              href="tel:1900232389"
              className="inline-flex items-center gap-1 font-bold text-red-600 hover:text-red-700 hover:underline"
            >
              <PhoneCall className="w-3.5 h-3.5" />
              <span>Gọi Cứu hộ 24/7: 1900-232389</span>
            </a>
            <span className="text-slate-300">•</span>
            <span className="text-slate-400">Hỗ trợ toàn bộ dòng xe điện VinFast</span>
          </div>

          {/* Gợi ý cuộn xuống (Tự ẩn khi cuộn) */}
          <div
            className={`pt-6 transition-all duration-300 ${
              hasScrolled ? "opacity-0 pointer-events-none translate-y-2" : "opacity-100"
            }`}
          >
            <a
              href="#issue-categories"
              className="inline-flex flex-col items-center text-[11px] font-medium text-slate-400 hover:text-[#1E40AF] transition"
            >
              <span>Cuộn để khám phá</span>
              <ChevronDown className="w-4 h-4 animate-bounce mt-1" />
            </a>
          </div>
        </div>
      </section>


      {/* ─────────────────────────────────────────────────────────
          3. HÀNG 4 THẺ NGANG CHO NHÓM SỰ CỐ (TINH GỌN, KHÔNG DÀI DÒNG)
      ───────────────────────────────────────────────────────── */}
      <section id="issue-categories" className="py-14 sm:py-18 border-t border-slate-200/80 bg-white scroll-mt-14">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8 space-y-6">
          {/* Header nhóm */}
          <div className="text-center max-w-xl mx-auto space-y-1.5 reveal">
            <span className="inline-block px-2.5 py-0.5 rounded-full bg-blue-50 text-[#1E40AF] text-[11px] font-bold uppercase tracking-wider">
              Khởi đầu nhanh
            </span>
            <h2 className="text-2xl sm:text-[26px] font-bold tracking-tight text-slate-900">
              Chủ đề hỗ trợ thường gặp
            </h2>
            <p className="text-[13px] text-slate-500">
              Chọn nhanh tình huống xe của bạn để chuyển thẳng vào câu hỏi trong Trợ lý Chat.
            </p>
          </div>

          {/* Lưới 4 Thẻ Ngang Nhỏ (Horizontal cards) */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
            {ISSUE_CATEGORIES.map((cat, idx) => {
              const Icon = cat.icon;
              return (
                <button
                  key={cat.id}
                  type="button"
                  onClick={() => handleSubmit(cat.query, cat.model)}
                  style={{ transitionDelay: `${idx * 60}ms` }}
                  className="reveal group text-left p-3.5 sm:p-4 rounded-2xl border border-slate-200/80 bg-slate-50/60 hover:bg-white hover:border-blue-300 shadow-2xs hover:shadow-sm transition-all flex items-center justify-between gap-3 active:scale-[0.98]"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="w-10 h-10 rounded-xl bg-white border border-slate-200 flex items-center justify-center text-[#1E40AF] group-hover:bg-[#1E40AF] group-hover:text-white transition shrink-0 shadow-2xs">
                      <Icon className="w-5 h-5" />
                    </div>
                    <div className="min-w-0">
                      <h3 className="text-[13.5px] font-bold text-slate-900 group-hover:text-[#1E40AF] transition truncate">
                        {cat.title}
                      </h3>
                      <p className="text-[11.5px] text-slate-500 truncate mt-0.5">
                        {cat.desc}
                      </p>
                    </div>
                  </div>

                  <div className="w-6 h-6 rounded-full flex items-center justify-center text-slate-300 group-hover:text-[#1E40AF] group-hover:translate-x-0.5 transition shrink-0">
                    <ChevronRight className="w-4 h-4" />
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      </section>

      {/* ─────────────────────────────────────────────────────────
          4. KHỐI CHIA ĐÔI CHO QUY TRÌNH: TRÁI 4 BƯỚC — PHẢI HỒ SƠ MẪU NỔI
      ───────────────────────────────────────────────────────── */}
      <section className="py-16 sm:py-20 border-t border-slate-200/80 bg-[#F8FAFC]">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-12 items-center">
            {/* Cột trái: 4 bước 1 dòng */}
            <div className="lg:col-span-6 space-y-5 reveal">
              <div>
                <span className="px-2.5 py-0.5 rounded-full bg-blue-50 text-[#1E40AF] text-[11px] font-bold uppercase tracking-wider">
                  Minh bạch & Chuẩn hóa
                </span>
                <h2 className="mt-2 text-2xl sm:text-[28px] font-bold tracking-tight text-slate-900 leading-tight">
                  Tiếp nhận & Xử lý trong 4 bước
                </h2>
                <p className="mt-1.5 text-[13px] text-slate-500 leading-relaxed">
                  Mỗi sự cố kỹ thuật đều có quy trình đối soát cẩm nang chính hãng và sự phê duyệt của chuyên viên xưởng VinFast.
                </p>
              </div>

              {/* 4 bước rút gọn dạng list mỏng */}
              <div className="space-y-3 pt-1">
                {[
                  { num: "01", title: "Gửi mô tả hoặc ảnh táp-lô", desc: "Nhập triệu chứng xe hoặc chụp đèn báo táp-lô để AI đọc mã sơ bộ." },
                  { num: "02", title: "AI đối soát cẩm nang kỹ thuật", desc: "Hỏi 1-2 câu bối cảnh nhanh, tra cứu tài liệu vận hành chính hãng." },
                  { num: "03", title: "Phân loại ưu tiên & Tạo hồ sơ", desc: "Chuẩn hóa dữ kiện sự cố, cấp mã Case ID theo dõi thời gian thực." },
                  { num: "04", title: "Chuyên viên xác nhận & Xử lý", desc: "Kỹ thuật viên xưởng tiếp nhận, cử cứu hộ hoặc hẹn thợ xử lý dứt điểm." },
                ].map((s) => (
                  <div key={s.num} className="flex items-start gap-3 p-2.5 rounded-xl hover:bg-white transition border border-transparent hover:border-slate-200/60">
                    <span className="font-mono text-[12px] font-bold text-[#1E40AF] px-2 py-0.5 rounded-md bg-blue-50 shrink-0 mt-0.5">
                      {s.num}
                    </span>
                    <div className="text-[12.5px]">
                      <strong className="text-slate-900 font-bold block">{s.title}</strong>
                      <span className="text-slate-500 text-[12px]">{s.desc}</span>
                    </div>
                  </div>
                ))}
              </div>

              <div className="pt-2">
                <Link
                  href="/chat"
                  className="inline-flex items-center gap-2 rounded-xl bg-[#1E40AF] hover:bg-[#1D4ED8] px-5 py-2.5 text-[13px] font-semibold text-white shadow-2xs transition active:scale-[0.98]"
                >
                  <span>Bắt đầu gửi yêu cầu</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </div>
            </div>

            {/* Cột phải: Khối thẻ hồ sơ mẫu có Stepper NỔI (Chiều sâu thị giác) */}
            <div className="lg:col-span-6 reveal">
              <div className="relative rounded-3xl bg-gradient-to-br from-blue-50/80 via-slate-100 to-indigo-50/60 p-6 sm:p-8 border border-blue-100/80 shadow-xs">
                {/* Badge góc */}
                <div className="flex items-center justify-between text-[11.5px] mb-4">
                  <span className="font-bold text-[#1E40AF] flex items-center gap-1">
                    <ScanLine className="w-3.5 h-3.5" /> Mô phỏng hồ sơ thực tế
                  </span>
                  <span className="text-emerald-700 bg-emerald-100/70 font-semibold px-2 py-0.2 rounded-full text-[10.5px]">
                    Cập nhật thời gian thực
                  </span>
                </div>

                {/* Thẻ trắng nổi (Floating Card) */}
                <div className="bg-white rounded-2xl p-5 border border-slate-200/90 shadow-md space-y-4">
                  {/* Case Header */}
                  <div className="flex items-start justify-between gap-3 border-b border-slate-100 pb-3">
                    <div>
                      <span className="font-mono text-[11px] font-bold text-slate-500 bg-slate-100 px-2 py-0.5 rounded">
                        CASE-20260924-001
                      </span>
                      <h4 className="text-[14px] font-bold text-slate-900 mt-1.5 leading-snug">
                        Lỗi sạc trụ P02 không vào điện DC (Mã CC01)
                      </h4>
                      <p className="text-[11.5px] text-slate-400 mt-0.5 flex items-center gap-1">
                        <Car className="w-3.5 h-3.5 text-[#1E40AF]" />
                        <span>VinFast VF8 Plus · Pin 18%</span>
                      </p>
                    </div>

                    <span className="shrink-0 px-2.5 py-1 rounded-full text-[11px] font-semibold bg-blue-50 text-[#1E40AF] border border-blue-200">
                      Đang xử lý
                    </span>
                  </div>

                  {/* Stepper 4 bước thu nhỏ */}
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between text-[11px] text-slate-500 font-semibold">
                      <span>Tiến trình xử lý kỹ thuật</span>
                      <span className="text-[#1E40AF]">Bước 3/4</span>
                    </div>

                    <div className="grid grid-cols-4 gap-1.5 pt-1 text-center">
                      {[
                        { step: 1, title: "Tiếp nhận", done: true },
                        { step: 2, title: "Làm rõ", done: true },
                        { step: 3, title: "Xử lý", current: true },
                        { step: 4, title: "Hoàn tất" },
                      ].map((st) => (
                        <div key={st.step} className="flex flex-col items-center">
                          <div
                            className={`h-6 w-full rounded-md flex items-center justify-center text-[10px] font-bold transition ${
                              st.done
                                ? "bg-emerald-500 text-white"
                                : st.current
                                ? "bg-[#1E40AF] text-white ring-2 ring-blue-100"
                                : "bg-slate-100 text-slate-400"
                            }`}
                          >
                            {st.done ? "✓" : st.step}
                          </div>
                          <span className={`text-[10px] mt-1 ${st.current ? "font-bold text-[#1E40AF]" : "text-slate-500"}`}>
                            {st.title}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Bước tiếp theo nổi bật */}
                  <div className="p-3 rounded-xl bg-blue-50/90 border border-blue-200 text-[12px] text-blue-950 flex items-start gap-2">
                    <Sparkles className="w-4 h-4 text-[#1E40AF] shrink-0 mt-0.5" />
                    <div>
                      <strong className="block text-[11px] uppercase tracking-wide text-[#1E40AF]">Bước tiếp theo:</strong>
                      <span className="font-medium">Kỹ thuật viên trạm đang kiểm tra trụ P02. Dự kiến phản hồi trong ít phút.</span>
                    </div>
                  </div>

                  {/* Cập nhật trao đổi */}
                  <div className="pt-1 text-[11.5px] text-slate-600 flex items-center justify-between">
                    <span className="text-slate-400 font-mono">15:35 · KTV trạm: Đang ping kiểm tra module trụ...</span>
                    <Link href="/track-case" className="text-[#1E40AF] font-bold hover:underline">
                      Tra cứu →
                    </Link>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ─────────────────────────────────────────────────────────
          5. HAI KHỐI MÀU LỚN CHIA THEO 2 TÌNH HUỐNG (HIGH CONTRAST)
      ───────────────────────────────────────────────────────── */}
      <section className="py-14 sm:py-18 border-t border-slate-200/80 bg-white">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8 space-y-6">
          <div className="text-center max-w-xl mx-auto space-y-1.5 reveal">
            <span className="inline-block px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-700 text-[11px] font-bold uppercase tracking-wider">
              Hỗ trợ đúng lúc
            </span>
            <h2 className="text-2xl sm:text-[26px] font-bold tracking-tight text-slate-900">
              Chọn cách hỗ trợ phù hợp với bạn
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {/* Khối 1: Xe đang gặp sự cố, cần cứu hộ ngay (Nền tối / Đỏ sang trọng) */}
            <div className="reveal rounded-3xl bg-gradient-to-br from-slate-950 via-slate-900 to-red-950 text-white p-7 sm:p-8 flex flex-col justify-between border border-red-900/40 shadow-sm relative overflow-hidden">
              <div className="space-y-3 relative z-10">
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-red-600/30 text-red-300 border border-red-500/30 text-[11px] font-bold uppercase tracking-wider">
                  <PhoneCall className="w-3 h-3 text-red-400" />
                  Cứu hộ khẩn cấp 24/7
                </span>

                <h3 className="text-xl sm:text-[22px] font-bold text-white leading-snug">
                  Xe chết máy hoặc gặp sự cố trên cao tốc?
                </h3>

                <p className="text-[13px] text-slate-300 leading-relaxed">
                  Đội cứu hộ phản ứng nhanh VinFast túc trực 24/7 toàn quốc. Hãy bật ngay đèn khẩn cấp hazard, tấp vào lề an toàn và đứng sau rào hộ lan.
                </p>
              </div>

              <div className="pt-6 relative z-10">
                <a
                  href="tel:1900232389"
                  className="inline-flex items-center justify-center gap-2 w-full sm:w-auto px-5 py-3 rounded-xl bg-red-600 hover:bg-red-700 text-white font-bold text-[13px] shadow-sm transition active:scale-[0.98]"
                >
                  <PhoneCall className="w-4 h-4" />
                  <span>Gọi Hotline Cứu hộ: 1900-232389</span>
                </a>
                <p className="text-[11px] text-slate-400 mt-2">
                  Miễn phí cuộc gọi • Điều phối cẩu kéo và sạc pin lưu động tức thời
                </p>
              </div>
            </div>

            {/* Khối 2: Hỏi về lỗi kỹ thuật, cẩm nang, bảo dưỡng (Nền xanh Deep Indigo) */}
            <div className="reveal rounded-3xl bg-gradient-to-br from-[#1E40AF] via-[#1D4ED8] to-[#1E3A8A] text-white p-7 sm:p-8 flex flex-col justify-between shadow-sm relative overflow-hidden">
              <div className="space-y-3 relative z-10">
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/20 text-blue-100 border border-white/20 text-[11px] font-bold uppercase tracking-wider">
                  <Sparkles className="w-3 h-3 text-white" />
                  Trợ lý Kỹ thuật AI
                </span>

                <h3 className="text-xl sm:text-[22px] font-bold text-white leading-snug">
                  Cần tra cứu cẩm nang, đèn táp-lô hoặc lịch bảo dưỡng?
                </h3>

                <p className="text-[13px] text-blue-100 leading-relaxed">
                  Giải đáp chi tiết về biểu tượng lạ trên màn hình, cách xử lý trụ sạc không vào điện, định mức bảo dưỡng 12.000km đối chiếu từ tài liệu chính hãng.
                </p>
              </div>

              <div className="pt-6 relative z-10">
                <Link
                  href="/chat"
                  className="inline-flex items-center justify-center gap-2 w-full sm:w-auto px-5 py-3 rounded-xl bg-white hover:bg-blue-50 text-[#1E40AF] font-bold text-[13px] shadow-sm transition active:scale-[0.98]"
                >
                  <MessageSquare className="w-4 h-4" />
                  <span>Chat với Trợ lý AI ngay</span>
                  <ArrowRight className="w-4 h-4" />
                </Link>
                <p className="text-[11px] text-blue-200 mt-2">
                  Hỗ trợ tra cứu thông tin kỹ thuật &amp; chính sách 24/7
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ─────────────────────────────────────────────────────────
          6. KNOWLEDGE HUB: CẨM NANG & CHÍNH SÁCH KIỂM CHỨNG (PUB-01)
      ───────────────────────────────────────────────────────── */}
      <section id="knowledge-hub" className="py-16 sm:py-20 border-t border-slate-200/80 bg-[#F8FAFC] scroll-mt-14">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8 space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 reveal">
            <div>
              <span className="px-2.5 py-0.5 rounded-full bg-blue-50 text-[#1E40AF] text-[11px] font-bold uppercase tracking-wider flex items-center gap-1.5 w-fit">
                <BookOpen className="h-3.5 w-3.5" /> Nguồn chính thức VinFast
              </span>
              <h2 className="mt-2 text-2xl sm:text-[26px] font-bold tracking-tight text-slate-900">
                Cẩm nang kỹ thuật & Chính sách đã kiểm chứng
              </h2>
              <p className="mt-1 text-[13px] text-slate-500">
                Tài liệu chính thức được AI đối soát khi phản hồi và hỗ trợ chẩn đoán cho khách hàng.
              </p>
            </div>

            {/* Filter Pills */}
            <div className="flex items-center gap-1.5 flex-wrap">
              {[
                { id: "ALL", label: "Tất cả" },
                { id: "Sạc & Pin", label: "Sạc & Pin" },
                { id: "Vận hành", label: "Vận hành" },
                { id: "Bảo dưỡng", label: "Bảo dưỡng" },
                { id: "Cứu hộ", label: "Cứu hộ" },
                { id: "Bảo hành", label: "Bảo hành" },
              ].map((c) => (
                <button
                  key={c.id}
                  type="button"
                  onClick={() => setSelectedArticleCategory(c.id)}
                  className={`px-3 py-1 rounded-lg text-[12px] font-medium transition ${
                    selectedArticleCategory === c.id
                      ? "bg-[#1E40AF] text-white font-semibold shadow-2xs"
                      : "bg-white text-slate-600 hover:bg-slate-100 border border-slate-200"
                  }`}
                >
                  {c.label}
                </button>
              ))}
            </div>
          </div>

          {/* Grid Cẩm nang Widget Cao Cấp */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filteredArticles.map((art, idx) => (
              <div
                key={art.id}
                style={{ transitionDelay: `${idx * 60}ms` }}
                className="reveal group rounded-2xl border border-slate-200/80 bg-white p-5 shadow-2xs hover:border-blue-300 hover:shadow-xs transition-all flex flex-col justify-between space-y-3"
              >
                <div className="space-y-2">
                  <div className="flex items-center justify-between gap-2">
                    <span className="rounded-full bg-blue-50 px-2.5 py-0.5 text-[11px] font-bold text-[#1E40AF] border border-blue-200/60">
                      {art.category}
                    </span>
                    <span className="font-mono text-[11px] text-slate-400">
                      Kiểm chứng: {art.verified_at}
                    </span>
                  </div>

                  <h3 className="text-[14.5px] font-bold text-slate-900 group-hover:text-[#1E40AF] transition leading-snug">
                    {art.title}
                  </h3>

                  <p className="text-[12.5px] leading-relaxed text-slate-500">
                    {art.summary}
                  </p>
                </div>

                <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-[12px]">
                  <a
                    href={art.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 font-semibold text-slate-500 hover:text-[#1E40AF] transition"
                  >
                    <ExternalLink className="h-3.5 w-3.5" />
                    <span>Xem tài liệu gốc</span>
                  </a>

                  <button
                    type="button"
                    onClick={() => handleSubmit(`Cho tôi hỏi về: ${art.title}`)}
                    className="inline-flex items-center gap-1 text-[11.5px] font-bold text-[#1E40AF] hover:underline"
                  >
                    <span>Hỏi AI về mục này</span>
                    <ArrowRight className="h-3 w-3" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ─────────────────────────────────────────────────────────
          7. DẢI TIN CẬY (3 Ý MỘT DÒNG, TIẾNG THƯỜNG KHÔNG JARGON)
      ───────────────────────────────────────────────────────── */}
      <section className="py-10 border-t border-slate-200/80 bg-white">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-center md:text-left">
            <div className="reveal space-y-1">
              <div className="flex items-center justify-center md:justify-start gap-2 text-slate-900 font-bold text-[14px]">
                <ShieldCheck className="w-4 h-4 text-emerald-600" />
                <span>Bảo mật dữ liệu riêng tư</span>
              </div>
              <p className="text-[12px] text-slate-500 leading-relaxed">
                Tự động mã hóa thông tin cá nhân. Chỉ lưu trữ các dữ kiện kỹ thuật xe phục vụ chẩn đoán.
              </p>
            </div>

            <div className="reveal space-y-1" style={{ transitionDelay: "80ms" }}>
              <div className="flex items-center justify-center md:justify-start gap-2 text-slate-900 font-bold text-[14px]">
                <CheckCircle2 className="w-4 h-4 text-[#1E40AF]" />
                <span>Tài liệu kiểm chứng 100%</span>
              </div>
              <p className="text-[12px] text-slate-500 leading-relaxed">
                Mọi chỉ dẫn kỹ thuật đều trích xuất trực tiếp từ cẩm nang an toàn và vận hành VinFast chính hãng.
              </p>
            </div>

            <div className="reveal space-y-1" style={{ transitionDelay: "160ms" }}>
              <div className="flex items-center justify-center md:justify-start gap-2 text-slate-900 font-bold text-[14px]">
                <Wrench className="w-4 h-4 text-[#1E40AF]" />
                <span>Kỹ thuật viên đồng hành</span>
              </div>
              <p className="text-[12px] text-slate-500 leading-relaxed">
                Mọi sự cố xe đều được Cố vấn Dịch vụ xem xét, phê duyệt phương án trước khi điều phối xưởng.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ─────────────────────────────────────────────────────────
          8. DẢI CTA CUỐI NỀN TỐI (DARK BAND CTA)
      ───────────────────────────────────────────────────────── */}
      <section className="py-12 px-4 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-5xl rounded-3xl bg-slate-950 text-white p-8 sm:p-12 text-center space-y-5 shadow-lg relative overflow-hidden reveal">
          <div className="space-y-2 relative z-10">
            <h2 className="text-2xl sm:text-[30px] font-bold tracking-tight text-white leading-tight">
              Sẵn sàng đồng hành cùng bạn trên mọi nẻo đường
            </h2>
            <p className="mx-auto max-w-lg text-[13.5px] text-slate-300 leading-relaxed">
              Trợ lý VF Serv AI túc trực 24/7 để tiếp nhận, hỗ trợ và kết nối kỹ thuật viên giải quyết sự cố tức thời.
            </p>
          </div>

          <div className="pt-2 flex flex-col sm:flex-row items-center justify-center gap-3 relative z-10">
            <Link
              href="/chat"
              className="inline-flex items-center justify-center gap-2 w-full sm:w-auto rounded-xl bg-[#1E40AF] hover:bg-[#1D4ED8] px-6 py-3 text-[13px] font-bold text-white shadow-sm transition active:scale-[0.98]"
            >
              <MessageSquare className="w-4 h-4" />
              <span>Bắt đầu trò chuyện với AI</span>
            </Link>

            <a
              href="tel:1900232389"
              className="inline-flex items-center justify-center gap-2 w-full sm:w-auto rounded-xl border border-slate-700 bg-white/5 hover:bg-white/10 px-6 py-3 text-[13px] font-semibold text-white transition"
            >
              <PhoneCall className="w-4 h-4 text-red-400" />
              <span>Gọi Cứu hộ 24/7: 1900-232389</span>
            </a>
          </div>
        </div>
      </section>
      {/* ─────────────────────────────────────────────────────────
          BONG BÓNG THEO DÕI HỒ SƠ NỔI (DESKTOP: PILL/CARD GÓC PHẢI; MOBILE: THANH MỎNG DƯỚI CÙNG)
      ───────────────────────────────────────────────────────── */}
      {/* ─────────────────────────────────────────────────────────
          BONG BÓNG THEO DÕI HỒ SƠ NỔI (DESKTOP: PILL/CARD GÓC PHẢI; MOBILE: THANH MỎNG DƯỚI CÙNG)
      ───────────────────────────────────────────────────────── */}
      {role === "CUSTOMER" && activeUserCase && bubbleConfig && (
        <>
          {/* Màn hình lớn (Desktop / Tablet >= sm): Bong bóng góc dưới phải */}
          <aside
            aria-label="Thông báo hồ sơ đang xử lý"
            className={`hidden sm:block fixed bottom-6 right-6 z-40 transition-all duration-300 ease-out motion-reduce:transition-none motion-reduce:transform-none ${
              isBubbleMounted
                ? "opacity-100 translate-y-0 translate-x-0"
                : "opacity-0 translate-y-4 translate-x-2 pointer-events-none"
            }`}
          >
            {isCaseBubbleExpanded ? (
              /* Thẻ mở rộng rút gọn đúng 2 dòng, cả thẻ bấm được */
              <div className={`relative group w-[340px] rounded-2xl border p-3 shadow-xl backdrop-blur-md transition-all hover:shadow-2xl ${bubbleConfig.cardClass}`}>
                <Link
                  href="/track-case"
                  className="block text-left pr-6 cursor-pointer focus:outline-none"
                  title="Bấm để xem chi tiết tiến trình hồ sơ"
                >
                  {/* Dòng 1: ● Badge trạng thái · Phụ đề hướng dẫn */}
                  <div className="flex items-center gap-1.5 min-w-0">
                    <span className="relative flex h-2 w-2 shrink-0">
                      <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${bubbleConfig.dotPing}`} />
                      <span className={`relative inline-flex rounded-full h-2 w-2 ${bubbleConfig.dotBg}`} />
                    </span>
                    <span className="text-[12px] font-bold text-slate-900 shrink-0">
                      {bubbleConfig.badgeText}
                    </span>
                    <span className="text-slate-300">·</span>
                    <span className={`text-[11.5px] truncate ${bubbleConfig.ctaColor}`}>
                      {bubbleConfig.subtitle}
                    </span>
                  </div>

                  {/* Dòng 2: Tóm tắt sự cố … Xem / Bổ sung / Nghiệm thu › */}
                  <div className="mt-1 flex items-center justify-between gap-2 text-[12px] text-slate-600">
                    <p className="truncate min-w-0 font-normal">
                      {activeUserCase.summary || activeUserCase.id}
                    </p>
                    <span className={`inline-flex items-center gap-0.5 text-[11.5px] font-bold shrink-0 group-hover:translate-x-0.5 transition ${bubbleConfig.ctaColor}`}>
                      <span>{bubbleConfig.ctaText}</span>
                      <ChevronRight className="h-3 w-3" />
                    </span>
                  </div>
                </Link>

                {/* Nút đóng (x): Thu về dạng pill, không biến mất hẳn, lưu sessionStorage */}
                <button
                  type="button"
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    handleCollapseBubble();
                  }}
                  className="absolute top-2.5 right-2.5 rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition"
                  title="Thu gọn về dạng viên thuốc"
                  aria-label="Thu gọn"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </div>
            ) : (
              /* Dạng thu gọn mặc định (Pill): Không chiếm tầm nhìn của Hero hay Hotline */
              <button
                type="button"
                onClick={handleExpandBubble}
                onMouseEnter={handleExpandBubble}
                className={`group relative flex items-center gap-2 rounded-full border px-3.5 py-2 shadow-lg backdrop-blur-md hover:shadow-xl transition-all ${bubbleConfig.pillClass}`}
                title="Rê chuột hoặc bấm để xem chi tiết hồ sơ"
              >
                {/* Ping chấm màu theo trạng thái */}
                <span className="relative flex h-2 w-2 shrink-0">
                  <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${bubbleConfig.dotPing}`} />
                  <span className={`relative inline-flex rounded-full h-2 w-2 ${bubbleConfig.dotBg}`} />
                </span>

                {/* Chấm đỏ nhỏ khi có cập nhật mới từ nhân viên KTV hoặc khi Cần bổ sung */}
                {(hasStaffUpdate || bubbleConfig.type === "NEEDS_INFO") && (
                  <span
                    className="absolute -top-0.5 -right-0.5 h-2.5 w-2.5 rounded-full bg-red-500 ring-2 ring-white animate-pulse"
                    title={bubbleConfig.type === "NEEDS_INFO" ? "Cần bổ sung thông tin" : "Có phản hồi mới từ kỹ thuật viên"}
                  />
                )}

                <span className="text-[12px] font-bold">
                  {bubbleConfig.pillText}
                </span>

                {openCasesCount > 1 && bubbleConfig.type === "IN_PROGRESS" && (
                  <span className="px-1.5 py-0.2 rounded-full bg-blue-100 text-[#1E40AF] text-[10px] font-bold">
                    {openCasesCount}
                  </span>
                )}

                <ChevronRight className="h-3.5 w-3.5 text-slate-400 group-hover:translate-x-0.5 transition" />
              </button>
            )}
          </aside>

          {/* Màn hình hẹp (< sm / Mobile): Thanh mỏng cố định phía dưới, không dùng thẻ nổi che màn hình */}
          <aside
            aria-label="Hồ sơ đang xử lý trên di động"
            className={`sm:hidden fixed bottom-0 left-0 right-0 z-40 border-t px-3.5 py-2 backdrop-blur-md shadow-[0_-4px_16px_rgba(0,0,0,0.06)] transition-all duration-300 ease-out motion-reduce:transition-none motion-reduce:transform-none ${bubbleConfig.mobileClass} ${
              isBubbleMounted
                ? "opacity-100 translate-y-0"
                : "opacity-0 translate-y-full pointer-events-none"
            }`}
          >
            <Link
              href="/track-case"
              className="flex items-center justify-between gap-2 text-left w-full focus:outline-none"
            >
              <div className="flex items-center gap-2 min-w-0">
                <span className="relative flex h-2 w-2 shrink-0">
                  <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${bubbleConfig.dotPing}`} />
                  <span className={`relative inline-flex rounded-full h-2 w-2 ${bubbleConfig.dotBg}`} />
                </span>
                {(hasStaffUpdate || bubbleConfig.type === "NEEDS_INFO") && (
                  <span className="h-2 w-2 rounded-full bg-red-500 shrink-0 animate-pulse" />
                )}
                <div className="min-w-0">
                  <p className="text-[11.5px] font-bold text-slate-900 truncate">
                    {bubbleConfig.badgeText} · {bubbleConfig.subtitle}
                  </p>
                  <p className="text-[10.5px] text-slate-500 truncate">
                    {activeUserCase.summary || activeUserCase.id}
                  </p>
                </div>
              </div>

              <div className={`flex items-center gap-0.5 text-[11.5px] font-bold shrink-0 ${bubbleConfig.ctaColor}`}>
                <span>{bubbleConfig.ctaText}</span>
                <ChevronRight className="h-3.5 w-3.5" />
              </div>
            </Link>
          </aside>
        </>
      )}
    </div>
  );
}
