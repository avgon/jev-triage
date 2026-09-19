"""Core Jev client — zero dependencies."""

from __future__ import annotations

import json
import os
import ssl
import urllib.request
from typing import Any


class JevClient:
    """Minimal TypeSafe Jev client using only stdlib."""

    DEFAULT_URL = "https://api.typesafe.ai/v1/systemone"

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str = "jev-latest",
    ):
        self.api_key = (
            api_key
            or os.getenv("TYPESAFE_API_KEY")
            or os.getenv("OPENROUTER_API_KEY", "")
        )
        if not self.api_key:
            raise ValueError("Set TYPESAFE_API_KEY or pass api_key=")
        self.base_url = base_url or self.DEFAULT_URL
        self.model = model
        self._ctx = ssl.create_default_context()

    def ask(
        self,
        state: str,
        questions: dict[str, dict[str, Any]],
        *,
        timeout: int = 30,
    ) -> dict[str, Any]:
        payload = json.dumps(
            {"model": self.model, "state": state, "questions": questions}
        ).encode()
        req = urllib.request.Request(
            self.base_url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout, context=self._ctx) as resp:
            return json.loads(resp.read().decode()).get("answers", {})
