export function googleClientId() {
  return process.env.GOOGLE_CLIENT_ID || process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || "";
}

export function secretKeyValue() {
  return process.env.SECRET_KEY || "";
}

export const SESSION_COOKIE_NAME = process.env.SESSION_COOKIE_NAME || "won_session";
export const SESSION_MAX_AGE_SECONDS = Number(process.env.SESSION_MAX_AGE_SECONDS || 604800);
export function langgraphUrl() {
  return process.env.LANGGRAPH_URL || "http://127.0.0.1:2024";
}

export function assistantId() {
  return process.env.ASSISTANT_ID || process.env.NEXT_PUBLIC_ASSISTANT_ID || "agent";
}
export function isDev() {
  return process.env.NODE_ENV !== "production";
}

