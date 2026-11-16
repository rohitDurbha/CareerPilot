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

**Backend and interview room addresses**

The pages default to the local servers, so nothing needs changing for local work. When the backend or the interview room runs somewhere else, change the two values at the top of `Project/settings.js`. `apiUrl` is where `index.html` and `dashboard.html` send their requests and `meetUrl` is where the dashboard opens the interview room. The interview room reaches the backend through `NEXT_PUBLIC_CAREERPILOT_API_URL`, which also falls back to `http://localhost:5001` when it is not set.

Start the interview room from the `meet` folder in a second terminal.

```bash
cd meet
npm install
npm run dev
```

The mock interview agents in `interview_agent/` need a LiveKit server, which you can run locally with Docker or point at LiveKit Cloud.
