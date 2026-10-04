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
      if (res && res.success && res.data) {
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
    let isMounted = true;
    const fetchDetail = async () => {
      setLoading(true);
      try {
        const res = await getTicketDetail(initialId);
        if (isMounted && res && res.success && res.data) {
          setDetail(res.data);
          setStatus(res.data.case.status);
          setEditedSummary(res.data.case_brief.summary);
        }
      } catch {
        // Fallback to mock data if backend unavailable
      } finally {
        if (isMounted) setLoading(false);
      }
    };
    fetchDetail();
    return () => {
      isMounted = false;
    };
  }, [initialId]);

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
    actionTypeOrStatus?: StaffActionType | TicketStatus,
    targetStatus?: TicketStatus
  ) => {
    let finalActionType: StaffActionType = "EDIT_BRIEF";
    let finalStatus: TicketStatus = "In Progress";

    if (typeof actionTypeOrStatus === "string") {
      if (
        actionTypeOrStatus === "APPROVE" ||
        actionTypeOrStatus === "EDIT_BRIEF" ||
        actionTypeOrStatus === "REROUTE" ||
        actionTypeOrStatus === "CLOSE" ||
        actionTypeOrStatus === "REOPEN" ||
        actionTypeOrStatus === "REQUEST_INFO"
      ) {
        finalActionType = actionTypeOrStatus;
        finalStatus = targetStatus || "In Progress";
      } else {
        finalStatus = actionTypeOrStatus as TicketStatus;
        if (actionName.includes("Duyệt") || actionName.includes("Approve")) finalActionType = "APPROVE";
        else if (actionName.includes("Yêu cầu") || actionName.includes("thông tin")) finalActionType = "REQUEST_INFO";
        else if (actionName.includes("Chuyển") || actionName.includes("Reroute")) finalActionType = "REROUTE";
        else if (actionName.includes("Đóng") || actionName.includes("Close")) finalActionType = "CLOSE";
        else if (actionName.includes("Mở lại")) finalActionType = "REOPEN";
      }
    }

    setStatus(finalStatus);
    setIsSubmitting(true);
    setActionSuccess(`Đang ghi nhận: ${actionName}...`);

    try {
      await submitStaffAction(initialId, {
        action: finalActionType,
        staff_id: "STAFF_VINFAST_DEMO",
        updated_status: finalStatus,
        edited_brief: detail.case_brief.is_edited_by_staff ? { summary: editedSummary } : undefined,
        notes: notes || undefined,
      });
      setActionSuccess(`Đã thực hiện thành công: ${actionName} cho hồ sơ ${initialId}!`);
    } catch {
      setActionSuccess(`Đã cập nhật trạng thái: ${actionName} (chế độ demo).`);
    } finally {
      setIsSubmitting(false);
      setDetail((prev) => ({
        ...prev,
        case: { ...prev.case, status: finalStatus },
      }));
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
