"use client";

import { useState } from "react";
import { VehicleCard } from "../types";

export function VehicleInfoCard({ card }: { card: VehicleCard }) {
  const [imageFailed, setImageFailed] = useState(false);
  return (
    <article aria-label={card.name} className="flex w-full max-w-[420px] flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white text-slate-800">
      <div className="relative flex aspect-[2/1] shrink-0 items-center justify-center overflow-hidden bg-gradient-to-br from-slate-200 to-slate-50">
        {imageFailed ? <span className="text-sm text-slate-500">Chưa tải được ảnh {card.name}</span> : (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={card.image_url} alt={card.name} width={640} height={360}
            className="absolute inset-0 h-full w-full object-contain" loading="lazy" onError={() => setImageFailed(true)} />
        )}
      </div>
      <div className="flex flex-1 flex-col gap-5 p-4 text-center sm:p-5">
        <h3 className="text-lg font-semibold">{card.name}</h3>
        <dl className="grid grid-cols-2 gap-x-4 gap-y-5 py-2">
          {card.specs.map(spec => <div key={spec.label} className="min-w-0">
            <dt className="text-xs text-slate-500">{spec.label}</dt>
            <dd className="mt-1 text-sm font-medium leading-relaxed">{spec.value}</dd>
          </div>)}
        </dl>
        <div className="border-t border-slate-200 pt-3">
          <p className="text-sm text-slate-700">Giá bán từ</p>
          <p className="mt-2 break-words bg-gradient-to-r from-sky-600 to-blue-600 bg-clip-text text-2xl font-semibold text-transparent">{card.price_label.replace(/^Từ\s+/, '')}</p>
        </div>
        {card.test_drive_url && <a href={card.test_drive_url} target="_blank" rel="noopener noreferrer"
          className="mt-auto flex min-h-11 items-center justify-center rounded-xl bg-gradient-to-r from-sky-700 to-blue-600 px-3 py-2.5 text-sm font-semibold text-white hover:from-sky-800 hover:to-blue-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600">
          Đăng ký lái thử
        </a>}
        <div className="space-x-2 text-xs text-slate-500">
        <a href={card.source_url} target="_blank" rel="noopener noreferrer"
          className="inline-block text-xs font-medium text-[#1E40AF] underline underline-offset-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4">
          Giá VinFast
        </a>
        <p className="mt-1">Cập nhật {card.verified_at.split('-').reverse().join('/')}</p>
        </div>
      </div>
    </article>
  );
}
