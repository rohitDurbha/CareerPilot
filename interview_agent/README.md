# Interview agent

These are the two LiveKit agents that the Flask backend starts when a mock interview begins. They were originally taken from the LiveKit `python-agents-examples` repository, and only the pieces CareerPilot actually runs are kept here.

`interviewer.py` joins the room as the interviewer. It greets the candidate, asks about their background and resume, follows up one question at a time, and writes the running transcript to `ai_interview_log.txt`.

`transcriber.py` joins the same room and records what the candidate says to `user_transcribed_log.txt`, which the dashboard reads back after the session.

## Running locally

Copy `.env.example` to `.env` in this folder and fill in your LiveKit Cloud credentials and a Deepgram key, then install the requirements and connect both agents to a room.

```bash
pip install -r requirements.txt
python interviewer.py connect --room test-room
python transcriber.py connect --room test-room
```

The backend runs the same two commands for you through the `/run_agents` route.
