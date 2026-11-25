# CareerPilot Roadmap

Each session finishes a whole item when it can, and items stay split into steps so progress is easy to follow. Items 4 and 5 are the live link and come before everything else, because bugs are easier to find and fix while a link is up.

- [x] 1. Debloat the repository
  - [x] a. Keep only the two LiveKit interview agents that `Project/backend.py` launches, move them into `interview_agent/` with their own requirements, delete the rest of the vendored `python-agents-examples` folder, and point the backend at the new paths.
  - [x] b. Remove `Project/test.html` and drop torch, transformers, sentence-transformers and llama-index from `Project/requirements.txt` in favour of the packages the Flask app actually imports.
- [x] 2. Merge the duplicate `Project/app.py` and `Project/backend.py` into one Flask app, and move the Activepieces webhook URLs and the MongoDB connection string into environment variables.
  - [x] a. Add a small `Project/config.py` that reads the MongoDB connection string, database and collection names and the two Activepieces webhook URLs from environment variables (with an optional `Project/.env`), document them in `Project/.env.example`, and have both Flask files use it so no URL or password stays in the code.
  - [x] b. Fold the one useful piece of `Project/app.py` into `Project/backend.py`, delete `app.py`, drop the unused Supabase import, and point the HTML pages and README at the single app on port 5001.
  - [x] c. Add Flask test client tests for every route with the workflows and MongoDB stubbed out, so the merged app is covered before the mock mode in item 3.
- [x] 3. Add a local mock mode that replays sample job and scoring payloads so every workflow can be tested without Activepieces or Apify.
  - [x] a. Add a `CAREERPILOT_MOCK` setting and sample job search and resume match payloads in `Project/mock_data`, and have `/trigger` and `/upload_resume` replay them through `mock://` addresses instead of calling Activepieces, with tests that block the network.
  - [x] b. Serve `/latest_jobs` in mock mode from the sample jobs joined with their scores, sorted the same way as MongoDB, without opening a MongoDB connection.
  - [x] c. Make `/run_agents` and `/cancel_file1` pretend to start and stop the interview agents in mock mode so the dashboard flow can be clicked through without LiveKit, and document the whole mock flow in the README.

The goal right now is a working hosted link. Items 4 to 6 get a demo online in mock mode first and then switch on the real services. The bigger rebuilds come after that.

- [x] 4. Make the app hostable.
  - [x] a. Replace every hardcoded `localhost:5001` call in `index.html`, `dashboard.html` and the interview room with one backend address setting, and replace the hardcoded `localhost:3000` interview room link with a second setting, both defaulting to the local addresses.
  - [x] b. Stop exposing the LiveKit secret to the browser. Read the key and secret in `meet` from server-only variables instead of `NEXT_PUBLIC_LIVEKIT_API_SECRET` and `NEXT_PUBLIC_LIVEKIT_API_KEY`, and add `meet/.env.example`.
  - [x] c. Make the Flask backend production ready. Serve it with gunicorn on the `PORT` variable, lock CORS to a configured frontend origin, and add tests for both.
- [ ] 5. Deploy a public demo in mock mode.
  - [ ] a. Add a Dockerfile for a Hugging Face Docker Space that runs the backend with `CAREERPILOT_MOCK=1` on port 7860, check that the image builds and answers `/` locally, and add a workflow that pushes it to the Space with the `HF_TOKEN` repository secret.
  - [ ] b. Serve the dashboard and search pages from the `meet` Next.js app so one Vercel project hosts the whole frontend, pointed at the hosted backend, and deploy it from a workflow with the `VERCEL_TOKEN` repository secret.
  - [ ] c. Add a check after each deploy that loads the dashboard and calls the backend, then put the live link at the top of the README and of this roadmap.
  - [ ] d. Add a workflow that sends one test prompt with the `GROQ_API_KEY` and `GEMINI_API_KEY` repository secrets, so a key that stops working shows up as a failed run.
### Bugs found on the live site

Every session opens the live link first, adds anything broken here, and fixes these before the numbered items.

- None logged yet, because the site is not live.

- [ ] 6. Switch on the real services in the hosted app. Document the MongoDB Atlas and Activepieces settings for the host, add a health check that reports which services are configured, and turn mock mode off once the keys are in place.
- [ ] 7. Replace the paid Tavus and Hedra video avatars with a free mock interview stack. LiveKit Cloud free tier plus the Gemini Live API free tier for real-time voice, or Groq with faster-whisper and Piper for a fully open setup. Use the open-source TalkingHead three.js avatar for a lip-synced face in the browser.
- [ ] 8. Replace the LinkedIn crawler, which breaks LinkedIn's terms, with public Greenhouse, Lever and Ashby job board APIs.
- [ ] 9. Keep resume scoring on the Groq free tier and add a clear score breakdown.
- [ ] 10. Rebuild the plain HTML dashboard and search pages as real Next.js pages that share components with the interview room.
- [ ] 11. Tests, CI and a rewritten README.

## Needs Rohit

- Copy `Project/.env.example` to `Project/.env` and fill in the MongoDB connection string and the two Activepieces webhook URLs. The old webhook URLs were removed from the code, so either reuse them from your Activepieces flows or create fresh webhooks.
- Rotate the MongoDB Atlas password for the `cs156` user. It used to be hardcoded in `Project/backend.py` and still sits in git history even though item 2 moved it into an environment variable.
- Done. `GROQ_API_KEY` and `GEMINI_API_KEY` are saved as repository secrets.
- Add `VERCEL_TOKEN` and `HF_TOKEN` as repository secrets for item 5. The same tokens already saved in safe-stride work here too.
- Add the connection string of the new CareerPilot Atlas cluster as the `MONGO_URI` repository secret for item 6.
- If the LiveKit API secret was ever stored under `NEXT_PUBLIC_LIVEKIT_API_SECRET` on a host such as Vercel, rotate it in the LiveKit Cloud dashboard and set the new key and secret as `LIVEKIT_API_KEY` and `LIVEKIT_API_SECRET` instead.
- LiveKit Cloud project keys, a Gemini or Groq key, an Activepieces account and an Apify free account.
