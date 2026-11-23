/**
 * LiveKit settings that must only ever be read on the server.
 *
 * Anything prefixed with NEXT_PUBLIC_ is inlined into the browser bundle by
 * Next.js, so the API key and secret are read from plain LIVEKIT_* variables.
 * The old public-prefixed key and secret names are deliberately ignored so a
 * stale .env.local cannot leak the secret again.
 */
export type LiveKitServerConfig = {
  url: string;
  apiKey: string;
  apiSecret: string;
};

export type LiveKitConfigResult =
  | { ok: true; config: LiveKitServerConfig }
  | { ok: false; missing: string[] };

type Env = Record<string, string | undefined>;

export function readLiveKitServerConfig(env: Env = process.env): LiveKitConfigResult {
  // The server URL is not secret, so the old public name still works as a fallback.
  const url = (env.LIVEKIT_URL || env.NEXT_PUBLIC_LIVEKIT_URL || '').trim();
  const apiKey = (env.LIVEKIT_API_KEY || '').trim();
  const apiSecret = (env.LIVEKIT_API_SECRET || '').trim();

  const missing: string[] = [];
  if (!url) missing.push('LIVEKIT_URL');
  if (!apiKey) missing.push('LIVEKIT_API_KEY');
  if (!apiSecret) missing.push('LIVEKIT_API_SECRET');

  if (missing.length > 0) {
    return { ok: false, missing };
  }
  return { ok: true, config: { url, apiKey, apiSecret } };
}

export function missingConfigMessage(missing: string[]): string {
  return `Missing LiveKit server settings ${missing.join(', ')}. Set them in meet/.env.local or on your host.`;
}
