"use client";

import { useLocale } from "@/features/shared/context/LocaleContext";

export function LanguageSwitch() {
  const { language, setLanguage } = useLocale();
  return (
    <div role="group" aria-label="Ngôn ngữ / Language" className="inline-flex shrink-0 rounded-full bg-[#F3F4F6] p-0.5">
      {(["vi", "en"] as const).map(value => (
        <button
          key={value}
          type="button"
          lang={value}
          aria-label={value === "vi" ? "Tiếng Việt" : "English"}
          onClick={() => setLanguage(value)}
          className={`h-10 min-w-11 rounded-full px-2 text-[13px] font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1E40AF] focus-visible:ring-offset-2 ${language === value ? "bg-[#E2E5E9] text-[#1F2937]" : "text-[#596779] hover:bg-[#E9ECF0] hover:text-[#1F2937]"}`}
          aria-pressed={language === value}
        >{value.toUpperCase()}</button>
      ))}
    </div>
  );
}
