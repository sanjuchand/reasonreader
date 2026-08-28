"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { citeHover, linkifyCites, type CiteIndex } from "@/lib/cites";

export function TutorMarkdown({
  text,
  onCite,
  citeIndex,
}: {
  text: string;
  onCite: (id: string) => void;
  citeIndex: CiteIndex;
}) {
  const prepared = linkifyCites(text.replace(/\n{3,}/g, "\n\n"), citeIndex);
  return (
    <div className="text-[14.5px] leading-relaxed text-[#1c1612] [&_p]:mb-2 [&_p]:last:mb-0 [&_p:empty]:hidden [&_li]:ml-4 [&_li]:list-disc">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ href, children }) => {
            if (href?.startsWith("#cite=")) {
              const id = decodeURIComponent(href.slice(6));
              return (
                <button
                  type="button"
                  onClick={() => onCite(id)}
                  className="mx-0.5 inline rounded bg-[#efe4cc] px-1.5 py-0.5 align-baseline text-[11px] text-[#9a7840] hover:bg-[#f0d48a]"
                  title={citeHover(id, citeIndex)}
                >
                  {children}
                </button>
              );
            }
            return (
              <a href={href} className="underline">
                {children}
              </a>
            );
          },
          strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
        }}
      >
        {prepared}
      </ReactMarkdown>
    </div>
  );
}
