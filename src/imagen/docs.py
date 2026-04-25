"""Machine-readable usage doc for AI agents (`imagen docs`).

Kept separate from README so it's terse, deterministic, and easy to embed in a
prompt. Returns the same string from `imagen docs` (text) and `imagen docs --json`
(structured).
"""

from __future__ import annotations

from typing import Any

from imagen import __version__


AGENT_DOCS = f"""\
# imagen v{__version__} — agent usage

A CLI for generating images from a prompt via one of three providers.
Output: writes PNG/JPEG/WebP file(s) to disk and prints the resulting paths
(one per line) to stdout. Non-zero exit on error; error message goes to stderr.

## Synopsis

  imagen -p PROMPT [-m MODEL] [-a ASPECT] [-r RESOLUTION]
         [-o PATH] [-n N] [--seed INT] [--negative TEXT]
         [--template NAME] [--template-var KEY=VALUE]...
         [--comfy-url URL] [--dry-run] [--json] [-v]

## Models (`-m / --model`)

  nano-banana       Gemini 2.5 Flash Image (default).        env: GEMINI_API_KEY
  nano-banana-pro   Gemini 3 Pro Image.                       env: GEMINI_API_KEY
  chatgpt           OpenAI gpt-image-* family.                env: OPENAI_API_KEY
  comfyui           Local ComfyUI server, Jinja2 workflow.    config: providers.comfyui.url

  With `-r high`, `nano-banana` auto-upgrades to `nano-banana-pro` unless
  `providers.nano_banana.upgrade_on_high = false` in config.

## Aspect (`-a / --aspect`)

  Either a ratio (`1:1`, `9:16`, `16:9`, `4:3`, `3:4`, `21:9`, ...) or absolute
  pixels (`1024x1536`). Each provider receives a normalized native form:

    nano-banana   -> ImageConfig.aspect_ratio (nearest supported, e.g. "9:16")
    chatgpt       -> size in {{1024x1024, 1024x1536, 1536x1024}} (nearest)
    comfyui       -> width x height computed from `-r` target megapixels

## Resolution (`-r / --resolution`)

  low | medium | high | auto (default: auto)

  - chatgpt: passed straight through as `quality`.
  - comfyui: target pixel area: low=0.26MP, medium=1.05MP, high=1.64MP.
             Dimensions are rounded to multiples of 64.
  - nano-banana: only triggers the auto-upgrade rule above.

## Output

  Default: `./imagen_YYYYMMDD_HHMMSS.png` in the current directory. With `-n N`
  and no `-o`, files get `_1`..`_N` suffixes. With `-o PATH`:

    -o file.png      single image (or `_i` suffixed when n>1)
    -o -             write the single image bytes to stdout (requires n=1)

  Use `--json` to get a one-line JSON summary on stdout instead of paths:
    {{"provider": "...", "model": "...", "paths": [...], "count": N}}

  Use `--dry-run` to print the request payload that would be sent (JSON) and
  exit without calling any API. Useful for verification before spending tokens.

## ComfyUI templates

  Workflow JSON files with Jinja2 placeholders. Lookup order for `--template NAME`:
    1. `~/.config/imagen/comfyui/templates/<NAME>.json.j2` (user)
    2. packaged builtin (e.g. `sdxl`)

  Template variables exposed by the builtin `sdxl` template:
    prompt, negative_prompt, width, height, n, seed,
    steps (=25), cfg (=7.0), sampler (=euler), scheduler (=normal),
    checkpoint (=sd_xl_base_1.0.safetensors)

  Override any of these (or pass extras) via `--template-var KEY=VALUE`. Values
  are coerced: `true`/`false` -> bool, integers -> int, decimals -> float,
  everything else stays string.

## Subcommands

  imagen docs [--json]            this document (use --json to get a structured form)
  imagen models                   list configured `-m` aliases
  imagen config init [--force]    create ~/.config/imagen/config.toml from defaults
  imagen config show              dump resolved config as JSON
  imagen config path              print the config file path
  imagen templates ls             list available ComfyUI templates
  imagen templates show NAME      print the raw .json.j2 source
  imagen templates path           print the user-template directory path

## Examples

  # quickest: portrait via Gemini Nano Banana
  imagen -p "a banana on a plate" -m nano-banana -a 9:16

  # high quality square via OpenAI
  imagen -p "a banana on a plate" -m chatgpt -a 1:1 -r high

  # local ComfyUI with a fixed seed and tweaked sampler
  imagen -p "a banana" -m comfyui -a 16:9 -r medium --seed 42 \\
         --template-var steps=30 --template-var cfg=5.5

  # batch of 4 images to a directory
  imagen -p "..." -n 4 -o ./out/banana.png

  # pipe a single PNG to another tool
  imagen -p "..." -o - | open -f -a Preview

  # inspect what would be sent (no API call)
  imagen -p "..." -m chatgpt -a 16:9 -r medium --dry-run

## Exit codes

  0   success
  1   provider error (network, API rejection, missing key, no image returned)
  2   user error (unknown model/template, bad flag value, missing prompt)
"""


def agent_docs_text() -> str:
    return AGENT_DOCS


def agent_docs_json() -> dict[str, Any]:
    return {
        "version": __version__,
        "synopsis": (
            "imagen -p PROMPT [-m MODEL] [-a ASPECT] [-r RESOLUTION] "
            "[-o PATH] [-n N] [--seed INT] [--negative TEXT] "
            "[--template NAME] [--template-var KEY=VALUE]... "
            "[--comfy-url URL] [--dry-run] [--json] [-v]"
        ),
        "models": {
            "nano-banana": {
                "backend": "gemini-2.5-flash-image",
                "env": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
            },
            "nano-banana-pro": {
                "backend": "gemini-3-pro-image-preview",
                "env": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
            },
            "chatgpt": {
                "backend": "openai images.generate (gpt-image family)",
                "env": ["OPENAI_API_KEY"],
            },
            "comfyui": {
                "backend": "local ComfyUI HTTP API + Jinja2 workflow template",
                "env": [],
                "config": "providers.comfyui.url",
            },
        },
        "aspect": {
            "accepts": ["RATIO e.g. 1:1, 9:16, 16:9, 4:3, 3:4", "PIXELS e.g. 1024x1536"],
            "nano_banana": "nearest supported ImageConfig.aspect_ratio",
            "chatgpt": ["1024x1024", "1024x1536", "1536x1024"],
            "comfyui": "width x height computed from resolution target megapixels, rounded to /64",
        },
        "resolution": {
            "values": ["low", "medium", "high", "auto"],
            "default": "auto",
            "comfyui_target_megapixels": {"low": 0.26, "medium": 1.05, "high": 1.64},
            "chatgpt": "passed through as `quality`",
            "nano_banana": "with `high`, auto-upgrades to nano-banana-pro (unless disabled)",
        },
        "output": {
            "default_path": "./imagen_YYYYMMDD_HHMMSS.png (suffixed _1.._N when n>1)",
            "stdout": "use `-o -` (n must be 1)",
            "json_summary_flag": "--json",
            "dry_run_flag": "--dry-run",
        },
        "comfyui_templates": {
            "lookup_order": [
                "~/.config/imagen/comfyui/templates/<name>.json.j2",
                "packaged builtin (e.g. sdxl)",
            ],
            "builtin_sdxl_vars": {
                "prompt": "from CLI",
                "negative_prompt": "",
                "width": "from aspect+resolution",
                "height": "from aspect+resolution",
                "n": "from --num",
                "seed": "from --seed (random if omitted)",
                "steps": 25,
                "cfg": 7.0,
                "sampler": "euler",
                "scheduler": "normal",
                "checkpoint": "sd_xl_base_1.0.safetensors",
            },
            "override_flag": "--template-var KEY=VALUE (bool/int/float auto-coerced)",
        },
        "subcommands": {
            "imagen docs [--json]": "this document",
            "imagen models": "list configured -m aliases",
            "imagen config init|show|path": "config management",
            "imagen templates ls|show NAME|path": "ComfyUI template management",
        },
        "examples": [
            "imagen -p 'a banana on a plate' -m nano-banana -a 9:16",
            "imagen -p 'a banana' -m chatgpt -a 1:1 -r high",
            "imagen -p 'a banana' -m comfyui -a 16:9 -r medium --seed 42 --template-var steps=30",
            "imagen -p '...' -n 4 -o ./out/banana.png",
            "imagen -p '...' -o - | open -f -a Preview",
            "imagen -p '...' -m chatgpt --dry-run",
        ],
        "exit_codes": {
            "0": "success",
            "1": "provider error (network/API/missing key/no image)",
            "2": "user error (unknown model/template, bad flag, missing prompt)",
        },
    }
