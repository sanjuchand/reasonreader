import { NextResponse } from "next/server";
import { getSessionUser } from "@/lib/auth/current-user";
import { getAccessibleCopy, publicCopy } from "@/lib/copies";

export const dynamic = "force-dynamic";

type Ctx = { params: Promise<{ id: string }> };

export async function GET(_request: Request, ctx: Ctx) {
  const user = await getSessionUser();
  if (!user) return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  const { id } = await ctx.params;
  const copy = await getAccessibleCopy(user.id, id);
  if (!copy) return NextResponse.json({ detail: "Not found" }, { status: 404 });
  return NextResponse.json({ copy: publicCopy(copy) });
}
