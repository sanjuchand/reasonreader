import { NextResponse } from "next/server";
import { eq } from "drizzle-orm";
import { db } from "@/lib/db";
import { users } from "@/lib/db/schema";
import { GoogleTokenError, verifyGoogleIdToken } from "@/lib/auth/google";
import { createSessionToken, sessionCookieOptions, SESSION_COOKIE_NAME } from "@/lib/auth/session";
import { seedFirstUnit } from "@/lib/progress";
import { DEMO_COPY_ID } from "@/lib/constants";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  const body = (await request.json().catch(() => null)) as { credential?: string } | null;
  const credential = body?.credential;
  if (!credential) {
    return NextResponse.json({ detail: "Missing credential" }, { status: 400 });
  }
  try {
    const claims = await verifyGoogleIdToken(credential);
    const email = claims.email || "";
    const name = claims.name || "";
    const avatarUrl = claims.picture || "";
    const existing = await db.select().from(users).where(eq(users.googleSub, claims.sub)).limit(1);
    let user = existing[0];
    if (!user) {
      const inserted = await db
        .insert(users)
        .values({ googleSub: claims.sub, email, name, avatarUrl })
        .returning();
      user = inserted[0];
      await seedFirstUnit(user.id, DEMO_COPY_ID);
    } else {
      const updated = await db
        .update(users)
        .set({ email, name, avatarUrl })
        .where(eq(users.id, user.id))
        .returning();
      user = updated[0];
    }
    const token = await createSessionToken(user.id);
    const response = NextResponse.json({
      id: user.id,
      email: user.email,
      name: user.name,
      avatarUrl: user.avatarUrl,
    });
    response.cookies.set(SESSION_COOKIE_NAME, token, sessionCookieOptions());
    return response;
  } catch (err) {
    const detail = err instanceof GoogleTokenError ? err.message : "Sign-in failed";
    return NextResponse.json({ detail }, { status: 401 });
  }
}
