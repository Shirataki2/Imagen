from __future__ import annotations

from imagen.config import Config, ResolvedAlias
from imagen.errors import ProviderError
from imagen.providers.base import Provider


def get_provider(alias: ResolvedAlias, config: Config) -> Provider:
    name = alias.provider
    settings = config.provider_settings(name)
    settings.update(alias.overrides)
    if name == "nano_banana":
        from imagen.providers.nano_banana import NanoBananaProvider

        return NanoBananaProvider(settings)
    if name == "chatgpt":
        from imagen.providers.chatgpt import ChatGPTProvider

        return ChatGPTProvider(settings)
    if name == "comfyui":
        from imagen.providers.comfyui import ComfyUIProvider

        return ComfyUIProvider(settings)
    raise ProviderError(f"Unknown provider '{name}'")
