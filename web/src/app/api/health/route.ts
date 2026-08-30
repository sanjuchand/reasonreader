import { NextResponse } from "next/server";
import { checkHealth, pingDatabase } from "@/lib/health";

export const dynamic = "force-dynamic";

export async function GET() {
  const health = await checkHealth(() => pingDatabase(process.env.DATABASE_URL));
  return NextResponse.json(health, { status: health.ok ? 200 : 503 });
}
