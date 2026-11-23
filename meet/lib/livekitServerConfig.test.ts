import { describe, expect, it } from 'vitest';
import { missingConfigMessage, readLiveKitServerConfig } from './livekitServerConfig';

describe('readLiveKitServerConfig', () => {
  it('reads the url, key and secret from server-only variables', () => {
    const result = readLiveKitServerConfig({
      LIVEKIT_URL: 'wss://demo.livekit.cloud',
      LIVEKIT_API_KEY: 'key',
      LIVEKIT_API_SECRET: 'secret',
    });
    expect(result).toEqual({
      ok: true,
      config: { url: 'wss://demo.livekit.cloud', apiKey: 'key', apiSecret: 'secret' },
    });
  });

  it('ignores the old public key and secret names', () => {
    const result = readLiveKitServerConfig({
      LIVEKIT_URL: 'wss://demo.livekit.cloud',
      NEXT_PUBLIC_LIVEKIT_API_KEY: 'key',
      NEXT_PUBLIC_LIVEKIT_API_SECRET: 'secret',
    });
    expect(result).toEqual({ ok: false, missing: ['LIVEKIT_API_KEY', 'LIVEKIT_API_SECRET'] });
  });

  it('still accepts the public url name because the url is not secret', () => {
    const result = readLiveKitServerConfig({
      NEXT_PUBLIC_LIVEKIT_URL: 'wss://demo.livekit.cloud',
      LIVEKIT_API_KEY: 'key',
      LIVEKIT_API_SECRET: 'secret',
    });
    expect(result.ok).toBe(true);
  });

  it('treats blank values as missing and names every missing setting', () => {
    const result = readLiveKitServerConfig({ LIVEKIT_URL: '  ', LIVEKIT_API_KEY: '' });
    expect(result).toEqual({
      ok: false,
      missing: ['LIVEKIT_URL', 'LIVEKIT_API_KEY', 'LIVEKIT_API_SECRET'],
    });
    expect(missingConfigMessage(['LIVEKIT_URL'])).toContain('LIVEKIT_URL');
  });
});
