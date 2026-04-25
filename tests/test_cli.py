import json

from typer.testing import CliRunner

from imagen.cli import app

runner = CliRunner()


def test_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Multi-provider image generation CLI" in result.stdout


def test_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "imagen" in result.stdout


def test_models_lists_aliases():
    result = runner.invoke(app, ["models"])
    assert result.exit_code == 0
    assert "nano-banana" in result.stdout
    assert "chatgpt" in result.stdout
    assert "comfyui" in result.stdout


def test_dry_run_nano_banana_json():
    result = runner.invoke(
        app,
        ["-p", "hi", "-m", "nano-banana", "-a", "9:16", "-r", "high", "--dry-run"],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["model"] == "gemini-3-pro-image-preview"  # auto-upgrade
    assert payload["config"]["image_config"]["aspect_ratio"] == "9:16"


def test_dry_run_chatgpt_size_quality():
    result = runner.invoke(
        app,
        ["-p", "hi", "-m", "chatgpt", "-a", "16:9", "-r", "low", "--dry-run"],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["size"] == "1536x1024"
    assert payload["quality"] == "low"


def test_dry_run_comfyui_renders_workflow():
    result = runner.invoke(
        app,
        [
            "-p",
            "hi",
            "-m",
            "comfyui",
            "--template",
            "sdxl",
            "-a",
            "1:1",
            "-r",
            "medium",
            "--seed",
            "1",
            "--dry-run",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["template"] == "sdxl"
    assert payload["workflow"]["5"]["inputs"]["width"] == 1024
    assert payload["workflow"]["5"]["inputs"]["height"] == 1024


def test_template_var_typed_coercion():
    result = runner.invoke(
        app,
        [
            "-p",
            "hi",
            "-m",
            "comfyui",
            "--template",
            "sdxl",
            "--seed",
            "1",
            "--template-var",
            "steps=30",
            "--template-var",
            "cfg=4.5",
            "--dry-run",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    sampler = payload["workflow"]["3"]["inputs"]
    assert sampler["steps"] == 30
    assert sampler["cfg"] == 4.5


def test_docs_text_contains_synopsis():
    result = runner.invoke(app, ["docs"])
    assert result.exit_code == 0, result.output
    assert "imagen -p PROMPT" in result.stdout
    assert "nano-banana" in result.stdout
    assert "comfyui" in result.stdout
    assert "--dry-run" in result.stdout


def test_docs_json_is_structured():
    result = runner.invoke(app, ["docs", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert "models" in payload and "nano-banana" in payload["models"]
    assert payload["resolution"]["values"] == ["low", "medium", "high", "auto"]
    assert "exit_codes" in payload


def test_unknown_model_errors():
    result = runner.invoke(app, ["-p", "hi", "-m", "no-such", "--dry-run"])
    assert result.exit_code != 0
    assert "Unknown model" in (result.stderr or result.output)
