import { eq } from "drizzle-orm";
import { db } from "@/lib/db";
import { userThreads } from "@/lib/db/schema";
import { langgraphUrl } from "@/lib/auth/config";
import { firstUnitId, loadCorpus } from "@/lib/corpus";
import { loadMasteryMap } from "@/lib/progress";

async function langgraph(path: string, init?: RequestInit) {
  const response = await fetch(`${langgraphUrl()}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `LangGraph ${response.status}`);
  }
  return response;
}

function currentChapter(mastery: Record<string, { status?: string; unlocked?: boolean }>, firstId: string) {
  const inPlay = Object.entries(mastery).find(
    ([, entry]) => entry.status === "in_progress" || entry.status === "revise",
  );
  if (inPlay) return inPlay[0];
  const unlocked = Object.entries(mastery).filter(([, entry]) => entry.unlocked && entry.status !== "mastered");
  return unlocked.at(-1)?.[0] || firstId;
}

export async function ensureThread(userId: string): Promise<string> {
  const existing = await db.select().from(userThreads).where(eq(userThreads.userId, userId)).limit(1);
  if (existing[0]) return existing[0].langgraphThreadId;

  const created = await langgraph("/threads", { method: "POST", body: "{}" });
  const payload = (await created.json()) as { thread_id: string };
  const threadId = payload.thread_id;
  const corpus = await loadCorpus();
  const first = firstUnitId(corpus.units) || "chap01";
  const mastery = await loadMasteryMap(userId);
  if (!mastery[first]) {
    mastery[first] = { unlocked: true, status: "in_progress", score: 0 };
  }
  await langgraph(`/threads/${threadId}/state`, {
    method: "POST",
    body: JSON.stringify({
      values: {
        mastery,
        current_chapter_id: currentChapter(mastery, first),
        mode: "teach",
        user_id: userId,
      },
    }),
  });
  await db.insert(userThreads).values({ userId, langgraphThreadId: threadId });
  return threadId;
}

export async function replaceThread(userId: string): Promise<string> {
  await db.delete(userThreads).where(eq(userThreads.userId, userId));
  return ensureThread(userId);
}

export function userOwnsThread(userThreadId: string, requestedId: string) {
  return userThreadId === requestedId;
}
