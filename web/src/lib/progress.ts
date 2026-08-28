import { eq, sql } from "drizzle-orm";
import { db } from "@/lib/db";
import { unitProgress } from "@/lib/db/schema";
import type { MasteryEntry } from "@/lib/types";
import { firstUnitId, loadCorpus } from "@/lib/corpus";

export async function seedFirstUnit(userId: string) {
  const corpus = await loadCorpus();
  const first = firstUnitId(corpus.units);
  if (!first) return;
  await db
    .insert(unitProgress)
    .values({
      userId,
      unitId: first,
      status: "in_progress",
      score: 0,
      unlocked: true,
      concepts: [],
    })
    .onConflictDoNothing();
}

export async function loadMasteryMap(userId: string): Promise<Record<string, MasteryEntry>> {
  const rows = await db.select().from(unitProgress).where(eq(unitProgress.userId, userId));
  const map: Record<string, MasteryEntry> = {};
  for (const row of rows) {
    map[row.unitId] = {
      unlocked: row.unlocked,
      score: row.score,
      status: row.status,
      concepts: (row.concepts as MasteryEntry["concepts"]) ?? [],
    };
  }
  return map;
}

export async function replaceProgress(userId: string, mastery: Record<string, MasteryEntry>) {
  const corpus = await loadCorpus();
  const known = new Set(corpus.units.map((unit) => unit.id));
  const rows = Object.entries(mastery)
    .filter(([unitId]) => known.has(unitId))
    .map(([unitId, entry]) => ({
      userId,
      unitId,
      status: entry.status || (entry.unlocked ? "in_progress" : "locked"),
      score: entry.score ?? 0,
      unlocked: Boolean(entry.unlocked),
      concepts: entry.concepts ?? [],
      updatedAt: new Date(),
    }));
  if (!rows.length) return;
  await db
    .insert(unitProgress)
    .values(rows)
    .onConflictDoUpdate({
      target: [unitProgress.userId, unitProgress.unitId],
      set: {
        status: sql`excluded.status`,
        score: sql`excluded.score`,
        unlocked: sql`excluded.unlocked`,
        concepts: sql`excluded.concepts`,
        updatedAt: sql`excluded.updated_at`,
      },
    });
}

export async function resetProgress(userId: string) {
  await db.delete(unitProgress).where(eq(unitProgress.userId, userId));
  await seedFirstUnit(userId);
}
