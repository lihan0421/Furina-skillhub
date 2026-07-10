"""
Render the top portion of a paper's first PDF page (title, authors,
abstract) as a PNG, for use as the editorial-theme cover screenshot in
xiaohongshu-publish's make_cards.py.

Usage:
    python render_pdf_cover.py --url https://arxiv.org/abs/2607.02807 --out cover_shot.png
    python render_pdf_cover.py --pdf local_paper.pdf --out cover_shot.png
"""
import argparse
import os
import re
import tempfile

import fitz  # PyMuPDF
import requests


def normalize_to_pdf_url(url):
    m = re.search(r"(\d{4}\.\d{4,5}(v\d+)?)", url)
    if not m:
        raise SystemExit(f"Couldn't find an arXiv id in: {url}")
    return f"https://arxiv.org/pdf/{m.group(1)}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--url", help="arXiv URL (any form) to fetch the PDF from")
    src.add_argument("--pdf", help="Path to a local PDF file")
    parser.add_argument("--out", required=True)
    parser.add_argument("--top-fraction", type=float, default=0.5, help="Fraction of the first page (from the top) to keep")
    parser.add_argument("--dpi", type=int, default=200)
    args = parser.parse_args()

    if args.url:
        pdf_url = normalize_to_pdf_url(args.url)
        print(f"[render_pdf_cover] Fetching {pdf_url}")
        resp = requests.get(pdf_url, timeout=60, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        fd, pdf_path = tempfile.mkstemp(suffix=".pdf")
        with os.fdopen(fd, "wb") as f:
            f.write(resp.content)
    else:
        pdf_path = args.pdf

    doc = fitz.open(pdf_path)
    page = doc[0]
    zoom = args.dpi / 72
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
    full_path = args.out + ".full.png"
    pix.save(full_path)

    from PIL import Image
    img = Image.open(full_path)
    crop_h = int(img.height * args.top_fraction)
    img.crop((0, 0, img.width, crop_h)).save(args.out)
    os.remove(full_path)
    print(f"[render_pdf_cover] Saved {args.out} ({img.width}x{crop_h})")


if __name__ == "__main__":
    main()
