import { copyKey, getBytes, objectExists } from "@/lib/s3";
import type { Corpus, Unit } from "@/lib/types";

export async function loadCorpus(copyId: string): Promise<Corpus> {
  const key = copyKey(copyId, "chapters.json");
  if (!(await objectExists(key))) {
    throw new Error("Corpus not built for this copy.");
  }
  const raw = await getBytes(key);
  return JSON.parse(raw.toString("utf8")) as Corpus;
}

export function firstUnitId(units: Unit[]): string | undefined {
  return units[0]?.id;
}
