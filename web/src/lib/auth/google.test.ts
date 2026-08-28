import { describe, expect, it } from "vitest";
import { GoogleTokenError, verifyGoogleIdToken } from "./google";

describe("google id token", () => {
  it("rejects when GOOGLE_CLIENT_ID is not configured", async () => {
    const previous = process.env.GOOGLE_CLIENT_ID;
    const previousPublic = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;
    delete process.env.GOOGLE_CLIENT_ID;
    delete process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;
    try {
      await expect(verifyGoogleIdToken("a-credential")).rejects.toBeInstanceOf(GoogleTokenError);
    } finally {
      if (previous) process.env.GOOGLE_CLIENT_ID = previous;
      if (previousPublic) process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID = previousPublic;
    }
  });
});
