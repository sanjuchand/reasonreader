import { cookies } from "next/headers";
import { eq } from "drizzle-orm";
import { db } from "@/lib/db";
import { users } from "@/lib/db/schema";
import { decodeSessionToken, SESSION_COOKIE_NAME } from "./session";

export type SessionUser = {
  id: string;
  email: string;
  name: string;
  avatarUrl: string;
};

export async function getSessionUser(): Promise<SessionUser | null> {
  const store = await cookies();
  const token = store.get(SESSION_COOKIE_NAME)?.value;
  if (!token) return null;
  const payload = await decodeSessionToken(token);
  if (!payload) return null;
  const [user] = await db.select().from(users).where(eq(users.id, payload.sub)).limit(1);
  if (!user) return null;
  return {
    id: user.id,
    email: user.email,
    name: user.name,
    avatarUrl: user.avatarUrl,
  };
}
