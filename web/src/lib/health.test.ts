import { describe, expect, it } from "vitest";
import { checkHealth } from "./health";

describe("health contract", () => {
  it("is ok when the database answers", async () => {
    expect(await checkHealth(async () => true)).toEqual({ ok: true });
  });

  it("is not ok when the database does not answer", async () => {
    expect(await checkHealth(async () => false)).toEqual({ ok: false });
  });

  it("is not ok when the ping throws", async () => {
    expect(
      await checkHealth(async () => {
        throw new Error("unreachable");
      }),
    ).toEqual({ ok: false });
  });
});
