import type { Metadata } from "next";
import { ServiceFlowPage } from "@/features/landing/components/ServiceFlowPage";

export const metadata: Metadata = {
  title: "Project Overview — VFServ · Team VFO2O-18",
  description: "Dự án VinFast ServiceFlow AI của Team VFO2O-18: kết nối chủ xe, trợ lý AI và nhân viên dịch vụ trong một quy trình tiếp nhận và bàn giao có ngữ cảnh.",
};

export default function ProjectOverviewPage() {
  return <ServiceFlowPage />;
}
