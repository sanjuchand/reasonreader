import { NextResponse } from "next/server";
import { getSessionUser } from "@/lib/auth/current-user";
import { loadCorpus } from "@/lib/corpus";
import { loadMasteryMap, replaceProgress, resetProgress } from "@/lib/progress";
import { replaceThread } from "@/lib/langgraph";
import type { MasteryEntry, Unit } from "@/lib/types";

export const dynamic = "force-dynamic";

export type BookProgress = {
  book: string;
  totalUnits: number;
  masteredUnits: number;
  totalWords: number;
  masteredWords: number;
  remainingWords: number;
};

export type ProgressPayload = {
  mastery: Record<string, MasteryEntry>;
  books: BookProgress[];
  remainingWords: number;
  remainingUnits: number;
  currentUnitId: string | null;
};

function statusOf(unit: Unit, mastery: Record<string, MasteryEntry>): string {
  return mastery[unit.id]?.status || (mastery[unit.id]?.unlocked ? "in_progress" : "locked");
}

export async function GET() {
  const user = await getSessionUser();
  if (!user) return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  const corpus = await loadCorpus();
  const mastery = await loadMasteryMap(user.id);
  const books: BookProgress[] = [];
  for (const unit of corpus.units) {
    let group = books[books.length - 1];
    if (!group || group.book !== unit.book) {
      group = {
        book: unit.book,
        totalUnits: 0,
        masteredUnits: 0,
        totalWords: 0,
        masteredWords: 0,
        remainingWords: 0,
      };
      books.push(group);
    }
    group.totalUnits += 1;
    group.totalWords += unit.word_count;
    const mastered = statusOf(unit, mastery) === "mastered";
    if (mastered) {
      group.masteredUnits += 1;
      group.masteredWords += unit.word_count;
    } else {
      group.remainingWords += unit.word_count;
    }
  }
  const remainingWords = books.reduce((sum, book) => sum + book.remainingWords, 0);
  const remainingUnits = corpus.units.filter((unit) => statusOf(unit, mastery) !== "mastered").length;
  const current =
    corpus.units.find((unit) => {
      const status = statusOf(unit, mastery);
      return status === "in_progress" || status === "revise";
    }) || corpus.units.find((unit) => mastery[unit.id]?.unlocked && statusOf(unit, mastery) !== "mastered");
  const payload: ProgressPayload = {
    mastery,
    books,
    remainingWords,
    remainingUnits,
    currentUnitId: current?.id ?? corpus.units[0]?.id ?? null,
  };
  return NextResponse.json(payload);
}

export async function POST(request: Request) {
  const user = await getSessionUser();
  if (!user) return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  const body = (await request.json().catch(() => null)) as { mastery?: Record<string, MasteryEntry> } | null;
  if (!body?.mastery) {
    return NextResponse.json({ detail: "Missing mastery" }, { status: 400 });
  }
  await replaceProgress(user.id, body.mastery);
  return NextResponse.json({ ok: true });
}

export async function DELETE() {
  const user = await getSessionUser();
  if (!user) return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  await resetProgress(user.id);
  const threadId = await replaceThread(user.id);
  return NextResponse.json({ ok: true, threadId });
}
