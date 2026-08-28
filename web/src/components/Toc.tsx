"use client";

import { cn } from "@/lib/utils";
import type { BookProgress, MasteryEntry, Unit } from "@/lib/types";
import { Check, Lock, RotateCcw } from "lucide-react";
import { ProgressMap } from "@/components/ProgressMap";

function shortTitle(unit: Unit) {
  return unit.title.replace(/\s+/g, " ");
}

export function Toc({
  units,
  mastery,
  activeId,
  onSelect,
  books,
  remainingWords,
  remainingUnits,
}: {
  units: Unit[];
  mastery: Record<string, MasteryEntry>;
  activeId: string | undefined;
  onSelect: (id: string) => void;
  books?: BookProgress[];
  remainingWords?: number;
  remainingUnits?: number;
}) {
  const groups: { book: string; units: Unit[] }[] = [];
  for (const unit of units) {
    const last = groups[groups.length - 1];
    if (!last || last.book !== unit.book) groups.push({ book: unit.book, units: [unit] });
    else last.units.push(unit);
  }

  return (
    <nav className="toc-scroll flex h-full min-h-0 flex-col overflow-y-auto text-[13px] text-[#efe6d4]">
      {books && (
        <ProgressMap
          books={books}
          remainingWords={remainingWords ?? 0}
          remainingUnits={remainingUnits ?? 0}
        />
      )}
      <div className="px-3 py-4">
        {groups.map((group) => (
          <div key={group.book} className="mb-5">
            <div className="mb-2 px-2 font-[family-name:var(--font-serif)] text-[11px] font-semibold tracking-[0.14em] text-[#c4a15a] uppercase">
              {group.book}
            </div>
            <ul className="space-y-0.5">
              {group.units.map((unit) => {
                const entry = mastery[unit.id] || {};
                const unlocked = Boolean(entry.unlocked);
                const active = unit.id === activeId;
                const status = entry.status || (unlocked ? "in_progress" : "locked");
                return (
                  <li key={unit.id}>
                    <button
                      type="button"
                      disabled={!unlocked}
                      onClick={() => onSelect(unit.id)}
                      className={cn(
                        "w-full rounded-md px-2 py-1.5 text-left transition",
                        active && "bg-white/10",
                        unlocked ? "hover:bg-white/8 cursor-pointer" : "cursor-not-allowed opacity-45",
                      )}
                    >
                      <div className="flex items-start gap-2">
                        {status === "locked" && <Lock className="mt-0.5 size-3 shrink-0 text-[#c4a15a]" />}
                        {status === "mastered" && <Check className="mt-0.5 size-3 shrink-0 text-[#6fbf86]" />}
                        {status === "revise" && <RotateCcw className="mt-0.5 size-3 shrink-0 text-[#c4a15a]" />}
                        {status === "in_progress" && (
                          <span className="mt-1.5 size-2 shrink-0 rounded-full bg-[#c4a15a]" />
                        )}
                        <div className="min-w-0">
                          <div className="leading-snug">{shortTitle(unit)}</div>
                          {unit.part_title && (
                            <div className="mt-0.5 truncate text-[11px] text-[#cbbda4]">{unit.part_title}</div>
                          )}
                        </div>
                      </div>
                    </button>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </div>
    </nav>
  );
}
