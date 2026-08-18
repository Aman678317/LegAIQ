"""OCR provider abstraction.

Providers: tesseract (local, free), google_vision (cloud), mock.
Page-by-page results are stored; the original file is never modified.
"""
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

from app.config import get_settings

settings = get_settings()

from app.ai.historical_ocr import historical_preprocessor

# Indian language mapping for OCR
LANGUAGE_CODES = {
    "eng": "en", "hin": "hi", "kan": "kn", "tam": "ta", "tel": "te",
    "mal": "ml", "mar": "mr", "ben": "bn", "guj": "gu", "pan": "pa", "urd": "ur",
    "ori": "or", "asm": "as",
}


@dataclass
class OCRPageResult:
    page_number: int
    text: str
    language: str
    confidence: float
    bounding_boxes: list[dict] = field(default_factory=list)


@dataclass
class OCRDocumentResult:
    pages: list[OCRPageResult] = field(default_factory=list)
    provider: str = "mock"

    @property
    def full_text(self) -> str:
        return "\n\n".join(p.text for p in self.pages)

    @property
    def mean_confidence(self) -> float:
        return sum(p.confidence for p in self.pages) / len(self.pages) if self.pages else 0.0


class BaseOCRProvider(ABC):
    name: str = "base"

    @abstractmethod
    async def process(self, file_bytes: bytes, file_type: str) -> OCRDocumentResult: ...

    @abstractmethod
    def is_configured(self) -> bool: ...


class TesseractProvider(BaseOCRProvider):
    name = "tesseract"

    def is_configured(self) -> bool:
        try:
            import pytesseract  # noqa: F401
            from PIL import Image  # noqa: F401
            return True
        except ImportError:
            return False

    async def process(self, file_bytes: bytes, file_type: str) -> OCRDocumentResult:
        import io
        import pytesseract
        from PIL import Image
        from langdetect import detect

        if hasattr(pytesseract, "pytesseract"):
            pytesseract = pytesseract.pytesseract
        if settings.TESSERACT_CMD:
            pytesseract.cmd = settings.TESSERACT_CMD

        result = OCRDocumentResult(provider=self.name)

        images: list[Image.Image] = []
        if file_type == "application/pdf":
            from pdf2image import convert_from_bytes
            images = convert_from_bytes(file_bytes, dpi=300)
        else:
            images = [Image.open(io.BytesIO(file_bytes))]

        for i, img in enumerate(images):
            # Preprocess historical / faded / skewed document
            prep = historical_preprocessor.preprocess_image(img)
            proc_img = prep.image

            # Multi-script pass: English + Hindi are the most common in Indian deeds
            try:
                data = pytesseract.image_to_data(proc_img, lang="eng+hin", output_type=pytesseract.Output.DICT)
            except Exception:
                data = pytesseract.image_to_data(proc_img, lang="eng", output_type=pytesseract.Output.DICT)

            raw_words = []
            for j, word in enumerate(data.get("text", [])):
                if not word or not word.strip():
                    continue
                raw_words.append({
                    "text": word,
                    "conf": data["conf"][j],
                    "x": data["left"][j], "y": data["top"][j],
                    "w": data["width"][j], "h": data["height"][j],
                })

            calibrated_text, calibrated_conf, boxes = historical_preprocessor.calibrate_ocr_uncertainty(raw_words)

            lang = "en"
            try:
                if len(calibrated_text) > 20:
                    detected = detect(calibrated_text)
                    lang = detected if detected in settings.SUPPORTED_LANGUAGES else "en"
            except Exception:
                pass

            result.pages.append(OCRPageResult(
                page_number=i + 1,
                text=re.sub(r"\s+", " ", calibrated_text).strip(),
                language=lang,
                confidence=calibrated_conf,
                bounding_boxes=boxes,
            ))

        return result


class GoogleVisionProvider(BaseOCRProvider):
    """Google Cloud Vision document-text OCR.

    Requires `pip install google-cloud-vision` plus application credentials
    (GOOGLE_APPLICATION_CREDENTIALS). Set OCR_PROVIDER=google_vision to use.
    """
    name = "google_vision"

    def is_configured(self) -> bool:
        return bool(settings.GOOGLE_APPLICATION_CREDENTIALS)

    async def process(self, file_bytes: bytes, file_type: str) -> OCRDocumentResult:
        try:
            import io
            from google.cloud import vision
        except ImportError as e:
            raise NotImplementedError(
                "google-cloud-vision is not installed. Run pip install google-cloud-vision "
                "or use OCR_PROVIDER=tesseract."
            ) from e

        from langdetect import detect

        client = vision.ImageAnnotatorClient()
        result = OCRDocumentResult(provider=self.name)

        # PDFs -> page images via poppler; images pass through directly
        images: list[bytes] = []
        if file_type == "application/pdf":
            from pdf2image import convert_from_bytes
            pil_images = convert_from_bytes(file_bytes, dpi=300)
            for img in pil_images:
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                images.append(buf.getvalue())
        else:
            images = [file_bytes]

        for i, raw in enumerate(images):
            image = vision.Image(content=raw)
            response = client.document_text_detection(image=image)
            if response.error.message:
                raise RuntimeError(
                    f"Google Vision error on page {i + 1}: {response.error.message}"
                )

            annotation = response.full_text_annotation
            words, confs, boxes = [], [], []
            for page in annotation.pages:
                for block in page.blocks:
                    for paragraph in block.paragraphs:
                        for word in paragraph.words:
                            text = "".join(sym.text for sym in word.symbols)
                            if not text.strip():
                                continue
                            conf = word.confidence or 0.0
                            v = word.bounding_box.vertices
                            words.append(text)
                            confs.append(conf)
                            boxes.append({
                                "x": v[0].x, "y": v[0].y,
                                "w": v[1].x - v[0].x, "h": v[3].y - v[0].y,
                                "text": text, "conf": round(conf, 3),
                            })

            text = " ".join(words)
            lang = "en"
            try:
                if len(text) > 20:
                    detected = detect(text)
                    lang = detected if detected in settings.SUPPORTED_LANGUAGES else "en"
            except Exception:
                pass

            result.pages.append(OCRPageResult(
                page_number=i + 1,
                text=re.sub(r"\s+", " ", text).strip(),
                language=lang,
                confidence=sum(confs) / len(confs) if confs else 0.0,
                bounding_boxes=boxes,
            ))

        return result


class MockOCRProvider(BaseOCRProvider):
    name = "mock"

    def is_configured(self) -> bool:
        return True

    async def process(self, file_bytes: bytes, file_type: str) -> OCRDocumentResult:
        return OCRDocumentResult(
            pages=[OCRPageResult(
                page_number=1,
                text="Not configured: no OCR provider is available. "
                     "Install tesseract (OCR_PROVIDER=tesseract) or configure Google Vision.",
                language="en",
                confidence=0.0,
            )],
            provider=self.name,
        )


def get_ocr_provider() -> BaseOCRProvider:
    name = settings.OCR_PROVIDER
    if name == "tesseract":
        provider = TesseractProvider()
        if provider.is_configured():
            return provider
    elif name == "google_vision":
        provider = GoogleVisionProvider()
        if provider.is_configured():
            return provider
    return MockOCRProvider()
