from pathlib import Path
import datetime
from dotenv import load_dotenv, find_dotenv
from livekit.agents import (
    JobContext,
    WorkerOptions,
    cli,
)
from livekit.agents.voice import Agent, AgentSession
from livekit.plugins import deepgram



# ==========
# LOAD ENV
# ==========
load_dotenv(find_dotenv(), override=True)

# === Where to store the AI-transcribed log ===
AI_TRANSCRIBED_FILE = Path(__file__).parent / "user_transcribed_log.txt"
AI_TRANSCRIBED_FILE.touch(exist_ok=True)

conversation_log = []

async def entrypoint(ctx: JobContext):
    # You can use 'args' global for job_title and job_description!
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
            with open(AI_TRANSCRIBED_FILE, "a", encoding="utf-8") as f:
                f.write(f"[{ts}] USER: {text}\n")

    # AI MESSAGE HANDLER
    @session.on("conversation_item_added")
    def on_ai_message(event):
        msg = getattr(event.item, "text_content", None)
        if msg:
            ts = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            entry = {"timestamp": ts, "role": "ai", "text": msg.strip()}
            conversation_log.append(entry)
            print(f"[{ts}] AI transcribed: {msg.strip()}")
            with open(AI_TRANSCRIBED_FILE, "a", encoding="utf-8") as f:
                f.write(f"[{ts}] AI transcribed: {msg.strip()}\n")

    # Put job title and job description into agent session, log, or your flow as needed
    print("Agent starting with job title:", args.job_title)
    print("Job description:", args.job_description)

    await session.start(
        agent=Agent(
            instructions="You are a helpful real-time transcriber. "
                         "Listen carefully and log every phrase of both user and AI.",
            stt=deepgram.STT(model="nova-3"),
        ),
        room=ctx.room,
    )

    # At the end, print the whole conversation
    print("\n=== FULL CONVERSATION ===")
    for msg in conversation_log:
        print(f"[{msg['timestamp']}] {msg['role'].upper()}: {msg['text']}")

if __name__ == "__main__":
    # All CLI parsing already done above.
    # No need to check args.command - argparse enforces it.
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
