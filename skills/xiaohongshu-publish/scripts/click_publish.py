"""
Click the real Xiaohongshu publish button.

Why this exists: as of 2026-07, Xiaohongshu renders the actual submit button
inside a closed shadow DOM custom element (<xhs-publish-btn>). Closed shadow
roots are invisible to querySelector AND to JS treewalkers, so the vendored
tool's own selector-based `_click_publish()` times out with
"Publish button did not become ready within 20s" even though the button is
sitting there, visible and clickable, in the bottom-right of the page.

The workaround: screenshot the page, find the button by its distinctive
brand-red color in the bottom-right quadrant (where the real submit button
lives), and dispatch a real mouse click at those coordinates. Coordinate
clicks don't care what's inside a shadow root - they hit whatever is
rendered on screen.

Two things this script protects against:
1. A decoy: the left sidebar has a nav item also labeled "发布笔记"
   (top-left, ~y 64-140). Restricting the color search to the
   bottom-right quadrant avoids ever matching it.
2. A minimized Chrome window: Browser.setWindowBounds silently no-ops if
   the window is minimized. This script restores + resizes it first.

Usage:
    python click_publish.py [--host 127.0.0.1] [--port 9222] [--reuse-existing-tab]
"""
import argparse
import base64
import io
import json
import sys
import time
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
VENDOR_SCRIPTS = SKILL_DIR / "vendor" / "XiaohongshuSkills" / "scripts"
sys.path.insert(0, str(VENDOR_SCRIPTS))

from cdp_publish import XiaohongshuPublisher  # noqa: E402


def ensure_window_not_minimized(publisher, width=1400, height=1000):
    win = publisher._send("Browser.getWindowForTarget", {})
    window_id = win.get("windowId")
    bounds = win.get("bounds", {})
    if bounds.get("windowState") == "minimized":
        publisher._send("Browser.setWindowBounds", {"windowId": window_id, "bounds": {"windowState": "normal"}})
        time.sleep(1.0)
    # Small windows can clip the publish button's scroll container. Make sure
    # there's enough room regardless of prior state.
    if bounds.get("width", 0) < width or bounds.get("height", 0) < height:
        publisher._send("Browser.setWindowBounds", {
            "windowId": window_id,
            "bounds": {"width": width, "height": height},
        })
        time.sleep(1.0)


def find_publish_button_css_coords(publisher):
    try:
        from PIL import Image
    except ImportError:
        raise SystemExit(
            "Pillow is required (pip install pillow) to locate the publish "
            "button by color."
        )

    shot = publisher._send("Page.captureScreenshot", {"format": "png"})
    img = Image.open(io.BytesIO(base64.b64decode(shot["data"])))
    w, h = img.size

    # Bottom-right quadrant only: this is where the real submit button lives,
    # and it keeps us well away from the sidebar decoy near the top-left.
    x0, y0 = int(w * 0.4), int(h * 0.85)
    minx = maxx = miny = maxy = None
    pixels = img.load()
    for y in range(y0, h):
        for x in range(x0, w):
            r, g, b = pixels[x, y][:3]
            if r > 200 and g < 80 and b < 100:
                minx = x if minx is None else min(minx, x)
                maxx = x if maxx is None else max(maxx, x)
                miny = y if miny is None else min(miny, y)
                maxy = y if maxy is None else max(maxy, y)

    if minx is None:
        raise RuntimeError(
            "Could not find the red publish button in the bottom-right of "
            "the screenshot. The page may not be fully filled yet, or the "
            "UI may have changed again - inspect the screenshot manually."
        )

    center_px_x = (minx + maxx) / 2
    center_px_y = (miny + maxy) / 2

    dpr = publisher._evaluate("(() => window.devicePixelRatio)()") or 1
    return center_px_x / dpr, center_px_y / dpr


def click_at(publisher, cx, cy):
    for event_type in ("mousePressed", "mouseReleased"):
        publisher._send("Input.dispatchMouseEvent", {
            "type": event_type,
            "x": cx,
            "y": cy,
            "button": "left",
            "clickCount": 1,
        })
        time.sleep(0.05)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9222)
    parser.add_argument("--reuse-existing-tab", action="store_true", default=True)
    args = parser.parse_args()

    publisher = XiaohongshuPublisher(host=args.host, port=args.port)
    publisher.connect(reuse_existing_tab=args.reuse_existing_tab)

    ensure_window_not_minimized(publisher)

    cx, cy = find_publish_button_css_coords(publisher)
    print(f"[click_publish] Clicking publish button at ({cx:.0f}, {cy:.0f})")
    click_at(publisher, cx, cy)

    time.sleep(3)
    try:
        result = publisher._evaluate(
            "(() => ({url: location.href, bodyText: document.body.innerText.slice(0, 300)}))()"
        )
    except Exception:
        # A native JS dialog (window.confirm/alert) blocks the renderer
        # thread - CDP calls like Runtime.evaluate and even
        # Page.captureScreenshot will hang/timeout while one is open, and
        # no amount of coordinate-clicking or re-screenshotting from here
        # can dismiss it. Don't loop retrying against a frozen page - hand
        # it back to the user.
        print(
            "PUBLISH_STATUS: UNKNOWN - the page stopped responding to CDP "
            "(likely a native browser dialog is open and blocking the "
            "renderer). Ask the user to check the Chrome window and click "
            "through/confirm manually rather than retrying this script."
        )
        return

    print(json.dumps(result, ensure_ascii=False, indent=2))

    url = result.get("url", "")
    body = result.get("bodyText", "")
    if "/publish/success" in url or "published=true" in url or "发布成功" in body:
        print("PUBLISH_STATUS: SUCCESS")
    else:
        print(
            "PUBLISH_STATUS: UNKNOWN - inspect the browser window to confirm. "
            "It's safe to run this script again once (it re-screenshots and "
            "relocates the button fresh each time). If a second attempt also "
            "doesn't change the URL, stop and ask the user to click publish "
            "manually instead of retrying further - repeated clicks against "
            "a page that isn't responding the way we expect risks doing "
            "something unintended on a real account."
        )


if __name__ == "__main__":
    main()
