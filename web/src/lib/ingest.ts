import { spawn } from "node:child_process";
import path from "node:path";

function ingestUrl() {
  return (process.env.INGEST_URL || "").replace(/\/$/, "");
}

function ingestToken() {
  return process.env.INGEST_TOKEN || process.env.SECRET_KEY || "";
}

export async function runIngest(copyId: string): Promise<void> {
  const base = ingestUrl();
  if (base) {
    const token = ingestToken();
    if (!token) throw new Error("INGEST_TOKEN or SECRET_KEY is required when INGEST_URL is set");
    const response = await fetch(`${base}/ingest`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ copyId }),
      signal: AbortSignal.timeout(290_000),
    });
    const data = (await response.json().catch(() => ({}))) as { detail?: string };
    if (!response.ok) {
      throw new Error(data.detail || `Ingest failed (${response.status})`);
    }
    return;
  }

  const root = path.join(process.cwd(), "..");
  await new Promise<void>((resolve, reject) => {
    const child = spawn("uv", ["run", "python", "-m", "ingest", "--copy-id", copyId], {
      cwd: root,
      env: process.env,
    });
    let stderr = "";
    child.stderr.on("data", (chunk) => {
      stderr += chunk.toString();
    });
    child.on("error", reject);
    child.on("close", (code) => {
      if (code === 0) resolve();
      else reject(new Error(stderr.trim() || `ingest exited ${code}`));
    });
  });
}
