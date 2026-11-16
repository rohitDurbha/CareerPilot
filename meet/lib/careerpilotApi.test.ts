import { describe, it, expect } from 'vitest';
import { careerpilotApiUrl, DEFAULT_CAREERPILOT_API_URL } from './careerpilotApi';

describe('careerpilotApiUrl', () => {
  it('falls back to the local Flask port when no address is set', () => {
    expect(careerpilotApiUrl('/cancel_file1', undefined)).toBe(
      `${DEFAULT_CAREERPILOT_API_URL}/cancel_file1`,
    );
  });

  it('treats a blank setting the same as a missing one', () => {
    expect(careerpilotApiUrl('/cancel_file1', '   ')).toBe('http://localhost:5001/cancel_file1');
  });

  it('joins a configured address and path with exactly one slash', () => {
    expect(careerpilotApiUrl('/cancel_file1', 'https://api.example.test/')).toBe(
      'https://api.example.test/cancel_file1',
    );
    expect(careerpilotApiUrl('cancel_file1', 'https://api.example.test')).toBe(
      'https://api.example.test/cancel_file1',
    );
  });

  it('returns the bare address for an empty path', () => {
    expect(careerpilotApiUrl('', 'https://api.example.test/')).toBe('https://api.example.test');
  });
});
