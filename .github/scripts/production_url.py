"""Print the stable production address of a fresh Vercel deployment.

    VERCEL_TOKEN=... python .github/scripts/production_url.py https://x-abc.vercel.app

Each deploy gets a one-off address, while the shortest vercel.app alias of a
production deployment stays the same from one deploy to the next. The deploy
workflow uses that stable address for the live check and for linking the
search pages and the interview room to each other. When the alias cannot be
read, the one-off address is printed instead.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request


def host_of(url):
    url = url.strip()
    for prefix in ("https://", "http://"):
        if url.startswith(prefix):
            url = url[len(prefix):]
    return url.split("/", 1)[0]


def pick_alias(deployment, host):
    aliases = [a for a in deployment.get("alias") or [] if a.endswith(".vercel.app")]
    return "https://" + (min(aliases, key=len) if aliases else host)


def fetch_deployment(host, token):
    request = urllib.request.Request(
        f"https://api.vercel.com/v13/deployments/{host}",
        headers={"Authorization": f"Bearer {token}", "User-Agent": "careerpilot-deploy"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def main(argv, env, fetch=fetch_deployment):
    if len(argv) != 2:
        print("usage: production_url.py https://deployment.vercel.app", file=sys.stderr)
        return 2
    host = host_of(argv[1])
    try:
        deployment = fetch(host, env.get("VERCEL_TOKEN", ""))
    except (OSError, ValueError) as error:
        print(f"Could not read the aliases of {host}: {error}", file=sys.stderr)
        deployment = {}
    print(pick_alias(deployment, host))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv, os.environ))
