from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import typer

from imagen import __version__
from imagen.config import Config, config_path, write_default_config
from imagen.errors import ImagenError
from imagen.output import write_images
from imagen.providers import get_provider
from imagen.providers.base import GenerationRequest

app = typer.Typer(
    add_completion=False,
    help="Multi-provider image generation CLI",
    no_args_is_help=True,
)
config_app = typer.Typer(help="Configuration management")
templates_app = typer.Typer(help="ComfyUI template management")
app.add_typer(config_app, name="config")
app.add_typer(templates_app, name="templates")


def _parse_template_vars(values: list[str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for entry in values:
        if "=" not in entry:
            raise typer.BadParameter(f"--template-var '{entry}' must be KEY=VALUE")
        key, val = entry.split("=", 1)
        out[key.strip()] = _coerce(val.strip())
    return out


def _coerce(value: str) -> Any:
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value


@app.callback(invoke_without_command=True)
def root(
    ctx: typer.Context,
    prompt: str = typer.Option(
        None, "-p", "--prompt", help="Prompt text. Use '-' for stdin."
    ),
    model: str = typer.Option(
        None,
        "-m",
        "--model",
        help="Model alias (nano-banana, nano-banana-pro, chatgpt, comfyui).",
    ),
    aspect: str = typer.Option(
        "1:1", "-a", "--aspect", help="Aspect ratio (e.g. 9:16) or pixels (1024x1536)."
    ),
    resolution: str = typer.Option(
        "auto", "-r", "--resolution", help="low | medium | high | auto"
    ),
    output: str = typer.Option(
        None,
        "-o",
        "--output",
        help="Output file path. '-' for stdout. Default: cwd timestamped.",
    ),
    n: int = typer.Option(1, "-n", "--num", help="Number of images."),
    seed: int = typer.Option(None, "--seed", help="Seed (where supported)."),
    negative: str = typer.Option(None, "--negative", help="Negative prompt (ComfyUI)."),
    template: str = typer.Option(None, "--template", help="ComfyUI template name."),
    template_var: list[str] = typer.Option(
        [], "--template-var", help="Template variable KEY=VALUE (repeatable)."
    ),
    comfy_url: str = typer.Option(
        None, "--comfy-url", help="Override ComfyUI server URL."
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print payload, no API call."),
    output_json: bool = typer.Option(
        False, "--json", help="Emit a JSON summary on stdout."
    ),
    verbose: bool = typer.Option(False, "-v", "--verbose"),
    version: bool = typer.Option(False, "--version", is_eager=True),
) -> None:
    if version:
        typer.echo(f"imagen {__version__}")
        raise typer.Exit()
    if ctx.invoked_subcommand is not None:
        return
    if prompt is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()

    cfg = Config.load()
    if prompt == "-":
        prompt_text = sys.stdin.read().strip()
        if not prompt_text:
            raise typer.BadParameter("empty prompt from stdin")
    else:
        prompt_text = prompt

    model_name = model or cfg.default_model
    try:
        alias = cfg.resolve_model(model_name)
        if comfy_url and alias.provider == "comfyui":
            alias.overrides["url"] = comfy_url
        provider = get_provider(alias, cfg)
    except ImagenError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(2) from exc

    template_vars = _parse_template_vars(template_var)
    req = GenerationRequest(
        prompt=prompt_text,
        aspect=aspect,
        resolution=resolution,  # type: ignore[arg-type]
        n=n,
        seed=seed,
        negative_prompt=negative,
        template=template,
        template_vars=template_vars,
    )

    try:
        if dry_run:
            payload = provider.dry_run(req)
            typer.echo(json.dumps(payload, indent=2, ensure_ascii=False, default=str))
            return

        if verbose:
            typer.secho(
                f"-> provider={alias.provider} model={provider.model}",
                fg=typer.colors.CYAN,
                err=True,
            )

        result = provider.generate(req)
        paths = write_images(result.images, output, output_dir=cfg.output_dir)

        if output_json:
            typer.echo(
                json.dumps(
                    {
                        "provider": result.provider,
                        "model": result.model,
                        "paths": [str(p) for p in paths],
                        "count": len(result.images),
                    },
                    ensure_ascii=False,
                )
            )
        else:
            for p in paths:
                typer.echo(str(p))
    except ImagenError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from exc


@config_app.command("init")
def config_init(
    force: bool = typer.Option(False, "--force", help="Overwrite if exists."),
) -> None:
    """Write the default config to ~/.config/imagen/config.toml."""
    try:
        path = write_default_config(force=force)
    except ImagenError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from exc
    typer.echo(f"Wrote {path}")


@config_app.command("show")
def config_show() -> None:
    """Print resolved config (defaults merged with user overrides)."""
    cfg = Config.load()
    typer.echo(json.dumps(cfg.data, indent=2, ensure_ascii=False))


@config_app.command("path")
def config_show_path() -> None:
    typer.echo(str(config_path()))


@app.command()
def models() -> None:
    """List configured aliases."""
    cfg = Config.load()
    for name, entry in cfg.list_aliases().items():
        typer.echo(f"{name}\t{entry}")


@app.command()
def docs(
    output_json: bool = typer.Option(
        False, "--json", help="Emit a structured JSON document instead of text."
    ),
) -> None:
    """Print agent-friendly usage docs (text or JSON)."""
    from imagen.docs import agent_docs_json, agent_docs_text

    if output_json:
        typer.echo(json.dumps(agent_docs_json(), indent=2, ensure_ascii=False))
    else:
        typer.echo(agent_docs_text())


@templates_app.command("ls")
def templates_ls() -> None:
    from imagen.providers.comfyui import list_templates

    for name, source in list_templates():
        typer.echo(f"{name}\t({source})")


@templates_app.command("show")
def templates_show(name: str) -> None:
    from imagen.providers.comfyui import load_template_source

    typer.echo(load_template_source(name))


@templates_app.command("path")
def templates_show_path() -> None:
    from imagen.config import user_templates_dir

    typer.echo(str(user_templates_dir()))


def main() -> None:  # pragma: no cover
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
