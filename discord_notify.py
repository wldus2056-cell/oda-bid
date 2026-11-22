from __future__ import annotations

import time

import requests


def send_discord(
    webhook_url: str,
    content: str | None = None,
    embeds: list[dict] | None = None,
):
    payload = {}
    if content:
        payload["content"] = content
    if embeds:
        payload["embeds"] = embeds

    for attempt in range(3):
        response = requests.post(webhook_url, json=payload, timeout=30)
        if response.status_code == 429:
            try:
                retry_after = float(response.json().get("retry_after", 1))
            except (ValueError, TypeError):
                retry_after = 1
            time.sleep(max(retry_after, 0.1))
            continue
        if response.status_code >= 500 and attempt < 2:
            time.sleep(2**attempt)
            continue
        response.raise_for_status()
        return

    response.raise_for_status()
