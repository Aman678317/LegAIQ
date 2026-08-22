"""Standalone entry point: python tests/make_sample.py --out sample.pdf"""

from pdfgen import build_sample_pdf

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate the sample inspection PDF")
    parser.add_argument("--out", default="sample.pdf")
    path = build_sample_pdf(parser.parse_args().out).resolve()
    print(f"wrote {path}")
