"use client";

import {
  RotateCcw,
  ShieldCheck,
  ArrowRight,
  Compass,
} from "lucide-react";
import { useState, useEffect, useRef, useCallback } from "react";
import Link from "next/link";
import { UserLocationState, CaseLocationPayload, NearbyAction } from "../types";
import { useChat } from "../hooks/useChat";
import { EmergencyAlertBanner } from "./EmergencyAlertBanner";
import { ChatFeed } from "./ChatFeed";
import { ChatInputBar } from "./ChatInputBar";
import { LocationConsentCard } from "./LocationConsentCard";
import { NearbyResults } from "./NearbyResults";
import { submitCustomerLocation, uploadAttachment } from "../api/chatApi";
import { shouldSyncLocation } from "../utils/locationTracking";
import { getUploadError } from "../uploadState";
import { useAuth, ProductMark } from "@/features/shared";

export function CustomerChatContainer() {
  const { user, isReady } = useAuth();
  if (!isReady) return null;
  return <CustomerChatSession key={user?.id || "guest"} />;
}

function CustomerChatSession() {
  const { user, role } = useAuth();
  const {
    messages,
    input,
    setInput,
    loading,
    currentCaseId,
    criticalBanner,
    criticalBannerDismissed,
    dismissCriticalBanner,
    restoreCriticalBanner,
    safetyPending,
    safetyError,
    canAcknowledgeSafety,
    nearbyAction,
    sendMessage,
    resetChat,
    updateMessageChips,
  } = useChat({
    userName: user?.name,
  });

  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [imageName, setImageName] = useState<string | null>(null);
  const [uploadedAttachmentId, setUploadedAttachmentId] = useState<string | null>(null);
  const [isUploadingImage, setIsUploadingImage] = useState<boolean>(false);
  const [resolvedImageKind, setResolvedImageKind] = useState<"dashboard" | "charger" | "exterior" | null>(null);
  const [imageUploadError, setImageUploadError] = useState<string | null>(null);
  const uploadRequestId = useRef(0);
  const locationRequestId = useRef(0);
  const syncRequestId = useRef(0);
  const failedLocationPayload = useRef<CaseLocationPayload | null>(null);
  const stopWatchRef = useRef<(() => void) | null>(null);
  const lastLocationSync = useRef<{ lat: number; lng: number; time: number; caseId: string } | null>(null);
  const hasSentInitialPrompt = useRef(false);

  // ===========================================================================
  // SERVICE MAP PREVIEW & LOCATION CONSENT (ADR-005, screen-spec.md Section 5.4, CUS-03)
  // ===========================================================================
  const [locationState, setLocationState] = useState<UserLocationState>({
    status: "PENDING",
    source: "USER_TEXT",
    label: "",
  });
  const [locationSyncError, setLocationSyncError] = useState<string | null>(null);
  const [isLocating, setIsLocating] = useState<boolean>(false);
  const [isMapOpen, setIsMapOpen] = useState<boolean>(false);
  const consentAt = useRef(0);
  const [shareWithCase, setShareWithCase] = useState(false);
  const [manualAction, setManualAction] = useState<NearbyAction | null>(null);
  const activeAction = nearbyAction ?? manualAction;
  const [showLocationCard, setShowLocationCard] = useState<boolean>(false);

  const invalidateLocationRequest = () => {
    locationRequestId.current += 1;
    stopWatchRef.current?.();
    stopWatchRef.current = null;
    lastLocationSync.current = null;
    setIsLocating(false);
  };

  useEffect(() => () => {
    locationRequestId.current += 1;
    stopWatchRef.current?.();
    stopWatchRef.current = null;
  }, []);

  const syncLocation = useCallback((payload: CaseLocationPayload) => {
    const id = ++syncRequestId.current;
    failedLocationPayload.current = null;
    setLocationSyncError(null);
    void submitCustomerLocation(payload).then(() => {
      if (id === syncRequestId.current) setLocationSyncError(null);
    }).catch(() => {
      if (id !== syncRequestId.current) return;
      lastLocationSync.current = null;
      failedLocationPayload.current = payload;
      setLocationSyncError("Chưa đồng bộ được vị trí với hồ sơ. Vui lòng thử lại.");
    });
  }, []);

  useEffect(() => {
    if (!shareWithCase || !currentCaseId || locationState.status !== "CONSENTED") return;
    const coords = locationState.coords;
    if (!coords) return;
    const now = Date.now();
    const previous = lastLocationSync.current;
    if (coords && previous?.caseId === currentCaseId && !shouldSyncLocation(previous, coords, now)) return;
    if (coords) lastLocationSync.current = { ...coords, time: now, caseId: currentCaseId };
    syncLocation({
      case_id: currentCaseId,
      status: "CONSENTED",
      source: "BROWSER_GPS",
      location_label: "Vị trí hiện tại",
      latitude: coords?.lat ?? null, longitude: coords?.lng ?? null,
      precision: coords && (locationState.accuracy ?? 0) <= 500 ? "EXACT" : "APPROXIMATE",
      share_with_staff: true,
    });
  }, [shareWithCase, currentCaseId, locationState, syncLocation]);

  useEffect(() => {
    if (loading) {
      locationRequestId.current += 1;
      setIsLocating(false);
      setManualAction(null);
      setShowLocationCard(false);
    }
  }, [loading]);

  useEffect(() => {
    if (!activeAction) return;
    setIsMapOpen(false);
    if (activeAction.category === "ALL") { setShowLocationCard(false); return; }
    if (activeAction.area_text) {
      consentAt.current = 0;
      locationRequestId.current += 1;
      setLocationState({ status: "MANUAL", source: "USER_TEXT", label: activeAction.area_text });
      setShowLocationCard(false);
      return;
    }
    // Reuse only a deliberate location choice within this mounted session for 15 minutes.
    const reusable = Date.now() - consentAt.current < 15 * 60 * 1000;
    if (!reusable) setLocationState({ status: "PENDING", source: "USER_TEXT", label: "" });
    setShowLocationCard(!reusable && !criticalBanner);
    // Each server action is a new turn; location updates must not reopen its popup.
  }, [activeAction, criticalBanner]);

  useEffect(() => {
    locationRequestId.current += 1;
    consentAt.current = 0;
    setLocationState({ status: "PENDING", source: "USER_TEXT", label: "" });
    setShareWithCase(false);
    setManualAction(null);
    setShowLocationCard(false);
  }, [user?.id]);

  const handleResetAll = () => {
    invalidateLocationRequest();
    if (shareWithCase && currentCaseId) syncLocation({ case_id: currentCaseId, status: "NOT_SHARED", source: "USER_TEXT", location_label: "Không chia sẻ", latitude: null, longitude: null, share_with_staff: false });
    setShareWithCase(false);
    consentAt.current = 0;
    setManualAction(null);
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
    setLocationState({ status: "PENDING", source: "USER_TEXT", label: "" });
  };

  // Pre-load draft or auto-send prompt from Landing Hero if available
  useEffect(() => {
    if (hasSentInitialPrompt.current) return;

    try {
      const savedPrompt = sessionStorage.getItem("vf_initial_prompt");
      sessionStorage.removeItem("vf_initial_model");
      const savedImg = sessionStorage.getItem("vf_initial_image");
      const savedImgName = sessionStorage.getItem("vf_initial_image_name");

      if (savedImg) {
        setImagePreview(savedImg);
        setImageName(savedImgName || "anh_canh_bao.jpg");
        sessionStorage.removeItem("vf_initial_image");
        sessionStorage.removeItem("vf_initial_image_name");
      }

      if (savedPrompt) {
        sessionStorage.removeItem("vf_initial_prompt");
        if (!savedImg) {
          // Gửi trực tiếp tin nhắn bằng sendMessage thay vì setInput rồi bắt bấm gửi lần 2
          hasSentInitialPrompt.current = true;
          sendMessage(savedPrompt.trim());
        } else {
          setInput(savedPrompt);
        }
      }
    } catch { }
  }, [sendMessage, setInput]);

  // ===========================================================================
  // LOCATION HANDLERS (Kế hoạch 11/10: Desktop Browser định vị qua Wi-Fi/IP, timeout 8s, không lấy GPS nền, 3 lựa chọn)
  // ===========================================================================
  const handleConsentGps = () => {
    invalidateLocationRequest();
    const requestId = locationRequestId.current;
    setIsLocating(true);
    if (typeof navigator === "undefined" || !navigator.geolocation) {
      setIsLocating(false);
      setLocationState({ status: "MANUAL", source: "USER_TEXT", label: "", errorCode: "UNSUPPORTED" });
      return;
    }
    const successHandler = (pos: GeolocationPosition) => {
      if (requestId !== locationRequestId.current) return;
      const lat = pos.coords.latitude, lng = pos.coords.longitude, accuracy = pos.coords.accuracy;
      if (!Number.isFinite(lat) || Math.abs(lat) > 90 || !Number.isFinite(lng) || Math.abs(lng) > 180 || !Number.isFinite(accuracy) || accuracy < 0) { errorHandler({ code: 2 } as GeolocationPositionError); return; }
      setIsLocating(false);
      setLocationState({ status: "CONSENTED", source: "BROWSER_GPS", label: "Vị trí hiện tại", coords: { lat, lng }, accuracy, isTracking: false, errorCode: accuracy > 500 ? "ACCURACY_LOW" : undefined });
      consentAt.current = Date.now();
      setShowLocationCard(false);
    };
    const errorHandler = (err: GeolocationPositionError) => {
      if (requestId !== locationRequestId.current) return;
      invalidateLocationRequest();
      setLocationState({ status: "MANUAL", source: "USER_TEXT", label: "", errorCode: err.code === 1 ? "PERMISSION_DENIED" : err.code === 3 ? "TIMEOUT" : "POSITION_UNAVAILABLE" });
    };
    try { navigator.geolocation.getCurrentPosition(successHandler, errorHandler, { enableHighAccuracy: false, maximumAge: 0, timeout: 8000 }); }
    catch { errorHandler({ code: 2 } as GeolocationPositionError); }
  };

  const handleManualLocation = (areaText: string) => {
    invalidateLocationRequest();
    setLocationState({
      status: "MANUAL",
      source: "USER_TEXT",
      label: areaText,
    });
    consentAt.current = Date.now();
    setShowLocationCard(false);
  };

  const handleSkipLocation = () => {
    invalidateLocationRequest();
    consentAt.current = 0;
    setShowLocationCard(false);
    if (shareWithCase && currentCaseId) syncLocation({ case_id: currentCaseId, status: "NOT_SHARED", source: "USER_TEXT", location_label: "Không chia sẻ", latitude: null, longitude: null, share_with_staff: false });
    setShareWithCase(false);
    setLocationState({ status: "NOT_SHARED", source: "USER_TEXT", label: "Không chia sẻ" });
    setIsMapOpen(false);
  };

  const handleResetLocation = () => {
    invalidateLocationRequest();
    consentAt.current = 0;
    setShowLocationCard(true);
    setShareWithCase(false);
    setIsMapOpen(false);
    setLocationState({ status: "PENDING", source: "USER_TEXT", label: "" });
    if (shareWithCase && currentCaseId) syncLocation({ case_id: currentCaseId, status: "NOT_SHARED", source: "USER_TEXT", location_label: "Không chia sẻ", latitude: null, longitude: null, share_with_staff: false });
  };

  const selectImage = async (file: File) => {
    if (role !== "CUSTOMER") {
      setImageUploadError("Vui lòng đăng nhập tài khoản khách hàng để tải ảnh.");
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
          setImageUploadError(error);
        } else {
          setResolvedImageKind(kind === "exterior" ? "exterior" : kind === "charger" ? "charger" : "dashboard");
          setUploadedAttachmentId(res.data.attachment_id);
        }
      } else { throw new Error("Upload failed"); }
    } catch {
      if (requestId === uploadRequestId.current) setImageUploadError("Chưa tải được ảnh lên máy chủ. Vui lòng chọn lại ảnh hoặc gửi mô tả bằng chữ.");
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
          ? "Tôi gửi ảnh ngoại thất xe. Nhờ Trợ lý AI kiểm tra dấu hiệu hư hại."
          : "Tôi gửi ảnh cảnh báo táp-lô/trụ sạc. Nhờ Trợ lý AI nhận diện triệu chứng sơ bộ."
        : "");
    if (!text) return;
    sendMessage(
      text,
      uploadedAttachmentId ? [uploadedAttachmentId] : undefined,
      imagePreview ? { src: imagePreview, name: imageName || "Ảnh đã gửi", caption: input.trim() } : undefined,
    );

    // Việc mở thẻ vị trí tuân thủ Single Source of Truth từ Backend:
    // Backend trả về cờ request_location (hoặc sự cố CRITICAL) thì useEffect([criticalBanner, requestLocation])
    // sẽ tự động mở thẻ chia sẻ vị trí và đặt suggestedCategory tương ứng.

    setImagePreview(null);
    setImageName(null);
    setUploadedAttachmentId(null);
    setResolvedImageKind(null);
  };

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
          isMapOpen ? "w-full" : "max-w-4xl"
        }`}
      >

      {/* Desktop: chat 40%, panel 60%; canvas uses 2/3 of the panel (~40% page width). */}
      <div
        className={`grid gap-4 items-start transition-all duration-300 ${
          isMapOpen ? "grid-cols-1 xl:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]" : "grid-cols-1"
        }`}
      >
        {/* =============================================================
            KHUNG CHAT CHÍNH (RỘNG RÃI, CHIẾM 70% CHIỀU CAO, KHÔNG BỊ BÓP)
        ============================================================= */}
        <div className="min-w-0 bg-white border border-slate-200/90 rounded-2xl shadow-xs overflow-hidden flex flex-col h-[calc(100vh-140px)] min-h-[580px] max-h-[820px]">
          {/* Header thu gọn thấp (~40px) */}
          <div className="px-3.5 py-2 bg-slate-50/90 text-slate-900 flex items-center justify-between border-b border-slate-200/80">
            <div className="flex items-center space-x-2 min-w-0">
              <div className="w-7 h-7 rounded-lg bg-[#1E40AF] flex items-center justify-center text-white shrink-0 shadow-2xs">
                <ProductMark className="w-4 h-4 text-white" />
              </div>
              <div className="min-w-0">
                <div className="font-bold text-[13px] text-slate-900 truncate">
                  VFServ AI · <span className="font-normal text-slate-600">Trợ lý Dịch vụ VinFast</span>
                </div>
              </div>
              <div className="text-[11px] text-slate-500 hidden sm:flex items-center gap-1.5 pl-2 border-l border-slate-200">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 inline-block animate-pulse shrink-0" />
                <span className="truncate max-w-[200px]">
                  {role === "GUEST" ? "Guest" : "Sẵn sàng 24/7"}
                </span>
              </div>
            </div>

            {/* Header Right Actions: Gộp Làm mới & Chọn xe thành 1 hàng thấp */}
            <div className="flex items-center gap-1.5 shrink-0">
              <button type="button" onClick={() => setManualAction({ type: "FIND_NEARBY", request_id: crypto.randomUUID(), turn_id: "manual", category: "CHARGING_STATION", vehicle_type: "CAR", requires_location: true, reason: "Tìm trạm sạc ô tô gần bạn.", limit: 5 })} className="flex min-h-10 items-center gap-1 rounded-xl border border-blue-200 bg-white px-2 py-2 text-xs font-medium text-blue-800">
                <Compass className="h-3 w-3" /> Tìm điểm gần đây
              </button>
              <button
                type="button"
                onClick={handleResetAll}
                className="flex items-center gap-1 rounded-lg bg-white hover:bg-slate-100 text-slate-600 hover:text-slate-900 text-[11.5px] font-medium px-2 py-1 border border-slate-200 shadow-2xs transition active:scale-95"
                title="Làm mới cuộc trò chuyện"
              >
                <RotateCcw className="w-3 h-3" />
                <span className="hidden sm:inline">Làm mới</span>
              </button>

            </div>
          </div>

          {/* Case Status Strip: Thanh mỏng 1 dòng khi đã có Case ID */}
          {currentCaseId && (
            <div className="px-3.5 py-1.5 bg-blue-50/80 border-b border-blue-200/60 flex items-center justify-between text-[11.5px] animate-fadeIn">
              <div className="flex items-center gap-1.5 truncate">
                <span className="w-1.5 h-1.5 rounded-full bg-blue-600 animate-pulse shrink-0" />
                <span className="text-slate-600">Hồ sơ:</span>
                <strong className="font-mono font-bold text-slate-900">{currentCaseId}</strong>
                <span className="text-slate-400">·</span>
                <span className="text-blue-700 font-medium">Đang tiếp nhận xử lý</span>
              </div>
              {role === "GUEST" ? (
                <Link
                  href="/login"
                  className="text-[#1E40AF] font-bold hover:underline flex items-center gap-0.5 shrink-0 text-[11px]"
                >
                  <span>Đăng nhập</span>
                  <ArrowRight className="w-3 h-3" />
                </Link>
              ) : (
                <Link
                  href={currentCaseId ? `/track-case?case_id=${encodeURIComponent(currentCaseId)}` : "/track-case"}
                  className="text-[#1E40AF] font-bold hover:underline flex items-center gap-0.5 shrink-0 text-[11px]"
                >
                  <span>Xem tiến trình ›</span>
                </Link>
              )}
            </div>
          )}

          {/* Messages Feed (Không còn hàng QuickPromptsBar trùng lặp, giữ khung chat thông thoáng) */}
          <ChatFeed
            messages={messages}
            nearbyRequestId={activeAction?.request_id}
            loading={loading}
            isMapOpen={isMapOpen}
            showLocationCard={showLocationCard}
            onSelectReply={(reply) => {
              // Khi khách chọn "Báo sự cố kỹ thuật": mở các chip lỗi cụ thể ngay dưới bong bóng chào
              if (reply === "Báo sự cố kỹ thuật") {
                const lastMsg = messages[messages.length - 1];
                if (lastMsg) {
                  updateMessageChips(lastMsg.id, [
                    "Mã lỗi CC01 trụ sạc",
                    "Cảnh báo rùa vàng",
                    "Kẹt súng sạc",
                    "Xe không khởi động",
                  ]);
                }
                setInput("Xe của tôi đang gặp sự cố kỹ thuật: ");
                return;
              }

              // Điền sẵn câu hỏi vào ô nhập đối với các nhóm chip tư vấn / tra cứu
              const GREETING_PREFILLS: Record<string, string> = {
                "Tư vấn xe": "Tôi muốn tư vấn các dòng xe điện VinFast, giá lăn bánh và đăng ký lái thử.",
                "Trạm sạc & ứng dụng": "Hướng dẫn cách sạc pin tại trạm sạc công cộng, biểu phí sạc và tính năng trên App VinFast.",
                "Bảo hành & bảo dưỡng": "Tôi muốn hỏi chính sách bảo hành pin và lịch bảo dưỡng định kỳ.",
              };

              if (GREETING_PREFILLS[reply]) {
                setInput(GREETING_PREFILLS[reply]);
                return;
              }

              sendMessage(reply);
            }}
          >
            <NearbyResults action={activeAction} locationState={locationState}
              onChangeLocation={handleResetLocation} onStopSharing={handleSkipLocation}
              onChooseCategory={(category) => sendMessage(`Tìm ${category === "SHOWROOM" ? "showroom" : category === "SERVICE_WORKSHOP" ? "xưởng dịch vụ" : "trạm sạc"} gần đây`)} />
          </ChatFeed>

          {/* Card Xin Quyền Vị Trí: ĐƯA RA KHỎI LUỒNG CHAT, LÀM THANH MỎNG DÍNH TRÊN Ô NHẬP */}
          {locationSyncError && <div role="alert" className="px-3 py-2 text-xs text-amber-900 bg-amber-50">{locationSyncError} <button type="button" className="underline" onClick={() => { if (failedLocationPayload.current) syncLocation(failedLocationPayload.current); }}>Thử lại đồng bộ</button></div>}
          {showLocationCard && (
            <LocationConsentCard
              reason={activeAction?.reason}
              modal
              locationState={locationState}
              isLocating={isLocating}
              isMapOpen={isMapOpen}
              onConsentGps={handleConsentGps}
              onManualLocation={handleManualLocation}
              onSkip={handleSkipLocation}
              onToggleMap={() => setIsMapOpen(!isMapOpen)}
              onResetLocation={handleResetLocation}
              onStopSharing={handleSkipLocation}
            />
          )}

          {currentCaseId && locationState.status === "CONSENTED" && !shareWithCase && (
            <button type="button" className="mx-3 my-2 rounded-xl border px-3 py-2 text-sm" onClick={() => setShareWithCase(true)}>Chia sẻ vị trí với hồ sơ</button>
          )}
          {shareWithCase && <p className="px-3 text-xs text-slate-600">Vị trí đang được chia sẻ với hồ sơ. Dừng chia sẻ để xóa tọa độ.</p>}
          {/* Input Bar */}
          {(isUploadingImage || resolvedImageKind || imageUploadError) && (
            <div className="px-3 py-2 border-t border-slate-200 text-xs text-slate-600">
              {isUploadingImage && <p role="status" className="mt-1">Đang tải và phân tích ảnh…</p>}
              {resolvedImageKind && <p role="status" className="mt-1">Đã tự nhận diện: {resolvedImageKind === "exterior" ? "Ngoại thất xe" : resolvedImageKind === "charger" ? "Trụ sạc" : "Táp-lô"}</p>}
              {imageUploadError && <p role="alert" className="mt-1 text-red-700">{imageUploadError}</p>}
            </div>
          )}
          <ChatInputBar
            input={input}
            onChangeInput={setInput}
            onSend={submit}
            disabled={loading || isUploadingImage || (!!imagePreview && !uploadedAttachmentId)}
            uploadDisabled={loading || isUploadingImage || role !== "CUSTOMER"}
            uploadHint={role !== "CUSTOMER" ? "Đăng nhập tài khoản khách hàng để tải ảnh" : undefined}
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
            <span>Dữ liệu được mã hóa và bảo mật theo chính sách quyền riêng tư VinFast.</span>
          </div>
        </div>

        {/* =============================================================
            BẢN ĐỒ: CỘT PHẢI Ở DESKTOP, XẾP DƯỚI CHAT Ở MÀN HẸP
            Mặc định không có 5 card tĩnh làm rối mắt!
        ============================================================= */}

      </div>


      </div>
    </div>
  );
}
