"""Tests for the Historical Document AI Scanner & Preprocessing Engine."""
from PIL import Image
from app.ai.historical_ocr import HistoricalDocumentPreprocessor, historical_preprocessor


def test_quality_assessment_clean_image():
    # Create a high-contrast test image
    img = Image.new("L", (200, 200), color=255)
    for y in range(50, 150):
        for x in range(50, 150):
            img.putpixel((x, y), 0)

    is_damaged, quality = historical_preprocessor._assess_quality(img)
    assert not is_damaged
    assert quality > 0.5


def test_quality_assessment_faded_image():
    # Create a low-contrast washed out test image (simulating faded aged revenue document)
    img = Image.new("L", (200, 200), color=230)
    for y in range(50, 150):
        for x in range(50, 150):
            img.putpixel((x, y), 220)

    is_damaged, quality = historical_preprocessor._assess_quality(img)
    assert is_damaged
    assert quality < 0.5


def test_preprocess_image_pipeline():
    img = Image.new("RGB", (300, 400), color=(245, 240, 220))
    result = historical_preprocessor.preprocess_image(img)
    assert result.image is not None
    assert isinstance(result.skew_angle, float)
    assert len(result.detected_stamps) >= 2
    assert result.detected_stamps[0]["type"] == "REVENUE_STAMP_ZONE"


def test_calibrate_ocr_uncertainty_tags_low_confidence():
    raw_words = [
        {"text": "Karnataka", "conf": 95, "x": 10, "y": 10, "w": 50, "h": 15},
        {"text": "Sub-Registrar", "conf": 90, "x": 65, "y": 10, "w": 70, "h": 15},
        {"text": "fadedtext", "conf": 40, "x": 140, "y": 10, "w": 40, "h": 15},
        {"text": "124/3", "conf": 70, "x": 185, "y": 10, "w": 30, "h": 15}, # Number with < 75% -> uncertain
    ]

    text, mean_conf, boxes = historical_preprocessor.calibrate_ocr_uncertainty(raw_words)
    assert "Karnataka" in text
    assert "Sub-Registrar" in text
    assert "[UNCERTAIN: fadedtext (conf: 40%)]" in text
    assert "[UNCERTAIN: 124/3 (conf: 70%)]" in text
    assert len(boxes) == 4
    assert boxes[2]["is_uncertain"] is True
    assert boxes[3]["is_uncertain"] is True
    assert mean_conf > 0.5
