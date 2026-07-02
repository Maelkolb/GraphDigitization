"""Gemini client wrapper: typed structured output with a schema-validation retry loop.

Ports HistOrniGraph's region-detector patterns (JSON retry, fence cleaning) and upgrades
them for Gemini 3.x: `response_schema` typed output instead of prose parsing, `thinking_level`
instead of temperature knobs (temperature/top_p/top_k are deliberately never set).
"""

from __future__ import annotations

import io
import json
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TypeVar

from PIL import Image
from pydantic import BaseModel, ValidationError

from graphdig.config import GeminiConfig

TModel = TypeVar("TModel", bound=BaseModel)

MIME_BY_EXT = {
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
    ".webp": "image/webp", ".tif": "image/tiff", ".tiff": "image/tiff",
}

_MEDIA_RESOLUTION = {
    "low": "MEDIA_RESOLUTION_LOW",
    "medium": "MEDIA_RESOLUTION_MEDIUM",
    "high": "MEDIA_RESOLUTION_HIGH",
    # the generativelanguage v1beta API rejects ULTRA_HIGH (400); cap at HIGH
    "ultra_high": "MEDIA_RESOLUTION_HIGH",
}


class GeminiUnavailable(RuntimeError):
    """Raised when no API key is configured."""


def clean_llm_json(text: str) -> str:
    """Strip markdown fences and leading chatter around a JSON payload."""
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    start = min((i for i in (text.find("{"), text.find("[")) if i >= 0), default=0)
    return text[start:]


@dataclass
class GeminiResult[TModel: BaseModel]:
    data: TModel | None
    raw_text: str = ""
    attempts: int = 1
    usage: dict[str, int] = field(default_factory=dict)
    error: str | None = None
    prompt_id: str = ""
    model: str = ""
    thinking_level: str = ""

    @property
    def ok(self) -> bool:
        return self.data is not None


def _image_part(image: Path | str | Image.Image):
    from google.genai import types

    if isinstance(image, Image.Image):
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        return types.Part.from_bytes(data=buf.getvalue(), mime_type="image/png")
    path = Path(image)
    mime = MIME_BY_EXT.get(path.suffix.lower())
    data = path.read_bytes()
    if mime is None or mime == "image/tiff":  # normalize exotic formats to PNG
        buf = io.BytesIO()
        Image.open(io.BytesIO(data)).save(buf, format="PNG")
        data, mime = buf.getvalue(), "image/png"
    return types.Part.from_bytes(data=data, mime_type=mime)


def _usage_dict(resp) -> dict[str, int]:
    meta = getattr(resp, "usage_metadata", None)
    if meta is None:
        return {}
    out = {}
    for key in ("prompt_token_count", "candidates_token_count",
                "thoughts_token_count", "total_token_count"):
        val = getattr(meta, key, None)
        if isinstance(val, int):
            out[key] = val
    return out


class GeminiClient:
    """Thin wrapper around google-genai; the only place that talks to the API."""

    def __init__(self, cfg: GeminiConfig | None = None, api_key: str | None = None):
        from dotenv import load_dotenv

        load_dotenv()
        self.cfg = cfg or GeminiConfig()
        key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not key:
            raise GeminiUnavailable(
                "No GEMINI_API_KEY / GOOGLE_API_KEY found. Copy .env.example to .env "
                "and add your key, or export it in the environment."
            )
        from google import genai

        self._client = genai.Client(api_key=key)

    def generate_json(self, *, images: list[Path | str | Image.Image], prompt: str,
                      schema: type[TModel], prompt_id: str,
                      thinking_level: str = "medium",
                      media_resolution: str | None = None) -> GeminiResult[TModel]:
        """One structured-output call: images first, instruction last (Gemini 3 guidance).

        Retries on schema/JSON failures up to cfg.retries times; transient API errors get
        one backoff retry each. Never raises for content problems - inspect `result.error`.
        """
        from google.genai import types

        contents = [_image_part(img) for img in images] + [prompt]
        config_kwargs: dict = {
            "response_mime_type": "application/json",
            "response_schema": schema,
            "max_output_tokens": self.cfg.max_output_tokens,
            "thinking_config": types.ThinkingConfig(thinking_level=thinking_level),
        }
        if media_resolution:
            config_kwargs["media_resolution"] = _MEDIA_RESOLUTION.get(
                media_resolution, media_resolution)

        last_error = ""
        raw_text = ""
        attempts = 0
        usage: dict[str, int] = {}
        for attempt in range(self.cfg.retries + 1):
            attempts = attempt + 1
            try:
                resp = self._client.models.generate_content(
                    model=self.cfg.model_id, contents=contents,
                    config=types.GenerateContentConfig(**config_kwargs),
                )
            except (TypeError, ValueError) as exc:
                # e.g. SDK/backend rejecting media_resolution: drop it once and retry
                if "media_resolution" in config_kwargs and "media_resolution" in str(exc):
                    config_kwargs.pop("media_resolution")
                    continue
                last_error = f"request error: {exc}"
                break
            except Exception as exc:  # transient API/network errors
                if "media_resolution" in str(exc) and "media_resolution" in config_kwargs:
                    config_kwargs.pop("media_resolution")  # backend rejected the enum
                    continue
                last_error = f"api error: {exc}"
                time.sleep(2.0 * (attempt + 1))
                continue

            usage = _usage_dict(resp)
            raw_text = resp.text or ""
            parsed = getattr(resp, "parsed", None)
            if isinstance(parsed, schema):
                return GeminiResult(data=parsed, raw_text=raw_text, attempts=attempts,
                                    usage=usage, prompt_id=prompt_id,
                                    model=self.cfg.model_id, thinking_level=thinking_level)
            try:  # fall back to manual parse of the raw text
                data = schema.model_validate(json.loads(clean_llm_json(raw_text)))
                return GeminiResult(data=data, raw_text=raw_text, attempts=attempts,
                                    usage=usage, prompt_id=prompt_id,
                                    model=self.cfg.model_id, thinking_level=thinking_level)
            except (json.JSONDecodeError, ValidationError) as exc:
                last_error = f"schema error: {exc}"
                continue

        return GeminiResult(data=None, raw_text=raw_text, attempts=attempts, usage=usage,
                            error=last_error or "exhausted retries", prompt_id=prompt_id,
                            model=self.cfg.model_id, thinking_level=thinking_level)
