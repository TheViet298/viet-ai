export function TicketTableSkeleton() {
  return (
    <div className="space-y-3" role="status" aria-label="Đang tải dữ liệu hồ sơ sự cố">
      {[1, 2, 3].map((i) => (
        <div
          key={i}
          className="bg-white border border-[#E2E8F0] rounded-2xl p-4 sm:p-5 shadow-[0_1px_2px_rgba(0,0,0,0.04)] animate-pulse"
        >
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="space-y-2.5 flex-1">
              <div className="flex items-center gap-2.5">
                <div className="h-5 w-32 bg-[#E2E8F0] rounded-md" />
                <div className="h-5 w-20 bg-[#F1F5F9] rounded-full" />
                <div className="h-5 w-24 bg-[#F1F5F9] rounded-full" />
              </div>
              <div className="flex items-center gap-3">
                <div className="h-4 w-36 bg-[#F1F5F9] rounded" />
                <div className="h-4 w-28 bg-[#F1F5F9] rounded" />
                <div className="h-4 w-20 bg-[#F1F5F9] rounded" />
              </div>
            </div>
            <div className="flex items-center gap-3 sm:self-center">
              <div className="h-8 w-24 bg-[#F1F5F9] rounded-lg" />
              <div className="h-8 w-8 bg-[#F1F5F9] rounded-lg" />
            </div>
          </div>
        </div>
      ))}
      <span className="sr-only">Đang tải danh sách hồ sơ sự cố...</span>
    </div>
  );
}

export function TicketDetailSkeleton() {
  return (
    <div className="max-w-6xl mx-auto px-4 py-8 sm:px-6 lg:px-8 space-y-6 animate-pulse" role="status" aria-label="Đang tải chi tiết hồ sơ">
      <div className="h-4 w-40 bg-[#E2E8F0] rounded mb-4" />
      <div className="bg-white border border-[#E2E8F0] rounded-2xl p-6 shadow-subtle space-y-4">
        <div className="h-6 w-48 bg-[#E2E8F0] rounded" />
        <div className="h-4 w-96 bg-[#F1F5F9] rounded" />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-white border border-[#E2E8F0] rounded-2xl p-6 h-72" />
          <div className="bg-white border border-[#E2E8F0] rounded-2xl p-6 h-48" />
        </div>
        <div className="bg-white border border-[#E2E8F0] rounded-2xl p-6 h-[500px]" />
      </div>
    </div>
  );
}
