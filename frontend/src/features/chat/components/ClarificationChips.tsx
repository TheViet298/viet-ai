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
    <div className="mt-2.5 flex flex-wrap gap-1.5 max-w-[85%]">
      {chips.map((chip, idx) => (
        <button
          key={idx}
          onClick={() => onSelectChip(chip)}
          className="text-[12px] bg-[#EFF3FC] text-[#1E40AF] hover:bg-[#1E40AF] hover:text-white border border-[#E2E8F0] rounded-full px-3 py-1 font-medium transition-colors shadow-[0_1px_2px_rgba(0,0,0,0.04)]"
        >
          {chip}
        </button>
      ))}
    </div>
  );
}
