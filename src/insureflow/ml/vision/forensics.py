"""Photo tamper forensics — EXIF software tags and JPEG Error Level Analysis.

Deterministic and local. No vendor API. Missing Pillow degrades to no findings
rather than a fake clean bill of health.
"""

from __future__ import annotations

import io
import logging
from typing import Any

from insureflow.ml.vision.models import VisualFinding

logger = logging.getLogger(__name__)

_EDITOR_MARKERS = (
    "photoshop",
    "adobe photoshop",
    "gimp",
    "affinity photo",
    "pixelmator",
    "photopea",
    "canva",
    "snagit",
    "paint.net",
    "facetune",
    "picsart",
)

# ELA: a locally edited JPEG leaves a hotter residual than a once-compressed original.
_ELA_QUALITY = 90
_ELA_BLOCK = 8
_ELA_HOTSPOT_RATIO = 3.0
_ELA_HOTSPOT_MIN = 8.0


def inspect_photo_forensics(image_data: bytes, filename: str = "") -> list[VisualFinding]:
    """Return tamper findings for a photo. Empty list if we cannot inspect."""
    if not image_data:
        return []
    findings: list[VisualFinding] = []
    findings.extend(_exif_findings(image_data, filename))
    findings.extend(_ela_findings(image_data, filename))
    return findings


def _open_image(image_data: bytes) -> Any | None:
    try:
        from PIL import Image

        return Image.open(io.BytesIO(image_data))
    except Exception:
        return None


def _exif_findings(image_data: bytes, filename: str) -> list[VisualFinding]:
    img = _open_image(image_data)
    if img is None:
        return []
    findings: list[VisualFinding] = []
    software = _exif_software(img)
    if software and any(marker in software.lower() for marker in _EDITOR_MARKERS):
        findings.append(
            VisualFinding(
                category="photo_forensics",
                description=f"EXIF software tag indicates an editor ({software.strip()}) — request the original camera file",
                severity="warning",
                confidence=0.85,
            )
        )
    original, digitized = _exif_datetimes(img)
    if original and digitized and original != digitized:
        findings.append(
            VisualFinding(
                category="photo_forensics",
                description=f"EXIF capture time ({original}) does not match modify time ({digitized}) — file was resaved",
                severity="info",
                confidence=0.7,
            )
        )
    fmt = (img.format or "").upper()
    name = (filename or "").lower()
    looks_jpeg = fmt == "JPEG" or name.endswith((".jpg", ".jpeg"))
    if looks_jpeg and not software and not original:
        # A JPEG with no EXIF at all is common after messaging apps strip metadata.
        findings.append(
            VisualFinding(
                category="photo_forensics",
                description="JPEG has no EXIF capture metadata — cannot confirm it is an original camera file",
                severity="info",
                confidence=0.55,
            )
        )
    return findings


def _exif_software(img: Any) -> str:
    try:
        exif = img.getexif()
        if not exif:
            return ""
        # 0x0131 = Software
        value = exif.get(0x0131) or exif.get("Software") or ""
        return str(value)
    except Exception:
        return ""


def _exif_datetimes(img: Any) -> tuple[str, str]:
    try:
        exif = img.getexif()
        if not exif:
            return "", ""
        original = str(exif.get(0x9003) or exif.get("DateTimeOriginal") or "")
        digitized = str(exif.get(0x0132) or exif.get("DateTime") or "")
        return original, digitized
    except Exception:
        return "", ""


def _ela_findings(image_data: bytes, filename: str) -> list[VisualFinding]:
    img = _open_image(image_data)
    if img is None:
        return []
    fmt = (img.format or "").upper()
    name = (filename or "").lower()
    if fmt != "JPEG" and not name.endswith((".jpg", ".jpeg")):
        return []
    mean_res, max_block = _ela_residuals(img)
    if max_block <= 0:
        return []
    if max_block >= _ELA_HOTSPOT_MIN and mean_res > 0 and (max_block / max(mean_res, 1e-6)) >= _ELA_HOTSPOT_RATIO:
        return [
            VisualFinding(
                category="photo_forensics",
                description=(f"JPEG error-level analysis shows a local recompress hotspot (block residual {max_block:.0f} vs mean {mean_res:.0f}) — possible edit or paste"),
                severity="warning",
                confidence=min(0.9, 0.55 + (max_block / 80.0)),
            )
        ]
    return []


def _ela_residuals(img: Any) -> tuple[float, float]:
    """Re-encode at a known JPEG quality and measure per-block residual energy."""
    try:
        from PIL import Image

        rgb = img.convert("RGB")
        buf = io.BytesIO()
        rgb.save(buf, format="JPEG", quality=_ELA_QUALITY)
        recompressed = Image.open(io.BytesIO(buf.getvalue())).convert("RGB")
        w, h = rgb.size
        orig_px = rgb.tobytes()
        rec_px = recompressed.tobytes()
        if not orig_px or len(orig_px) != len(rec_px):
            return 0.0, 0.0
        residuals = [abs(orig_px[i] - rec_px[i]) + abs(orig_px[i + 1] - rec_px[i + 1]) + abs(orig_px[i + 2] - rec_px[i + 2]) for i in range(0, len(orig_px), 3)]
        mean_res = sum(residuals) / (len(residuals) * 3.0)
        max_block = 0.0
        block = _ELA_BLOCK
        for y0 in range(0, h, block):
            for x0 in range(0, w, block):
                total = 0.0
                n = 0
                for yy in range(y0, min(y0 + block, h)):
                    row = yy * w
                    for xx in range(x0, min(x0 + block, w)):
                        total += residuals[row + xx]
                        n += 1
                if n:
                    max_block = max(max_block, total / (n * 3.0))
        return mean_res, max_block
    except Exception as exc:
        logger.debug("ELA skipped: %s", exc)
        return 0.0, 0.0
