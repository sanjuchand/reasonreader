import {
  boolean,
  doublePrecision,
  jsonb,
  pgTable,
  primaryKey,
  text,
  timestamp,
  uuid,
} from "drizzle-orm/pg-core";

export const users = pgTable("users", {
  id: uuid("id").defaultRandom().primaryKey(),
  googleSub: text("google_sub").notNull().unique(),
  email: text("email").notNull(),
  name: text("name").notNull().default(""),
  avatarUrl: text("avatar_url").notNull().default(""),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
});

export const userThreads = pgTable("user_threads", {
  userId: uuid("user_id")
    .primaryKey()
    .references(() => users.id, { onDelete: "cascade" }),
  langgraphThreadId: text("langgraph_thread_id").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
});

export const unitProgress = pgTable(
  "unit_progress",
  {
    userId: uuid("user_id")
      .notNull()
      .references(() => users.id, { onDelete: "cascade" }),
    unitId: text("unit_id").notNull(),
    status: text("status").notNull().default("locked"),
    score: doublePrecision("score").notNull().default(0),
    unlocked: boolean("unlocked").notNull().default(false),
    concepts: jsonb("concepts").notNull().default([]),
    updatedAt: timestamp("updated_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (table) => [primaryKey({ columns: [table.userId, table.unitId] })],
);
