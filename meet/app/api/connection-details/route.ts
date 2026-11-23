import { AccessToken } from "livekit-server-sdk";
import { missingConfigMessage, readLiveKitServerConfig } from "@/lib/livekitServerConfig";

export async function GET(req: Request) {
  try {
    const { searchParams } = new URL(req.url);
    const roomName = searchParams.get("roomName");
    const participantName = searchParams.get("participantName");

    if (!roomName || !participantName) {
      return new Response(
        JSON.stringify({ error: "Missing roomName or participantName" }),
        { status: 400, headers: { "Content-Type": "application/json" } }
      );
    }

    const settings = readLiveKitServerConfig();
    if (!settings.ok) {
      return new Response(
        JSON.stringify({ error: missingConfigMessage(settings.missing) }),
        { status: 500, headers: { "Content-Type": "application/json" } }
      );
    }
    const { url: livekitUrl, apiKey, apiSecret } = settings.config;

    const at = new AccessToken(apiKey, apiSecret, {
      identity: participantName,
    });
    at.addGrant({
      roomJoin: true,
      room: roomName,
    });
    const token = await at.toJwt();

    return new Response(JSON.stringify({
      serverUrl: livekitUrl,
      participantToken: token
    }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  } catch (err: any) {
    console.error("Error generating connection details:", err);
    return new Response(
      JSON.stringify({ error: err.message || "Internal Server Error" }),
      { status: 500, headers: { "Content-Type": "application/json" } }
    );
  }
}
