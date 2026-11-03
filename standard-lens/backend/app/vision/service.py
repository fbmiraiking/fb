from fastapi import UploadFile
from starlette.concurrency import run_in_threadpool

from app.ai import get_vision_provider
from app.ai.config import AIConfig
from app.schemas.vision import VisionAnalysisResponse
from app.vision.image import prepare_image, read_limited_upload
from app.vision.parser import parse_vision_json


async def analyze_upload(
    image: UploadFile,
    config: AIConfig,
) -> VisionAnalysisResponse:
    """Read, compress, analyze and parse one upload; always closes the upload."""
    raw: bytes | None = None
    processed: bytes | None = None
    try:
        raw = await read_limited_upload(image)
        processed = await run_in_threadpool(prepare_image, raw)
        raw = None

        provider = get_vision_provider(config.provider)
        result = await provider.analyze_image(processed, config)
        processed = None

        return parse_vision_json(result.text)
    finally:
        raw = None
        processed = None
        try:
            await image.close()
        except Exception:  # noqa: BLE001 - cleanup must not mask a response
            pass
