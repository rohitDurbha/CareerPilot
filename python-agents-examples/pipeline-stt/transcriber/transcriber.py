# """
# ---
# title: Transcriber
# category: pipeline-stt
# tags: [pipeline-stt, openai, deepgram]
# difficulty: beginner
# description: Shows how to transcribe user speech to text without TTS or an LLM.
# demonstrates:
#   - Saving transcripts to a file.
#   - An Agent that does not have TTS or an LLM. This is STT only.
# ---
# """
# from pathlib import Path
# from dotenv import load_dotenv
# from livekit.agents import JobContext, WorkerOptions, cli
# from livekit.agents.voice import Agent, AgentSession
# from livekit.plugins import deepgram
# import datetime

# load_dotenv(dotenv_path=Path(__file__).parent.parent / '.env')

# async def entrypoint(ctx: JobContext):
#     session = AgentSession()
    
#     @session.on("user_input_transcribed")
#     def on_transcript(transcript):
#         if transcript.is_final:
#             timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#             with open("user_speech_log.txt", "a") as f:
#                 f.write(f"[{timestamp}] {transcript.transcript}\n") 
    
#     await session.start(
#         agent=Agent(
#             instructions="You are a helpful assistant that transcribes user speech to text.",
#             stt=deepgram.STT()
#         ),
#         room=ctx.room
#     )

# if __name__ == "__main__":
#     cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))

"""
---
title: Transcriber
category: pipeline-stt
tags: [pipeline-stt, deepgram, livekit]
difficulty: beginner
description: 
  Basic transcriber agent that connects to a LiveKit room, 
  listens to user and AI messages, and stores conversation in memory.
---
"""

from pathlib import Path
import datetime
import os
from dotenv import load_dotenv, find_dotenv
from livekit.agents import (
    JobContext,
    WorkerOptions,
    cli,
)
from livekit.agents.voice import Agent, AgentSession
from livekit.plugins import deepgram

# ==============================
# ENV SETUP
# ==============================
load_dotenv(find_dotenv(), override=True)

conversation_log = []  # Unified storage for user + AI logs
TRANSCRIPT_FILE = Path(__file__).parent / "conversation_log.txt"
TRANSCRIPT_FILE.touch(exist_ok=True)


# ==============================
# MAIN ENTRYPOINT
# ==============================
async def entrypoint(ctx: JobContext):
    # Connect to room before using session or Agent
    await ctx.connect()

    session = AgentSession()

    # USER SPEECH HANDLER (STT)
    @session.on("user_input_transcribed")
    def on_user_transcribed(event):
        if getattr(event, "is_final", False):
            text = getattr(event, "transcript", "").strip()
            if not text:
                return
            ts = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            entry = {"timestamp": ts, "role": "user", "text": text}
            conversation_log.append(entry)
            print(f"[{ts}] USER: {text}")
            with open(TRANSCRIPT_FILE, "a", encoding="utf-8") as f:
                f.write(f"[{ts}] USER: {text}\n")

    # AI / ASSISTANT MESSAGE HANDLER
    @session.on("conversation_item_added")
    def on_ai_message(event):
        msg = getattr(event.item, "text_content", None)
        if msg:
            ts = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            entry = {"timestamp": ts, "role": "ai", "text": msg.strip()}
            conversation_log.append(entry)
            print(f"[{ts}] AI: {msg}")
            with open(TRANSCRIPT_FILE, "a", encoding="utf-8") as f:
                f.write(f"[{ts}] AI: {msg}\n")

    # ==============================
    # START SESSION
    # ==============================
    await session.start(
        agent=Agent(
            instructions="You are a helpful real-time transcriber. "
                         "Listen carefully and log every user phrase.",
            stt=deepgram.STT(model="nova-3"),
        ),
        room=ctx.room,
    )

    # When session ends, show full captured conversation
    print("\n=== FULL CONVERSATION ===")
    for msg in conversation_log:
        print(f"[{msg['timestamp']}] {msg['role'].upper()}: {msg['text']}")


# ==============================
# WORKER STARTUP
# ==============================
if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
