**CareerPilot**

Find. Fit. Apply. Train.

CareerPilot is an AI-powered job search companion that automates opportunity discovery, resume–JD scoring, and interview preparation. It helps students and jobseekers reduce repetitive effort and get real-time insights through intelligent agents.

**Features**

**1. Job Discovery Automation:**
Uses Activepieces and Apify to scrape and normalize job listings from multiple sources.
   
**2. Resume Scoring**
   Groq API matches your resume with job descriptions and provides improvement tips.
   
**3. AI-Powered Interview Practice**
LiveKit agents conduct mock interviews, analyze responses, and deliver real-time coaching.

**4. Centralized Dashboard**
All jobs, sessions, scores, and training history are tracked in one unified interface.

**Data Storage: MongoDB**
Stores job records, resume scores, interview transcripts, analytics, and session metadata.


**How It Works**

**1. Job Search Workflow**: User enters keywords/location, Activepieces triggers Apify job-scraping actors, Backend cleans, enriches, geocodes, and deduplicates results, Jobs are stored with provenance and freshness checks.


**2. Resume Evaluation**: User uploads resume, Groq compares resume vs job descriptions, System generates similarity score + tips.


**3. Interview Training**: LiveKit captures real-time audio, Streaming STT → diarization → segmentation, LLM agent reviews performance, Dashboard displays insights (filler words, sentiment, pacing, etc.).


**Tech Stack**

**Frontend:** HTML
**Backend:** Flask
**DB:** MongoDB
**Automation:** Activepieces + Apify
**AI Scoring:** Groq
**Mock Interviews:** LiveKit
**Enhanced Retrieval:** LlamaIndex (planned)

**Run Instructions:**

Start the Flask backend from the `Project` folder. It is the only backend now and it listens on port 5001, which is where `index.html` and `dashboard.html` send their requests.

```bash
cd Project
pip install -r requirements.txt
cp .env.example .env   # then fill in MongoDB and the Activepieces webhooks
python backend.py
```

**Mock mode**

To click through the whole dashboard without Activepieces, Apify, MongoDB or LiveKit, start the backend in mock mode. You do not need a `.env` file for this.

```bash
cd Project
CAREERPILOT_MOCK=1 python backend.py
```

Here is what each part of the app does while mock mode is on.

- `index.html` posts your resume to `/trigger`, and the backend answers both the job search and the resume match workflows from the sample payloads in `Project/mock_data` instead of calling Activepieces. Your resume text is only reported back as a length.
- `dashboard.html` loads `/latest_jobs`, which returns the three sample jobs joined with their sample scores in the same order MongoDB would use.
- Starting a mock interview from the dashboard calls `/run_agents`, which returns the usual started response with `"mock": true` but does not launch the LiveKit agents. Leaving the room calls `/cancel_file1`, which stops those stand-in agents the normal way.

Every mock response carries `"mock": true` so it is easy to tell sample data from real results. To change the sample jobs or scores, edit the two JSON files in `Project/mock_data` and keep their `jobId` values matching.

**Running the backend on a host**

Hosts run the backend with gunicorn, which reads its settings from `Project/gunicorn.conf.py`. It listens on the `PORT` variable that the host provides and falls back to 5001 when that is not set. It keeps a single worker with a few threads, because the interview agent processes are tracked inside that one worker.

```bash
cd Project
PORT=7860 CAREERPILOT_ALLOWED_ORIGINS=https://your-frontend.vercel.app gunicorn backend:app
```

Browsers may only call the backend from the origins listed in `CAREERPILOT_ALLOWED_ORIGINS`, separated by commas. When it is not set, only pages on `localhost` or `127.0.0.1` and pages opened straight from disk are allowed, which keeps local work unchanged.

**Hosted demo**

The demo runs on two free Vercel projects, both published by `.github/workflows/deploy.yml` on every push to `main`. The workflow runs the backend tests and the interview room's typecheck and tests, then publishes `careerpilot-demo` (the two pages built into `site/` by `scripts/build-site.mjs`, with the backend in mock mode as a Python function under `/api`) and `careerpilot-meet` (the Next.js interview room in `meet/`). It publishes the pages once more so the dashboard's mock interview button opens the hosted room and the backend accepts calls from it, and finally runs `.github/scripts/live_check.py` against both addresses. Each project is deployed by `.github/scripts/vercel_deploy.sh`, which prints the stable address found by `.github/scripts/production_url.py`.

It needs the `VERCEL_TOKEN` repository secret. The `LIVEKIT_URL`, `LIVEKIT_API_KEY` and `LIVEKIT_API_SECRET` secrets are optional. Without them the room still loads, `/api/health` lists what is missing, and joining shows that message instead of failing silently.

The hosted backend reads the same settings as `Project/.env.example`, passed in from repository secrets by `.github/scripts/backend_flags.sh`.

| Secret | What it is |
| --- | --- |
| `MONGO_URI` | Connection string of the MongoDB Atlas cluster that holds the scored jobs. A free M0 cluster is enough. In Atlas, allow access from anywhere (`0.0.0.0/0`), because Vercel functions have no fixed address. |
| `ACTIVEPIECES_JOB_SEARCH_WEBHOOK` | Webhook URL of the Activepieces flow that searches for jobs. |
| `ACTIVEPIECES_RESUME_MATCH_WEBHOOK` | Webhook URL of the Activepieces flow that scores the resume against those jobs. |
| `MONGO_DB`, `MONGO_COLLECTION` | Optional database and collection names, defaulting to `scrapped_jobs` and `Careerpilot`. |

The backend leaves mock mode only when the first three are all saved, so a half finished setup keeps showing the sample jobs instead of a broken page.

`GET /health` (or `/api/health` on the hosted demo) reports whether the backend is in mock or live mode, which of MongoDB and the two Activepieces webhooks are configured, and `missing`, the variables live mode still needs. It only answers yes or no for each service and never shows a connection string or webhook address. MongoDB counts as configured once `MONGO_URI` points somewhere other than the local default. The live check fails when `ready` is false.

**LLM keys and free tier limits**

`.github/workflows/key-check.yml` sends one short prompt a day to each provider with the `GROQ_API_KEY` and `GEMINI_API_KEY` secrets, and logs the tokens each one counted. Both keys are on free tiers.

| Provider | Model | Free tier limits (checked November 25, 2026) |
| --- | --- | --- |
| Groq | `openai/gpt-oss-20b` | 30 requests and 8K tokens a minute, 1K requests and 200K tokens a day |
| Gemini | `gemini-3.5-flash-lite` (2.5 Flash-Lite is closed to new users) | Shown only in the Google AI Studio dashboard for each key |

**Backend and interview room addresses**

The pages default to the local servers, so nothing needs changing for local work. When the backend or the interview room runs somewhere else, change the two values at the top of `Project/settings.js`. `apiUrl` is where `index.html` and `dashboard.html` send their requests and `meetUrl` is where the dashboard opens the interview room. The interview room reaches the backend through `NEXT_PUBLIC_CAREERPILOT_API_URL`, which also falls back to `http://localhost:5001` when it is not set.

Start the interview room from the `meet` folder in a second terminal. Copy `meet/.env.example` to `meet/.env.local` first and fill in your LiveKit project URL, API key and API secret.

```bash
cd meet
cp .env.example .env.local
npm install
npm run dev
```

The LiveKit key and secret are read only on the server, by the route that signs room tokens, through `LIVEKIT_URL`, `LIVEKIT_API_KEY` and `LIVEKIT_API_SECRET`. Older setups used names starting with `NEXT_PUBLIC_`, which Next.js copies into the browser bundle, so the room now ignores those and asks for the server-only names instead. If you had the secret under the old name anywhere public, rotate it in the LiveKit Cloud dashboard.

The mock interview agents in `interview_agent/` need a LiveKit server, which you can run locally with Docker or point at LiveKit Cloud.
