from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path

from insureflow.models.submissions import UnstructuredSubmission

logger = logging.getLogger(__name__)


class OCRProcessor:
    def __init__(self, engine: str = "auto") -> None:
        self.engine = engine

    def extract_text(self, file_path: str, submission_id: str) -> UnstructuredSubmission:
        ext = Path(file_path).suffix.lower()
        if ext == ".pdf":
            return self._ocr_pdf(file_path, submission_id)
        elif ext in (".png", ".jpg", ".jpeg", ".tiff", ".bmp"):
            return self._ocr_image(file_path, submission_id)
        else:
            raw = Path(file_path).read_text(errors="replace")
            return UnstructuredSubmission(
                submission_id=submission_id,
                source="ocr_processor",
                document_type="ocr_text",
                raw_text=raw,
            )

    def extract_text_from_bytes(
        self, data: bytes, filename: str, submission_id: str
    ) -> UnstructuredSubmission:
        ext = Path(filename).suffix.lower()
        if ext == ".pdf":
            return self._ocr_pdf_bytes(data, submission_id)
        elif ext in (".png", ".jpg", ".jpeg", ".tiff", ".bmp"):
            return self._ocr_image_bytes(data, submission_id)
        else:
            text = data.decode("utf-8", errors="replace")
            return UnstructuredSubmission(
                submission_id=submission_id,
                source="ocr_processor",
                document_type="ocr_text",
                raw_text=text,
            )

    def _ocr_pdf(self, file_path: str, submission_id: str) -> UnstructuredSubmission:
        if self.engine == "unstructured" or self.engine == "auto":
            try:
                return self._ocr_pdf_unstructured(file_path, submission_id)
            except ImportError:
                if self.engine == "unstructured":
                    raise
                logger.info("unstructured not available, falling back to pdfminer")

        return self._ocr_pdf_pdfminer(file_path, submission_id)

    def _ocr_pdf_bytes(self, data: bytes, submission_id: str) -> UnstructuredSubmission:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(data)
            tmp_path = tmp.name
        try:
            return self._ocr_pdf(tmp_path, submission_id)
        finally:
            os.unlink(tmp_path)

    def _ocr_image(self, file_path: str, submission_id: str) -> UnstructuredSubmission:
        text = self._extract_image_text(file_path)
        return UnstructuredSubmission(
            submission_id=submission_id,
            source="ocr_processor",
            document_type="ocr_text",
            raw_text=text or "[OCR: No text could be extracted from image]",
        )

    def _extract_image_text(self, file_path: str) -> str:
        # 1. Tesseract OCR (best for scans/handwriting)
        if self.engine in ("auto", "tesseract"):
            try:
                import pytesseract
                from PIL import Image

                text = pytesseract.image_to_string(Image.open(file_path))
                if text and text.strip():
                    return text
            except ImportError:
                if self.engine == "tesseract":
                    raise
                logger.debug("pytesseract/PIL not available")
            except Exception as exc:
                logger.warning("Tesseract OCR failed: %s", exc)

        # 2. pdfminer fallback (some TIFF/PDF hybrids)
        try:
            from pdfminer.high_level import extract_text
            text = extract_text(file_path)
            if text and text.strip():
                return text
        except Exception:
            pass

        return Path(file_path).read_text(errors="replace")

    def _ocr_image_bytes(self, data: bytes, submission_id: str) -> UnstructuredSubmission:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp.write(data)
            tmp_path = tmp.name
        try:
            return self._ocr_image(tmp_path, submission_id)
        finally:
            os.unlink(tmp_path)

    def _ocr_pdf_unstructured(self, file_path: str, submission_id: str) -> UnstructuredSubmission:
        from unstructured.partition.pdf import partition_pdf
        elements = partition_pdf(filename=file_path, strategy="auto")
        text = "\n\n".join(str(el) for el in elements)
        return UnstructuredSubmission(
            submission_id=submission_id,
            source="ocr_processor",
            document_type="ocr_text",
            raw_text=text,
        )

    def _ocr_pdf_pdfminer(self, file_path: str, submission_id: str) -> UnstructuredSubmission:
        text = self._extract_pdf_text(file_path)
        return UnstructuredSubmission(
            submission_id=submission_id,
            source="ocr_processor",
            document_type="ocr_text",
            raw_text=text or "[OCR: No text could be extracted]",
        )

    def _extract_pdf_text(self, file_path: str) -> str:
        try:
            from pdfminer.high_level import extract_text
            text = extract_text(file_path)
            if text and len(text.strip()) > 50:
                return text
        except Exception as e:
            logger.warning("pdfminer extraction failed: %s", e)

        # Scanned PDF fallback — render pages and Tesseract
        if self.engine in ("auto", "tesseract"):
            try:
                import pytesseract
                from pdf2image import convert_from_path

                pages = convert_from_path(file_path, dpi=200)
                ocr_parts = [pytesseract.image_to_string(page) for page in pages]
                combined = "\n\n".join(p for p in ocr_parts if p.strip())
                if combined.strip():
                    return combined
            except ImportError:
                logger.debug("pdf2image/pytesseract not available for scanned PDF OCR")
            except Exception as exc:
                logger.warning("Scanned PDF OCR failed: %s", exc)

        try:
            import PyPDF2
            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                return "\n".join(page.extract_text() or "" for page in reader.pages)
        except ImportError:
            pass

        return Path(file_path).read_text(errors="replace")
