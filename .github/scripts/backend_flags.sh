# Source this file to fill the bash array backend_flags with the vercel deploy
# flags for the CareerPilot backend.
#
# The backend runs in live mode only when MONGO_URI and both Activepieces
# webhook URLs are set. Otherwise it stays in mock mode with the sample jobs,
# so a half configured deploy never shows a broken site. Each value goes in
# its own array element, so passwords with spaces or symbols stay intact.

backend_flags=()
backend_mode=live
for name in MONGO_URI ACTIVEPIECES_JOB_SEARCH_WEBHOOK ACTIVEPIECES_RESUME_MATCH_WEBHOOK; do
  if [ -n "${!name:-}" ]; then
    backend_flags+=(--env "$name=${!name}")
  else
    backend_mode=mock
  fi
done
for name in MONGO_DB MONGO_COLLECTION; do
  if [ -n "${!name:-}" ]; then
    backend_flags+=(--env "$name=${!name}")
  fi
done
if [ "$backend_mode" = mock ]; then
  backend_flags+=(--env CAREERPILOT_MOCK=1)
else
  backend_flags+=(--env CAREERPILOT_MOCK=0)
fi
