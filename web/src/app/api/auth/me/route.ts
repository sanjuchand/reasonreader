import { NextResponse } from "next/server";
import { getSessionUser } from "@/lib/auth/current-user";

export const dynamic = "force-dynamic";

export async function GET() {
  const user = await getSessionUser();
  if (!user) {
    return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  }
  return NextResponse.json(user);
}
