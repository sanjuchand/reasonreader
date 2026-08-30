import { drizzle } from "drizzle-orm/postgres-js";
import postgres from "postgres";
import * as schema from "./schema";

function createDb() {
  const url = process.env.DATABASE_URL;
  if (!url) {
    throw new Error("DATABASE_URL is not set");
  }
  return drizzle(postgres(url, { max: 4 }), { schema });
}

type Db = ReturnType<typeof createDb>;

let cached: Db | undefined;

export const db = new Proxy({} as Db, {
  get(_target, property, receiver) {
    cached ??= createDb();
    return Reflect.get(cached, property, receiver);
  },
});
