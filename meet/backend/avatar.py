import os
import logging
from dotenv import load_dotenv
from livekit.agents import JobContext, AgentSession
from livekit.plugins import openai, simli

logging.basicConfig(level=logging.INFO)
load_dotenv()

async def entrypoint(ctx: JobContext):
    # Build a text + voice pipeline for your AI interview agent
    session = AgentSession(
        stt=openai.realtime.RealtimeModel(),             # or your STT choice
        llm=openai.realtime.RealtimeModel(voice="alloy"), # LLM + voice model
    )

    # Fetch keys from environment
    simli_api_key = os.getenv("SIMLI_API_KEY")
    simli_face_id = os.getenv("SIMLI_FACE_ID")

    # Create your Simli avatar configuration
    avatar = simli.AvatarSession(
        simli_config=simli.SimliConfig(
            api_key=simli_api_key,
            face_id=simli_face_id,
            avatar_participant_name="simli-avatar-agent"
        )
    )

    # Start avatar session (it syncs with agent’s speech in the room)
    await avatar.start(session, room=ctx.room)

    # Start the agent session in that room
    await session.start()
