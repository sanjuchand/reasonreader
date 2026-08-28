import { SignJWT, jwtVerify } from "jose";
import { isDev, secretKeyValue, SESSION_COOKIE_NAME, SESSION_MAX_AGE_SECONDS } from "./config";

export type SessionPayload = {
  sub: string;
};

function secretKey() {
  const key = secretKeyValue();
  if (!key) {
    throw new Error("SECRET_KEY is not configured");
  }
  return new TextEncoder().encode(key);
}

export async function createSessionToken(userId: string): Promise<string> {
  return new SignJWT({ sub: userId })
    .setProtectedHeader({ alg: "HS256" })
    .setExpirationTime(`${SESSION_MAX_AGE_SECONDS}s`)
    .sign(secretKey());
}

export async function decodeSessionToken(token: string): Promise<SessionPayload | null> {
  try {
    const { payload } = await jwtVerify(token, secretKey(), { algorithms: ["HS256"] });
    if (typeof payload.sub !== "string") return null;
    return { sub: payload.sub };
  } catch {
    return null;
  }
}

export function sessionCookieOptions() {
  return {
    httpOnly: true,
    secure: !isDev(),
    sameSite: "lax" as const,
    path: "/",
    maxAge: SESSION_MAX_AGE_SECONDS,
  };
}

export { SESSION_COOKIE_NAME };
