#!/usr/bin/env bash
# Deploy one folder to its own Vercel project and print its stable address.
#
#   .github/scripts/vercel_deploy.sh <folder> <project> [extra vercel deploy flags]
#
# Creates the project on the first run, links the folder to it by name so no
# other Vercel project is touched, deploys to production with up to three
# attempts, and prints the shortest vercel.app alias on the last line of
# stdout. Progress goes to stderr. Needs VERCEL_TOKEN in the environment.
set -euo pipefail

folder=$1
project=$2
shift 2
vercel=(npx --yes vercel@63.1.0)
scripts=$(cd "$(dirname "$0")" && pwd)

if [ -z "${VERCEL_TOKEN:-}" ]; then
  echo "VERCEL_TOKEN is not set" >&2
  exit 1
fi

output=$(mktemp)
cd "$folder"
# Creating the project fails harmlessly once it exists.
"${vercel[@]}" project add "$project" --token "$VERCEL_TOKEN" >&2 || true
"${vercel[@]}" link --yes --project "$project" --token "$VERCEL_TOKEN" >&2

for attempt in 1 2 3; do
  if "${vercel[@]}" deploy --prod --yes --token "$VERCEL_TOKEN" "$@" > "$output"; then
    break
  fi
  if [ "$attempt" = 3 ]; then exit 1; fi
  sleep 15
done
deployment=$(tail -n 1 "$output")
rm -f "$output"
echo "Deployed $project to $deployment" >&2
python "$scripts/production_url.py" "$deployment"
