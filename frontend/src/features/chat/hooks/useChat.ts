"use client";

import { useState, useEffect } from "react";
import { ChatMessage, Citation, VehicleModel } from "../types";
import { sendChatMessage } from "../api/chatApi";

export interface ChatUserContext {
  userName?: string;
  vehicleModel?: string;
  caseId?: string | null;
}

export function getSalutation(fullName?: string): { title: string; shortName: string; pronoun: string } {
  if (!fullName || !fullName.trim()) {
    return { title: "", shortName: "", pronoun: "bạn" };
  }
  const parts = fullName.trim().split(/\s+/);
  const shortName = parts[parts.length - 1];
  const lower = fullName.toLowerCase();
  const isFemale =
    lower.includes("thị") ||
    ["hoa", "lan", "mai", "hương", "trang", "linh", "ngọc", "thảo", "hằng", "nhung", "yến", "my", "vy"].includes(shortName.toLowerCase());
  const isMale =
    lower.includes("văn") ||
    ["an", "bình", "cường", "dũng", "hùng", "long", "minh", "nam", "phúc", "quân", "tuấn", "việt"].includes(shortName.toLowerCase());

  if (isFemale) {
    return { title: "chị", shortName, pronoun: "chị" };
  }
  if (isMale) {
    return { title: "anh", shortName, pronoun: "anh" };
  }
  return { title: "", shortName, pronoun: "bạn" };
}

export function createWelcomeMessage(context?: ChatUserContext | string): ChatMessage {
  const ctx: ChatUserContext =
    typeof context === "string" ? { userName: context } : context || {};
  const { userName, vehicleModel, caseId } = ctx;
  const { title, shortName, pronoun } = getSalutation(userName);

  let content: string;
  if (shortName) {
    const greetingStart = title ? `Chào ${title} ${shortName}!` : `Chào ${shortName}!`;
    if (caseId) {
      content = `${greetingStart} Hồ sơ ${caseId} đang được kỹ thuật viên kiểm tra. Em giúp gì thêm được cho ${pronoun} hôm nay ạ?`;
    } else if (vehicleModel) {
      content = `${greetingStart} Em giúp gì được cho ${pronoun} về chiếc ${vehicleModel} hôm nay ạ?`;
    } else {
      content = `${greetingStart} Em là Trợ lý VF Serv. Em có thể hỗ trợ gì cho ${pronoun} hôm nay ạ?`;
    }
  } else {
    // Khách vãng lai (Guest)
    if (caseId) {
      content = `Chào bạn! Hồ sơ ${caseId} đang được kỹ thuật viên kiểm tra. Bạn cần em hỗ trợ thêm thông tin gì không ạ?`;
    } else {
      content = `Chào bạn! Em là Trợ lý VF Serv. Em có thể hỗ trợ gì cho bạn hôm nay ạ?`;
    }
  }

  return {
    id: "welcome-1",
    sender: "AGENT",
    content,
    timestamp: new Date().toISOString(),
    suggested_replies: [
      "Tư vấn xe",
      "Trạm sạc & ứng dụng",
      "Bảo hành & bảo dưỡng",
      "Báo sự cố kỹ thuật",
    ],
  };
}

export const INITIAL_WELCOME_MESSAGE: ChatMessage = createWelcomeMessage();

export function useChat(context?: ChatUserContext | string) {
  const ctx: ChatUserContext =
    typeof context === "string" ? { userName: context } : context || {};
  const [messages, setMessages] = useState<ChatMessage[]>(() => [createWelcomeMessage(ctx)]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [selectedModel, setSelectedModel] = useState<VehicleModel>(
    (ctx.vehicleModel as VehicleModel) || "VF8"
  );
  const [sessionId, setSessionId] = useState(() => `sess_vf_${Math.random().toString(36).substring(2, 9)}`);
  const [currentCaseId, setCurrentCaseId] = useState<string | null>(ctx.caseId || null);
  const [criticalBanner, setCriticalBanner] = useState(false);
  const [sessionHasCritical, setSessionHasCritical] = useState(false);
  const [requestLocation, setRequestLocation] = useState(false);

  useEffect(() => {
    setMessages((prev) => {
      if (prev.length === 1 && prev[0].id === "welcome-1") {
        return [createWelcomeMessage(ctx)];
      }
      return prev;
    });
  }, [ctx.userName, ctx.vehicleModel, ctx.caseId]);

  const resetChat = () => {
    setMessages([createWelcomeMessage(ctx)]);
    setInput("");
    setLoading(false);
    setCurrentCaseId(null);
    setCriticalBanner(false);
    setSessionHasCritical(false);
    setRequestLocation(false);
    setSessionId(`sess_vf_${Math.random().toString(36).substring(2, 9)}`);
  };

  const updateMessageChips = (messageId: string, newChips: string[]) => {
    setMessages((prev) =>
      prev.map((msg) => (msg.id === messageId ? { ...msg, suggested_replies: newChips } : msg))
    );
  };

  const sendMessage = async (messageText?: string, attachmentIds?: string[]) => {
    const textToSend = messageText || input.trim();
    if (!textToSend || loading) return;

    // Phía client chỉ giữ danh sách rất ngắn các từ nguy hiểm cứng (cháy, khói, mất phanh)
    // để banner hiện tức thì trước khi backend trả lời (tránh lag giật tâm lý khách hàng).
    const lowerText = textToSend.toLowerCase();
    const isHardEmergency =
      lowerText.includes("cháy") ||
      lowerText.includes("bốc khói") ||
      lowerText.includes("mất phanh") ||
      lowerText.includes("liệt phanh") ||
      lowerText.includes("lật xe") ||
      lowerText.includes("tai nạn");

    if (isHardEmergency) {
      setCriticalBanner(true);
    }

    const userMsg: ChatMessage = {
      id: `usr_${Date.now()}`,
      sender: "CUSTOMER",
      content: textToSend,
      timestamp: new Date().toISOString(),
      attachment_ids: attachmentIds,
    };

    // 1. Xuất hiện câu hỏi của User trước
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    // 2. Kích hoạt trạng thái AI đang suy nghĩ
    setLoading(true);

    const startTime = Date.now();

    try {
      const response = await sendChatMessage({
        sessionId,
        message: textToSend,
        caseId: currentCaseId,
        attachmentIds: attachmentIds,
        clientContext: {
          mock_customer_id: "CUST_MOCK_01",
          vehicle_model: selectedModel,
          vehicle_code_mock: `VF-${selectedModel}-8899`,
          customer_name: ctx.userName,
        },
      });

      // Đảm bảo có một khoảng delay tự nhiên (~400ms) để người dùng thấy AI đang phân tích
      const elapsed = Date.now() - startTime;
      if (elapsed < 400) {
        await new Promise((resolve) => setTimeout(resolve, 400 - elapsed));
      }

      if (response.success && response.data) {
        const data = response.data;
        if (data.case_id) {
          setCurrentCaseId(data.case_id);
        }

        const agentMsg: ChatMessage = {
          id: `agent_${Date.now()}`,
          sender: "AGENT",
          content: data.message,
          timestamp: new Date().toISOString(),
          response_type: data.response_type,
          citations: data.citations,
          suggested_replies: data.suggested_replies,
          safe_guidance: data.safe_guidance,
          case_id: data.case_id,
          priority: data.priority,
        };

        // Banner khẩn cấp gắn với trạng thái hồ sơ / phiên làm việc:
        // Nếu trong phiên có sự cố CRITICAL (hoặc show_emergency_banner từ backend), banner không tự tắt
        const isServerCritical = Boolean(data.show_emergency_banner || data.priority === "CRITICAL");
        if (isServerCritical) {
          setSessionHasCritical(true);
          setCriticalBanner(true);
        } else if (sessionHasCritical) {
          setCriticalBanner(true);
        } else {
          setCriticalBanner(false);
        }

        // Backend trả về cờ request_location rõ ràng:
        if (data.request_location !== undefined) {
          setRequestLocation(Boolean(data.request_location));
        } else if (isServerCritical) {
          setRequestLocation(true);
        }

        // 3. AI trả lời xuất hiện sau khi suy nghĩ xong
        setMessages((prev) => [...prev, agentMsg]);
      }
    } catch {
      // Mock fallback response for smooth testing before backend is started
      const elapsed = Date.now() - startTime;
      if (elapsed < 400) {
        await new Promise((resolve) => setTimeout(resolve, 400 - elapsed));
      }

      // Rich fallback response for smooth testing and demonstration
      let fallbackContent = `Dạ em đã ghi nhận thông tin về xe ${selectedModel}. Theo cẩm nang kỹ thuật VinFast, khi gặp tình huống này anh/chị nên kiểm tra kết nối súng sạc và quan sát đèn chỉ báo trên táp-lô.`;
      let fallbackCitations: Citation[] | undefined = undefined;
      let fallbackGuidance: string | undefined = undefined;
      let fallbackReplies = ["Mã lỗi CC01, trụ P02", "Đèn trụ nháy đỏ", "Xe dừng hẳn, an toàn"];

      const isExplanation =
        textToSend.toLowerCase().includes("nghĩa là gì") ||
        textToSend.toLowerCase().includes("là gì") ||
        textToSend.toLowerCase().includes("ý nghĩa") ||
        textToSend.toLowerCase().includes("giải thích") ||
        textToSend.toLowerCase().includes("tại sao") ||
        textToSend.toLowerCase().includes("khi nào");

      let isCrit = false;

      if (!isExplanation && (textToSend.toLowerCase().includes("cao tốc") || textToSend.toLowerCase().includes("mất phanh") || textToSend.toLowerCase().includes("cứu hộ"))) {
        isCrit = true;
        setSessionHasCritical(true);
        setCriticalBanner(true);
        setRequestLocation(true);
        fallbackContent = `Đội cứu hộ phản ứng nhanh 24/7 và Cố vấn VinFast đã được thông báo ở mức ưu tiên cao nhất. Anh/chị hãy bật ngay đèn cảnh báo hazard, rời khỏi xe và đứng sau hộ lan an toàn cao tốc.`;
        fallbackCitations = [
          {
            source_id: "SRC-EMERGENCY-01",
            title: "Quy trình xử lý sự cố khẩn cấp trên đường cao tốc — Sổ tay VinFast",
            url: "https://vinfastauto.com/vn_vi/chinh-sach-bao-hanh-va-cuu-ho-xe-dien",
          },
        ];
        fallbackReplies = ["Đã vào làn an toàn", "Xem bản đồ cứu hộ ›", "Gọi 1900-232389"];
      } else if (textToSend.toLowerCase().includes("bảo dưỡng") || textToSend.toLowerCase().includes("12.000km")) {
        fallbackContent = `Cấp bảo dưỡng 12.000km cho xe ${selectedModel} bao gồm kiểm tra hệ thống pin cao áp, độ mòn phanh và nâng cấp phần mềm ECU. Anh/chị nên đặt hẹn trước để xưởng chuẩn bị sẵn vật tư.`;
        fallbackCitations = [
          {
            source_id: "SRC-MAINT-12K",
            title: "Cẩm nang bảo dưỡng định kỳ xe điện VinFast — Mục 3.1",
            url: "https://vinfastauto.com/vn_vi/chinh-sach-bao-hanh-va-cuu-ho-xe-dien",
          },
        ];
        fallbackReplies = ["Xem danh sách xưởng", "Đặt hẹn xưởng gần nhất", "Chi phí ước tính"];
      } else if (
        textToSend.toLowerCase().includes("sạc") ||
        textToSend.toLowerCase().includes("cc01") ||
        textToSend.toLowerCase().includes("trụ") ||
        textToSend.toLowerCase().includes("không vào điện")
      ) {
        fallbackContent = `Lỗi CC01 thường do súng sạc chưa khớp ngàm hoặc timeout giao tiếp BMS. Anh/chị bấm nút dừng sạc trên màn hình xe (hoặc bấm mở khóa cửa 2 lần) rồi cắm lại súng dứt khoát.`;
        fallbackCitations = [
          {
            source_id: "SRC-DC-CC01",
            title: "Sổ tay sạc nhanh DC VinFast — Mục 4.2 Xử lý mã CC01",
            url: "https://vinfastauto.com/vn_vi/chinh-sach-va-bieu-phi-sac-pin-cong-cong",
          },
        ];
        fallbackReplies = ["Xem bản đồ trạm sạc ›", "Mã lỗi CC01, trụ P02", "Đèn trụ nháy đỏ"];
      } else if (textToSend.toLowerCase().includes("rùa vàng")) {
        const isExp =
          textToSend.toLowerCase().includes("nghĩa là gì") ||
          textToSend.toLowerCase().includes("là gì") ||
          textToSend.toLowerCase().includes("ý nghĩa") ||
          textToSend.toLowerCase().includes("giải thích");
        isCrit = !isExp;
        setCriticalBanner(isCrit);
        fallbackContent = isExp
          ? `Biểu tượng Con Rùa Vàng (Turtle Mode) là chế độ bảo vệ giới hạn công suất của xe VinFast khi dung lượng pin xuống dưới 10% hoặc nhiệt độ pack pin tăng cao.\n\nKhi đèn này sáng, xe vẫn có thể di chuyển ở tốc độ vừa phải để bạn an tâm tấp lề hoặc tiếp cận trạm sạc gần nhất.`
          : `Biểu tượng Con Rùa Vàng (Turtle Mode) kích hoạt để bảo vệ pin khi dung lượng dưới 10% hoặc nhiệt độ pin tăng cao. Anh/chị vui lòng giảm tốc độ, tắt bớt điều hòa và di chuyển vào trạm sạc hoặc vị trí an toàn gần nhất.`;
        fallbackCitations = [
          {
            source_id: "SRC-TURTLE-WARN",
            title: "Sổ tay an toàn vận hành xe điện VinFast — Chương 6",
            url: "https://vinfastauto.com/vn_vi/chinh-sach-bao-hanh-va-cuu-ho-xe-dien",
          },
        ];
        fallbackReplies = isExp
          ? ["Bảo dưỡng định kỳ 12.000km", "Trạm sạc & ứng dụng", "Chính sách bảo hành pin"]
          : ["Đã vào làn an toàn", "Xem bản đồ cứu hộ ›", "Tìm trạm sạc gần nhất"];
      } else if (
        textToSend.toLowerCase().includes("lái thử") ||
        textToSend.toLowerCase().includes("chạy thử")
      ) {
        fallbackContent = `Dạ anh/chị có thể đăng ký lái thử xe điện VinFast hoàn toàn miễn phí theo các bước rất thuận tiện sau:\n\n1. **Chọn hình thức**: Trải nghiệm tại Showroom/Nhà phân phối gần nhất hoặc đăng ký lái thử tận nhà.\n2. **Điều kiện**: Chuẩn bị CCCD và Giấy phép lái xe (bằng B1 hoặc B2 trở lên) còn hiệu lực.\n3. **Đăng ký nhanh**: Đặt lịch qua Ứng dụng VinFast, website chính thức hoặc gọi Tổng đài CSKH 1900-232389.\n\nAnh/chị đang muốn trải nghiệm lái thử dòng xe nào (như chiếc ${selectedModel}, VF 7 hay VF 9) ạ?`;
        fallbackCitations = [
          {
            source_id: "SRC-DRIVE-01",
            title: "Cổng Đăng ký Lái thử Xe điện VinFast Toàn quốc",
            url: "https://vinfastauto.com/vn_vi/dang-ky-lai-thu",
          },
        ];
        fallbackReplies = [
          `Lái thử xe ${selectedModel}`,
          "Lái thử xe VF 7",
          "Tìm showroom gần nhất",
          "Hotline tư vấn 1900-232389",
        ];
      } else if (
        textToSend.toLowerCase().includes("giá lăn bánh") ||
        textToSend.toLowerCase().includes("bảng giá") ||
        textToSend.toLowerCase().includes("chi phí lăn bánh") ||
        textToSend.toLowerCase().includes("trả góp")
      ) {
        fallbackContent = `Dạ về chính sách giá và chi phí lăn bánh ô tô điện VinFast hiện có những ưu thế vượt trội:\n\n- **Ưu đãi lệ phí trước bạ**: Ô tô điện chạy pin được hưởng chính sách miễn 100% lệ phí trước bạ theo quy định của Chính phủ.\n- **Tùy chọn linh hoạt**: Lựa chọn mua kèm pin hoặc thuê pin hàng tháng giúp tối ưu chi phí đầu tư ban đầu.\n- **Hỗ trợ trả góp**: Hỗ trợ vay vốn ngân hàng lên đến 70-80% giá trị xe với lãi suất ưu đãi.\n\nAnh/chị đang quan tâm giá lăn bánh xe ${selectedModel} hay dòng xe nào khác ạ?`;
        fallbackCitations = [
          {
            source_id: "SRC-PRICE-01",
            title: "Bảng giá Ô tô điện VinFast và Chính sách Ưu đãi Mới nhất",
            url: "https://vinfastauto.com/vn_vi/bang-gia-xe-o-to-vinfast",
          },
        ];
        fallbackReplies = [
          `Giá lăn bánh ${selectedModel}`,
          "Giá xe VF 3 & VF 5",
          "Chính sách thuê pin",
          "Đăng ký lái thử miễn phí",
        ];
      } else if (
        textToSend.toLowerCase().includes("tư vấn xe") ||
        textToSend.toLowerCase().includes("dòng xe") ||
        textToSend.toLowerCase().includes("mua xe") ||
        textToSend.toLowerCase().includes("vf 3")
      ) {
        fallbackContent = `VinFast hiện có dải xe điện phủ nhiều phân khúc:\n\n- **VF 3**: mini SUV đô thị nhỏ gọn, thiết kế vuông vức, di chuyển linh hoạt\n- **VF 5 Plus**: A-SUV trẻ trung, tối ưu chi phí vận hành cho gia đình và đô thị\n- **VF 6**: B-SUV thời thượng, nhiều công nghệ thông minh và an toàn\n- **VF 7**: C-SUV phong cách thể thao, có 2 phiên bản Eco và Plus\n- **VF 8**: D-SUV sang trọng, có hệ thống hỗ trợ lái nâng cao (ADAS) và trợ lý ảo\n- **VF 9**: E-SUV 7 chỗ đẳng cấp thương gia, tiện nghi hàng đầu\n\nAnh/chị đang quan tâm dòng nào, hoặc cần em tư vấn thêm về tầm giá, chính sách thuê/mua pin, đặt lịch lái thử?`;
        fallbackCitations = [
          {
            source_id: "SRC-006",
            title: "Danh mục Sản phẩm và Chính sách Bán hàng Ô tô điện VinFast",
            url: "https://vinfastauto.com/vn_vi/cac-dong-xe-o-to",
          },
        ];
        fallbackReplies = [
          "Đăng ký lái thử miễn phí",
          "Bảng giá xe mới nhất",
          "Tư vấn xe VF 7 & VF 8",
          "Chính sách thuê/mua pin",
        ];
      }

      // Tạo mã Case ID động theo từng phiên chat thật (không fix cứng ngày tháng cũ)
      // Chỉ tạo case khi là sự cố cần hỗ trợ kỹ thuật, không tạo khi khách chỉ hỏi giải thích
      const shouldCreateCase =
        !isExplanation &&
        (textToSend.toLowerCase().includes("lỗi") ||
          textToSend.toLowerCase().includes("hỏng") ||
          textToSend.toLowerCase().includes("không sạc") ||
          textToSend.toLowerCase().includes("kẹt") ||
          textToSend.toLowerCase().includes("cứu hộ") ||
          textToSend.toLowerCase().includes("mất phanh"));

      let assignedCaseId: string | undefined = undefined;
      if (shouldCreateCase) {
        if (currentCaseId) {
          assignedCaseId = currentCaseId;
        } else {
          const nowStr = new Date().toISOString().slice(0, 10).replace(/-/g, "");
          const rand = Math.floor(100 + Math.random() * 900);
          assignedCaseId = `CASE-${nowStr}-${rand}`;
          setCurrentCaseId(assignedCaseId);
        }
      }

      const fallbackMsg: ChatMessage = {
        id: `mock_${Date.now()}`,
        sender: "AGENT",
        content: fallbackContent,
        timestamp: new Date().toISOString(),
        citations: fallbackCitations,
        safe_guidance: fallbackGuidance,
        suggested_replies: fallbackReplies,
        case_id: assignedCaseId,
        priority: isCrit ? "CRITICAL" : undefined,
      };
      setMessages((prev) => [...prev, fallbackMsg]);
    } finally {
      setLoading(false);
    }
  };

  return {
    messages,
    input,
    setInput,
    loading,
    selectedModel,
    setSelectedModel,
    sessionId,
    currentCaseId,
    criticalBanner,
    setCriticalBanner,
    sessionHasCritical,
    requestLocation,
    sendMessage,
    resetChat,
    updateMessageChips,
  };
}
