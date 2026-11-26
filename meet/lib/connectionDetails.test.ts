import { describe, expect, it } from 'vitest';
import { parseConnectionDetails } from './connectionDetails';

describe('parseConnectionDetails', () => {
  it('returns the details when the server signed a token', () => {
    const data = { serverUrl: 'wss://demo.livekit.cloud', participantToken: 'a.b.c' };
    expect(parseConnectionDetails(200, data)).toEqual(data);
  });

  it('throws the server error message when LiveKit is not configured', () => {
    const data = { error: 'Missing LiveKit server settings LIVEKIT_URL.' };
    expect(() => parseConnectionDetails(500, data)).toThrow('Missing LiveKit server settings');
  });

  it('throws when a success answer has no token', () => {
    expect(() => parseConnectionDetails(200, { serverUrl: 'wss://x' })).toThrow('answered 200');
  });

  it('throws on an answer that is not an object', () => {
    expect(() => parseConnectionDetails(502, null)).toThrow('answered 502');
  });
});
