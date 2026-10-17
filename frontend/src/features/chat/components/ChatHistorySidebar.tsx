"use client";
import { useLocale } from "@/features/shared/context/LocaleContext";
import { parseServerTimestamp } from "@/lib/utils";

import React, { useState, useEffect, useMemo, useRef } from "react";
import { createPortal } from "react-dom";
import Link from "next/link";
import {
  Plus,
  Search,
  MoreHorizontal,
  ChevronLeft,
  Trash2,
  Edit2,
  Check,
  X,
  LogIn,
  AlertCircle,
  RotateCcw,
} from "lucide-react";
import { ChatSessionItem } from "../types";
import {
  fetchChatSessions,
  updateChatSessionTitle,
  deleteChatSession,
  deleteAllChatSessions,
} from "../api/chatApi";

interface ChatHistorySidebarProps {
  currentSessionId: string;
  onSelectSession: (sessionId: string) => void;
  onNewChat: () => void;
  isOpen: boolean;
  onToggleCollapse: () => void;
  isGuest: boolean;
  userId?: string;
  isMobileDrawer?: boolean;
  onCloseMobileDrawer?: () => void;
  refreshTrigger?: number;
  onModalOpenChange?: (isOpen: boolean) => void;
}

interface GroupedSessions {
  today: ChatSessionItem[];
  yesterday: ChatSessionItem[];
  last7Days: ChatSessionItem[];
  older: ChatSessionItem[];
}

export function ChatHistorySidebar({
  currentSessionId,
  onSelectSession,
  onNewChat,
  isOpen,
  onToggleCollapse,
  isGuest,
  userId,
  isMobileDrawer = false,
  onCloseMobileDrawer,
  refreshTrigger,
  onModalOpenChange,
}: ChatHistorySidebarProps) {
  const { t } = useLocale();
  const [mounted, setMounted] = useState(false);
  const [sessions, setSessions] = useState<ChatSessionItem[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState("");
  const [activeMenuSessionId, setActiveMenuSessionId] = useState<string | null>(null);
  const [showClearAllConfirm, setShowClearAllConfirm] = useState(false);
  const [isClearingAll, setIsClearingAll] = useState(false);
  const [clearAllError, setClearAllError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const isNotFoundRef = useRef(false);
  const inFlightRef = useRef(false);
  const retryTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  // Đảm bảo mount an toàn ở client cho createPortal
  useEffect(() => {
    setMounted(true);
    return () => {
      if (retryTimeoutRef.current) clearTimeout(retryTimeoutRef.current);
    };
  }, []);

  // Thông báo trạng thái modal ra bên ngoài để khóa ô nhập/nút Gửi
  useEffect(() => {
    onModalOpenChange?.(showClearAllConfirm);
  }, [showClearAllConfirm, onModalOpenChange]);

  // Đóng modal bằng Escape (nhưng không đóng khi đang thực hiện xóa)
  useEffect(() => {
    if (!showClearAllConfirm) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !isClearingAll) {
        setShowClearAllConfirm(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [showClearAllConfirm, isClearingAll]);

  // Tải danh sách session
  const loadSessions = async (force: boolean = false) => {
    // Không tải nếu là mobile drawer đang đóng (tránh gọi dư thừa trong nền)
    if (isMobileDrawer && !isOpen && !force) {
      return;
    }
    // Nếu API đã trả 404 và không phải do người dùng bấm thử lại thủ công (force), dừng auto retry
    if (isNotFoundRef.current && !force) {
      return;
    }
    // Tránh gọi trùng lặp song song
    if (inFlightRef.current && !force) {
      return;
    }

    try {
      inFlightRef.current = true;
      setLoading(true);
      const res = await fetchChatSessions();
      if (res.success && res.data?.sessions) {
        setSessions(res.data.sessions);
        setLoadError(null);
        isNotFoundRef.current = false;
        if (retryTimeoutRef.current) {
          clearTimeout(retryTimeoutRef.current);
          retryTimeoutRef.current = null;
        }
      }
    } catch (err: any) {
      const is404 = err?.status === 404 || String(err?.message || "").includes("404");
      if (is404) {
        isNotFoundRef.current = true;
        setLoadError(t("Dịch vụ lịch sử trò chuyện chưa sẵn sàng (404 Not Found)."));
        // Tự động thử lại 1 lần sau 4s phòng trường hợp backend đang khởi động/reload
        if (!retryTimeoutRef.current) {
          retryTimeoutRef.current = setTimeout(() => {
            retryTimeoutRef.current = null;
            isNotFoundRef.current = false;
            loadSessions(true);
          }, 4000);
        }
      } else {
        setLoadError(err?.message || t("Không thể tải danh sách cuộc trò chuyện."));
      }
    } finally {
      inFlightRef.current = false;
      setLoading(false);
    }
  };

  // Tự động phục hồi khi người dùng focus lại tab trình duyệt
  useEffect(() => {
    const handleFocus = () => {
      if (isNotFoundRef.current || loadError) {
        isNotFoundRef.current = false;
        setLoadError(null);
        loadSessions(true);
      }
    };
    window.addEventListener("focus", handleFocus);
    return () => window.removeEventListener("focus", handleFocus);
  }, [loadError]);

  // Khi đổi tài khoản hoặc đăng xuất: reset toàn bộ state sidebar và refetch
  const lastUserRef = useRef(userId);
  useEffect(() => {
    if (lastUserRef.current !== userId) {
      lastUserRef.current = userId;
      setSessions([]);
      setSearchQuery("");
      setActionError(null);
      setClearAllError(null);
      setEditingSessionId(null);
      setActiveMenuSessionId(null);
      setShowClearAllConfirm(false);
      isNotFoundRef.current = false;
      setLoadError(null);
      if (retryTimeoutRef.current) {
        clearTimeout(retryTimeoutRef.current);
        retryTimeoutRef.current = null;
      }
      loadSessions(true);
    }
  }, [userId]);

  // Đóng drawer trên mobile khi nhấn Escape
  useEffect(() => {
    if (!isMobileDrawer || !isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && onCloseMobileDrawer) {
        onCloseMobileDrawer();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isMobileDrawer, isOpen, onCloseMobileDrawer]);

  // Đóng popover menu khi click ra ngoài
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setActiveMenuSessionId(null);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useEffect(() => {
    if (isMobileDrawer && !isOpen) {
      return;
    }
    loadSessions();
  }, [currentSessionId, isGuest, refreshTrigger, isOpen, isMobileDrawer]);

  // Phân nhóm session theo thời gian
  const groupedSessions = useMemo(() => {
    const now = new Date();
    const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
    const yesterdayStart = todayStart - 86400000;
    const sevenDaysAgoStart = todayStart - 6 * 86400000;

    const filtered = sessions.filter((s) =>
      s.title.toLowerCase().includes(searchQuery.trim().toLowerCase())
    );

    const groups: GroupedSessions = {
      today: [],
      yesterday: [],
      last7Days: [],
      older: [],
    };

    filtered.forEach((session) => {
      const time = parseServerTimestamp(session.updated_at).getTime();
      if (time >= todayStart) {
        groups.today.push(session);
      } else if (time >= yesterdayStart) {
        groups.yesterday.push(session);
      } else if (time >= sevenDaysAgoStart) {
        groups.last7Days.push(session);
      } else {
        groups.older.push(session);
      }
    });

    return groups;
  }, [sessions, searchQuery]);

  // Bắt đầu chỉnh sửa tiêu đề
  const handleStartEdit = (session: ChatSessionItem) => {
    setEditingSessionId(session.session_id);
    setEditingTitle(session.title);
    setActiveMenuSessionId(null);
  };

  // Lưu tiêu đề mới (giới hạn 50 ký tự, không lưu rỗng)
  const handleSaveTitle = async (sessionId: string) => {
    const trimmed = editingTitle.trim();
    if (!trimmed) {
      setEditingSessionId(null);
      return;
    }
    const finalTitle = trimmed.slice(0, 50);
    setActionError(null);
    try {
      await updateChatSessionTitle(sessionId, finalTitle);
      setSessions((prev) =>
        prev.map((s) => (s.session_id === sessionId ? { ...s, title: finalTitle } : s))
      );
    } catch (err: any) {
      setActionError(err?.message || t("Không thể đổi tên cuộc trò chuyện."));
    } finally {
      setEditingSessionId(null);
    }
  };

  // Xóa một session (tự động chuyển sang session kế tiếp nếu đang mở session bị xóa)
  const handleDelete = async (sessionId: string) => {
    setActiveMenuSessionId(null);
    setActionError(null);
    try {
      await deleteChatSession(sessionId);
      const remaining = sessions.filter((s) => s.session_id !== sessionId);
      setSessions(remaining);
      if (sessionId === currentSessionId) {
        if (remaining.length > 0) {
          onSelectSession(remaining[0].session_id);
        } else {
          onNewChat();
        }
      }
    } catch (err: any) {
      setActionError(err?.message || t("Không thể xóa cuộc trò chuyện."));
    }
  };

  // Xóa toàn bộ lịch sử trò chuyện (giữ modal mở nếu có lỗi để người dùng thấy thông báo)
  const handleClearAll = async () => {
    setIsClearingAll(true);
    setClearAllError(null);
    try {
      await deleteAllChatSessions();
      setSessions([]);
      setShowClearAllConfirm(false);
      onNewChat();
    } catch (err: any) {
      setClearAllError(err?.message || t("Không thể xóa tất cả cuộc trò chuyện. Vui lòng thử lại."));
    } finally {
      setIsClearingAll(false);
    }
  };

  // Render một nhóm session
  const renderSessionGroup = (title: string, groupList: ChatSessionItem[]) => {
    if (groupList.length === 0) return null;

    return (
      <div className="mb-4">
        <div className="px-2.5 mb-1.5 text-[11px] font-semibold text-slate-600 tracking-wider">
          {title}
        </div>
        <div className="space-y-0.5">
          {groupList.map((session) => {
            const isActive = session.session_id === currentSessionId;
            const isEditing = editingSessionId === session.session_id;

            if (isEditing) {
              return (
                <div
                  key={session.session_id}
                  className="flex items-center gap-1.5 px-2 py-1.5 rounded-lg bg-white border border-blue-300 shadow-2xs"
                >
                  <input
                    type="text"
                    value={editingTitle}
                    maxLength={50}
                    onChange={(e) => setEditingTitle(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") handleSaveTitle(session.session_id);
                      if (e.key === "Escape") setEditingSessionId(null);
                    }}
                    autoFocus
                    className="flex-1 bg-transparent text-[12.5px] text-slate-800 outline-none min-w-0"
                  />
                  <button
                    type="button"
                    onClick={() => handleSaveTitle(session.session_id)}
                    className="p-1 rounded text-emerald-600 hover:bg-emerald-50 transition"
                    title={t("Lưu")}
                  >
                    <Check className="w-3.5 h-3.5" />
                  </button>
                  <button
                    type="button"
                    onClick={() => setEditingSessionId(null)}
                    className="p-1 rounded text-slate-400 hover:bg-slate-100 transition"
                    title={t("Hủy")}
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              );
            }

            return (
              <div
                key={session.session_id}
                className={`group relative flex items-center justify-between rounded-lg px-2.5 py-2 text-[12.5px] cursor-pointer transition ${
                  isActive
                    ? "bg-blue-50 text-[#1E40AF] font-medium border border-blue-200/80 shadow-2xs"
                    : "text-slate-700 hover:bg-slate-100/90 hover:text-slate-900"
                }`}
                onClick={() => {
                  onSelectSession(session.session_id);
                  if (isMobileDrawer && onCloseMobileDrawer) {
                    onCloseMobileDrawer();
                  }
                }}
              >
                <div className="flex-1 min-w-0 pr-2">
                  <p className="truncate leading-tight select-none" title={session.title}>
                    {session.title}
                  </p>
                </div>

                {/* Menu nút ba chấm (hover hoặc đang mở) */}
                <div className="shrink-0 relative">
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      setActiveMenuSessionId(
                        activeMenuSessionId === session.session_id ? null : session.session_id
                      );
                    }}
                    className={`p-1 rounded-md text-slate-400 hover:text-slate-700 hover:bg-white/80 transition ${
                      isActive || activeMenuSessionId === session.session_id
                        ? "opacity-100"
                        : "opacity-0 group-hover:opacity-100"
                    }`}
                    title={t("Tùy chọn cuộc trò chuyện")}
                  >
                    <MoreHorizontal className="w-3.5 h-3.5" />
                  </button>

                  {/* Popover Menu Đổi tên / Xóa */}
                  {activeMenuSessionId === session.session_id && (
                    <div
                      ref={menuRef}
                      className="absolute right-0 top-full mt-1 w-32 rounded-xl bg-white border border-slate-200/90 shadow-lg py-1 z-50 animate-fadeIn"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <button
                        type="button"
                        onClick={() => handleStartEdit(session)}
                        className="w-full flex items-center gap-2 px-3 py-1.5 text-[12px] text-slate-700 hover:bg-slate-50 transition"
                      >
                        <Edit2 className="w-3.5 h-3.5 text-slate-400" />
                        <span>{t("Đổi tên")}</span>
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDelete(session.session_id)}
                        className="w-full flex items-center gap-2 px-3 py-1.5 text-[12px] text-rose-600 hover:bg-rose-50 transition"
                      >
                        <Trash2 className="w-3.5 h-3.5 text-rose-500" />
                        <span>{t("Xóa")}</span>
                      </button>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  const hasAnySession = sessions.length > 0;

  const sidebarContent = (
    <div className="flex flex-col h-full bg-slate-50/70 select-none">
      {/* 1. Header Sidebar */}
      <div className="px-3.5 py-2.5 flex items-center justify-between border-b border-slate-200/80">
        <span className="text-[12.5px] font-bold text-slate-800">
          {t("Lịch sử trò chuyện")}</span>
        <button
          type="button"
          onClick={isMobileDrawer ? onCloseMobileDrawer : onToggleCollapse}
          className="p-1.5 rounded-lg text-slate-500 hover:text-slate-800 hover:bg-slate-200/70 transition active:scale-95"
          title={t("Thu gọn sidebar")}
        >
          <ChevronLeft className="w-4 h-4" />
        </button>
      </div>

      {/* 2. Nút Cuộc trò chuyện mới & Ô tìm kiếm */}
      <div className="p-3 space-y-2 border-b border-slate-200/70">
        <button
          type="button"
          onClick={() => {
            onNewChat();
            if (isMobileDrawer && onCloseMobileDrawer) {
              onCloseMobileDrawer();
            }
          }}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-xl bg-[#1E40AF] hover:bg-[#1D4ED8] text-white text-[12.5px] font-semibold shadow-xs transition active:scale-98"
        >
          <Plus className="w-4 h-4 shrink-0" />
          <span>{t("Cuộc trò chuyện mới")}</span>
        </button>

        {/* Ô tìm kiếm */}
        <div className="relative">
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder={t("Tìm kiếm cuộc trò chuyện...")}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-8 pr-2.5 py-1.5 text-[12px] bg-white border border-slate-200 rounded-lg text-slate-800 placeholder-slate-400 outline-none focus:border-blue-400 transition"
          />
        </div>
      </div>

      {/* 3. Danh sách session có phân nhóm */}
      <div className="flex-1 overflow-y-auto p-2 scrollbar-thin scrollbar-thumb-slate-200">
        {actionError && (
          <div className="mb-2 p-2 rounded-lg bg-rose-50 border border-rose-200/80 text-rose-700 text-[11px] leading-snug flex items-center justify-between gap-1.5 animate-fadeIn">
            <span className="truncate">{actionError}</span>
            <button
              type="button"
              onClick={() => setActionError(null)}
              className="text-rose-500 hover:text-rose-800 p-0.5 rounded shrink-0 transition"
              title={t("Đóng thông báo lỗi")}
            >
              <X className="w-3 h-3" />
            </button>
          </div>
        )}

        {loading && sessions.length === 0 ? (
          <div className="py-8 text-center text-[12px] text-slate-400">
            {t("Đang tải lịch sử...")}</div>
        ) : loadError && sessions.length === 0 ? (
          <div className="py-10 text-center px-4">
            <div className="w-8 h-8 rounded-full bg-rose-50 text-rose-500 flex items-center justify-center mx-auto mb-2.5">
              <AlertCircle className="w-4 h-4" />
            </div>
            <p className="text-[12px] text-slate-700 font-medium mb-1">{t("Không thể tải lịch sử")}</p>
            <p className="text-[11px] text-slate-400 mb-3 line-clamp-2">{loadError}</p>
            <button
              type="button"
              onClick={() => {
                isNotFoundRef.current = false;
                setLoadError(null);
                loadSessions(true);
              }}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px] font-medium text-blue-600 bg-blue-50 hover:bg-blue-100 transition shadow-xs cursor-pointer"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>{t("Thử lại")}</span>
            </button>
          </div>
        ) : !hasAnySession ? (
          <div className="py-12 text-center text-[12px] text-slate-400 px-4">
            {t("Chưa có cuộc trò chuyện nào")}</div>
        ) : (
          <>
            {renderSessionGroup(t("HÔM NAY"), groupedSessions.today)}
            {renderSessionGroup(t("HÔM QUA"), groupedSessions.yesterday)}
            {renderSessionGroup(t("7 NGÀY QUA"), groupedSessions.last7Days)}
            {renderSessionGroup(t("CŨ HƠN"), groupedSessions.older)}

            {/* Nút Xóa tất cả lịch sử */}
            <div className="pt-2 pb-1 px-1 border-t border-slate-200/60 mt-2 text-center">
              <button
                type="button"
                onClick={() => {
                  setClearAllError(null);
                  setShowClearAllConfirm(true);
                }}
                className="inline-flex items-center justify-center gap-1.5 py-1 px-2 rounded-md text-[11px] text-slate-400 hover:text-rose-600 hover:bg-rose-50/70 transition"
                title={t("Xóa tất cả các cuộc trò chuyện")}
              >
                <Trash2 className="w-3 h-3" />
                <span>{t("Xóa tất cả cuộc trò chuyện")}</span>
              </button>
            </div>
          </>
        )}
      </div>

      {/* 4. Banner Đăng nhập cho Guest ở đáy sidebar */}
      {isGuest && (
        <div className="p-3 border-t border-slate-200/80 bg-white/80">
          <div className="p-2.5 rounded-xl bg-blue-50/80 border border-blue-200/70 text-slate-700">
            <p className="text-[11.5px] font-medium leading-relaxed mb-2 text-slate-800">
              {t("Đăng nhập để lưu và xem lại lịch sử trò chuyện trên mọi thiết bị.")}</p>
            <Link
              href="/login"
              className="w-full inline-flex items-center justify-center gap-1.5 py-1.5 px-3 rounded-lg bg-[#1E40AF] hover:bg-[#1D4ED8] text-white text-[11.5px] font-semibold transition"
            >
              <LogIn className="w-3.5 h-3.5" />
              <span>{t("Đăng nhập ngay")}</span>
            </Link>
          </div>
        </div>
      )}

      {/* Modal Xác nhận Xóa tất cả render qua createPortal ra document.body */}
      {showClearAllConfirm && mounted && typeof document !== "undefined" && createPortal(
        <div
          className="fixed inset-0 z-[1000] flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4 animate-fadeIn"
          onClick={() => {
            if (!isClearingAll) setShowClearAllConfirm(false);
          }}
        >
          <div
            className="bg-white rounded-2xl p-5 max-w-xs w-full shadow-2xl border border-slate-200/90 animate-scaleIn relative"
            onClick={(e) => e.stopPropagation()}
          >
            <h4 className="font-bold text-[14px] text-slate-900 mb-1.5">
              {t("Xóa tất cả cuộc trò chuyện?")}</h4>
            <p className="text-[12px] text-slate-500 mb-3.5 leading-relaxed">
              {t("Toàn bộ lịch sử trò chuyện của bạn sẽ bị xóa vĩnh viễn và không thể khôi phục.")}</p>

            {clearAllError && (
              <div className="mb-3.5 p-2.5 rounded-lg bg-rose-50 border border-rose-200/80 text-rose-700 text-[11px] leading-snug flex items-start gap-1.5 animate-fadeIn">
                <span className="font-semibold shrink-0">{t("Lỗi:")}</span>
                <span className="break-words">{clearAllError}</span>
              </div>
            )}

            <div className="flex items-center justify-end gap-2">
              <button
                type="button"
                onClick={() => {
                  if (!isClearingAll) setShowClearAllConfirm(false);
                }}
                disabled={isClearingAll}
                className="px-3 py-1.5 rounded-lg text-[12px] font-medium text-slate-600 hover:bg-slate-100 transition disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {t("Hủy")}</button>
              <button
                type="button"
                onClick={handleClearAll}
                disabled={isClearingAll}
                className="px-3.5 py-1.5 rounded-lg text-[12px] font-medium bg-rose-600 hover:bg-rose-700 text-white transition shadow-2xs disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isClearingAll ? t("Đang xóa...") : t("Xác nhận xóa")}
              </button>
            </div>
          </div>
        </div>,
        document.body
      )}
    </div>
  );

  // Với Drawer trên Mobile
  if (isMobileDrawer) {
    if (!isOpen) return null;
    return (
      <div className="fixed inset-0 z-50 lg:hidden flex">
        {/* Backdrop mờ */}
        <div
          className="fixed inset-0 bg-slate-900/40 backdrop-blur-2xs animate-fadeIn"
          onClick={onCloseMobileDrawer}
        />
        {/* Sheet trượt từ trái */}
        <div className="relative w-[280px] max-w-[85vw] h-full bg-white shadow-2xl z-10 animate-slideRight">
          {sidebarContent}
        </div>
      </div>
    );
  }

  // Desktop: Khi thu gọn thì ẩn
  if (!isOpen) {
    return null;
  }

  return (
    <div className="hidden lg:flex w-[260px] shrink-0 border-r border-slate-200/80 h-full flex-col">
      {sidebarContent}
    </div>
  );
}
