FROM python:3.12-slim

WORKDIR /app

# System deps for OCR (tesseract + Indian language packs) and PDF processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr tesseract-ocr-eng tesseract-ocr-hin tesseract-ocr-kan \
    tesseract-ocr-tam tesseract-ocr-tel tesseract-ocr-mal tesseract-ocr-mar \
    tesseract-ocr-ben tesseract-ocr-guj tesseract-ocr-pa tesseract-ocr-urd \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
