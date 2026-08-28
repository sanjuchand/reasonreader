"use client";

import { useState } from "react";
import type { QuizQuestion } from "@/lib/types";

export function QuizForm({
  questions,
  disabled,
  onSubmit,
  onKeepTeaching,
}: {
  questions: QuizQuestion[];
  disabled?: boolean;
  onSubmit: (answers: { id: string; answer: string }[]) => void;
  onKeepTeaching?: () => void;
}) {
  const [answers, setAnswers] = useState<Record<string, string>>(() =>
    Object.fromEntries(questions.map((question) => [question.id, ""])),
  );

  return (
    <form
      className="max-h-[42vh] space-y-3 overflow-y-auto border-t border-[#d9c9ae] bg-[#efe4cc] px-4 py-3"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit(questions.map((q) => ({ id: q.id, answer: (answers[q.id] || "").trim() })));
      }}
    >
      <p className="text-[12px] tracking-[0.12em] text-[#9a7840] uppercase">
        Short-answer test
      </p>
      {questions.map((question, index) => (
        <label key={question.id} className="block">
          <span className="mb-1 block text-[13.5px] font-medium text-[#1c1612]">
            {index + 1}. {question.prompt}
            <span className="ml-2 text-[11px] font-normal tracking-wide text-[#9a7840] uppercase">
              {question.kind} · {question.concept}
            </span>
          </span>
          <textarea
            required
            rows={3}
            disabled={disabled}
            value={answers[question.id] ?? ""}
            onChange={(event) =>
              setAnswers((prev) => ({ ...prev, [question.id]: event.target.value }))
            }
            className="w-full resize-y rounded-md border border-[#d9c9ae] bg-[#f7f1e6] px-3 py-2 text-[14px] text-[#1c1612] outline-none focus:border-[#9a7840]"
          />
        </label>
      ))}
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="submit"
          disabled={disabled}
          className="rounded-md bg-[#1c2d24] px-4 py-2 text-[13px] font-medium text-[#f3ead8] disabled:opacity-50"
        >
          Submit answers
        </button>
        {onKeepTeaching && (
          <button
            type="button"
            disabled={disabled}
            onClick={onKeepTeaching}
            className="rounded-md px-3 py-2 text-[13px] text-[#4a4036] hover:bg-[#e6d7b8] disabled:opacity-50"
          >
            Keep teaching instead
          </button>
        )}
      </div>
    </form>
  );
}
