import type { Unit } from "@/lib/types";

export type CiteHit = {
  book: string;
  title: string;
  n: number;
  snippet: string;
};

export type CiteIndex = Record<string, CiteHit>;

const CITE_RE = /\[@([^\]]+)\]|\[((?:u\d+|chap\d+(?:-p\d+)?):p\d+)\]/g;
const PARA_ID = /(?:u\d+|chap\d+(?:-p\d+)?):p\d+/;

export function buildCiteIndex(units: Unit[]): CiteIndex {
  const index: CiteIndex = {};
  for (const unit of units) {
    unit.paragraphs.forEach((paragraph, i) => {
      index[paragraph.paragraph_id] = {
        book: unit.book,
        title: unit.title,
        n: i + 1,
        snippet: paragraph.text.slice(0, 180),
      };
    });
  }
  return index;
}

export function shortChapter(title: string): string {
  if (/INTRODUCTION/i.test(title)) return "Intro";
  const match = title.match(/CHAPTER\s+([IVXLCDM]+)/i);
  if (match) return `Ch. ${match[1]}`;
  return title.replace(/\s+/g, " ").slice(0, 28);
}

export function citeButtonLabel(id: string, index: CiteIndex): string {
  const hit = index[id];
  if (!hit) return `¶ ${id}`;
  const chapter = shortChapter(hit.title);
  if (hit.book === "Introduction") return `Intro · ¶${hit.n}`;
  return `${hit.book} · ${chapter} · ¶${hit.n}`;
}

export function citeHover(id: string, index: CiteIndex): string {
  const hit = index[id];
  if (!hit) return "Show this passage in the reader";
  const ellipsis = hit.snippet.length >= 180 ? "…" : "";
  return `${hit.snippet}${ellipsis}`;
}

export function expandCiteInner(inner: string): string[] {
  return inner
    .split(/\s*-@\s*|\s*,\s*/)
    .map((part) => part.replace(/^@/, "").trim())
    .filter((id) => PARA_ID.test(id));
}

export function linkifyCites(text: string, index: CiteIndex): string {
  return text.replace(CITE_RE, (full, atInner?: string, bare?: string) => {
    const ids = expandCiteInner(atInner ?? bare ?? "");
    if (!ids.length) return full;
    return ids
      .map((id) => ` [${citeButtonLabel(id, index)}](#cite=${encodeURIComponent(id)})`)
      .join("");
  });
}

export function isContextSummary(text: string, extra?: Record<string, unknown> | null): boolean {
  if (extra && extra.lc_source === "summarization") return true;
  const trimmed = text.trimStart();
  return (
    trimmed.startsWith("Here is a summary of the conversation to date:") ||
    trimmed.startsWith("Previous conversation was too long to summarize.")
  );
}
