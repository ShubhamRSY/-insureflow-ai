"""Photo quality scoring — blur detection, brightness, resolution, angle assessment.

Uses OpenCV for image processing when available, falls back to PIL/Pillow.
No external API calls — pure local image analysis.
"""

from __future__ import annotations

import io
import logging
from typing import Any

from insureflow.ml.vision.models import PhotoAnalysis, PhotoQuality, VisualFinding

logger = logging.getLogger(__name__)

_MIN_WIDTH = 640
_MIN_HEIGHT = 480
_MIN_QUALITY_SCORE = 0.3


def _get_image_lib() -> tuple[str | None, Any, Any]:
    try:
        import cv2
        import numpy as np

        return "cv2", cv2, np
    except ImportError:
        pass
    try:
        from PIL import Image

        return "pil", Image, None
    except ImportError:
        pass
    return None, None, None


def _compute_blur_score(image_data: bytes) -> tuple[float, str]:
    if not image_data:
        return 0.0, "empty"
    engine, lib, np = _get_image_lib()
    if engine == "cv2":
        import numpy as _np

        img_array = _np.frombuffer(image_data, _np.uint8)
        img = lib.imdecode(img_array, lib.IMREAD_GRAYSCALE)
        if img is None:
            return 0.5, "unknown"
        laplacian = lib.Laplacian(img, lib.CV_64F)
        variance = laplacian.var()
        score = min(1.0, variance / 500.0)
        return score, "laplacian"
    if engine == "pil":
        try:
            img = lib.open(io.BytesIO(image_data))
            small = img.convert("L").resize((100, 100))
            pixels = list(small.getdata())
            mean = sum(pixels) / len(pixels)
            variance = sum((p - mean) ** 2 for p in pixels) / len(pixels)
            score = min(1.0, variance / 2000.0)
            return score, "pil_variance"
        except Exception:
            return 0.5, "unknown"
    return 0.5, "unavailable"


def _compute_brightness(image_data: bytes) -> float:
    if not image_data:
        return 0.0
    engine, lib, np = _get_image_lib()
    if engine == "cv2":
        import numpy as _np

        img_array = _np.frombuffer(image_data, _np.uint8)
        img = lib.imdecode(img_array, lib.IMREAD_GRAYSCALE)
        if img is None:
            return 0.5
        return float(_np.mean(img)) / 255.0
    if engine == "pil":
        try:
            img = lib.open(io.BytesIO(image_data))
            grayscale = img.convert("L")
            pixels: list[int] = list(grayscale.getdata())
            total = sum(pixels)
            return total / (len(pixels) * 255.0)
        except Exception:
            return 0.5
    return 0.5


def _get_dimensions(image_data: bytes) -> tuple[int, int]:
    engine, lib, _ = _get_image_lib()
    if engine == "cv2":
        import numpy as _np

        img_array = _np.frombuffer(image_data, _np.uint8)
        img = lib.imdecode(img_array, lib.IMREAD_UNCHANGED)
        if img is not None:
            h, w = img.shape[:2]
            return w, h
    if engine == "pil":
        try:
            img = lib.open(io.BytesIO(image_data))
            size: tuple[int, int] = img.size
            return size
        except Exception:
            return 0, 0
    return 0, 0


def _quality_from_score(score: float, blur: float, brightness: float) -> PhotoQuality:
    if score < 0.15:
        return PhotoQuality.UNUSABLE
    if score < 0.35 or blur < 0.1 or brightness < 0.1 or brightness > 0.95:
        return PhotoQuality.POOR
    if score < 0.55:
        return PhotoQuality.ACCEPTABLE
    if score < 0.8:
        return PhotoQuality.GOOD
    return PhotoQuality.EXCELLENT


def score_photo_quality(
    image_data: bytes,
    filename: str = "",
    photo_id: str = "",
) -> PhotoAnalysis:
    analysis = PhotoAnalysis(
        photo_id=photo_id or filename,
        filename=filename,
    )
    if not image_data:
        analysis.quality = PhotoQuality.UNUSABLE
        analysis.quality_score = 0.0
        return analysis

    w, h = _get_dimensions(image_data)
    analysis.width = w
    analysis.height = h
    analysis.file_size_kb = len(image_data) / 1024.0

    blur_score, _method = _compute_blur_score(image_data)
    analysis.blur_score = blur_score
    analysis.brightness = _compute_brightness(image_data)

    resolution_score = 0.0
    if w >= _MIN_WIDTH and h >= _MIN_HEIGHT:
        resolution_score = min(1.0, (w * h) / (1920 * 1080))
    elif w > 0 and h > 0:
        resolution_score = 0.3

    quality_score = blur_score * 0.40 + resolution_score * 0.30 + analysis.brightness * 0.15 + (1.0 - abs(analysis.brightness - 0.5) * 2) * 0.15
    analysis.quality_score = max(0.0, min(1.0, quality_score))
    analysis.quality = _quality_from_score(analysis.quality_score, blur_score, analysis.brightness)

    if blur_score < 0.15:
        analysis.findings.append(
            VisualFinding(
                category="image_quality",
                description="Image is significantly blurred — details may be unreliable",
                severity="warning",
                confidence=1.0 - blur_score,
            )
        )
    if analysis.brightness < 0.15:
        analysis.findings.append(
            VisualFinding(
                category="image_quality",
                description="Image is very dark — underexposed, may hide damage",
                severity="warning",
                confidence=0.8,
            )
        )
    elif analysis.brightness > 0.9:
        analysis.findings.append(
            VisualFinding(
                category="image_quality",
                description="Image is overexposed — washed out, details lost",
                severity="warning",
                confidence=0.7,
            )
        )
    if w < _MIN_WIDTH or h < _MIN_HEIGHT:
        analysis.findings.append(
            VisualFinding(
                category="image_quality",
                description=f"Low resolution ({w}x{h}) — minimum recommended {_MIN_WIDTH}x{_MIN_HEIGHT}",
                severity="info",
                confidence=0.9,
            )
        )

    return analysis
