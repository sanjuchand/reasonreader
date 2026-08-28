"use client";

import { useEffect } from "react";
import type { Unit } from "@/lib/types";

export function Reader({
  unit,
  highlightId,
}: {
  unit: Unit | undefined;
  highlightId: string | null;
}) {
  useEffect(() => {
    if (!highlightId) return;
    const el = document.getElementById(highlightId);
    if (!el) return;
    const scroller = el.closest(".reader-scroll");
    if (scroller instanceof HTMLElement) {
      const top = el.offsetTop - scroller.clientHeight / 2 + el.clientHeight / 2;
      scroller.scrollTo({ top: Math.max(0, top), behavior: "smooth" });
    }
    el.classList.remove("cite-flash");
    void el.offsetWidth;
    el.classList.add("cite-flash");
  }, [highlightId, unit?.id]);

  if (!unit) {
    return (
      <div className="flex h-full items-center justify-center font-[family-name:var(--font-serif)] text-[#4a4036]">
        Select a chapter to begin.
      </div>
    );
  }

  return (
    <article className="reader-scroll h-full min-h-0 overflow-y-auto px-10 py-10">
      <p className="mb-2 text-[12px] tracking-[0.16em] text-[#9a7840] uppercase">
        {unit.book}
      </p>
      <h1 className="font-[family-name:var(--font-serif)] text-[28px] leading-tight font-semibold text-[#1c1612]">
        {unit.title}
      </h1>
      {unit.part_title && (
        <h2 className="mt-3 font-[family-name:var(--font-serif)] text-[18px] text-[#4a4036]">
          {unit.part_title}
        </h2>
      )}
      <div className="mt-8 space-y-5 font-[family-name:var(--font-serif)] text-[17.5px] leading-[1.7] text-[#1c1612]">
        {unit.paragraphs.map((paragraph) => (
          <p key={paragraph.paragraph_id} id={paragraph.paragraph_id}>
            {paragraph.text}
          </p>
        ))}
      </div>
    </article>
  );
}
