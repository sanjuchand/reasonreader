import type { MasteryEntry } from "@/lib/types";

export type GraphThreadPresence = "ok" | "missing" | "error";
export type MasteryMap = Record<string, MasteryEntry>;

export function currentChapter(mastery: MasteryMap, firstId: string) {
  const inPlay = Object.entries(mastery).find(
    ([, entry]) => entry.status === "in_progress" || entry.status === "revise",
  );
  if (inPlay) return inPlay[0];
  const unlocked = Object.entries(mastery).filter(([, entry]) => entry.unlocked && entry.status !== "mastered");
  return unlocked.at(-1)?.[0] || firstId;
}

export function threadValues(copyId: string, userId: string | null, mastery: MasteryMap, firstId: string) {
  const next: MasteryMap = { ...mastery };
  if (!next[firstId]) {
    next[firstId] = { unlocked: true, status: "in_progress", score: 0 };
  }
  return {
    mastery: next,
    current_chapter_id: currentChapter(next, firstId),
    mode: "teach" as const,
    user_id: userId,
    copy_id: copyId,
  };
}

export async function restoreMissingThread(
  storedId: string | null,
  presence: (id: string) => Promise<GraphThreadPresence>,
  restore: (id: string) => Promise<void>,
): Promise<string | null> {
  if (!storedId) return null;
  if ((await presence(storedId)) === "missing") await restore(storedId);
  return storedId;
}
