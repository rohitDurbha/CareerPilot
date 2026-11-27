# Interview agent

These are the two LiveKit agents that the Flask backend starts when a mock interview begins. They were originally taken from the LiveKit `python-agents-examples` repository, and only the pieces CareerPilot actually runs are kept here.

`interviewer.py` joins the room as the interviewer. It greets the candidate, asks about their background and resume, follows up one question at a time, and writes the running transcript to `ai_interview_log.txt`.

The interviewer runs entirely on the Groq free tier with one `GROQ_API_KEY`. It listens with Whisper (`whisper-large-v3-turbo`), replies with GPT-OSS 20B (`openai/gpt-oss-20b`, capped at 300 completion tokens with low reasoning effort) and speaks with Orpheus (`canopylabs/orpheus-v1-english`, voice `autumn`). The paid AssemblyAI, OpenAI and Cartesia models it used before are gone.

`groq_budget.py` keeps each interview inside a fixed share of the daily limits. Groq only publishes its Developer plan base limits, which the free tier never exceeds, so those are the upper bound, and each of `CAREERPILOT_INTERVIEWS_PER_DAY` interviews (default 2) gets an equal share of 80% of them. Orpheus is the tightest, at 100 requests and 3,600 tokens a day with at most 200 characters per request, so each reply is packed into as few chunks of up to 200 characters as possible and the requests are paced at 8 a minute. Once any share is 75% used the interviewer thanks the candidate and ends the interview, and when the session closes it logs one line with the requests, tokens, audio seconds and characters each model used. `.env.example` lists the models and their published limits.

`transcriber.py` joins the same room and records what the candidate says to `user_transcribed_log.txt`, which the dashboard reads back after the session.

## Running locally

Copy `.env.example` to `.env` in this folder and fill in your LiveKit Cloud credentials, a Groq key and a Deepgram key, then install the requirements and connect both agents to a room.

```bash
pip install -r requirements.txt
python interviewer.py connect --room test-room
python transcriber.py connect --room test-room
```

The backend runs the same two commands for you through the `/run_agents` route.
