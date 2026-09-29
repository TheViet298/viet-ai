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
    <div className="mt-2 flex flex-wrap gap-1.5 max-w-[85%]">
      {chips.map((chip, idx) => (
        <button
          key={idx}
          onClick={() => onSelectChip(chip)}
          className="text-xs bg-blue-50 text-blue-700 hover:bg-blue-100 border border-blue-300 rounded-full px-3 py-1 font-medium transition-colors"
        >
          {chip}
        </button>
      ))}
    </div>
  );
}
