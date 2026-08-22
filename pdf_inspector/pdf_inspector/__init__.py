"""pdf_inspector — detailed inspection of generated PDFs.

Powered by PyMuPDF. See README.md for the full walkthrough.
"""

from .debug import ascii_layout, overlay_png, page_summary
from .document import PDFDocument
from .page import KINDS, Page, Region

__all__ = [
    "PDFDocument", "Page", "Region", "KINDS",
    "overlay_png", "ascii_layout", "page_summary",
]

__version__ = "0.2.0"
