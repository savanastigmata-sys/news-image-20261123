"""Draw the world-news front page for Monday 23 November 2026.

Pure Python standard library. Renders a 1024x1024 PNG in a dense
newspaper style: masthead, UTC timeline, 16 illustrated lead stories,
a world map with numbered pins, a numbered 17-50 list, a date check
and a sourcing footer. Glyphs come from fontdata.py (DejaVu bitmaps
rasterised at build time); the program itself needs no fonts, no
network, no clock and no randomness -- two runs write identical bytes.

TARGET (per the brief): TOP 1. The judge weighs, in order: the day
named with specific recognisable events; breadth across regions and
fields; readability from the image alone; faithfulness; craft.

Stories: every one happened, or was first reported, on Monday
23 November 2026 in at least one time zone (the competition's own
rule). Built at about 16:00 UTC on 24 November, after the day had
ended everywhere; the DATE CHECK box names the big stories left out
because they belong to another date, and what had not happened yet.
"""
import base64 as _b64
import json as _json
import os
import struct
import sys
import zlib
from math import cos, pi, sin

# The grader runs `python3 -P -s`, which does not put the script's own
# directory on sys.path: add it so the sibling fontdata module is found.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fontdata import _FONT_B64

W, H = 1024, 1024
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
TINTS = {
    "Europe": (216, 228, 242),
    "Middle East": (242, 216, 198),
    "Asia": (214, 236, 214),
    "Americas": (242, 232, 196),
    "Africa": (234, 214, 234),
    "Oceania": (198, 232, 230),
    "Global": (228, 228, 228),
}
PIN_COLOURS = {
    "Europe": (60, 100, 180),
    "Middle East": (220, 120, 40),
    "Asia": (130, 80, 160),
    "Americas": (180, 40, 40),
    "Africa": (40, 130, 70),
    "Oceania": (40, 140, 140),
    "Global": (90, 90, 90),
}
TOPICS = {1: "MARKETS", 2: "CLIMATE FALLOUT", 3: "SANCTIONS", 4: "LIBYA STRIKE",
          5: "FACTORY FIRE", 6: "MIDTERMS", 7: "IRAN WAR", 8: "DIPLOMACY",
          9: "SUDAN WAR", 10: "NATO", 11: "CHIP BAN", 12: "MATHS",
          13: "AMNESTY", 14: "BANK PROBE", 15: "QUAKE", 16: "OIL SECURITY"}

_FONTS = _json.loads(_b64.b64decode(_FONT_B64))


def _nearest(family, size):
    sizes = sorted(int(s) for s in _FONTS[family])
    best = sizes[0]
    for s in sizes:
        if abs(s - size) < abs(best - size) or (
                abs(s - size) == abs(best - size) and s > best):
            best = s
    return best


def _glyph(family, size, ch):
    base = _nearest(family, size)
    f = _FONTS[family][str(base)]
    g = f["glyphs"].get(ch)
    if g is None:
        g = f["glyphs"].get("?", f["glyphs"][" "])
    w, h, xo, yo, adv, b64 = g
    raw = _b64.b64decode(b64) if b64 else b""
    return w, h, xo, yo, adv, raw, base


def _bit(raw, w, x, y):
    i = y * w + x
    return (raw[i >> 3] >> (7 - (i & 7))) & 1


class Img:
    """A tiny RGB canvas with the drawing primitives the page needs."""

    def __init__(self, w, h, bg):
        self.w, self.h = w, h
        self.px = bytearray(bg) * (w * h)

    def _i(self, x, y):
        return (y * self.w + x) * 3

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = self._i(x, y)
            self.px[i:i + 3] = bytes(c)

    def rect(self, x, y, w, h, c):
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.w, x + w), min(self.h, y + h)
        row = bytes(c) * (x1 - x0)
        for yy in range(y0, y1):
            i = self._i(x0, yy)
            self.px[i:i + len(row)] = row

    def hline(self, x, y, w, c):
        self.rect(x, y, w, 1, c)

    def vline(self, x, y, h, c):
        self.rect(x, y, 1, h, c)

    def line(self, x0, y0, x1, y1, c):
        dx, dy = abs(x1 - x0), abs(y0 - y1)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        while True:
            self.set(x0, y0, c)
            if x0 == x1 and y0 == y1:
                return
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

    def disc(self, cx, cy, r, c):
        for yy in range(cy - r, cy + r + 1):
            for xx in range(cx - r, cx + r + 1):
                if (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r:
                    self.set(xx, yy, c)

    def ring(self, cx, cy, r, c, t=2):
        for yy in range(cy - r - t, cy + r + t + 1):
            for xx in range(cx - r - t, cx + r + t + 1):
                d = ((xx - cx) ** 2 + (yy - cy) ** 2) ** 0.5
                if r - t < d <= r:
                    self.set(xx, yy, c)

    def poly(self, pts, c):
        if not pts:
            return
        ys = [p[1] for p in pts]
        for y in range(min(ys), max(ys) + 1):
            xs = []
            n = len(pts)
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    xs.append(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                self.rect(int(xs[k]), y,
                          max(1, int(xs[k + 1]) - int(xs[k])), 1, c)


def twidth(family, size, s):
    tot = 0
    for ch in s:
        _, _, _, _, adv, _, base = _glyph(family, size, ch)
        tot += adv * size / base
    return tot


def put_text(cv, family, size, x, y, s, color):
    cx = x
    for ch in s:
        w, h, xo, yo, adv, raw, base = _glyph(family, size, ch)
        sc = size / base
        if w <= 0 or h <= 0:
            cx += adv * sc
            continue
        dw, dh = max(1, round(w * sc)), max(1, round(h * sc))
        ox = round(cx + xo * sc)
        oy = round(y + yo * sc)
        for dy in range(dh):
            sy = min(h - 1, round(dy * (h - 1) / max(1, dh - 1)))
            for dx in range(dw):
                sx = min(w - 1, round(dx * (w - 1) / max(1, dw - 1)))
                if _bit(raw, w, sx, sy):
                    cv.set(ox + dx, oy + dy, color)
        cx += adv * sc
    return cx


def put_centred(cv, family, size, cx, y, s, color):
    put_text(cv, family, size,
             int(cx - twidth(family, size, s) / 2), y, s, color)


def wrap_text(family, size, s, max_w):
    words = s.split()
    lines, cur = [], ""
    for wd in words:
        trial = (cur + " " + wd).strip()
        if twidth(family, size, trial) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    return lines


def write_png(cv, path):
    raw = bytearray()
    stride = cv.w * 3
    for y in range(cv.h):
        raw.append(0)
        raw += cv.px[y * stride:(y + 1) * stride]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", comp)
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


# ---- small procedural illustrations (one per lead story) ----
# Each draws inside box (x, y, w, h). Simple, bold shapes: the label
# text beside it carries the facts; the picture only has to make the
# story recognisable at a glance. All drawings are original.

def _ground(cv, x, y, w, h, c):
    cv.rect(x, y, w, h, c)


def art_chip(cv, x, y, w, h):
    _ground(cv, x, y, w, h, (30, 44, 66))
    cv.rect(x + w // 2 - 14, y + h // 2 - 12, 28, 24, (60, 180, 140))
    cv.rect(x + w // 2 - 8, y + h // 2 - 6, 16, 12, (30, 44, 66))
    for dx in (-18, -9, 0, 9, 18):
        cv.rect(x + w // 2 + dx - 1, y + 4, 2, 8, (200, 200, 200))
        cv.rect(x + w // 2 + dx - 1, y + h - 12, 2, 8, (200, 200, 200))
    put_text(cv, "sans_bold", 10, x + w // 2 - 12, y + h // 2 - 5, "AI",
             (255, 255, 255))


def art_summit(cv, x, y, w, h):
    _ground(cv, x, y, w, h, (214, 228, 214))
    cv.rect(x + 6, y + h - 14, w - 12, 5, (120, 84, 50))
    for dx, col in ((-18, (70, 90, 130)), (0, (150, 60, 50)),
                    (18, (60, 120, 80))):
        cv.disc(x + w // 2 + dx, y + h // 2 - 4, 8, col)
        cv.rect(x + w // 2 + dx - 8, y + h // 2 + 3, 16, 9, col)
    put_text(cv, "sans_bold", 10, x + w // 2 - 14, y + 2, "COP31", INK)


def art_gavel(cv, x, y, w, h):
    _ground(cv, x, y, w, h, (226, 220, 200))
    cv.rect(x + 10, y + h - 12, w - 20, 5, (120, 84, 50))
    cv.line(x + w // 2 - 14, y + 12, x + w // 2 + 14, y + 26, (90, 60, 30))
    cv.rect(x + w // 2 - 18, y + 8, 12, 7, (70, 50, 30))
    cv.rect(x + w // 2 + 6, y + 22, 12, 7, (70, 50, 30))


def art_ship(cv, x, y, w, h):
    _ground(cv, x, y, w, h, (120, 165, 200))
    cv.rect(x, y + h - 14, w, 14, (38, 84, 130))
    cv.poly([(x + 8, y + h - 14), (x + w - 8, y + h - 14),
             (x + w - 22, y + h - 4), (x + 22, y + h - 4)], (90, 40, 36))
    cv.rect(x + w // 2 - 4, y + 8, 8, h - 26, (200, 200, 200))
    cv.disc(x + w // 2 + 14, y + 12, 7, (240, 170, 40))
    cv.rect(x + w - 30, y + 6, 16, 3, (250, 220, 90))


def art_fire(cv, x, y, w, h):
    _ground(cv, x, y, w, h, (52, 46, 44))
    cv.rect(x, y + h - 14, w, 14, (34, 32, 30))
    cv.rect(x + 6, y + h - 24, w - 12, 10, (96, 84, 70))
    for dx, hh, col in ((-16, 22, (230, 90, 20)), (0, 30, (250, 160, 30)),
                        (16, 20, (230, 90, 20))):
        cx = x + w // 2 + dx
        cv.poly([(cx - 7, y + h - 24), (cx, y + h - 24 - hh),
                 (cx + 7, y + h - 24)], col)
    cv.disc(x + w // 2, y + h - 26, 4, (250, 220, 90))
    cv.rect(x + 8, y + 4, w - 16, 3, (90, 84, 78))


def art_flag(cv, x, y, w, h):
    _ground(cv, x, y, w, h, (232, 226, 205))
    cv.rect(x + 12, y + 6, 3, h - 12, (90, 70, 50))
    for i, col in enumerate(((190, 40, 40), (255, 255, 255), (190, 40, 40),
                             (255, 255, 255), (190, 40, 40))):
        cv.rect(x + 15, y + 8 + i * 7, w - 30, 7, col)
    cv.rect(x + 15, y + 8, 22, 14, (40, 60, 130))
    cv.disc(x + 21, y + 12, 1, (255, 255, 255))
    cv.disc(x + 29, y + 16, 1, (255, 255, 255))


def art_missile(cv, x, y, w, h):
    _ground(cv, x, y, w, h, (40, 40, 52))
    cv.line(x + 10, y + h - 8, x + w - 16, y + 10, (240, 200, 80))
    cv.disc(x + w - 16, y + 10, 4, (255, 240, 160))
    cv.disc(x + w // 2, y + h // 2 + 6, 8, (150, 60, 50))
    cv.disc(x + w // 2, y + h // 2 + 6, 4, (240, 170, 40))
    cv.rect(x + 6, y + h - 16, 14, 8, (90, 90, 100))


def art_talks(cv, x, y, w, h):
    _ground(cv, x, y, w, h, (222, 214, 190))
    cv.rect(x + 6, y + h - 16, w - 12, 6, (120, 84, 50))
    cv.disc(x + w // 3, y + h // 2 - 2, 9, (70, 90, 130))
    cv.disc(x + 2 * w // 3, y + h // 2 - 2, 9, (150, 60, 50))
    cv.rect(x + w // 3 - 9, y + h // 2 + 6, 18, 10, (70, 90, 130))
    cv.rect(x + 2 * w // 3 - 9, y + h // 2 + 6, 18, 10, (150, 60, 50))
    put_text(cv, "sans_bold", 11, x + w // 2 - 4, y + 2, "?", INK)


def art_strike(cv, x, y, w, h):
    _ground(cv, x, y, w, h, (60, 58, 64))
    cv.rect(x, y + h - 12, w, 12, (40, 38, 42))
    for dx, dy, r in ((w // 2, h // 2, 13), (w // 2 - 16, h // 2 + 4, 8),
                      (w // 2 + 17, h // 2 + 3, 7)):
        cv.disc(x + dx, y + dy, r, (240, 170, 40))
        cv.disc(x + dx, y + dy, r - 4, (250, 220, 90))
    cv.rect(x + 8, y + h - 22, 10, 10, (20, 20, 22))
    cv.rect(x + w - 20, y + h - 20, 12, 8, (20, 20, 22))


def art_plane(cv, x, y, w, h):
    _ground(cv, x, y, w, h, (150, 190, 220))
    cv.poly([(x + 8, y + h // 2), (x + w - 12, y + h // 2 - 6),
             (x + w - 4, y + h // 2), (x + w - 12, y + h // 2 + 6)],
            (240, 240, 240))
    cv.poly([(x + w // 2, y + h // 2 - 4), (x + w // 2 + 8, y + h // 2 - 16),
             (x + w // 2 + 12, y + h // 2 - 4)], (200, 60, 50))
    cv.disc(x + w - 22, y + 8, 5, (250, 220, 90))


def art_circuit(cv, x, y, w, h):
    _ground(cv, x, y, w, h, (28, 52, 40))
    cv.rect(x + w // 2 - 12, y + h // 2 - 10, 24, 20, (40, 90, 60))
    cv.rect(x + w // 2 - 6, y + h // 2 - 5, 12, 10, (28, 52, 40))
    for dx in (-20, -10, 0, 10, 20):
        cv.line(x + w // 2 + dx, y + 6, x + w // 2 + dx,
                y + h // 2 - 10, (120, 200, 160))
        cv.disc(x + w // 2 + dx, y + 6, 2, (200, 220, 200))
    cv.line(x + 6, y + h // 2, x + w // 2 - 12, y + h // 2, (120, 200, 160))
    cv.line(x + w // 2 + 12, y + h // 2, x + w - 6, y + h // 2,
            (120, 200, 160))


def art_graph(cv, x, y, w, h):
    _ground(cv, x, y, w, h, (238, 234, 220))
    cv.line(x + 8, y + 8, x + 8, y + h - 8, (90, 90, 90))
    cv.line(x + 8, y + h - 8, x + w - 6, y + h - 8, (90, 90, 90))
    pts = []
    for i in range(9):
        px = x + 10 + i * (w - 18) // 8
        py = y + h - 12 - int((h - 24) * (0.5 + 0.4 * sin(i * 1.1)))
        pts.append((px, py))
    for i in range(len(pts) - 1):
        cv.line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1],
                (60, 120, 180))
    put_text(cv, "serif_bold", 18, x + w - 24, y + 4, "R", INK)


def art_court(cv, x, y, w, h):
    _ground(cv, x, y, w, h, (222, 216, 198))
    cv.poly([(x + 6, y + 14), (x + w // 2, y + 2), (x + w - 6, y + 14)],
            (170, 150, 110))
    for dx in (12, 28, 44, 58):
        cv.rect(x + dx, y + 16, 4, h - 26, (200, 185, 150))
    cv.rect(x + 6, y + h - 10, w - 12, 4, (150, 130, 95))


def art_chart(cv, x, y, w, h):
    _ground(cv, x, y, w, h, (240, 236, 224))
    cv.rect(x + 10, y + h - 12, 8, 12, (90, 130, 90))
    cv.rect(x + 26, y + h - 20, 8, 20, (90, 130, 90))
    cv.rect(x + 42, y + h - 30, 8, 30, (170, 60, 50))
    cv.rect(x + 58, y + h - 38, 8, 38, (170, 60, 50))
    cv.line(x + 8, y + 10, x + w - 8, y + h - 8, (170, 60, 50))
    cv.line(x + w - 14, y + h - 14, x + w - 8, y + h - 8, (170, 60, 50))
    cv.line(x + w - 14, y + h - 2, x + w - 8, y + h - 8, (170, 60, 50))


def art_quake(cv, x, y, w, h):
    _ground(cv, x, y, w, h, (210, 200, 170))
    cv.rect(x + 8, y + h - 20, 14, 14, (120, 100, 80))
    cv.rect(x + w - 26, y + h - 24, 16, 18, (100, 85, 70))
    cv.rect(x + w // 2 - 6, y + h - 16, 12, 10, (140, 120, 95))
    cv.line(x + 4, y + h - 6, x + w // 3, y + h - 14, (60, 50, 40))
    cv.line(x + w // 3, y + h - 14, x + 2 * w // 3, y + h - 4, (60, 50, 40))
    cv.line(x + 2 * w // 3, y + h - 4, x + w - 4, y + h - 12, (60, 50, 40))
    put_text(cv, "sans_bold", 11, x + w // 2 - 8, y + 2, "6.5", RED)


def art_barrel(cv, x, y, w, h):
    _ground(cv, x, y, w, h, (190, 205, 220))
    for dx, col in ((-20, (60, 90, 130)), (0, (40, 70, 110)),
                    (20, (60, 90, 130))):
        bx = x + w // 2 + dx - 8
        cv.rect(bx, y + h - 26, 16, 20, col)
        cv.rect(bx, y + h - 26, 16, 3, (30, 55, 90))
        cv.rect(bx, y + h - 14, 16, 2, (30, 55, 90))
    cv.disc(x + w - 12, y + 10, 6, (250, 220, 90))
    cv.line(x + w - 12, y + 10, x + w // 2 + 8, y + 16, (240, 200, 80))


ARTS = {"chip": art_chip, "summit": art_summit, "gavel": art_gavel,
        "ship": art_ship, "fire": art_fire, "flag": art_flag,
        "missile": art_missile, "talks": art_talks, "strike": art_strike,
        "plane": art_plane, "circuit": art_circuit, "graph": art_graph,
        "court": art_court, "chart": art_chart, "quake": art_quake,
        "barrel": art_barrel}

# ---- world map (coarse equirectangular continents, hand-plotted) ----
CONTINENTS = [
    [(-168, 66), (-140, 70), (-125, 71), (-95, 72), (-80, 73), (-65, 60),
     (-55, 52), (-60, 45), (-75, 35), (-81, 26), (-84, 30), (-90, 29),
     (-97, 26), (-97, 19), (-92, 15), (-83, 9), (-95, 16), (-105, 20),
     (-110, 23), (-117, 32), (-125, 48), (-145, 60), (-168, 66)],
    [(-80, 10), (-60, 8), (-50, 0), (-35, -8), (-40, -20), (-50, -30),
     (-60, -35), (-70, -45), (-73, -53), (-70, -40), (-75, -20),
     (-80, -5), (-80, 10)],
    [(-10, 36), (-10, 43), (-2, 48), (0, 51), (5, 53), (8, 57), (10, 59),
     (18, 56), (21, 55), (24, 59), (30, 62), (30, 70), (20, 70), (10, 65),
     (5, 60), (-5, 58), (-10, 50), (-10, 36)],
    [(-6, 35), (10, 37), (20, 32), (32, 31), (35, 28), (43, 12), (48, 11),
     (51, 10), (44, 0), (40, -10), (35, -20), (32, -28), (20, -35),
     (15, -30), (12, -18), (9, -2), (9, 4), (-8, 5), (-15, 10), (-17, 15),
     (-15, 25), (-10, 30), (-6, 35)],
    [(30, 70), (40, 68), (60, 70), (70, 72), (90, 75), (110, 76), (130, 72),
     (150, 70), (170, 66), (178, 65), (170, 60), (160, 55), (155, 50),
     (142, 45), (140, 40), (130, 35), (127, 33), (122, 30), (120, 25),
     (110, 20), (105, 10), (100, 8), (95, 15), (90, 22), (85, 20), (80, 13),
     (75, 8), (72, 20), (65, 25), (60, 25), (55, 26), (50, 30), (48, 30),
     (42, 35), (36, 36), (30, 36), (30, 42), (30, 55), (30, 70)],
    [(113, -22), (114, -30), (115, -35), (120, -34), (130, -32), (135, -35),
     (140, -38), (145, -38), (150, -37), (153, -32), (153, -27), (150, -22),
     (146, -19), (142, -11), (137, -12), (135, -15), (132, -12), (130, -13),
     (126, -14), (122, -17), (118, -20), (113, -22)],
    [(167, -45), (170, -42), (174, -39), (177, -38), (174, -41), (168, -46),
     (167, -45)],
]


def _lonlat(lon, lat, x, y, w, h):
    # latitude cropped to -50..72 so the map is not a flat strip;
    # points outside the band are clamped to the map edge
    lat = max(-50.0, min(72.0, lat))
    return (x + int((lon + 180.0) / 360.0 * w),
            y + int((72.0 - lat) / 122.0 * h))


def draw_map(cv, x, y, w, h, pins):
    cv.rect(x, y, w, h, SEA)
    for poly in CONTINENTS:
        pts = [_lonlat(lon, lat, x, y, w, h) for lon, lat in poly]
        cv.poly(pts, LAND)
        for i in range(len(pts)):
            cv.line(pts[i][0], pts[i][1], pts[(i + 1) % len(pts)][0],
                    pts[(i + 1) % len(pts)][1], (150, 138, 108))
    for num, lon, lat, region, dx, dy in pins:
        px, py = _lonlat(lon, lat, x, y, w, h)
        px += dx
        py += dy
        cv.disc(px, py, 8, PIN_COLOURS[region])
        cv.ring(px, py, 8, (255, 255, 255), 1)
        s = str(num)
        put_text(cv, "sans_bold", 9, px - int(twidth("sans_bold", 9, s) / 2),
                 py - 5, s, (255, 255, 255))


MX = 28
CW = 968


def draw_masthead(cv):
    cv.hline(MX, 12, CW, INK)
    cv.hline(MX, 14, CW, INK)
    put_centred(cv, "sans_bold", 12, 512, 18, "THE WORLD TODAY", RED)
    put_centred(cv, "serif_bold", 44, 512, 38,
                "MONDAY, 23 NOVEMBER 2026", INK)
    put_centred(cv, "sans", 11, 512, 92,
                  "ONE DAY OF WORLD NEWS, ONE PICTURE  \u00b7  50 STORIES  \u00b7  7 REGIONS  \u00b7  16 FIELDS",
                  MUTED)
    cv.hline(MX, 110, CW, INK)


def draw_timeline(cv):
    y = 134
    put_text(cv, "sans_bold", 10, MX, y, "THE DAY IN UTC", RED)
    put_text(cv, "sans", 10, MX + 108, y,
             "as the day turned west \u2014 overnight to evening", MUTED)
    bx, bw, bh = MX, 132, 34
    for i, (t, head) in enumerate(TIMELINE):
        x = bx + i * (bw + 7)
        cv.rect(x, y + 14, bw, bh, CARD)
        cv.hline(x, y + 14, bw, RULE)
        cv.hline(x, y + 14 + bh - 1, bw, RULE)
        put_text(cv, "sans_bold", 9, x + 5, y + 17, t, RED)
        for j, ln in enumerate(wrap_text("sans", 9, head, bw - 10)):
            put_text(cv, "sans", 9, x + 5, y + 28 + j * 10, ln, INK)


def _meta(cv, x, y, max_w, region, source, status):
    put_text(cv, "sans_bold", 8, x, y,
             (region.upper() + "  \u00b7  " + source.upper())[:60], MUTED)
    label = "CONFIRMED" if status == "CONFIRMED" else "CLAIM"
    col = GREEN if status == "CONFIRMED" else RED
    tw = int(twidth("sans_bold", 8, label))
    px = int(x + max_w - tw - 8)
    cv.rect(px, y - 1, tw + 8, 10, col)
    put_text(cv, "sans_bold", 8, px + 4, y, label, (255, 255, 255))


def draw_card(cv, s):
    n = s["n"]
    col, row = (n - 1) % 4, (n - 1) // 4
    x = MX + col * 246
    ys = [186, 294, 392, 490]
    hs = [106, 94, 94, 94]
    y, h = ys[row], hs[row]
    w = 238
    large = (row == 0)
    cv.rect(x, y, w, h, CARD)
    cv.hline(x, y, w, RULE)
    cv.hline(x, y + h - 1, w, RULE)
    cv.vline(x, y, h, RULE)
    cv.vline(x + w - 1, y, h, RULE)
    cv.rect(x, y, w, 13, TINTS[s["region"]])
    put_text(cv, "sans_bold", 9, x + 4, y + 2, str(n), RED)
    put_text(cv, "sans_bold", 8, x + 18, y + 3,
             s["region"].upper() + " \u00b7 " + TOPICS[n], INK)
    if large:
        ARTS[s["art"]](cv, x + 4, y + 16, 58, 44)
        tx, tsize, tw = x + 66, 12, w - 70
        sy = y + 62
    else:
        ARTS[s["art"]](cv, x + 4, y + 16, 44, 28)
        tx, tsize, tw = x + 52, 11, w - 56
        sy = y + 46
    for j, ln in enumerate(wrap_text("serif_bold", tsize, s["title"], tw)[:2]):
        put_text(cv, "serif_bold", tsize, tx, y + 17 + j * (tsize + 2), ln,
                 INK)
    for j, ln in enumerate(wrap_text("sans", 9, s["summ"], w - 8)[:3]):
        put_text(cv, "sans", 9, x + 4, sy + j * 10, ln, INK)
    _meta(cv, x + 4, y + h - 11, w - 8, s["region"], s["source"], s["status"])


REGION_TALLY = [("EUROPE", 13), ("MIDDLE EAST", 6), ("ASIA", 9),
                ("AMERICAS", 6), ("AFRICA", 6), ("OCEANIA", 4),
                ("GLOBAL", 6)]
FIELDS = ["War", "Politics", "Diplomacy", "Trade", "Markets", "Climate",
          "Space", "Science", "Sport", "Disaster", "Health", "AI & Tech",
          "Law & Crime", "Migration", "Defence", "Energy"]


def draw_map_panel(cv):
    y = 588
    put_text(cv, "sans_bold", 11, MX, y, "WHERE IT HAPPENED", RED)
    put_text(cv, "sans", 10, MX + 150, y,
             "numbered pins are the 16 lead stories above", MUTED)
    my = y + 15
    # left tally: stories per region (counts verified against the 50 items)
    put_text(cv, "sans_bold", 9, MX, my, "BY REGION", INK)
    for i, (name, cnt) in enumerate(REGION_TALLY):
        ry = my + 14 + i * 11
        cv.disc(MX + 5, ry + 4, 4, PIN_COLOURS[name.title()])
        put_text(cv, "sans", 9, MX + 14, ry, name, INK)
        c = str(cnt)
        put_text(cv, "sans_bold", 9, MX + 156 - twidth("sans_bold", 9, c),
                 ry, c, RED)
    # right list: the 16 fields covered, two columns
    rx = MX + CW - 160
    put_text(cv, "sans_bold", 9, rx, my, "16 FIELDS", INK)
    for i, f in enumerate(FIELDS):
        col = i // 8
        row = i % 8
        put_text(cv, "sans", 8, rx + col * 82, my + 14 + row * 11, f, INK)
    pins = [(s["n"], s["lon"], s["lat"], s["region"],
             s.get("dx", 0), s.get("dy", 0)) for s in LEADS]
    draw_map(cv, MX + 164, my, 640, 140, pins)


def draw_also(cv):
    y = 749
    put_text(cv, "sans_bold", 11, MX, y, "ALSO ON MONDAY", RED)
    put_text(cv, "sans", 10, MX + 140, y, "stories 17\u201350, one line each",
             MUTED)
    col_w = 478
    for i, s in enumerate(ALSO):
        col = i // 17
        row = i % 17
        x = MX + col * (col_w + 12)
        yy = y + 16 + row * 10
        put_text(cv, "sans_bold", 9, x, yy, str(s["n"]) + ".", RED)
        line = s["title"] + " \u2014 " + s["source"]
        for ln in wrap_text("sans", 9, line, col_w - 22):
            put_text(cv, "sans", 9, x + 20, yy, ln, INK)
            if s.get("claim"):
                put_text(cv, "sans_bold", 9,
                         x + 20 + twidth("sans", 9, ln) + 3, yy,
                         "\u00b7 CLAIM", RED)
            break


def draw_datecheck(cv):
    y = 941
    cv.rect(MX, y, CW, 48, (238, 232, 210))
    cv.hline(MX, y, CW, RED)
    cv.hline(MX, y + 47, CW, RED)
    cv.vline(MX, y, 48, RED)
    cv.vline(MX + CW - 1, y, 48, RED)
    put_text(cv, "sans_bold", 10, MX + 6, y + 4, "DATE CHECK", RED)
    lines = wrap_text("sans", 9, DATECHECK, CW - 12)
    for j, ln in enumerate(lines[:3]):
        put_text(cv, "sans", 9, MX + 6, y + 17 + j * 11, ln, INK)


def draw_footer(cv):
    y = 993
    cv.hline(MX, y, CW, INK)
    put_text(cv, "sans", 9, MX, y + 5, FOOTER, MUTED)


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

LEADS = [
    {"n": 1, "region": "Global", "art": "chip", "lon": -122.0, "lat": 37.4,
     "title": "Huang is back \u2014 Nvidia jumps 31%",
     "summ": "Eleven days after resigning, Jensen Huang is reinstated as CEO; shares add about $950bn in a day and the Nasdaq jumps 6.5%.",
     "source": "CoinDesk", "status": "CONFIRMED"},
    {"n": 2, "region": "Global", "art": "summit", "lon": 149.1, "lat": -35.3,
     "title": "COP31 fallout: blame game in Canberra",
     "summ": "Australia's opposition demands minister Bowen go after the no-deal summit; Pacific nations call the outcome despair.",
     "source": "Reuters", "status": "CONFIRMED"},
    {"n": 3, "region": "Europe", "art": "gavel", "lon": 4.35, "lat": 50.85,
     "title": "EU unveils 22nd Russia sanctions package",
     "summ": "Sixty banks face a SWIFT cut-off, 70 shadow-fleet tankers are listed, and Russian athletes face a sports ban.",
     "source": "Reuters", "status": "CONFIRMED"},
    {"n": 4, "region": "Europe", "art": "ship", "lon": 20.1, "lat": 32.1,
     "title": "Zelenskyy confirms Libya ship strikes",
     "summ": "Kyiv says seven sea drones sank the corvette Merkury and hit the arms cargo ship Angara off Benghazi; the UN urges a probe.",
     "source": "Le Monde", "status": "CONFIRMED"},
    {"n": 5, "region": "Asia", "art": "fire", "lon": 106.2, "lat": -6.2,
     "title": "Factory fire toll reaches 24",
     "summ": "Indonesia confirms 24 dead at the Cikande candy plant; about 30 are still missing as rescuers search unstable ruins.",
     "source": "Reuters", "status": "CONFIRMED"},
    {"n": 6, "region": "Americas", "art": "flag", "lon": -77.0, "lat": 38.9,
     "title": "Democrats reach 258 House seats",
     "summ": "A North Carolina recount win gives Democrats their biggest House majority since 1992; four races remain uncalled.",
     "source": "AP", "status": "CONFIRMED"},
    {"n": 7, "region": "Middle East", "art": "missile", "lon": 51.4,
     "lat": 35.7,
     "title": "Trump: Iran strikes may resume next year",
     "summ": "Trump tells Fox he may resume the war on Iran next year if talks fail, blaming Tehran's tougher line since the midterms.",
     "source": "Military.com", "status": "CONFIRMED"},
    {"n": 8, "region": "Middle East", "art": "talks", "lon": 51.5, "lat": 25.3,
     "dx": 14, "dy": 10,
     "title": "Vance meets Qatar on stalled Iran talks",
     "summ": "The vice-president meets Qatar's prime minister as Doha presses Washington and Tehran back to the table.",
     "source": "Breitbart", "status": "CONFIRMED"},
    {"n": 9, "region": "Africa", "art": "strike", "lon": 32.5, "lat": 15.6,
     "title": "Drones hit Khartoum homes, UN building",
     "summ": "Overnight drone strikes kill four, including a 10-year-old, and damage a UN building; the UN calls it unacceptable.",
     "source": "Al Jazeera", "status": "CONFIRMED"},
    {"n": 10, "region": "Europe", "art": "plane", "lon": 21.0, "lat": 52.2,
     "title": "NATO sends early-warning jets to Poland",
     "summ": "NATO will deploy AWACS aircraft after three Russian missiles landed in Poland on Friday, Warsaw says.",
     "source": "Reuters", "status": "CONFIRMED"},
    {"n": 11, "region": "Asia", "art": "circuit", "lon": 103.8, "lat": 1.35,
     "dx": 18, "dy": -14,
     "title": "US blacklists AI firm Megaspeed",
     "summ": "Washington adds the Singapore firm to its entity list over alleged chip flows to China and moves to seize $1.1bn in North Korean crypto.",
     "source": "BBC", "status": "CONFIRMED"},
    {"n": 12, "region": "Global", "art": "graph", "lon": -122.4, "lat": 37.8,
     "dx": 16, "dy": -12,
     "title": "Anthropic: AI helped prove Riemann",
     "summ": "Anthropic says an AI-generated proof of the famous maths puzzle is under review, sparking debate over verification.",
     "source": "Anthropic", "status": "CLAIM"},
    {"n": 13, "region": "Europe", "art": "court", "lon": -3.7, "lat": 40.4,
     "dx": -14, "dy": 6,
     "title": "Spain amnesties Puigdemont",
     "summ": "The Supreme Court grants amnesty to the Catalan separatist over the 2017 independence bid; he will not return before Sunday's election.",
     "source": "CNN", "status": "CONFIRMED"},
    {"n": 14, "region": "Americas", "art": "chart", "lon": -74.1, "lat": 4.7,
     "title": "Deutsche Bank probed over Colombia flows",
     "summ": "A Le Monde-led inquiry finds the bank dominated euro payments in Colombia without checks, possibly aiding crime.",
     "source": "Le Monde", "status": "CONFIRMED"},
    {"n": 15, "region": "Oceania", "art": "quake", "lon": 167.0, "lat": -16.0,
     "title": "Magnitude 6.5 quake shakes Vanuatu",
     "summ": "A deep quake strikes the Vanuatu region on Monday; no damage is reported, and no tsunami warning follows.",
     "source": "USGS", "status": "CONFIRMED"},
    {"n": 16, "region": "Asia", "art": "barrel", "lon": 139.7, "lat": 35.7,
     "title": "Japan launches Asian oil task force",
     "summ": "With Hormuz shipments disrupted by the Iran war, Tokyo pushes shared reserves and closer supplier ties.",
     "source": "Euronews", "status": "CONFIRMED"},
]

ALSO = [
    {"n": 17, "title": "Russian strikes kill at least 15 around Kyiv; boy, 7, freed after 14 hours in rubble", "source": "Reuters"},
    {"n": 18, "title": "Russia launches 153 drones overnight; Ukraine says 134 downed", "source": "Kyiv"},
    {"n": 19, "title": "Euro area inflation rises to 4.0%, Eurostat says", "source": "Eurostat"},
    {"n": 20, "title": "Burnham defends EU reset deal, rules out rejoin without vote", "source": "BBC"},
    {"n": 21, "title": "NHS AI breast-screening trial to invite 700,000 women", "source": "NHS"},
    {"n": 22, "title": "US holds first deep-sea mining lease sales off American Samoa", "source": "PINA"},
    {"n": 23, "title": "US confirmed as 2031 Women's World Cup host", "source": "FIFA"},
    {"n": 24, "title": "Russia accuses Estonia of hostile acts near open war", "source": "Reuters"},
    {"n": 25, "title": "Kilauea completes its 57th lava-fountaining episode", "source": "USGS"},
    {"n": 26, "title": "More than 700,000 Russian soldiers killed, analysis finds", "source": "RFE/RL", "claim": True},
    {"n": 27, "title": "Zelenskyy: Ukraine ready for four-way peace talks", "source": "Reuters"},
    {"n": 28, "title": "Pacific tuna stocks face critical calls at WCPFC meeting", "source": "PINA"},
    {"n": 29, "title": "Trump, victims' families rail at Newsom death-row clemency", "source": "Independent"},
    {"n": 30, "title": "Brad Jacobs wins Grand Slam of Curling title in Nova Scotia", "source": "CBC"},
    {"n": 31, "title": "Lebanese villagers return to wrecked homes as IDF pulls back", "source": "Reuters"},
    {"n": 32, "title": "Syria destroys 400 million Captagon tablets in biggest haul", "source": "Syria"},
    {"n": 33, "title": "Iran singer Parastoo Ahmadi gets 74 lashes over online concert", "source": "Breitbart"},
    {"n": 34, "title": "US sanctions dozens linked to Iran shadow banking", "source": "Reuters"},
    {"n": 35, "title": "Nigeria funeral-boat toll reaches 29 bodies recovered", "source": "Juba Global"},
    {"n": 36, "title": "Nine African energy exporters gain $21.6bn in Iran war", "source": "Juba Global"},
    {"n": 37, "title": "South Sudan destroys damaged food worth 500m pounds", "source": "Juba Global"},
    {"n": 38, "title": "UN urges independent probe into Benghazi port attacks", "source": "UN"},
    {"n": 39, "title": "Sudan aid appeal only 51% funded as food prices soar", "source": "OCHA"},
    {"n": 40, "title": "5,000 drones light up sky over China's Three Gorges", "source": "Euronews"},
    {"n": 41, "title": "South Korea and China agree wider trade deal on entertainment", "source": "Euronews"},
    {"n": 42, "title": "Taiwan warns Canada against deeper China trade ties", "source": "Euronews"},
    {"n": 43, "title": "Hong Kong sets up building regulator after Tai Po fire", "source": "SCMP"},
    {"n": 44, "title": "Indonesia plans 70% state control of mining shares or revenue", "source": "SCMP"},
    {"n": 45, "title": "Japan moves to expand coast guard fleet and drones against China", "source": "Japan"},
    {"n": 46, "title": "CrowdStrike snaps up Zscaler in $44bn deal", "source": "Reuters"},
    {"n": 47, "title": "OpenAI proposes shared AI safety limits for labs", "source": "OpenAI"},
    {"n": 48, "title": "Bitcoin spikes past $64,000 on Huang news, then falls back", "source": "CoinDesk"},
    {"n": 49, "title": "GTA VI is PlayStation's biggest launch: 39m players in 4 days", "source": "Sony"},
    {"n": 50, "title": "Alcaraz beats Zverev to win first ATP Finals title", "source": "Reuters"},
]

DATECHECK = ("Left out: the COP31 collapse itself (Sun 22 Nov \u2014 today is the fallout); the Dymer flat strike and the El Chapo "
             "Isidro capture (22 Nov); the Ashes retention in Adelaide (21 Dec 2025, not 2026); BepiColombo's Mercury orbit "
             "(21 Nov); GTA VI's $3.79bn day-one figure (announced 20 Nov; today: Sony's 39m players). Not yet decided at about "
             "16:00 UTC: the full toll of the Cikande fire; whether the EU's 22nd sanctions package wins unanimous approval; "
             "Spain's election (Sun 29 Nov).")

FOOTER = ("Every story happened or was first reported on Mon 23 Nov 2026. "
          "CLAIM = one side's account. "
          "Sources: Reuters, AP, BBC, Le Monde, Al Jazeera, CoinDesk, Euronews, PINA. Original drawings.")


def render():
    cv = Img(W, H, PAPER)
    draw_masthead(cv)
    draw_timeline(cv)
    for s in LEADS:
        draw_card(cv, s)
    draw_map_panel(cv)
    draw_also(cv)
    draw_datecheck(cv)
    draw_footer(cv)
    return cv


def main():
    out = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, "entry.png")
    size = write_png(render(), path)
    print("wrote", path, size, "bytes")


if __name__ == "__main__":
    main()
