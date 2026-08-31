import { describe, expect, it, vi } from "vitest";
import { currentChapter, restoreMissingThread, threadValues } from "./langgraph-thread";

describe("currentChapter", () => {
  it("prefers the unit already in play", () => {
    expect(
      currentChapter(
        {
          a: { unlocked: true, status: "mastered" },
          b: { unlocked: true, status: "in_progress" },
        },
        "a",
      ),
    ).toBe("b");
  });

  it("falls back to the first unit", () => {
    expect(currentChapter({}, "u0000")).toBe("u0000");
  });
});

describe("threadValues", () => {
  it("unlocks the first unit without mutating the input map", () => {
    const mastery = {};
    const values = threadValues("copy-1", "user-1", mastery, "chap01");
    expect(mastery).toEqual({});
    expect(values.current_chapter_id).toBe("chap01");
    expect(values.mastery.chap01).toEqual({ unlocked: true, status: "in_progress", score: 0 });
    expect(values.copy_id).toBe("copy-1");
    expect(values.user_id).toBe("user-1");
  });
});

describe("restoreMissingThread", () => {
  it("recreates a stored thread that the graph no longer has", async () => {
    const restore = vi.fn(async () => undefined);
    const kept = await restoreMissingThread(
      "thread-old",
      async () => "missing",
      restore,
    );
    expect(kept).toBe("thread-old");
    expect(restore).toHaveBeenCalledWith("thread-old");
  });

  it("leaves a live thread alone", async () => {
    const restore = vi.fn(async () => undefined);
    await restoreMissingThread("thread-live", async () => "ok", restore);
    expect(restore).not.toHaveBeenCalled();
  });

  it("does not invent a thread when the graph is unreachable", async () => {
    const restore = vi.fn(async () => undefined);
    const kept = await restoreMissingThread("thread-old", async () => "error", restore);
    expect(kept).toBe("thread-old");
    expect(restore).not.toHaveBeenCalled();
  });

  it("returns null when nothing is stored", async () => {
    const restore = vi.fn(async () => undefined);
    expect(await restoreMissingThread(null, async () => "missing", restore)).toBeNull();
    expect(restore).not.toHaveBeenCalled();
  });
});
