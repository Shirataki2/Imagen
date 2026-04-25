from __future__ import annotations

import os
from typing import Any

from imagen.aspect import gemini_aspect, parse_aspect
from imagen.errors import ProviderError
from imagen.providers.base import (
    GeneratedImage,
    GenerationRequest,
    GenerationResult,
)


class NanoBananaProvider:
    name = "nano_banana"

    def __init__(self, settings: dict[str, Any]):
        self._base_model = settings.get("model", "gemini-2.5-flash-image")
        self._pro_model = settings.get(
            "pro_model", "gemini-3-pro-image-preview"
        )
        self._upgrade_on_high = bool(settings.get("upgrade_on_high", True))

    @property
    def model(self) -> str:
        # Reported after generate(); placeholder for dry-run before resolve.
        return self._base_model

    def _resolve_model(self, req: GenerationRequest) -> str:
        if req.resolution == "high" and self._upgrade_on_high:
            return self._pro_model
        return self._base_model

    def _payload(self, req: GenerationRequest) -> dict[str, Any]:
        aspect = gemini_aspect(parse_aspect(req.aspect))
        return {
            "model": self._resolve_model(req),
            "contents": req.prompt,
            "config": {
                "response_modalities": ["IMAGE"],
                "image_config": {"aspect_ratio": aspect},
            },
        }

    def dry_run(self, req: GenerationRequest) -> dict[str, Any]:
        return self._payload(req)

    def generate(self, req: GenerationRequest) -> GenerationResult:
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get(
            "GOOGLE_API_KEY"
        )
        if not api_key:
            raise ProviderError(
                "GEMINI_API_KEY (or GOOGLE_API_KEY) must be set"
            )
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise ProviderError(
                "google-genai is not installed. Run `uv pip install google-genai`."
            ) from exc

        payload = self._payload(req)
        client = genai.Client(api_key=api_key)
        config = types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            image_config=types.ImageConfig(
                aspect_ratio=payload["config"]["image_config"]["aspect_ratio"]
            ),
        )

        images: list[GeneratedImage] = []
        # Gemini's generate_content returns multiple parts when n>1 not supported
        # uniformly; loop to honor req.n.
        for _ in range(max(1, req.n)):
            response = client.models.generate_content(
                model=payload["model"],
                contents=req.prompt,
                config=config,
            )
            for part in getattr(response, "parts", []) or []:
                inline = getattr(part, "inline_data", None)
                if inline is None:
                    continue
                data = getattr(inline, "data", None)
                mime = getattr(inline, "mime_type", "image/png") or "image/png"
                if not data:
                    continue
                images.append(GeneratedImage(data=data, mime=mime))

        if not images:
            raise ProviderError(
                "Nano Banana returned no image data (check safety filters / prompt)."
            )

        return GenerationResult(
            images=images,
            provider=self.name,
            model=payload["model"],
            request_payload=payload,
        )
