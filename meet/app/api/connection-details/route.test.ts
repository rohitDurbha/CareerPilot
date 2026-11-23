import { afterEach, describe, expect, it, vi } from 'vitest';
import { GET } from './route';

const url = 'http://localhost/api/connection-details?roomName=interview&participantName=rohit';

afterEach(() => {
  vi.unstubAllEnvs();
});

function stubLiveKit(values: Record<string, string>) {
  for (const name of [
    'LIVEKIT_URL',
    'LIVEKIT_API_KEY',
    'LIVEKIT_API_SECRET',
    'NEXT_PUBLIC_LIVEKIT_URL',
    'NEXT_PUBLIC_LIVEKIT_API_KEY',
    'NEXT_PUBLIC_LIVEKIT_API_SECRET',
  ]) {
    vi.stubEnv(name, values[name] ?? '');
  }
}

describe('GET /api/connection-details', () => {
  it('returns a signed token when the server-only settings are present', async () => {
    stubLiveKit({
      LIVEKIT_URL: 'wss://demo.livekit.cloud',
      LIVEKIT_API_KEY: 'devkey',
      LIVEKIT_API_SECRET: 'a-test-secret-that-is-long-enough-for-hs256',
    });
    const response = await GET(new Request(url));
    expect(response.status).toBe(200);
    const body = await response.json();
    expect(body.serverUrl).toBe('wss://demo.livekit.cloud');
    expect(body.participantToken.split('.')).toHaveLength(3);
    expect(JSON.stringify(body)).not.toContain('a-test-secret');
  });

  it('refuses to sign with the old public key and secret', async () => {
    stubLiveKit({
      LIVEKIT_URL: 'wss://demo.livekit.cloud',
      NEXT_PUBLIC_LIVEKIT_API_KEY: 'devkey',
      NEXT_PUBLIC_LIVEKIT_API_SECRET: 'a-test-secret-that-is-long-enough-for-hs256',
    });
    const response = await GET(new Request(url));
    expect(response.status).toBe(500);
    const body = await response.json();
    expect(body.error).toContain('LIVEKIT_API_KEY');
    expect(body.error).toContain('LIVEKIT_API_SECRET');
  });

  it('still rejects requests without a room or participant name', async () => {
    const response = await GET(new Request('http://localhost/api/connection-details'));
    expect(response.status).toBe(400);
  });
});
