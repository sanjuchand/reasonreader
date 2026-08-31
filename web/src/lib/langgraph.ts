import { and, eq } from "drizzle-orm";
import { db } from "@/lib/db";
import { userThreads } from "@/lib/db/schema";
import { assistantId, langgraphUrl } from "@/lib/auth/config";
import { firstUnitId, loadCorpus } from "@/lib/corpus";
import { loadMasteryMap } from "@/lib/progress";
import type { MasteryMap } from "@/lib/langgraph-thread";
import { restoreMissingThread, threadValues } from "@/lib/langgraph-thread";

export { currentChapter, restoreMissingThread, threadValues } from "@/lib/langgraph-thread";
export type { GraphThreadPresence, MasteryMap } from "@/lib/langgraph-thread";

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

export async function graphThreadPresence(threadId: string) {
  try {
    const response = await fetch(`${langgraphUrl()}/threads/${encodeURIComponent(threadId)}`);
    if (response.ok) return "ok" as const;
    if (response.status === 404) return "missing" as const;
    return "error" as const;
  } catch {
    return "error" as const;
  }
}

async function createThreadWithState(
  copyId: string,
  userId: string | null,
  mastery: MasteryMap,
  threadId?: string,
) {
  const created = await fetch(`${langgraphUrl()}/threads`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      metadata: { graph_id: assistantId() },
      ...(threadId ? { thread_id: threadId } : {}),
    }),
  });
  if (!created.ok && created.status !== 409) {
    const text = await created.text();
    throw new Error(text || `LangGraph ${created.status}`);
  }
  const payload = created.ok ? ((await created.json()) as { thread_id: string }) : { thread_id: threadId || "" };
  const id = payload.thread_id || threadId;
  if (!id) throw new Error("LangGraph did not return a thread id");
  const corpus = await loadCorpus(copyId);
  const first = firstUnitId(corpus.units) || "u0000";
  await langgraph(`/threads/${id}/state`, {
    method: "POST",
    body: JSON.stringify({ values: threadValues(copyId, userId, mastery, first) }),
  });
  return id;
}

export async function createGuestThread(copyId: string): Promise<string> {
  return createThreadWithState(copyId, null, {});
}

export async function ensureThread(userId: string, copyId: string): Promise<string> {
  const existing = await db
    .select()
    .from(userThreads)
    .where(and(eq(userThreads.userId, userId), eq(userThreads.copyId, copyId)))
    .limit(1);
  const stored = existing[0]?.langgraphThreadId ?? null;
  const kept = await restoreMissingThread(stored, graphThreadPresence, async (id) => {
    const mastery = await loadMasteryMap(userId, copyId);
    await createThreadWithState(copyId, userId, mastery, id);
  });
  if (kept) return kept;

  const mastery = await loadMasteryMap(userId, copyId);
  const threadId = await createThreadWithState(copyId, userId, mastery);
  await db.insert(userThreads).values({ userId, copyId, langgraphThreadId: threadId });
  return threadId;
}

export async function replaceThread(userId: string, copyId: string): Promise<string> {
  await db
    .delete(userThreads)
    .where(and(eq(userThreads.userId, userId), eq(userThreads.copyId, copyId)));
  return ensureThread(userId, copyId);
}

export function userOwnsThread(userThreadId: string, requestedId: string) {
  return userThreadId === requestedId;
}

export async function isAnonymousThread(threadId: string): Promise<boolean> {
  try {
    const response = await langgraph(`/threads/${threadId}/state`);
    const payload = (await response.json()) as { values?: { user_id?: string | null } };
    return !payload.values?.user_id;
  } catch {
    return false;
  }
}
