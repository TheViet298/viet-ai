"use client";
import { Moon, Sun } from "lucide-react";
import { useTheme } from "@/features/shared/context/ThemeContext";
import { useLocale } from "@/features/shared/context/LocaleContext";
export function ThemeToggle() {
  const {theme,setTheme}=useTheme();
  const {t}=useLocale();
  const label=t(theme === "dark" ? "Chuyển sang giao diện sáng" : "Chuyển sang giao diện tối");
  const Icon=theme === "dark" ? Sun : Moon;
  return <button type="button" aria-label={label} title={label} aria-pressed={theme === "dark"}
    onClick={()=>setTheme(theme === "dark" ? "light" : "dark")}
    className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-full text-[#596779] hover:bg-[#F1F5F9] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500">
    <Icon className="h-5 w-5" aria-hidden="true" />
  </button>;
}
