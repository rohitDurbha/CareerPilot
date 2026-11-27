#!/usr/bin/env bash
# Commit a built site to the gh-pages branch, which GitHub Pages serves.
#
#   publish_gh_pages.sh DIRECTORY
#
# Needs GH_TOKEN (the workflow's GITHUB_TOKEN with contents: write) and the
# standard GITHUB_REPOSITORY and GITHUB_SHA variables. The branch keeps its
# history, so every publish is one new commit on top and nothing is forced.
# Tests set GH_PAGES_REMOTE to a local repository instead.
set -euo pipefail

site=$(cd "${1:?usage: publish_gh_pages.sh DIRECTORY}" && pwd)
remote="${GH_PAGES_REMOTE:-https://x-access-token:${GH_TOKEN}@github.com/${GITHUB_REPOSITORY}.git}"
work=$(mktemp -d)

if git ls-remote --exit-code --heads "$remote" gh-pages >/dev/null 2>&1; then
  git clone --quiet --depth 1 --branch gh-pages "$remote" "$work"
else
  git init --quiet --initial-branch gh-pages "$work"
fi

cd "$work"
find . -mindepth 1 -maxdepth 1 ! -name .git -exec rm -rf {} +
cp -R "$site"/. .
# Stamp the source commit so the live check can tell the new copy is served.
printf '\n// Built from %s\n' "$GITHUB_SHA" >> settings.js

git add -A
if git diff --cached --quiet; then
  echo "The gh-pages branch already has this build"
  exit 0
fi
git -c user.name="Rohit Durbha" -c user.email="rohitdurbha@gmail.com" \
  commit --quiet -m "Publish the static demo built from ${GITHUB_SHA:0:7}"
git push --quiet "$remote" HEAD:gh-pages
echo "Published $(git rev-parse --short HEAD) to gh-pages"
