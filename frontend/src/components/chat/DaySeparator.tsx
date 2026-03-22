'use client';

interface DaySeparatorProps {
  label: string;
  day: number;
}

export default function DaySeparator({ label, day }: DaySeparatorProps) {
  return (
    <div className="flex items-center gap-3 py-4 px-2">
      <div className="flex-1 h-px bg-border-default" />
      <span className="text-xs text-text-tertiary font-medium whitespace-nowrap">
        {label} &middot; day {day}
      </span>
      <div className="flex-1 h-px bg-border-default" />
    </div>
  );
}
