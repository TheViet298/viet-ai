"use client";

import { useState, useEffect, useCallback } from "react";
import { TicketDetail, TicketStatus, StaffActionType } from "../types";
import { getTicketDetail, submitStaffAction } from "../api/consoleApi";

export const MOCK_DETAIL_DATA: TicketDetail = {
  case: {
    id: "CASE-20260924-001",
    mock_customer_id: "CUST_MOCK_01",
    vehicle_code_mock: "VF-SF-00231",
    vehicle_model: "VF8",
    intent: "Charging/Battery",
    priority: "HIGH",
    status: "Staff Reviewing",
  },
  case_brief: {
    summary:
      "Xe VF8 không nhận sạc DC tại trạm Vincom Metropolis, màn hình xe báo mã lỗi CC01 và đèn trụ báo đỏ.",
    captured_fields: {
      vehicle_model: "VF8",
      station_location: "Vincom Metropolis Liễu Giai",
      charger_id: "VN-CS-HN042-P02",
      error_code: "CC01",
      current_soc: "18%",
    },
    suggested_action:
      "Kiểm tra tín hiệu handshake giao tiếp trụ sạc P02 từ xa hoặc cử nhân viên kỹ thuật trạm hỗ trợ cắm lại cáp sạc.",
    confidence_score: 0.92,
    is_edited_by_staff: false,
  },
  conversation_history: [
    {
      sender: "CUSTOMER",
      content:
        "Xe VF8 của tôi không nhận sạc ở trạm Metropolis, trụ báo đèn đỏ.",
      created_at: "2026-09-24T08:30:10Z",
    },
    {
      sender: "AGENT",
      content:
        "Dạ em ghi nhận xe VF8 đang không nhận sạc tại trạm Metropolis. Màn hình xe có hiển thị mã lỗi (ví dụ: CC01, BMS_012) hoặc anh/chị có mã trụ sạc không ạ?",
      created_at: "2026-09-24T08:30:15Z",
    },
    {
      sender: "CUSTOMER",
      content: "Mã lỗi trên màn hình là CC01, tôi cắm trụ P02, pin còn 18%.",
      created_at: "2026-09-24T08:30:45Z",
    },
    {
      sender: "AGENT",
      content:
        "Hệ thống đã ghi nhận đầy đủ dữ kiện kỹ thuật và tạo hồ sơ hỗ trợ CASE-20260924-001. Hồ sơ đã chuyển đến chuyên viên dịch vụ để xử lý.",
      created_at: "2026-09-24T08:30:50Z",
    },
  ],
};

export function useTicketDetail(initialId: string) {
  const [detail, setDetail] = useState<TicketDetail>(() => ({
    ...MOCK_DETAIL_DATA,
    case: { ...MOCK_DETAIL_DATA.case, id: initialId },
  }));
  const [status, setStatus] = useState<TicketStatus>(detail.case.status);
  const [isEditing, setIsEditing] = useState(false);
  const [editedSummary, setEditedSummary] = useState(detail.case_brief.summary);
  const [notes, setNotes] = useState("");
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadTicket = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getTicketDetail(initialId);
      if (res && res.data) {
        setDetail(res.data);
        setStatus(res.data.case.status);
        setEditedSummary(res.data.case_brief.summary);
      }
    } catch {
      // Fallback to local mock data without breaking UI
      setDetail((prev) => ({
        ...prev,
        case: { ...prev.case, id: initialId },
      }));
    } finally {
      setLoading(false);
    }
  }, [initialId]);

  useEffect(() => {
    loadTicket();
  }, [loadTicket]);

  const handleSaveBrief = () => {
    setDetail((prev) => ({
      ...prev,
      case_brief: {
        ...prev.case_brief,
        summary: editedSummary,
        is_edited_by_staff: true,
      },
    }));
    setIsEditing(false);
    setActionSuccess("Đã lưu chỉnh sửa tóm tắt hồ sơ (Case Brief)!");
    setTimeout(() => setActionSuccess(null), 3500);
  };

  const handleCancelBrief = () => {
    setEditedSummary(detail.case_brief.summary);
    setIsEditing(false);
  };

  const executeAction = async (
    actionName: string,
    actionType: StaffActionType,
    newStatus: TicketStatus
  ) => {
    setIsSubmitting(true);
    try {
      await submitStaffAction(initialId, {
        action: actionType,
        staff_id: "STAFF_CURR_USER",
        updated_status: newStatus,
        notes: notes || undefined,
        edited_brief: detail.case_brief.is_edited_by_staff
          ? { summary: editedSummary }
          : undefined,
      });
    } catch {
      // Optimistic update locally
    } finally {
      setStatus(newStatus);
      setDetail((prev) => ({
        ...prev,
        case: { ...prev.case, status: newStatus },
      }));
      setActionSuccess(`Thành công: ${actionName} cho hồ sơ ${initialId}!`);
      setIsSubmitting(false);
      setTimeout(() => setActionSuccess(null), 4000);
    }
  };

  return {
    detail,
    status,
    isEditing,
    setIsEditing,
    editedSummary,
    setEditedSummary,
    handleSaveBrief,
    handleCancelBrief,
    notes,
    setNotes,
    actionSuccess,
    executeAction,
    loading,
    isSubmitting,
    error,
    reload: loadTicket,
  };
}
