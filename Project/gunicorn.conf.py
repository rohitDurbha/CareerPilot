"""Gunicorn settings for hosting the CareerPilot backend.

Run from the Project folder with ``gunicorn backend:app``. Gunicorn picks this
file up on its own and listens on the PORT variable that hosts such as
Hugging Face Spaces and Render provide, falling back to 5001 locally.
"""

import os

bind = f"0.0.0.0:{os.environ.get('PORT', '').strip() or '5001'}"

# One worker keeps the interview agent process handles in a single place, so
# /run_agents and /cancel_file1 always see the same processes. Threads still
# let several requests run at once while one waits on a webhook.
workers = 1
threads = int(os.environ.get("GUNICORN_THREADS", "4"))

# The resume match webhook can take a while to answer.
timeout = int(os.environ.get("GUNICORN_TIMEOUT", "120"))

accesslog = "-"
errorlog = "-"
