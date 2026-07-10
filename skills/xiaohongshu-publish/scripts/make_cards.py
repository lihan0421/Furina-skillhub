# -*- coding: utf-8 -*-
"""
Render a set of Xiaohongshu note "cards" - 1080x1440 images with a
tag/title/body layout - from a JSON spec. Used when the text won't fit in
the 1000-char body limit, so the detailed write-up goes into a small image
carousel instead (a very common Xiaohongshu format for information-dense
posts).

Three themes are available:
- "dark": a dark gradient card, bold white title, gold accent (the
  original look this skill shipped with).
- "notebook": a light, clean "notebook page / sticky note" look - cream
  paper background with faint ruled lines, a rotated washi-tape strip
  holding the section tag, colors that rotate per card so the carousel
  doesn't feel monotonous.
- "editorial": a plain white "long read" look - no card chrome (no tag
  chip, no ruled lines, no page counter), serif body text, bold sans
  headings, highlighter-style bands behind key sentences (wrap a span in
  `==...==` to highlight it), and small gray left-bordered subheadings
  (use `{"subhead": "..."}` as a paragraph entry). Meant for paper/article
  explainers - see xiaohongshu-paper-explainer's SKILL.md, which uses this
  theme by default. The cover can embed a real screenshot (e.g. a paper's
  own first page) via `cover.screenshot` + `cover.read_time` instead of a
  generated title card.

Every text card and every image caption auto-fits its body font size to
fill the available vertical space (see fit_and_render_body) - a card
written a bit shorter than another still reads as a full page rather than
trailing off into blank space, and a card written a bit longer shrinks to
fit rather than overflowing. This means density in the JSON still matters
(write enough content that a card carries real narrative weight - a
one-sentence card will still get blown up in font size to fill the page,
which looks strange), but you don't have to hand-tune font sizes or line
counts per card to make the deck look consistent.

Usage:
    python make_cards.py --spec cards.json --out-dir cards/

Spec format (see references/cards_spec_example.json for a full example):
{
  "theme": "notebook",
  "cover": {
    "tag": "标签文字",
    "title": ["标题第一行", "标题第二行"],
    "quote": ["一句引用或钩子，可多行"],
    "subtitle": "来源 / 署名"
  },
  "cards": [
    {"tag": "章节标签", "title": "这张卡的标题", "paragraphs": ["第一段", "第二段，段内可以用 \\n 强制换行"]}
  ]
}

Paragraphs are wrapped automatically. Use "\\n" inside a paragraph string for
a manual line break (e.g. between numbered points); use separate paragraph
entries for the visual gap between paragraphs. A paragraph entry can also be
`{"subhead": "..."}` for a small labeled sub-point instead of a body
paragraph (see the "editorial" theme above).
"""
import argparse
import json
import os

from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1440
MARGIN = 72
MAX_W = W - MARGIN * 2

BOLD = "C:/Windows/Fonts/msyhbd.ttc"
REG = "C:/Windows/Fonts/msyh.ttc"
SERIF = "C:/Windows/Fonts/simsun.ttc"
# NOTE: simsunb.ttf ("SimSun Bold") is a Latin-only bold face - it has no
# CJK glyphs at all, so Chinese titles rendered with it show as tofu boxes.
# There's no good bold CJK serif on stock Windows, so titles in the
# editorial theme use the bold sans face instead; only body copy gets the
# serif "long read" look.
SERIF_BOLD = BOLD

THEMES = {
    "dark": {
        "kind": "gradient",
        "top": (20, 22, 46),
        "bottom": (46, 24, 74),
        "title_color": (255, 255, 255),
        "body_color": (200, 196, 224),
        "tag_colors": [((255, 209, 102), None)],  # (accent, unused) - single accent throughout
        "page_color": (200, 196, 224),
        "rule_lines": False,
    },
    "notebook": {
        "kind": "paper",
        "paper_color": (250, 246, 237),
        "rule_color": (225, 217, 199),
        "title_color": (58, 47, 38),
        "body_color": (74, 64, 55),
        "page_color": (150, 138, 120),
        "rule_lines": True,
        # (tape color, tape text/accent color) - rotates per card for variety
        "tag_colors": [
            ((255, 214, 145), (120, 78, 20)),
            ((168, 218, 220), (29, 53, 87)),
            ((241, 167, 160), (107, 44, 44)),
            ((181, 226, 164), (47, 82, 51)),
            ((201, 182, 228), (74, 59, 107)),
        ],
    },
    "editorial": {
        # A plain white "long read" look: no card chrome (no tag chip, no
        # ruled lines, no page counter) - reads as one continuous article
        # cut into image-height pages, the way many paper-explainer posts
        # on the platform are laid out. Body copy uses a serif face and key
        # sentences get a highlighter-style background band instead of
        # colored accents, and figures/tables sit inline in the text flow.
        "kind": "flat",
        "bg_color": (255, 255, 255),
        "title_color": (26, 26, 26),
        "body_color": (43, 43, 43),
        "subhead_color": (140, 140, 140),
        "page_color": (170, 170, 170),
        "highlight_color": (255, 231, 154),
        "tag_colors": [((26, 26, 26), None)],
        "rule_lines": False,
    },
}


def tokenize(text):
    tokens = []
    cur = ""
    for ch in text:
        if ch.isascii() and (ch.isalnum() or ch in "+-_./%"):
            cur += ch
        else:
            if cur:
                tokens.append(cur)
                cur = ""
            tokens.append(ch)
    if cur:
        tokens.append(cur)
    return tokens


def wrap_line(draw, text, font, max_w):
    lines = []
    cur = ""
    for tok in tokenize(text):
        test = cur + tok
        if draw.textlength(test, font=font) > max_w and cur:
            lines.append(cur)
            cur = tok
        else:
            cur = test
    if cur:
        lines.append(cur)
    return lines


def base_canvas(theme):
    if theme["kind"] == "gradient":
        img = Image.new("RGB", (W, H), theme["top"])
        draw = ImageDraw.Draw(img)
        top, bottom = theme["top"], theme["bottom"]
        for y in range(H):
            t = y / H
            r = int(top[0] + (bottom[0] - top[0]) * t)
            g = int(top[1] + (bottom[1] - top[1]) * t)
            b = int(top[2] + (bottom[2] - top[2]) * t)
            draw.line([(0, y), (W, y)], fill=(r, g, b))
        return img, draw

    if theme["kind"] == "flat":
        img = Image.new("RGB", (W, H), theme["bg_color"])
        return img, ImageDraw.Draw(img)

    # "paper" theme: flat cream background + faint horizontal rule lines,
    # like a notebook page.
    img = Image.new("RGB", (W, H), theme["paper_color"])
    draw = ImageDraw.Draw(img)
    if theme["rule_lines"]:
        y = 230
        while y < H - 60:
            draw.line([(MARGIN, y), (W - MARGIN, y)], fill=theme["rule_color"], width=2)
            y += 58
    return img, draw


def draw_tag(draw, theme, tag_color_idx, tag_text, x, y):
    """Draw the section tag. Dark theme: pill outline. Notebook theme: a
    rotated washi-tape strip, like a sticky note held down with tape."""
    tag_colors = theme["tag_colors"]
    accent, text_color = tag_colors[tag_color_idx % len(tag_colors)]

    if theme["kind"] == "flat":
        # No chip/pill here on purpose - the editorial look reads as one
        # continuous document, not a deck of individually-labeled cards.
        # Only draw anything if the caller actually passed a tag.
        if tag_text:
            f_tag = ImageFont.truetype(REG, 26)
            draw.text((x, y), tag_text, font=f_tag, fill=theme["subhead_color"])
        return theme["title_color"]

    if theme["kind"] == "gradient":
        f_tag = ImageFont.truetype(REG, 28)
        bbox = draw.textbbox((0, 0), tag_text, font=f_tag)
        tw = bbox[2] - bbox[0]
        pill_w = tw + 56
        draw.rounded_rectangle([(x, y), (x + pill_w, y + 52)], radius=26, outline=accent, width=2)
        draw.text((x + 28, y + 10), tag_text, font=f_tag, fill=accent)
        return accent

    # notebook theme: draw a rotated tape rectangle on its own small layer,
    # then paste it onto the card so the rotation doesn't clip.
    f_tag = ImageFont.truetype(BOLD, 30)
    tmp = Image.new("RGBA", (400, 120), (0, 0, 0, 0))
    tdraw = ImageDraw.Draw(tmp)
    bbox = tdraw.textbbox((0, 0), tag_text, font=f_tag)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tape_w, tape_h = tw + 64, 70
    tdraw.rectangle([(0, 0), (tape_w, tape_h)], fill=accent + (235,))
    tdraw.text((32, (tape_h - th) / 2 - bbox[1]), tag_text, font=f_tag, fill=text_color + (255,))
    rotated = tmp.crop((0, 0, tape_w, tape_h)).rotate(-3, expand=True, resample=Image.BICUBIC)
    draw._image.paste(rotated, (x, y), rotated)
    return accent


def tokenize_with_highlight(text):
    """Split text on '==highlighted==' markers into (token, is_highlighted)
    pairs, tokenized the same word-safe way as tokenize()."""
    segments = text.split("==")
    tokens = []
    for i, seg in enumerate(segments):
        highlighted = (i % 2 == 1)
        for tok in tokenize(seg):
            tokens.append((tok, highlighted))
    return tokens


def wrap_tokens_with_highlight(draw, tokens, font, max_w):
    lines = []
    cur, cur_w = [], 0
    for tok, hl in tokens:
        tw = draw.textlength(tok, font=font)
        if cur and cur_w + tw > max_w:
            lines.append(cur)
            cur, cur_w = [], 0
        cur.append((tok, hl))
        cur_w += tw
    if cur:
        lines.append(cur)
    return lines


def draw_highlighted_line(draw, line_tokens, font, x, y, line_h, color, highlight_color):
    """Draw one wrapped line, painting a highlighter-style band behind any
    tokens marked highlighted before drawing the text on top of it."""
    cx = x
    for tok, hl in line_tokens:
        tw = draw.textlength(tok, font=font)
        if hl and tok.strip():
            draw.rectangle([cx - 2, y + line_h * 0.18, cx + tw + 2, y + line_h * 0.92], fill=highlight_color)
        cx += tw
    cx = x
    for tok, hl in line_tokens:
        tw = draw.textlength(tok, font=font)
        draw.text((cx, y), tok, font=font, fill=color)
        cx += tw


def _layout_body(draw, paragraphs, f_body, f_subhead, max_w, is_flat, theme, x, y, line_h, subhead_line_h, render):
    """Shared paragraph-layout logic used both to measure how tall a body of
    text will be at a given font size (render=False, no drawing happens -
    just returns the final y) and to actually draw it (render=True). Reusing
    one function for both means the measurement can never silently drift
    out of sync with what actually gets drawn."""
    for para in paragraphs:
        if isinstance(para, dict) and "subhead" in para:
            label_lines = wrap_line(draw, para["subhead"], f_subhead, max_w - 30)
            bar_top = y
            for line in label_lines:
                if render:
                    draw.text((x + 26, y), line, font=f_subhead, fill=theme.get("subhead_color", theme["body_color"]))
                y += subhead_line_h
            if render:
                draw.rectangle([(x, bar_top + 4), (x + 5, y - 6)], fill=theme.get("page_color", theme["body_color"]))
            y += 18
            continue

        for hard_line in para.split("\n"):
            if is_flat and "==" in hard_line:
                tokens = tokenize_with_highlight(hard_line)
                for line_tokens in wrap_tokens_with_highlight(draw, tokens, f_body, max_w):
                    if render:
                        draw_highlighted_line(draw, line_tokens, f_body, x, y, line_h, theme["body_color"], theme["highlight_color"])
                    y += line_h
            else:
                for line in wrap_line(draw, hard_line, f_body, max_w):
                    if render:
                        draw.text((x, y), line, font=f_body, fill=theme["body_color"])
                    y += line_h
        y += round(26 * line_h / 48)
    return y


def fit_and_render_body(draw, paragraphs, max_w, is_flat, theme, body_font_path, subhead_font_path, x, y_start, y_max, sizes=(40, 38, 36, 34, 33, 31, 29, 27, 25)):
    """Pick the largest body font size (from `sizes`, descending) whose
    rendered content fits between y_start and y_max, then draw at that size.

    The point of sizing up rather than always using one fixed size is the
    thing this whole helper exists for: a card whose text was written a bit
    shorter than another still ends up reading as a full page instead of
    trailing off into blank space two-thirds of the way down - the same
    tool that prevents overflow on long cards also prevents visible empty
    space on short ones, so card density in the input JSON doesn't have to
    be hand-tuned per card to look right.
    """
    chosen_size = sizes[-1]
    for size in sizes:
        line_h = round(size * 48 / 33)
        subhead_size = max(18, round(size * 28 / 33))
        subhead_line_h = round(size * 40 / 33)
        f_body = ImageFont.truetype(body_font_path, size)
        f_subhead = ImageFont.truetype(subhead_font_path, subhead_size)
        end_y = _layout_body(draw, paragraphs, f_body, f_subhead, max_w, is_flat, theme, x, y_start, line_h, subhead_line_h, render=False)
        if end_y <= y_max:
            chosen_size = size
            break

    line_h = round(chosen_size * 48 / 33)
    subhead_size = max(18, round(chosen_size * 28 / 33))
    subhead_line_h = round(chosen_size * 40 / 33)
    f_body = ImageFont.truetype(body_font_path, chosen_size)
    f_subhead = ImageFont.truetype(subhead_font_path, subhead_size)
    _layout_body(draw, paragraphs, f_body, f_subhead, max_w, is_flat, theme, x, y_start, line_h, subhead_line_h, render=True)


def render_image_card(theme_name, out_path, page_label, tag_idx, tag_text, image_path, caption):
    """A card that embeds a real picture (e.g. a paper figure) instead of
    generated text, framed with the same tag/page-label chrome as a text
    card so it reads as part of the same deck rather than a pasted-in
    screenshot."""
    theme = THEMES[theme_name]
    img, draw = base_canvas(theme)
    draw._image = img

    is_flat = theme["kind"] == "flat"
    if not is_flat:
        draw_tag(draw, theme, tag_idx, tag_text, MARGIN, 88)
        f_page = ImageFont.truetype(REG, 26)
        pbbox = draw.textbbox((0, 0), page_label, font=f_page)
        pw = pbbox[2] - pbbox[0]
        draw.text((W - MARGIN - pw, 100), page_label, font=f_page, fill=theme["page_color"])
    elif tag_text:
        draw_tag(draw, theme, tag_idx, tag_text, MARGIN, 88)

    fig_raw = Image.open(image_path)
    if fig_raw.mode in ("RGBA", "LA") or (fig_raw.mode == "P" and "transparency" in fig_raw.info):
        # Figures exported from papers are often transparent-background
        # PNGs; naively converting straight to RGB turns transparent
        # pixels black. Composite onto white first so it reads correctly
        # as a "printed" figure on the card.
        fig_raw = fig_raw.convert("RGBA")
        white_bg = Image.new("RGB", fig_raw.size, (255, 255, 255))
        white_bg.paste(fig_raw, mask=fig_raw.split()[3])
        fig = white_bg
    else:
        fig = fig_raw.convert("RGB")
    box_w = MAX_W
    box_h = 880
    scale = min(box_w / fig.width, box_h / fig.height)
    new_w, new_h = int(fig.width * scale), int(fig.height * scale)
    fig = fig.resize((new_w, new_h), Image.LANCZOS)

    fx = MARGIN + (MAX_W - new_w) // 2
    fy = 200 if theme["kind"] != "flat" else 140
    if theme["kind"] != "flat":
        border = 3
        draw.rectangle(
            [(fx - border, fy - border), (fx + new_w + border, fy + new_h + border)],
            outline=theme["page_color"],
            width=border,
        )
    img.paste(fig, (fx, fy))

    y = fy + new_h + 40
    body_font_path = SERIF if theme["kind"] == "flat" else REG
    # Caption gets its own (smaller) size ladder than a full text card - it's
    # explaining a figure that's already doing most of the visual work, so
    # it shouldn't grow large enough to compete with it, but it still
    # shouldn't trail off into a mostly-empty lower half of the card either.
    fit_and_render_body(draw, [caption], MAX_W, is_flat, theme, body_font_path, REG, MARGIN, y, H - 90, sizes=(34, 32, 30, 28, 26, 24))

    img.save(out_path, quality=95)


def render_editorial_cover(theme, img, draw, out_path, cover):
    """Editorial-theme cover: a reading-time line, then the paper's own
    first-page screenshot (faded out at the bottom so it blends into the
    page instead of ending in a hard edge), then a bold hook title and an
    indented quote-bar subtitle underneath - not a generated title card."""
    y = 90
    if cover.get("read_time"):
        f_meta = ImageFont.truetype(REG, 30)
        draw.text((MARGIN, y), cover["read_time"], font=f_meta, fill=theme["subhead_color"])
        y += 46
        draw.line([(MARGIN, y), (W - MARGIN, y)], fill=(225, 225, 225), width=2)
        y += 30

    shot = Image.open(cover["screenshot"]).convert("RGB")
    shot_w = MAX_W
    shot_h = int(shot.height * (shot_w / shot.width))
    shot_h = min(shot_h, 620)
    scale = shot_w / shot.width
    crop_h = int(shot_h / scale)
    shot = shot.crop((0, 0, shot.width, min(crop_h, shot.height)))
    shot = shot.resize((shot_w, int(shot.height * scale)), Image.LANCZOS)

    # Fade the bottom ~30% of the screenshot into the page background so it
    # reads as "trailing off" rather than being cut off mid-page.
    fade = Image.new("L", shot.size, 255)
    fade_draw = ImageDraw.Draw(fade)
    fade_start = int(shot.height * 0.7)
    for fy in range(fade_start, shot.height):
        t = (fy - fade_start) / max(1, (shot.height - fade_start))
        fade_draw.line([(0, fy), (shot.width, fy)], fill=int(255 * (1 - t)))
    white_layer = Image.new("RGB", shot.size, theme["bg_color"])
    shot = Image.composite(shot, white_layer, fade)

    img.paste(shot, (MARGIN, y))
    y += shot.height + 50

    f_title = ImageFont.truetype(BOLD, 62)
    for line in cover["title"]:
        for wrapped in wrap_line(draw, line, f_title, MAX_W):
            draw.text((MARGIN, y), wrapped, font=f_title, fill=theme["title_color"])
            y += 76
    y += 20

    subtitle = cover.get("subtitle", "")
    if subtitle:
        f_sub = ImageFont.truetype(BOLD, 32)
        lines = wrap_line(draw, subtitle, f_sub, MAX_W - 40)
        bar_top = y
        for line in lines:
            draw.text((MARGIN + 32, y), line, font=f_sub, fill=theme["body_color"])
            y += 44
        draw.rectangle([(MARGIN, bar_top + 4), (MARGIN + 6, y - 8)], fill=theme["title_color"])

    img.save(out_path, quality=95)


def render(theme_name, out_path, page_label, tag_idx, tag_text, title, paragraphs, cover=None):
    theme = THEMES[theme_name]
    img, draw = base_canvas(theme)
    draw._image = img  # so draw_tag can paste onto it for the notebook theme

    if cover:
        if theme["kind"] == "flat" and cover.get("screenshot"):
            render_editorial_cover(theme, img, draw, out_path, cover)
            return

        accent = draw_tag(draw, theme, tag_idx, tag_text, MARGIN, 100)
        y = 260
        f_title = ImageFont.truetype(BOLD, 72)
        for line in cover["title"]:
            draw.text((MARGIN, y), line, font=f_title, fill=theme["title_color"])
            y += 90
        draw.line([(MARGIN, y + 18), (MARGIN + 120, y + 18)], fill=accent, width=6)
        y += 66
        f_quote = ImageFont.truetype(BOLD, 42)
        for line in cover.get("quote", []):
            draw.text((MARGIN, y), line, font=f_quote, fill=theme["body_color"])
            y += 56
        if cover.get("subtitle"):
            draw.text((MARGIN, H - 120), cover["subtitle"], font=ImageFont.truetype(REG, 30), fill=theme["body_color"])
        img.save(out_path, quality=95)
        return

    is_flat = theme["kind"] == "flat"

    y = 90
    if not is_flat:
        draw_tag(draw, theme, tag_idx, tag_text, MARGIN, 88)
        f_page = ImageFont.truetype(REG, 26)
        pbbox = draw.textbbox((0, 0), page_label, font=f_page)
        pw = pbbox[2] - pbbox[0]
        draw.text((W - MARGIN - pw, 100), page_label, font=f_page, fill=theme["page_color"])
        y = 210

    body_font_path = SERIF if is_flat else REG
    title_font_path = SERIF_BOLD if is_flat else BOLD

    if title:
        f_title = ImageFont.truetype(title_font_path, 50 if is_flat else 56)
        for line in wrap_line(draw, title, f_title, MAX_W):
            draw.text((MARGIN, y), line, font=f_title, fill=theme["title_color"])
            y += 66 if is_flat else 70
        if not is_flat:
            accent = theme["tag_colors"][tag_idx % len(theme["tag_colors"])][0]
            draw.line([(MARGIN, y + 12), (MARGIN + 100, y + 12)], fill=accent, width=5)
        y += 54

    # Auto-fit the body font size so the card's text fills the page down to
    # near the bottom margin instead of trailing off into blank space -
    # see fit_and_render_body's docstring for why this is a size search
    # rather than one fixed font size.
    fit_and_render_body(draw, paragraphs, MAX_W, is_flat, theme, body_font_path, REG, MARGIN, y, H - 90)

    img.save(out_path, quality=95)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--spec", required=True, help="Path to a cards JSON spec")
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    with open(args.spec, encoding="utf-8") as f:
        spec = json.load(f)

    theme_name = spec.get("theme", "dark")
    os.makedirs(args.out_dir, exist_ok=True)

    total = len(spec.get("cards", [])) + (1 if spec.get("cover") else 0)
    n = 1
    paths = []

    if spec.get("cover"):
        out_path = os.path.join(args.out_dir, f"card_{n:02d}.jpg")
        render(theme_name, out_path, "", 0, spec["cover"].get("tag", ""), None, None, cover=spec["cover"])
        paths.append(out_path)
        n += 1

    for i, card in enumerate(spec.get("cards", [])):
        out_path = os.path.join(args.out_dir, f"card_{n:02d}.jpg")
        page_label = f"{n:02d}/{total:02d}"
        if "image" in card:
            render_image_card(theme_name, out_path, page_label, i, card["tag"], card["image"], card.get("caption", ""))
        else:
            render(theme_name, out_path, page_label, i, card["tag"], card["title"], card["paragraphs"])
        paths.append(out_path)
        n += 1

    for p in paths:
        print(p)


if __name__ == "__main__":
    main()
