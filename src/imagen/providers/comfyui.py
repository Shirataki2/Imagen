from __future__ import annotations

import json
import random
import time
import uuid
from importlib import resources
from pathlib import Path
from typing import Any, Iterable

import httpx
from jinja2 import Environment, StrictUndefined, TemplateError as JinjaTemplateError

from imagen.aspect import comfyui_dimensions, parse_aspect
from imagen.config import user_templates_dir
from imagen.errors import ProviderError, TemplateError
from imagen.providers.base import (
    GeneratedImage,
    GenerationRequest,
    GenerationResult,
)


_TEMPLATE_SUFFIX = ".json.j2"


def _user_template(name: str) -> Path | None:
    p = user_templates_dir() / f"{name}{_TEMPLATE_SUFFIX}"
    return p if p.exists() else None


def _packaged_template(name: str) -> str | None:
    pkg = resources.files("imagen.templates.comfyui")
    file = pkg / f"{name}{_TEMPLATE_SUFFIX}"
    if file.is_file():
        return file.read_text(encoding="utf-8")
    return None


def list_templates() -> list[tuple[str, str]]:
    """Return [(name, source_label)] across user dir and package."""
    seen: dict[str, str] = {}
    user_dir = user_templates_dir()
    if user_dir.exists():
        for path in sorted(user_dir.glob(f"*{_TEMPLATE_SUFFIX}")):
            name = path.name[: -len(_TEMPLATE_SUFFIX)]
            seen[name] = "user"
    pkg = resources.files("imagen.templates.comfyui")
    for entry in pkg.iterdir():
        n = entry.name
        if n.endswith(_TEMPLATE_SUFFIX) and entry.is_file():
            name = n[: -len(_TEMPLATE_SUFFIX)]
            seen.setdefault(name, "builtin")
    return list(seen.items())


def load_template_source(name: str) -> str:
    user = _user_template(name)
    if user:
        return user.read_text(encoding="utf-8")
    packaged = _packaged_template(name)
    if packaged is not None:
        return packaged
    raise TemplateError(
        f"Template '{name}' not found. Run `imagen templates ls` for options."
    )


def _render_template(source: str, context: dict[str, Any]) -> str:
    env = Environment(undefined=StrictUndefined, autoescape=False)
    try:
        return env.from_string(source).render(**context)
    except JinjaTemplateError as exc:
        raise TemplateError(f"Template render failed: {exc}") from exc


class ComfyUIProvider:
    name = "comfyui"

    def __init__(self, settings: dict[str, Any]):
        self._url = str(settings.get("url", "http://127.0.0.1:8188")).rstrip("/")
        self._default_template = settings.get("default_template", "sdxl")
        self._poll_interval = float(settings.get("poll_interval_ms", 500)) / 1000
        self._timeout = float(settings.get("timeout_s", 300))

    @property
    def model(self) -> str:
        return f"comfyui:{self._default_template}"

    def _build_context(self, req: GenerationRequest) -> dict[str, Any]:
        parsed = parse_aspect(req.aspect)
        width, height = comfyui_dimensions(parsed, req.resolution)
        ctx: dict[str, Any] = {
            "prompt": req.prompt,
            "negative_prompt": req.negative_prompt or "",
            "width": width,
            "height": height,
            "n": req.n,
            "seed": req.seed
            if req.seed is not None
            else random.randint(0, 2**31 - 1),
        }
        ctx.update(req.template_vars)
        return ctx

    def _resolve_template_name(self, req: GenerationRequest) -> str:
        return req.template or self._default_template

    def _render(self, req: GenerationRequest) -> tuple[str, dict[str, Any], dict[str, Any]]:
        name = self._resolve_template_name(req)
        source = load_template_source(name)
        ctx = self._build_context(req)
        rendered = _render_template(source, ctx)
        try:
            workflow = json.loads(rendered)
        except json.JSONDecodeError as exc:
            raise TemplateError(
                f"Rendered template '{name}' is not valid JSON: {exc}"
            ) from exc
        return name, ctx, workflow

    def dry_run(self, req: GenerationRequest) -> dict[str, Any]:
        name, ctx, workflow = self._render(req)
        return {
            "url": self._url,
            "template": name,
            "context": ctx,
            "workflow": workflow,
        }

    def generate(self, req: GenerationRequest) -> GenerationResult:
        name, ctx, workflow = self._render(req)
        client_id = str(uuid.uuid4())
        with httpx.Client(timeout=self._timeout) as client:
            try:
                resp = client.post(
                    f"{self._url}/prompt",
                    json={"prompt": workflow, "client_id": client_id},
                )
                resp.raise_for_status()
            except httpx.HTTPError as exc:
                raise ProviderError(f"ComfyUI POST /prompt failed: {exc}") from exc
            body = resp.json()
            prompt_id = body.get("prompt_id")
            node_errors = body.get("node_errors") or {}
            if not prompt_id:
                raise ProviderError(
                    f"ComfyUI did not return prompt_id; node_errors={node_errors}"
                )

            history = self._wait_history(client, prompt_id)
            outputs = history.get("outputs", {})
            files = list(_iter_output_files(outputs))
            if not files:
                raise ProviderError(
                    f"ComfyUI prompt {prompt_id} produced no SaveImage output"
                )
            images: list[GeneratedImage] = []
            for filename, subfolder, type_ in files:
                img_resp = client.get(
                    f"{self._url}/view",
                    params={"filename": filename, "subfolder": subfolder, "type": type_},
                )
                img_resp.raise_for_status()
                images.append(
                    GeneratedImage(
                        data=img_resp.content,
                        mime=_mime_for(filename),
                        seed=ctx.get("seed"),
                        extra={"filename": filename, "subfolder": subfolder},
                    )
                )

        return GenerationResult(
            images=images,
            provider=self.name,
            model=f"comfyui:{name}",
            request_payload={"template": name, "context": ctx, "workflow": workflow},
        )

    def _wait_history(self, client: httpx.Client, prompt_id: str) -> dict[str, Any]:
        deadline = time.monotonic() + self._timeout
        while True:
            try:
                resp = client.get(f"{self._url}/history/{prompt_id}")
                resp.raise_for_status()
            except httpx.HTTPError as exc:
                raise ProviderError(f"ComfyUI GET /history failed: {exc}") from exc
            data = resp.json()
            entry = data.get(prompt_id)
            if entry and entry.get("outputs"):
                return entry
            if time.monotonic() >= deadline:
                raise ProviderError(
                    f"ComfyUI timed out waiting for prompt {prompt_id}"
                )
            time.sleep(self._poll_interval)


def _iter_output_files(
    outputs: dict[str, Any],
) -> Iterable[tuple[str, str, str]]:
    for node_output in outputs.values():
        for image in node_output.get("images", []) or []:
            yield (
                image.get("filename", ""),
                image.get("subfolder", ""),
                image.get("type", "output"),
            )


def _mime_for(filename: str) -> str:
    lower = filename.lower()
    if lower.endswith(".jpg") or lower.endswith(".jpeg"):
        return "image/jpeg"
    if lower.endswith(".webp"):
        return "image/webp"
    return "image/png"
