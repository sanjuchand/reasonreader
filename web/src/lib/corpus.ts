import { promises as fs } from "node:fs";
import path from "node:path";
import type { Corpus, Unit } from "@/lib/types";

export async function loadCorpus(): Promise<Corpus> {
  const file = path.join(process.cwd(), "..", "corpus", "chapters.json");
  const raw = await fs.readFile(file, "utf8");
  return JSON.parse(raw) as Corpus;
}

export function firstUnitId(units: Unit[]): string | undefined {
  return units[0]?.id;
}
