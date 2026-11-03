import warnings
from io import BytesIO

from fastapi import UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_DIMENSION = 2048
MAX_PIXELS = 40_000_000
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}


class ImageProcessingError(Exception):
    def __init__(self, message: str, status_code: int) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


async def read_limited_upload(image: UploadFile) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await image.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > MAX_IMAGE_BYTES:
            raise ImageProcessingError("图片不能超过 10MB", 413)
        chunks.append(chunk)

    if total == 0:
        raise ImageProcessingError("图片不能为空", 400)
    return b"".join(chunks)


def _flatten_to_rgb(image: Image.Image) -> Image.Image:
    has_alpha = image.mode in {"RGBA", "LA"} or (
        image.mode == "P" and "transparency" in image.info
    )
    if has_alpha:
        rgba = image.convert("RGBA")
        background = Image.new("RGB", rgba.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.getchannel("A"))
        return background
    return image.convert("RGB")


def prepare_image(data: bytes) -> bytes:
    """Validate, orient, shrink to 2048px, and re-encode as JPEG in memory."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as probe:
                image_format = probe.format
                width, height = probe.size
                probe.verify()
    except ImageProcessingError:
        raise
    except Exception as exc:  # noqa: BLE001 - untrusted image input
        raise ImageProcessingError(
            "无法识别图片，请上传 JPEG、PNG 或 WebP 图片",
            415,
        ) from exc

    if image_format not in ALLOWED_FORMATS:
        raise ImageProcessingError(
            "仅支持 JPEG、PNG、WebP 图片（暂不支持 HEIC）",
            415,
        )
    if width * height > MAX_PIXELS:
        raise ImageProcessingError("图片像素过大，请缩小后重试", 413)

    try:
        with Image.open(BytesIO(data)) as image:
            image = ImageOps.exif_transpose(image)
            image.thumbnail(
                (MAX_DIMENSION, MAX_DIMENSION),
                Image.Resampling.LANCZOS,
            )
            output = BytesIO()
            _flatten_to_rgb(image).save(
                output,
                format="JPEG",
                quality=85,
                optimize=True,
            )
            return output.getvalue()
    except ImageProcessingError:
        raise
    except Exception as exc:  # noqa: BLE001 - untrusted image input
        raise ImageProcessingError(
            "图片处理失败，请上传有效的 JPEG、PNG 或 WebP 图片",
            415,
        ) from exc
