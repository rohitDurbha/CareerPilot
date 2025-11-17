import { AccessToken } from "livekit-server-sdk";

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

    const livekitUrl = process.env.NEXT_PUBLIC_LIVEKIT_URL;
    const apiKey = process.env.NEXT_PUBLIC_LIVEKIT_API_KEY;
    const apiSecret = process.env.NEXT_PUBLIC_LIVEKIT_API_SECRET;

    if (!livekitUrl || !apiKey || !apiSecret) {
      return new Response(
        JSON.stringify({
          error:
            "Missing environment configuration. Check your .env.local file for NEXT_PUBLIC_LIVEKIT_URL, API_KEY, and API_SECRET.",
        }),
        { status: 500, headers: { "Content-Type": "application/json" } }
      );
    }

    const at = new AccessToken(apiKey, apiSecret, {
      identity: participantName,
    });
    at.addGrant({
      roomJoin: true,
      room: roomName,
    });
    const token = await at.toJwt();

    // ✅ Use key names expected by frontend!
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
