import { TicketItem } from "../types";
import { TicketCard } from "./TicketCard";

interface TicketTableProps {
  tickets: TicketItem[];
}

export function TicketTable({ tickets }: TicketTableProps) {
  if (tickets.length === 0) {
    return (
      <div className="text-center py-12 bg-white rounded-xl border border-slate-200 text-slate-500 text-sm">
        Không tìm thấy ticket nào phù hợp với bộ lọc hiện tại.
      </div>
    );
  }

  return (
    <div className="space-y-3 mt-2">
      {tickets.map((ticket) => (
        <TicketCard key={ticket.id} ticket={ticket} />
      ))}
    </div>
  );
}
