"""LiveKit interviewer agent for CareerPilot mock interviews.

Run with `python interviewer.py connect --room <room>`.

Everything runs on the Groq free tier with one GROQ_API_KEY. Whisper turns the
candidate's speech into text, GPT-OSS 20B writes the interviewer's replies and
Orpheus speaks them. groq_budget.py gives each interview a fixed share of the
daily allowance, and the interviewer closes politely before that share runs
out. The usage is logged when the interview ends.
"""

import asyncio
import logging
import os
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
from livekit.agents import tokenize, tts
from livekit.agents.voice import Agent, AgentSession
from livekit.plugins import groq, silero

from groq_budget import (
    LLM_MAX_COMPLETION_TOKENS,
    LLM_MODEL,
    STT_MODEL,
    TTS_CHAR_LIMIT,
    TTS_MODEL,
    TTS_VOICE,
    InterviewBudget,
    RateWindow,
    split_for_tts,
)


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

WRAP_UP_INSTRUCTIONS = (
    "Time is up. Thank the candidate warmly and close the interview in one short sentence."
)


def build_models():
    """The Groq speech, language and voice models, sized for the free tier."""
    return {
        "stt": groq.STT(model=STT_MODEL, language="en"),
        "llm": groq.LLM(
            model=LLM_MODEL,
            temperature=0.6,
            max_completion_tokens=LLM_MAX_COMPLETION_TOKENS,
            reasoning_effort="low",
        ),
        # Orpheus does not stream. The adapter sends each chunk from tts_node
        # whole, because no chunk reaches the minimum sentence length.
        "tts": tts.StreamAdapter(
            tts=groq.TTS(model=TTS_MODEL, voice=TTS_VOICE),
            sentence_tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=TTS_CHAR_LIMIT + 1),
        ),
    }


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
    def __init__(self, chat_ctx: ChatContext, tts_window: RateWindow):
        super().__init__(
            chat_ctx=chat_ctx,
            instructions=(
                "You are a professional AI interviewer conducting a job interview. "
                "Start with a greeting, then ask 'Their name, Tell me about yourself'. "
                "Ask one question about the resume and one behavioural question but make sure to ask one question at a time, following up when needed. "
                "End politely by asking for the candidate’s questions or any related concerns they might have. "
                "Your replies are spoken aloud, so keep each one to one or two short sentences "
                "with no lists, markdown or emoji."
            ),
            **build_models(),
            vad=silero.VAD.load(),
        )
        self.transcript = []  # running transcript in memory
        self.my_ctx = chat_ctx
        self.tts_window = tts_window

    # ----------- SPEECH NODE -----------
    async def tts_node(self, text: AsyncIterable[str], model_settings: ModelSettings):
        """Speak each reply in as few Orpheus requests as possible, paced per minute."""
        reply = "".join([part async for part in text])
        for chunk in split_for_tts(reply):
            wait = self.tts_window.delay()
            if wait > 0:
                logger.info("Waiting %.1fs to stay under the Orpheus per minute limit", wait)
                await asyncio.sleep(wait)
            self.tts_window.mark()

            async def one_chunk(value=chunk):
                yield value

            async for frame in Agent.default.tts_node(self, one_chunk(), model_settings):
                yield frame


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
    # One log file per interview, overwritten each run.
    open(LOG_FILE, "w", encoding="utf-8").close()
    budget = InterviewBudget.from_env(os.environ)
    logger.info("Interview budget: %s", budget.caps)

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

    closing = {"started": False}

    async def close_interview(reason):
        logger.info("Closing the interview because the %s budget is nearly used", reason)
        try:
            await session.generate_reply(instructions=WRAP_UP_INSTRUCTIONS)
        finally:
            session.shutdown()

    @session.on("metrics_collected")
    def on_metrics(event):
        budget.record(event.metrics)
        if budget.exhausted_reason() and closing["started"]:
            # The closing line itself ran over, so stop without another request.
            session.shutdown()
            return
        reason = budget.wrap_up_reason()
        if reason and not closing["started"]:
            closing["started"] = True
            asyncio.create_task(close_interview(reason))

    @session.on("close")
    def on_close(_event):
        logger.info(budget.summary())

    await session.start(
        agent=AIInterviewerAgent(
            chat_ctx=context,
            tts_window=RateWindow(budget.caps.tts_requests_per_minute),
        ),
        room=ctx.room,
        room_output_options=RoomOutputOptions(sync_transcription=False),
    )


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
