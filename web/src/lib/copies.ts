import { and, eq, or } from "drizzle-orm";
import { db } from "@/lib/db";
import { copies } from "@/lib/db/schema";
import { canReadCopy } from "@/lib/copies-access";

export type CopyRow = typeof copies.$inferSelect;

export async function getAccessibleCopy(userId: string | null, copyId: string): Promise<CopyRow | null> {
  const rows = await db.select().from(copies).where(eq(copies.id, copyId)).limit(1);
  const copy = rows[0];
  if (!copy) return null;
  return canReadCopy(copy, userId) ? copy : null;
}

export async function listDemoCopies(): Promise<CopyRow[]> {
  return db.select().from(copies).where(eq(copies.kind, "demo")).orderBy(copies.createdAt);
}

export async function listVisibleCopies(userId: string): Promise<CopyRow[]> {
  return db
    .select()
    .from(copies)
    .where(or(eq(copies.kind, "demo"), and(eq(copies.kind, "private"), eq(copies.ownerId, userId))))
    .orderBy(copies.createdAt);
}

export function publicCopy(copy: CopyRow) {
  return {
    id: copy.id,
    kind: copy.kind,
    title: copy.title,
    author: copy.author,
    status: copy.status,
    error: copy.error,
    createdAt: copy.createdAt,
  };
}
