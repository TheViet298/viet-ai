import { TicketQueueContainer } from "@/features/console";

export const metadata = {
  title: "Bàn Điều Phối Dịch Vụ (HITL Console) — VinFast ServiceFlow AI",
  description: "Hàng đợi xử lý hồ sơ sự cố xe điện VinFast dành cho Cố vấn Dịch vụ.",
};

export default function ConsolePage() {
  return <TicketQueueContainer />;
}
