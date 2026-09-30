"use client";

import { useEffect, useState } from "react";
import { TicketItem } from "../types";
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
  },
];

export function useTickets() {
  const [tickets, setTickets] = useState<TicketItem[]>(INITIAL_TICKETS);
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [priorityFilter, setPriorityFilter] = useState<string>("ALL");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let isMounted = true;
    const fetchTickets = async () => {
      setLoading(true);
      try {
        const res = await getTicketQueue({
          status: statusFilter,
          priority: priorityFilter,
        });
        if (isMounted && res.success && res.data?.items) {
          setTickets(res.data.items);
        }
      } catch {
        // Fallback to initial state if backend is not reachable
      } finally {
        if (isMounted) setLoading(false);
      }
    };
    fetchTickets();
    return () => {
      isMounted = false;
    };
  }, [statusFilter, priorityFilter]);

  const filteredTickets = tickets.filter((t) => {
    if (statusFilter !== "ALL" && t.status !== statusFilter) return false;
    if (priorityFilter !== "ALL" && t.priority !== priorityFilter) return false;
    return true;
  });

  const reviewingCount = tickets.filter((t) => t.status === "Staff Reviewing").length;
  const criticalCount = tickets.filter((t) => t.priority === "CRITICAL").length;

  return {
    tickets,
    setTickets,
    filteredTickets,
    statusFilter,
    setStatusFilter,
    priorityFilter,
    setPriorityFilter,
    loading,
    reviewingCount,
    criticalCount,
  };
}
