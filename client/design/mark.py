"""The mark: a quaver whose flag curls into a question mark. Who? When?

Engraving proportions: a heavy oval head, a thin stem, and a flag that swells
over the top of its loop and tapers to a point at the tip. Prints the SVG
fragment for one weight. Regenerate rather than nudge points:

    python3 client/design/mark.py        # regular: client/components/Logo.tsx
    python3 client/design/mark.py 1.2    # heavier: client/app/icon.svg

The centreline runs from the stem top through a short S into the loop, then
round the loop to the tip. The width along it follows FLAG_KEYS; the stem is a
thin rounded bar; the head is an ellipse whose right edge meets the stem's.
"""
import math
import sys
from itertools import pairwise

HEAD = dict(cx=24.8, cy=51.0, rx=10.2, ry=7.0, rot=-22)
STEM_X, STEM_W, STEM_TOP, STEM_BOTTOM = 32.8, 3.4, 29.5, 50.0
LOOP_C, LOOP_R = (33.8, 19.5), 11.2
JOIN_DEG, TIP_DEG = 55, 145  # positions on the loop circle, screen angles
FLAG_KEYS = [(0.0, 3.4), (0.14, 3.7), (0.34, 6.6), (0.52, 7.8), (0.72, 6.0), (0.9, 2.8), (1.0, 0.5)]


def arc(cx, cy, r, a0, a1, n):
    for i in range(n + 1):
        a = math.radians(a0 + (a1 - a0) * i / n)
        yield (cx + r * math.cos(a), cy + r * math.sin(a))


def cubic(p0, p1, p2, p3, n):
    for i in range(1, n + 1):
        t = i / n
        u = 1 - t
        yield (
            u**3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t**3 * p3[0],
            u**3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t**3 * p3[1],
        )


def ease(t, keys):
    for (t0, w0), (t1, w1) in pairwise(keys):
        if t0 <= t <= t1:
            f = (t - t0) / (t1 - t0)
            f = (1 - math.cos(math.pi * f)) / 2
            return w0 + (w1 - w0) * f
    return keys[-1][1]


def centreline():
    cx, cy = LOOP_C
    a = math.radians(JOIN_DEG)
    join = (cx + LOOP_R * math.cos(a), cy + LOOP_R * math.sin(a))
    tx, ty = math.sin(a), -math.cos(a)  # along the loop at the join, heading up-right
    p0 = (STEM_X, STEM_TOP)
    handle_in, handle_out = (STEM_X, STEM_TOP - 4.6), (join[0] - 4.6 * tx, join[1] - 4.6 * ty)
    pts = [p0, *cubic(p0, handle_in, handle_out, join, 18)]
    pts += list(arc(cx, cy, LOOP_R, JOIN_DEG, TIP_DEG - 360, 90))[1:]
    return pts


def outline(pts, keys, scale):
    seg = [0.0]
    for (x0, y0), (x1, y1) in pairwise(pts):
        seg.append(seg[-1] + math.hypot(x1 - x0, y1 - y0))
    total = seg[-1]
    left, right = [], []
    for i, (x, y) in enumerate(pts):
        xa, ya = pts[max(i - 1, 0)]
        xb, yb = pts[min(i + 1, len(pts) - 1)]
        tx, ty = xb - xa, yb - ya
        length = math.hypot(tx, ty) or 1.0
        nx, ny = -ty / length, tx / length
        w = ease(seg[i] / total, keys) * scale / 2
        left.append(((x + nx * w, y + ny * w), (tx / length, ty / length)))
        right.append(((x - nx * w, y - ny * w), (tx / length, ty / length)))
    poly = _forward_only(left) + _forward_only(right)[::-1]
    return "M" + " L".join(f"{x:.2f} {y:.2f}" for x, y in poly) + " Z"


def _forward_only(side):
    """Drop the points where an offset edge folds back on itself.

    On the inside of a tight bend an offset wider than the bend's radius runs
    backwards for a few samples; filled, that fold reads as a notch. Keep a
    point only if it advances along the centreline from the last kept one.
    """
    kept = [side[0][0]]
    for (pt, tangent) in side[1:]:
        dx, dy = pt[0] - kept[-1][0], pt[1] - kept[-1][1]
        if dx * tangent[0] + dy * tangent[1] > 0:
            kept.append(pt)
    return kept


def fragment(weight=1.0):
    flag = f'<path d="{outline(centreline(), FLAG_KEYS, weight)}"/>'
    w = STEM_W * weight
    stem = (
        f'<rect x="{STEM_X - w / 2:.2f}" y="{STEM_TOP - 0.6:.2f}" width="{w:.2f}" '
        f'height="{STEM_BOTTOM - STEM_TOP + 0.6:.2f}" rx="{w / 2:.2f}"/>'
    )
    h = HEAD
    head = (
        f'<ellipse cx="{h["cx"]}" cy="{h["cy"]}" rx="{h["rx"]}" ry="{h["ry"]}" '
        f'transform="rotate({h["rot"]} {h["cx"]} {h["cy"]})"/>'
    )
    return "\n".join((flag, stem, head))


if __name__ == "__main__":
    print(fragment(float(sys.argv[1]) if len(sys.argv) > 1 else 1.0))
