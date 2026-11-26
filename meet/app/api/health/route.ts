import { readLiveKitServerConfig } from '@/lib/livekitServerConfig';

export const dynamic = 'force-dynamic';

/**
 * Report whether the interview room can sign LiveKit tokens, naming any missing
 * setting but never its value. The deploy workflow's live check reads this.
 */
export async function GET() {
  const settings = readLiveKitServerConfig();
  const body = settings.ok
    ? { ok: true, livekitConfigured: true, missing: [] as string[] }
    : { ok: true, livekitConfigured: false, missing: settings.missing };
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' },
  });
}
