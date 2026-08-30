export type Health = { ok: boolean };

export async function checkHealth(ping: () => Promise<boolean>): Promise<Health> {
  try {
    return { ok: Boolean(await ping()) };
  } catch {
    return { ok: false };
  }
}

export async function pingDatabase(url: string | undefined): Promise<boolean> {
  if (!url) return false;
  const postgres = (await import("postgres")).default;
  const sql = postgres(url, { max: 1, connect_timeout: 3 });
  try {
    await sql`select 1`;
    return true;
  } finally {
    await sql.end({ timeout: 1 });
  }
}
