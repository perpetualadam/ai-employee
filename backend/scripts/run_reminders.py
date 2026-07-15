"""Run appointment reminders — use from cron or docker scheduler service."""

from __future__ import annotations

import os
import sys
import time

import httpx


def _run_once(api_url: str, headers: dict[str, str]) -> None:
    response = httpx.post(
        f"{api_url}/api/v1/internal/reminders/run",
        headers=headers,
        timeout=120.0,
    )
    response.raise_for_status()
    data = response.json()
    print(
        f"Reminders: checked={data.get('checked')} sent={data.get('sent')}",
        flush=True,
    )


def main() -> int:
    api_url = os.environ.get("PUBLIC_API_URL", "http://localhost:8000").rstrip("/")
    secret = os.environ.get("CRON_SECRET", "")
    interval = int(os.environ.get("REMINDER_CRON_INTERVAL_SECONDS", "3600"))
    startup_retries = int(os.environ.get("REMINDER_STARTUP_RETRIES", "12"))
    startup_delay = int(os.environ.get("REMINDER_STARTUP_RETRY_SECONDS", "5"))

    headers = {}
    if secret:
        headers["X-Cron-Secret"] = secret

    while True:
        for attempt in range(startup_retries):
            try:
                _run_once(api_url, headers)
                break
            except Exception as exc:
                is_last = attempt == startup_retries - 1
                if is_last:
                    print(f"Reminder run failed: {exc}", file=sys.stderr, flush=True)
                else:
                    print(
                        f"Reminder run retry {attempt + 1}/{startup_retries}: {exc}",
                        file=sys.stderr,
                        flush=True,
                    )
                    time.sleep(startup_delay)
        time.sleep(interval)


if __name__ == "__main__":
    raise SystemExit(main())
