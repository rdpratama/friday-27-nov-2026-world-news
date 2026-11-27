#!/usr/bin/env python3
"""Friday 27 November 2026 - the world in one image.

A newspaper front page drawn with the Python 3.13 standard library only.
It writes a deterministic 1024x1024 PNG to /output/entry.png (or to the
directory named by MAKEFUN_OUTPUT_DIR). No network, no randomness: two runs
write identical bytes.

Layout (superskie newspaper template): giant serif-style date masthead,
count line, THE DAY IN UTC strip, THE DAY IN NUMBERS strip, 3 hero panels
+ 10 medium panels with original drawn scenes, WHERE IT HAPPENED world map
with region counts, a numbered list of the remaining stories, a DATE CHECK
box of deliberately excluded pre-dated stories, and a source footer.
48 verified stories, 7 regions, 14 fields, all from Friday 27 November 2026.
"""

import os
import struct
import zlib

W = 1024
H = 1024

# ---------------------------------------------------------------- PNG encoder

def png_bytes(rgb, w, h):
    """Encode a flat RGB bytearray as a PNG (colour type 2, no filtering)."""
    raw = bytearray()
    stride = w * 3
    for y in range(h):
        raw.append(0)
        raw += rgb[y * stride:(y + 1) * stride]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(ctype, data):
        c = struct.pack(">I", len(data)) + ctype + data
        c += struct.pack(">I", zlib.crc32(ctype + data) & 0xFFFFFFFF)
        return c

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", comp) + chunk(b"IEND", b""))


# ------------------------------------------------------------------- canvas

class Canvas:
    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.px = bytearray(bg * (w * h))

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i:i + 3] = c

    def rect(self, x, y, w, h, c):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        for yy in range(y0, y1):
            i = (yy * self.w + x0) * 3
            self.px[i:(i + (x1 - x0) * 3)] = c * (x1 - x0)

    def hline(self, x, y, w, c):
        self.rect(x, y, w, 1, c)

    def vline(self, x, y, h, c):
        self.rect(x, y, 1, h, c)

    def line(self, x0, y0, x1, y1, c):
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            self.set(x0, y0, c)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def circle(self, cx, cy, r, c):
        for yy in range(cy - r, cy + r + 1):
            dx = int((r * r - (yy - cy) ** 2) ** 0.5) if abs(yy - cy) <= r else 0
            self.hline(cx - dx, yy, 2 * dx + 1, c)

    def ring(self, cx, cy, r, c, t=2):
        for k in range(t):
            rr = r - k
            for a in range(360):
                import math
                x = cx + int(rr * math.cos(a * math.pi / 180))
                y = cy + int(rr * math.sin(a * math.pi / 180))
                self.set(x, y, c)

    def poly(self, pts, c):
        """Scanline fill of a polygon given as [(x, y), ...]."""
        if len(pts) < 3:
            return
        ys = [p[1] for p in pts]
        for y in range(max(0, min(ys)), min(self.h, max(ys) + 1)):
            xs = []
            n = len(pts)
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    xs.append(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                self.hline(int(xs[k]), y, max(1, int(xs[k + 1]) - int(xs[k])), c)

    def tri(self, ax, ay, bx, by, cx, cy, c):
        self.poly([(ax, ay), (bx, by), (cx, cy)], c)


# ------------------------------------------------------------- 5x7 bitmap font
# Each glyph: 7 rows of 5 bits, '#' = ink. Uppercase + digits + punctuation.

FONT = {
    'A': ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    'B': ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    'C': ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    'D': ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    'E': ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    'F': ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    'G': ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    'H': ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    'I': ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    'J': ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    'K': ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    'L': ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    'M': ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    'N': ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    'O': ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    'P': ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    'Q': ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    'R': ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    'S': ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    'T': ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    'U': ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    'V': ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    'W': ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    'X': ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    'Y': ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    'Z': ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    '0': ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    '1': ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    '2': ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    '3': ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    '4': ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    '5': ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    '6': ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    '7': ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    '8': ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    '9': ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    ' ': ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    '.': ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ',': ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    ':': ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    ';': ("00000", "01100", "01100", "00000", "01100", "00100", "01000"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    '-': ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    '/': ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    '(': ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ')': ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    '&': ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    '%': ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    '+': ("00000", "00100", "00100", "01110", "00100", "00100", "00000"),
    '!': ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    '?': ("01110", "10001", "00001", "00110", "00100", "00000", "00100"),
    '$': ("00100", "01111", "10100", "01110", "00101", "11110", "00100"),
    '=': ("00000", "00000", "01110", "00000", "01110", "00000", "00000"),
    '#': ("01010", "01010", "11111", "01010", "11111", "01010", "01010"),
    '[': ("01110", "01000", "01000", "01000", "01000", "01000", "01110"),
    ']': ("01110", "00010", "00010", "00010", "00010", "00010", "01110"),
    '_': ("00000", "00000", "00000", "00000", "00000", "00000", "11111"),
    '"': ("01010", "01010", "00000", "00000", "00000", "00000", "00000"),
    '>': ("01000", "00100", "00010", "00001", "00010", "00100", "01000"),
    '<': ("00010", "00100", "01000", "10000", "01000", "00100", "00010"),
    '*': ("00000", "00100", "10101", "01110", "10101", "00100", "00000"),
    '@': ("01110", "10001", "10111", "10101", "10110", "10000", "01110"),
}

CHAR_W = 6  # 5 pixels + 1 gap, times scale


def text_w(s, scale):
    return len(s) * CHAR_W * scale - scale


def draw_text(cv, x, y, s, scale, color):
    s = s.upper()
    cx = x
    for ch in s:
        g = FONT.get(ch, FONT['?'])
        for r in range(7):
            row = g[r]
            for c in range(5):
                if row[c] == '1':
                    cv.rect(cx + c * scale, y + r * scale, scale, scale, color)
        cx += CHAR_W * scale
    return cx


def wrap(s, width_chars):
    """Greedy word wrap into lines of at most width_chars characters."""
    words = s.split()
    lines = []
    cur = ""
    for w in words:
        if not cur:
            cur = w
        elif len(cur) + 1 + len(w) <= width_chars:
            cur += " " + w
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def draw_para(cv, x, y, s, scale, color, width_chars, line_h=None):
    lh = line_h if line_h is not None else 9 * scale
    for line in wrap(s, width_chars):
        draw_text(cv, x, y, line, scale, color)
        y += lh
    return y


# ------------------------------------------------------------------- palette
PAPER = bytes((250, 246, 238))
INK = bytes((26, 26, 26))
RED = bytes((178, 34, 34))
BLUE = bytes((31, 78, 121))
TEAL = bytes((14, 110, 110))
GOLD = bytes((176, 124, 22))
GREY = bytes((110, 110, 108))
LGREY = bytes((226, 222, 212))
DGREY = bytes((70, 70, 68))
WHITE = bytes((255, 255, 255))
BLACK = bytes((10, 10, 10))
SKY = bytes((135, 190, 220))
NIGHT = bytes((18, 28, 52))
SUN = bytes((240, 180, 40))
GREEN = bytes((46, 125, 60))
SEA = bytes((38, 110, 150))
SAND = bytes((222, 196, 150))
ORANGE = bytes((214, 110, 30))
BROWN = bytes((122, 82, 46))
PINK = bytes((214, 130, 150))
PURPLE = bytes((96, 64, 140))
CREAM = bytes((245, 232, 200))


def sky_band(cv, x, y, w, h, top, bot):
    """Vertical gradient sky made of flat bands (deterministic)."""
    steps = 8
    for i in range(steps):
        t = i / (steps - 1)
        c = bytes((int(top[0] + (bot[0] - top[0]) * t),
                   int(top[1] + (bot[1] - top[1]) * t),
                   int(top[2] + (bot[2] - top[2]) * t)))
        cv.rect(x, y + i * h // steps, w, h // steps + 1, c)


def buildings(cv, x, y, w, h, base, cols, seed):
    """A flat skyline of rectangles with lit windows."""
    n = 6
    bw = w // n
    for i in range(n):
        bh = h * (35 + ((seed * 37 + i * 53) % 60)) // 100
        bx = x + i * bw
        col = cols[(seed + i) % len(cols)]
        cv.rect(bx + 1, y + h - bh, bw - 2, bh, col)
        for wy in range(y + h - bh + 4, y + h - 4, 7):
            for wx in range(bx + 4, bx + bw - 4, 7):
                if (wx * 7 + wy * 13 + seed) % 5 == 0:
                    cv.rect(wx, wy, 3, 3, SUN)


def rain(cv, x, y, w, h, color, seed):
    for i in range(w // 9):
        rx = x + (i * 37 + seed * 11) % w
        ry = y + (i * 23 + seed * 7) % (h // 2)
        cv.line(rx, ry, rx - 3, ry + 9, color)


def burst(cv, cx, cy, r, c1, c2):
    """Explosion burst: spiked star + core."""
    for k in range(12):
        import math
        a = k * math.pi / 6
        x2 = cx + int(r * math.cos(a))
        y2 = cy + int(r * math.sin(a))
        cv.line(cx, cy, x2, y2, c1)
    cv.circle(cx, cy, r // 2, c2)
    cv.circle(cx, cy, r // 4, c1)


def waves(cv, x, y, w, h, c1, c2):
    cv.rect(x, y, w, h, c1)
    for i in range(4):
        yy = y + 4 + i * (h // 4)
        for xx in range(x, x + w, 16):
            cv.line(xx, yy, xx + 8, yy - 3, c2)
            cv.line(xx + 8, yy - 3, xx + 16, yy, c2)


# ------------------------------------------------------- scenes (13 panels)
# Each scene draws an original flat illustration inside (x, y, w, h).

def scene_kuwait(cv, x, y, w, h):
    sky_band(cv, x, y, w, h, NIGHT, bytes((60, 50, 90)))
    cv.circle(x + w - 26, y + 18, 10, CREAM)          # moon
    cv.rect(x + 8, y + h - 46, 14, 46, DGREY)         # refinery towers
    cv.rect(x + 26, y + h - 34, 10, 34, DGREY)
    cv.rect(x + 40, y + h - 52, 12, 52, DGREY)
    cv.rect(x + 56, y + h - 30, 18, 30, DGREY)
    cv.rect(x + 8, y + h - 58, 66, 4, DGREY)
    burst(cv, x + w // 2 + 30, y + 34, 22, ORANGE, SUN)
    burst(cv, x + w // 2 - 40, y + 52, 14, RED, ORANGE)
    cv.tri(x + w - 60, y + 20, x + w - 44, y + 20, x + w - 52, y + 6, GREY)
    cv.rect(x + w - 54, y + 20, 4, 14, GREY)          # drone
    cv.line(x + w - 66, y + 27, x + w - 38, y + 27, GREY)
    cv.rect(x, y + h - 8, w, 8, BLACK)


def scene_storm(cv, x, y, w, h):
    sky_band(cv, x, y, w, h, bytes((70, 80, 100)), bytes((140, 150, 160)))
    cv.circle(x + 40, y + 22, 16, DGREY)              # storm clouds
    cv.circle(x + 64, y + 16, 20, DGREY)
    cv.circle(x + 92, y + 24, 14, DGREY)
    cv.circle(x + w - 50, y + 20, 15, DGREY)
    cv.circle(x + w - 74, y + 14, 18, DGREY)
    rain(cv, x, y + 30, w, h - 30, bytes((200, 210, 220)), 3)
    cv.rect(x + 16, y + h - 52, 46, 36, BROWN)        # house
    cv.tri(x + 12, y + h - 52, x + 66, y + h - 52, x + 39, y + h - 70, RED)
    cv.rect(x + 34, y + h - 24, 10, 24, DGREY)
    cv.line(x + w - 60, y + h - 80, x + w - 60, y + h - 10, BLACK)  # pole
    cv.line(x + w - 60, y + h - 78, x + w - 30, y + h - 70, BLACK)
    cv.line(x + w - 60, y + h - 78, x + w - 88, y + h - 70, BLACK)
    cv.line(x + w - 88, y + h - 70, x + w - 120, y + h - 62, BLACK)
    cv.tri(x + w - 52, y + h - 78, x + w - 46, y + h - 78, x + w - 49, y + h - 66, SUN)
    cv.rect(x, y + h - 10, w, 10, bytes((60, 70, 60)))


def scene_chess(cv, x, y, w, h):
    cv.rect(x, y, w, h, CREAM)
    sq = min(w, h) // 8
    ox = x + (w - sq * 8) // 2
    oy = y + (h - sq * 8) // 2
    for r in range(8):
        for c in range(8):
            if (r + c) % 2 == 0:
                cv.rect(ox + c * sq, oy + r * sq, sq, sq, bytes((120, 90, 60)))
    # two kings facing off
    cv.rect(ox + 2 * sq + 3, oy + 1 * sq + 2, sq - 6, sq - 2, WHITE)
    cv.circle(ox + 2 * sq + sq // 2, oy + 1 * sq - 2, 4, WHITE)
    cv.rect(ox + 5 * sq + 3, oy + 6 * sq + 2, sq - 6, sq - 2, BLACK)
    cv.circle(ox + 5 * sq + sq // 2, oy + 6 * sq - 2, 4, BLACK)
    cv.rect(x, y + h - 6, w, 6, BROWN)


def scene_migration(cv, x, y, w, h):
    sky_band(cv, x, y, w, h, SKY, CREAM)
    cv.rect(x + 14, y + 16, 60, 10, WHITE)            # plane body
    cv.tri(x + 74, y + 16, x + 92, y + 21, x + 74, y + 26, WHITE)
    cv.tri(x + 30, y + 26, x + 44, y + 26, x + 30, y + 38, WHITE)
    cv.tri(x + 56, y + 16, x + 66, y + 16, x + 56, y + 6, WHITE)
    cv.circle(x + 20, y + 21, 3, BLUE)
    # falling bars chart
    base = y + h - 14
    for i, bh in enumerate((34, 28, 22, 15, 9)):
        cv.rect(x + 14 + i * 16, base - bh, 11, bh, (RED, ORANGE, GOLD, TEAL, BLUE)[i])
    cv.line(x + 8, base, x + w - 8, base, INK)
    draw_text(cv, x + w - 44, y + h - 26, "1997", 1, INK)


def scene_court(cv, x, y, w, h):
    sky_band(cv, x, y, w, h, SKY, CREAM)
    cv.rect(x + 12, y + h - 44, w - 24, 6, DGREY)     # courthouse base
    cv.tri(x + 8, y + 18, x + w - 8, y + 18, x + w // 2, y + 4, BROWN)
    for i in range(4):
        cx = x + 22 + i * (w - 44) // 3
        cv.rect(cx, y + 20, 8, h - 64, CREAM)
        cv.rect(cx - 2, y + 18, 12, 4, CREAM)
    cv.rect(x + w // 2 - 22, y + h - 44, 44, 22, BROWN)  # door
    cv.circle(x + w - 24, y + h - 22, 8, GOLD)        # gavel head
    cv.line(x + w - 30, y + h - 16, x + w - 14, y + h - 30, BROWN)
    cv.rect(x + w - 34, y + h - 12, 22, 3, GOLD)


def scene_tanker(cv, x, y, w, h):
    sky_band(cv, x, y, w, h, SKY, bytes((210, 225, 235)))
    cv.circle(x + w - 26, y + 16, 11, SUN)
    waves(cv, x, y + h // 2, w, h // 2, SEA, bytes((120, 190, 220)))
    cv.tri(x + 20, y + h // 2 - 6, x + 90, y + h // 2 - 6, x + 55, y + h // 2 + 16, RED)
    cv.rect(x + 24, y + h // 2 - 18, 62, 14, BROWN)   # capsized hull
    cv.rect(x + 40, y + h // 2 - 30, 10, 12, DGREY)
    cv.rect(x + 60, y + h // 2 - 26, 8, 8, DGREY)
    cv.circle(x + w - 40, y + h - 16, 6, WHITE)       # life ring
    cv.circle(x + w - 40, y + h - 16, 3, SEA)


def scene_gaza(cv, x, y, w, h):
    sky_band(cv, x, y, w, h, bytes((230, 200, 160)), bytes((240, 225, 200)))
    buildings(cv, x, y + 10, w, h - 10, 0, (DGREY, BROWN, GREY), 5)
    burst(cv, x + w // 2, y + 26, 16, ORANGE, SUN)
    cv.circle(x + w - 20, y + 14, 8, SUN)
    cv.rect(x, y + h - 8, w, 8, SAND)


def scene_musk(cv, x, y, w, h):
    sky_band(cv, x, y, w, h, NIGHT, bytes((40, 40, 90)))
    for sx, sy in ((12, 10), (40, 26), (70, 8), (110, 18), (150, 10), (30, 50), (130, 44)):
        cv.rect(x + sx, y + sy, 2, 2, WHITE)
    cv.tri(x + w // 2 - 8, y + 8, x + w // 2 + 8, y + 8, x + w // 2, y + 44, WHITE)
    cv.rect(x + w // 2 - 8, y + 44, 16, 22, WHITE)    # rocket
    cv.rect(x + w // 2 - 14, y + 58, 6, 12, RED)
    cv.rect(x + w // 2 + 8, y + 58, 6, 12, RED)
    cv.tri(x + w // 2 - 6, y + 66, x + w // 2 + 6, y + 66, x + w // 2, y + 84, ORANGE)
    cv.circle(x + 20, y + h - 22, 10, GOLD)           # coins
    cv.circle(x + 40, y + h - 20, 10, GOLD)
    cv.circle(x + w - 24, y + h - 22, 10, GOLD)
    draw_text(cv, x + 16, y + h - 26, "$", 1, BROWN)
    draw_text(cv, x + 36, y + h - 24, "$", 1, BROWN)
    draw_text(cv, x + w - 28, y + h - 26, "$", 1, BROWN)


def scene_nz(cv, x, y, w, h):
    sky_band(cv, x, y, w, h, SKY, CREAM)
    cv.rect(x + 14, y + h - 46, 54, 40, BLUE)         # ballot box
    cv.rect(x + 10, y + h - 52, 62, 8, BLUE)
    cv.rect(x + 32, y + h - 50, 18, 3, BLACK)
    cv.rect(x + 78, y + 14, 34, 44, WHITE)            # ballot paper
    cv.line(x + 82, y + 18, x + 108, y + 18, GREY)
    cv.line(x + 82, y + 26, x + 108, y + 26, GREY)
    cv.rect(x + 84, y + 34, 10, 10, WHITE)
    cv.line(x + 84, y + 39, x + 88, y + 44, RED)
    cv.line(x + 88, y + 44, x + 96, y + 34, RED)
    cv.rect(x + w - 30, y + h - 30, 22, 24, GREEN)    # 67 seats bar
    cv.rect(x + w - 56, y + h - 18, 22, 12, RED)
    draw_text(cv, x + 16, y + h - 44, "67", 2, WHITE)
    cv.rect(x, y + h - 6, w, 6, DGREY)


def scene_bangkok(cv, x, y, w, h):
    sky_band(cv, x, y, w, h, bytes((90, 100, 110)), bytes((170, 160, 140)))
    cv.rect(x + 10, y + h - 40, 12, 40, DGREY)        # refinery stacks
    cv.rect(x + 26, y + h - 52, 10, 52, DGREY)
    cv.rect(x + 40, y + h - 34, 16, 34, DGREY)
    cv.rect(x + 60, y + h - 30, 20, 30, BROWN)
    burst(cv, x + w // 2 + 26, y + 30, 20, ORANGE, SUN)
    burst(cv, x + w - 26, y + 52, 12, RED, ORANGE)
    cv.circle(x + 16, y + 18, 12, DGREY)              # smoke
    cv.circle(x + 30, y + 12, 14, DGREY)
    cv.circle(x + 46, y + 18, 10, DGREY)
    cv.rect(x, y + h - 8, w, 8, BLACK)


def scene_fifa(cv, x, y, w, h):
    sky_band(cv, x, y, w, h, bytes((200, 220, 235)), CREAM)
    cv.rect(x + 20, y + 14, 76, 52, DGREY)            # laptop screen
    cv.rect(x + 24, y + 18, 68, 44, bytes((20, 40, 60)))
    cv.rect(x + 12, y + 66, 92, 6, DGREY)
    cv.tri(x + 58, y + 24, x + 78, y + 54, x + 38, y + 54, SUN)  # warning
    draw_text(cv, x + 55, y + 36, "!", 2, BLACK)
    for i in range(5):                                 # binary rain
        cv.rect(x + 8 + i * 4, y + 78 + (i % 2) * 4, 2, 6, TEAL)
    cv.circle(x + w - 22, y + h - 20, 12, WHITE)
    cv.ring(x + w - 22, y + h - 20, 11, BLACK, 2)
    draw_text(cv, x + w - 26, y + h - 24, "O", 1, BLACK)


def scene_un(cv, x, y, w, h):
    sky_band(cv, x, y, w, h, bytes((120, 140, 180)), CREAM)
    for i in range(5):                                 # figures
        fx = x + 14 + i * (w - 28) // 4
        cv.circle(fx, y + 22, 7, (PINK, TEAL, PURPLE, GOLD, BLUE)[i])
        cv.rect(fx - 6, y + 30, 12, 22, (PINK, TEAL, PURPLE, GOLD, BLUE)[i])
    cv.rect(x + 10, y + h - 34, w - 20, 26, BLUE)
    draw_text(cv, x + 14, y + h - 30, "47,000", 2, WHITE)
    cv.rect(x, y + h - 8, w, 8, DGREY)


def scene_cartagena(cv, x, y, w, h):
    sky_band(cv, x, y, w, h, SKY, CREAM)
    cv.rect(x + 12, y + 22, w - 24, h - 44, ORANGE)   # supermarket
    cv.rect(x + 12, y + 22, w - 24, 12, RED)
    draw_text(cv, x + 18, y + 26, "MARKET", 1, WHITE)
    for i in range(4):
        cv.rect(x + 22 + i * (w - 60) // 3, y + 44, 16, 18, WHITE)
    cv.rect(x + w // 2 - 12, y + h - 34, 24, 20, BROWN)
    for i in range(3):                                 # crowd figures
        fx = x + 26 + i * 22
        cv.circle(fx, y + h - 22, 5, (TEAL, PURPLE, BLUE)[i])
        cv.rect(fx - 4, y + h - 16, 8, 12, (TEAL, PURPLE, BLUE)[i])
    cv.rect(x, y + h - 8, w, 8, DGREY)


SCENES = {
    'kuwait': scene_kuwait, 'storm': scene_storm, 'chess': scene_chess,
    'migration': scene_migration, 'court': scene_court, 'tanker': scene_tanker,
    'gaza': scene_gaza, 'musk': scene_musk, 'nz': scene_nz,
    'bangkok': scene_bangkok, 'fifa': scene_fifa, 'un': scene_un,
    'cartagena': scene_cartagena,
}


# ------------------------------------------------------------- world map
# Coarse equirectangular continent outlines (lon, lat) -> map pixels.
CONTINENTS = [
    # North America
    [(-168, 66), (-140, 70), (-125, 72), (-110, 68), (-95, 69), (-85, 66),
     (-80, 62), (-75, 58), (-65, 60), (-60, 52), (-55, 47), (-65, 44),
     (-70, 42), (-75, 35), (-80, 32), (-81, 26), (-84, 30), (-90, 29),
     (-97, 26), (-97, 22), (-94, 18), (-90, 14), (-86, 12), (-83, 9),
     (-90, 13), (-97, 16), (-105, 20), (-110, 23), (-114, 28), (-120, 34),
     (-125, 40), (-124, 48), (-130, 54), (-140, 60), (-155, 58), (-165, 60),
     (-168, 66)],
    # South America
    [(-79, 9), (-72, 12), (-62, 10), (-52, 5), (-50, 0), (-44, -3),
     (-35, -8), (-40, -20), (-48, -28), (-52, -33), (-58, -38), (-65, -41),
     (-68, -50), (-70, -54), (-73, -44), (-73, -30), (-70, -18), (-77, -12),
     (-81, -5), (-80, 1), (-79, 9)],
    # Europe
    [(-10, 36), (-9, 43), (-2, 48), (-4, 50), (0, 51), (3, 53), (8, 57),
     (10, 59), (5, 60), (10, 62), (18, 69), (25, 71), (31, 70), (40, 68),
     (45, 66), (40, 60), (35, 55), (30, 60), (28, 55), (23, 58), (20, 54),
     (18, 55), (12, 54), (8, 57), (3, 53), (-2, 50), (-5, 44), (-9, 38),
     (-10, 36)],
    # Africa
    [(-6, 35), (10, 37), (11, 34), (20, 32), (30, 31), (32, 31), (35, 28),
     (39, 21), (43, 12), (51, 11), (48, 2), (41, -2), (40, -10), (36, -18),
     (33, -26), (27, -33), (19, -35), (15, -27), (12, -18), (13, -10),
     (9, -1), (9, 4), (4, 6), (-8, 5), (-13, 8), (-17, 15), (-16, 20),
     (-15, 27), (-10, 31), (-6, 35)],
    # Asia
    [(40, 68), (50, 69), (60, 69), (70, 72), (80, 73), (90, 75), (100, 77),
     (110, 76), (120, 73), (130, 72), (140, 72), (150, 70), (160, 69),
     (170, 67), (178, 65), (170, 60), (162, 56), (158, 52), (150, 59),
     (142, 54), (140, 45), (135, 43), (130, 38), (127, 35), (122, 32),
     (120, 25), (115, 22), (109, 18), (105, 10), (103, 8), (100, 6),
     (98, 10), (95, 16), (92, 21), (89, 22), (86, 20), (80, 15), (77, 8),
     (75, 12), (72, 20), (68, 23), (62, 25), (57, 26), (52, 28), (50, 30),
     (48, 30), (44, 29), (40, 30), (36, 36), (30, 36), (27, 40), (23, 40),
     (26, 45), (28, 45), (30, 46), (32, 50), (35, 55), (38, 60), (40, 68)],
    # Australia
    [(113, -22), (114, -30), (115, -35), (124, -33), (130, -32), (136, -35),
     (140, -38), (146, -39), (150, -37), (153, -32), (153, -27), (150, -22),
     (146, -19), (142, -15), (142, -11), (137, -12), (135, -15), (132, -12),
     (130, -13), (126, -14), (122, -17), (118, -20), (113, -22)],
]


def lonlat_to_xy(lon, lat, x, y, w, h):
    px = x + int((lon + 180) / 360 * w)
    py = y + int((90 - lat) / 180 * h)
    return px, py


def draw_map(cv, x, y, w, h):
    cv.rect(x, y, w, h, bytes((24, 60, 96)))
    for cont in CONTINENTS:
        pts = [lonlat_to_xy(lon, lat, x, y, w, h) for lon, lat in cont]
        cv.poly(pts, bytes((120, 170, 120)))
    # graticule
    for gx in range(x + w // 6, x + w, w // 6):
        cv.vline(gx, y, h, bytes((40, 80, 120)))
    for gy in range(y + h // 4, y + h, h // 4):
        cv.hline(x, gy, w, bytes((40, 80, 120)))


# ------------------------------------------------------------------- stories
# (headline, body, tag, scene) — all verified 27 Nov 2026, see stories.md.

HEROES = [
    ("DRONE STRIKE KILLS TWO ITALIANS IN KUWAIT",
     "A drone hit a site in Kuwait overnight, killing two Italian workers. "
     "Iran denies any role as Kuwait and Rome demand answers.",
     "CONFIRMED - BBC, NYT", "kuwait"),
    ("THANKSGIVING STORM CUTS POWER TO 800,000",
     "A fierce coastal storm lashed the US East Coast on Thanksgiving: "
     "800,000 customers in the dark and 1,000+ flights cancelled or delayed.",
     "CONFIRMED - BBC", "storm"),
    ("GUKESH AND SINDAROV DRAW MARATHON GAME 3",
     "The World Championship match stays level after a marathon third game "
     "in which Gukesh held an advantage for 43 moves.",
     "CONFIRMED - INDIA TODAY", "chess"),
]

MEDIUMS = [
    ("UK MIGRATION LOWEST SINCE 1997",
     "Net migration at its lowest since 1997, pandemic aside.",
     "CONFIRMED - NYT", "migration"),
    ("DEPARDIEU TO STAND TRIAL FOR RAPE",
     "Court orders trial over alleged rape of actress in 2018.",
     "CONFIRMED - BBC", "court"),
    ("TANKER CAPSIZES OFF IBIZA, ONE DEAD",
     "Diesel tanker carrying 7,000 tonnes capsizes; one dead.",
     "CONFIRMED - BBC", "tanker"),
    ("HAMAS WEIGHS REPLY AS ISRAEL KILLS 10",
     "Hamas weighs its reply after Israeli strikes kill 10.",
     "CONFIRMED - REUTERS", "gaza"),
    ("MUSK: TWO SPACEX SHARES PER US CHILD",
     "Elon Musk says every US child will get two SpaceX shares.",
     "REPORTED", "musk"),
    ("NZ FINAL COUNT: COALITION HOLDS ON",
     "Final results give the coalition 67 of 131 seats.",
     "CONFIRMED - NZH", "nz"),
    ("BANGKOK REFINERY BLAST INJURES NINE",
     "Nine hurt, three critically, in Bangkok refinery blast.",
     "CONFIRMED - BBC", "bangkok"),
    ("FIFA CONFIRMS CYBERATTACK",
     "Hackers accessed personal and business information.",
     "REPORTED", "fifa"),
    ("47,000 WOMEN KILLED BY RELATIVES",
     "Over 47,000 women killed by relatives in 2025, UN says.",
     "OFFICIAL - UN", "un"),
    ("GUNMEN SEIZE CARTAGENA SUPERMARKET",
     "Armed men seize a supermarket, taking dozens hostage.",
     "REPORTED", "cartagena"),
]

# Numbered remainder, stories 14-48 (one line each).
REST = [
    "USA - TRUMP TELLS PUTIN TO PULL BACK IN EUROPE",
    "VATICAN - POPE'S DIARIES TELL OF DEVIL VISIONS",
    "EUROPE - SCHOOL BOMB THREATS IN GERMANY, DENMARK",
    "IRAN - SINGER GETS 74 LASHES FOR SINGING UNVEILED",
    "EGYPT - DRIVER HELD OVER CAIRO TANKER FIRE, 31 DEAD",
    "LIBYA - UKRAINE 'HIT RUSSIAN SHIP' OFF BENGHAZI",
    "ESTONIA - RUSSIA ALLEGES 'HOSTILE ACTIONS'",
    "CHINA - OFFICIAL SENTENCED TO DEATH FOR SPYING",
    "NORTH KOREA - KIM INSPECTS NUCLEAR SITES",
    "INDIA - TOP COURT ON JUDGE ROLE IN PMLA CASES",
    "INDIA - COURT QUASHES RELEASE OF EX-MP ANAND MOHAN",
    "INDIA - CABINET BACKS RS 11,000 CRORE PLAN",
    "INDIA - GST CANCELLATIONS AUTOMATIC FROM 1 DEC",
    "BANGLADESH - SPEAKER ON INDIA AND 1971 WAR",
    "SOLOMON IS. - CHINA PACT MAY YIELD TO AUSTRALIA",
    "NEW ZEALAND - SECOND TEST V INDIA BEGINS",
    "NEW ZEALAND - BARRETT TO CAPTAIN ALL BLACKS",
    "AUSTRALIA - KIBORI TIED SECOND AT AUSTRALIAN PGA",
    "UK - TRAIN KNIFEMAN GUILTY OF TRYING TO MURDER 14",
    "USA - PREGNANT INMATE ESCAPES IN PRISON VEHICLE",
    "USA - MAN AND DOG ESCAPE KING TIDE IN OREGON",
    "USA - PLANES AIRDROP THANKSGIVING TURKEYS TO ALASKA",
    "USA - FIREBALL AT INDIANA DRONE DISPLAY",
    "USA - TRUMP ALLEGES 'FAKE' GDP FIGURES",
    "GAZA - STRIKE KILLS HAMAS OFFICIAL AND FAMILY",
    "EUROPE - EU LEADERS MEET IN BRUSSELS, DAY TWO",
    "SPAIN - ELECTION COULD TOPPLE A LEFT-WING HOLDOUT",
    "MOTORSPORT - FERRARI SETS HAMILTON, LECLERC TARGET",
    "FOOTBALL - BOURNEMOUTH FANS BOOK EUROPA HOTELS",
    "FRANCE - MAINSTREAM RISKS PRESIDENTIAL VOTE DEBACLE",
    "AFRICA - CHEAPER HIV JAB REACHES MILLIONS",
    "UK - RESERVISTS CONTACTED AS THREAT LEVEL RISES",
    "MYANMAR - REFUSES PARTS OF ICJ GENOCIDE RULING",
    "IRAN - DEATH-ROW WOMEN APPEAL AFTER PROTESTS",
    "CULTURE - GUITAR WARS OVER THE STRATOCASTER",
]

UTC_STRIP = [
    ("02:05", "KUWAIT", "DRONE STRIKE KILLS TWO ITALIANS"),
    ("02:11", "PARIS", "DEPARDIEU TO STAND TRIAL"),
    ("03:31", "IBIZA", "TANKER CAPSIZES, ONE DEAD"),
    ("04:00", "WELLINGTON", "FINAL COUNT: COALITION 67/131"),
    ("06:00", "BANGKOK", "REFINERY BLAST INJURES NINE"),
    ("09:30", "LONDON", "MIGRATION LOWEST SINCE 1997"),
    ("16:00", "CARTAGENA", "GUNMEN SEIZE SUPERMARKET"),
]

NUMBERS = [
    ("2", "ITALIANS KILLED IN KUWAIT STRIKE"),
    ("800,000", "US CUSTOMERS WITHOUT POWER"),
    ("1,000+", "US FLIGHTS CANCELLED OR DELAYED"),
    ("47,000", "WOMEN KILLED BY RELATIVES IN 2025"),
    ("67/131", "NZ COALITION SEATS AFTER FINAL COUNT"),
    ("74", "LASHES FOR IRANIAN SINGER AHMADI"),
]

REGIONS = [
    ("EUROPE", 10), ("MIDDLE EAST", 5), ("AMERICAS", 9), ("ASIA", 11),
    ("AFRICA", 3), ("OCEANIA", 5), ("WORLD", 5),
]

# (lon, lat, pin number) for the 12 featured stories with a place.
# Europe pins are nudged a few degrees apart so the numbered dots do not
# pile on one another at this scale.
PINS = [
    (47.5, 29.3, "1"), (-74.0, 40.7, "2"), (-8.0, 56.0, "3"),
    (-2.0, 50.0, "4"), (2.8, 38.9, "5"), (34.5, 31.5, "6"),
    (-77.0, 38.9, "7"), (174.8, -41.3, "8"), (100.5, 13.75, "9"),
    (13.0, 52.0, "10"), (6.0, 43.0, "11"), (-75.5, 10.4, "12"),
]

DATE_CHECK = [
    "MACY'S PARADE POSTPONED (25 NOV) - JAZAN REFINERY HIT (26 NOV) - FCC CLEARS SPACEX 1M SATELLITES (25 NOV)",
    "ECB BACKS DE COS (26 NOV) - DR CONGO EBOLA 12,000 CASES (26 NOV) - SUDAN BLUE NILE STRIKES (24 NOV)",
    "THANKSGIVING DAY ITSELF (26 NOV) - SHENZHOU-24 DOCKED 25 NOV - TAI PO FIRE WAS 26 NOV 2025",
    "NOT YET: RESCHEDULED MACY'S PARADE RUNS SAT 28 NOV",
]


def panel_border(cv, x, y, w, h):
    cv.rect(x, y, w, 2, INK)
    cv.rect(x, y + h - 2, w, 2, INK)
    cv.rect(x, y, 2, h, INK)
    cv.rect(x + w - 2, y, 2, h, INK)


def build_page():
    assert len(HEROES) + len(MEDIUMS) + len(REST) == 48
    assert sum(n for _, n in REGIONS) == 48
    cv = Canvas(W, H, PAPER)
    # top rules
    cv.rect(0, 0, W, 4, INK)
    cv.rect(0, 6, W, 2, RED)

    # masthead
    title = "FRIDAY 27 NOVEMBER 2026"
    draw_text(cv, (W - text_w(title, 6)) // 2, 12, title, 6, INK)
    sub = "THE WORLD IN ONE PAGE"
    draw_text(cv, (W - text_w(sub, 2)) // 2, 58, sub, 2, RED)
    count = "48 STORIES - 6 REGIONS + WORLD - 14 FIELDS - ALL FROM THIS FRIDAY"
    draw_text(cv, (W - text_w(count, 2)) // 2, 78, count, 2, INK)
    cv.rect(8, 96, W - 16, 2, INK)

    # THE DAY IN UTC strip
    draw_text(cv, 12, 102, "THE DAY IN UTC", 1, RED)
    for i, (t, place, txt) in enumerate(UTC_STRIP):
        x = 10 + i * 144
        draw_text(cv, x, 114, t, 1, RED)
        draw_text(cv, x, 124, place, 1, INK)
        draw_para(cv, x, 134, txt, 1, DGREY, 22, line_h=9)

    # THE DAY IN NUMBERS strip
    draw_text(cv, 12, 164, "THE DAY IN NUMBERS", 1, RED)
    for i, (num, label) in enumerate(NUMBERS):
        x = 12 + i * 169
        draw_text(cv, x, 176, num, 3, INK)
        draw_para(cv, x, 199, label, 1, DGREY, 26, line_h=9)
    cv.rect(8, 220, W - 16, 2, INK)

    # 3 hero panels
    for i, (head, body, tag, scene) in enumerate(HEROES):
        x = 8 + i * 340
        y = 228
        panel_border(cv, x, y, 328, 212)
        SCENES[scene](cv, x + 3, y + 3, 322, 116)
        draw_para(cv, x + 10, y + 126, head, 2, INK, 26, line_h=16)
        draw_para(cv, x + 10, y + 162, body, 1, DGREY, 50, line_h=9)
        draw_text(cv, x + 10, y + 196, tag, 1, RED)

    # 10 medium panels, two rows of five
    for i, (head, body, tag, scene) in enumerate(MEDIUMS):
        col = i % 5
        row = i // 5
        x = 8 + col * 204
        y = 448 + row * 106
        panel_border(cv, x, y, 198, 100)
        SCENES[scene](cv, x + 3, y + 3, 192, 48)
        draw_para(cv, x + 6, y + 55, head, 1, INK, 31, line_h=9)
        draw_para(cv, x + 6, y + 74, body, 1, DGREY, 31, line_h=9)
        draw_text(cv, x + 6, y + 90, tag, 1, RED)

    # WHERE IT HAPPENED map + region counts
    draw_text(cv, 12, 668, "WHERE IT HAPPENED - PINS: THE 12 FEATURED STORIES WITH A PLACE", 1, RED)
    draw_map(cv, 8, 682, 700, 124)
    for lon, lat, num in PINS:
        px, py = lonlat_to_xy(lon, lat, 8, 682, 700, 124)
        cv.circle(px, py, 8, RED)
        cv.ring(px, py, 8, WHITE, 1)
        draw_text(cv, px - 3, py - 3, num, 1, WHITE)
    cv.rect(716, 682, 300, 124, LGREY)
    draw_text(cv, 728, 690, "STORIES BY REGION", 1, INK)
    for i, (name, n) in enumerate(REGIONS):
        yy = 704 + i * 13
        draw_text(cv, 728, yy, name, 1, DGREY)
        draw_text(cv, 960, yy, str(n), 1, INK)
    draw_text(cv, 728, 792, "TOTAL 48", 1, RED)

    # numbered list of the rest
    draw_text(cv, 12, 816, "THE REST OF THE DAY - STORIES 14 TO 48", 1, RED)
    for i, item in enumerate(REST):
        col = i // 12
        row = i % 12
        x = 12 + col * 336
        y = 830 + row * 11
        draw_text(cv, x, y, "%d. %s" % (14 + i, item), 1, INK)

    # DATE CHECK box
    cv.rect(8, 962, W - 16, 2, RED)
    draw_text(cv, 12, 968, "DATE CHECK - LEFT OUT ON PURPOSE", 1, RED)
    yy = 978
    for line in DATE_CHECK:
        draw_text(cv, 12, yy, line, 1, DGREY)
        yy += 8
    # footer
    draw_text(cv, 12, 1012, "SOURCES: BBC - REUTERS - NYT - AP - INDIA TODAY - NDTV - MINT - NEWSTALK ZB - TAGS: CONFIRMED 2+ OUTLETS, OFFICIAL ON RECORD, REPORTED ONE OUTLET", 1, GREY)
    cv.rect(0, H - 4, W, 4, INK)
    return cv


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    cv = build_page()
    data = png_bytes(cv.px, W, H)
    path = os.path.join(out_dir, "entry.png")
    with open(path, "wb") as f:
        f.write(data)
    import hashlib
    print("wrote %s (%d bytes, sha256 %s)" % (path, len(data),
          hashlib.sha256(data).hexdigest()))
    print("stories: %d (heroes %d, mediums %d, list %d)"
          % (len(HEROES) + len(MEDIUMS) + len(REST),
             len(HEROES), len(MEDIUMS), len(REST)))


if __name__ == "__main__":
    main()
