"""
Render a page (or a cropped region of a page) from a local PDF to a PNG.

This is the workhorse for pulling figures out of a paper that isn't on
arXiv (so `fetch_paper_figures.py`'s HTML scraping doesn't apply) - or,
even for an arXiv paper, when a figure spans a layout `fetch_paper_figures.py`
doesn't capture cleanly (e.g. a multi-panel figure embedded in a wider
page). There's no reliable way to auto-detect "where Figure 3 is" on an
arbitrary PDF page - papers lay figures out too differently - so this is
built around a short view-then-crop loop rather than one-shot extraction:

1. Render the full page (no --box) and look at it (Read tool) to find the
   figure's pixel bounding box.
2. Re-run with --box "x0,y0,x1,y1" (in pixels, at the same --dpi) to crop
   just the figure (+ its caption, if you want the caption baked into the
   image - usually you don't, since you'll write your own caption text in
   the card instead).
3. Look at the crop; nudge the box and re-run if it's off. Two or three
   iterations is normal and expected, not a sign something's wrong.

Usage:
    # Step 1: see the full page to find coordinates
    python render_pdf_page.py --pdf paper.pdf --page 6 --out page_06.png

    # Step 2: crop once you know the box (in pixels at --dpi 200 by default)
    python render_pdf_page.py --pdf paper.pdf --page 6 --out fig3_crop.png \\
        --box 150,180,1650,960
"""
import argparse

import fitz  # PyMuPDF
from PIL import Image


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pdf", required=True)
    parser.add_argument("--page", type=int, required=True, help="1-indexed page number")
    parser.add_argument("--out", required=True)
    parser.add_argument("--dpi", type=int, default=200)
    parser.add_argument("--box", help="x0,y0,x1,y1 in pixels at --dpi, for cropping. Omit to render the full page.")
    args = parser.parse_args()

    doc = fitz.open(args.pdf)
    page = doc[args.page - 1]
    zoom = args.dpi / 72
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))

    if args.box:
        x0, y0, x1, y1 = (int(v) for v in args.box.split(","))
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        img.crop((x0, y0, x1, y1)).save(args.out)
    else:
        pix.save(args.out)

    print(args.out)


if __name__ == "__main__":
    main()
