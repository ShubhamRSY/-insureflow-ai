"""Handwriting detection and recognition for insurance documents.

Detects handwritten content in document images and extracts text using
TrOCR (Transformer-based OCR) optimized for handwriting. Falls back
gracefully when models are unavailable.

    USE_HTR=1               enable handwriting recognition
    HTR_DETECTION_MODEL     HF model for handwriting detection (default: microsoft/trocr-large-handwritten)
    HTR_OCR_MODEL           HF model for handwriting OCR (default: microsoft/trocr-large-handwritten)
    HTR_CONFIDENCE_THRESHOLD minimum confidence to accept HTR output (default: 0.3)
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_DETECTION_MODEL = "microsoft/trocr-large-handwritten"
_DEFAULT_OCR_MODEL = "microsoft/trocr-large-handwritten"
_CONFIDENCE_THRESHOLD = float(os.getenv("HTR_CONFIDENCE_THRESHOLD", "0.3"))


def _htr_enabled() -> bool:
    val = os.getenv("USE_HTR", "").strip().lower()
    return val in {"1", "true", "on", "yes"}


class HandwritingDetector:
    """Detects whether a document image contains handwritten content.

    Uses multiple signals:
    1. Stroke width transform analysis (handwriting has variable stroke width)
    2. Connected component analysis (handwriting has irregular components)
    3. Optional TrOCR confidence (low confidence on printed text = likely handwriting)
    """

    def __init__(self) -> None:
        self._model: Any = None
        self._processor: Any = None
        self._loaded = False

    def _ensure_model(self) -> bool:
        if self._loaded:
            return self._model is not None
        self._loaded = True
        if not _htr_enabled():
            return False
        try:
            from transformers import TrOCRProcessor, VisionEncoderDecoderModel

            model_name = os.getenv("HTR_DETECTION_MODEL", _DEFAULT_DETECTION_MODEL)
            self._processor = TrOCRProcessor.from_pretrained(model_name)
            self._model = VisionEncoderDecoderModel.from_pretrained(model_name)
            logger.info("Loaded HTR detection model: %s", model_name)
            return True
        except Exception as exc:
            logger.warning("HTR detection model unavailable: %s", exc)
            return False

    def detect(self, image: Any) -> dict[str, Any]:
        """Analyze an image for handwriting presence.

        Args:
            image: PIL Image or path to image

        Returns:
            dict with keys: has_handwriting, confidence, method, details
        """
        result: dict[str, Any] = {
            "has_handwriting": False,
            "confidence": 0.0,
            "method": "none",
            "details": "",
        }

        try:
            from PIL import Image

            if isinstance(image, str):
                image = Image.open(image)
            image_rgb = image.convert("RGB")
        except Exception as exc:
            result["details"] = f"Failed to load image: {exc}"
            return result

        # Method 1: Heuristic analysis (always available, no model needed)
        heuristic = self._heuristic_detection(image_rgb)
        result["confidence"] = heuristic["confidence"]
        result["method"] = "heuristic"
        result["details"] = heuristic["details"]

        if heuristic["confidence"] > 0.6:
            result["has_handwriting"] = True
            return result

        # Method 2: TrOCR confidence analysis (if model available)
        if self._ensure_model() and self._model is not None:
            trocr_result = self._trocr_detection(image_rgb)
            if trocr_result["confidence"] > result["confidence"]:
                result["confidence"] = trocr_result["confidence"]
                result["method"] = "trocr"
                result["details"] = trocr_result["details"]
                result["has_handwriting"] = trocr_result["has_handwriting"]

        return result

    def _heuristic_detection(self, image: Any) -> dict[str, Any]:
        """Detect handwriting via image heuristics — no model needed."""
        import numpy as np

        try:
            img_array = np.array(image.convert("L"))
        except Exception:
            return {"confidence": 0.0, "details": "numpy unavailable"}

        # Check 1: Variable stroke width (handwriting has high variance)
        # Binarize
        threshold = 128
        binary = (img_array < threshold).astype(np.uint8)
        if binary.sum() == 0:
            return {"confidence": 0.0, "details": "blank image"}

        # Distance transform for stroke width estimation
        from scipy.ndimage import distance_transform_edt

        dist = distance_transform_edt(binary)
        stroke_pixels = dist[dist > 0]
        if len(stroke_pixels) == 0:
            return {"confidence": 0.0, "details": "no strokes detected"}

        stroke_cv = float(np.std(stroke_pixels) / max(np.mean(stroke_pixels), 1e-6))
        # Handwriting typically has CV > 0.5, printed text < 0.3
        stroke_score = min(stroke_cv / 1.0, 1.0)

        # Check 2: Ink density variation (handwriting is patchier)
        block_size = 32
        h, w = img_array.shape
        blocks_h = max(h // block_size, 1)
        blocks_w = max(w // block_size, 1)
        densities = []
        for i in range(blocks_h):
            for j in range(blocks_w):
                block = binary[
                    i * block_size : min((i + 1) * block_size, h),
                    j * block_size : min((j + 1) * block_size, w),
                ]
                densities.append(float(block.mean()))

        if densities:
            mean_density = float(np.mean(densities))
            std_density = float(np.std(densities))
            density_cv = std_density / max(mean_density, 1e-6)
            density_score = min(density_cv / 2.0, 1.0)
        else:
            density_score = 0.0

        # Check 3: Connected component irregularity
        from scipy.ndimage import label

        labeled, num_features = label(binary)
        if num_features > 0:
            sizes = []
            for feat_id in range(1, min(num_features + 1, 100)):
                component = labeled == feat_id
                sizes.append(float(component.sum()))
            if sizes:
                mean_size = float(np.mean(sizes))
                std_size = float(np.std(sizes))
                size_cv = std_size / max(mean_size, 1e-6)
                irregularity_score = min(size_cv / 3.0, 1.0)
            else:
                irregularity_score = 0.0
        else:
            irregularity_score = 0.0

        # Combined score
        combined = 0.4 * stroke_score + 0.3 * density_score + 0.3 * irregularity_score

        return {
            "confidence": round(combined, 3),
            "details": f"stroke_cv={stroke_cv:.2f}, density_cv={density_cv if densities else 0:.2f}, components={num_features}",
        }

    def _trocr_detection(self, image: Any) -> dict[str, Any]:
        """Use TrOCR to detect handwriting via confidence analysis.

        TrOCR gives low confidence on printed text it wasn't trained on,
        and high confidence on handwriting it was trained on.
        """
        try:
            import torch

            processor = self._processor
            model = self._model
            if processor is None or model is None:
                return {"confidence": 0.0, "has_handwriting": False, "details": "model not loaded"}

            image_resized = image.convert("RGB").resize((384, 384))
            pixel_values = processor(images=image_resized, return_tensors="pt").pixel_values

            with torch.no_grad():
                outputs = model.generate(
                    pixel_values,
                    max_new_tokens=128,
                    return_dict_in_generate=True,
                    output_scores=True,
                )

            # Get confidence from generated token scores
            if outputs.scores:
                all_scores = torch.cat(outputs.scores, dim=0)
                avg_confidence = float(torch.softmax(all_scores, dim=-1).max(dim=-1).values.mean())
            else:
                avg_confidence = 0.0

            # Decode the text
            generated_ids = outputs.sequences
            text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]

            # High confidence on TrOCR = likely handwriting (it was trained on handwriting)
            has_handwriting = avg_confidence > _CONFIDENCE_THRESHOLD and len(text.strip()) > 0

            return {
                "confidence": round(avg_confidence, 3),
                "has_handwriting": has_handwriting,
                "details": f"trocr_confidence={avg_confidence:.3f}, text='{text[:100]}'",
            }
        except Exception as exc:
            logger.debug("TrOCR detection failed: %s", exc)
            return {"confidence": 0.0, "has_handwriting": False, "details": str(exc)}


class HandwritingRecognizer:
    """Extracts text from handwritten content using TrOCR.

    Uses microsoft/trocr-large-handwritten which was trained on
    the IAM Handwriting Database and produces reasonable results
    on English handwriting including insurance form annotations.
    """

    def __init__(self) -> None:
        self._processor: Any = None
        self._model: Any = None
        self._loaded = False

    def _ensure_model(self) -> bool:
        if self._loaded:
            return self._model is not None
        self._loaded = True
        if not _htr_enabled():
            return False
        try:
            from transformers import TrOCRProcessor, VisionEncoderDecoderModel

            model_name = os.getenv("HTR_OCR_MODEL", _DEFAULT_OCR_MODEL)
            self._processor = TrOCRProcessor.from_pretrained(model_name)
            self._model = VisionEncoderDecoderModel.from_pretrained(model_name)
            logger.info("Loaded HTR OCR model: %s", model_name)
            return True
        except Exception as exc:
            logger.warning("HTR OCR model unavailable: %s", exc)
            return False

    def recognize(self, image: Any, regions: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        """Recognize handwritten text in an image.

        Args:
            image: PIL Image or path
            regions: optional list of bounding boxes [{x, y, w, h}] to recognize separately.
                     If None, processes the entire image.

        Returns:
            dict with: text, confidence, regions (per-region results)
        """
        if not self._ensure_model():
            return {"text": "", "confidence": 0.0, "regions": [], "model_available": False}

        try:
            from PIL import Image

            if isinstance(image, str):
                image = Image.open(image)
            image_rgb = image.convert("RGB")
        except Exception as exc:
            return {"text": "", "confidence": 0.0, "regions": [], "error": str(exc)}

        if regions:
            return self._recognize_regions(image_rgb, regions)
        return self._recognize_full(image_rgb)

    def _recognize_full(self, image: Any) -> dict[str, Any]:
        """Recognize handwriting across the full image."""
        try:
            import torch

            processor = self._processor
            model = self._model
            if processor is None or model is None:
                return {"text": "", "confidence": 0.0, "regions": [], "model_available": False}

            # Resize to model input size
            image_resized = image.resize((384, 384))
            pixel_values = processor(images=image_resized, return_tensors="pt").pixel_values

            with torch.no_grad():
                outputs = model.generate(
                    pixel_values,
                    max_new_tokens=256,
                    return_dict_in_generate=True,
                    output_scores=True,
                )

            generated_ids = outputs.sequences
            text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0].strip()

            confidence = 0.0
            if outputs.scores:
                all_scores = torch.cat(outputs.scores, dim=0)
                confidence = float(torch.softmax(all_scores, dim=-1).max(dim=-1).values.mean())

            return {
                "text": text,
                "confidence": round(confidence, 3),
                "regions": [],
                "model_available": True,
            }
        except Exception as exc:
            logger.warning("HTR full recognition failed: %s", exc)
            return {"text": "", "confidence": 0.0, "regions": [], "error": str(exc)}

    def _recognize_regions(self, image: Any, regions: list[dict[str, Any]]) -> dict[str, Any]:
        """Recognize handwriting in specific regions of the image."""
        try:
            import torch

            processor = self._processor
            model = self._model
            if processor is None or model is None:
                return {"text": "", "confidence": 0.0, "regions": [], "model_available": False}

            region_results: list[dict[str, Any]] = []
            all_text_parts: list[str] = []
            total_confidence = 0.0

            for region in regions:
                x, y = int(region.get("x", 0)), int(region.get("y", 0))
                w, h = int(region.get("w", 0)), int(region.get("h", 0))
                if w <= 0 or h <= 0:
                    continue

                cropped = image.crop((x, y, x + w, y + h))
                cropped_resized = cropped.resize((384, 384))
                pixel_values = processor(images=cropped_resized, return_tensors="pt").pixel_values

                with torch.no_grad():
                    outputs = model.generate(
                        pixel_values,
                        max_new_tokens=128,
                        return_dict_in_generate=True,
                        output_scores=True,
                    )

                text = processor.batch_decode(outputs.sequences, skip_special_tokens=True)[0].strip()
                conf = 0.0
                if outputs.scores:
                    scores = torch.cat(outputs.scores, dim=0)
                    conf = float(torch.softmax(scores, dim=-1).max(dim=-1).values.mean())

                region_results.append(
                    {
                        "x": x,
                        "y": y,
                        "w": w,
                        "h": h,
                        "text": text,
                        "confidence": round(conf, 3),
                    }
                )
                if text:
                    all_text_parts.append(text)
                total_confidence += conf

            avg_confidence = total_confidence / max(len(region_results), 1)
            return {
                "text": "\n".join(all_text_parts),
                "confidence": round(avg_confidence, 3),
                "regions": region_results,
                "model_available": True,
            }
        except Exception as exc:
            logger.warning("HTR region recognition failed: %s", exc)
            return {"text": "", "confidence": 0.0, "regions": [], "error": str(exc)}
