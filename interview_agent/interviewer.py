"""LiveKit interviewer agent for CareerPilot mock interviews.

Run with `python interviewer.py connect --room <room>`.
"""

import os
import logging
import datetime
import uuid
from pathlib import Path
from dataclasses import dataclass
from dotenv import load_dotenv
from typing import AsyncIterable, AsyncGenerator

from livekit.agents import (
    JobContext,
    WorkerOptions,
    cli,
    ChatContext,
    RoomOutputOptions,
    ModelSettings,
)
from livekit.agents.voice import Agent, AgentSession
from livekit.plugins import silero


# ======================
# ENVIRONMENT SETUP
# ======================
load_dotenv(dotenv_path=Path(__file__).parent / ".env")

logger = logging.getLogger("ai-interviewer")
logger.setLevel(logging.INFO)


# ======================
# FILE SETUP (single file, overwritten each run)
# ======================
LOG_FILE = Path(__file__).parent / "ai_interview_log.txt"

# Clear or create the file at startup
open(LOG_FILE, "w", encoding="utf-8").close()


# ======================
# DATA MODEL
# ======================
@dataclass
class InterviewData:
    interview_id: str | None = None


# ======================
# AI INTERVIEWER AGENT CLASS
# ======================
class AIInterviewerAgent(Agent):
    def __init__(self, chat_ctx: ChatContext):
        super().__init__(
            chat_ctx=chat_ctx,
            instructions=(
                "You are a professional AI interviewer conducting a job interview. "
                "Start with a greeting, then ask 'Their name, Tell me about yourself'. "
                "Ask one question about the resume and one behavioural question but make sure to ask one question at a time, following up when needed. "
                "End politely by asking for the candidate’s questions or any related concerns they might have."
            ),
            stt="assemblyai/universal-streaming",   # Speech-to-text
            llm="openai/gpt-4.1-mini",              # LLM for conversation
            tts="cartesia/sonic-2:6f84f4b8-58a2-430c-8c79-688dad597532",  # Text-to-speech
            vad=silero.VAD.load(),                  # Voice activity detection
        )
        self.transcript = []  # running transcript in memory
        self.my_ctx = chat_ctx


    # ----------- TRANSCRIPTION NODE -----------
    async def transcription_node(
        self, text: AsyncIterable[str], model_settings: ModelSettings
    ) -> AsyncGenerator[str, None]:
        """Capture user and AI transcripts continuously and save to file."""
        async for segment in text:
            cleaned = segment.strip()
            if cleaned:
                self.transcript.append(cleaned)
                ts = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                with open(LOG_FILE, "a", encoding="utf-8") as f:
                    f.write(f"[{ts}] AI/User transcribed: {cleaned}\n")
                logger.info(f"📝 Transcribed: {cleaned}")
            yield cleaned


    # ----------- SESSION LIFECYCLE -----------
    async def on_enter(self):
        logger.info("✅ AI interviewer joined; conversation started.")
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write("=== Interview Session Started ===\n")
        await self.session.generate_reply()

    async def on_exit(self):
        transcript_text = "\n".join(self.transcript)
        print("\n===== FINAL INTERVIEW TRANSCRIPT =====\n", transcript_text)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write("=== Session Ended ===\n")
            f.write(transcript_text + "\n")
        logger.info(f"✅ Full transcript saved to {LOG_FILE.absolute()}")


# ======================
# MAIN ENTRYPOINT
# ======================
async def entrypoint(ctx: JobContext):
    meta = ctx.job.metadata or {}
    interview_id = meta.get("interview_id") or str(uuid.uuid4())

    context = ChatContext()
    context.add_message(
        role="system",
        content=(
            "You are an AI interviewer. Engage thoughtfully, record all user and AI speech "
            "to a single file (overwrite each run)."
        ),
    )

    session = AgentSession(
        userdata=InterviewData(interview_id=interview_id),
        use_tts_aligned_transcript=True,
    )

    await session.start(
        agent=AIInterviewerAgent(chat_ctx=context),
        room=ctx.room,
        room_output_options=RoomOutputOptions(sync_transcription=False),
    )


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
