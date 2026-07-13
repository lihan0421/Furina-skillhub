---
name: xiaohongshu-paper-explainer
description: Turn an academic paper (an arXiv link, or a paper the user pastes/describes) into a Xiaohongshu (小红书) note that explains it in plain language, using the paper's own figures alongside written cards. Use this whenever the user wants to write about, summarize, or post a paper/论文 to Xiaohongshu specifically - "帮我写一下这篇论文的小红书", "把这篇paper做成小红书笔记", "论文解读" - especially when they want real figures from the paper included, not just text. For a Xiaohongshu post that ISN'T about a paper, use the xiaohongshu-publish skill directly instead.
---

# Xiaohongshu Paper Explainer

Produces a Xiaohongshu "论文解读" (paper explainer) note: a card deck that mixes
short, plain-language write-up cards with the paper's own figures, in the
personal, hands-on voice this format uses on the platform - not a dry
abstract-and-methodology summary.

This skill only covers turning a paper into that specific format. It
depends on the **`xiaohongshu-publish`** skill for everything else: the
card-rendering engine (`make_cards.py`), and the actual
login/fill/preview/publish mechanics. Install that skill first if it isn't
already - this skill's scripts assume it's a sibling directory at
`../xiaohongshu-publish/`.

## Step 1: get the paper's text and figures

**If it's an arXiv paper**, use its `/html/` rendering, not the PDF - it's
plain server-rendered HTML with no anti-bot wall, so ordinary HTTP requests
work fine (unlike, say, a WeChat article, which needs a real browser to get
past its environment check).

1. Read the paper for content: `WebFetch` the `/html/<id>` URL (or `/abs/`,
   either works for reading) and ask it to extract the research problem,
   method, key numbers, and figure-by-figure descriptions in detail. Read
   enough to actually understand the mechanism, not just skim the abstract -
   the write-up in Step 3 needs to explain *how the thing works*, not just
   *that it works*.

2. Download the actual figure images:

   ```
   python scripts/fetch_paper_figures.py --url <arxiv URL> --out-dir figs/
   ```

   This writes `figs/fig_01.png`, `figs/fig_02.png`, ... plus
   `figs/manifest.json` (each entry has `index`, `path`, `caption`,
   `source_url`) so you can match figure numbers to what the paper's text
   calls them ("Figure 2", "Figure 6", etc.) without re-deriving URLs by
   hand.

3. Render a screenshot of the paper's own first page (title, authors,
   abstract) for the cover - this reads as far more credible than a
   generated title card, and is the standard opener for this format:

   ```
   python scripts/render_pdf_cover.py --url <arxiv URL> --out cover_shot.png
   ```

   `--top-fraction` (default 0.5) controls how much of the page height to
   keep - the default usually captures title/authors/abstract without
   trailing into body text. This needs PyMuPDF (`pip install pymupdf`) -
   install it once per machine if `render_pdf_cover.py` reports it's
   missing.

**If it's not on arXiv** (a PDF the user attached, a link to a publisher
page, etc.) - this is the common case, since users often just hand you a
local PDF:

1. Read it directly with the Read tool (works for local PDFs) or WebFetch
   (for a web page) to get the content. `fetch_paper_figures.py` doesn't
   apply here - it scrapes arXiv's HTML figure structure specifically -
   but `render_pdf_cover.py --pdf <local path>` still works for the cover
   screenshot, same as the arXiv case.

2. For the other figures, there's no reliable way to auto-locate "Figure 3"
   on an arbitrary PDF page - layouts vary too much between papers - so
   pull them with a short view-then-crop loop instead of one-shot
   extraction:

   ```
   # See the full page to find the figure's pixel coordinates
   python scripts/render_pdf_page.py --pdf paper.pdf --page 6 --out page_06.png
   ```

   Read the rendered page image, estimate the figure's bounding box, then
   crop it:

   ```
   python scripts/render_pdf_page.py --pdf paper.pdf --page 6 --out fig3_crop.png \
       --box 150,180,1650,960
   ```

   Read the crop back to check it - if it's cutting off part of the figure
   or dragging in surrounding text, adjust the box and rerun. Two or three
   iterations per figure is normal, not a sign anything's wrong - papers
   really do lay figures out too inconsistently for a fixed heuristic to
   get every crop right on the first try. Do this once per figure you
   picked in Step 2, at whatever page each one lives on.

## Step 2: don't use every figure

Papers have far more figures than a short explainer needs. Pick 2-5 that
actually carry the story - typically: one architecture/system diagram, one
headline result chart, and maybe one concrete example or case-study figure.
Skip ablation tables, appendix figures, and anything that needs the full
paper's context to parse. A card deck with 4 well-chosen figures reads
better than one with all 8 of the paper's figures crammed in.

This is also the point to decide arXiv-scraped vs. page-cropped for each
figure: `fetch_paper_figures.py` is faster when it works, but if a figure
you want is a multi-panel layout it splits awkwardly, or the paper isn't on
arXiv at all, use `render_pdf_page.py`'s view-then-crop loop from Step 1
instead - it works equally well against an arXiv paper's own PDF, not just
non-arXiv ones.

## Step 3: write in the paper-explainer voice, not the paper's voice

The point of this format is translation, not compression. A few things that
consistently make these read as a genuine personal take rather than a
repackaged abstract:

- **Open with a concrete hook, not the paper's title-and-abstract.** What's
  the one surprising or ballsy claim this paper makes? Lead with that.
- **First-person, hands-on framing where honest.** If you actually read the
  method closely enough to explain the mechanism, say so plainly ("这篇论文
  盯上一个很真实的现象..."). Don't fabricate having run code or reproduced
  results you didn't - the reference behavior this skill was built around
  is being a careful, engaged reader, not claiming false hands-on
  verification.
- **Explain the mechanism with a plain-language analogy before (or instead
  of) the paper's own terminology.** A reader deciding whether to keep
  swiping shouldn't need to already know the paper's jargon.
- **Concrete numbers over vague superlatives.** "4.58x throughput" lands
  harder than "significantly faster."
- **It's fine to note a limitation or a failure case the paper itself
  reports** - papers that include a "here's where it didn't work" moment
  make for a more credible, more interesting card than a highlight reel.
- **Write original paraphrase, not lifted sentences.** Summarize numbers,
  claims, and figure captions in your own words. Never reproduce paragraphs
  of the paper's actual text verbatim, even in translation-shaped
  paraphrase - the value of this format is your own compression and
  explanation of the idea, and copying substantial passages both defeats
  that purpose and raises copyright concerns. A short attribution line
  (title + arXiv id) at the end is enough credit.
- **Write enough per card that it reads as continuous narrative, not
  bullet-point fragments.** `make_cards.py`'s body text auto-fits its font
  size to fill each card's available height (see that script's docstring),
  which keeps a slightly-shorter card from visibly trailing into blank
  space - but that's a safety net, not a substitute for actually writing
  enough. A card with one short paragraph will just get blown up to a
  large, slightly odd-looking font rather than reading as a full page.
  Aim for 3-5 solid paragraphs per text card (each 1-3 sentences), and for
  image cards, a real caption of 2-4 sentences that both explains the
  figure *and* carries a bit of forward narrative - not a one-line label.
  If a section only has one short thing to say, look for the natural next
  point from the paper to fold in alongside it rather than leaving the
  card sparse.

Keep the title ≤20 characters. Each card should carry a real chunk of the
explanation - if a point runs long, that's fine (the auto-fit sizing keeps
it from overflowing down to a reasonable minimum size); split into a new
card only when you're moving to a genuinely different topic or figure, not
just because a card is getting text-dense.

## Step 4: build the deck

Default to the **`"editorial"`** theme for this format: plain white
background, serif body text, bold headings, no per-card chrome (no tag
chip, no ruled lines, no page counter) - it reads as one continuous
long-form piece cut into image-height pages, which is the dominant look for
this kind of paper-explainer post. Use `"notebook"` or `"dark"` instead only
if the user asks for a different feel.

The editorial theme supports two extra things worth using:
- **Highlighting**: wrap a key sentence or number in `==...==` inside a
  paragraph string to give it a highlighter-style background band - use
  this on the one or two most important claims per card, not everything.
- **Sub-points**: use `{"subhead": "小标题文字"}` as a paragraph-list entry
  to mark an enumerated point (e.g. "发现一：..." / "杠杆一：...") with a
  small gray left-bordered label, matching how these posts commonly break
  up a card into 2-3 named sub-findings instead of one flat paragraph.
- **Cover screenshot**: pass `cover.screenshot` (the image from
  `render_pdf_cover.py`) and `cover.read_time` (e.g. `"全文约2000字 · 阅读约6分钟"`)
  instead of `cover.tag`/`cover.quote` - this renders the paper's own first
  page fading into the title below it, instead of a generated title card.

Write a `cards.json` spec combining ordinary text cards and image cards (see
`../xiaohongshu-publish/references/cards_spec_example.json` for the full
schema, written against this theme). An image card uses `"image"` +
`"caption"` instead of `"title"`/`"paragraphs"`:

```json
{
  "tag": "",
  "image": "figs/fig_02.png",
  "caption": "先说清楚这张图在讲什么，而不是照抄论文的图注，再补一两句这张图对整体论证意味着什么、或者接下来要讲的东西是怎么从这里长出来的。"
}
```

(`tag` can be left as `""` in the editorial theme - it doesn't render a
visible chip - but text cards still take a `tag` argument positionally, so
keep the key present.)

Interleave figure cards with text cards rather than clustering all the text
first and all the figures at the end - each figure should land right after
the text card that sets it up, and its caption should read as a continuation
of that card's narrative rather than a standalone note. Then render:

```
python ../xiaohongshu-publish/scripts/make_cards.py --spec cards.json --out-dir cards/
```

## Step 5: write the title and hook body

Hand off to the `xiaohongshu-publish` skill for the actual
login/fill/preview/publish mechanics - follow that skill's SKILL.md for the
exact commands, this skill doesn't duplicate them. But the title and hook
body are specific to the paper-explainer format, so write them with this in
mind:

- **Work the paper's name or a recognizable abbreviation into the title**
  if it fits in 20 characters (e.g. `"DeepSWE:换基准见真章"`). A named
  benchmark or method reads as more credible and more searchable than a
  generic hook, and it's usually not hard to fit alongside a short hook
  phrase - don't drop it just because a hook-only title was shorter.
- **Make the hook body carry real information, not commentary about the
  post itself.** The body is prime real estate - it's what shows in the
  feed before anyone taps in - so spend it on the paper's actual claim and
  a concrete number, not on describing the card deck. Concretely, avoid a
  closing line like "论文原图直接放进去了，翻完就懂了" (or the English
  equivalent, "the paper's own figures are in here, read through and
  you'll get it") - it's true of every post this skill produces, so it
  says nothing this specific reader couldn't already guess, and it reads
  as filler. Close on a real finding instead: a number, a named failure
  mode, a comparison - something that couldn't be copy-pasted onto a
  different paper's post unchanged.
- Two short paragraphs is usually enough: one framing the problem/claim,
  one landing a concrete result or the most surprising specific finding.
  Hashtags go on their own last line, same convention as any
  `xiaohongshu-publish` post.
