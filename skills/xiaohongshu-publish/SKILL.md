---
name: xiaohongshu-publish
description: Publish a note (title + body + cover image, optionally topic tags) to the user's Xiaohongshu (小红书/RED) account via browser automation. Use this whenever the user asks to write or publish a Xiaohongshu/小红书 post, wants something "发到小红书" or "发布笔记", or asks to turn an article/idea into a 小红书文案 and post it - even if they don't mention automation explicitly. Do not use this just to draft copy in that style without a request to actually publish it.
---

# Xiaohongshu Publish

Automates posting a note to Xiaohongshu through the vendored `XiaohongshuSkills`
CDP tool in `vendor/XiaohongshuSkills/`. Publishing is a public, hard-to-reverse
action on the user's real account, so this skill is built around a
fill-then-confirm-then-click sequence, not a single fire-and-forget command.

## Before you start: read the risk note

The vendored tool's own README says platform automation risks rate-limiting
or account restriction. That's a real constraint, not boilerplate - don't loop
this skill to test things or "try again" more than once or twice without the
user in the loop. One real publish per user request.

## Step 0: one-time setup

The tool lives at `vendor/XiaohongshuSkills/` next to this SKILL.md - already
vendored, no need to clone it again. Just make sure dependencies are
installed once per machine:

```
python -m pip install -r vendor/XiaohongshuSkills/requirements.txt
```

(It's just `requests` and `websockets` - fast and safe to re-run.)

## Step 1: check / establish login

```
python vendor/XiaohongshuSkills/scripts/cdp_publish.py check-login
```

Login is cached locally for ~12h, so this is often already good. If it
reports not logged in:

```
python vendor/XiaohongshuSkills/scripts/cdp_publish.py login
```

This opens a headed Chrome window with a QR code. Tell the user to scan it
with the Xiaohongshu app on their phone, then re-run `check-login` to
confirm before moving on.

## Step 2: write the content, respecting the platform's real limits

- **Title: 20 characters max.** This is a hard platform limit, not a style
  suggestion - count with Python (`len(text)` on the actual string, since
  wc -m and byte-counting tools misreport CJK text) before filling the form.
- **Body: 1000 characters max.** Same rule - count before filling.
- Put hashtags on the **last line** of the body, e.g.
  `#AI #Agent #技术分享` - the tool auto-detects that line as topic tags and
  clicks them into the topic picker.
- Match whatever tone/register the user asked for (this skill doesn't
  prescribe a writing style - that's a separate concern from the mechanics
  of getting it published). Save the title and body to two small text files
  so they can be handed to the fill command below.

## Step 3: cover image, or a full card carousel

If the user already has an image (a screenshot, a photo, an existing asset),
use that as the single cover image and skip to Step 4.

**If there's no image**, or **the write-up is too detailed for the 1000-char
body limit**, generate images with the text instead - this is a completely
normal Xiaohongshu format (an image carousel of "note cards"), not a
workaround. Two tools cover the two cases:

### Just need *a* cover (short post, no real image)

```
python scripts/make_cover.py --out cover.jpg \
    --tag "AI 阅读笔记" \
    --title "第一行标题" "第二行标题" \
    --quote "一句引用或金句" \
    --subtitle "来源/署名"
```

`--title`/`--quote` take multiple lines (wrap manually wherever reads best);
`--tag` and `--subtitle` are optional.

### The content itself doesn't fit in 1000 characters

Put the detailed write-up into a multi-image carousel instead of trying to
compress it - Xiaohongshu supports up to 18 images per note, and dense,
information-heavy carousels are a normal format on the platform, not a
compromise. Write a JSON spec (see
`references/cards_spec_example.json` for the exact shape: a `cover` block
plus a `cards` array, each card with `tag`/`title`/`paragraphs`), then:

```
python scripts/make_cards.py --spec cards.json --out-dir cards/
```

This renders one 1080x1440 image per card, with text wrapped and page
numbers ("03/09" etc.) added automatically - you don't need to hand-tune
line breaks or coordinates, just write the content. Two themes are built in:

- `"dark"` - a dark gradient card, bold white title, gold accent. The
  original look this skill shipped with.
- `"notebook"` - a light, clean "notebook page / sticky note" look: cream
  paper background with faint ruled lines, a rotated washi-tape strip
  holding the section tag, and accent colors that rotate per card so a long
  carousel doesn't feel monotonous. Use this when the user asks for
  something cleaner/fresher-looking than the dark theme.

Pick whichever theme suits the user's ask (or ask them if it's not obvious).
Both scripts fall back to Microsoft YaHei fonts on Windows
(`C:/Windows/Fonts/msyhbd.ttc` / `msyh.ttc`) - if you're ever on a machine
without them, pass different font paths or add a candidate list the same
way `make_cards.py` already does for its two font roles.

If the user wants a genuinely custom visual design beyond what these two
themes offer, consider the `dataviz` or `artifact-design` skills for the
card art itself, then pass the resulting image paths into Step 4 the same
way.

## Step 4: fill the form in preview mode and get user confirmation

```
python vendor/XiaohongshuSkills/scripts/publish_pipeline.py --preview \
    --title-file title.txt \
    --content-file content.txt \
    --images cover.jpg \
    --reuse-existing-tab
```

`--preview` fills the title/body/image/tags into the real Chrome window
*without* clicking publish. This always comes before the final click -
**show the user what's in the browser and get an explicit go-ahead** before
Step 5, the same way you'd confirm before any other action that posts
publicly under the user's name.

If anything needs to change (title too long, wrong image, tone off), fix the
files and re-run this fill step - it's fully idempotent and safe to repeat.

## Step 5: actually publish

Once the user has confirmed the preview, click publish:

```
python scripts/click_publish.py --reuse-existing-tab
```

**Don't use the vendored tool's own `publish` command or `_click_publish()`
for the final click** - as of 2026-07 it's broken against the live site (see
"Known bug" below) and will either time out or, worse, land on the wrong
element. `scripts/click_publish.py` in this skill is the tested workaround;
use it instead.

Check its output: success shows a URL containing `/publish/success` or
`published=true`, or body text containing `发布成功`. If it instead raises
"Could not find the red publish button," take a screenshot yourself
(`Page.captureScreenshot` via the same CDP connection, or just look at the
Chrome window) - the UI may have changed again, and the color-based heuristic
in `find_publish_button_css_coords()` may need adjusting.

**If the click doesn't seem to do anything** (URL and body text unchanged,
status comes back `UNKNOWN`), it's fine to run the script again once - it
re-screenshots and relocates the button fresh every time. But if a *second*
attempt also doesn't change anything, or a CDP call (screenshot or evaluate)
times out outright, stop and ask the user to click publish themselves in the
Chrome window rather than retrying further. A hung CDP call there usually
means a native browser dialog (`window.confirm`/`alert`) popped up and is
blocking the renderer thread - no amount of re-screenshotting or coordinate
guessing from this side can see through that, only a human looking at the
actual window can. Repeatedly firing clicks at a page that isn't responding
the way you expect is exactly the kind of thing to avoid on a real account.

### Known bug: why the vendored tool's own publish-click is unreliable

Xiaohongshu currently renders the real submit button inside a **closed shadow
DOM** custom element, `<xhs-publish-btn>`. Closed shadow roots are invisible
to `querySelector` *and* to JS tree-walkers - there's no selector that can see
inside one. That's why `_is_publish_button_ready()` in the vendored tool times
out ("Publish button did not become ready within 20s") even when the button
is sitting there, fully visible and clickable, on screen.

Coordinate-based clicks don't care what's inside a shadow root, so
`click_publish.py` takes a screenshot, finds the button by its brand-red
pixel color in the **bottom-right quadrant** of the page, and dispatches a
real mouse click there. Restricting the search to the bottom-right is not
an arbitrary choice - it's what keeps this from ever hitting the decoy
below.

**The decoy:** the left sidebar has its own nav item labeled "发布笔记"
(top-left of the page, roughly y 64-140px). It looks like a plausible match
if you search the whole page for that text, but clicking it just switches to
the video-upload tab and throws away everything filled in Steps 2-4. If a
fill-then-click attempt ever lands on the wrong place and the browser
navigates away from the image/text editor, don't try to recover the old
state - just redo Step 4's fill and continue from there.

**Minimized window gotcha:** if `Browser.getWindowForTarget` reports
`windowState: "minimized"`, calls to `Browser.setWindowBounds` with just a
width/height silently no-op - the window has to be restored to `"normal"`
state first, then resized. `click_publish.py` already does this
automatically before screenshotting; mention it here mainly so that if you
end up debugging this by hand, you know why a resize call did nothing.
