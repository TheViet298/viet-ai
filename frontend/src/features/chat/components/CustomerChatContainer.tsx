"use client";
import { useLocale } from "@/features/shared/context/LocaleContext";

import {
  Car,
  FileImage,
  RotateCcw,
  ScanLine,
  ShieldCheck,
  PhoneCall,
  ArrowRight,
  ExternalLink,
  MapPin,
  Map,
  Compass,
  Plus,
  PanelLeft,
  History,
} from "lucide-react";
import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { UserLocationState } from "../types";
import { useChat } from "../hooks/useChat";
import { EmergencyAlertBanner } from "./EmergencyAlertBanner";
import { ChatFeed } from "./ChatFeed";
import { ChatInputBar } from "./ChatInputBar";
import { LocationConsentCard } from "./LocationConsentCard";
import { ServiceMapPanel } from "./ServiceMapPanel";
import { ChatHistorySidebar } from "./ChatHistorySidebar";
import { getAiSystemStatus, uploadAttachment } from "../api/chatApi";
import { getUploadError } from "../uploadState";
import { ServMascot, type ServStatus } from "@/features/shared/components/serv/ServMascot";
import { useAuth } from "@/features/shared";

export function CustomerChatContainer() {
  const { user, isReady } = useAuth();
  if (!isReady) return null;
  return <CustomerChatSession key={user?.id || "guest"} />;
}

function CustomerChatSession() {
  const { t } = useLocale();
  const servInputRef = useRef<HTMLTextAreaElement>(null);
  const { user, role } = useAuth();
  const {
    guestLimitReached,
    messages,
    input,
    setInput,
    loading,
    sessionId,
    currentCaseId,
    criticalBanner,
    criticalBannerDismissed,
    dismissCriticalBanner,
    restoreCriticalBanner,
    safetyPending,
    safetyError,
    canAcknowledgeSafety,
    requestLocation,
    sendMessage,
    resetChat,
    loadSession,
    updateMessageChips,
  } = useChat({
    userName: user?.name,
  });

  const [isSidebarOpen, setIsSidebarOpen] = useState<boolean>(() => {
    if (typeof window === "undefined") return true;
    try {
      const saved = localStorage.getItem("vf_chat_sidebar_open");
      return saved !== null ? saved === "true" : true;
    } catch {
      return true;
    }
  });

  const handleToggleSidebar = (open: boolean) => {
    setIsSidebarOpen(open);
    try {
      localStorage.setItem("vf_chat_sidebar_open", String(open));
    } catch {}
  };

  const [isMobileDrawerOpen, setIsMobileDrawerOpen] = useState<boolean>(false);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [imageName, setImageName] = useState<string | null>(null);
  const [uploadedAttachmentId, setUploadedAttachmentId] = useState<string | null>(null);
  const [isUploadingImage, setIsUploadingImage] = useState<boolean>(false);
  const [resolvedImageKind, setResolvedImageKind] = useState<"dashboard" | "charger" | "exterior" | null>(null);
  const [imageUploadError, setImageUploadError] = useState<string | null>(null);
  const [isModalBlockingChat, setIsModalBlockingChat] = useState<boolean>(false);
  const uploadRequestId = useRef(0);
  const hasSentInitialPrompt = useRef(false);
  const [aiStatus, setAiStatus] = useState<string>("Trợ lý VFServ • Hỗ trợ dịch vụ xe điện VinFast");

  // ===========================================================================
  // SERVICE MAP PREVIEW & LOCATION CONSENT (ADR-005, screen-spec.md Section 5.4, CUS-03)
  // ===========================================================================
  const [locationState, setLocationState] = useState<UserLocationState>({
    status: "PENDING",
    source: "USER_TEXT",
    label: "",
  });
  const [isLocating, setIsLocating] = useState<boolean>(false);
  const [isMapOpen, setIsMapOpen] = useState<boolean>(false);
  const [selectedPointId, setSelectedPointId] = useState<string | null>(null);
  const [showLocationCard, setShowLocationCard] = useState<boolean>(false);
  const [suggestedCategory, setSuggestedCategory] = useState<
    "ALL" | "EXPRESSWAY_RESCUE" | "CHARGING_STATION" | "SERVICE_WORKSHOP"
  >("ALL");

  // Tự động kích hoạt Card xin vị trí khi phát hiện ca khẩn cấp hoặc backend gửi cờ request_location
  useEffect(() => {
    if (criticalBanner || requestLocation) {
      setShowLocationCard(true);
      if (criticalBanner) {
        setSuggestedCategory("EXPRESSWAY_RESCUE");
      } else {
        setSuggestedCategory("CHARGING_STATION");
      }
    }
  }, [criticalBanner, requestLocation]);

  const handleResetAll = () => {
    setResolvedImageKind(null);
    uploadRequestId.current += 1;
    setIsUploadingImage(false);
    setImageUploadError(null);
    resetChat();
    setImagePreview(null);
    setImageName(null);
    setUploadedAttachmentId(null);
    setIsMapOpen(false);
    setShowLocationCard(false);
    setSuggestedCategory("ALL");
    setSelectedPointId(null);
    setLocationState({
      status: "PENDING",
      source: "USER_TEXT",
      label: "",
    });
  };

  // Load AI System Status from /api/v1/status
  useEffect(() => {
    getAiSystemStatus()
      .then((res) => {
        if (res?.status === "ready") {
          setAiStatus("Trợ lý VFServ • Sẵn sàng hỗ trợ");
        }
      })
      .catch(() => { });
  }, []);

  // Pre-load draft or auto-send prompt from Landing Hero or URL if available
  useEffect(() => {
    if (hasSentInitialPrompt.current) return;

    try {
      // 1. Đọc prompt từ URL hoặc sessionStorage
      const urlParams = typeof window !== "undefined" ? new URLSearchParams(window.location.search) : null;
      const urlPrompt = urlParams?.get("prompt");
      const savedPrompt = urlPrompt || sessionStorage.getItem("vf_initial_prompt");
      const savedImg = sessionStorage.getItem("vf_initial_image");
      const savedImgName = sessionStorage.getItem("vf_initial_image_name");

      // 2. Xóa ngay lập tức khỏi sessionStorage và URL TRƯỚC KHI gửi (tránh F5 gửi lại)
      sessionStorage.removeItem("vf_initial_prompt");
      sessionStorage.removeItem("vf_initial_model");
      if (savedImg) {
        sessionStorage.removeItem("vf_initial_image");
        sessionStorage.removeItem("vf_initial_image_name");
      }
      if (urlParams && (urlParams.has("prompt") || urlParams.has("model"))) {
        window.history.replaceState({}, "", "/chat");
      }

      if (savedImg) {
        setImagePreview(savedImg);
        setImageName(savedImgName || "anh_canh_bao.jpg");
      }

      if (savedPrompt && savedPrompt.trim()) {
        hasSentInitialPrompt.current = true;
        if (!savedImg) {
          sendMessage(savedPrompt.trim());
        } else {
          setInput(savedPrompt.trim());
        }
      }
    } catch { }
  }, [sendMessage, setInput]);

  // ===========================================================================
  // LOCATION HANDLERS (Tuân thủ ADR-005: timeout 8s, không lấy GPS nền, 3 lựa chọn)
  // ===========================================================================
  const handleConsentGps = () => {
    setIsLocating(true);
    if (typeof window === "undefined" || !navigator.geolocation) {
      setIsLocating(false);
      setLocationState({
        status: "MANUAL",
        source: "USER_TEXT",
        label: t("Trình duyệt không hỗ trợ GPS (Vui lòng nhập tay)"),
      });
      return;
    }

    let timeoutId: NodeJS.Timeout;

    const successHandler = (pos: GeolocationPosition) => {
      clearTimeout(timeoutId);
      setIsLocating(false);
      const lat = pos.coords.latitude;
      const lng = pos.coords.longitude;
      setLocationState({
        status: "CONSENTED",
        source: "BROWSER_GPS",
        label: t("Đã ghi nhận vị trí của bạn (GPS)"),
        coords: { lat, lng },
      });
      setIsMapOpen(true);
    };

    const errorHandler = () => {
      clearTimeout(timeoutId);
      setIsLocating(false);
      setLocationState({
        status: "MANUAL",
        source: "USER_TEXT",
        label: t("Tín hiệu GPS yếu hoặc bị chặn (Vui lòng nhập tay)"),
      });
    };

    // Timeout 8 giây theo đúng tài liệu (tránh treo khi ở trong hầm hoặc cao tốc)
    timeoutId = setTimeout(() => {
      setIsLocating(false);
      setLocationState({
        status: "MANUAL",
        source: "USER_TEXT",
        label: t("Quá thời gian chờ GPS > 8s (Vui lòng nhập tay)"),
      });
    }, 8000);

    navigator.geolocation.getCurrentPosition(successHandler, errorHandler, {
      timeout: 8000,
      enableHighAccuracy: false,
    });
  };

  const handleManualLocation = (areaText: string) => {
    setLocationState({
      status: "MANUAL",
      source: "USER_TEXT",
      label: areaText,
    });
    setIsMapOpen(true);
  };

  const handleSkipLocation = () => {
    setLocationState({
      status: "NOT_SHARED",
      source: "USER_TEXT",
      label: t("Không chia sẻ"),
    });
    setIsMapOpen(false);
  };

  const handleResetLocation = () => {
    setLocationState({
      status: "PENDING",
      source: "USER_TEXT",
      label: "",
    });
  };

  const selectImage = async (file: File) => {
    if (role !== "CUSTOMER") {
      setImageUploadError(t("Vui lòng đăng nhập tài khoản khách hàng để tải ảnh."));
      return;
    }
    setResolvedImageKind(null);
    const requestId = ++uploadRequestId.current;
    setUploadedAttachmentId(null);
    setImageUploadError(null);
    setImageName(file.name);
    const reader = new FileReader();
    reader.onload = () => {
      if (requestId === uploadRequestId.current) setImagePreview(String(reader.result));
    };
    reader.readAsDataURL(file);

    // Upload lên máy chủ backend để OCR/Vision phân tích sơ bộ
    setIsUploadingImage(true);
    try {
      const res = await uploadAttachment(file, "auto");
      if (requestId !== uploadRequestId.current) return;
      if (res?.success && res.data?.attachment_id) {
        const kind = res.data.detected_signals?.image_kind;
        const error = getUploadError(res.data);
        if (error) {
          setImageUploadError(t(error));
        } else {
          setResolvedImageKind(kind === "exterior" ? "exterior" : kind === "charger" ? "charger" : "dashboard");
          setUploadedAttachmentId(res.data.attachment_id);
        }
      } else { throw new Error("Upload failed"); }
    } catch {
      if (requestId === uploadRequestId.current) setImageUploadError(t("Chưa tải được ảnh lên máy chủ. Vui lòng chọn lại ảnh hoặc gửi mô tả bằng chữ."));
    } finally {
      if (requestId === uploadRequestId.current) setIsUploadingImage(false);
    }
  };

  const submit = () => {
    if (loading || isUploadingImage || (imagePreview && !uploadedAttachmentId)) return;
    const text =
      input.trim() ||
      (imagePreview
        ? resolvedImageKind === "exterior"
          ? t("Tôi gửi ảnh ngoại thất xe. Nhờ Trợ lý AI kiểm tra dấu hiệu hư hại.")
          : t("Tôi gửi ảnh cảnh báo táp-lô/trụ sạc. Nhờ Trợ lý AI nhận diện triệu chứng sơ bộ.")
        : "");
    if (!text) return;
    sendMessage(
      text,
      uploadedAttachmentId ? [uploadedAttachmentId] : undefined,
      imagePreview ? { src: imagePreview, name: imageName || t("Ảnh đã gửi"), caption: input.trim() } : undefined,
    );

    // Việc mở thẻ vị trí tuân thủ Single Source of Truth từ Backend:
    // Backend trả về cờ request_location (hoặc sự cố CRITICAL) thì useEffect([criticalBanner, requestLocation])
    // sẽ tự động mở thẻ chia sẻ vị trí và đặt suggestedCategory tương ứng.

    setImagePreview(null);
    setImageName(null);
    setUploadedAttachmentId(null);
    setResolvedImageKind(null);
  };

  const lastMessage = messages[messages.length - 1];
  const servStatus: ServStatus = criticalBanner || imageUploadError || safetyError || guestLimitReached || lastMessage?.id.startsWith("error_")
    ? "care" : isUploadingImage ? "uploading" : loading ? "thinking"
    : messages.length > 1 && lastMessage?.sender === "AGENT" ? "result" : "idle";

  return (
    <div className="w-full">
      {/* Critical Alert Banner (Sticky 46px ngay dưới Navbar, đỏ đậm tương phản cao hoặc ribbon khi đã an toàn) */}
      <EmergencyAlertBanner
        visible={criticalBanner}
        isDismissed={criticalBannerDismissed}
        onDismiss={dismissCriticalBanner}
        onRestore={restoreCriticalBanner}
        pending={safetyPending}
        error={safetyError}
        canAcknowledge={canAcknowledgeSafety}
      />

      <div
        className={`mx-auto px-4 py-3 sm:py-4 transition-all duration-300 ${
          isMapOpen ? "max-w-7xl" : isSidebarOpen ? "max-w-6xl" : "max-w-4xl"
        }`}
      >

      {/* Mobile Drawer Sidebar */}
      <ChatHistorySidebar
        currentSessionId={sessionId}
        onSelectSession={loadSession}
        onNewChat={handleResetAll}
        isOpen={isMobileDrawerOpen}
        onToggleCollapse={() => setIsMobileDrawerOpen(false)}
        isGuest={role === "GUEST"}
        userId={user?.id || (role === "GUEST" ? "guest" : undefined)}
        isMobileDrawer={true}
        onCloseMobileDrawer={() => setIsMobileDrawerOpen(false)}
        refreshTrigger={messages.length}
        onModalOpenChange={setIsModalBlockingChat}
      />

      {/* Main Layout: Desktop 55/45 khi mở map, Mặc định chat chiếm toàn bộ container */}
      <div
        className={`grid gap-4 items-start transition-all duration-300 ${
          isMapOpen ? "lg:grid-cols-[1.12fr_0.88fr]" : "grid-cols-1"
        }`}
      >
        {/* =============================================================
            KHUNG CHAT CHÍNH VỚI SIDEBAR LỊCH SỬ (PHƯƠNG ÁN 1)
        ============================================================= */}
        <div className="bg-white border border-slate-200/90 rounded-2xl shadow-xs overflow-hidden flex flex-row h-[calc(100vh-140px)] min-h-[580px] max-h-[820px]">
          {/* Desktop Left Sidebar: Option 1 */}
          <ChatHistorySidebar
            currentSessionId={sessionId}
            onSelectSession={loadSession}
            onNewChat={handleResetAll}
            isOpen={isSidebarOpen}
            onToggleCollapse={() => handleToggleSidebar(false)}
            isGuest={role === "GUEST"}
            userId={user?.id || (role === "GUEST" ? "guest" : undefined)}
            refreshTrigger={messages.length}
            onModalOpenChange={setIsModalBlockingChat}
          />

          {/* Cột Chat chính bên phải */}
          <div className="flex-1 flex flex-col min-w-0 h-full">
            {/* Header thu gọn thấp (~40px) */}
            <div data-chat-header className="min-h-14 px-3.5 py-1.5 bg-slate-50/90 text-slate-900 flex items-center justify-between gap-2 border-b border-slate-200/80">
              <div className="flex items-center space-x-2 min-w-0">
                {/* Nút mở sidebar khi thu gọn trên Desktop */}
                {!isSidebarOpen && (
                  <button
                    type="button"
                    onClick={() => handleToggleSidebar(true)}
                    className="hidden lg:flex p-1.5 rounded-lg text-slate-500 hover:text-slate-800 hover:bg-slate-200/70 transition"
                    title={t("Mở lịch sử cuộc trò chuyện")}
                  >
                    <PanelLeft className="w-4 h-4" />
                  </button>
                )}
                {/* Nút mở lịch sử trên Mobile */}
                <button
                  type="button"
                  onClick={() => setIsMobileDrawerOpen(true)}
                  className="lg:hidden p-1.5 rounded-lg text-slate-500 hover:text-slate-800 hover:bg-slate-200/70 transition"
                  title={t("Lịch sử cuộc trò chuyện")}
                >
                  <History className="w-4 h-4" />
                </button>

                <ServMascot inputRef={servInputRef} status={servStatus} responseKey={lastMessage?.id} compact />
                <div className="min-w-0">
                  <div className="font-bold text-[13px] text-slate-900 truncate">
                    Serv · <span className="font-normal text-slate-600">{t("Trợ lý Dịch vụ VinFast")}</span>
                  </div>
                </div>
                <div className="text-[11px] text-slate-500 hidden sm:flex items-center gap-1.5 pl-2 border-l border-slate-200">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 inline-block animate-pulse shrink-0" />
                  <span className="truncate max-w-[200px]">
                    {role === "GUEST" ? "Guest" : t("Sẵn sàng 24/7")}
                  </span>
                </div>
              </div>

              {/* Header Right Actions:
                  Chỉ giữ một nút "Cuộc trò chuyện mới" ở sidebar.
                  Header chat chỉ hiện icon "+" khi sidebar thu gọn hoặc trên mobile. */}
              <div className="flex items-center gap-1.5 shrink-0">
                {!isSidebarOpen && (
                  <button
                    type="button"
                    onClick={handleResetAll}
                    className="hidden lg:flex p-1.5 rounded-lg bg-white hover:bg-slate-100 text-slate-700 hover:text-slate-900 border border-slate-200 shadow-2xs transition active:scale-95"
                    title={t("Cuộc trò chuyện mới")}
                  >
                    <Plus className="w-4 h-4" />
                  </button>
                )}
                <button
                  type="button"
                  onClick={handleResetAll}
                  className="lg:hidden p-1.5 rounded-lg bg-white hover:bg-slate-100 text-slate-700 hover:text-slate-900 border border-slate-200 shadow-2xs transition active:scale-95"
                  title={t("Cuộc trò chuyện mới")}
                >
                  <Plus className="w-4 h-4" />
                </button>
              </div>
            </div>

          {/* Case Status Strip: Thanh mỏng 1 dòng khi đã có Case ID */}
          {currentCaseId && (
            <div className="px-3.5 py-1.5 bg-blue-50/80 border-b border-blue-200/60 flex items-center justify-between text-[11.5px] animate-fadeIn">
              <div className="flex items-center gap-1.5 truncate">
                <span className="w-1.5 h-1.5 rounded-full bg-blue-600 animate-pulse shrink-0" />
                <span className="text-slate-600">{t("Hồ sơ:")}</span>
                <strong className="font-mono font-bold text-slate-900">{currentCaseId}</strong>
                <span className="text-slate-400">·</span>
                <span className="text-blue-700 font-medium">{t("Đang tiếp nhận xử lý")}</span>
              </div>
              {role === "GUEST" ? (
                <Link
                  href="/login"
                  className="text-[#1E40AF] font-bold hover:underline flex items-center gap-0.5 shrink-0 text-[11px]"
                >
                  <span>{t("Đăng nhập")}</span>
                  <ArrowRight className="w-3 h-3" />
                </Link>
              ) : (
                <Link
                  href={currentCaseId ? `/track-case?case_id=${encodeURIComponent(currentCaseId)}` : "/track-case"}
                  className="text-[#1E40AF] font-bold hover:underline flex items-center gap-0.5 shrink-0 text-[11px]"
                >
                  <span>{t("Xem tiến trình ›")}</span>
                </Link>
              )}
            </div>
          )}

          {/* Messages Feed (Không còn hàng QuickPromptsBar trùng lặp, giữ khung chat thông thoáng) */}
          <ChatFeed
            messages={messages}
            loading={loading}
            isMapOpen={isMapOpen}
            showLocationCard={showLocationCard}
            onSelectReply={(reply) => {
              const lower = reply.toLowerCase();
              if (
                lower.includes("map") ||
                lower.includes("bản đồ") ||
                lower.includes("xem bản đồ") ||
                lower.includes("điểm cứu hộ")
              ) {
                setShowLocationCard(true);
                setIsMapOpen(true);
                return;
              }

              // Khi khách chọn "Báo sự cố kỹ thuật": mở các chip lỗi cụ thể ngay dưới bong bóng chào
              if (reply === t("Báo sự cố kỹ thuật")) {
                const lastMsg = messages[messages.length - 1];
                if (lastMsg) {
                  updateMessageChips(lastMsg.id, [
                    t("Mã lỗi CC01 trụ sạc"),
                    t("Cảnh báo rùa vàng"),
                    t("Kẹt súng sạc"),
                    t("Xe không khởi động"),
                  ]);
                }
                setInput(t("Xe của tôi đang gặp sự cố kỹ thuật: "));
                return;
              }

              // Điền sẵn câu hỏi vào ô nhập đối với các nhóm chip tư vấn / tra cứu
              const GREETING_PREFILLS: Record<string, string> = {
                "Tư vấn xe": t("Tư vấn xe"),
                "Trạm sạc & ứng dụng": t("Hướng dẫn cách sạc pin tại trạm sạc công cộng, biểu phí sạc và tính năng trên App VinFast."),
                "Bảo hành & bảo dưỡng": t("Tôi muốn hỏi chính sách bảo hành pin và lịch bảo dưỡng định kỳ."),
              };

              const prefill = Object.entries(GREETING_PREFILLS).find(([key]) => t(key) === reply)?.[1];
              if (prefill) {
                setInput(prefill);
                return;
              }

              sendMessage(reply);
              if (lower.includes("sạc") || lower.includes("trạm") || lower.includes("charging")) {
                setSuggestedCategory("CHARGING_STATION");
                setShowLocationCard(true);
              } else if (lower.includes("xưởng") || lower.includes("bảo dưỡng") || lower.includes("maintenance")) {
                setSuggestedCategory("SERVICE_WORKSHOP");
                setShowLocationCard(true);
              } else if (lower.includes("cứu hộ") || lower.includes("cao tốc")) {
                setSuggestedCategory("EXPRESSWAY_RESCUE");
                setShowLocationCard(true);
              }
            }}
          />

          {/* Card Xin Quyền Vị Trí: ĐƯA RA KHỎI LUỒNG CHAT, LÀM THANH MỎNG DÍNH TRÊN Ô NHẬP */}
          {showLocationCard && (
            <LocationConsentCard
              locationState={locationState}
              isLocating={isLocating}
              isMapOpen={isMapOpen}
              onConsentGps={handleConsentGps}
              onManualLocation={handleManualLocation}
              onSkip={handleSkipLocation}
              onToggleMap={() => setIsMapOpen(!isMapOpen)}
              onResetLocation={handleResetLocation}
            />
          )}

          {/* Input Bar */}
          {(isUploadingImage || resolvedImageKind || imageUploadError) && (
            <div className="px-3 py-2 border-t border-slate-200 text-xs text-slate-600">
              {isUploadingImage && <p role="status" className="mt-1">{t("Đang tải và phân tích ảnh…")}</p>}
              {resolvedImageKind && <p role="status" className="mt-1">{t("Đã tự nhận diện:")}{" "}{resolvedImageKind === "exterior" ? t("Ngoại thất xe") : resolvedImageKind === "charger" ? t("Trụ sạc") : t("Táp-lô")}</p>}
              {imageUploadError && <p role="alert" className="mt-1 text-red-700">{imageUploadError}</p>}
            </div>
          )}
          {guestLimitReached && role !== "CUSTOMER" && (
            <p role="alert" className="border-t border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
              {t("Quý khách đã hết lượt sử dụng, cần phải đăng nhập để sử dụng tiếp dịch vụ")}
            </p>
          )}
          <ChatInputBar
            inputRef={servInputRef}
            input={input}
            onChangeInput={setInput}
            onSend={submit}
            disabled={loading || isUploadingImage || isModalBlockingChat || (!!imagePreview && !uploadedAttachmentId)}
            uploadDisabled={loading || isUploadingImage || isModalBlockingChat || role !== "CUSTOMER"}
            uploadHint={role !== "CUSTOMER" ? t("Đăng nhập tài khoản khách hàng để tải ảnh") : undefined}
            imageReady={!!uploadedAttachmentId}
            imagePreview={imagePreview}
            imageName={imageName}
            onSelectImage={selectImage}
            onClearImage={() => {
              setResolvedImageKind(null);
              uploadRequestId.current += 1;
              setIsUploadingImage(false);
              setImageUploadError(null);
              setImagePreview(null);
              setImageName(null);
              setUploadedAttachmentId(null);
            }}
          />

          {/* Ghi chú bảo mật: 1 dòng mỏng nhẹ thay cho Card cồng kềnh */}
          <div className="py-1 px-3 bg-slate-50/70 border-t border-slate-100 flex items-center justify-center gap-1.5 text-[10.5px] text-slate-400">
            <ShieldCheck className="w-3 h-3 text-emerald-600 shrink-0" />
            <span>{t("Dữ liệu được mã hóa và bảo mật theo chính sách quyền riêng tư VinFast.")}</span>
          </div>
        </div>
      </div>

        {/* =============================================================
            CỘT PHẢI (DESKTOP): CHỈ TRƯỢT RA KHI KHÁCH KÍCH HOẠT ACTION (XEM MAP)
            Mặc định không có 5 card tĩnh làm rối mắt!
        ============================================================= */}
        {isMapOpen && (
          <div className="hidden lg:block animate-fadeIn">
            <ServiceMapPanel
              isOpen={isMapOpen}
              onClose={() => setIsMapOpen(false)}
              locationState={locationState}
              servicePoints={[]}
              selectedPointId={selectedPointId}
              onSelectPoint={(id) => setSelectedPointId(id)}
              suggestedCategory={suggestedCategory}
            />
          </div>
        )}
      </div>

      {/* =============================================================
          MOBILE: BOTTOM-SHEET MODAL (HIỆN TRÊN ĐIỆN THOẠI KHI MỞ MAP)
      ============================================================= */}
      {isMapOpen && (
        <ServiceMapPanel
          isOpen={isMapOpen}
          onClose={() => setIsMapOpen(false)}
          locationState={locationState}
          servicePoints={[]}
          selectedPointId={selectedPointId}
          onSelectPoint={(id) => setSelectedPointId(id)}
          suggestedCategory={suggestedCategory}
          isMobileModal={true}
        />
      )}

      {/* Keep the mobile map action in flow so it cannot cover the footer hotline. */}
      {!isMapOpen && (
        <div className="lg:hidden mt-3 flex justify-end">
          <button
            type="button"
            onClick={() => {
              setShowLocationCard(true);
              setIsMapOpen(true);
            }}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-full bg-[#1E40AF] hover:bg-[#1D4ED8] text-white font-bold text-[12.5px] shadow-lg active:scale-95 transition"
          >
            <Compass className="w-4 h-4 animate-spin [animation-duration:8s]" />
            <span>{t("Bản đồ hỗ trợ")}</span>
          </button>
        </div>
      )}
      </div>
    </div>
  );
}
