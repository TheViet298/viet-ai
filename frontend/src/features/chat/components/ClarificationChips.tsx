import React from "react";

interface ClarificationChipsProps {
  chips?: string[];
  onSelectChip: (chip: string) => void;
}

export function ClarificationChips({
  chips,
  onSelectChip,
}: ClarificationChipsProps) {
  if (!chips || chips.length === 0) return null;

  return (
    <div className="mt-2.5 pb-2 flex flex-wrap gap-1.5 max-w-full pl-0.5 animate-fadeIn">
      {chips.map((chip, idx) => (
        <button
          key={idx}
          type="button"
          onClick={() => onSelectChip(chip)}
          className="inline-flex items-center text-[12px] bg-white hover:bg-blue-50/90 text-slate-700 hover:text-[#1E40AF] border border-slate-200/90 hover:border-blue-300 rounded-xl px-3 py-1.5 font-medium transition-all shadow-2xs active:scale-[0.98]"
        >
          <span>{chip}</span>
        </button>
      ))}
    </div>
  );
}
