"""
Download a paper's figures (image + caption) from its arXiv HTML page.

arXiv's HTML rendering (arxiv.org/html/<id>) is plain server-rendered HTML -
no JS, no anti-bot wall - so a normal HTTP request works fine (unlike, say,
WeChat article pages, which need a real browser). This script accepts an
/abs/, /pdf/, or /html/ arXiv URL, normalizes it to the /html/ version,
downloads every <figure><img>...<figcaption> pair it finds, and writes a
manifest so a card deck can reference them.

Usage:
    python fetch_paper_figures.py --url https://arxiv.org/abs/2607.02807 --out-dir figs/

Output:
    figs/manifest.json  - [{"index": 1, "path": "figs/fig_01.png", "caption": "..."}]
    figs/fig_01.png, figs/fig_02.png, ...
"""
import argparse
import json
import os
import re
from html.parser import HTMLParser
from urllib.parse import urljoin

import requests


def normalize_to_html_url(url):
    m = re.search(r"(\d{4}\.\d{4,5}(v\d+)?)", url)
    if not m:
        raise SystemExit(f"Couldn't find an arXiv id in: {url}")
    arxiv_id = m.group(1)
    return f"https://arxiv.org/html/{arxiv_id}"


class FigureExtractor(HTMLParser):
    """Walks the HTML looking for <figure>...<img src=...>...<figcaption>
    text</figcaption>...</figure> blocks. Deliberately simple - arXiv's HTML
    export has a very regular structure, so a full DOM tree isn't needed."""

    def __init__(self):
        super().__init__()
        self.figures = []
        self._in_figure = False
        self._in_caption = False
        self._current_src = None
        self._current_caption = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "figure":
            self._in_figure = True
            self._current_src = None
            self._current_caption = []
        elif tag == "img" and self._in_figure:
            self._current_src = attrs.get("src")
        elif tag == "figcaption" and self._in_figure:
            self._in_caption = True

    def handle_endtag(self, tag):
        if tag == "figcaption":
            self._in_caption = False
        elif tag == "figure":
            if self._current_src:
                self.figures.append({
                    "src": self._current_src,
                    "caption": "".join(self._current_caption).strip(),
                })
            self._in_figure = False

    def handle_data(self, data):
        if self._in_caption:
            self._current_caption.append(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", required=True, help="arXiv URL (/abs/, /pdf/, or /html/ form)")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--max-figures", type=int, default=20)
    args = parser.parse_args()

    html_url = normalize_to_html_url(args.url)
    print(f"[fetch_paper_figures] Fetching {html_url}")
    resp = requests.get(html_url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()

    # Figure <img> src attributes in arXiv's HTML export are paths like
    # "2607.02807v1/x1.png" - i.e. already including the versioned paper id
    # as their first segment, relative to /html/ itself (not to the page's
    # own URL, versioned or not). So the base for urljoin is always just
    # the flat "https://arxiv.org/html/" prefix.
    base_url = "https://arxiv.org/html/"

    extractor = FigureExtractor()
    extractor.feed(resp.text)

    os.makedirs(args.out_dir, exist_ok=True)
    manifest = []
    for i, fig in enumerate(extractor.figures[: args.max_figures], start=1):
        img_url = urljoin(base_url, fig["src"])
        ext = os.path.splitext(img_url)[1] or ".png"
        local_path = os.path.join(args.out_dir, f"fig_{i:02d}{ext}")
        img_resp = requests.get(img_url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        img_resp.raise_for_status()
        with open(local_path, "wb") as f:
            f.write(img_resp.content)
        manifest.append({"index": i, "path": local_path, "caption": fig["caption"], "source_url": img_url})
        print(f"[fetch_paper_figures] Saved figure {i}: {local_path}")
        print(f"    caption: {fig['caption'][:120]}")

    manifest_path = os.path.join(args.out_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"[fetch_paper_figures] Wrote manifest: {manifest_path} ({len(manifest)} figures)")


if __name__ == "__main__":
    main()
