"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useStream } from "@langchain/langgraph-sdk/react";
import { BookOpen, LogOut, RotateCcw } from "lucide-react";
import { ChatPanel } from "@/components/ChatPanel";
import { Reader } from "@/components/Reader";
import { Toc } from "@/components/Toc";
import { useAuth } from "@/components/AuthProvider";
import { buildCiteIndex } from "@/lib/cites";
import type { Corpus, ProgressPayload, TutorState, Unit } from "@/lib/types";

const ASSISTANT_ID = process.env.NEXT_PUBLIC_ASSISTANT_ID || "agent";

function unitLabel(unit: Unit) {
  const part = unit.part_title ? ` — ${unit.part_title}` : "";
  return `${unit.book}: ${unit.title}${part}`;
}

export function Studio() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!authLoading && !user) router.replace("/login");
  }, [authLoading, user, router]);

  if (authLoading || !user) {
    return <div className="h-screen bg-[#1c2d24]" />;
  }
  return <StudioApp user={user} />;
}

function StudioApp({ user }: { user: NonNullable<ReturnType<typeof useAuth>["user"]> }) {
  const { logout } = useAuth();
  const router = useRouter();
  const [corpus, setCorpus] = useState<Corpus | null>(null);
  const [corpusError, setCorpusError] = useState<string | null>(null);
  const [progress, setProgress] = useState<ProgressPayload | null>(null);
  const [pinnedId, setPinnedId] = useState<string | null>(null);
  const [highlightId, setHighlightId] = useState<string | null>(null);
  const [connected, setConnected] = useState<boolean | null>(null);
  const [threadId, setThreadId] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/corpus")
      .then(async (res) => {
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "Failed to load corpus");
        setCorpus(data);
      })
      .catch((err: Error) => setCorpusError(err.message));
  }, []);

  const refreshProgress = useCallback(() => {
    return fetch("/api/progress")
      .then(async (res) => {
        if (!res.ok) return;
        setProgress(await res.json());
      })
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    if (!user) return;
    void refreshProgress();
  }, [user, refreshProgress]);

  useEffect(() => {
    fetch("/api/tutor/info")
      .then((res) => setConnected(res.ok))
      .catch(() => setConnected(false));
  }, []);

  const stream = useStream<TutorState>({
    apiUrl: "/api/tutor",
    assistantId: ASSISTANT_ID,
    threadId,
    onThreadId: (id) => setThreadId(id),
  });

  const values = stream.values;
  const units = corpus?.units ?? [];
  const mastery = useMemo(() => {
    if (values.mastery && Object.keys(values.mastery).length) return values.mastery;
    return progress?.mastery ?? {};
  }, [values.mastery, progress]);
  const firstId = units[0]?.id;
  const activeId = pinnedId ?? values.current_chapter_id ?? progress?.currentUnitId ?? firstId;
  const activeUnit = useMemo(
    () => units.find((unit) => unit.id === activeId),
    [units, activeId],
  );
  const citeIndex = useMemo(() => buildCiteIndex(units), [units]);

  const lastSyncedMastery = useRef("");

  useEffect(() => {
    if (values.last_judgment && values.current_chapter_id) {
      setPinnedId(null);
    }
  }, [values.last_judgment, values.current_chapter_id]);

  useEffect(() => {
    if (!values.mastery || !Object.keys(values.mastery).length) return;
    const encoded = JSON.stringify(values.mastery);
    if (encoded === lastSyncedMastery.current) return;
    lastSyncedMastery.current = encoded;
    void fetch("/api/progress", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mastery: values.mastery }),
    }).then(() => refreshProgress());
  }, [values.mastery, refreshProgress]);

  const submitText = useCallback(
    (text: string, extra?: Partial<TutorState>) => {
      stream.submit({
        messages: [{ type: "human", content: text }],
        current_chapter_id: extra?.current_chapter_id ?? activeId,
        ...extra,
      });
    },
    [stream, activeId],
  );

  const openUnit = useCallback(
    (id: string) => {
      const unit = units.find((item) => item.id === id);
      if (!unit) return;
      const entry = mastery[id];
      if (!entry?.unlocked && id !== firstId) return;
      setPinnedId(id);
      submitText(`[NAV] unit_id=${id} I am now reading: ${unitLabel(unit)}. Teach this unit.`, {
        current_chapter_id: id,
        mode: "teach",
        open_quiz: null,
      });
    },
    [units, mastery, firstId, submitText],
  );

  const reset = async () => {
    if (!window.confirm("Reset your progress and start the Introduction again?")) return;
    const res = await fetch("/api/progress", { method: "DELETE" });
    const data = await res.json().catch(() => ({}));
    setPinnedId(null);
    if (data.threadId) setThreadId(data.threadId);
    await refreshProgress();
    window.location.reload();
  };

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-[#1c2d24] font-[family-name:var(--font-sans)]">
      <header className="flex items-center justify-between border-b border-white/10 px-4 py-2.5 text-[#efe6d4]">
        <div className="flex items-center gap-2">
          <BookOpen className="size-4 text-[#c4a15a]" />
          <div>
            <div className="text-[13px] font-semibold tracking-wide">The Wealth of Nations</div>
            <div className="text-[11px] text-[#cbbda4]">
              Chapter-mastery tutor · {values.mode ?? "teach"}
              {activeUnit ? ` · ${activeUnit.book}` : ""}
              {progress ? ` · ~${Math.round((progress.remainingWords || 0) / 100) / 10}k words left` : ""}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3 text-[12px]">
          {connected === false && <span className="text-[#e2b1a0]">Graph not reachable</span>}
          <span className="max-w-[140px] truncate text-[#cbbda4]" title={user.email}>
            {user.name || user.email}
          </span>
          <button
            type="button"
            onClick={() => void reset()}
            className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-[#cbbda4] hover:bg-white/10 hover:text-white"
          >
            <RotateCcw className="size-3.5" />
            Reset
          </button>
          <button
            type="button"
            onClick={() => logout().then(() => router.replace("/login"))}
            className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-[#cbbda4] hover:bg-white/10 hover:text-white"
          >
            <LogOut className="size-3.5" />
            Sign out
          </button>
        </div>
      </header>

      {corpusError && (
        <div className="bg-[#8a2f2f] px-4 py-2 text-[13px] text-white">{corpusError}</div>
      )}

      <div className="grid min-h-0 flex-1 grid-cols-[280px_minmax(0,1.15fr)_minmax(320px,0.9fr)] overflow-hidden">
        <aside className="min-h-0 overflow-hidden border-r border-white/10 bg-[#17241d]">
          <Toc
            units={units}
            mastery={
              Object.keys(mastery).length
                ? mastery
                : firstId
                  ? { [firstId]: { unlocked: true, status: "in_progress", score: 0 } }
                  : {}
            }
            activeId={activeId}
            onSelect={openUnit}
            books={progress?.books}
            remainingWords={progress?.remainingWords}
            remainingUnits={progress?.remainingUnits}
          />
        </aside>
        <main className="min-h-0 min-w-0 overflow-hidden bg-[#f3ead8]">
          <Reader unit={activeUnit} highlightId={highlightId} />
        </main>
        <section className="flex min-h-0 min-w-0 flex-col overflow-hidden border-l border-[#d9c9ae]">
          <ChatPanel
            messages={stream.messages ?? []}
            mode={values.mode}
            quiz={values.open_quiz}
            isLoading={stream.isLoading}
            onCite={setHighlightId}
            citeIndex={citeIndex}
            onBegin={firstId ? () => openUnit(firstId) : undefined}
            onSend={(text) => submitText(text)}
            onQuiz={(answers) =>
              submitText(`[[QUIZ_SUBMISSION]]\n${JSON.stringify({ answers })}`)
            }
          />
        </section>
      </div>
    </div>
  );
}
