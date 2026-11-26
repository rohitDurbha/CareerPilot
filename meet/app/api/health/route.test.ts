import { afterEach, describe, expect, it, vi } from 'vitest';
import { GET } from './route';

afterEach(() => {
  vi.unstubAllEnvs();
});

describe('GET /api/health', () => {
  it('names the missing LiveKit settings when none are set', async () => {
    vi.stubEnv('LIVEKIT_URL', '');
    vi.stubEnv('NEXT_PUBLIC_LIVEKIT_URL', '');
    vi.stubEnv('LIVEKIT_API_KEY', '');
    vi.stubEnv('LIVEKIT_API_SECRET', '');
    const response = await GET();
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({
      ok: true,
      livekitConfigured: false,
      missing: ['LIVEKIT_URL', 'LIVEKIT_API_KEY', 'LIVEKIT_API_SECRET'],
    });
  });

  it('reports a configured room without echoing the secret', async () => {
    vi.stubEnv('LIVEKIT_URL', 'wss://demo.livekit.cloud');
    vi.stubEnv('LIVEKIT_API_KEY', 'devkey');
    vi.stubEnv('LIVEKIT_API_SECRET', 'a-test-secret-value');
    const response = await GET();
    const text = await response.text();
    expect(JSON.parse(text)).toEqual({ ok: true, livekitConfigured: true, missing: [] });
    expect(text).not.toContain('a-test-secret-value');
    expect(text).not.toContain('devkey');
  });
});
