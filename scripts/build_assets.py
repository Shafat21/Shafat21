"""Generate the animated README banners in assets/.

GitHub READMEs can't run JS/WebGL, so these are SMIL-animated SVG ports of
three React effects: GradientASCII (glyph field), TrueFocus (word focus cycle)
and AeroShards (glass shards flowing along a ribbon).

Run: python scripts/build_assets.py
"""
import math
import random
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "assets"
W = 1200
ARCH_A, ARCH_B = -0.24, 0.3  # header horizon curve: y = A - B*x^2
BG = "#0b0d17"
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"


def lerp_hex(a, b, k):
    ca = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    cb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * k):02x}" for x, y in zip(ca, cb))


def ramp(colors, t):
    x = min(max(t, 0), 1) * (len(colors) - 1)
    i = min(int(x), len(colors) - 2)
    return lerp_hex(colors[i], colors[i + 1], x - i)


def loop_keys(points, total):
    """(time, value) points on a looping timeline -> SMIL keyTimes/values."""
    pts = sorted(points)
    return ";".join(f"{t / total:.4f}" for t, _ in pts), ";".join(str(v) for _, v in pts)


# ---------------------------------------------------------------- header

def header():
    H, CW, CH = 320, 12, 20
    cols, rows = W // CW, H // CH
    chars = " =+xX0S8#@"
    colors = ["#1e3fd8", "#38bdf8", "#a5d8ff", "#f6f8ff"]
    rnd = random.Random(21)
    aspect = W / H

    def intensity(cx, cy):
        u, v = (cx + 0.5) / cols, (cy + 0.5) / rows
        x = (u - 0.5) * 2
        y = 0.5 - v
        arch = ARCH_A - ARCH_B * x * x
        edge = y - arch + 0.03 * math.sin(u * 13 + v * 7) * math.cos(u * 5 - v * 11)
        t = math.exp(-((edge / 0.09) ** 2)) * (0.55 + 0.45 * math.exp(-x * x * 1.5))
        if edge > 0:
            t += 0.45 * math.exp(-edge / 0.35) * (0.6 + 0.4 * math.exp(-x * x))
        # keep the title area calm
        px, py = (u - 0.5) * W, v * H - 150
        hole = math.exp(-((px / 470) ** 4) - ((py / 85) ** 4))
        return min(max(t * (1 - 0.8 * hole), 0), 1)

    # gradient underlay: the soft field GradientASCII draws beneath its glyphs
    rim = " ".join(f"{u * W:.0f},{H * (0.5 - (ARCH_A - ARCH_B * (u * 2 - 1) ** 2)):.1f}" for u in [i / 40 for i in range(41)])
    under = (f'<ellipse cx="{W / 2}" cy="{H + 40}" rx="{W * 0.7:g}" ry="190" fill="url(#sky)"/>'
             f'<polyline points="{rim}" fill="none" stroke="#38bdf8" stroke-width="26" stroke-opacity="0.35" filter="url(#soft)"/>'
             f'<polyline points="{rim}" fill="none" stroke="#a5d8ff" stroke-width="4" stroke-opacity="0.5" filter="url(#soft2)"/>')

    out = []
    flicker_cells = []
    for cy in range(rows):
        buckets = {}
        for cx in range(cols):
            t = intensity(cx, cy)
            if t < 0.06 or rnd.random() > 0.85 * (0.45 + 0.55 * (0.3 + t * 1.1)):
                continue
            tone = min(max(t ** 0.75 + (rnd.random() - 0.5) * 0.12, 0), 1)
            ch = chars[max(1, round(tone * (len(chars) - 1)))]
            if t > 0.2 and rnd.random() < 0.05:
                flicker_cells.append((cx, cy, t))
                continue
            b = min(7, int(t * 8))
            buckets.setdefault(b, []).append((cx * CW + CW / 2, ch))
        delay = 0.15 + (rows - 1 - cy) * 0.06
        out.append(f'<g opacity="0"><animate attributeName="opacity" from="0" to="1" begin="{delay:.2f}s" dur="0.5s" fill="freeze"/>')
        for b, glyphs in sorted(buckets.items()):
            k = (b + 0.5) / 8
            xs = " ".join(f"{x:g}" for x, _ in glyphs)
            text = "".join(c for _, c in glyphs)
            out.append(f'<text x="{xs}" y="{cy * CH + 15}" fill="{ramp(colors, k ** 1.6)}" fill-opacity="{0.3 + 0.7 * k:.2f}">{text}</text>')
        out.append("</g>")

    # decode flicker: glyph pairs swapping, like the scramble in GradientASCII
    flick = []
    for cx, cy, t in flicker_cells:
        a, b = rnd.sample(chars[2:], 2)
        dur, begin = 0.4 + rnd.random() * 1.2, 1.4 + rnd.random() * 2
        col = ramp(colors, t)
        x, y = cx * CW + CW / 2, cy * CH + 15
        flick.append(f'<text x="{x:g}" y="{y}" fill="{col}">{a}<animate attributeName="opacity" values="1;0" calcMode="discrete" dur="{dur:.2f}s" begin="{begin:.2f}s" repeatCount="indefinite"/></text>')
        flick.append(f'<text x="{x:g}" y="{y}" fill="{col}" opacity="0">{b}<animate attributeName="opacity" values="0;1" calcMode="discrete" dur="{dur:.2f}s" begin="{begin:.2f}s" repeatCount="indefinite"/></text>')

    # TrueFocus: one word sharp at a time, brackets glide between words
    words = ["Agentic", "Engineer", "Full-Stack", "Developer"]
    fs, gap, frame_gap, size, bw = 32, 28, 10, 16, 3
    anim, pause = 0.5, 1.0
    step = anim + pause
    total = step * len(words)
    widths = [0.6 * fs * len(w) for w in words]
    x = (W - sum(widths) - gap * (len(words) - 1)) / 2
    base = 205
    rects = []
    for w in widths:
        rects.append((x, base - fs * 0.8, w, fs * 1.05))
        x += w + gap

    focus = ['<g font-family="{}" font-size="{}" font-weight="800" fill="#e6ecff">'.format(MONO, fs)]
    defs = []
    for i, (word, (rx, ry, rw, rh)) in enumerate(zip(words, rects)):
        t0 = i * step
        # blur 5 -> 0 over anim, hold, back to 5 while the next word sharpens
        raw = [(t0, 5), (t0 + anim, 0), (t0 + step, 0), (t0 + step + anim, 5)]
        pts = {}
        for t, v in raw:
            pts[round(t % total, 4) if t >= total else t] = v
        if t0 + step + anim > total:  # wrapped word: also pin the loop start
            pts[0.0] = 0
            pts[total] = 0
        else:
            pts.setdefault(0.0, 5)
            pts.setdefault(total, 5)
        kt, blur = loop_keys(pts.items(), total)
        _, opac = loop_keys(((t, 1 if v == 0 else 0.65) for t, v in pts.items()), total)
        defs.append(f'<filter id="f{i}" x="-20%" y="-60%" width="140%" height="220%"><feGaussianBlur stdDeviation="5"><animate attributeName="stdDeviation" keyTimes="{kt}" values="{blur}" dur="{total}s" repeatCount="indefinite"/></feGaussianBlur></filter>')
        focus.append(f'<text x="{rx:g}" y="{base}" textLength="{rw:g}" lengthAdjust="spacingAndGlyphs" filter="url(#f{i})">{word}<animate attributeName="opacity" keyTimes="{kt}" values="{opac}" dur="{total}s" repeatCount="indefinite"/></text>')
    focus.append("</g>")

    corners = {
        "tl": (f"M{bw / 2},{size} V{bw / 2} H{size}", lambda r: (r[0] - frame_gap, r[1] - frame_gap)),
        "tr": (f"M0,{bw / 2} H{size - bw / 2} V{size}", lambda r: (r[0] + r[2] + frame_gap - size, r[1] - frame_gap)),
        "bl": (f"M{bw / 2},0 V{size - bw / 2} H{size}", lambda r: (r[0] - frame_gap, r[1] + r[3] + frame_gap - size)),
        "br": (f"M0,{size - bw / 2} H{size - bw / 2} V0", lambda r: (r[0] + r[2] + frame_gap - size, r[1] + r[3] + frame_gap - size)),
    }
    times, which = [0.0], [len(words) - 1]
    for i in range(len(words)):
        times += [i * step + anim, (i + 1) * step]
        which += [i, i]
    kt = ";".join(f"{t / total:.4f}" for t in times)
    splines = ";".join("0.65 0 0.35 1" if k % 2 == 0 else "0 0 1 1" for k in range(len(times) - 1))
    brackets = ['<g fill="none" stroke="#7aa2f7" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" filter="url(#glow)">']
    for path, at in corners.values():
        vals = ";".join("{:g} {:g}".format(*at(rects[w])) for w in which)
        first = "{:g},{:g}".format(*at(rects[which[0]]))
        brackets.append(f'<path d="{path}" transform="translate({first})"><animateTransform attributeName="transform" type="translate" keyTimes="{kt}" values="{vals}" calcMode="spline" keySplines="{splines}" dur="{total}s" repeatCount="indefinite"/></path>')
    brackets.append("</g>")

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Hey, I'm Shafat. Agentic Engineer, Full-Stack Developer.">
<title>Hey, I'm Shafat. Agentic Engineer, Full-Stack Developer.</title>
<defs>
<clipPath id="card"><rect width="{W}" height="{H}" rx="18"/></clipPath>
<linearGradient id="band" gradientUnits="userSpaceOnUse" x1="-1200" y1="0" x2="0" y2="0">
<stop offset="0" stop-color="#fff" stop-opacity="0.6"/><stop offset="0.42" stop-color="#fff" stop-opacity="0.6"/><stop offset="0.5" stop-color="#fff" stop-opacity="1"/><stop offset="0.58" stop-color="#fff" stop-opacity="0.6"/><stop offset="1" stop-color="#fff" stop-opacity="0.6"/>
<animate attributeName="x1" values="-1200;1200" dur="7s" repeatCount="indefinite"/><animate attributeName="x2" values="0;2400" dur="7s" repeatCount="indefinite"/>
</linearGradient>
<mask id="sweep" maskUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{H}"><rect width="{W}" height="{H}" fill="url(#band)"/></mask>
<radialGradient id="sky"><stop offset="0" stop-color="#1e3fd8" stop-opacity="0.55"/><stop offset="0.6" stop-color="#1e3fd8" stop-opacity="0.18"/><stop offset="1" stop-color="#1e3fd8" stop-opacity="0"/></radialGradient>
<filter id="soft" x="-10%" y="-100%" width="120%" height="300%"><feGaussianBlur stdDeviation="18"/></filter>
<filter id="soft2" x="-10%" y="-100%" width="120%" height="300%"><feGaussianBlur stdDeviation="3"/></filter>
<filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="2.5" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
{chr(10).join(defs)}
</defs>
<g clip-path="url(#card)">
<rect width="{W}" height="{H}" fill="{BG}"/>
<g opacity="0">{under}<animate attributeName="opacity" from="0" to="1" begin="0.2s" dur="1.6s" fill="freeze"/></g>
<g font-family="{MONO}" font-size="16" text-anchor="middle" mask="url(#sweep)">
{chr(10).join(out)}
<g opacity="0"><animate attributeName="opacity" from="0" to="1" begin="1.2s" dur="0.6s" fill="freeze"/>{"".join(flick)}</g>
</g>
<text x="{W / 2}" y="112" text-anchor="middle" font-family="{SANS}" font-size="50" font-weight="800" fill="#ffffff">Hey 👋, I'm Shafat!</text>
{chr(10).join(focus)}
{chr(10).join(brackets)}
</g>
</svg>
'''
    (OUT / "header.svg").write_text(svg, encoding="utf-8")


# ---------------------------------------------------------------- footer

def footer():
    H = 150
    rnd = random.Random(1337)
    shard, accent = "#7aa2f7", "#bb9af7"
    # far -> near: count, size range, opacity, seconds per pass, blur, ribbon wobble
    levels = [
        (26, (4, 7), 0.3, 46, 1.2, 14),
        (20, (7, 11), 0.55, 34, 0.6, 22),
        (14, (11, 18), 0.9, 24, 0, 30),
    ]
    out = []
    for lv, (count, (lo, hi), op, dur, blur, a) in enumerate(levels):
        c = H / 2 + (lv - 1) * 6
        path = f"M-150,{c + a * 0.4:g} C250,{c - a:g} 550,{c + a:g} 750,{c - a * 0.6:g} S1150,{c + a * 0.8:g} 1350,{c - a * 0.4:g}"
        flt = f' filter="url(#dof{lv})"' if blur else ""
        out.append(f'<g opacity="{op}"{flt}>')
        for i in range(count):
            s = lo + rnd.random() * rnd.random() * (hi - lo) * 1.6
            fam = rnd.random()
            if fam < 0.55:
                sp = 0.17 + rnd.random() * 0.15
                pts = [(1, (rnd.random() - 0.5) * 0.08), (-0.6 - rnd.random() * 0.25, sp), (-0.6 - rnd.random() * 0.25, -sp)]
            elif fam < 0.8:
                sp = 0.2 + rnd.random() * 0.14
                pts = [(1, 0), ((rnd.random() - 0.3) * 0.5, sp), (-0.6 - rnd.random() * 0.2, 0), ((rnd.random() - 0.3) * 0.5, -sp)]
            else:
                n, turn, st = rnd.choice((4, 5)), rnd.random() * math.tau, 0.4 + rnd.random() * 0.3
                pts = [(math.cos(turn + (k + (rnd.random() - 0.5) * 0.6) * math.tau / n), math.sin(turn + (k + (rnd.random() - 0.5) * 0.6) * math.tau / n) * st) for k in range(n)]
            lane = (rnd.random() * 2 - 1) * (18 + lv * 8)
            poly = " ".join(f"{px * s * 1.6:.1f},{py * s * 1.6 + lane:.1f}" for px, py in pts)
            tilt = (rnd.random() - 0.5) * 40
            wob = 6 + rnd.random() * 10
            fdur = 2.5 + rnd.random() * 3
            grad = "glassA" if rnd.random() < 0.5 else "glassB"
            begin = -(i / count + rnd.random() * 0.5 / count) * dur
            out.append(
                f'<g><animateMotion path="{path}" rotate="auto" dur="{dur}s" begin="{begin:.2f}s" repeatCount="indefinite"/>'
                f'<polygon points="{poly}" fill="url(#{grad})" stroke="#e6ecff" stroke-opacity="0.55" stroke-width="0.8" stroke-linejoin="round">'
                f'<animateTransform attributeName="transform" type="rotate" values="{tilt - wob:.1f} 0 {lane:.1f};{tilt + wob:.1f} 0 {lane:.1f};{tilt - wob:.1f} 0 {lane:.1f}" dur="{fdur:.2f}s" repeatCount="indefinite"/>'
                f"</polygon></g>"
            )
        out.append("</g>")

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Glass shards drifting along a ribbon">
<title>Glass shards drifting along a ribbon</title>
<defs>
<clipPath id="card"><rect width="{W}" height="{H}" rx="18"/></clipPath>
<linearGradient id="glassA" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{accent}" stop-opacity="0.85"/><stop offset="1" stop-color="{shard}" stop-opacity="0.25"/></linearGradient>
<linearGradient id="glassB" x1="1" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffffff" stop-opacity="0.7"/><stop offset="0.4" stop-color="{shard}" stop-opacity="0.45"/><stop offset="1" stop-color="{accent}" stop-opacity="0.15"/></linearGradient>
<radialGradient id="haze" cx="0.5" cy="0.5" r="0.6"><stop offset="0" stop-color="{shard}" stop-opacity="0.18"/><stop offset="1" stop-color="{shard}" stop-opacity="0"/></radialGradient>
<filter id="dof0"><feGaussianBlur stdDeviation="1.2"/></filter>
<filter id="dof1"><feGaussianBlur stdDeviation="0.6"/></filter>
</defs>
<g clip-path="url(#card)">
<rect width="{W}" height="{H}" fill="{BG}"/>
<rect width="{W}" height="{H}" fill="url(#haze)"/>
{chr(10).join(out)}
</g>
</svg>
'''
    (OUT / "footer.svg").write_text(svg, encoding="utf-8")


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    header()
    footer()
    print("wrote", *(p.name for p in OUT.glob("*.svg")))
