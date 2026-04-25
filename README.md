# imagen

ローカル CLI から Gemini Nano Banana / OpenAI gpt-image / 自前の ComfyUI を共通インターフェースで叩いて画像を生成するツール。

```
imagen -p "プロンプト" --model nano-banana --aspect 9:16 --resolution high
```

## サポートしているプロバイダ

| `--model` | 実体 | API キー / URL |
| --- | --- | --- |
| `nano-banana` | `gemini-2.5-flash-image` (Gemini Nano Banana) | `GEMINI_API_KEY` または `GOOGLE_API_KEY` |
| `nano-banana-pro` | `gemini-3-pro-image-preview` (Nano Banana Pro) | 同上 |
| `chatgpt` | OpenAI `gpt-image-1` 系（config で `gpt-image-1.5` 等に切替可） | `OPENAI_API_KEY` |
| `comfyui` | ローカル ComfyUI を Jinja2 ワークフローテンプレで駆動 | config の `providers.comfyui.url` |

`--resolution high` を指定すると `nano-banana` は自動で Pro モデルへ切り替わります（`upgrade_on_high = false` で無効化可）。

## インストール

```bash
git clone <this repo> ~/projects/imagen
cd ~/projects/imagen
uv tool install .
imagen config init                 # ~/.config/imagen/config.toml を生成
export GEMINI_API_KEY=...
export OPENAI_API_KEY=...
```

## 使い方

```bash
# Gemini Nano Banana (縦長)
imagen -p "a banana on a plate" -m nano-banana -a 9:16

# OpenAI gpt-image-1 (横長 / 低品質ドラフト)
imagen -p "a banana on a plate" -m chatgpt -a 16:9 -r low

# ComfyUI (ローカル / シード固定)
imagen -p "a banana on a plate" -m comfyui -a 1:1 -r medium --seed 42

# テンプレート変数の上書き
imagen -p "..." -m comfyui --template-var steps=40 --template-var cfg=5.5

# 出力先指定 / 連番
imagen -p "..." -n 4 -o ./out/banana.png

# パイプ向け (1 枚を stdout)
imagen -p "..." -o - > banana.png

# API を叩かずに送信ペイロードを確認
imagen -p "..." -m chatgpt --dry-run
```

その他コマンド:

```bash
imagen models                  # 利用可能な --model エイリアス一覧
imagen config show             # 解決済み設定を JSON でダンプ
imagen config path             # config.toml のパス
imagen templates ls            # ComfyUI テンプレ一覧 (組み込み + ユーザ定義)
imagen templates show sdxl     # テンプレ本文を表示
imagen templates path          # ユーザテンプレ置き場のパス
```

## ComfyUI テンプレート

`imagen templates path` のディレクトリ（既定 `~/.config/imagen/comfyui/templates/`）に `<name>.json.j2` を置けば `--template <name>` で使えます。組み込みの `sdxl` テンプレートが露出する変数:

| 変数 | 既定値 |
| --- | --- |
| `prompt` | (CLI から) |
| `negative_prompt` | `""` |
| `width` / `height` | `--aspect` × `--resolution` から算出 |
| `seed` | `--seed` 未指定時は乱数 |
| `n` | `--num` |
| `steps` | `25` |
| `cfg` | `7.0` |
| `sampler` | `euler` |
| `scheduler` | `normal` |
| `checkpoint` | `sd_xl_base_1.0.safetensors` |

これら以外の値は `--template-var KEY=VALUE` で渡せます（int / float / bool は自動コアース）。

新しいワークフローを使いたいときは ComfyUI の "Save (API Format)" でエクスポートした JSON に Jinja2 プレースホルダを差し込んで保存するだけです。

## 設定

`~/.config/imagen/config.toml` のサンプル:

```toml
default_model = "nano-banana"
output_dir = "."
output_format = "png"

[providers.nano_banana]
model = "gemini-2.5-flash-image"
upgrade_on_high = true

[providers.chatgpt]
model = "gpt-image-1"
output_format = "png"
background = "auto"

[providers.comfyui]
url = "http://127.0.0.1:8188"
default_template = "sdxl"
poll_interval_ms = 500
timeout_s = 300

[aliases]
nano-banana       = { provider = "nano_banana" }
nano-banana-pro   = { provider = "nano_banana", model = "gemini-3-pro-image-preview" }
chatgpt           = { provider = "chatgpt" }
comfyui           = { provider = "comfyui" }
```

API キーは設定ファイルには書かず、環境変数のみで扱います。

## 開発

```bash
uv venv --python 3.13
uv pip install -e ".[dev]"
.venv/bin/pytest
```
