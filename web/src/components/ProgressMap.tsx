"use client";

import type { BookProgress } from "@/lib/types";

function formatWords(n: number) {
  if (n >= 1000) return `${Math.round(n / 100) / 10}k`;
  return String(n);
}

export function ProgressMap({
  books,
  remainingWords,
  remainingUnits,
}: {
  books: BookProgress[];
  remainingWords: number;
  remainingUnits: number;
}) {
  if (!books.length) return null;
  return (
    <div className="border-b border-white/10 px-3 py-3">
      <p className="text-[11px] tracking-[0.14em] text-[#c4a15a] uppercase">Reading map</p>
      <p className="mt-1 text-[12px] text-[#cbbda4]">
        {remainingUnits} units · ~{formatWords(remainingWords)} words left
      </p>
      <div className="mt-3 space-y-2">
        {books.map((book) => {
          const share = book.totalWords ? book.masteredWords / book.totalWords : 0;
          return (
            <div key={book.book}>
              <div className="mb-0.5 flex justify-between gap-2 text-[10px] text-[#cbbda4]">
                <span className="truncate">{book.book}</span>
                <span className="shrink-0">
                  {book.masteredUnits}/{book.totalUnits} · {formatWords(book.remainingWords)} left
                </span>
              </div>
              <div className="h-1.5 overflow-hidden rounded-full bg-white/10">
                <div className="h-full rounded-full bg-[#6fbf86]" style={{ width: `${Math.round(share * 100)}%` }} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
