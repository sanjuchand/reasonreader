import { NextResponse } from "next/server";
import { eq } from "drizzle-orm";
import { getSessionUser } from "@/lib/auth/current-user";
import { listVisibleCopies, publicCopy } from "@/lib/copies";
import { db } from "@/lib/db";
import { copies } from "@/lib/db/schema";
import { copyKey, putBytes } from "@/lib/s3";
import { runIngest } from "@/lib/ingest";
import { MAX_UPLOAD_BYTES } from "@/lib/constants";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";
export const maxDuration = 300;

export async function GET() {
  const user = await getSessionUser();
  if (!user) return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  const rows = await listVisibleCopies(user.id);
  return NextResponse.json({ copies: rows.map(publicCopy) });
}

export async function POST(request: Request) {
  const user = await getSessionUser();
  if (!user) return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  const form = await request.formData();
  const attested = form.get("rightsAttested");
  if (attested !== "true" && attested !== "on") {
    return NextResponse.json({ detail: "You must attest that you have the right to read this copy." }, { status: 400 });
  }
  const file = form.get("file");
  if (!(file instanceof File)) {
    return NextResponse.json({ detail: "Missing file" }, { status: 400 });
  }
  if (file.size > MAX_UPLOAD_BYTES) {
    return NextResponse.json({ detail: "File too large (40MB max)" }, { status: 400 });
  }
  const name = file.name || "upload";
  const lower = name.toLowerCase();
  const type = file.type || "";
  const kind = type.includes("pdf") || lower.endsWith(".pdf") ? "pdf" : type.includes("epub") || lower.endsWith(".epub") ? "epub" : null;
  if (!kind) {
    return NextResponse.json({ detail: "PDF or EPUB only" }, { status: 400 });
  }
  const contentType = kind === "pdf" ? "application/pdf" : "application/epub+zip";
  const inserted = await db
    .insert(copies)
    .values({
      kind: "private",
      ownerId: user.id,
      title: name.replace(/\.(pdf|epub)$/i, "") || "Untitled",
      author: "",
      status: "ingesting",
      sourceContentType: contentType,
      sourceFilename: name,
      rightsAttestedAt: new Date(),
    })
    .returning();
  const copy = inserted[0];
  const bytes = Buffer.from(await file.arrayBuffer());
  await putBytes(copyKey(copy.id, "source"), bytes, contentType);
  try {
    await runIngest(copy.id);
  } catch (err) {
    await db
      .update(copies)
      .set({
        status: "failed",
        error: err instanceof Error ? err.message.slice(0, 500) : "Ingest failed",
        updatedAt: new Date(),
      })
      .where(eq(copies.id, copy.id));
    return NextResponse.json({ detail: "Ingest failed", copy: publicCopy({ ...copy, status: "failed" }) }, { status: 500 });
  }
  const fresh = await db.select().from(copies).where(eq(copies.id, copy.id)).limit(1);
  return NextResponse.json({ copy: publicCopy(fresh[0] || copy) });
}
