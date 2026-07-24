#!/usr/bin/env python3
"""Render selected PDF pages at 144 DPI with the pinned PDFium runtime."""

from __future__ import annotations

import argparse
from pathlib import Path

import pypdfium2 as pdfium


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output_root", type=Path)
    parser.add_argument("document_id")
    parser.add_argument("pages", help="Comma-separated one-based page numbers")
    args = parser.parse_args()

    pages = sorted({int(value) for value in args.pages.split(",")})
    document = pdfium.PdfDocument(args.source)
    args.output_root.mkdir(parents=True, exist_ok=True)
    for page_number in pages:
        page = document[page_number - 1]
        bitmap = page.render(scale=2.0)
        image = bitmap.to_pil()
        destination = (
            args.output_root / f"{args.document_id}-page-{page_number}.png"
        )
        image.save(destination, format="PNG", optimize=False)
        image.close()
        bitmap.close()
        page.close()
    document.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
