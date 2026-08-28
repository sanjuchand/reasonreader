"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { BookOpen, LogOut, Upload } from "lucide-react";
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

export function Library() {
  const { user, loading, logout } = useAuth();
  const router = useRouter();
  const [copies, setCopies] = useState<CopyCard[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [attested, setAttested] = useState(false);

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);

  useEffect(() => {
    if (!user) return;
    void fetch("/api/copies")
      .then(async (res) => {
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Failed to load library");
        setCopies(data.copies || []);
      })
      .catch((err: Error) => setError(err.message));
  }, [user]);

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

  if (loading || !user) {
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

  return (
    <div className="min-h-screen bg-[#1c2d24] px-6 py-8 font-[family-name:var(--font-sans)] text-[#efe6d4]">
      <header className="mx-auto flex max-w-3xl items-center justify-between">
        <div className="flex items-center gap-2">
          <BookOpen className="size-5 text-[#c4a15a]" />
          <div>
            <div className="text-[15px] font-semibold tracking-wide">Ken</div>
            <div className="text-[12px] text-[#cbbda4]">Your copy. Your tutor. Not a library.</div>
          </div>
        </div>
        <button
          type="button"
          onClick={() => logout().then(() => router.replace("/login"))}
          className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-[12px] text-[#cbbda4] hover:bg-white/10 hover:text-white"
        >
          <LogOut className="size-3.5" />
          Sign out
        </button>
      </header>

      <main className="mx-auto mt-10 max-w-3xl">
        <p className="text-[13px] tracking-[0.12em] text-[#c4a15a] uppercase">Bring a book you have the right to read</p>
        <h1 className="mt-2 font-[family-name:var(--font-serif)] text-[32px] leading-tight">
          We tutor you through your copy.
        </h1>
        <p className="mt-3 max-w-xl text-[15px] leading-relaxed text-[#cbbda4]">
          Smith is here so you can try the loop without uploading. Your files stay private to this account.
        </p>

        <button
          type="button"
          onClick={() => router.push(`/read/${demo.id}`)}
          className="mt-8 w-full rounded-lg border border-white/10 bg-[#17241d] px-5 py-4 text-left hover:border-[#c4a15a]/50"
        >
          <div className="text-[11px] uppercase tracking-wide text-[#c4a15a]">Public demo</div>
          <div className="mt-1 text-[17px] font-medium">{demo.title || "The Wealth of Nations"}</div>
          <div className="text-[13px] text-[#cbbda4]">{demo.author || "Adam Smith"} · no upload</div>
        </button>

        <form onSubmit={(event) => void onUpload(event)} className="mt-8 rounded-lg border border-white/10 bg-[#17241d] px-5 py-5">
          <div className="flex items-center gap-2 text-[15px] font-medium">
            <Upload className="size-4 text-[#c4a15a]" />
            Bring your copy
          </div>
          <p className="mt-2 text-[13px] text-[#cbbda4]">PDF or EPUB. Digital text only — scanned pages are not supported yet.</p>
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
      </main>
    </div>
  );
}
