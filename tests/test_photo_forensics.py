"""EXIF software tags and JPEG error-level analysis. Skip cleanly without Pillow."""

from __future__ import annotations

import io
from typing import Any

import pytest

from insureflow.ml.vision.forensics import inspect_photo_forensics
from insureflow.ml.vision.photo_scorer import score_photo_quality

pytest.importorskip("PIL")

from PIL import Image  # noqa: E402


def _jpeg(*, software: str = "", size: tuple[int, int] = (48, 48), color: tuple[int, int, int] = (90, 90, 90)) -> bytes:
    img = Image.new("RGB", size, color)
    kwargs: dict[str, Any] = {"format": "JPEG", "quality": 90}
    if software:
        exif = Image.Exif()
        exif[0x0131] = software
        kwargs["exif"] = exif
    buf = io.BytesIO()
    img.save(buf, **kwargs)
    return buf.getvalue()


def _jpeg_with_ela_hotspot() -> bytes:
    base = Image.new("RGB", (128, 128), (80, 80, 80))
    buf = io.BytesIO()
    base.save(buf, format="JPEG", quality=95)
    original = Image.open(io.BytesIO(buf.getvalue())).convert("RGB")
    noise = Image.new("RGB", (48, 48))
    for y in range(48):
        for x in range(48):
            v = (x * 13 + y * 17) % 256
            noise.putpixel((x, y), (v, 255 - v, (x * y) % 256))
    original.paste(noise, (16, 16))
    out = io.BytesIO()
    original.save(out, format="JPEG", quality=90)
    return out.getvalue()


def test_empty_bytes_yield_no_findings() -> None:
    assert inspect_photo_forensics(b"") == []


def test_photoshop_exif_is_a_warning() -> None:
    findings = inspect_photo_forensics(_jpeg(software="Adobe Photoshop 24.0"), "roof.jpg")
    cats = [f.category for f in findings]
    assert "photo_forensics" in cats
    warning = next(f for f in findings if f.severity == "warning")
    assert "photoshop" in warning.description.lower() or "editor" in warning.description.lower()


def test_jpeg_without_exif_is_info_not_a_clean_bill() -> None:
    findings = inspect_photo_forensics(_jpeg(), "stripped.jpg")
    assert any("no EXIF" in f.description for f in findings)
    assert all(f.severity != "warning" or "EXIF" not in f.description for f in findings)


def test_ela_hotspot_flags_a_local_paste() -> None:
    findings = inspect_photo_forensics(_jpeg_with_ela_hotspot(), "edited.jpg")
    ela = [f for f in findings if "error-level" in f.description.lower() or "recompress" in f.description.lower()]
    assert ela, "pasted JPEG region should leave an ELA hotspot"
    assert ela[0].severity == "warning"


def test_score_photo_quality_includes_forensics() -> None:
    analysis = score_photo_quality(_jpeg(software="GIMP 2.10"), "yard.jpg")
    assert any(f.category == "photo_forensics" for f in analysis.findings)
