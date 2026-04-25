class ImagenError(Exception):
    """Base error."""


class ConfigError(ImagenError):
    pass


class ProviderError(ImagenError):
    pass


class TemplateError(ImagenError):
    pass
