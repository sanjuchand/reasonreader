"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { Message } from "@langchain/langgraph-sdk";
import { Send } from "lucide-react";
import { isContextSummary, type CiteIndex } from "@/lib/cites";
import { messageText } from "@/lib/utils";
import type { QuizQuestion, TutorState } from "@/lib/types";
import { QuizForm } from "@/components/QuizForm";
import { TutorMarkdown } from "@/components/TutorMarkdown";

function displayHuman(text: string) {
  if (text.startsWith("[[QUIZ_SUBMISSION]]")) return "Submitted written answers.";
  if (text.startsWith("[[SKIP_QUIZ]]")) return "Asked to keep teaching instead of retesting.";
  const nav = text.match(/^\[NAV\]\s+unit_id=\S+\s*(.*)$/);
  if (nav) return nav[1] || "Opened a unit.";
  return text;
}

const TEST_REQUEST = /^(quiz|test|ready)(\s+me)?[.!]?\s*$/i;

export function ChatPanel({
  messages,
  mode,
  quiz,
  isLoading,
  onSend,
  onQuiz,
  onCite,
  onBegin,
  beginLabel,
  citeIndex,
}: {
  messages: Message[];
  mode?: TutorState["mode"];
  quiz?: { questions: QuizQuestion[] } | null;
  isLoading: boolean;
  onSend: (text: string) => void;
  onQuiz: (answers: { id: string; answer: string }[]) => void;
  onCite: (id: string) => void;
  onBegin?: () => void;
  beginLabel?: string;
  citeIndex: CiteIndex;
}) {
  const [draft, setDraft] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);
  const showQuiz = mode === "test" && Boolean(quiz?.questions?.length);
  const askedForTest = useMemo(() => {
    for (const message of [...messages].reverse()) {
      if (message.type !== "human") continue;
      const text = messageText(message).trim();
      if (!text || text.startsWith("[[") || text.startsWith("[NAV]")) continue;
      return TEST_REQUEST.test(text) || /\b(quiz me|test me|ready to be tested)\b/i.test(text);
    }
    return false;
  }, [messages]);

  const visible = useMemo(
    () =>
      messages.filter((message) => {
        if (message.type === "tool") return false;
        const text = messageText(message);
        if (!text.trim()) return false;
        const extra =
          "additional_kwargs" in message
            ? (message.additional_kwargs as Record<string, unknown> | undefined)
            : undefined;
        return !isContextSummary(text, extra);
      }),
    [messages],
  );

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [visible.length, isLoading, showQuiz]);

  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden bg-[#f7f1e6]">
      <div ref={scrollRef} className="chat-scroll flex min-h-0 flex-1 flex-col overflow-y-auto px-4 py-4">
        <div className="mt-auto flex flex-col gap-3">
          {visible.length === 0 && !isLoading && (
            <div className="rounded-lg border border-[#d9c9ae] bg-[#efe4cc] px-4 py-5 font-[family-name:var(--font-serif)] text-[#4a4036]">
              <p className="text-[16px] text-[#1c1612]">A close-reading tutor, not a summary bot.</p>
              <p className="mt-2 text-[14px] leading-relaxed">
                It will teach this author’s argument, then test you in your own words. Weak points get
                reteaching. The next unit stays locked until this one is internalized.
              </p>
              {onBegin && (
                <button
                  type="button"
                  onClick={onBegin}
                  className="mt-4 rounded-md bg-[#1c2d24] px-3 py-2 text-[13px] font-medium text-[#f3ead8]"
                >
                  {beginLabel || "Begin"}
                </button>
              )}
            </div>
          )}
          {visible.map((message) => {
            const text = messageText(message);
            const human = message.type === "human";
            return (
              <div
                key={message.id ?? `${message.type}-${text.slice(0, 24)}`}
                className={human ? "ml-8" : "mr-4"}
              >
                <div
                  className={
                    human
                      ? "rounded-lg bg-[#1c2d24] px-3 py-2 text-[14px] text-[#f3ead8]"
                      : "rounded-lg border border-[#d9c9ae] bg-white/50 px-3 py-2"
                  }
                >
                  {human ? (
                    displayHuman(text)
                  ) : (
                    <TutorMarkdown text={text} onCite={onCite} citeIndex={citeIndex} />
                  )}
                </div>
              </div>
            );
          })}
          {isLoading && (
            <div className="text-[12px] tracking-wide text-[#9a7840] uppercase">Tutor is working…</div>
          )}
        </div>
      </div>

      {showQuiz ? (
        <QuizForm
          key={quiz!.questions.map((q) => q.id).join("-")}
          questions={quiz!.questions}
          disabled={isLoading}
          onSubmit={onQuiz}
          onKeepTeaching={
            askedForTest
              ? undefined
              : () =>
                  onSend(
                    "[[SKIP_QUIZ]] Continue teaching claims in this unit I have not yet covered. Do not present the same quiz again.",
                  )
          }
        />
      ) : (
        <form
          className="flex gap-2 border-t border-[#d9c9ae] p-3"
          onSubmit={(event) => {
            event.preventDefault();
            const text = draft.trim();
            if (!text || isLoading) return;
            onSend(text);
            setDraft("");
          }}
        >
          <textarea
            rows={2}
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                event.currentTarget.form?.requestSubmit();
              }
            }}
            placeholder="Ask, object, or say you are ready to be tested."
            className="flex-1 resize-none rounded-md border border-[#d9c9ae] bg-white/70 px-3 py-2 text-[14px] outline-none focus:border-[#9a7840]"
          />
          <button
            type="submit"
            disabled={isLoading || !draft.trim()}
            className="self-end rounded-md bg-[#1c2d24] p-2 text-[#f3ead8] disabled:opacity-40"
            aria-label="Send"
          >
            <Send className="size-4" />
          </button>
        </form>
      )}
    </div>
  );
}
