from io import BytesIO

import pytest
from PIL import Image

from app.vision.image import ImageProcessingError, prepare_image


def encode_image(
    size: tuple[int, int] = (3000, 1200),
    image_format: str = "PNG",
    mode: str = "RGB",
    color: object = (120, 160, 220),
) -> bytes:
    image = Image.new(mode, size, color)
    buffer = BytesIO()
    image.save(buffer, format=image_format)
    return buffer.getvalue()


def test_prepare_image_compresses_longest_side_to_2048() -> None:
    output = prepare_image(encode_image((3000, 1200)))

    with Image.open(BytesIO(output)) as image:
        assert image.format == "JPEG"
        assert max(image.size) == 2048
        assert image.size[0] / image.size[1] == pytest.approx(3000 / 1200, rel=0.01)


def test_prepare_image_does_not_upscale_small_images() -> None:
    output = prepare_image(encode_image((640, 480)))

    with Image.open(BytesIO(output)) as image:
        assert image.size == (640, 480)
        assert image.format == "JPEG"


def test_prepare_image_flattens_transparency() -> None:
    output = prepare_image(encode_image((500, 500), mode="RGBA", color=(255, 0, 0, 0)))

    with Image.open(BytesIO(output)) as image:
        assert image.mode == "RGB"
        assert image.format == "JPEG"
        assert image.getpixel((0, 0)) == (255, 255, 255)


def test_prepare_image_rejects_invalid_data() -> None:
    with pytest.raises(ImageProcessingError) as exc_info:
        prepare_image(b"not an image")

    assert exc_info.value.status_code == 415
    assert "JPEG" in exc_info.value.message


def test_prepare_image_rejects_unsupported_gif() -> None:
    with pytest.raises(ImageProcessingError) as exc_info:
        prepare_image(encode_image((100, 100), image_format="GIF"))

    assert exc_info.value.status_code == 415
    assert "JPEG、PNG、WebP" in exc_info.value.message
