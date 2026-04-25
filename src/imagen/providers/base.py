from __future__ import annotations

from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field


class GenerationRequest(BaseModel):
    prompt: str
    aspect: str = "1:1"
    resolution: Literal["low", "medium", "high", "auto"] = "auto"
    n: int = 1
    seed: int | None = None
    negative_prompt: str | None = None
    template: str | None = None
    template_vars: dict[str, Any] = Field(default_factory=dict)


class GeneratedImage(BaseModel):
    data: bytes
    mime: str = "image/png"
    seed: int | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class GenerationResult(BaseModel):
    images: list[GeneratedImage]
    provider: str
    model: str
    request_payload: dict[str, Any] = Field(default_factory=dict)


class Provider(Protocol):
    name: str
    model: str

    def generate(self, req: GenerationRequest) -> GenerationResult: ...

    def dry_run(self, req: GenerationRequest) -> dict[str, Any]:
        """Return the payload that would be sent, without calling the API."""
        ...
