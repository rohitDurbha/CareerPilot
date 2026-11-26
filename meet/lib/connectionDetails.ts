import { ConnectionDetails } from './types';

/**
 * Turn the /api/connection-details answer into connection details, or throw an
 * Error with a message a person can act on.
 *
 * Without this check an error answer (for example when the host has no LiveKit
 * keys yet) was passed straight to the room, which then tried to connect to an
 * undefined server and crashed.
 */
export function parseConnectionDetails(status: number, data: unknown): ConnectionDetails {
  const body = (data && typeof data === 'object' ? data : {}) as Record<string, unknown>;
  const serverUrl = typeof body.serverUrl === 'string' ? body.serverUrl : '';
  const token = typeof body.participantToken === 'string' ? body.participantToken : '';

  if (status >= 200 && status < 300 && serverUrl && token) {
    return body as unknown as ConnectionDetails;
  }
  const reason =
    typeof body.error === 'string' && body.error.trim()
      ? body.error.trim()
      : `The interview room server answered ${status} without connection details.`;
  throw new Error(reason);
}
