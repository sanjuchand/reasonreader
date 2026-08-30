export function canReadCopy(
  copy: { kind: string; ownerId: string | null },
  userId: string | null,
): boolean {
  if (copy.kind === "demo") return true;
  return Boolean(userId && copy.ownerId === userId);
}

export function safeNextPath(raw: string | null | undefined): string {
  if (!raw || !raw.startsWith("/") || raw.startsWith("//")) return "/";
  return raw;
}
