from __future__ import annotations

import httpx


def create_client() -> httpx.Client:
    return httpx.Client(
        follow_redirects=True,
        timeout=httpx.Timeout(45.0),
        headers={
            "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
            "User-Agent": "API-Price-Watch/1.0 (+GitHub Actions; public pricing monitor)",
        },
    )
