import { NextResponse } from "next/server";
import { getSessionUser } from "@/lib/auth/current-user";
import { getAccessibleCopy } from "@/lib/copies";
import { loadCorpus } from "@/lib/corpus";

export const dynamic = "force-dynamic";

type Ctx = { params: Promise<{ id: string }> };

export async function GET(_request: Request, ctx: Ctx) {
  const user = await getSessionUser();
  if (!user) return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  const { id } = await ctx.params;
  const copy = await getAccessibleCopy(user.id, id);
  if (!copy) return NextResponse.json({ detail: "Not found" }, { status: 404 });
  if (copy.status !== "ready") {
    return NextResponse.json({ error: "Copy is not ready", status: copy.status }, { status: 409 });
  }
  try {
    const corpus = await loadCorpus(copy.id);
    return NextResponse.json(corpus);
  } catch {
    return NextResponse.json({ error: "Corpus not built for this copy." }, { status: 404 });
  }
}
