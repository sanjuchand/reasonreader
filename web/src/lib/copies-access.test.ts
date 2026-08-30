import { describe, expect, it } from "vitest";
import { canReadCopy, safeNextPath } from "./copies-access";

describe("canReadCopy", () => {
  it("lets anyone read the public demo", () => {
    expect(canReadCopy({ kind: "demo", ownerId: null }, null)).toBe(true);
    expect(canReadCopy({ kind: "demo", ownerId: null }, "user-1")).toBe(true);
  });

  it("keeps private copies behind the owner", () => {
    expect(canReadCopy({ kind: "private", ownerId: "user-1" }, null)).toBe(false);
    expect(canReadCopy({ kind: "private", ownerId: "user-1" }, "user-2")).toBe(false);
    expect(canReadCopy({ kind: "private", ownerId: "user-1" }, "user-1")).toBe(true);
  });
});

describe("safeNextPath", () => {
  it("accepts in-app paths only", () => {
    expect(safeNextPath("/read/demo")).toBe("/read/demo");
    expect(safeNextPath(null)).toBe("/");
    expect(safeNextPath("//evil.example")).toBe("/");
    expect(safeNextPath("https://evil.example")).toBe("/");
  });
});
