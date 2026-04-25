from __future__ import annotations

import base64
import os
from typing import Any

from imagen.aspect import openai_size, parse_aspect
from imagen.errors import ProviderError
from imagen.providers.base import (
    GeneratedImage,
    GenerationRequest,
    GenerationResult,
)


_MIME_BY_FORMAT = {
    "png": "image/png",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
}


class ChatGPTProvider:
    name = "chatgpt"

    def __init__(self, settings: dict[str, Any]):
        self._model = settings.get("model", "gpt-image-2")
        self._output_format = settings.get("output_format", "png")
        self._background = settings.get("background", "auto")

    @property
    def model(self) -> str:
        return self._model

    def _payload(self, req: GenerationRequest) -> dict[str, Any]:
        size = openai_size(parse_aspect(req.aspect))
        quality = req.resolution if req.resolution != "auto" else "auto"
        payload: dict[str, Any] = {
            "model": self._model,
            "prompt": req.prompt,
            "size": size,
            "quality": quality,
            "n": req.n,
            "output_format": self._output_format,
        }
        if self._background and self._background != "auto":
            payload["background"] = self._background
        return payload

    def dry_run(self, req: GenerationRequest) -> dict[str, Any]:
        return self._payload(req)

    def generate(self, req: GenerationRequest) -> GenerationResult:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ProviderError("OPENAI_API_KEY must be set")
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ProviderError(
                "openai is not installed. Run `uv pip install openai`."
            ) from exc

        payload = self._payload(req)
        client = OpenAI(api_key=api_key)
        response = client.images.generate(**payload)

        mime = _MIME_BY_FORMAT.get(self._output_format, "image/png")
        images: list[GeneratedImage] = []
        for item in response.data or []:
            b64 = getattr(item, "b64_json", None)
            if not b64:
                raise ProviderError(
                    "OpenAI response missing b64_json (unexpected for gpt-image-*)"
                )
            images.append(GeneratedImage(data=base64.b64decode(b64), mime=mime))

        if not images:
            raise ProviderError("OpenAI returned no images")

        return GenerationResult(
            images=images,
            provider=self.name,
            model=self._model,
            request_payload=payload,
        )
