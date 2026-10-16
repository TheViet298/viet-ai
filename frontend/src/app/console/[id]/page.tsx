import { TicketDetailContainer } from "@/features/console";

interface PageProps {
  params: {
    id: string;
  };
}

export function generateMetadata({ params }: PageProps) {
  return {
    title: `Chi tiết Hồ sơ ${params.id} — VFServ`,
    description: `Xem xét Case Brief và thực hiện phê duyệt điều phối cho hồ sơ ${params.id}.`,
  };
}

export default function TicketDetailPage({ params }: PageProps) {
  return <TicketDetailContainer caseId={params.id} />;
}
