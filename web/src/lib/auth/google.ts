import { googleClientId } from "./config";

export class GoogleTokenError extends Error {}

export type GoogleClaims = {
  sub: string;
  email?: string;
  name?: string;
  picture?: string;
  aud?: string;
};

export async function verifyGoogleIdToken(credential: string): Promise<GoogleClaims> {
  const clientId = googleClientId();
  if (!clientId) {
    throw new GoogleTokenError("GOOGLE_CLIENT_ID is not configured");
  }
  const { OAuth2Client } = await import("google-auth-library");
  try {
    const client = new OAuth2Client(clientId);
    const ticket = await client.verifyIdToken({
      idToken: credential,
      audience: clientId,
    });
    const payload = ticket.getPayload();
    if (!payload?.sub) {
      throw new GoogleTokenError("Invalid Google ID token");
    }
    if (payload.aud !== clientId) {
      throw new GoogleTokenError("Token audience mismatch");
    }
    return {
      sub: payload.sub,
      email: payload.email,
      name: payload.name,
      picture: payload.picture,
      aud: typeof payload.aud === "string" ? payload.aud : payload.aud?.[0],
    };
  } catch (err) {
    if (err instanceof GoogleTokenError) throw err;
    throw new GoogleTokenError("Invalid Google ID token");
  }
}
