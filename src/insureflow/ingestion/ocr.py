from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path

from insureflow.ingestion.cloud_ocr import CloudOcrResult, cloud_extract
from insureflow.ingestion.vision_ml import vision_extract_image
from insureflow.models.submissions import UnstructuredSubmission

logger = logging.getLogger(__name__)


def _cell_str(value: object) -> str:
    """Render a cell value without float noise (2500000.0 -> 2500000)."""
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _table_to_markdown(rows: list[list[str]]) -> str:
    if not rows:
        return ""
    header = " | ".join(c.replace("\n", " ").strip() for c in rows[0])
    lines = [f"| {header} |", "|" + " --- |" * len(rows[0])]
    for row in rows[1:]:
        cells = row + [""] * (len(rows[0]) - len(row))
        lines.append("| " + " | ".join(c.replace("\n", " ").strip() for c in cells[: len(rows[0])]) + " |")
    return "\n".join(lines)


class OCRProcessor:
    def __init__(self, engine: str = "auto") -> None:
        self.engine = engine
        self._last_pdf_lines: dict[int, dict[str, list[float]]] = {}

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

    def extract_text_from_bytes(self, data: bytes, filename: str, submission_id: str) -> UnstructuredSubmission:
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
        from insureflow.models.submissions import ExtractedField

        text, engine, lines = self._extract_image_text(file_path)
        failed = not text or not text.strip()
        raw = text if text and text.strip() else "[OCR: No text could be extracted from image]"
        fields: dict[str, list[ExtractedField]] = {
            "ocr_engine": [ExtractedField(field_name="ocr_engine", value=engine, confidence=1.0 if not failed else 0.0)],
        }
        if failed:
            fields["ocr_failed"] = [ExtractedField(field_name="ocr_failed", value="true", confidence=1.0)]
        return UnstructuredSubmission(
            submission_id=submission_id,
            source="ocr_processor",
            document_type="ocr_text",
            raw_text=raw,
            extracted_fields=fields,
            spatial_lines=lines,
        )

    def _extract_image_text(self, file_path: str) -> tuple[str, str, dict[int, dict[str, list[float]]]]:
        """Return ``(text, engine, spatial_lines)``; cloud/vision-ML providers first."""
        # 0. Opt-in cloud OCR (Textract / Document AI)
        cloud = cloud_extract(Path(file_path).read_bytes(), file_path)
        if cloud is not None and cloud.text.strip():
            text = cloud.text + (f"\n\n{cloud.tables}" if cloud.tables.strip() else "")
            return text, cloud.provider, cloud.lines

        # 0.5. Opt-in vision ML (PaddleOCR / HF image-to-text)
        ml_text = vision_extract_image(file_path)
        if ml_text and ml_text.strip():
            return ml_text, "vision_ml", {}

        # 1. Tesseract OCR (best for scans/handwriting)
        if self.engine in ("auto", "tesseract"):
            try:
                import pytesseract
                from PIL import Image

                text = pytesseract.image_to_string(Image.open(file_path))
                if text and text.strip():
                    return str(text), "tesseract", {}
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
                return str(text), "pdfminer", {}
        except Exception:
            pass

        return Path(file_path).read_text(errors="replace"), "raw", {}

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
        spatial: dict[int, dict[str, list[float]]] = {}
        if os.getenv("USE_SPATIAL_GROUNDING", "1").strip().lower() not in {"0", "false", "off", "no", "none"}:
            spatial = self._build_pdf_spatial_lines(file_path)
        return UnstructuredSubmission(
            submission_id=submission_id,
            source="ocr_processor",
            document_type="ocr_text",
            raw_text=text,
            spatial_lines=spatial,
        )

    def _ocr_pdf_pdfminer(self, file_path: str, submission_id: str) -> UnstructuredSubmission:
        from insureflow.models.submissions import ExtractedField

        text = self._extract_pdf_text(file_path)
        tables = self._extract_pdf_tables(file_path)
        if tables:
            text = f"{text}\n\n{tables}" if text and not text.strip().startswith("[OCR: No text") else tables
        failed = not text or not text.strip() or text.strip().startswith("[OCR: No text")
        raw = text if text and text.strip() else "[OCR: No text could be extracted]"
        fields: dict[str, list[ExtractedField]] = {
            "ocr_engine": [ExtractedField(field_name="ocr_engine", value="pdfminer", confidence=1.0 if not failed else 0.0)],
        }
        if failed:
            fields["ocr_failed"] = [ExtractedField(field_name="ocr_failed", value="true", confidence=1.0)]
        return UnstructuredSubmission(
            submission_id=submission_id,
            source="ocr_processor",
            document_type="ocr_text",
            raw_text=raw,
            extracted_fields=fields,
            spatial_lines=self._last_pdf_lines,
        )

    def _extract_pdf_text(self, file_path: str) -> str:
        # 0. Opt-in cloud/ML OCR (LlamaParse, Textract, Document AI)
        cloud = self._cloud_or_ml_pdf(file_path)
        if cloud is not None and cloud.text.strip():
            self._last_pdf_lines = cloud.lines or {}
            return cloud.text + (f"\n\n{cloud.tables}" if cloud.tables.strip() else "")

        try:
            import pdfplumber

            with pdfplumber.open(file_path) as pdf:
                text = "\n".join(page.extract_text() or "" for page in pdf.pages)
            if text and len(text.strip()) > 50:
                if os.getenv("USE_SPATIAL_GROUNDING", "1").strip().lower() not in {"0", "false", "off", "no", "none"}:
                    self._last_pdf_lines = self._build_pdf_spatial_lines(file_path)
                else:
                    self._last_pdf_lines = {}
                return text
        except ImportError:
            logger.debug("pdfplumber not available")
        except Exception as exc:
            logger.warning("pdfplumber extraction failed: %s", exc)
        self._last_pdf_lines = {}

        try:
            from pdfminer.high_level import extract_text

            text = extract_text(file_path)
            if text and len(text.strip()) > 50:
                return text
        except Exception as e:
            logger.warning("pdfminer extraction failed: %s", e)

        # PyMuPDF fallback — better than PyPDF2 on layout-heavy digital PDFs
        try:
            try:
                import pymupdf
            except ImportError:  # pragma: no cover - older package name
                import fitz as pymupdf  # type: ignore[no-redef]

            doc = pymupdf.open(file_path)
            try:
                text = "\n".join(page.get_text("text") for page in doc)
            finally:
                doc.close()
            if text and len(text.strip()) > 50:
                return text
        except ImportError:
            logger.debug("pymupdf not available")
        except Exception as exc:
            logger.warning("pymupdf extraction failed: %s", exc)

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

    def _build_pdf_spatial_lines(self, file_path: str) -> dict[int, dict[str, list[float]]]:
        """Line-level normalized boxes via pdfplumber for spatial grounding."""
        result: dict[int, dict[str, list[float]]] = {}
        try:
            import pdfplumber

            with pdfplumber.open(file_path) as pdf:
                for page_index, page in enumerate(pdf.pages, start=1):
                    words = page.extract_words()
                    rows: dict[int, list[dict[str, object]]] = {}
                    for word in words:
                        key = round(float(word["top"]) / 4.0)
                        rows.setdefault(key, []).append(word)
                    page_map: dict[str, list[float]] = {}
                    for key in sorted(rows):
                        ws = sorted(rows[key], key=lambda w: float(w["x0"]))
                        text = " ".join(str(w["text"]) for w in ws)
                        if not text:
                            continue
                        x0 = min(float(w["x0"]) for w in ws) / page.width
                        y0 = min(float(w["top"]) for w in ws) / page.height
                        x1 = max(float(w["x1"]) for w in ws) / page.width
                        y1 = max(float(w["bottom"]) for w in ws) / page.height
                        page_map[text] = [round(x0, 4), round(y0, 4), round(x1, 4), round(y1, 4)]
                    if page_map:
                        result[page_index] = page_map
        except Exception as exc:
            logger.debug("spatial line build skipped: %s", exc)
        return result

    def _cloud_or_ml_pdf(self, file_path: str) -> CloudOcrResult | None:
        """Run configured structured-OCR providers for PDFs; None when unconfigured."""
        try:
            from insureflow.ingestion.llamaparse import parse_pdf_with_llamaparse

            text = parse_pdf_with_llamaparse(file_path)
            if text and text.strip():
                return CloudOcrResult(text=text, tables="", provider="llamaparse")
        except ImportError:
            pass
        except Exception as exc:
            logger.warning("LlamaParse failed: %s", exc)
        try:
            data = Path(file_path).read_bytes()
        except OSError:
            return None
        return cloud_extract(data, file_path)

    def _extract_pdf_tables(self, file_path: str) -> str:
        """Append any tabular regions detected (SOVs, loss runs, schedules).

        pdfplumber's table extraction is preferred; PyMuPDF ``find_tables`` is
        the fallback. Only returns rows where at least one cell has content.
        """
        blocks: list[str] = []
        try:
            import pdfplumber

            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    for table in page.extract_tables() or []:
                        rows = [
                            [_cell_str(c) for c in row]
                            for row in table
                            if any(c is not None and str(c).strip() for c in row)
                        ]
                        if rows:
                            blocks.append(_table_to_markdown(rows))
            if blocks:
                return "\n\n".join(blocks)
        except ImportError:
            logger.debug("pdfplumber not available for table extraction")
        except Exception as exc:
            logger.debug("pdfplumber table extraction failed: %s", exc)

        try:
            try:
                import pymupdf
            except ImportError:  # pragma: no cover - older package name
                import fitz as pymupdf  # type: ignore[no-redef]
        except ImportError:
            return ""
        try:
            doc = pymupdf.open(file_path)
            try:
                for page in doc:
                    for table in page.find_tables().tables:
                        rows = [
                            [_cell_str(c) for c in r]
                            for r in table.extract()
                            if any(c is not None and str(c).strip() for c in r)
                        ]
                        if rows:
                            blocks.append(_table_to_markdown(rows))
            finally:
                doc.close()
            return "\n\n".join(blocks)
        except Exception as exc:
            logger.debug("pymupdf table extraction failed: %s", exc)
            return ""
