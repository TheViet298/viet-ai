"use client";

import { useEffect, useState } from "react";
import { StaffActionType, TicketDetail, TicketStatus } from "../types";
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
  const [detail, setDetail] = useState<TicketDetail>(MOCK_DETAIL_DATA);
  const [status, setStatus] = useState<TicketStatus>(detail.case.status);
  const [isEditing, setIsEditing] = useState(false);
  const [editedSummary, setEditedSummary] = useState(detail.case_brief.summary);
  const [notes, setNotes] = useState("");
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    const fetchDetail = async () => {
      try {
        const res = await getTicketDetail(initialId);
        if (isMounted && res.success && res.data) {
          setDetail(res.data);
          setStatus(res.data.case.status);
          setEditedSummary(res.data.case_brief.summary);
        }
      } catch {
        // Fallback to mock data if backend unavailable
      }
    };
    fetchDetail();
    return () => {
      isMounted = false;
    };
  }, [initialId]);

  const executeAction = async (actionName: string, newStatus: TicketStatus) => {
    setStatus(newStatus);
    setActionSuccess(`Đang ghi nhận: ${actionName}...`);

    let staffAction: StaffActionType = "EDIT_BRIEF";
    if (actionName.includes("Duyệt") || actionName.includes("Approve")) staffAction = "APPROVE";
    else if (actionName.includes("Yêu cầu") || actionName.includes("thông tin")) staffAction = "REQUEST_INFO";
    else if (actionName.includes("Chuyển") || actionName.includes("Reroute")) staffAction = "REROUTE";
    else if (actionName.includes("Đóng") || actionName.includes("Close")) staffAction = "CLOSE";
    else if (actionName.includes("Mở lại")) staffAction = "REOPEN";

    try {
      await submitStaffAction(initialId, {
        action: staffAction,
        staff_id: "STAFF_VINFAST_DEMO",
        updated_status: newStatus,
        edited_brief: { summary: editedSummary },
        notes: notes || undefined,
      });
      setActionSuccess(`Đã thực hiện thành công: ${actionName} cho hồ sơ ${initialId}!`);
    } catch {
      setActionSuccess(`Đã cập nhật trạng thái tạm: ${actionName} (chế độ demo).`);
    }
    setTimeout(() => setActionSuccess(null), 4000);
  };

  return {
    detail,
    status,
    isEditing,
    setIsEditing,
    editedSummary,
    setEditedSummary,
    notes,
    setNotes,
    actionSuccess,
    executeAction,
  };
}
