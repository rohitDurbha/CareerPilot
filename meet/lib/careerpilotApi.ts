/** Where the interview room reaches the CareerPilot Flask backend. */
export const DEFAULT_CAREERPILOT_API_URL = 'http://localhost:5001';

/**
 * Build a backend address from NEXT_PUBLIC_CAREERPILOT_API_URL, falling back to
 * the local Flask port so `npm run dev` keeps working without any setup.
 */
export function careerpilotApiUrl(
  path: string,
  base: string | undefined = process.env.NEXT_PUBLIC_CAREERPILOT_API_URL,
): string {
  const root = (base?.trim() || DEFAULT_CAREERPILOT_API_URL).replace(/\/+$/, '');
  const cleanPath = path.replace(/^\/+/, '');
  return cleanPath ? `${root}/${cleanPath}` : root;
}
