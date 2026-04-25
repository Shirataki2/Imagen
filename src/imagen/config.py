from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import tomli_w

from imagen.errors import ConfigError


def config_dir() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "imagen"


def config_path() -> Path:
    return config_dir() / "config.toml"


def user_templates_dir() -> Path:
    return config_dir() / "comfyui" / "templates"


DEFAULT_CONFIG: dict[str, Any] = {
    "default_model": "nano-banana",
    "output_dir": ".",
    "output_format": "png",
    "providers": {
        "nano_banana": {
            "model": "gemini-2.5-flash-image",
            "upgrade_on_high": True,
        },
        "chatgpt": {
            "model": "gpt-image-1",
            "output_format": "png",
            "background": "auto",
        },
        "comfyui": {
            "url": "http://127.0.0.1:8188",
            "default_template": "sdxl",
            "poll_interval_ms": 500,
            "timeout_s": 300,
        },
    },
    "aliases": {
        "nano-banana": {"provider": "nano_banana"},
        "nano-banana-pro": {
            "provider": "nano_banana",
            "model": "gemini-3-pro-image-preview",
        },
        "chatgpt": {"provider": "chatgpt"},
        "comfyui": {"provider": "comfyui"},
    },
}


@dataclass
class ResolvedAlias:
    provider: str
    overrides: dict[str, Any] = field(default_factory=dict)


@dataclass
class Config:
    data: dict[str, Any]

    @classmethod
    def load(cls) -> "Config":
        path = config_path()
        if not path.exists():
            return cls(data=_deep_copy(DEFAULT_CONFIG))
        try:
            with path.open("rb") as f:
                user = tomllib.load(f)
        except tomllib.TOMLDecodeError as exc:
            raise ConfigError(f"Failed to parse {path}: {exc}") from exc
        merged = _deep_merge(_deep_copy(DEFAULT_CONFIG), user)
        return cls(data=merged)

    @property
    def default_model(self) -> str:
        return str(self.data.get("default_model", "nano-banana"))

    @property
    def output_dir(self) -> Path:
        return Path(str(self.data.get("output_dir", "."))).expanduser()

    @property
    def output_format(self) -> str:
        return str(self.data.get("output_format", "png"))

    def provider_settings(self, provider: str) -> dict[str, Any]:
        providers = self.data.get("providers", {})
        if provider not in providers:
            raise ConfigError(f"Unknown provider: {provider}")
        return dict(providers[provider])

    def resolve_model(self, name: str) -> ResolvedAlias:
        """Map a CLI --model name to (provider, overrides)."""
        aliases = self.data.get("aliases", {})
        if name in aliases:
            entry = aliases[name]
            if isinstance(entry, str):
                return ResolvedAlias(provider=entry)
            provider = entry.get("provider")
            if not provider:
                raise ConfigError(f"Alias '{name}' missing 'provider'")
            overrides = {k: v for k, v in entry.items() if k != "provider"}
            return ResolvedAlias(provider=provider, overrides=overrides)
        # Treat as raw provider name.
        if name in self.data.get("providers", {}):
            return ResolvedAlias(provider=name)
        raise ConfigError(
            f"Unknown model/alias '{name}'. Run `imagen models` to list available."
        )

    def list_aliases(self) -> dict[str, dict[str, Any]]:
        aliases: dict[str, dict[str, Any]] = {}
        for name, entry in self.data.get("aliases", {}).items():
            if isinstance(entry, str):
                aliases[name] = {"provider": entry}
            else:
                aliases[name] = dict(entry)
        return aliases


def write_default_config(force: bool = False) -> Path:
    path = config_path()
    if path.exists() and not force:
        raise ConfigError(f"{path} already exists (use --force to overwrite)")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(tomli_w.dumps(DEFAULT_CONFIG).encode("utf-8"))
    user_templates_dir().mkdir(parents=True, exist_ok=True)
    return path


def _deep_copy(d: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in d.items():
        if isinstance(v, dict):
            out[k] = _deep_copy(v)
        else:
            out[k] = v
    return out


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            base[k] = _deep_merge(base[k], v)
        else:
            base[k] = v
    return base
