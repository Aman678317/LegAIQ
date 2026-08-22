import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))  # make pdfgen importable
from pdfgen import build_sample_pdf  # noqa: E402


@pytest.fixture(scope="session")
def sample_pdf(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return build_sample_pdf(tmp_path_factory.mktemp("pdfs") / "sample.pdf")
