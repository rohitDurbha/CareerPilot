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
  - [x] a. Host the backend for free. The Hugging Face Docker Space plan was dropped, because on November 24, 2026 Hugging Face answered 402 Payment Required for free Docker Spaces on the safe-stride project. The backend now runs in mock mode as a Vercel Python function at `/api` (`api/index.py`, with `Project/prefix.py` stripping the prefix and the root `requirements.txt` listing its packages), checked locally with the dashboard loading all three sample jobs through `/api`.
  - [x] b. Serve the search and dashboard pages from the same Vercel project. `scripts/build-site.mjs` copies them into `site/` and points `settings.js` at `/api`, so the pages and the backend share one address and need no CORS. Moving the pages into the `meet` Next.js app is left to item 10.
  - [ ] c. Deploy from `.github/workflows/deploy.yml` with the `VERCEL_TOKEN` secret on every push, then run `.github/scripts/live_check.py` against the live address and put the live link at the top of the README and of this roadmap. The workflow and the check are in place, and the first run on November 25, 2026 passed its tests but stopped because `VERCEL_TOKEN` is not saved in this repository yet.
  - [x] d. Add a workflow that sends one test prompt with the `GROQ_API_KEY` and `GEMINI_API_KEY` repository secrets, so a key that stops working shows up as a failed run. `.github/workflows/key-check.yml` runs daily with `.github/scripts/key_check.py`, using Groq `openai/gpt-oss-20b` (the Llama 3.1 and 3.3 models were shut down on August 16, 2026) and Gemini 2.5 Flash-Lite with a fallback to the stable Gemini 3.5 Flash-Lite.
  - [ ] e. Host the interview room from `meet` so the dashboard's mock interview button stops pointing at `localhost:3000`, and pass its address to the build as `CAREERPILOT_MEET_URL`.
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
- Add `VERCEL_TOKEN` as a repository secret in CareerPilot (Settings, Secrets and variables, Actions). The token already saved in safe-stride works here too. It is the only thing between the finished deploy workflow and a live link. `HF_TOKEN` is no longer needed, because Hugging Face now charges for Docker Spaces.
- Check the Gemini free tier limits for your key in the Google AI Studio rate limit page, since Google only publishes them there. The daily key check sends one request a day, so it stays well inside any limit.
- Add the connection string of the new CareerPilot Atlas cluster as the `MONGO_URI` repository secret for item 6.
- If the LiveKit API secret was ever stored under `NEXT_PUBLIC_LIVEKIT_API_SECRET` on a host such as Vercel, rotate it in the LiveKit Cloud dashboard and set the new key and secret as `LIVEKIT_API_KEY` and `LIVEKIT_API_SECRET` instead.
- LiveKit Cloud project keys, a Gemini or Groq key, an Activepieces account and an Apify free account.
