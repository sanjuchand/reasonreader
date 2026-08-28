import { spawn } from "node:child_process";
import path from "node:path";

export function runIngest(copyId: string): Promise<void> {
  const root = path.join(process.cwd(), "..");
  return new Promise((resolve, reject) => {
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
