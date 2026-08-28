import { promises as fs } from "node:fs";
import path from "node:path";
import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET() {
  const file = path.join(process.cwd(), "..", "corpus", "chapters.json");
  try {
    const raw = await fs.readFile(file, "utf8");
    return NextResponse.json(JSON.parse(raw));
  } catch {
    return NextResponse.json(
      {
        error:
          "Corpus not built. Run `uv run python ingest.py --embed` from the project root.",
      },
      { status: 404 },
    );
  }
}
