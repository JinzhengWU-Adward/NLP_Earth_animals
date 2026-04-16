from __future__ import annotations

import json
import time
from dataclasses import dataclass

import httpx


@dataclass(frozen=True)
class DeepSeekConfig:
    api_key: str
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-chat"
    timeout_s: float = 30.0
    max_tokens: int = 700


class DeepSeekClient:
    """
    DeepSeek Chat Completions client (OpenAI-compatible).
    Docs:
    - https://api-docs.deepseek.com/api/create-chat-completion
    - https://api-docs.deepseek.com/guides/json_mode
    """

    def __init__(self, cfg: DeepSeekConfig):
        self.cfg = cfg

    def chat_json(self, *, system_prompt: str, user_prompt: str) -> dict:
        """
        Returns a parsed JSON object. Uses DeepSeek JSON mode to guarantee valid JSON.
        """
        url = self.cfg.base_url.rstrip("/") + "/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.cfg.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.cfg.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "max_tokens": self.cfg.max_tokens,
            "temperature": 0.2,
        }

        last_err: Exception | None = None
        for attempt in range(2):
            try:
                with httpx.Client(timeout=self.cfg.timeout_s) as client:
                    resp = client.post(url, headers=headers, json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                last_err = None
                break
            except Exception as e:
                last_err = e
                if attempt == 0:
                    time.sleep(0.4)
                else:
                    raise
        if last_err is not None:
            raise last_err

        content = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )
        if not content or not content.strip():
            raise RuntimeError("DeepSeek returned empty content.")

        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"DeepSeek did not return valid JSON: {e}") from e

