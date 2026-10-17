"use client";

import { useState, useEffect, useCallback, useMemo, useRef } from "react";
import { TicketItem, TicketPriority, TicketStatus } from "../types";
export type { TicketItem, TicketPriority, TicketStatus };
import { getTicketQueue } from "../api/consoleApi";

export type SortOption = "NEWEST" | "PRIORITY_DESC" | "CONFIDENCE_DESC";

export function useTickets() {
  const [tickets, setTickets] = useState<TicketItem[]>([]);
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [priorityFilter, setPriorityFilter] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [sortBy, setSortBy] = useState<SortOption>("NEWEST");
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isLiveApi, setIsLiveApi] = useState<boolean>(false);

  const requestId = useRef(0);

  const fetchTickets = useCallback(async () => {
    const currentRequest = ++requestId.current;
    setLoading(true);
    setError(null);
    try {
      const res = await getTicketQueue({
        status: statusFilter !== "ALL" ? statusFilter : undefined,
        priority: priorityFilter !== "ALL" ? priorityFilter : undefined,
      });
      if (currentRequest !== requestId.current) return;
      if (!res?.success || !Array.isArray(res.data?.items)) {
        throw new Error("Invalid queue response");
      }
      setTickets(res.data.items);
      setIsLiveApi(true);
    } catch {
      if (currentRequest !== requestId.current) return;
      setTickets([]);
      setIsLiveApi(false);
      setError("Không thể tải hàng đợi. Vui lòng thử lại.");
    } finally {
      if (currentRequest === requestId.current) setLoading(false);
    }
  }, [statusFilter, priorityFilter]);

  useEffect(() => {
    void fetchTickets();
    return () => { requestId.current += 1; };
  }, [fetchTickets]);

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
          const matchCust = (
            t.customer_name
              ? `${t.customer_name} ${t.mock_customer_id} ${t.customer_phone || ""}`
              : t.mock_customer_id
          ).toLowerCase().includes(q);
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
        // Mặc định (NEWEST): Luôn ghim ca Khẩn cấp (CRITICAL) lên trên cùng, sau đó xếp theo thời gian mới nhất
        if (a.priority === "CRITICAL" && b.priority !== "CRITICAL") return -1;
        if (b.priority === "CRITICAL" && a.priority !== "CRITICAL") return 1;
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
