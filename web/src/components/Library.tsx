"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { BookOpen, LogIn, LogOut, Upload } from "lucide-react";
import { useAuth } from "@/components/AuthProvider";
import { DEMO_COPY_ID } from "@/lib/constants";

type CopyCard = {
  id: string;
  kind: string;
  title: string;
  author: string;
  status: string;
  error: string | null;
};

const DEMO_UNIT_COUNT = 132;

export function Library() {
  const { user, loading, logout } = useAuth();
  const router = useRouter();
  const [copies, setCopies] = useState<CopyCard[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [attested, setAttested] = useState(false);

  useEffect(() => {
    if (loading) return;
    void fetch("/api/copies")
      .then(async (res) => {
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Failed to load library");
        setCopies(data.copies || []);
      })
      .catch((err: Error) => setError(err.message));
  }, [loading]);

  async function onUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const fileInput = form.elements.namedItem("file") as HTMLInputElement;
    const file = fileInput.files?.[0];
    if (!file) return;
    if (!attested) {
      setError("Attest that you have the right to read this copy.");
      return;
    }
    setBusy(true);
    setError("");
    const body = new FormData();
    body.set("file", file);
    body.set("rightsAttested", "true");
    try {
      const res = await fetch("/api/copies", { method: "POST", body });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Upload failed");
      const id = data.copy?.id;
      if (id && data.copy?.status === "ready") router.push(`/read/${id}`);
      else {
        setCopies((prev) => {
          const next = prev.filter((c) => c.id !== data.copy?.id);
          return data.copy ? [...next, data.copy] : prev;
        });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setBusy(false);
      form.reset();
      setAttested(false);
    }
  }

  if (loading) {
    return <div className="h-screen bg-[#1c2d24]" />;
  }

  const demo = copies.find((c) => c.kind === "demo") || {
    id: DEMO_COPY_ID,
    kind: "demo",
    title: "The Wealth of Nations",
    author: "Adam Smith",
    status: "ready",
    error: null,
  };
  const mine = copies.filter((c) => c.kind === "private");
  const demoHref = `/read/${demo.id}`;

  return (
    <div className="min-h-screen bg-[#1c2d24] font-[family-name:var(--font-sans)] text-[#efe6d4]">
      <header className="mx-auto flex max-w-3xl items-center justify-between px-6 py-6">
        <div className="flex items-center gap-2">
          <BookOpen className="size-5 text-[#c4a15a]" />
          <div className="text-[15px] font-semibold tracking-wide">Ken</div>
        </div>
        {user ? (
          <button
            type="button"
            onClick={() => logout().then(() => router.replace("/"))}
            className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-[12px] text-[#cbbda4] hover:bg-white/10 hover:text-white"
          >
            <LogOut className="size-3.5" />
            Sign out
          </button>
        ) : (
          <button
            type="button"
            onClick={() => router.push("/login?next=/")}
            className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-[12px] text-[#cbbda4] hover:bg-white/10 hover:text-white"
          >
            <LogIn className="size-3.5" />
            Sign in
          </button>
        )}
      </header>

      <section className="mx-auto max-w-3xl px-6 pb-16 pt-6 sm:pt-14">
        <p className="text-[13px] tracking-[0.18em] text-[#c4a15a] uppercase">Ken</p>
        <h1 className="mt-4 max-w-2xl font-[family-name:var(--font-serif)] text-[34px] leading-[1.15] sm:text-[46px]">
          Summarization is the wrong shape for learning.
        </h1>
        <div className="mt-6 max-w-xl space-y-4 text-[16px] leading-relaxed text-[#cbbda4]">
          <p>
            Ask an AI about a book and it gives you a competent summary. You feel like you understood it. A week later,
            you cannot reconstruct the argument.
          </p>
          <p>
            Ken does the opposite: it teaches one unit at a time, tests you in your own words, and keeps the next unit
            locked until this one is internalized.
          </p>
        </div>
        <div className="mt-10 flex flex-col gap-3 sm:flex-row sm:items-center">
          <button
            type="button"
            onClick={() => router.push(demoHref)}
            className="rounded-md bg-[#c4a15a] px-5 py-2.5 text-[14px] font-medium text-[#1c2d24] hover:bg-[#d4b36c]"
          >
            Try the Adam Smith demo
          </button>
          {user ? (
            <a
              href="#bring-your-copy"
              className="rounded-md border border-white/15 px-5 py-2.5 text-center text-[14px] text-[#efe6d4] hover:border-[#c4a15a]/50"
            >
              Bring your own book
            </a>
          ) : (
            <button
              type="button"
              onClick={() => router.push("/login?next=/#bring-your-copy")}
              className="rounded-md border border-white/15 px-5 py-2.5 text-[14px] text-[#efe6d4] hover:border-[#c4a15a]/50"
            >
              Sign in to bring your own book
            </button>
          )}
        </div>
      </section>

      <section className="border-y border-white/10 bg-[#17241d]">
        <div className="mx-auto max-w-3xl px-6 py-16">
          <h2 className="font-[family-name:var(--font-serif)] text-[28px] leading-tight sm:text-[32px]">
            The constraint is the product.
          </h2>
          <p className="mt-4 max-w-xl text-[16px] leading-relaxed text-[#cbbda4]">
            Summaries optimize for coverage. Ken optimizes for internalization.
          </p>
          <p className="mt-4 max-w-xl text-[16px] leading-relaxed text-[#cbbda4]">
            You cannot skip ahead. You cannot collect a polished explanation and call it learning. You read, answer, get
            corrected, and move only when you can explain the argument yourself.
          </p>
        </div>
      </section>

      <section className="mx-auto max-w-3xl px-6 py-16">
        <div className="rounded-lg border border-white/10 bg-[#17241d] px-6 py-7">
          <div className="text-[11px] uppercase tracking-wide text-[#c4a15a]">Public demo</div>
          <h3 className="mt-2 font-[family-name:var(--font-serif)] text-[24px] leading-tight">
            Adam Smith’s <em>The Wealth of Nations</em>
          </h3>
          <p className="mt-3 text-[15px] leading-relaxed text-[#cbbda4]">
            {DEMO_UNIT_COUNT} units. The next one unlocks only when you earn it.
          </p>
          <button
            type="button"
            onClick={() => router.push(demoHref)}
            className="mt-6 rounded-md bg-[#c4a15a] px-5 py-2.5 text-[14px] font-medium text-[#1c2d24] hover:bg-[#d4b36c]"
          >
            Start the public demo
          </button>
        </div>

        {user ? (
          <form
            id="bring-your-copy"
            onSubmit={(event) => void onUpload(event)}
            className="mt-8 scroll-mt-8 rounded-lg border border-white/10 bg-[#17241d] px-6 py-7"
          >
            <div className="flex items-center gap-2 text-[15px] font-medium">
              <Upload className="size-4 text-[#c4a15a]" />
              Bring your own book
            </div>
            <p className="mt-2 text-[13px] text-[#cbbda4]">
              PDF or EPUB you have the right to read. Digital text only — scanned pages are not supported yet.
            </p>
            <input
              name="file"
              type="file"
              accept=".pdf,.epub,application/pdf,application/epub+zip"
              required
              className="mt-4 block w-full text-[13px] file:mr-3 file:rounded-md file:border-0 file:bg-[#c4a15a] file:px-3 file:py-1.5 file:text-[12px] file:font-medium file:text-[#1c2d24]"
            />
            <label className="mt-4 flex items-start gap-2 text-[13px] leading-relaxed text-[#cbbda4]">
              <input
                type="checkbox"
                checked={attested}
                onChange={(event) => setAttested(event.target.checked)}
                className="mt-1"
              />
              I have the right to read this copy. Ken will not share it or become a library for others.
            </label>
            <button
              type="submit"
              disabled={busy || !attested}
              className="mt-4 rounded-md bg-[#c4a15a] px-4 py-2 text-[13px] font-medium text-[#1c2d24] disabled:opacity-40"
            >
              {busy ? "Ingesting…" : "Tutor this copy"}
            </button>
          </form>
        ) : null}

        {mine.length > 0 && (
          <div className="mt-10">
            <h2 className="text-[13px] uppercase tracking-wide text-[#c4a15a]">Your copies</h2>
            <ul className="mt-3 space-y-2">
              {mine.map((copy) => (
                <li key={copy.id}>
                  <button
                    type="button"
                    disabled={copy.status !== "ready"}
                    onClick={() => router.push(`/read/${copy.id}`)}
                    className="w-full rounded-lg border border-white/10 bg-[#17241d] px-4 py-3 text-left disabled:opacity-60"
                  >
                    <div className="text-[15px]">{copy.title || "Untitled"}</div>
                    <div className="text-[12px] text-[#cbbda4]">
                      {copy.author}
                      {copy.author ? " · " : ""}
                      {copy.status}
                      {copy.error ? ` · ${copy.error}` : ""}
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}

        {error ? <p className="mt-4 text-[13px] text-[#e2b1a0]">{error}</p> : null}
      </section>
    </div>
  );
}
