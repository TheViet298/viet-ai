"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import { TicketItem, TicketPriority, TicketStatus } from "../types";
import { getTicketQueue } from "../api/consoleApi";

export const INITIAL_TICKETS: TicketItem[] = [
  {
    id: "CASE-20260924-001",
    mock_customer_id: "CUST_MOCK_01",
    vehicle_model: "VF8",
    vehicle_code_mock: "VF-SF-00231",
    intent: "Charging/Battery",
    priority: "HIGH",
    status: "Staff Reviewing",
    missing_info_flag: false,
    created_at: "2026-09-24T08:30:00Z",
    confidence_score: 0.92,
    issue_summary: "Trụ P02 Vincom Metropolis lỗi CC01 không sạc được DC",
    suggested_action: "Kiểm tra handshake trụ sạc P02 từ xa hoặc cử nhân viên trạm khởi động lại module",
    has_location_consent: true,
    error_code_short: "CC01",
  },
  {
    id: "CASE-20260924-002",
    mock_customer_id: "CUST_MOCK_99",
    vehicle_model: "VF8",
    vehicle_code_mock: "VF-SF-99120",
    intent: "Service/Incident",
    priority: "CRITICAL",
    status: "Staff Reviewing",
    missing_info_flag: false,
    created_at: "2026-09-24T08:35:00Z",
    confidence_score: 0.95,
    issue_summary: "Cảnh báo rùa vàng & mất trợ lực lái nhẹ trên cao tốc Long Thành",
    suggested_action: "Kích hoạt cứu hộ 24/7 khẩn cấp, hướng dẫn tài xế đứng sau rào hộ lan an toàn",
    has_location_consent: true,
    error_code_short: "TURTLE_WARN",
  },
  {
    id: "CASE-20260924-003",
    mock_customer_id: "CUST_MOCK_02",
    vehicle_model: "VF5",
    vehicle_code_mock: "VF-SF-00445",
    intent: "Service/Incident",
    priority: "MEDIUM",
    status: "Needs Information",
    missing_info_flag: true,
    created_at: "2026-09-24T08:40:00Z",
    confidence_score: 0.65,
    issue_summary: "Đèn cảnh báo rùa vàng do dung lượng pin dưới 10% trong đô thị",
    suggested_action: "Yêu cầu khách chụp ảnh táp-lô và hướng dẫn tới điểm sạc gần nhất 500m",
    has_location_consent: false,
    error_code_short: "RÙA VÀNG",
  },
  {
    id: "CASE-20260924-004",
    mock_customer_id: "CUST_MOCK_15",
    vehicle_model: "VF9",
    vehicle_code_mock: "VF-SF-00789",
    intent: "Charging/Battery",
    priority: "LOW",
    status: "In Progress",
    missing_info_flag: false,
    created_at: "2026-09-24T07:15:00Z",
    confidence_score: 0.88,
    issue_summary: "Bộ sạc tại nhà 7.4kW tự động ngắt sau 2 tiếng sạc ban đêm",
    suggested_action: "Kiểm tra nhiệt độ dây nguồn và cài đặt giới hạn dòng sạc trên xe",
    has_location_consent: true,
    error_code_short: "WALLBOX_AC",
  },
  {
    id: "CASE-20260924-005",
    mock_customer_id: "CUST_MOCK_23",
    vehicle_model: "VF6",
    vehicle_code_mock: "VF-SF-00612",
    intent: "Service/Incident",
    priority: "HIGH",
    status: "Resolved",
    missing_info_flag: false,
    created_at: "2026-09-24T06:45:00Z",
    confidence_score: 0.94,
    issue_summary: "Cảnh báo áp suất lốp TPMS bánh sau bên phụ tụt còn 1.8 bar",
    suggested_action: "Đã hướng dẫn ghé xưởng VinFast Trần Duy Hưng bơm lốp tiêu chuẩn 2.4 bar",
    has_location_consent: true,
    error_code_short: "TPMS_1.8",
  },
];

export type SortOption = "NEWEST" | "PRIORITY_DESC" | "CONFIDENCE_DESC";

export function useTickets() {
  const [tickets, setTickets] = useState<TicketItem[]>(INITIAL_TICKETS);
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [priorityFilter, setPriorityFilter] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [sortBy, setSortBy] = useState<SortOption>("NEWEST");
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [isLiveApi, setIsLiveApi] = useState<boolean>(false);

  const fetchTickets = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getTicketQueue({
        status: statusFilter !== "ALL" ? statusFilter : undefined,
        priority: priorityFilter !== "ALL" ? priorityFilter : undefined,
      });
      if (res && res.success && res.data?.items) {
        setTickets(res.data.items);
        setIsLiveApi(true);
      }
    } catch {
      // Fallback to initial state if backend is not reachable
      setIsLiveApi(false);
    } finally {
      setLoading(false);
    }
  }, [statusFilter, priorityFilter]);

  useEffect(() => {
    let isMounted = true;
    const load = async () => {
      setLoading(true);
      try {
        const res = await getTicketQueue({
          status: statusFilter !== "ALL" ? statusFilter : undefined,
          priority: priorityFilter !== "ALL" ? priorityFilter : undefined,
        });
        if (isMounted && res && res.success && res.data?.items) {
          setTickets(res.data.items);
          setIsLiveApi(true);
        }
      } catch {
        if (isMounted) setIsLiveApi(false);
      } finally {
        if (isMounted) setLoading(false);
      }
    };
    load();
    return () => {
      isMounted = false;
    };
  }, [statusFilter, priorityFilter]);

  const priorityWeight: Record<TicketPriority, number> = {
    CRITICAL: 4,
    HIGH: 3,
    MEDIUM: 2,
    LOW: 1,
  };

  const filteredTickets = useMemo(() => {
    return tickets
      .filter((t) => {
        // Status filter
        if (statusFilter !== "ALL" && t.status !== statusFilter) return false;
        // Priority filter
        if (priorityFilter !== "ALL" && t.priority !== priorityFilter) return false;
        // Search query
        if (searchQuery.trim()) {
          const q = searchQuery.toLowerCase().trim();
          const matchId = t.id.toLowerCase().includes(q);
          const matchCust = t.mock_customer_id.toLowerCase().includes(q);
          const matchModel = t.vehicle_model.toLowerCase().includes(q);
          const matchCode = (t.vehicle_code_mock || "").toLowerCase().includes(q);
          const matchIntent = t.intent.toLowerCase().includes(q);
          if (!matchId && !matchCust && !matchModel && !matchCode && !matchIntent) {
            return false;
          }
        }
        return true;
      })
      .sort((a, b) => {
        if (sortBy === "PRIORITY_DESC") {
          return (priorityWeight[b.priority] || 0) - (priorityWeight[a.priority] || 0);
        }
        if (sortBy === "CONFIDENCE_DESC") {
          return b.confidence_score - a.confidence_score;
        }
        // Default: NEWEST
        return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
      });
  }, [tickets, statusFilter, priorityFilter, searchQuery, sortBy]);

  // Aggregate stats across all loaded tickets
  const stats = useMemo(() => {
    return {
      total: tickets.length,
      reviewing: tickets.filter((t) => t.status === "Staff Reviewing").length,
      critical: tickets.filter((t) => t.priority === "CRITICAL").length,
      needsInfo: tickets.filter((t) => t.status === "Needs Information").length,
      inProgress: tickets.filter((t) => t.status === "In Progress").length,
      resolved: tickets.filter((t) => t.status === "Resolved").length,
    };
  }, [tickets]);

  const resetFilters = useCallback(() => {
    setStatusFilter("ALL");
    setPriorityFilter("ALL");
    setSearchQuery("");
    setSortBy("NEWEST");
  }, []);

  return {
    tickets,
    setTickets,
    filteredTickets,
    statusFilter,
    setStatusFilter,
    priorityFilter,
    setPriorityFilter,
    searchQuery,
    setSearchQuery,
    sortBy,
    setSortBy,
    loading,
    error,
    isLiveApi,
    refreshTickets: fetchTickets,
    resetFilters,
    reviewingCount: stats.reviewing,
    criticalCount: stats.critical,
    stats,
  };
}
