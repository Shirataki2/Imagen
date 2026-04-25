import json

from imagen.providers.base import GenerationRequest
from imagen.providers.comfyui import ComfyUIProvider


def _provider() -> ComfyUIProvider:
    return ComfyUIProvider({"default_template": "sdxl"})


def test_default_sdxl_template_renders_valid_json():
    p = _provider()
    payload = p.dry_run(
        GenerationRequest(prompt="a banana", aspect="9:16", resolution="medium", seed=7)
    )
    workflow = payload["workflow"]
    assert workflow["5"]["inputs"]["width"] > 0
    assert workflow["5"]["inputs"]["height"] > workflow["5"]["inputs"]["width"]
    assert workflow["3"]["inputs"]["seed"] == 7
    assert workflow["6"]["inputs"]["text"] == "a banana"


def test_template_var_overrides_steps_and_cfg():
    p = _provider()
    payload = p.dry_run(
        GenerationRequest(
            prompt="a banana",
            template_vars={"steps": 40, "cfg": 5.5, "checkpoint": "custom.safetensors"},
            seed=1,
        )
    )
    sampler = payload["workflow"]["3"]["inputs"]
    assert sampler["steps"] == 40
    assert sampler["cfg"] == 5.5
    assert payload["workflow"]["4"]["inputs"]["ckpt_name"] == "custom.safetensors"


def test_negative_prompt_is_json_safe():
    p = _provider()
    payload = p.dry_run(
        GenerationRequest(
            prompt='he said "hi"',
            negative_prompt='blurry, "low quality"',
            seed=2,
        )
    )
    assert payload["workflow"]["6"]["inputs"]["text"] == 'he said "hi"'
    assert (
        payload["workflow"]["7"]["inputs"]["text"]
        == 'blurry, "low quality"'
    )
    # Round-trip: payload's workflow stays JSON-serializable.
    json.dumps(payload["workflow"])
