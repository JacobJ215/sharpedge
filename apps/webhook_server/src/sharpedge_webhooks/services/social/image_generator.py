"""Generate branded image cards for social media posts."""

from __future__ import annotations

import io

# ---------------------------------------------------------------------------
# Graceful Pillow import
# ---------------------------------------------------------------------------
try:
    from PIL import Image, ImageDraw, ImageFont  # type: ignore

    _PILLOW_AVAILABLE = True
except ImportError:
    _PILLOW_AVAILABLE = False

# ---------------------------------------------------------------------------
# Design constants
# ---------------------------------------------------------------------------
_CANVAS_SIZE = (1080, 1080)
_BG_TOP = (10, 14, 26)  # #0A0E1A
_BG_BOTTOM = (15, 20, 33)  # #0F1421
_TEAL = (0, 212, 170)  # #00D4AA
_AMBER = (245, 158, 11)  # #F59E0B
_WHITE = (255, 255, 255)
_GREY = (160, 170, 190)
_DARK_TEAL_BG = (0, 60, 50)


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------


def _make_canvas() -> Image.Image:
    """Create a 1080x1080 canvas with a vertical gradient background."""
    img = Image.new("RGB", _CANVAS_SIZE, _BG_TOP)
    draw = ImageDraw.Draw(img)
    w, h = _CANVAS_SIZE
    for y in range(h):
        ratio = y / h
        r = int(_BG_TOP[0] + (_BG_BOTTOM[0] - _BG_TOP[0]) * ratio)
        g = int(_BG_TOP[1] + (_BG_BOTTOM[1] - _BG_TOP[1]) * ratio)
        b = int(_BG_TOP[2] + (_BG_BOTTOM[2] - _BG_TOP[2]) * ratio)
        draw.line([(0, y), (w, y)], fill=(r, g, b))
    return img


def _draw_chrome(draw: ImageDraw.ImageDraw, accent: tuple[int, int, int]) -> None:
    """Draw the top accent bar, logo monogram, and wordmark."""
    w, _ = _CANVAS_SIZE

    # Top accent bar
    draw.rectangle([(0, 0), (w, 6)], fill=accent)

    # "SE" monogram (top-left)
    draw.rectangle([(30, 20), (80, 70)], fill=accent)
    try:
        font_logo = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 28)
    except OSError:
        font_logo = ImageFont.load_default()
    draw.text((36, 24), "SE", fill=_BG_TOP, font=font_logo)

    # "SHARPEDGE" wordmark (top-right)
    try:
        font_word = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 22)
    except OSError:
        font_word = ImageFont.load_default()
    draw.text((w - 200, 30), "SHARPEDGE", fill=_GREY, font=font_word)

    # Bottom strip
    try:
        font_small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 18)
    except OSError:
        font_small = ImageFont.load_default()
    draw.text((w // 2 - 70, _CANVAS_SIZE[1] - 36), "sharpedge.ai", fill=_GREY, font=font_small)


def _draw_ev_badge(draw: ImageDraw.ImageDraw, ev_text: str, cx: int, y: int) -> None:
    """Draw a rounded-rect EV badge centred on cx at y."""
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 26)
    except OSError:
        font = ImageFont.load_default()

    # Measure text width for badge sizing
    bbox = draw.textbbox((0, 0), ev_text, font=font)
    tw = bbox[2] - bbox[0]
    pad_x, pad_y = 20, 10
    bx0 = cx - tw // 2 - pad_x
    bx1 = cx + tw // 2 + pad_x
    by0, by1 = y, y + (bbox[3] - bbox[1]) + pad_y * 2

    draw.rounded_rectangle([(bx0, by0), (bx1, by1)], radius=12, fill=_TEAL)
    draw.text((cx - tw // 2, by0 + pad_y), ev_text, fill=_BG_TOP, font=font)


def _fmt_odds(odds: int | float) -> str:
    odds = int(odds)
    return f"+{odds}" if odds >= 0 else str(odds)


def _render_to_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_alert_card(play: dict) -> bytes | None:
    """Generate 1080x1080 alert card PNG. Returns bytes or None if Pillow unavailable."""
    if not _PILLOW_AVAILABLE:
        return None

    img = _make_canvas()
    draw = ImageDraw.Draw(img)
    _draw_chrome(draw, _TEAL)

    w, _h = _CANVAS_SIZE
    cx = w // 2

    game = str(play.get("game") or play.get("event", "Unknown Game"))
    side = str(play.get("side") or play.get("team", ""))
    market = str(play.get("bet_type") or play.get("market", ""))
    book = str(play.get("sportsbook") or play.get("book", ""))
    odds_raw = play.get("market_odds") or play.get("book_odds") or 0
    ev_raw = play.get("ev_percentage") or play.get("expected_value", 0)
    ev = float(ev_raw) if float(ev_raw) > 1 else float(ev_raw) * 100

    # "VALUE PLAY ALERT" label
    try:
        font_label = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 22)
        font_game = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 52)
        font_side = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 38)
        font_sub = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
    except OSError:
        font_label = font_game = font_side = font_sub = ImageFont.load_default()

    draw.text((cx - 100, 120), "VALUE PLAY ALERT", fill=_TEAL, font=font_label)

    # Divider
    draw.line([(80, 165), (w - 80, 165)], fill=_TEAL, width=1)

    # Game name (truncate if too long)
    game_display = game[:38] + "\u2026" if len(game) > 38 else game
    bbox = draw.textbbox((0, 0), game_display, font=font_game)
    draw.text((cx - (bbox[2] - bbox[0]) // 2, 340), game_display, fill=_WHITE, font=font_game)

    # Pick (side)
    bbox = draw.textbbox((0, 0), side, font=font_side)
    draw.text((cx - (bbox[2] - bbox[0]) // 2, 430), side, fill=_TEAL, font=font_side)

    # EV badge
    _draw_ev_badge(draw, f"+{ev:.1f}% EV", cx, 510)

    # Book + odds
    book_line = f"{book}  {_fmt_odds(odds_raw)}"
    bbox = draw.textbbox((0, 0), book_line, font=font_sub)
    draw.text((cx - (bbox[2] - bbox[0]) // 2, 600), book_line, fill=_GREY, font=font_sub)

    # Market label
    bbox = draw.textbbox((0, 0), market, font=font_sub)
    draw.text((cx - (bbox[2] - bbox[0]) // 2, 650), market, fill=_GREY, font=font_sub)

    return _render_to_bytes(img)


def generate_win_card(bet: dict, profit: float, roi: float) -> bytes | None:
    """Generate 1080x1080 win announcement card PNG. Returns bytes or None if Pillow unavailable."""
    if not _PILLOW_AVAILABLE:
        return None

    img = _make_canvas()
    draw = ImageDraw.Draw(img)
    _draw_chrome(draw, _TEAL)

    w, _ = _CANVAS_SIZE
    cx = w // 2

    game = str(bet.get("game") or bet.get("event", "Unknown Game"))
    selection = str(bet.get("selection") or bet.get("side") or bet.get("team", ""))
    odds_raw = bet.get("odds") or bet.get("book_odds") or 0

    try:
        font_winner = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 64)
        font_game = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 38)
        font_pick = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 32)
        font_profit = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 72)
        font_sub = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
    except OSError:
        font_winner = font_game = font_pick = font_profit = font_sub = ImageFont.load_default()

    # "WINNER" banner
    winner_text = "\U0001f3c6  WINNER!"
    bbox = draw.textbbox((0, 0), winner_text, font=font_winner)
    draw.text((cx - (bbox[2] - bbox[0]) // 2, 130), winner_text, fill=_TEAL, font=font_winner)

    # Divider
    draw.line([(80, 225), (w - 80, 225)], fill=_TEAL, width=1)

    # Game
    game_display = game[:42] + "\u2026" if len(game) > 42 else game
    bbox = draw.textbbox((0, 0), game_display, font=font_game)
    draw.text((cx - (bbox[2] - bbox[0]) // 2, 320), game_display, fill=_WHITE, font=font_game)

    # Selection + checkmark
    pick_line = f"{selection} \u2705"
    bbox = draw.textbbox((0, 0), pick_line, font=font_pick)
    draw.text((cx - (bbox[2] - bbox[0]) // 2, 390), pick_line, fill=_WHITE, font=font_pick)

    # Odds
    odds_line = f"Odds: {_fmt_odds(odds_raw)}"
    bbox = draw.textbbox((0, 0), odds_line, font=font_sub)
    draw.text((cx - (bbox[2] - bbox[0]) // 2, 450), odds_line, fill=_GREY, font=font_sub)

    # Profit (large teal)
    profit_text = f"+${profit:,.2f}"
    bbox = draw.textbbox((0, 0), profit_text, font=font_profit)
    draw.text((cx - (bbox[2] - bbox[0]) // 2, 530), profit_text, fill=_TEAL, font=font_profit)

    # ROI line
    roi_line = f"Season ROI: +{roi:.1f}%"
    bbox = draw.textbbox((0, 0), roi_line, font=font_sub)
    draw.text((cx - (bbox[2] - bbox[0]) // 2, 640), roi_line, fill=_GREY, font=font_sub)

    return _render_to_bytes(img)
