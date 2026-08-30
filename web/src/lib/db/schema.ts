import {
  boolean,
  doublePrecision,
  integer,
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

export const copies = pgTable("copies", {
  id: uuid("id").defaultRandom().primaryKey(),
  kind: text("kind").notNull(),
  ownerId: uuid("owner_id").references(() => users.id, { onDelete: "cascade" }),
  title: text("title").notNull().default(""),
  author: text("author").notNull().default(""),
  status: text("status").notNull().default("uploading"),
  flavor: text("flavor"),
  sourceContentType: text("source_content_type"),
  sourceFilename: text("source_filename"),
  rightsAttestedAt: timestamp("rights_attested_at", { withTimezone: true }),
  error: text("error"),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).notNull().defaultNow(),
});

export const userThreads = pgTable(
  "user_threads",
  {
    userId: uuid("user_id")
      .notNull()
      .references(() => users.id, { onDelete: "cascade" }),
    copyId: uuid("copy_id")
      .notNull()
      .references(() => copies.id, { onDelete: "cascade" }),
    langgraphThreadId: text("langgraph_thread_id").notNull(),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (table) => [primaryKey({ columns: [table.userId, table.copyId] })],
);

export const unitProgress = pgTable(
  "unit_progress",
  {
    userId: uuid("user_id")
      .notNull()
      .references(() => users.id, { onDelete: "cascade" }),
    copyId: uuid("copy_id")
      .notNull()
      .references(() => copies.id, { onDelete: "cascade" }),
    unitId: text("unit_id").notNull(),
    status: text("status").notNull().default("locked"),
    score: doublePrecision("score").notNull().default(0),
    unlocked: boolean("unlocked").notNull().default(false),
    concepts: jsonb("concepts").notNull().default([]),
    updatedAt: timestamp("updated_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (table) => [primaryKey({ columns: [table.userId, table.copyId, table.unitId] })],
);

export const tutorEvents = pgTable("tutor_events", {
  id: uuid("id").defaultRandom().primaryKey(),
  userId: uuid("user_id")
    .notNull()
    .references(() => users.id, { onDelete: "cascade" }),
  copyId: uuid("copy_id")
    .notNull()
    .references(() => copies.id, { onDelete: "cascade" }),
  threadId: text("thread_id"),
  unitId: text("unit_id"),
  kind: text("kind").notNull(),
  concept: text("concept"),
  score: text("score"),
  recitation: boolean("recitation"),
  overall: doublePrecision("overall"),
  attempt: integer("attempt"),
  answerChars: integer("answer_chars"),
  answerClip: text("answer_clip"),
  payload: jsonb("payload").notNull().default({}),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
});
