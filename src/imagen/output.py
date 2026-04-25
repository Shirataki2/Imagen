from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

from imagen.providers.base import GeneratedImage

_EXT_BY_MIME = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
}


def _ext_for(image: GeneratedImage) -> str:
    return _EXT_BY_MIME.get(image.mime, ".png")


def write_images(
    images: list[GeneratedImage],
    output: str | None,
    *,
    output_dir: Path,
    now: datetime | None = None,
) -> list[Path]:
    """Write images according to CLI rules.

    - output == "-": write the first image to stdout (binary), error if n>1.
    - output is a path: when n==1, write directly. When n>1, append _1.. _n
      before the extension.
    - output is None: write to ``output_dir/imagen_YYYYMMDD_HHMMSS[_n]<ext>``.
    """
    if output == "-":
        if len(images) != 1:
            raise ValueError("stdout output requires exactly one image (use -n 1)")
        sys.stdout.buffer.write(images[0].data)
        sys.stdout.buffer.flush()
        return []

    if output is not None:
        target = Path(output).expanduser()
        if len(images) == 1:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(images[0].data)
            return [target]
        return _write_numbered(images, target)

    ts = (now or datetime.now()).strftime("%Y%m%d_%H%M%S")
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for i, img in enumerate(images, start=1):
        suffix = f"_{i}" if len(images) > 1 else ""
        path = output_dir / f"imagen_{ts}{suffix}{_ext_for(img)}"
        path.write_bytes(img.data)
        paths.append(path)
    return paths


def _write_numbered(images: list[GeneratedImage], base: Path) -> list[Path]:
    base.parent.mkdir(parents=True, exist_ok=True)
    stem, ext = base.stem, base.suffix or _ext_for(images[0])
    paths: list[Path] = []
    for i, img in enumerate(images, start=1):
        path = base.with_name(f"{stem}_{i}{ext}")
        path.write_bytes(img.data)
        paths.append(path)
    return paths
