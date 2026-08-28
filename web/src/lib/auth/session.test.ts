import { afterEach, describe, expect, it, vi } from "vitest";
import { createSessionToken, decodeSessionToken, sessionCookieOptions } from "./session";

describe("session cookie", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("round-trips a user id", async () => {
    vi.stubEnv("SECRET_KEY", "test-secret-key-for-jwt");
    const token = await createSessionToken("11111111-1111-1111-1111-111111111111");
    const payload = await decodeSessionToken(token);
    expect(payload?.sub).toBe("11111111-1111-1111-1111-111111111111");
  });

  it("the session cookie is locked down", () => {
    vi.stubEnv("NODE_ENV", "production");
    const opts = sessionCookieOptions();
    expect(opts.httpOnly).toBe(true);
    expect(opts.secure).toBe(true);
    expect(opts.sameSite).toBe("lax");
    expect(opts.path).toBe("/");
  });

  it("rejects a token that will not validate", async () => {
    vi.stubEnv("SECRET_KEY", "test-secret-key-for-jwt");
    expect(await decodeSessionToken("not-a-jwt")).toBeNull();
  });
});
