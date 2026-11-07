# CareerPilot Roadmap

Work moves one step at a time. A step is ticked when it is done and an item is ticked once all of its steps are done.

- [x] 1. Debloat the repository
  - [x] a. Keep only the two LiveKit interview agents that `Project/backend.py` launches, move them into `interview_agent/` with their own requirements, delete the rest of the vendored `python-agents-examples` folder, and point the backend at the new paths.
  - [x] b. Remove `Project/test.html` and drop torch, transformers, sentence-transformers and llama-index from `Project/requirements.txt` in favour of the packages the Flask app actually imports.
- [ ] 2. Merge the duplicate `Project/app.py` and `Project/backend.py` into one Flask app, and move the Activepieces webhook URLs and the MongoDB connection string into environment variables.
  - [ ] a. Add a small `Project/config.py` that reads the MongoDB connection string, database and collection names and the two Activepieces webhook URLs from environment variables (with an optional `Project/.env`), document them in `Project/.env.example`, and have both Flask files use it so no URL or password stays in the code.
  - [ ] b. Fold the one useful piece of `Project/app.py` into `Project/backend.py`, delete `app.py`, drop the unused Supabase import, and point the HTML pages and README at the single app on port 5001.
  - [ ] c. Add Flask test client tests for every route with the workflows and MongoDB stubbed out, so the merged app is covered before the mock mode in item 3.
- [ ] 3. Add a local mock mode that replays sample job and scoring payloads so every workflow can be tested without Activepieces or Apify.
- [ ] 4. Replace the paid Tavus and Hedra video avatars with a free mock interview stack. LiveKit Cloud free tier plus the Gemini Live API free tier for real-time voice, or Groq with faster-whisper and Piper for a fully open setup. Use the open-source TalkingHead three.js avatar for a lip-synced face in the browser.
- [ ] 5. Replace the LinkedIn crawler, which breaks LinkedIn's terms, with public Greenhouse, Lever and Ashby job board APIs.
- [ ] 6. Keep resume scoring on the Groq free tier and add a clear score breakdown.
- [ ] 7. Unify the frontend into the Next.js app so the dashboard and the interview room live in one place.
- [ ] 8. Host for free. Vercel for Next.js, Render or Hugging Face Spaces for Flask, LiveKit Cloud free, MongoDB Atlas M0, and the Activepieces free cloud plan or a self-hosted n8n.
- [ ] 9. Tests, CI and a rewritten README.

## Needs Rohit

- Rotate the MongoDB Atlas password for the `cs156` user. It is hardcoded in `Project/backend.py` and remains in git history even after item 2 moves it into an environment variable.
- LiveKit Cloud project keys, a Gemini or Groq key, an Activepieces account, an Apify free account and a Vercel account.
