"""Monday 23 November 2026, as one picture.

Pure Python standard library. Draws a 1024x1024 newspaper front page
-- masthead, UTC timeline, 16 illustrated lead stories, a world map
with numbered pins, stories 17-50 in a numbered list, a date check
and a sourcing footer -- from a hand-drawn 8x8 bitmap font in
fontdata.py. No network, no clock, no randomness: two runs write
identical bytes.

Every story happened, or was first reported, on Monday 23 November
2026 in at least one time zone. CLAIM marks one side's account, not
an independently confirmed fact. The page was built at about 16:00
UTC on 24 November, after the day had ended everywhere; the DATE
CHECK box names the big stories left out because they belong to
another date, and what had not happened yet.
"""
import os
import struct
import sys
import zlib

# The grader runs `python3 -P -s`, which leaves the script's own
# directory off sys.path: put it back so fontdata is importable.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fontdata import advance, rows_for

PAGE_W, PAGE_H = 1024, 1024
MARGIN = 28
CONTENT_W = PAGE_W - 2 * MARGIN

PAPER = (247, 241, 222)
CARD = (255, 252, 242)
INK = (26, 26, 26)
RED = (143, 29, 33)
MAROON = (112, 20, 24)
MUTED = (104, 94, 78)
RULE = (176, 164, 136)
LAND = (203, 192, 158)
SEA = (226, 232, 228)
GREEN = (34, 120, 60)
DATE_BG = (238, 232, 210)

REGION_TINT = {
    "Europe": (216, 228, 242),
    "Middle East": (242, 216, 198),
    "Asia": (214, 236, 214),
    "Americas": (242, 232, 196),
    "Africa": (234, 214, 234),
    "Oceania": (198, 232, 230),
    "Global": (228, 228, 228),
}
PIN_COLOUR = {
    "Europe": (60, 100, 180),
    "Middle East": (220, 120, 40),
    "Asia": (130, 80, 160),
    "Americas": (180, 40, 40),
    "Africa": (40, 130, 70),
    "Oceania": (40, 140, 140),
    "Global": (90, 90, 90),
}


class Sheet:
    """An RGB canvas backed by one flat bytearray."""

    def __init__(self, w, h, bg):
        self.w, self.h = w, h
        self.px = bytearray(bg) * (w * h)

    def _off(self, x, y):
        return (y * self.w + x) * 3

    def dot(self, x, y, colour):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = self._off(x, y)
            self.px[i:i + 3] = bytes(colour)

    def box(self, x, y, w, h, colour):
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.w, x + w), min(self.h, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(colour) * (x1 - x0)
        for yy in range(y0, y1):
            i = self._off(x0, yy)
            self.px[i:i + len(row)] = row

    def hrule(self, x, y, w, colour):
        self.box(x, y, w, 1, colour)

    def vrule(self, x, y, h, colour):
        self.box(x, y, 1, h, colour)

    def seg(self, x0, y0, x1, y1, colour):
        """Bresenham line between two points."""
        dx, dy = abs(x1 - x0), abs(y0 - y1)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        while True:
            self.dot(x0, y0, colour)
            if x0 == x1 and y0 == y1:
                return
            step = 2 * err
            if step > -dy:
                err -= dy
                x0 += sx
            if step < dx:
                err += dx
                y0 += sy

    def disc(self, cx, cy, r, colour):
        for yy in range(cy - r, cy + r + 1):
            for xx in range(cx - r, cx + r + 1):
                if (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r:
                    self.dot(xx, yy, colour)

    def ring(self, cx, cy, r, colour, thick=1):
        for yy in range(cy - r - thick, cy + r + thick + 1):
            for xx in range(cx - r - thick, cx + r + thick + 1):
                d = ((xx - cx) ** 2 + (yy - cy) ** 2) ** 0.5
                if r - thick < d <= r:
                    self.dot(xx, yy, colour)

    def fill(self, pts, colour):
        """Scanline fill of a polygon given as (x, y) points."""
        if not pts:
            return
        top = min(p[1] for p in pts)
        bottom = max(p[1] for p in pts)
        n = len(pts)
        for y in range(top, bottom + 1):
            xs = []
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    xs.append(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                xa, xb = int(xs[k]), int(xs[k + 1])
                if xb > xa:
                    self.box(xa, y, xb - xa, 1, colour)


# ---- text, from the 8x8 bitmap font ----
#
# A glyph cell is 8 rows tall; cap height is 7 of those rows, so a
# requested size means scale = size / 7 and the cell on the page is
# round(8 * size / 7) pixels tall. Text is placed by the top of its
# cell; descenders live in the cell's last row.

def cell_h(size):
    return max(1, round(8 * size / 7.0))


def text_w(text, size):
    units = 0
    for ch in text:
        units += advance(ch)
    return units * size / 7.0


def draw_text(sheet, text, size, x, y, colour, bold=False):
    """Draw text with its cell top at (x, y); return the x after it."""
    scale = size / 7.0
    cw = max(1, round(8 * scale))      # cell width in pixels
    chh = cell_h(size)
    cx = x
    for ch in text:
        rows = rows_for(ch, bold)
        adv = advance(ch)
        aw = max(1, round(adv * scale))
        for dy in range(chh):
            sy = min(7, int(dy * 8 / chh))
            bits = rows[sy]
            if not bits:
                continue
            for dx in range(aw):
                sx = min(7, int(dx * 8 / cw))
                if (bits >> (7 - sx)) & 1:
                    sheet.dot(int(cx) + dx, y + dy, colour)
        cx += aw
    return cx


def draw_centred(sheet, text, size, cx, y, colour, bold=False):
    draw_text(sheet, text, size, int(cx - text_w(text, size) / 2),
              y, colour, bold)


def wrap_lines(text, size, max_w):
    """Greedy word wrap; a single over-long word stays on its own line."""
    lines, cur = [], ""
    for word in text.split(" "):
        trial = (cur + " " + word).strip()
        if text_w(trial, size) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def save_png(sheet, path):
    raw = bytearray()
    stride = sheet.w * 3
    for y in range(sheet.h):
        raw.append(0)
        raw += sheet.px[y * stride:(y + 1) * stride]
    blob = zlib.compress(bytes(raw), 9)

    def chunk(tag, data):
        piece = struct.pack(">I", len(data)) + tag + data
        return piece + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR",
                  struct.pack(">IIBBBBB", sheet.w, sheet.h, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", blob)
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


# ---- one small original picture per lead story ----
# Each paints inside the box (x, y, w, h). Bold flat shapes; the
# headline next to it carries the facts, the picture only has to make
# the story recognisable at a glance.

def _pic_chip(s, x, y, w, h):
    s.box(x, y, w, h, (30, 44, 66))
    s.box(x + w // 2 - 13, y + h // 2 - 11, 26, 22, (60, 180, 140))
    s.box(x + w // 2 - 7, y + h // 2 - 5, 14, 10, (30, 44, 66))
    for off in (-18, -9, 0, 9, 18):
        s.box(x + w // 2 + off - 1, y + 3, 2, 7, (200, 200, 200))
        s.box(x + w // 2 + off - 1, y + h - 10, 2, 7, (200, 200, 200))
    draw_text(s, "AI", 10, x + w // 2 - 11, y + h // 2 - 5,
              (255, 255, 255), bold=True)


def _pic_summit(s, x, y, w, h):
    s.box(x, y, w, h, (214, 228, 214))
    s.box(x + 5, y + h - 13, w - 10, 4, (120, 84, 50))
    for off, col in ((-18, (70, 90, 130)), (0, (150, 60, 50)),
                     (18, (60, 120, 80))):
        s.disc(x + w // 2 + off, y + h // 2 - 6, 7, col)
        s.box(x + w // 2 + off - 7, y + h // 2 + 1, 14, 8, col)


def _pic_gavel(s, x, y, w, h):
    s.box(x, y, w, h, (226, 220, 200))
    s.box(x + 8, y + h - 11, w - 16, 4, (120, 84, 50))
    s.seg(x + w // 2 - 13, y + 10, x + w // 2 + 13, y + 24, (90, 60, 30))
    s.box(x + w // 2 - 17, y + 6, 11, 6, (70, 50, 30))
    s.box(x + w // 2 + 6, y + 20, 11, 6, (70, 50, 30))
    s.disc(x + w // 2 - 12, y + 9, 2, (200, 170, 120))
    s.disc(x + w // 2 + 11, y + 23, 2, (200, 170, 120))


def _pic_ship(s, x, y, w, h):
    s.box(x, y, w, h, (120, 165, 200))
    s.box(x, y + h - 13, w, 13, (38, 84, 130))
    s.fill([(x + 8, y + h - 13), (x + w - 8, y + h - 13),
            (x + w - 22, y + h - 3), (x + 22, y + h - 3)], (90, 40, 36))
    s.box(x + w // 2 - 3, y + 7, 6, h - 24, (200, 200, 200))
    s.disc(x + w // 2 + 13, y + 11, 6, (240, 170, 40))
    s.box(x + w - 28, y + 5, 14, 3, (250, 220, 90))


def _pic_fire(s, x, y, w, h):
    s.box(x, y, w, h, (52, 46, 44))
    s.box(x, y + h - 13, w, 13, (34, 32, 30))
    s.box(x + 5, y + h - 23, w - 10, 10, (96, 84, 70))
    for off, hh, col in ((-15, 20, (230, 90, 20)), (0, 28, (250, 160, 30)),
                         (15, 18, (230, 90, 20))):
        cx = x + w // 2 + off
        s.fill([(cx - 6, y + h - 23), (cx, y + h - 23 - hh),
                (cx + 6, y + h - 23)], col)
    s.disc(x + w // 2, y + h - 25, 3, (250, 220, 90))
    s.box(x + 7, y + 3, w - 14, 3, (90, 84, 78))


def _pic_flag(s, x, y, w, h):
    s.box(x, y, w, h, (232, 226, 205))
    s.box(x + 11, y + 5, 3, h - 10, (90, 70, 50))
    for i, col in enumerate(((190, 40, 40), (255, 255, 255), (190, 40, 40),
                             (255, 255, 255), (190, 40, 40))):
        s.box(x + 14, y + 7 + i * 6, w - 28, 6, col)
    s.box(x + 14, y + 7, 20, 12, (40, 60, 130))
    s.disc(x + 20, y + 11, 1, (255, 255, 255))
    s.disc(x + 28, y + 15, 1, (255, 255, 255))


def _pic_missile(s, x, y, w, h):
    s.box(x, y, w, h, (40, 40, 52))
    s.seg(x + 9, y + h - 7, x + w - 15, y + 9, (240, 200, 80))
    s.disc(x + w - 15, y + 9, 4, (255, 240, 160))
    s.disc(x + w // 2, y + h // 2 + 5, 7, (150, 60, 50))
    s.disc(x + w // 2, y + h // 2 + 5, 3, (240, 170, 40))
    s.box(x + 5, y + h - 15, 12, 7, (90, 90, 100))


def _pic_talks(s, x, y, w, h):
    s.box(x, y, w, h, (222, 214, 190))
    s.box(x + 5, y + h - 15, w - 10, 5, (120, 84, 50))
    s.disc(x + w // 3, y + h // 2 - 2, 8, (70, 90, 130))
    s.disc(x + 2 * w // 3, y + h // 2 - 2, 8, (150, 60, 50))
    s.box(x + w // 3 - 8, y + h // 2 + 5, 16, 9, (70, 90, 130))
    s.box(x + 2 * w // 3 - 8, y + h // 2 + 5, 16, 9, (150, 60, 50))
    s.disc(x + w // 2, y + 7, 6, (255, 252, 242))
    draw_text(s, "?", 11, x + w // 2 - 3, y + 2, INK, bold=True)


def _pic_strike(s, x, y, w, h):
    s.box(x, y, w, h, (60, 58, 64))
    s.box(x, y + h - 11, w, 11, (40, 38, 42))
    for off, dy, r in ((0, 0, 12), (-15, 4, 7), (16, 3, 6)):
        s.disc(x + w // 2 + off, y + h // 2 + dy, r, (240, 170, 40))
        s.disc(x + w // 2 + off, y + h // 2 + dy, r - 4, (250, 220, 90))
    s.box(x + 7, y + h - 21, 9, 9, (20, 20, 22))
    s.box(x + w - 19, y + h - 19, 11, 7, (20, 20, 22))


def _pic_plane(s, x, y, w, h):
    s.box(x, y, w, h, (150, 190, 220))
    s.fill([(x + 7, y + h // 2), (x + w - 11, y + h // 2 - 5),
            (x + w - 3, y + h // 2), (x + w - 11, y + h // 2 + 5)],
           (240, 240, 240))
    s.fill([(x + w // 2, y + h // 2 - 3), (x + w // 2 + 7, y + h // 2 - 15),
            (x + w // 2 + 11, y + h // 2 - 3)], (200, 60, 50))
    s.disc(x + w - 21, y + 7, 4, (250, 220, 90))


def _pic_circuit(s, x, y, w, h):
    s.box(x, y, w, h, (28, 52, 40))
    s.box(x + w // 2 - 11, y + h // 2 - 9, 22, 18, (40, 90, 60))
    s.box(x + w // 2 - 5, y + h // 2 - 4, 10, 8, (28, 52, 40))
    for off in (-19, -10, 0, 10, 19):
        s.seg(x + w // 2 + off, y + 5, x + w // 2 + off,
              y + h // 2 - 9, (120, 200, 160))
        s.disc(x + w // 2 + off, y + 5, 2, (200, 220, 200))
    s.seg(x + 5, y + h // 2, x + w // 2 - 11, y + h // 2, (120, 200, 160))
    s.seg(x + w // 2 + 11, y + h // 2, x + w - 5, y + h // 2,
          (120, 200, 160))


def _pic_graph(s, x, y, w, h):
    s.box(x, y, w, h, (238, 234, 220))
    s.seg(x + 7, y + 7, x + 7, y + h - 7, (90, 90, 90))
    s.seg(x + 7, y + h - 7, x + w - 5, y + h - 7, (90, 90, 90))
    pts = []
    levels = (0.38, 0.58, 0.48, 0.68, 0.55, 0.78, 0.62, 0.85, 0.72)
    for i in range(9):
        px = x + 9 + i * (w - 16) // 8
        py = y + h - 11 - int((h - 22) * levels[i])
        pts.append((px, py))
    for i in range(len(pts) - 1):
        s.seg(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1],
              (60, 120, 180))
    draw_text(s, "R", 18, x + w - 22, y + 3, INK, bold=True)


def _pic_court(s, x, y, w, h):
    s.box(x, y, w, h, (222, 216, 198))
    s.fill([(x + 5, y + 13), (x + w // 2, y + 1), (x + w - 5, y + 13)],
           (170, 150, 110))
    for off in (11, 26, 41, 56):
        s.box(x + off, y + 15, 4, h - 25, (200, 185, 150))
    s.box(x + 5, y + h - 9, w - 10, 4, (150, 130, 95))


def _pic_chart(s, x, y, w, h):
    s.box(x, y, w, h, (240, 236, 224))
    s.box(x + 9, y + h - 11, 7, 11, (90, 130, 90))
    s.box(x + 24, y + h - 19, 7, 19, (90, 130, 90))
    s.box(x + 39, y + h - 28, 7, 28, (170, 60, 50))
    s.box(x + 54, y + h - 36, 7, 36, (170, 60, 50))
    s.seg(x + 7, y + 9, x + w - 7, y + h - 7, (170, 60, 50))
    s.seg(x + w - 13, y + h - 13, x + w - 7, y + h - 7, (170, 60, 50))
    s.seg(x + w - 13, y + h - 1, x + w - 7, y + h - 7, (170, 60, 50))


def _pic_quake(s, x, y, w, h):
    s.box(x, y, w, h, (210, 200, 170))
    s.box(x + 7, y + h - 19, 13, 13, (120, 100, 80))
    s.box(x + w - 25, y + h - 23, 15, 17, (100, 85, 70))
    s.box(x + w // 2 - 5, y + h - 15, 11, 9, (140, 120, 95))
    s.seg(x + 3, y + h - 5, x + w // 3, y + h - 13, (60, 50, 40))
    s.seg(x + w // 3, y + h - 13, x + 2 * w // 3, y + h - 3, (60, 50, 40))
    s.seg(x + 2 * w // 3, y + h - 3, x + w - 3, y + h - 11, (60, 50, 40))
    draw_text(s, "6.5", 11, x + w // 2 - 8, y + 1, RED, bold=True)


def _pic_barrel(s, x, y, w, h):
    s.box(x, y, w, h, (190, 205, 220))
    for off, col in ((-19, (60, 90, 130)), (0, (40, 70, 110)),
                     (19, (60, 90, 130))):
        bx = x + w // 2 + off - 7
        s.box(bx, y + h - 25, 14, 19, col)
        s.box(bx, y + h - 25, 14, 3, (30, 55, 90))
        s.box(bx, y + h - 13, 14, 2, (30, 55, 90))
    s.disc(x + w - 11, y + 9, 5, (250, 220, 90))
    s.seg(x + w - 11, y + 9, x + w // 2 + 7, y + 15, (240, 200, 80))


PICTURES = {"chip": _pic_chip, "summit": _pic_summit, "gavel": _pic_gavel,
            "ship": _pic_ship, "fire": _pic_fire, "flag": _pic_flag,
            "missile": _pic_missile, "talks": _pic_talks,
            "strike": _pic_strike, "plane": _pic_plane,
            "circuit": _pic_circuit, "graph": _pic_graph,
            "court": _pic_court, "chart": _pic_chart,
            "quake": _pic_quake, "barrel": _pic_barrel}


# ---- world map: coarse equirectangular landmasses, hand-plotted ----
LANDMASSES = [
    # North America
    [(-168, 66), (-140, 70), (-120, 71), (-95, 69), (-85, 66), (-80, 73),
     (-70, 62), (-60, 55), (-55, 47), (-65, 44), (-70, 42), (-75, 35),
     (-80, 32), (-81, 26), (-84, 30), (-90, 21), (-97, 16), (-92, 15),
     (-86, 12), (-83, 9), (-79, 9), (-85, 15), (-92, 15), (-97, 26),
     (-105, 20), (-110, 23), (-114, 29), (-120, 34), (-125, 40),
     (-124, 48), (-130, 55), (-145, 60), (-155, 58), (-165, 60),
     (-168, 66)],
    # South America
    [(-79, 9), (-77, 4), (-80, -3), (-81, -6), (-77, -12), (-72, -18),
     (-70, -23), (-70, -30), (-71, -35), (-73, -44), (-74, -53),
     (-70, -54), (-66, -55), (-68, -50), (-65, -45), (-62, -40),
     (-58, -35), (-52, -32), (-48, -28), (-41, -23), (-39, -17),
     (-35, -9), (-35, -6), (-40, -3), (-44, -2), (-50, 0), (-53, 4),
     (-60, 8), (-68, 11), (-75, 10), (-79, 9)],
    # Europe
    [(-10, 36), (-9, 43), (-2, 48), (0, 51), (5, 53), (8, 57), (10, 59),
     (18, 56), (21, 55), (28, 59), (30, 62), (30, 70), (20, 70),
     (10, 68), (5, 60), (-5, 58), (-10, 50), (-10, 36)],
    # Africa
    [(-6, 35), (0, 36), (10, 37), (11, 34), (20, 32), (25, 31), (32, 31),
     (34, 28), (37, 22), (39, 18), (43, 12), (48, 11), (51, 12), (44, 5),
     (41, 0), (40, -5), (40, -12), (36, -18), (33, -26), (28, -33),
     (20, -35), (17, -32), (14, -22), (12, -18), (9, -4), (9, 4),
     (4, 6), (-8, 4), (-13, 8), (-17, 12), (-16, 20), (-15, 27),
     (-10, 31), (-6, 35)],
    # Asia
    [(30, 70), (35, 68), (45, 68), (55, 69), (65, 69), (75, 72),
     (90, 75), (105, 76), (120, 73), (135, 72), (150, 70), (162, 66),
     (170, 66), (178, 65), (170, 60), (162, 58), (158, 52), (150, 60),
     (142, 55), (140, 45), (138, 38), (130, 35), (127, 33), (122, 30),
     (120, 25), (110, 20), (108, 12), (105, 8), (100, 8), (97, 15),
     (92, 21), (88, 22), (85, 20), (80, 13), (77, 8), (74, 20),
     (70, 25), (66, 25), (62, 25), (57, 26), (53, 27), (50, 29),
     (48, 30), (44, 29), (42, 35), (39, 36), (36, 36), (33, 36),
     (30, 36), (30, 42), (28, 45), (28, 50), (30, 55), (30, 62),
     (30, 70)],
    # Australia
    [(113, -22), (114, -30), (115, -35), (118, -35), (124, -33),
     (129, -32), (132, -32), (135, -35), (138, -35), (140, -38),
     (145, -38), (150, -37), (153, -32), (153, -27), (150, -23),
     (146, -19), (142, -11), (137, -12), (135, -15), (132, -12),
     (130, -13), (126, -14), (122, -17), (118, -20), (113, -22)],
    # New Zealand
    [(167, -45), (170, -42), (174, -39), (177, -38), (178, -38),
     (174, -41), (170, -44), (167, -45)],
]


def project(lon, lat, x, y, w, h):
    """Equirectangular, latitude cropped to -50..72 so the map is
    not a flat strip; points outside the band clamp to the edge."""
    lat = max(-50.0, min(72.0, lat))
    return (x + int((lon + 180.0) / 360.0 * w),
            y + int((72.0 - lat) / 122.0 * h))


def paint_map(sheet, x, y, w, h, pins):
    sheet.box(x, y, w, h, SEA)
    for land in LANDMASSES:
        pts = [project(lon, lat, x, y, w, h) for lon, lat in land]
        sheet.fill(pts, LAND)
        for i in range(len(pts)):
            a, b = pts[i], pts[(i + 1) % len(pts)]
            sheet.seg(a[0], a[1], b[0], b[1], (150, 138, 108))
    for num, lon, lat, region, dx, dy in pins:
        px, py = project(lon, lat, x, y, w, h)
        px += dx
        py += dy
        sheet.disc(px, py, 8, PIN_COLOUR[region])
        sheet.ring(px, py, 8, (255, 255, 255), 1)
        label = str(num)
        draw_text(sheet, label, 9, px - int(text_w(label, 9) / 2), py - 5,
                  (255, 255, 255), bold=True)


# ---- page sections ----

def paint_masthead(s):
    s.hrule(MARGIN, 12, CONTENT_W, INK)
    s.hrule(MARGIN, 14, CONTENT_W, INK)
    draw_centred(s, "THE WORLD TODAY", 12, 512, 20, RED, bold=True)
    draw_centred(s, "MONDAY, 23 NOVEMBER 2026", 36, 512, 38, INK, bold=True)
    draw_centred(s, "ONE DAY OF WORLD NEWS, ONE PICTURE  \u00b7  50 STORIES"
                  "  \u00b7  7 REGIONS  \u00b7  16 FIELDS", 11, 512, 88, MUTED)
    s.hrule(MARGIN, 108, CONTENT_W, INK)


def paint_timeline(s):
    y = 130
    draw_text(s, "THE DAY IN UTC", 10, MARGIN, y, RED, bold=True)
    note_x = MARGIN + int(text_w("THE DAY IN UTC", 10)) + 8
    draw_text(s, "as the day turned west \u2014 overnight to evening",
              10, note_x, y, MUTED)
    box_w, box_h = 132, 40
    for i, (when, head) in enumerate(TIMELINE):
        x = MARGIN + i * (box_w + 7)
        s.box(x, y + 14, box_w, box_h, CARD)
        s.hrule(x, y + 14, box_w, RULE)
        s.hrule(x, y + 14 + box_h - 1, box_w, RULE)
        draw_text(s, when, 8, x + 5, y + 17, RED, bold=True)
        for j, ln in enumerate(wrap_lines(head, 7, box_w - 10)[:3]):
            draw_text(s, ln, 7, x + 5, y + 28 + j * 8, INK)


CARD_Y = (186, 294, 392, 490)
CARD_H = (106, 94, 94, 94)


def paint_lead(s, story):
    (n, region, pic, lon, lat, dx, dy, title, summ, source,
     status, topic) = story
    col, row = (n - 1) % 4, (n - 1) // 4
    x = MARGIN + col * 246
    y, h = CARD_Y[row], CARD_H[row]
    w = 238
    big = (row == 0)
    s.box(x, y, w, h, CARD)
    s.hrule(x, y, w, RULE)
    s.hrule(x, y + h - 1, w, RULE)
    s.vrule(x, y, h, RULE)
    s.vrule(x + w - 1, y, h, RULE)
    s.box(x, y, w, 13, REGION_TINT[region])
    draw_text(s, str(n), 9, x + 4, y + 2, RED, bold=True)
    head_x = x + 4 + int(text_w(str(n), 9)) + 6
    draw_text(s, region.upper() + " \u00b7 " + topic, 8, head_x, y + 3, INK,
              bold=True)
    if big:
        PICTURES[pic](s, x + 4, y + 16, 54, 40)
        tx, tw = x + 62, 172
        sy = y + 58
    else:
        PICTURES[pic](s, x + 4, y + 16, 44, 28)
        tx, tw = x + 52, 182
        sy = y + 46
    for j, ln in enumerate(wrap_lines(title, 9, tw)[:2]):
        draw_text(s, ln, 9, tx, y + 17 + j * 11, INK, bold=True)
    for j, ln in enumerate(wrap_lines(summ, 7, w - 8)[:4]):
        draw_text(s, ln, 7, x + 4, sy + j * 8, INK)
    draw_text(s, region.upper() + "  \u00b7  " + source.upper(), 7,
              x + 4, y + h - 10, MUTED)
    label = "CONFIRMED" if status == "CONFIRMED" else "CLAIM"
    colr = GREEN if status == "CONFIRMED" else RED
    lw = int(text_w(label, 7))
    px = x + w - lw - 12
    s.box(px, y + h - 11, lw + 8, 10, colr)
    draw_text(s, label, 7, px + 4, y + h - 10, (255, 255, 255), bold=True)


REGION_TALLY = [("EUROPE", 13), ("MIDDLE EAST", 6), ("ASIA", 9),
                ("AMERICAS", 6), ("AFRICA", 6), ("OCEANIA", 4),
                ("GLOBAL", 6)]
FIELDS = ["War", "Politics", "Diplomacy", "Trade", "Markets", "Climate",
          "Space", "Science", "Sport", "Disaster", "Health", "AI & Tech",
          "Law & Crime", "Migration", "Defence", "Energy"]


def paint_map_panel(s):
    y = 588
    draw_text(s, "WHERE IT HAPPENED", 11, MARGIN, y, RED, bold=True)
    note_x = MARGIN + int(text_w("WHERE IT HAPPENED", 11)) + 8
    draw_text(s, "numbered pins are the 16 lead stories above", 10,
              note_x, y, MUTED)
    my = y + 15
    draw_text(s, "BY REGION", 9, MARGIN, my, INK, bold=True)
    for i, (name, cnt) in enumerate(REGION_TALLY):
        ry = my + 14 + i * 11
        s.disc(MARGIN + 5, ry + 4, 4, PIN_COLOUR[name.title()])
        draw_text(s, name, 8, MARGIN + 14, ry, INK)
        c = str(cnt)
        draw_text(s, c, 8, MARGIN + 156 - int(text_w(c, 8)), ry, RED,
                  bold=True)
    rx = MARGIN + CONTENT_W - 160
    draw_text(s, "16 FIELDS", 9, rx, my, INK, bold=True)
    for i, f in enumerate(FIELDS):
        draw_text(s, f, 8, rx + (i // 8) * 82, my + 14 + (i % 8) * 11, INK)
    pins = [(st[0], st[3], st[4], st[1], st[5], st[6]) for st in LEADS]
    paint_map(s, MARGIN + 164, my, 640, 140, pins)


def paint_also(s):
    y = 747
    draw_text(s, "ALSO ON MONDAY", 11, MARGIN, y, RED, bold=True)
    note_x = MARGIN + int(text_w("ALSO ON MONDAY", 11)) + 8
    draw_text(s, "stories 17\u201350, one line each", 10, note_x, y,
              MUTED)
    col_w = 478
    for i, (n, line) in enumerate(ALSO):
        col, row = i // 17, i % 17
        x = MARGIN + col * (col_w + 12)
        yy = y + 16 + row * 10
        draw_text(s, str(n) + ".", 7, x, yy, RED, bold=True)
        draw_text(s, line, 7, x + 20, yy, INK)


def paint_datecheck(s):
    y = 939
    s.box(MARGIN, y, CONTENT_W, 50, DATE_BG)
    s.hrule(MARGIN, y, CONTENT_W, RED)
    s.hrule(MARGIN, y + 49, CONTENT_W, RED)
    s.vrule(MARGIN, y, 50, RED)
    s.vrule(MARGIN + CONTENT_W - 1, y, 50, RED)
    draw_text(s, "DATE CHECK", 10, MARGIN + 6, y + 4, RED, bold=True)
    for j, ln in enumerate(wrap_lines(DATECHECK, 7, CONTENT_W - 12)[:4]):
        draw_text(s, ln, 7, MARGIN + 6, y + 17 + j * 8, INK)


def paint_footer(s):
    y = 993
    s.hrule(MARGIN, y, CONTENT_W, INK)
    for j, ln in enumerate(wrap_lines(FOOTER, 8, CONTENT_W)[:2]):
        draw_text(s, ln, 8, MARGIN, y + 5 + j * 9, MUTED)


# ---- the day's stories (verified Monday 23 November 2026) ----
# Every item happened, or was first reported, on 23 Nov 2026 in at
# least one time zone. CLAIM = one side's account, not confirmed.
# Sources checked 24 Nov 2026 ~15:30 UTC: Principia day page
# 2026-11-23, One Turn country pages (Ukraine, Turkey, Indonesia,
# Sudan, Mexico, Singapore, Spain, Canada), Reuters (EU sanctions,
# NATO AWACS, COP31 fallout, CrowdStrike-Zscaler, Trading Day),
# CoinDesk (Nvidia), Le Monde (Libya ships, Colombia bank),
# Military.com (Trump Iran), AP (Democrats 258), BBC (Megaspeed).
TIMELINE = [
    ("Overnight", "Drones hit Khartoum homes, UN building"),
    ("~06:10 UTC", "Democrats clinch 258th House seat"),
    ("~09:30 UTC", "Indonesia confirms 24 dead in factory fire"),
    ("~12:00 UTC", "Spain amnesties Puigdemont"),
    ("~14:15 UTC", "Nvidia reinstates Huang; shares jump 31%"),
    ("~17:35 UTC", "EU unveils 22nd sanctions package"),
    ("Evening", "COP31 blame game erupts in Canberra"),
]

# Lead story: (n, region, picture, lon, lat, dx, dy, title, summary,
#                source, status, topic)
LEADS = [
    (1, "Global", "chip", -122.0, 37.4, 0, 0,
     "Huang is back \u2014 Nvidia jumps 31%",
     "Eleven days after resigning, Jensen Huang is reinstated as CEO; "
     "shares add about $950bn in a day and the Nasdaq jumps 6.5%.",
     "CoinDesk", "CONFIRMED", "MARKETS"),
    (2, "Global", "summit", 149.1, -35.3, 0, 0,
     "COP31 fallout: blame game in Canberra",
     "Australia's opposition demands minister Bowen go after the "
     "no-deal summit; Pacific nations call the outcome despair.",
     "Reuters", "CONFIRMED", "CLIMATE FALLOUT"),
    (3, "Europe", "gavel", 4.35, 50.85, 0, 0,
     "EU unveils 22nd Russia sanctions",
     "Sixty banks face a SWIFT cut-off, 70 shadow-fleet tankers are "
     "listed, and Russian athletes face a sports ban.",
     "Reuters", "CONFIRMED", "SANCTIONS"),
    (4, "Europe", "ship", 20.1, 32.1, 0, 0,
     "Zelenskyy confirms Libya ship strikes",
     "Kyiv says seven sea drones sank the corvette Merkury and hit the "
     "arms cargo ship Angara off Benghazi; the UN urges a probe.",
     "Le Monde", "CONFIRMED", "LIBYA STRIKE"),
    (5, "Asia", "fire", 106.2, -6.2, 0, 0,
     "Factory fire toll reaches 24",
     "Indonesia confirms 24 dead at the Cikande candy plant; about 30 "
     "are still missing as rescuers search unstable ruins.",
     "Reuters", "CONFIRMED", "FACTORY FIRE"),
    (6, "Americas", "flag", -77.0, 38.9, 0, 0,
     "Democrats reach 258 House seats",
     "A North Carolina recount win gives Democrats their biggest House "
     "majority since 1992; four races remain uncalled.",
     "AP", "CONFIRMED", "MIDTERMS"),
    (7, "Middle East", "missile", 51.4, 35.7, 0, 0,
     "Trump: Iran strikes may resume next year",
     "Trump tells Fox he may resume the war on Iran next year if talks "
     "fail, blaming Tehran's tougher line since the midterms.",
     "Military.com", "CONFIRMED", "IRAN WAR"),
    (8, "Middle East", "talks", 51.5, 25.3, 14, 10,
     "Vance meets Qatar on stalled Iran talks",
     "The vice-president meets Qatar's prime minister as Doha presses "
     "Washington and Tehran back to the table.",
     "Breitbart", "CONFIRMED", "DIPLOMACY"),
    (9, "Africa", "strike", 32.5, 15.6, 0, 0,
     "Drones hit Khartoum homes, UN building",
     "Overnight drone strikes kill four, including a 10-year-old, and "
     "damage a UN building; the UN calls it unacceptable.",
     "Al Jazeera", "CONFIRMED", "SUDAN WAR"),
    (10, "Europe", "plane", 21.0, 52.2, 0, 0,
     "NATO sends AWACS jets to Poland",
     "NATO will deploy AWACS aircraft after three Russian missiles "
     "landed in Poland on Friday, Warsaw says.",
     "Reuters", "CONFIRMED", "NATO"),
    (11, "Asia", "circuit", 103.8, 1.35, 18, -14,
     "US blacklists AI firm Megaspeed",
     "Washington blacklists the Singapore firm over alleged chip flows "
     "to China and moves to seize $1.1bn in North Korean crypto.",
     "BBC", "CONFIRMED", "CHIP BAN"),
    (12, "Global", "graph", -122.4, 37.8, 16, -12,
     "Anthropic: AI helped prove Riemann",
     "Anthropic says an AI-generated proof of the famous maths puzzle "
     "is under review, sparking debate over verification.",
     "Anthropic", "CLAIM", "MATHS"),
    (13, "Europe", "court", -3.7, 40.4, -14, 6,
     "Spain amnesties Puigdemont",
     "The Supreme Court amnesties the Catalan separatist over the 2017 "
     "independence bid; he will not return before Sunday's election.",
     "CNN", "CONFIRMED", "AMNESTY"),
    (14, "Americas", "chart", -74.1, 4.7, 0, 0,
     "Deutsche Bank probed over Colombia flows",
     "A Le Monde-led inquiry finds the bank dominated euro payments in "
     "Colombia without checks, possibly aiding crime.",
     "Le Monde", "CONFIRMED", "BANK PROBE"),
    (15, "Oceania", "quake", 167.0, -16.0, 0, 0,
     "Magnitude 6.5 quake shakes Vanuatu",
     "A deep quake strikes the Vanuatu region on Monday; no damage is "
     "reported, and no tsunami warning follows.",
     "USGS", "CONFIRMED", "QUAKE"),
    (16, "Asia", "barrel", 139.7, 35.7, 0, 0,
     "Japan launches Asian oil task force",
     "With Hormuz shipments disrupted by the Iran war, Tokyo pushes "
     "shared reserves and closer supplier ties.",
     "Euronews", "CONFIRMED", "OIL SECURITY"),
]

# Stories 17-50: (n, "title \u2014 source"), one line each.
ALSO = [
    (17, "Russian strikes kill 15 near Kyiv; boy, 7, freed after 14h in "
         "rubble \u2014 Reuters"),
    (18, "Russia launches 153 drones overnight; Ukraine says 134 downed "
         "\u2014 Kyiv"),
    (19, "Euro area inflation rises to 4.0%, Eurostat says \u2014 Eurostat"),
    (20, "Burnham defends EU reset deal, rules out rejoin without vote "
         "\u2014 BBC"),
    (21, "NHS AI breast-screening trial to invite 700,000 women \u2014 NHS"),
    (22, "US holds first deep-sea mining lease sales off American Samoa "
         "\u2014 PINA"),
    (23, "US confirmed as 2031 Women's World Cup host \u2014 FIFA"),
    (24, "Russia accuses Estonia of hostile acts near open war "
         "\u2014 Reuters"),
    (25, "Kilauea completes its 57th lava-fountaining episode \u2014 USGS"),
    (26, "More than 700,000 Russian soldiers killed, analysis finds "
         "\u2014 RFE/RL \u00b7 CLAIM"),
    (27, "Zelenskyy: Ukraine ready for four-way peace talks \u2014 Reuters"),
    (28, "Pacific tuna stocks face critical calls at WCPFC meeting "
         "\u2014 PINA"),
    (29, "Trump, victims' families rail at Newsom death-row clemency "
         "\u2014 Independent"),
    (30, "Brad Jacobs wins Grand Slam of Curling title in Nova Scotia "
         "\u2014 CBC"),
    (31, "Lebanese villagers return to wrecked homes as IDF pulls back "
         "\u2014 Reuters"),
    (32, "Syria destroys 400 million Captagon tablets in biggest haul "
         "\u2014 Syria"),
    (33, "Iran singer Parastoo Ahmadi gets 74 lashes for online concert "
         "\u2014 Breitbart"),
    (34, "US sanctions dozens linked to Iran shadow banking \u2014 Reuters"),
    (35, "Nigeria funeral-boat toll reaches 29 bodies recovered "
         "\u2014 Juba Global"),
    (36, "Nine African energy exporters gain $21.6bn in Iran war "
         "\u2014 Juba Global"),
    (37, "South Sudan destroys damaged food worth 500m pounds "
         "\u2014 Juba Global"),
    (38, "UN urges independent probe into Benghazi port attacks \u2014 UN"),
    (39, "Sudan aid appeal only 51% funded as food prices soar \u2014 OCHA"),
    (40, "5,000 drones light up sky over China's Three Gorges "
         "\u2014 Euronews"),
    (41, "South Korea and China agree wider trade deal on entertainment "
         "\u2014 Euronews"),
    (42, "Taiwan warns Canada against deeper China trade ties "
         "\u2014 Euronews"),
    (43, "Hong Kong sets up building regulator after Tai Po fire "
         "\u2014 SCMP"),
    (44, "Indonesia plans 70% state control of mining shares or revenue "
         "\u2014 SCMP"),
    (45, "Japan moves to expand coast guard fleet and drones against China "
         "\u2014 Japan"),
    (46, "CrowdStrike snaps up Zscaler in $44bn deal \u2014 Reuters"),
    (47, "OpenAI proposes shared AI safety limits for labs \u2014 OpenAI"),
    (48, "Bitcoin spikes past $64,000 on Huang news, then falls back "
         "\u2014 CoinDesk"),
    (49, "GTA VI is PlayStation's biggest launch: 39m players in 4 days "
         "\u2014 Sony"),
    (50, "Alcaraz beats Zverev to win first ATP Finals title \u2014 Reuters"),
]

DATECHECK = ("Left out: the COP31 collapse itself (Sun 22 Nov \u2014 today "
             "is the fallout); the Dymer flat strike and the El Chapo "
             "Isidro capture (22 Nov); the Ashes retention in Adelaide "
             "(21 Dec 2025, not 2026); BepiColombo's Mercury orbit "
             "(21 Nov); GTA VI's $3.79bn day-one figure (announced 20 Nov; "
             "today: Sony's 39m players). Not yet decided at about "
             "16:00 UTC: the full toll of the Cikande fire; whether the "
             "EU's 22nd sanctions package wins unanimous approval; "
             "Spain's election (Sun 29 Nov).")

FOOTER = ("Every story happened or was first reported on Mon 23 Nov 2026. "
          "CLAIM = one side's account. "
          "Sources: Reuters, AP, BBC, Le Monde, Al Jazeera, CoinDesk, "
          "Euronews, PINA. Original drawings.")


def build():
    sheet = Sheet(PAGE_W, PAGE_H, PAPER)
    paint_masthead(sheet)
    paint_timeline(sheet)
    for story in LEADS:
        paint_lead(sheet, story)
    paint_map_panel(sheet)
    paint_also(sheet)
    paint_datecheck(sheet)
    paint_footer(sheet)
    return sheet


def main():
    out = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, "entry.png")
    size = save_png(build(), path)
    print("wrote", path, size, "bytes")


if __name__ == "__main__":
    main()
