# """
# ---
# title: Listen and Respond
# category: basics
# tags: [listen, respond, openai, deepgram]
# difficulty: beginner
# description: Shows how to create an agent that can listen to the user and respond.
# demonstrates:
#   - This is the most basic agent that can listen to the user and respond. This is a good starting point for any agent.
# ---
# """

# import logging
# import os
# from pathlib import Path
# from dotenv import load_dotenv
# from livekit.agents import JobContext, WorkerOptions, cli
# from livekit.agents.voice import Agent, AgentSession
# from livekit.plugins import silero

# load_dotenv(dotenv_path=Path(__file__).parent.parent / '.env')

# logger = logging.getLogger("listen-and-respond")
# logger.setLevel(logging.INFO)

# class ListenAndRespondAgent(Agent):
#     def __init__(self) -> None:
#         super().__init__(
#             instructions="""
#                 You are a helpful agent.
#                 Ask me 2 random questions,
#                 At the end ask me for my name
#             """,
#             stt="assemblyai/universal-streaming",
#             llm="openai/gpt-4.1-mini",
#             tts="cartesia/sonic-2:6f84f4b8-58a2-430c-8c79-688dad597532",
#             vad=silero.VAD.load()
#         )

#     async def on_enter(self):
#         self.session.generate_reply()

# async def entrypoint(ctx: JobContext):
#     session = AgentSession()

#     await session.start(
#         agent=ListenAndRespondAgent(),
#         room=ctx.room
#     )

# if __name__ == "__main__":
#     cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))

# """
# ---
# title: Listen and Respond Interview Agent
# category: basics
# tags: [listen, respond, livekit, supabase, openai]
# description: A LiveKit interview agent that listens, responds, asks contextual questions one-by-one, and stores conversation transcripts in Supabase.
# ---
# """

# import os
# import argparse
# import logging
# from pathlib import Path
# from dotenv import load_dotenv
# from supabase import create_client, Client
# from livekit.agents import JobContext, WorkerOptions, cli
# from livekit.agents.voice import Agent, AgentSession
# from livekit.plugins import silero


# # ---------------- SETUP ----------------
# load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

# logger = logging.getLogger("livekit-interview")
# logger.setLevel(logging.INFO)

# # Command-line arguments (passed by shell)
# # parser = argparse.ArgumentParser(description="Interview agent with job & candidate parameters")
# # parser.add_argument("--jobid", type=str, required=True)
# # parser.add_argument("--candidate", type=str, required=True)
# # args = parser.parse_args()
# # JOB_ID = args.jobid
# # CANDIDATE_EMAIL = args.candidate

# parser = argparse.ArgumentParser(description="Interview agent with optional parameters for testing")
# parser.add_argument("--jobid", type=str, default="test-job", help="Job ID (optional)")
# parser.add_argument("--candidate", type=str, default="anon@example.com", help="Candidate email (optional)")
# args, unknown = parser.parse_known_args()  # allows extra args like 'connect --room'
# JOB_ID = args.jobid
# CANDIDATE_EMAIL = args.candidate


# # --- Supabase connection ---
# SUPABASE_URL = os.getenv("SUPABASE_URL")
# SUPABASE_KEY = os.getenv("SUPABASE_KEY")
# supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# # --- Retrieve job context ---
# try:
#     job_record = (
#         supabase.table("job")
#         .select("title, description, required_skills, preferred_skills")
#         .eq("job_id", JOB_ID)
#         .single()
#         .execute()
#     )
#     job_info = job_record.data if job_record.data else {}
# except Exception as e:
#     logger.error(f"Failed to load job info: {e}")
#     job_info = {}

# # ---------------- AGENT LOGIC ----------------

# # Dynamically generated prompt for this interview
# instructions = f"""
# You are a professional AI voice interviewer for a job candidate.

# Job Title: {job_info.get('title', 'Unknown Position')}
# Description: {job_info.get('description', 'No description available')}
# Skills: {job_info.get('skills', 'Not specified')}

# Your task:
# - Conduct this as a structured but conversational interview.
# - Ask **one question at a time**, and wait for the candidate to answer before proceeding.
# - If the candidate gives a vague or partial answer, ask a clarifying follow-up.
# - Cover both behavioral and technical dimensions relevant to the job.
# - Adapt your next question based on previous answers to make the interview natural.
# - End the session politely by asking: "Can you please tell me your full name for our records?"
# - Keep tone friendly and professional.
# """


# # Store full transcript per session
# conversation_log = []


# class ListenAndRespondAgent(Agent):
#     def __init__(self) -> None:
#         super().__init__(
#             instructions=instructions,
#             stt="assemblyai/universal-streaming",  # Speech-to-text
#             llm="openai/gpt-4.1-mini",            # Language model
#             tts="cartesia/sonic-2:6f84f4b8-58a2-430c-8c79-688dad597532",  # Text-to-speech
#             vad=silero.VAD.load()                 # Voice activity detector
#         )

#     async def on_chat_message(self, message):
#         """Triggered for every message (agent or candidate)."""
#         conversation_log.append({
#             "role": message.role,
#             "text": message.text
#         })
#         await super().on_chat_message(message)

#     async def on_enter(self):
#         """Called when agent joins the room."""
#         logger.info("✅ Interview agent joined room and ready.")
#         self.session.generate_reply()

#     async def on_leave(self):
#         """On meeting end: store conversation transcript."""
#         try:
#             if conversation_log:
#                 supabase.table("livekit_interviews").insert({
#                     "job_id": JOB_ID,
#                     "candidate_email": CANDIDATE_EMAIL,
#                     "room_name": self.session.room.name,
#                     "conversation": conversation_log
#                 }).execute()
#                 logger.info(f"✅ Conversation for {CANDIDATE_EMAIL} saved to Supabase.")
#         except Exception as e:
#             logger.error(f"❌ Failed to store conversation: {e}")


# # ---------------- ENTRYPOINT ----------------

# async def entrypoint(ctx: JobContext):
#     session = AgentSession()
#     await session.start(
#         agent=ListenAndRespondAgent(),
#         room=ctx.room
#     )


# if __name__ == "__main__":
#     cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))

#-------------------------------------------------------------

# import os
# import json
# import logging
# from datetime import datetime
# import uuid
# from pathlib import Path
# from dataclasses import dataclass
# from dotenv import load_dotenv
# from supabase import acreate_client
# from livekit.agents import JobContext, WorkerOptions, cli, ChatContext
# from livekit.agents.voice import Agent, AgentSession
# from livekit.plugins import silero

# # ======================
# # ENVIRONMENT SETUP
# # ======================
# load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

# SUPABASE_URL = os.getenv("SUPABASE_URL")
# SUPABASE_KEY = os.getenv("SUPABASE_KEY")
# logger = logging.getLogger("ai-interviewer")
# logger.setLevel(logging.INFO)

# # ======================
# # SUPABASE DATA RETRIEVAL
# # ======================
# async def fetch_applicant_data(app_id: str):
#     supabase = await acreate_client(SUPABASE_URL, SUPABASE_KEY)
#     query = (
#         "name, email, resume, "
#         "job:job_id ( title, description, required_skills, preferred_skills )"
#     )
#     response = await supabase.table("application").select(query).eq("app_id", app_id).execute()
#     if not response.data:
#         raise Exception(f"No data found for app_id {app_id}")
    
#     row = response.data[0]
#     job = row.get("job", {})
#     return {
#         "name": row["name"],
#         "email": row["email"],
#         "resume": row["resume"],
#         "title": job.get("title"),
#         "description": job.get("description"),
#         "required_skills": job.get("required_skills", []),
#         "preferred_skills": job.get("preferred_skills", []),
#     }

# # ======================
# # SUPABASE INTERVIEW SAVE LOGIC
# # ======================
# async def save_interview_results(interview_id: str, transcript: str, ai_score: dict):
#     supabase = await acreate_client(SUPABASE_URL, SUPABASE_KEY)
#     await supabase.table("interview").upsert({
#         "interview_id": interview_id,
#         "transcript": transcript,
#         "ai_score": json.dumps(ai_score),
#         "completed_at": datetime.utcnow().isoformat(),
#     }).execute()
#     logger.info(f"✅ Saved interview transcript and ai_score for {interview_id}")

# # ======================
# # USERDATA STORAGE
# # ======================
# @dataclass
# class InterviewData:
#     interview_id: str | None = None

# # ======================
# # AI INTERVIEWER AGENT CLASS
# # ======================
# class AIInterviewerAgent(Agent):
#     def __init__(self, chat_ctx: ChatContext):
#         super().__init__(
#             chat_ctx=chat_ctx,
#             instructions=(
#                 "You are a professional AI interviewer conducting a short behavioral interview. "
#                 "Ask one question at a time and wait for the candidate’s response. "
#                 "Start with greetings ('Hi, how are you?'), then move to 'Tell me about yourself.' "
#                 "Ask 2–3 resume-relevant or STAR-style questions and conclude with thanks."
#             ),
#             stt="assemblyai/universal-streaming",
#             llm="openai/gpt-4.1-mini",
#             tts="cartesia/sonic-2:6f84f4b8-58a2-430c-8c79-688dad597532",
#             vad=silero.VAD.load(),
#         )
#         self.transcript = []
#         self.my_ctx = chat_ctx

#     async def on_loaded(self):
#         # Register listeners globally to persist through lifecycle
#         self.session.on("conversation_item_added", self._handle_conversation_added)
#         self.session.on("user_input_transcribed", self._handle_user_transcribed)
#         logger.info("✅ Transcript event listeners initialized.")

#     async def _handle_conversation_added(self, event):
#         msg = event.item
#         if msg.role in ["assistant", "user"] and getattr(msg, "text_content", None):
#             self.transcript.append(f"{msg.role.upper()}: {msg.text_content.strip()}")
#             logger.debug(f"Captured conversation item ({msg.role}): {msg.text_content.strip()}")

#     async def _handle_user_transcribed(self, event):
#         # Live STT final results
#         if event.is_final:
#             self.transcript.append(f"USER (spoken): {event.transcript.strip()}")
#             logger.debug(f"User speech: {event.transcript.strip()}")

#     async def on_enter(self):
#         await self.session.generate_reply()

#     async def on_exit(self):
#         # Merge transcripts and persist to Supabase
#         transcript = "\n".join(self.transcript)
#         print("\n===== Interview Transcript =====\n", transcript)

#         ai_score = {
#             "communication": 8.8,
#             "clarity": 8.9,
#             "confidence": 8.7,
#             "behavioral_depth": 8.6,
#             "skills_alignment": 9.1,
#         }

#         interview_id = self.session.userdata.interview_id
#         if interview_id:
#             await save_interview_results(interview_id, transcript, ai_score)
#         else:
#             logger.warning("⚠️ Interview ID missing — transcript only printed locally.")

# # ======================
# # MAIN ENTRYPOINT
# # ======================
# async def entrypoint(ctx: JobContext):
#     meta = ctx.job.metadata or {}
#     app_id = meta.get("app_id") or "f7960521-0395-45bd-8814-614b66f4f90c"
#     interview_id = meta.get("interview_id") or str(uuid.uuid4())

#     data = await fetch_applicant_data(app_id)
#     name = data["name"]
#     resume = data["resume"]
#     title = data["title"]
#     description = data["description"]
#     required_skills = data.get("required_skills", [])
#     preferred_skills = data.get("preferred_skills", [])

#     context = ChatContext()
#     context.add_message(
#         role="system",
#         content=(
#             f"Candidate: {name}. Resume: {resume}. Interview for {title}. "
#             f"Description: {description}. "
#             f"Required skills: {', '.join(required_skills) or 'N/A'}. "
#             f"Preferred skills: {', '.join(preferred_skills) or 'N/A'}."
#         ),
#     )

#     session = AgentSession(userdata=InterviewData(interview_id=interview_id))
#     await session.start(agent=AIInterviewerAgent(chat_ctx=context), room=ctx.room)

# if __name__ == "__main__":
#     cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))

#-------------------------------------------------------------
# import os
# import json
# import logging
# from datetime import datetime
# import uuid
# from pathlib import Path
# from dataclasses import dataclass
# from dotenv import load_dotenv
# from supabase import acreate_client
# from typing import AsyncIterable, AsyncGenerator

# from livekit.agents import (
#     JobContext,
#     WorkerOptions,
#     cli,
#     ChatContext,
#     RoomOutputOptions,
#     ModelSettings,
# )
# from livekit.agents.voice import Agent, AgentSession
# from livekit.plugins import silero


# # ======================
# # ENVIRONMENT SETUP
# # ======================
# load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

# SUPABASE_URL = os.getenv("SUPABASE_URL")
# SUPABASE_KEY = os.getenv("SUPABASE_KEY")
# logger = logging.getLogger("ai-interviewer")
# logger.setLevel(logging.INFO)


# # ======================
# # SUPABASE HELPERS
# # ======================
# async def fetch_applicant_data(app_id: str):
#     supabase = await acreate_client(SUPABASE_URL, SUPABASE_KEY)
#     query = (
#         "name, email, resume, "
#         "job:job_id ( title, description, required_skills, preferred_skills )"
#     )
#     response = await supabase.table("application").select(query).eq("app_id", app_id).execute()
#     if not response.data:
#         raise Exception(f"No data found for app_id {app_id}")
#     row = response.data[0]
#     job = row.get("job", {})
#     return {
#         "name": row["name"],
#         "email": row["email"],
#         "resume": row["resume"],
#         "title": job.get("title"),
#         "description": job.get("description"),
#         "required_skills": job.get("required_skills", []),
#         "preferred_skills": job.get("preferred_skills", []),
#     }


# async def save_interview_results(interview_id: str, transcript: str, ai_score: dict):
#     supabase = await acreate_client(SUPABASE_URL, SUPABASE_KEY)
#     await supabase.table("interview").upsert({
#         "interview_id": interview_id,
#         "transcript": transcript,
#         "ai_score": json.dumps(ai_score),
#         "completed_at": datetime.utcnow().isoformat(),
#     }).execute()
#     logger.info(f"✅ Saved interview transcript & score for {interview_id}")


# # ======================
# # DATA MODEL
# # ======================
# @dataclass
# class InterviewData:
#     interview_id: str | None = None


# # ======================
# # AGENT CLASS
# # ======================
# class AIInterviewerAgent(Agent):
#     def __init__(self, chat_ctx: ChatContext):
#         super().__init__(
#             chat_ctx=chat_ctx,
#             instructions=(
#                 "You are a professional AI interviewer conducting a short behavioral interview. "
#                 "Start with a greeting, then move to 'Tell me about yourself'. "
#                 "Ask 2-3 technical or behavioral questions based on the candidate’s resume, "
#                 "and conclude politely by asking for full name."
#             ),
#             stt="assemblyai/universal-streaming",
#             llm="openai/gpt-4.1-mini",
#             tts="cartesia/sonic-2:6f84f4b8-58a2-430c-8c79-688dad597532",
#             vad=silero.VAD.load(),
#         )
#         self.transcript = []
#         self.my_ctx = chat_ctx

#     # ----------- TRANSCRIPTION NODE -----------
#     async def transcription_node(
#         self, text: AsyncIterable[str], model_settings: ModelSettings
#     ) -> AsyncGenerator[str, None]:
#         async for segment in text:
#             cleaned = segment.strip()
#             if cleaned:
#                 self.transcript.append(cleaned)
#                 logger.debug(f"📝 Transcript captured: {cleaned}")
#             yield cleaned  # pass on to be streamed live

#     # ----------- LIFECYCLE HOOKS -----------
#     async def on_enter(self):
#         logger.info("✅ AI interviewer joined; starting conversation.")
#         await self.session.generate_reply()

#     async def on_exit(self):
#         transcript_text = "\n".join(self.transcript)
#         print("\n===== INTERVIEW TRANSCRIPT =====\n", transcript_text)

#         ai_score = {
#             "communication": 8.8,
#             "clarity": 8.9,
#             "confidence": 8.7,
#             "behavioral_depth": 8.6,
#             "skills_alignment": 9.1,
#         }

#         interview_id = self.session.userdata.interview_id
#         if interview_id:
#             await save_interview_results(interview_id, transcript_text, ai_score)
#         else:
#             logger.warning("⚠️ Interview ID missing — transcript only printed locally.")


# # ======================
# # MAIN ENTRYPOINT
# # ======================
# async def entrypoint(ctx: JobContext):
#     meta = ctx.job.metadata or {}
#     app_id = meta.get("app_id") or "f7960521-0395-45bd-8814-614b66f4f90c"
#     interview_id = meta.get("interview_id") or str(uuid.uuid4())

#     data = await fetch_applicant_data(app_id)
#     name = data["name"]
#     resume = data["resume"]
#     title = data["title"]
#     description = data["description"]
#     required_skills = data.get("required_skills", [])
#     preferred_skills = data.get("preferred_skills", [])

#     context = ChatContext()
#     context.add_message(
#         role="system",
#         content=(
#             f"Candidate: {name}. Resume: {resume}. Interview for {title}. "
#             f"Description: {description}. "
#             f"Required skills: {', '.join(required_skills) or 'N/A'}. "
#             f"Preferred skills: {', '.join(preferred_skills) or 'N/A'}."
#         ),
#     )

#     session = AgentSession(
#         userdata=InterviewData(interview_id=interview_id),
#         use_tts_aligned_transcript=True,
#     )

#     await session.start(
#         agent=AIInterviewerAgent(chat_ctx=context),
#         room=ctx.room,
#         room_output_options=RoomOutputOptions(sync_transcription=False),
#     )


# if __name__ == "__main__":
#     cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
#-------------------------------------------------------------

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
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

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
