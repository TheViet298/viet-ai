"use client";

import { useLocale } from "@/features/shared/context/LocaleContext";

import React, { useState, useEffect } from "react";
import { createPortal } from "react-dom";
import {
  X,
  Car,
  Phone,
  Mail,
  Check,
  AlertCircle,
  Loader2,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";

const VINFAST_VEHICLES = ["VF3", "VF5", "VF6", "VF7", "VF8", "VF9", "e34"];

interface UserProfileModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function UserProfileModal({ isOpen, onClose }: UserProfileModalProps) {
  const { t } = useLocale();
  const { user, updateProfile } = useAuth();

  const [mounted, setMounted] = useState(false);
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [vehicleModel, setVehicleModel] = useState("VF8");
  const [saving, setSaving] = useState(false);
  const [statusMessage, setStatusMessage] = useState<{
    type: "success" | "error";
    text: string;
  } | null>(null);

  // Đảm bảo mount trên client trước khi dùng createPortal
  useEffect(() => {
    setMounted(true);
  }, []);

  // Đồng bộ dữ liệu hiện tại khi mở modal (lọc bỏ các chuỗi legacy/mock)
  useEffect(() => {
    if (isOpen && user) {
      const cleanName = user.name?.startsWith("CUST_MOCK") ? "" : (user.name || "");
      const cleanPhone =
        user.phone === "customer" || user.phone?.startsWith("customer")
          ? ""
          : (user.phone || "");
      setName(cleanName);
      setPhone(cleanPhone);
      setVehicleModel(user.vehicleModel || "VF8");
      setStatusMessage(null);
    }
  }, [isOpen, user]);

  // Đóng modal bằng phím Escape
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen && !saving) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, saving, onClose]);

  if (!mounted || !isOpen || !user) return null;

  // Mã định danh hội viên chính thức từ user.id
  const customerIdCode = `VF-${user.id.replace(/-/g, "").slice(0, 8).toUpperCase()}`;
  const displayHeaderName =
    name.trim() ||
    (user.name && !user.name.startsWith("CUST_MOCK") ? user.name : t("Chủ xe VinFast"));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setStatusMessage({ type: "error", text: "Vui lòng nhập họ và tên chủ xe." });
      return;
    }

    setSaving(true);
    setStatusMessage(null);

    try {
      await updateProfile({
        name: name.trim(),
        phone: phone.trim() || undefined,
        vehicleModel,
      });
      setStatusMessage({
        type: "success",
        text: "Cập nhật hồ sơ tài khoản thành công!",
      });
      setTimeout(() => {
        onClose();
      }, 900);
    } catch (err) {
      setStatusMessage({
        type: "error",
        text: err instanceof Error ? err.message : "Không thể lưu thông tin. Vui lòng thử lại.",
      });
    } finally {
      setSaving(false);
    }
  };

  const modalContent = (
    <div
      className="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs animate-in fade-in duration-200"
      onClick={(e) => {
        if (e.target === e.currentTarget && !saving) onClose();
      }}
      role="dialog"
      aria-modal="true"
      aria-labelledby="user-profile-title"
    >
      <div className="relative w-full max-w-lg bg-white rounded-2xl shadow-2xl border border-slate-200 overflow-hidden animate-in zoom-in-95 duration-200 max-h-[92vh] flex flex-col my-auto">
        {/* Nút đóng */}
        <button
          type="button"
          onClick={onClose}
          disabled={saving}
          className="absolute top-4 right-4 z-10 p-1.5 rounded-full text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition"
          aria-label={t("Đóng")}
        >
          <X className="w-5 h-5" />
        </button>

        {/* Header: Nhận diện chủ xe */}
        <div className="px-6 pt-6 pb-4 border-b border-slate-100 bg-slate-50/70 shrink-0">
          <div className="flex items-start gap-3.5">
            <div className="w-12 h-12 rounded-xl bg-[#1E40AF] text-white flex items-center justify-center text-lg font-bold shadow-2xs shrink-0">
              {displayHeaderName.charAt(0).toUpperCase()}
            </div>
            <div className="flex-1 min-w-0 pr-6">
              <div className="flex items-center gap-2 flex-wrap">
                <h2 id="user-profile-title" className="text-lg font-bold text-slate-900 truncate">
                  {displayHeaderName}
                </h2>
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-blue-50 text-[#1E40AF] border border-blue-200 text-[11px] font-semibold">
                  <ShieldCheck className="w-3.5 h-3.5" />
                  {t("Chủ xe xác thực")}
                </span>
              </div>
              <div className="flex items-center gap-3 mt-1 text-[12px] text-slate-500 font-mono">
                <span>
                  {t("Mã hội viên:")} <strong className="text-slate-800">{customerIdCode}</strong>
                </span>
                <span>•</span>
                <span className="truncate">{user.email}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Vùng nội dung cuộn được */}
        <div className="overflow-y-auto px-6 py-4 space-y-4 flex-1">
          {/* Thông báo trạng thái nếu có */}
          {statusMessage && (
            <div
              className={`p-3 rounded-xl text-[13px] flex items-center gap-2 ${
                statusMessage.type === "success"
                  ? "bg-emerald-50 text-emerald-800 border border-emerald-200"
                  : "bg-red-50 text-red-800 border border-red-200"
              }`}
            >
              {statusMessage.type === "success" ? (
                <Check className="w-4 h-4 text-emerald-600 shrink-0" />
              ) : (
                <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
              )}
              <span>{t(statusMessage.text)}</span>
            </div>
          )}

          <form id="profile-form" onSubmit={handleSubmit} className="space-y-4">
            {/* Lựa chọn Dòng xe VinFast */}
            <div className="space-y-1.5">
              <label className="block text-[13px] font-semibold text-slate-700 flex items-center gap-1.5">
                <Car className="w-4 h-4 text-[#1E40AF]" />
                {t("Dòng xe điện đang sở hữu")}
              </label>
              <div className="grid grid-cols-4 sm:grid-cols-7 gap-1.5">
                {VINFAST_VEHICLES.map((model) => (
                  <button
                    key={model}
                    type="button"
                    onClick={() => setVehicleModel(model)}
                    className={`py-1.5 text-center text-[12.5px] font-semibold rounded-lg border transition ${
                      vehicleModel === model
                        ? "bg-[#1E40AF] text-white border-[#1E40AF] shadow-2xs"
                        : "bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100"
                    }`}
                  >
                    {model}
                  </button>
                ))}
              </div>
            </div>

            {/* Họ và tên */}
            <div className="space-y-1">
              <label htmlFor="profile-fullname" className="block text-[13px] font-semibold text-slate-700">
                {t("Họ và tên chủ xe")}
              </label>
              <input
                id="profile-fullname"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder={t("VD: Nguyễn Văn Tuấn")}
                required
                className="w-full rounded-xl border border-slate-200 px-3.5 py-2.5 text-[13.5px] text-slate-900 placeholder:text-slate-400 focus:border-[#1E40AF] focus:ring-2 focus:ring-blue-100 focus:outline-none transition"
              />
            </div>

            {/* Số điện thoại */}
            <div className="space-y-1">
              <label
                htmlFor="profile-phone"
                className="block text-[13px] font-semibold text-slate-700 flex items-center gap-1.5"
              >
                <Phone className="w-3.5 h-3.5 text-slate-400" />
                {t("Số điện thoại liên hệ nhận ca dịch vụ")}
              </label>
              <input
                id="profile-phone"
                type="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder={t("VD: 0912345678")}
                className="w-full rounded-xl border border-slate-200 px-3.5 py-2.5 text-[13.5px] text-slate-900 placeholder:text-slate-400 focus:border-[#1E40AF] focus:ring-2 focus:ring-blue-100 focus:outline-none transition"
              />
            </div>

            {/* Tên đăng nhập (chỉ đọc) */}
            <div className="space-y-1">
              <label className="block text-[12px] font-medium text-slate-500 flex items-center gap-1.5">
                <Mail className="w-3.5 h-3.5 text-slate-400" />
                {t("Tài khoản hệ thống (không đổi)")}
              </label>
              <input
                type="text"
                value={user.email}
                disabled
                className="w-full rounded-xl border border-slate-200 bg-slate-100/70 px-3.5 py-2 text-[13px] text-slate-500 cursor-not-allowed select-none"
              />
            </div>
          </form>
        </div>

        {/* Chân modal (Actions) */}
        <div className="flex items-center justify-end gap-2.5 px-6 py-4 border-t border-slate-100 bg-white shrink-0">
          <button
            type="button"
            onClick={onClose}
            disabled={saving}
            className="px-4 py-2 rounded-xl text-[13px] font-semibold text-slate-600 hover:bg-slate-100 transition"
          >
            {t("Hủy")}
          </button>
          <button
            type="submit"
            form="profile-form"
            disabled={saving}
            className="inline-flex items-center gap-2 px-5 py-2 rounded-xl bg-[#1E40AF] hover:bg-[#1D4ED8] text-white text-[13px] font-semibold shadow-2xs transition active:scale-[0.98] disabled:opacity-70"
          >
            {saving ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>{t("Đang lưu...")}</span>
              </>
            ) : (
              <>
                <Sparkles className="w-3.5 h-3.5" />
                <span>{t("Lưu thay đổi")}</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );

  return createPortal(modalContent, document.body);
}
