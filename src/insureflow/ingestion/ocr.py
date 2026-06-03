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
        text = ""
        try:
            from pdfminer.high_level import extract_text
            text = extract_text(file_path)
        except Exception as e:
            logger.warning("pdfminer extraction failed: %s", e)
            text = Path(file_path).read_text(errors="replace")
        return UnstructuredSubmission(
            submission_id=submission_id,
            source="ocr_processor",
            document_type="ocr_text",
            raw_text=text,
        )

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
        try:
            from pdfminer.high_level import extract_text
            text = extract_text(file_path)
        except Exception as e:
            logger.warning("pdfminer extraction failed: %s", e)
            try:
                import PyPDF2
                with open(file_path, "rb") as f:
                    reader = PyPDF2.PdfReader(f)
                    text = "\n".join(page.extract_text() for page in reader.pages)
            except ImportError:
                text = Path(file_path).read_text(errors="replace")

        return UnstructuredSubmission(
            submission_id=submission_id,
            source="ocr_processor",
            document_type="ocr_text",
            raw_text=text or "[OCR: No text could be extracted]",
        )
