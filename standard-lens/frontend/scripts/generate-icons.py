"""Generate PWA icons for the frontend.

Usage (from the project root, with Pillow installed):

    python frontend/scripts/generate-icons.py

The generated PNG files are committed, so this script only needs to be run
again when the brand mark changes.
"""

from pathlib import Path

from PIL import Image, ImageDraw

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "public" / "icons"
GRADIENT_START = (37, 99, 235)  # #2563eb
GRADIENT_END = (14, 165, 233)  # #0ea5e9
SUPERSAMPLE = 4


def _gradient(size: int) -> Image.Image:
    small = Image.new("RGB", (64, 64))
    pixels = small.load()
    for y in range(64):
        for x in range(64):
            t = (x + y) / 126
            pixels[x, y] = tuple(
                round(start + (end - start) * t)
                for start, end in zip(GRADIENT_START, GRADIENT_END)
            )
    return small.resize((size, size), Image.Resampling.BICUBIC)


def _background(size: int, rounded: bool) -> Image.Image:
    image = _gradient(size).convert("RGBA")
    if not rounded:
        return image

    mask = Image.new("L", (size * SUPERSAMPLE, size * SUPERSAMPLE), 0)
    draw = ImageDraw.Draw(mask)
    edge = size * SUPERSAMPLE - 1
    draw.rounded_rectangle(
        (0, 0, edge, edge),
        radius=int(size * SUPERSAMPLE * 0.22),
        fill=255,
    )
    mask = mask.resize((size, size), Image.Resampling.LANCZOS)
    image.putalpha(mask)
    return image


def _mark(size: int, scale: float) -> Image.Image:
    """Draw the magnifier + check mark on a transparent layer."""
    canvas = size * SUPERSAMPLE
    layer = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    center = canvas / 2

    def point(x: float, y: float) -> tuple[float, float]:
        return (
            center + (x * canvas - center) * scale,
            center + (y * canvas - center) * scale,
        )

    stroke = canvas * scale

    # Lens ring.
    ring_cx, ring_cy = point(0.46, 0.46)
    ring_r = 0.205 * stroke
    ring_width = max(1, round(0.055 * stroke))
    draw.ellipse(
        (ring_cx - ring_r, ring_cy - ring_r, ring_cx + ring_r, ring_cy + ring_r),
        outline=(255, 255, 255, 255),
        width=ring_width,
    )

    # Handle.
    handle_width = max(1, round(0.075 * stroke))
    start = point(0.612, 0.612)
    end = point(0.745, 0.745)
    draw.line((start, end), fill=(255, 255, 255, 255), width=handle_width)
    for x, y in (start, end):
        r = handle_width / 2
        draw.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, 255))

    # Check mark.
    check_width = max(1, round(0.05 * stroke))
    check_points = [point(0.392, 0.462), point(0.451, 0.522), point(0.566, 0.396)]
    draw.line(check_points, fill=(255, 255, 255, 255), width=check_width, joint="curve")
    for x, y in (check_points[0], check_points[-1]):
        r = check_width / 2
        draw.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, 255))

    return layer.resize((size, size), Image.Resampling.LANCZOS)


def build(name: str, size: int, *, rounded: bool, scale: float = 1.0) -> None:
    image = _background(size, rounded=rounded)
    image.alpha_composite(_mark(size, scale))
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    image.save(OUTPUT_DIR / name, optimize=True)
    print(f"generated {name} ({size}x{size})")


def main() -> None:
    build("pwa-192x192.png", 192, rounded=True)
    build("pwa-512x512.png", 512, rounded=True)
    build("pwa-maskable-512x512.png", 512, rounded=False, scale=0.72)
    build("apple-touch-icon.png", 180, rounded=False, scale=0.86)


if __name__ == "__main__":
    main()
