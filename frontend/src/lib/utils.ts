import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function parseServerTimestamp(value: string): Date {
  // Legacy API timestamps store UTC but omit its timezone suffix.
  const timestamp = value?.trim();
  const naive = /^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?$/.test(timestamp);
  return new Date(naive ? `${timestamp.replace(" ", "T")}Z` : timestamp);
}

export function formatDate(dateString: string): string {
  try {
    const d = parseServerTimestamp(dateString);
    return d.toLocaleTimeString("vi-VN", {
      hour: "2-digit",
      minute: "2-digit",
      day: "2-digit",
      month: "2-digit",
    });
  } catch {
    return dateString;
  }
}
