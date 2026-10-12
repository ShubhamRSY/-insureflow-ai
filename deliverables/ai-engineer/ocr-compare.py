"""Compare Tesseract with EasyOCR on development scans. Does not change the live reader.

Run: python deliverables/ai-engineer/ocr-compare.py
"""

import re
import sys
import time
from pathlib import Path

import easyocr
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "underwriting_pipeline" / "ai"))
import sources

INBOX = ROOT / "simulation" / "inbox"
GOLD = ROOT / "deliverables" / "senior-underwriter" / "gold-set"
IDS = ("SUB-057", "SUB-058", "SUB-064", "SUB-065", "SUB-067", "SUB-068", "SUB-074", "SUB-075")


def gold_bits(sid: str) -> tuple[str, str, str]:
    text = (GOLD / f"{sid}.md").read_text()
    name = re.search(r"- Named insured: (.+)", text).group(1).strip()
    premises = re.search(r"- Premises: (.+)", text).group(1).strip()
    number = premises.split()[0]
    street = premises.split()[1]
    return name, number, street


def prepared(image):
    candidates = [image]
    turned = sources._osd_turn(image)
    if turned is not None:
        candidates.append(turned)
    best_image = None
    best_text = ""
    best_mean = -1.0
    for candidate in candidates:
        text, mean, _words = sources._ocr_score(candidate)
        if mean > best_mean:
            best_mean = mean
            best_text = text
            best_image = sources._prepare_image(sources._deskew(candidate))
    return best_image, best_text


def hit(text: str, needle: str) -> bool:
    return needle.lower() in text.lower()


def main() -> None:
    started = time.perf_counter()
    reader = easyocr.Reader(["en", "es"], gpu=False, verbose=False)
    load_s = time.perf_counter() - started
    print(f"easyocr load {load_s:.1f}s")
    for sid in IDS:
        name, number, street = gold_bits(sid)
        path = INBOX / sid / "scan.jpg"
        image = Image.open(path)
        t0 = time.perf_counter()
        page, tess_text = prepared(image)
        tess_s = time.perf_counter() - t0
        t1 = time.perf_counter()
        lines = reader.readtext(np.array(page), detail=0)
        easy_s = time.perf_counter() - t1
        easy_text = "\n".join(lines)
        print(
            sid,
            f"tesseract {tess_s:.1f}s name {hit(tess_text, name.split()[0])} street {hit(tess_text, number)} {hit(tess_text, street)}",
            f"easyocr {easy_s:.1f}s name {hit(easy_text, name.split()[0])} street {hit(easy_text, number)} {hit(easy_text, street)}",
        )


if __name__ == "__main__":
    main()
