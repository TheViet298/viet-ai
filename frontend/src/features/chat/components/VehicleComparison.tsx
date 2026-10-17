"use client";
import { Language, useLocale } from "@/features/shared/context/LocaleContext";

import { useState } from "react";
import { VehicleCard } from "../types";

function ComparisonHeader({ card, language }: { card: VehicleCard; language?: Language }) {
  const { t } = useLocale(language);
  const [failed, setFailed] = useState(false);
  return <>
    <span className="block px-2 text-base font-medium">{card.name.replace(/^VinFast\s+/, "")}</span>
    <div className="relative mt-2 aspect-[2/1]">
      {failed ? <span className="block px-2 pt-5 text-xs text-slate-500">{t("Chưa tải được ảnh")}</span> : (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={card.image_url} alt={card.name} width={320} height={160}
          className="absolute inset-0 h-full w-full object-contain" onError={() => setFailed(true)} />
      )}
    </div>
  </>;
}

export function VehicleComparison({ cards, language }: { cards: VehicleCard[]; language?: Language }) {
  const { t, language: messageLanguage } = useLocale(language);
  if (cards.length !== 2) return null;
  const spec = (card: VehicleCard, label: string, englishLabel: string) => card.specs.find(item => item.label.startsWith(label) || item.label.startsWith(englishLabel))?.value || t("Chưa có dữ liệu");
  const valueLabel = (value: string) => messageLanguage === "en" ? value.replace(/phút/g, "minutes").replace(/chỗ/g, "seats") : value;
  const rows = [
    { label: t("Số chỗ ngồi"), values: cards.map(card => spec(card, "Số chỗ ngồi", "Seats")) },
    { label: t("Quãng đường mỗi lần sạc (km)"), values: cards.map(card => spec(card, "Quãng đường", "Range")) },
    { label: t("Dung lượng pin khả dụng (kWh)"), values: cards.map(card => card.battery_capacity || t("Chưa có dữ liệu")) },
    { label: t("Thời gian sạc nhanh (10%–70%)"), values: cards.map(card => card.fast_charge_time || t("Chưa có dữ liệu")) },
    { label: t("Giá bán từ"), values: cards.map(card => card.price_label.replace(/^Từ\s+/, "")) },
  ];
  return <div className="w-full max-w-[448px] space-y-2">
    <section aria-label={t("So sánh xe")} className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
      <div className="relative">
        <table className="w-full table-fixed text-center text-sm text-slate-800">
          <caption className="sr-only">{t("So sánh")}{" "}{cards.map(card => card.name).join(` ${t("và")} `)}</caption>
          <thead className="bg-gradient-to-br from-slate-200 to-slate-50">
            <tr>{cards.map(card => <th key={card.name} scope="col" className="w-1/2 py-3"><ComparisonHeader language={language} card={card} /></th>)}</tr>
          </thead>
          {rows.map((row, index) => <tbody key={row.label}>
            <tr><th colSpan={2} scope="rowgroup" className="px-2 pt-3 font-normal text-slate-500">{row.label}</th></tr>
            <tr>{row.values.map((value, column) => <td key={column} className={`break-words px-2 pb-3 pt-1 font-medium ${index === rows.length - 1 ? "text-blue-600" : "border-b border-slate-200"}`}>{valueLabel(value)}</td>)}</tr>
          </tbody>)}
        </table>
        <span aria-hidden="true" className="pointer-events-none absolute left-1/2 top-14 -translate-x-1/2 text-2xl font-semibold text-slate-300">VS</span>
      </div>
    </section>
    <div className="flex flex-col items-start gap-2 pt-1">
      {cards.map(card => card.test_drive_url && <a key={card.name} href={card.test_drive_url} target="_blank" rel="noopener noreferrer"
        className="min-h-11 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-800 hover:bg-slate-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600">
        {t("Đăng ký lái thử")}{" "}{card.name.replace(/^VinFast\s+/, "")}
      </a>)}
    </div>
  </div>;
}
