"""The mark: a quaver whose flag curls into a question mark. Who? When?

Prints the SVG fragment for one weight of the mark, as a filled outline with a
pen-like thick and thin. Regenerate rather than nudge points:

    python3 client/design/mark.py        # regular: client/components/Logo.tsx
    python3 client/design/mark.py 1.2    # heavy:   client/app/icon.svg

The centreline is a question-mark loop (an arc), a short cubic into a vertical
stem, and the stem down into the note head. The width follows a pen: thin at
the entry, fullest over the top of the loop, lighter on the inside, even down
the stem. The head is an ellipse whose right edge meets the stem's right edge.
"""
import math, sys

def arc_points(cx, cy, r, a0, a1, n):
    for i in range(n + 1):
        a = math.radians(a0 + (a1 - a0) * i / n)
        yield (cx + r * math.cos(a), cy + r * math.sin(a))

def cubic_points(p0, p1, p2, p3, n):
    for i in range(1, n + 1):
        t = i / n; u = 1 - t
        x = u**3*p0[0] + 3*u*u*t*p1[0] + 3*u*t*t*p2[0] + t**3*p3[0]
        y = u**3*p0[1] + 3*u*u*t*p1[1] + 3*u*t*t*p2[1] + t**3*p3[1]
        yield (x, y)

def width_at(t, keys):
    # keys: list of (t, width); cosine-eased interpolation
    for (t0, w0), (t1, w1) in zip(keys, keys[1:]):
        if t0 <= t <= t1:
            f = (t - t0) / (t1 - t0)
            f = (1 - math.cos(math.pi * f)) / 2
            return w0 + (w1 - w0) * f
    return keys[-1][1]

def build(scale_w=1.0, cx=32.2, cy=19.5, r=10.2, stem_x=34.4, stem_bottom=48.0):
    pts = []
    # loop: from the left (165 deg) clockwise over the top to lower right (60 deg)
    pts += list(arc_points(cx, cy, r, 165, 420, 60))
    p0 = pts[-1]
    # tangent at the arc end for increasing angle: (-sin a, cos a)
    a = math.radians(420)
    tx, ty = -math.sin(a), math.cos(a)
    p1 = (p0[0] + 5.0 * tx, p0[1] + 5.0 * ty)
    p3 = (stem_x, 39.5)
    p2 = (stem_x, 34.5)
    pts += list(cubic_points(p0, p1, p2, p3, 16))
    pts += [(stem_x, 39.5 + (stem_bottom - 39.5) * i / 10) for i in range(1, 11)]
    # arc lengths for t
    seg = [0.0]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        seg.append(seg[-1] + math.hypot(x1 - x0, y1 - y0))
    total = seg[-1]
    keys = [(0.0, 5.2), (0.2, 6.6), (0.4, 7.2), (0.6, 5.9), (0.74, 6.2), (1.0, 6.2)]
    left, right = [], []
    for i, (x, y) in enumerate(pts):
        # tangent by central difference
        xa, ya = pts[max(i - 1, 0)]; xb, yb = pts[min(i + 1, len(pts) - 1)]
        tx, ty = xb - xa, yb - ya
        L = math.hypot(tx, ty) or 1.0
        nx, ny = -ty / L, tx / L
        w = width_at(seg[i] / total, keys) * scale_w / 2
        left.append((x + nx * w, y + ny * w))
        right.append((x - nx * w, y - ny * w))
    outline = left + right[::-1]
    d = "M" + " L".join(f"{x:.2f} {y:.2f}" for x, y in outline) + " Z"
    start = pts[0]; w0 = width_at(0, keys) * scale_w / 2
    return d, start, w0

if __name__ == "__main__":
    scale_w = float(sys.argv[1]) if len(sys.argv) > 1 else 1.0
    d, (sx, sy), w0 = build(scale_w)
    print(f'<path d="{d}"/>')
    print('<ellipse cx="28" cy="52" rx="10" ry="7.1" transform="rotate(-25 28 52)"/>')
