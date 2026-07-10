"""
Generate a simple text-card cover image for a Xiaohongshu note, for when the
user has no photo/screenshot they want to use. A 3:4 gradient card with a
tag pill, a bold title, and an optional quote/subtitle reads as a normal
"reading notes" style cover on the platform.

Usage:
    python make_cover.py --out cover.jpg \
        --tag "AI 阅读笔记" \
        --title "AI要开始" "自己优化自己了" \
        --quote "人类应该往堆栈上层走，" "而不是被踢出这个循环。" \
        --subtitle "读 Lilian Weng《Harness Engineering》有感"

Title/quote accept multiple --title/--quote args, one per line, so long
lines can be wrapped manually where they read best.
"""
import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1440

# A couple of readable Windows CJK bold fonts, in preference order.
BOLD_FONT_CANDIDATES = [
    "C:/Windows/Fonts/msyhbd.ttc",   # Microsoft YaHei Bold
    "C:/Windows/Fonts/simhei.ttf",   # SimHei
]
REGULAR_FONT_CANDIDATES = [
    "C:/Windows/Fonts/msyh.ttc",     # Microsoft YaHei
    "C:/Windows/Fonts/simsun.ttc",
]


def first_existing(paths):
    for p in paths:
        if Path(p).exists():
            return p
    raise SystemExit(
        "No CJK font found among: " + ", ".join(paths) +
        ". Pass a different font with --bold-font/--regular-font."
    )


def make_cover(
    out_path,
    tag="AI 阅读笔记",
    title_lines=None,
    quote_lines=None,
    subtitle="",
    top_color=(25, 24, 60),
    bottom_color=(58, 28, 82),
    accent=(255, 209, 102),
    bold_font_path=None,
    regular_font_path=None,
):
    title_lines = title_lines or []
    quote_lines = quote_lines or []
    bold_font_path = bold_font_path or first_existing(BOLD_FONT_CANDIDATES)
    regular_font_path = regular_font_path or first_existing(REGULAR_FONT_CANDIDATES)

    img = Image.new("RGB", (W, H), top_color)
    draw = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        r = int(top_color[0] + (bottom_color[0] - top_color[0]) * t)
        g = int(top_color[1] + (bottom_color[1] - top_color[1]) * t)
        b = int(top_color[2] + (bottom_color[2] - top_color[2]) * t)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    font_tag = ImageFont.truetype(regular_font_path, 34)
    font_title = ImageFont.truetype(bold_font_path, 76)
    font_quote = ImageFont.truetype(bold_font_path, 52)
    font_sub = ImageFont.truetype(regular_font_path, 36)

    white = (255, 255, 255)
    faint = (210, 205, 230)

    if tag:
        pill_w = 300
        draw.rounded_rectangle([(70, 110), (70 + pill_w, 172)], radius=31, outline=accent, width=2)
        bbox = draw.textbbox((0, 0), tag, font=font_tag)
        tw = bbox[2] - bbox[0]
        draw.text((70 + (pill_w - tw) / 2, 122), tag, font=font_tag, fill=accent)

    y = 260
    for line in title_lines:
        draw.text((70, y), line, font=font_title, fill=white)
        y += 96

    if title_lines:
        draw.line([(70, y + 20), (70 + 120, y + 20)], fill=accent, width=6)
        y += 70

    for line in quote_lines:
        draw.text((70, y), line, font=font_quote, fill=faint)
        y += 68

    if subtitle:
        draw.text((70, H - 140), subtitle, font=font_sub, fill=faint)

    img.save(out_path, quality=95)
    return out_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--tag", default="AI 阅读笔记")
    parser.add_argument("--title", nargs="*", default=[])
    parser.add_argument("--quote", nargs="*", default=[])
    parser.add_argument("--subtitle", default="")
    parser.add_argument("--bold-font")
    parser.add_argument("--regular-font")
    args = parser.parse_args()

    out = make_cover(
        args.out,
        tag=args.tag,
        title_lines=args.title,
        quote_lines=args.quote,
        subtitle=args.subtitle,
        bold_font_path=args.bold_font,
        regular_font_path=args.regular_font,
    )
    print(out)


if __name__ == "__main__":
    main()
