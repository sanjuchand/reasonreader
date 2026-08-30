import { NextRequest, NextResponse } from "next/server";
import { getSessionUser } from "@/lib/auth/current-user";
import { langgraphUrl } from "@/lib/auth/config";
import { createGuestThread, ensureThread, isAnonymousThread, userOwnsThread } from "@/lib/langgraph";
import { replaceProgress } from "@/lib/progress";
import { getAccessibleCopy } from "@/lib/copies";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";
export const maxDuration = 300;

type Ctx = { params: Promise<{ copyId: string; path: string[] }> };

function threadIdFrom(path: string[]) {
  if (path[0] === "threads" && path[1] && path[1] !== "search") return path[1];
  return null;
}

async function persistMasteryFromBody(userId: string, copyId: string, body: unknown) {
  if (!body || typeof body !== "object") return;
  const record = body as { values?: { mastery?: Record<string, never> }; mastery?: Record<string, never> };
  const mastery = record.values?.mastery || record.mastery;
  if (mastery && typeof mastery === "object") {
    await replaceProgress(userId, copyId, mastery);
  }
}

export async function GET(request: NextRequest, ctx: Ctx) {
  return proxy(request, ctx);
}
export async function POST(request: NextRequest, ctx: Ctx) {
  return proxy(request, ctx);
}
export async function PUT(request: NextRequest, ctx: Ctx) {
  return proxy(request, ctx);
}
export async function PATCH(request: NextRequest, ctx: Ctx) {
  return proxy(request, ctx);
}
export async function DELETE(request: NextRequest, ctx: Ctx) {
  return proxy(request, ctx);
}

async function proxy(request: NextRequest, ctx: Ctx) {
  const user = await getSessionUser();
  const { copyId, path } = await ctx.params;
  const copy = await getAccessibleCopy(user?.id ?? null, copyId);
  if (!copy) {
    return NextResponse.json({ detail: "Not found" }, { status: 404 });
  }
  if (copy.kind !== "demo" && !user) {
    return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  }

  const segments = path || [];
  const needsThread = segments[0] === "threads";
  let owned = "";
  try {
    if (needsThread && user) {
      owned = await ensureThread(user.id, copyId);
    } else if (needsThread && request.method === "POST" && segments.length === 1) {
      owned = await createGuestThread(copyId);
    }
  } catch (err) {
    const detail = err instanceof Error ? err.message : "Failed to open tutor thread";
    return NextResponse.json({ detail }, { status: 500 });
  }
  const targetThread = threadIdFrom(segments);
  if (needsThread && targetThread) {
    if (user && !userOwnsThread(owned, targetThread)) {
      return NextResponse.json({ detail: "Thread not found" }, { status: 404 });
    }
    if (!user && !(await isAnonymousThread(targetThread))) {
      return NextResponse.json({ detail: "Thread not found" }, { status: 404 });
    }
  }

  if (request.method === "POST" && segments.length === 1 && segments[0] === "threads") {
    return NextResponse.json({ thread_id: owned });
  }

  const search = request.nextUrl.search;
  const upstream = `${langgraphUrl()}/${segments.join("/")}${search}`;
  const headers = new Headers();
  const accept = request.headers.get("accept");
  if (accept) headers.set("accept", accept);
  headers.set("content-type", request.headers.get("content-type") || "application/json");

  let body: string | undefined;
  if (request.method !== "GET" && request.method !== "HEAD") {
    const raw = await request.text();
    if (raw) {
      try {
        const parsed = JSON.parse(raw) as { input?: Record<string, unknown>; values?: Record<string, unknown> };
        if (parsed.input && typeof parsed.input === "object") {
          parsed.input.user_id = user?.id ?? null;
          parsed.input.copy_id = copyId;
        }
        if (parsed.values && typeof parsed.values === "object") {
          parsed.values.user_id = user?.id ?? null;
          parsed.values.copy_id = copyId;
        }
        body = JSON.stringify(parsed);
      } catch {
        body = raw;
      }
    }
  }

  const response = await fetch(upstream, {
    method: request.method,
    headers,
    body,
  });

  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("text/event-stream")) {
    return new NextResponse(response.body, {
      status: response.status,
      headers: {
        "Content-Type": contentType,
        "Cache-Control": "no-cache",
      },
    });
  }

  const text = await response.text();
  if (response.ok && text) {
    try {
      if (user) await persistMasteryFromBody(user.id, copyId, JSON.parse(text));
    } catch {
      /* ignore non-json */
    }
  }
  return new NextResponse(text, {
    status: response.status,
    headers: { "Content-Type": contentType || "application/json" },
  });
}
