# -*- coding: utf-8 -*-
"""Build the HyperFrames project (index.html + one scene per chapter + captions) from story.py.

Usage: python3 tools/build.py
Needs tools/voice_timing.json (tools/tts.py) and tools/maps.json (tools/maps.mjs).
"""
import html, json, math, os, random, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from story import CHAPTERS
import art
from art import g

W, H = 1920, 1080
TIMING = json.load(open(os.path.join(HERE, "voice_timing.json")))
MAPS = json.load(open(os.path.join(HERE, "maps.json")))
FONTS = open(os.path.join(ROOT, "assets", "fonts.css")).read()

GAP = 0.75        # silence after each line
PREROLL = 0.7     # extra time before a line that changes the picture
CARD = 6.0        # chapter card
XF = 0.6          # crossfade between pictures
TAIL = 1.2        # end of chapter
CREDITS = 14.0

E = html.escape
rnd = random.Random(1916)

# ------------------------------------------------------------------ palettes
PAL = {
    "ww1":   dict(sky1="#e6c992", sky2="#9b7448", ink="#1c140c", far="#6f5233", mid="#3e2c1a", hi="#8a6d4b", accent="#b8402f", text="#fbf1dc", glow="#ffb347", bg="#d9bd8c"),
    "ww2":   dict(sky1="#d9895a", sky2="#3b2a33", ink="#130d10", far="#5b3a3a", mid="#2c1d22", hi="#6b4d52", accent="#d6372b", text="#fbeee0", glow="#ffb347", bg="#c98b62"),
    "kz":    dict(sky1="#f2b26b", sky2="#5a3f73", ink="#1c1426", far="#7a5a86", mid="#3b2a4d", hi="#8f7aa3", accent="#f2c14e", text="#fff6e6", glow="#ffb347", bg="#e9b77a"),
    "night": dict(sky1="#2a3a66", sky2="#0b1022", ink="#05070f", far="#1b2444", mid="#0f1530", hi="#3b4a7a", accent="#f2c14e", text="#fff6e6", glow="#ffa53a", bg="#1a2344"),
    "dawn":  dict(sky1="#f6c38b", sky2="#6d7fb3", ink="#1a1a2a", far="#8a7fa8", mid="#3c3a5c", hi="#9a90b5", accent="#f2c14e", text="#fffaf0", glow="#ffb347", bg="#f0c79a"),
    "snow":  dict(sky1="#c9d3de", sky2="#5d6878", ink="#141821", far="#8a96a6", mid="#3e4656", hi="#9aa6b6", accent="#d6372b", text="#ffffff", glow="#ffcf7a", bg="#b9c4d1"),
    "forest":dict(sky1="#b8c2a2", sky2="#4a5a48", ink="#141a14", far="#6f806a", mid="#2f3b2e", hi="#7f8f78", accent="#f2c14e", text="#fffaf0", glow="#ffd27a", bg="#9fae8c"),
    "dark":  dict(sky1="#2a2220", sky2="#0c0a0a", ink="#000000", far="#3a302c", mid="#1c1614", hi="#4a3e38", accent="#d6372b", text="#fbf1dc", glow="#ffb347", bg="#1d1816"),
}


def pal_vars(p):
    c = PAL[p]
    return ";".join(f"--{k}:{v}" for k, v in c.items())


# ------------------------------------------------------------------ helpers
class Beat:
    def __init__(self, cid, n, start, dur, v):
        self.cid, self.n, self.t, self.d, self.v = cid, n, start, dur, v
        self.id = f"{cid}-b{n}"
        self.sel = "#" + self.id
        self.js = []

    def tw(self, target, frm, to, at=0.0, **kw):
        """fromTo tween at beat time `at` (seconds from the beat start)."""
        to = dict(to)
        to.update(kw)
        sel = target if target.startswith("#") else f"{self.sel} {target}"
        self.js.append(f'tl.fromTo("{sel}", {json.dumps(frm)}, {json.dumps(to)}, {self.t + at:.3f});')

    def loop(self, target, frm, to, period, at=0.0, **kw):
        """A yo-yo motion that runs for the whole beat, with a finite repeat count."""
        rep = max(1, int((self.d - at) / period))
        self.tw(target, frm, to, at, duration=period, ease="sine.inOut", repeat=rep, yoyo=True, **kw)

    def count(self, target, frm, to, at, dur, fmt="plain", pre="", post=""):
        sel = f"{self.sel} {target}"
        self.js.append(
            f'(function(){{const o={{v:{frm}}};const el=document.querySelector("{sel}");'
            f'tl.fromTo(o,{{v:{frm}}},{{v:{to},duration:{dur},ease:"power2.out",onUpdate:function(){{'
            f'let n=Math.round(o.v);let s={"String(n).replace(/\\B(?=(\\d{3})+(?!\\d))/g, \" \")" if fmt == "space" else "String(n)"};'
            f'el.textContent={json.dumps(pre)}+s+{json.dumps(post)};}}}},{self.t + at:.3f});}})();')


def svg(inner, defs="", cls="art"):
    return (f'<svg class="{cls}" viewBox="0 0 {W} {H}" width="{W}" height="{H}" preserveAspectRatio="xMidYMid slice">'
            f'<defs>{defs}</defs>{inner}</svg>')


def sky_defs(b, extra=""):
    return (f'<linearGradient id="{b.id}-sky" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0" stop-color="var(--sky2)"/><stop offset="1" stop-color="var(--sky1)"/></linearGradient>'
            f'<radialGradient id="{b.id}-sun" cx="0.5" cy="0.5" r="0.5"><stop offset="0" stop-color="var(--glow)" stop-opacity=".9"/>'
            f'<stop offset="1" stop-color="var(--glow)" stop-opacity="0"/></radialGradient>' + extra)


def hills(color, base, amp, seed, step=160):
    r = random.Random(seed)
    pts = [f"-40,{H+40}", f"-40,{base}"]
    x = -40
    while x < W + 200:
        x += step
        pts.append(f"{x},{base - r.uniform(0, amp):.0f}")
    pts.append(f"{W+200},{H+40}")
    return f'<polygon points="{" ".join(pts)}" fill="{color}"/>'


def landscape(b, sun=(1450, 560, 260), ground=880, extra_back="", seed=1):
    """Sky, sun glow, two hill layers and ground. Returns svg parts (back, front ground)."""
    sx, sy, sr = sun
    back = (f'<rect width="{W}" height="{H}" fill="url(#{b.id}-sky)"/>'
            f'<circle class="sun" cx="{sx}" cy="{sy}" r="{sr}" fill="url(#{b.id}-sun)"/>'
            + extra_back +
            f'<g class="far">{hills("var(--far)", ground - 140, 90, seed)}</g>'
            f'<g class="mid">{hills("var(--mid)", ground - 50, 50, seed + 1, 220)}</g>')
    front = f'<rect x="-50" y="{ground}" width="{W+100}" height="{H-ground+50}" fill="var(--ink)"/>'
    return back, front


def dust(b, n=40, color="var(--text)", size=(1.5, 4), area=(0, 0, W, H), drift=-60, op=0.35):
    out = []
    for i in range(n):
        x = rnd.uniform(area[0], area[2]); y = rnd.uniform(area[1], area[3]); r = rnd.uniform(*size)
        out.append(f'<circle class="pt pt{i%4}" cx="{x:.0f}" cy="{y:.0f}" r="{r:.1f}" fill="{color}" opacity="{rnd.uniform(op*0.4, op):.2f}"/>')
    for k in range(4):
        b.tw(f".pt{k}", {"x": 0, "y": 0}, {"x": drift * (0.5 + k * 0.3), "y": -30 - k * 12}, 0, duration=b.d, ease="none")
    return "".join(out)


def kenburns(b, s0=1.0, s1=1.06, x=0, y=0):
    b.tw(".cam", {"scale": s0, "x": 0, "y": 0}, {"scale": s1, "x": x, "y": y}, 0, duration=b.d, ease="none")


def text_in(b, target, at, y=30, dur=0.8):
    b.tw(target, {"opacity": 0, "y": y}, {"opacity": 1, "y": 0}, at, duration=dur, ease="power3.out")


# ------------------------------------------------------------------ beat renderers
def r_card(b, v):
    b.pal = "dark"
    kenburns(b, 1.0, 1.04)
    text_in(b, ".k-num", 0.3)
    b.tw(".k-line", {"scaleX": 0}, {"scaleX": 1}, 0.6, duration=1.0, ease="power3.inOut")
    text_in(b, ".k-title", 0.8, 40, 1.0)
    b.tw(".k-wrap", {"opacity": 1}, {"opacity": 0}, b.d - 0.9, duration=0.8)
    inner = svg(f'<rect width="{W}" height="{H}" fill="var(--sky2)"/>' + dust(b, 60, "var(--glow)", (1, 3), drift=40, op=0.5))
    return inner + (f'<div class="k-wrap"><div class="k-num">{E(v["num"])}</div><div class="k-line"></div>'
                    f'<div class="k-title">{E(v["t"])}</div></div>')


def r_title(b, v):
    era = v.get("era")
    b.pal = era or "kz"
    back, front = landscape(b, seed=3)
    marchers = ""
    if era in ("ww1", "ww2"):
        for i in range(9):
            marchers += g(art.soldier(era), 200 + i * 70, 878, 0.32, cls="mrch")
        if era == "ww2":
            marchers += g(art.tank2(), 1500, 878, 0.55, cls="tnk")
        else:
            marchers += g(art.tank1(), 1500, 878, 0.5, cls="tnk")
    else:
        for i in range(5):
            marchers += g(art.soldier("ww1"), 180 + i * 62, 878, 0.3, cls="mrch")
        for i in range(5):
            marchers += g(art.soldier("ww2"), 1250 + i * 62, 878, 0.3, cls="mrch")
    b.tw(".mrch", {"x": 0}, {"x": 260}, 0, duration=b.d, ease="none")
    b.tw(".tnk", {"x": 0}, {"x": -180}, 0, duration=b.d, ease="none")
    b.loop(".lg1", {"rotation": -18}, {"rotation": 18}, 0.45)
    b.loop(".lg2", {"rotation": 18}, {"rotation": -18}, 0.45)
    kenburns(b, 1.08, 1.0)
    text_in(b, ".t-main", 0.3, 50, 1.2)
    b.tw(".t-rule", {"scaleX": 0}, {"scaleX": 1}, 0.9, duration=1.0, ease="power3.inOut")
    text_in(b, ".t-sub", 1.3, 20, 1.0)
    inner = svg(f'<g class="cam">{back}<g fill="var(--ink)">{marchers}</g>{front}</g>' + dust(b, 50), sky_defs(b))
    return inner + (f'<div class="t-box"><div class="t-main">{E(v["t"])}</div><div class="t-rule"></div>'
                    f'<div class="t-sub">{E(v.get("sub",""))}</div></div>')


def r_yurt(b, v):
    b.pal = "dawn" if v.get("dawn") else "night"
    stars = "".join(f'<circle class="st st{i%3}" cx="{rnd.uniform(0,W):.0f}" cy="{rnd.uniform(0,560):.0f}" r="{rnd.uniform(1,2.6):.1f}" fill="#fff"/>' for i in range(110))
    if v.get("dawn"):
        stars = ""
    for k in range(3):
        b.loop(f".st{k}", {"opacity": 0.25}, {"opacity": 1}, 1.4 + k * 0.6, at=k * 0.3)
    moon = '' if v.get("dawn") else '<circle cx="1560" cy="190" r="62" fill="#f4ecd2"/><circle cx="1584" cy="176" r="58" fill="var(--sky2)" opacity=".9"/>'
    back, front = landscape(b, sun=(960, 860, 700) if v.get("dawn") else (520, 840, 520), ground=880, extra_back=stars + moon, seed=8)
    scene = (g(art.yurt(), 560, 882, 1.05) +
             g(art.campfire(), 1000, 882, 1.1) +
             g(art.elder(), 860, 884, 1.0) +
             g(art.boy(), 1160, 884, 1.05, flip=True))
    smoke = "".join(f'<circle class="sm sm{i}" cx="560" cy="630" r="{18+i*6}" fill="#c9c3d6" opacity=".18"/>' for i in range(5))
    for i in range(5):
        b.tw(f".sm{i}", {"y": 0, "x": 0, "opacity": 0.22}, {"y": -260 - i * 30, "x": 60 + i * 20, "opacity": 0},
             i * 1.1, duration=max(1.0, b.d - i * 1.1), ease="none")
    b.loop(".fl", {"scaleY": 0.86, "scaleX": 1.05}, {"scaleY": 1.12, "scaleX": 0.95}, 0.23)
    b.loop(".glowc", {"opacity": 0.55, "scale": 0.96}, {"opacity": 0.85, "scale": 1.04}, 0.37)
    photo = ""
    if v.get("photo"):
        photo = (f'<div class="photo"><div class="ph-in"><svg viewBox="0 0 300 380" width="300" height="380">'
                 f'<rect width="300" height="380" fill="#d8c29a"/><rect x="18" y="18" width="264" height="344" fill="#b89a6c"/>'
                 f'<g fill="#3a2a18">{art.officer_icon().replace("var(--bg)", "#b89a6c") if False else ""}'
                 f'<path d="M50,362 Q50,250 110,236 L190,236 Q250,250 250,362 Z"/><circle cx="150" cy="170" r="56"/>'
                 f'<path d="M86,146 Q150,70 214,146 L222,160 L78,160 Z"/>{g(art.star(14), 150, 126, 1)}</g>'
                 f'</svg></div></div>')
        b.tw(".ph-in", {"opacity": 0, "y": 40, "rotation": -8, "scale": 0.8}, {"opacity": 1, "y": 0, "rotation": -3, "scale": 1}, 0.4, duration=1.2, ease="power3.out")
    kenburns(b, 1.0, 1.07, 0, 10)
    glow = f'<circle class="glowc" cx="1000" cy="840" r="260" fill="url(#{b.id}-fire)" style="transform-origin:1000px 840px"/>'
    defs = sky_defs(b, f'<radialGradient id="{b.id}-fire"><stop offset="0" stop-color="#ff9a3a" stop-opacity=".55"/><stop offset="1" stop-color="#ff9a3a" stop-opacity="0"/></radialGradient>')
    return svg(f'<g class="cam">{back}{front}{glow}{smoke}<g fill="var(--ink)">{scene}</g></g>', defs) + photo


# --- maps
ENTENTE = {"250", "826", "372", "056", "688", "499", "380", "642", "300", "620", "840"}
RUSSIA_EMP = {"643", "804", "112", "398", "860", "795", "762", "417", "031", "051", "268", "498", "233", "428", "440", "246", "616"}
CENTRAL = {"276", "040", "348", "203", "703", "191", "705", "070", "792", "760", "368", "400", "376", "422", "100"}
AH = {"040", "348", "203", "703", "191", "705", "070"}
OTT = {"792", "760", "368", "400", "376", "422"}
USSR = {"643", "804", "112", "398", "860", "795", "762", "417", "031", "051", "268", "498", "233", "428", "440"}
AXIS = {"276", "380", "392", "040"}
ALLIES = USSR | {"826", "840", "156", "250", "124", "036", "554", "356", "076", "710"}
LAB_EU = {"RU": "РЕСЕЙ", "DE": "ГЕРМАНИЯ", "FR": "ФРАНЦИЯ", "GB": "ҰЛЫБРИТАНИЯ", "IT": "ИТАЛИЯ", "AH": "АВСТРИЯ-ВЕНГРИЯ",
          "OT": "ОСМАН ИМПЕРИЯСЫ", "RS": "СЕРБИЯ", "BG": "БОЛГАРИЯ"}
LAB_W = {"DE": "ГЕРМАНИЯ", "IT": "ИТАЛИЯ", "JP": "ЖАПОНИЯ", "SU": "КСРО", "US": "АҚШ", "CN": "ҚЫТАЙ"}


def r_map(b, v):
    era, mode = v["era"], v["mode"]
    b.pal = era
    view = "world" if (era == "ww2" and mode in ("sides", "world")) else "eu"
    M = MAPS[view]
    blue, red, gold, base = "#4d6b80", "#9a3b2c", "#e0a93a", "#c9b08a" if era == "ww1" else "#b99a86"

    def fill(cid):
        if mode == "kz":
            if cid == "398":
                return gold
            return "#7f8f9a" if cid in (RUSSIA_EMP if era == "ww1" else USSR) else base
        if era == "ww1":
            if mode == "empires":
                if cid in RUSSIA_EMP: return "#6f8796"
                if cid == "276": return "#8e3a2c"
                if cid in AH: return "#a5603c"
                if cid in OTT: return "#b98a3c"
                if cid in ("826", "372"): return "#5a7a6a"
                if cid == "250": return "#4d6b80"
                return base
            if cid in ENTENTE or cid in RUSSIA_EMP: return blue
            if cid in CENTRAL: return red
            return base
        if cid in AXIS: return red
        if cid in ALLIES: return blue
        return base

    paths = []
    for cid, d in M["shapes"].items():
        c = fill(cid)
        cls = "cty kzc" if cid == "398" else "cty"
        paths.append(f'<path class="{cls}" d="{d}" fill="{c}" stroke="#2b2118" stroke-width="1.2" stroke-opacity=".55"/>')
    sea = "#8ea3a8" if era == "ww1" else "#6f8a94"
    labels = ""
    labset = LAB_W if view == "world" else LAB_EU
    if mode != "kz":
        for k, name in labset.items():
            if k not in M["labels"]:
                continue
            x, y = M["labels"][k]
            small = k in ("RS", "BG")
            labels += f'<text class="mlab" x="{x}" y="{y}" font-size="{28 if small else 32}">{name}</text>'
    extra = ""
    if mode == "kz":
        x, y = M["labels"]["KZ"]
        lab = "ҚАЗАҚ ЖЕРІ" if era == "ww1" else "ҚАЗАҚ КСР"
        extra += f'<text class="mlab big" x="{x}" y="{y}">{lab}</text>'
        sub = "Ресей империясының құрамында" if era == "ww1" else "Кеңес Одағының құрамында"
        extra += f'<text class="mlab sub" x="{x-40}" y="{y-70}">{sub}</text>'
        b.loop(".kzc", {"opacity": 0.75}, {"opacity": 1}, 0.9, at=0.8)
        if era == "ww2":
            (mx, my), (ax, ay) = M["lines"]["moscow"][0], M["lines"]["almaty"][0]
            extra += (f'<path class="arrow" d="M{ax},{ay} Q{(ax+mx)/2},{min(ay,my)-180} {mx},{my}" fill="none" stroke="#d6372b" stroke-width="7" stroke-dasharray="1400" stroke-dashoffset="1400" stroke-linecap="round"/>'
                      f'<circle cx="{mx}" cy="{my}" r="10" fill="#d6372b"/><text class="mlab" x="{mx}" y="{my-22}">МӘСКЕУ</text>'
                      f'<circle cx="{ax}" cy="{ay}" r="10" fill="#1c140c"/><text class="mlab" x="{ax+40}" y="{ay+50}">АЛМАТЫ</text>')
            b.tw(".arrow", {"strokeDashoffset": 1400}, {"strokeDashoffset": 0}, 1.2, duration=2.5, ease="power2.inOut")
    if mode == "sides" and era == "ww1":
        x, y = M["lines"]["sarajevo"][0]
        extra += f'<circle class="pulse ps9" cx="{x}" cy="{y}" r="14" fill="#ffd36a"/><text class="mlab" x="{x-70}" y="{y+44}" font-size="28">Сараево</text>'
        b.loop(".ps9", {"scale": 0.7, "opacity": 1}, {"scale": 1.6, "opacity": 0.5}, 0.7, svgOrigin=f"{x} {y}")
    if mode == "fronts":
        for k, name, off in (("west", "Батыс майдан", (-190, -40)), ("east", "Шығыс майдан", (130, 0))):
            pts = M["lines"][k]
            d = "M" + " L".join(f"{x},{y}" for x, y in pts)
            extra += f'<path class="front" d="{d}" fill="none" stroke="#b01e14" stroke-width="9" stroke-linejoin="round" stroke-dasharray="900" stroke-dashoffset="900"/>'
            x, y = pts[len(pts) // 2]
            extra += f'<text class="mlab red" x="{x+off[0]}" y="{y+off[1]}">{name}</text>'
        px, py = M["lines"]["paris"][0]
        extra += g(art.star(16), px, py, 1, extra=' fill="#ffd36a"') + f'<text class="mlab" x="{px-60}" y="{py+40}" font-size="28">Париж</text>'
        b.tw(".front", {"strokeDashoffset": 900}, {"strokeDashoffset": 0}, 0.8, duration=2.4, ease="power2.inOut", stagger=0.6)
    if mode == "world":
        for j, k in enumerate(("europe", "pacific", "africa", "atlantic", "china")):
            x, y = M["lines"][k][0]
            extra += f'<circle class="pulse ps{j}" cx="{x}" cy="{y}" r="16" fill="#ffd36a"/>'
            b.loop(f".ps{j}", {"scale": 0.6, "opacity": 1}, {"scale": 1.8, "opacity": 0.4}, 0.8, at=j * 0.15, svgOrigin=f"{x} {y}")
    legend = ""
    if mode in ("sides", "fronts", "world"):
        a, c = ("Антанта", "Орталық державалар") if era == "ww1" else ("Одақтастар", "«Ось» елдері")
        legend = (f'<div class="legend"><div><i style="background:{blue}"></i>{a}</div>'
                  f'<div><i style="background:{red}"></i>{c}</div></div>')
        text_in(b, ".legend", 0.6, 20)
    if mode == "empires":
        legend = '<div class="legend"><div>1914 жылғы Еуропа</div><div class="lg-note">(шекаралар шамамен, қазіргі карта бойынша)</div></div>'
        text_in(b, ".legend", 0.6, 20)
    b.tw(".cty", {"opacity": 0}, {"opacity": 1}, 0.0, duration=0.9, stagger={"amount": 0.8, "from": "random"})
    text_in(b, ".mlab", 0.9, 10, 0.6)
    kenburns(b, 1.0, 1.08)
    paper = (f'<rect width="{W}" height="{H}" fill="{sea}"/>'
             f'<rect width="{W}" height="{H}" fill="url(#{b.id}-vig)"/>')
    defs = (f'<radialGradient id="{b.id}-vig" cx=".5" cy=".5" r=".75"><stop offset=".55" stop-color="#000" stop-opacity="0"/>'
            f'<stop offset="1" stop-color="#1a120a" stop-opacity=".6"/></radialGradient>')
    return svg(f'<g class="cam">{paper}{"".join(paths)}{labels}{extra}</g>', defs) + legend


def r_date(b, v):
    era = v.get("era", "ww1")
    b.pal = "snow" if v.get("snow") else era
    back, front = landscape(b, sun=(1500, 620, 300), ground=900, seed=len(v["t"]) + 11)
    fg = ""
    if v.get("flag"):
        fg += g(art.reichstag(), 1340, 902, 0.85)
        b.loop(".wave", {"skewY": -3, "scaleY": 0.95}, {"skewY": 3, "scaleY": 1.03}, 0.6)
    elif v.get("un"):
        rings = "".join(f'<circle cx="0" cy="0" r="{r}" fill="none" stroke="currentColor" stroke-width="5"/>' for r in (60, 110, 160))
        merid = '<path d="M0,-160 L0,160 M-160,0 L160,0 M-113,-113 L113,113 M113,-113 L-113,113" stroke="currentColor" stroke-width="4"/>'
        leaves = "".join(g(f'<ellipse cx="0" cy="0" rx="26" ry="10" transform="rotate({-50 + i*12})"/>',
                           s * (200 * math.cos(math.radians(100 + i * 14))), 200 * math.sin(math.radians(100 + i * 14)) * -1 + 40, 1)
                         for i in range(9) for s in (1, -1))
        fg += f'<g class="un" transform="translate(1560,640) scale(.7)" fill="currentColor" color="var(--text)" opacity=".9">{rings}{merid}{leaves}</g>'
        b.tw(".un", {"rotation": -8, "opacity": 0}, {"rotation": 0, "opacity": 0.9}, 0.4, duration=1.6, ease="power2.out", svgOrigin="1560 640")
    else:
        era_s = "ww2" if era == "ww2" else "ww1"
        for i in range(7):
            fg += g(art.soldier(era_s), 1080 + i * 95, 902, 0.42, cls="mrch")
        b.tw(".mrch", {"x": 0}, {"x": 220}, 0, duration=b.d, ease="none")
        b.loop(".lg1", {"rotation": -18}, {"rotation": 18}, 0.45)
        b.loop(".lg2", {"rotation": 18}, {"rotation": -18}, 0.45)
    snow = ""
    if v.get("snow"):
        flakes = "".join(f'<circle class="fk fk{i%3}" cx="{rnd.uniform(0,W):.0f}" cy="{rnd.uniform(-1100,0):.0f}" r="{rnd.uniform(2,5):.1f}" fill="#fff" opacity=".8"/>' for i in range(160))
        snow = f'<g>{flakes}</g>'
        for k in range(3):
            b.tw(f".fk{k}", {"y": 0, "x": 0}, {"y": 1100 + k * 300, "x": -120 + k * 60}, 0, duration=b.d, ease="none")
    fw = ""
    if v.get("fireworks"):
        for i, (cx, cy, col) in enumerate(((1250, 260, "#ffd36a"), (1600, 200, "#ff6b4a"), (1450, 380, "#9ad0ff"), (1750, 330, "#ffd36a"))):
            rays = "".join(f'<path d="M0,0 L{math.cos(a)*90:.0f},{math.sin(a)*90:.0f}" stroke="{col}" stroke-width="4" stroke-linecap="round"/>'
                           for a in [k * math.pi / 8 for k in range(16)])
            fw += f'<g class="fw fw{i}" transform="translate({cx},{cy})">{rays}</g>'
            for rep in range(int(b.d / 2.4) + 1):
                at = 0.6 + i * 0.55 + rep * 2.4
                if at + 1.4 < b.d:
                    b.tw(f".fw{i}", {"scale": 0.1, "opacity": 1}, {"scale": 1.2, "opacity": 0}, at, duration=1.4, ease="expo.out", svgOrigin=f"{cx} {cy}", immediateRender=False)
    b.tw(".fw", {"opacity": 0}, {"opacity": 0}, 0, duration=0.01)
    kenburns(b, 1.0, 1.06, -20, 0)
    b.tw(".d-year", {"opacity": 0, "scale": 1.25, "filter": "blur(14px)"}, {"opacity": 1, "scale": 1, "filter": "blur(0px)"}, 0.15, duration=1.0, ease="power3.out")
    b.tw(".d-rule", {"scaleX": 0}, {"scaleX": 1}, 0.7, duration=0.9, ease="power3.inOut")
    text_in(b, ".d-sub", 0.9, 24)
    inner = svg(f'<g class="cam">{back}{fw}<g fill="var(--ink)" color="var(--ink)">{fg}</g>{front}{snow}</g>', sky_defs(b))
    return inner + f'<div class="d-box"><div class="d-year">{E(v["t"])}</div><div class="d-rule"></div><div class="d-sub">{E(v["sub"])}</div></div>'


def r_march(b, v):
    era = v["era"]
    b.pal = era
    back, front = landscape(b, sun=(1300, 600, 300), ground=900, seed=21)
    rows = ""
    for row, (y, s, n, sp) in enumerate(((800, 0.42, 14, 120), (850, 0.6, 10, 175), (905, 0.95, 7, 290))):
        grp = "".join(g(art.soldier(era), -300 + i * sp + (row * 40), 0, 1) for i in range(n))
        rows += f'<g class="row row{row}" transform="translate(0,{y}) scale({s})" fill="var(--ink)" color="var(--ink)" opacity="{0.55 + row*0.22:.2f}">{grp}</g>'
        b.tw(f".row{row}", {"x": 0}, {"x": 120 + row * 160}, 0, duration=b.d, ease="none")
    b.loop(".lg1", {"rotation": -20}, {"rotation": 20}, 0.42)
    b.loop(".lg2", {"rotation": 20}, {"rotation": -20}, 0.42)
    flagpole = g(f'<rect x="-3" y="-260" width="6" height="260"/><path class="wave" d="M3,-260 Q40,-270 80,-252 L80,-200 Q40,-214 3,-206 Z" fill="var(--accent)"/>', 700, 905, 0.95, cls="row2")
    b.loop(".wave", {"skewY": -4}, {"skewY": 4}, 0.55)
    kenburns(b, 1.02, 1.08)
    return svg(f'<g class="cam">{back}{rows}{front}</g>' + dust(b, 60, "var(--glow)", (1.5, 4), (0, 600, W, H), drift=-160), sky_defs(b))


def r_trench(b, v):
    b.pal = "ww1"
    sky = f'<rect width="{W}" height="{H}" fill="url(#{b.id}-sky)"/>'
    flares = "".join(f'<circle class="flare fl{i}" cx="{x}" cy="300" r="10" fill="#fff3c4"/>' for i, x in enumerate((500, 1300, 900)))
    for i in range(3):
        for rep in range(int(b.d / 6) + 1):
            at = 1 + i * 2 + rep * 6
            if at + 3 < b.d:
                b.tw(f".fl{i}", {"y": 200, "opacity": 1, "scale": 1}, {"y": -120, "opacity": 0, "scale": 0.4}, at, duration=3, ease="power1.out", immediateRender=False)
    b.tw(".flare", {"opacity": 0}, {"opacity": 0}, 0, duration=0.01)
    nomans = (f'<path d="M-50,640 Q300,610 600,640 T1200,632 T1980,640 L1980,700 L-50,700 Z" fill="var(--mid)"/>'
              + f'<g fill="var(--ink)" color="var(--ink)">{art.barbed(0, 1950, 650)}</g>')
    soldiers = "".join(g(art.soldier("ww1", pose="aim"), x, 930, 1.35, cls=f"sold") for x in (200, 700, 1250, 1680))
    bags = f'<g fill="#4a3519">{art.sandbags(-40, 1980, 720)}</g>'
    earth = (f'<path d="M-50,730 L1980,730 L1980,1100 L-50,1100 Z" fill="#7a5a34"/>'
             + "".join(f'<rect x="{x}" y="740" width="14" height="190" fill="#5a4024"/>' for x in range(40, 1960, 130))
             + f'<path d="M-50,925 L1980,925 L1980,1100 L-50,1100 Z" fill="#3a2814"/>')
    planks = "".join(f'<rect x="{x}" y="925" width="80" height="14" fill="#5a3d20"/>' for x in range(0, 1960, 96))
    rain = "".join(f'<path class="rn rn{i%3}" d="M{rnd.uniform(0,W+300):.0f},{rnd.uniform(-1100,0):.0f} l-30,70" stroke="#e8e2d0" stroke-width="2" opacity=".35"/>' for i in range(170))
    for k in range(3):
        b.tw(f".rn{k}", {"y": 0, "x": 0}, {"y": 1300 + k * 120, "x": -560}, 0, duration=min(b.d, 30), ease="none", repeat=max(0, int(b.d / 30) - 1))
    b.loop(".sold", {"y": 0}, {"y": -6}, 1.6)
    kenburns(b, 1.0, 1.07)
    return svg(f'<g class="cam">{sky}{flares}{nomans}{bags}{earth}<g fill="var(--ink)" color="var(--ink)">{soldiers}</g>{planks}</g>{rain}', sky_defs(b))


def r_tech(b, v):
    b.pal = v.get("era", "ww1")
    cards = ""
    for i, (ic, label) in enumerate(v["items"]):
        cards += (f'<div class="tc tc{i}"><svg viewBox="-150 -150 300 300" width="260" height="260">'
                  f'<g fill="var(--ink)" color="var(--ink)">{art.icon(ic)}</g></svg><div class="tc-l">{E(label)}</div></div>')
        b.tw(f".tc{i}", {"opacity": 0, "y": 60, "scale": 0.9}, {"opacity": 1, "y": 0, "scale": 1}, 0.5 + i * 0.6, duration=0.8, ease="back.out(1.6)")
    b.loop(".prop", {"scaleY": 1}, {"scaleY": 0.15}, 0.06)
    back = svg(f'<rect width="{W}" height="{H}" fill="url(#{b.id}-sky)"/>' + dust(b, 50), sky_defs(b))
    return back + f'<div class="tc-row">{cards}</div>'


def r_battle(b, v):
    era = v["era"]
    b.pal = era
    back, front = landscape(b, sun=(600, 560, 340), ground=880, seed=31)
    fg = ""
    booms = ""
    if era == "ww1":
        fg += g(art.tank1(), 0, 878, 0.95, cls="tk tk0")
        fg += g(art.tank1(), 0, 860, 0.55, cls="tk tk1")
        b.tw(".tk0", {"x": -400}, {"x": 900}, 0, duration=b.d, ease="none")
        b.tw(".tk1", {"x": 600}, {"x": 1500}, 0, duration=b.d, ease="none")
        sold = "".join(g(art.soldier("ww1", "aim"), -200 + i * 150, 880, 0.55) for i in range(8))
        fg += f'<g class="chg">{sold}</g>'
        b.tw(".chg", {"x": -200}, {"x": 500}, 0, duration=b.d, ease="none")
        planes = g(art.biplane(), 0, 250, 0.9, cls="pl pl0") + g(art.biplane(), 0, 360, 0.6, cls="pl pl1")
    else:
        n = 4 if v.get("big") else 3
        for i in range(n):
            y, s = 880 - (i % 2) * 30, 1.0 - (i % 2) * 0.35
            fg += g(art.tank2(), 0, y, s, cls=f"tk tk{i}")
            b.tw(f".tk{i}", {"x": -500 - i * 520}, {"x": 1700 - i * 420}, 0, duration=b.d, ease="none")
        b.loop(".wh", {"rotation": 0}, {"rotation": 180}, 0.5)
        planes = g(art.fighter(), 0, 220, 0.9, cls="pl pl0") + g(art.bomber(), 0, 330, 0.8, cls="pl pl1") + g(art.fighter(), 0, 160, 0.6, cls="pl pl2")
        b.tw(".pl2", {"x": -300}, {"x": 2300}, 1.5, duration=min(9, b.d), ease="none")
    b.tw(".pl0", {"x": -300}, {"x": 2300}, 0.2, duration=min(12, b.d), ease="none")
    b.tw(".pl1", {"x": -400}, {"x": 2300}, 0.8, duration=min(16, b.d), ease="none")
    b.loop(".prop", {"scaleY": 1}, {"scaleY": 0.15}, 0.06)
    for i in range(6):
        x = 300 + i * 270 + rnd.uniform(-60, 60)
        booms += (f'<g class="bm bm{i}" transform="translate({x:.0f},850)"><circle r="70" fill="#f3d9a0" opacity=".9"/>'
                  f'<circle cx="-40" cy="-30" r="55" fill="#8b7355" opacity=".7"/><circle cx="40" cy="-50" r="60" fill="#6b5a48" opacity=".6"/></g>')
        for rep in range(int(b.d / 4.5) + 1):
            at = 0.8 + i * 0.7 + rep * 4.5
            if at + 1.8 < b.d:
                b.tw(f".bm{i}", {"scale": 0.1, "opacity": 1}, {"scale": 1.4, "opacity": 0}, at, duration=1.8, ease="power2.out", svgOrigin=f"{x:.0f} 850", immediateRender=False)
    b.tw(".bm", {"opacity": 0}, {"opacity": 0}, 0, duration=0.01)
    kenburns(b, 1.0, 1.06)
    return svg(f'<g class="cam">{back}{booms}<g fill="var(--ink)" color="var(--ink)">{planes}{fg}</g>{front}</g>' + dust(b, 70, "#c9b89a", (2, 5), (0, 500, W, H), -200, 0.4), sky_defs(b))


def r_stat(b, v):
    era = v.get("era", "ww1")
    b.pal = era
    to = v["to"]
    pre, post = v.get("pre", ""), v.get("post", "")
    fmt = v.get("fmt", "plain")
    b.count(".s-num", 0, to, 0.5, 2.2, fmt, pre, post)
    text_in(b, ".s-label", 0.2)
    text_in(b, ".s-unit", 1.2)
    icons = ""
    n = v.get("icons", 0)
    if n:
        cols = 20 if n > 30 else min(n, 14)
        sz = 46 if n > 30 else 64
        cells = "".join(f'<svg class="pi" viewBox="-12 -42 24 44" width="{sz*0.55:.0f}" height="{sz:.0f}"><g fill="var(--text)">{art.person_icon()}</g></svg>' for _ in range(n))
        icons = f'<div class="s-grid" style="width:{cols*(sz*0.55+10):.0f}px">{cells}</div>'
        b.tw(".pi", {"opacity": 0, "y": 14}, {"opacity": 0.9, "y": 0}, 1.2, duration=0.35, stagger={"amount": min(4.0, b.d - 2)}, ease="power2.out")
    kenburns(b, 1.0, 1.05)
    back = svg(f'<rect width="{W}" height="{H}" fill="url(#{b.id}-sky)"/><rect width="{W}" height="{H}" fill="#000" opacity=".35"/>' + dust(b, 50), sky_defs(b))
    return back + (f'<div class="s-box"><div class="s-label">{E(v["label"])}</div>'
                   f'<div class="s-num">{E(pre)}0{E(post)}</div><div class="s-unit">{E(v["unit"])}</div>{icons}</div>')


def r_compare(b, v):
    b.pal = "dark"
    cols = ""
    for i, (yr, n, lab) in enumerate((("1914–1918", 18, "15–22 млн"), ("1939–1945", 78, "70–85 млн"))):
        cells = "".join(f'<svg class="pi pi{i}" viewBox="-12 -42 24 44" width="{40 if i==0 else 30}" height="{74 if i==0 else 56}"><g fill="{"#e9c891" if i==0 else "#ff8a6b"}">{art.person_icon()}</g></svg>' for _ in range(n))
        cols += f'<div class="cp cp{i}"><div class="cp-y">{yr}</div><div class="cp-n">{lab}</div><div class="cp-g">{cells}</div></div>'
        text_in(b, f".cp{i}", 0.3 + i * 0.5)
        b.tw(f".pi{i}", {"opacity": 0, "scale": 0.4}, {"opacity": 1, "scale": 1}, 0.8 + i * 2.4, duration=0.3, stagger={"amount": 1.0 if i == 0 else 3.0}, ease="back.out(2)")
    back = svg(f'<rect width="{W}" height="{H}" fill="url(#{b.id}-sky)"/>' + dust(b, 40), sky_defs(b))
    return back + f'<div class="cp-row">{cols}</div><div class="cp-note">1 сұлба ≈ 1 миллион адам</div>'


def r_winner(b, v):
    b.pal = v["era"]
    leaves = "".join(g(f'<ellipse rx="22" ry="9" transform="rotate({-60 + i*14})"/>',
                       s * 150 * math.cos(math.radians(110 + i * 15)), -150 * math.sin(math.radians(110 + i * 15)) + 60, 1)
                     for i in range(9) for s in (1, -1))
    laurel = f'<svg class="laurel" viewBox="-200 -120 400 300" width="360" height="270"><g fill="#e8c35a">{leaves}{g(art.star(44), 0, -10, 1)}</g></svg>'
    text_in(b, ".w-win", 0.3, 40, 1.0)
    b.tw(".laurel", {"opacity": 0, "rotation": -20, "scale": 0.6}, {"opacity": 1, "rotation": 0, "scale": 1}, 0.5, duration=1.2, ease="back.out(1.4)")
    text_in(b, ".w-lose", 1.4, 20)
    back = svg(f'<rect width="{W}" height="{H}" fill="url(#{b.id}-sky)"/><rect width="{W}" height="{H}" fill="#000" opacity=".3"/>' + dust(b, 60, "var(--glow)"), sky_defs(b))
    kenburns(b, 1.0, 1.05)
    return back + (f'<div class="w-box"><div class="w-win">{laurel}<div class="w-tag">ЖЕҢІСКЕ ЖЕТТІ</div>'
                   f'<div class="w-name">{E(v["win"])}</div><div class="w-sub">{E(v["winSub"])}</div></div>'
                   f'<div class="w-lose">Жеңілді: <b>{E(v["lose"])}</b></div></div>')


def r_list(b, v):
    b.pal = v.get("era", "kz")
    items = "".join(f'<li class="li li{i}">{E(t)}</li>' for i, t in enumerate(v["items"]))
    text_in(b, ".l-title", 0.2)
    for i in range(len(v["items"])):
        b.tw(f".li{i}", {"opacity": 0, "x": -40}, {"opacity": 1, "x": 0}, 0.6 + i * min(0.9, (b.d - 2) / max(1, len(v["items"]))), duration=0.6, ease="power3.out")
    back = svg(f'<rect width="{W}" height="{H}" fill="url(#{b.id}-sky)"/><rect width="{W}" height="{H}" fill="#000" opacity=".45"/>' + dust(b, 50), sky_defs(b))
    return back + f'<div class="l-box"><div class="l-title">{E(v["title"])}</div><ul>{items}</ul></div>'


def r_note(b, v):
    b.pal = "dark"
    text_in(b, ".n-card", 0.2, 30, 1.0)
    back = svg(f'<rect width="{W}" height="{H}" fill="url(#{b.id}-sky)"/>' + dust(b, 60, "var(--glow)", (1, 3), drift=30, op=0.45), sky_defs(b))
    kenburns(b, 1.0, 1.04)
    return back + f'<div class="n-card"><div class="n-t">{E(v["t"])}</div><div class="n-b">{E(v["body"])}</div></div>'


def r_steppe(b, v):
    night = v.get("night")
    b.pal = "ww2" if night else "kz"
    back, front = landscape(b, sun=(1400, 700, 380), ground=890, seed=41)
    grass = "".join(f'<path class="gr gr{i%2}" d="M{x:.0f},{890} q{rnd.uniform(-8,8):.0f},-{rnd.uniform(30,70):.0f} {rnd.uniform(10,24):.0f},-{rnd.uniform(60,110):.0f}" stroke="var(--ink)" stroke-width="3" fill="none"/>'
                    for i, x in enumerate([rnd.uniform(0, W) for _ in range(90)]))
    b.loop(".gr0", {"skewX": -6}, {"skewX": 6}, 1.3)
    b.loop(".gr1", {"skewX": 5}, {"skewX": -5}, 1.7)
    fg = ""
    if v.get("riders") or night:
        for i in range(5):
            fg += g(art.rider(), 0, 888 - (i % 2) * 22, 0.9 - (i % 2) * 0.3, cls=f"rd rd{i}")
            b.tw(f".rd{i}", {"x": -400 - i * 260}, {"x": 2200 - i * 200}, 0, duration=max(8, b.d), ease="none")
        b.loop(".lg1", {"rotation": -26}, {"rotation": 26}, 0.22)
        b.loop(".lg2", {"rotation": 26}, {"rotation": -26}, 0.22)
        b.loop(".rd", {"y": 0}, {"y": -8}, 0.22)
    else:
        fg += g(art.yurt(), 1450, 888, 0.55) + g(art.yurt(), 1680, 888, 0.4)
        fg += g(art.rider(), 0, 888, 0.75, cls="rd rd0")
        b.tw(".rd0", {"x": 300}, {"x": 900}, 0, duration=b.d, ease="none")
        b.loop(".lg1", {"rotation": -12}, {"rotation": 12}, 0.6)
        b.loop(".lg2", {"rotation": 12}, {"rotation": -12}, 0.6)
    smoke = ""
    if night:
        for i, x in enumerate((300, 900, 1600)):
            smoke += "".join(f'<circle class="sk sk{i}" cx="{x+rnd.uniform(-20,20):.0f}" cy="{760 - k*90}" r="{40+k*22}" fill="#2a1a1a" opacity="{0.5 - k*0.07:.2f}"/>' for k in range(6))
        b.loop(".sk", {"x": 0, "scale": 1}, {"x": 30, "scale": 1.08}, 2.5)
    kenburns(b, 1.0, 1.06)
    return svg(f'<g class="cam">{back}{smoke}<g fill="var(--ink)" color="var(--ink)">{fg}</g>{front}{grass}</g>' + dust(b, 50, "var(--glow)", (1, 3), (0, 500, W, H)), sky_defs(b))


def r_decree(b, v):
    b.pal = "ww1"
    b.tw(".dc-paper", {"scaleY": 0.05, "opacity": 0}, {"scaleY": 1, "opacity": 1}, 0.3, duration=1.3, ease="power3.out")
    for i in range(5):
        text_in(b, f".dc{i}", 1.2 + i * 0.35, 10, 0.5)
    b.tw(".dc-stamp", {"opacity": 0, "scale": 2.2, "rotation": -30}, {"opacity": 0.85, "scale": 1, "rotation": -12}, 3.2, duration=0.5, ease="power4.in")
    back = svg(f'<rect width="{W}" height="{H}" fill="url(#{b.id}-sky)"/><rect width="{W}" height="{H}" fill="#000" opacity=".4"/>' + dust(b, 50), sky_defs(b))
    kenburns(b, 1.0, 1.05)
    return back + ('<div class="dc-paper"><div class="dc0 dc-h">ЖАРЛЫҚ</div><div class="dc1 dc-d">1916 жыл · 25 маусым</div>'
                   '<div class="dc2 dc-p">Ресей империясындағы «бұратана» ер адамдар</div>'
                   '<div class="dc3 dc-p"><b>19–43 жас</b> аралығында</div>'
                   '<div class="dc4 dc-p">майдан маңындағы қара жұмысқа алынсын</div>'
                   '<div class="dc-stamp">1916</div></div>')


def medal(icon_kind, size=420, ring="#e0b84e"):
    return (f'<svg class="md" viewBox="-220 -220 440 440" width="{size}" height="{size}">'
            f'<circle r="210" fill="{ring}"/><circle r="186" fill="#2a1d14"/><circle r="176" fill="none" stroke="{ring}" stroke-width="3" stroke-dasharray="6 10"/>'
            f'<g fill="#f3e3c0" color="#f3e3c0" style="--bg:#2a1d14;--accent:#d6372b;--hi:#2a1d14">{g(art.icon(icon_kind), 0, 20, 1.05)}</g></svg>')


def r_hero(b, v):
    b.pal = "ww2" if v.get("icon") != "poet" else "kz"
    b.tw(".md", {"opacity": 0, "scale": 0.6, "rotation": -30}, {"opacity": 1, "scale": 1, "rotation": 0}, 0.3, duration=1.1, ease="back.out(1.5)")
    text_in(b, ".h-name", 0.7, 30)
    text_in(b, ".h-role", 1.1, 20)
    text_in(b, ".h-years", 1.4, 20)
    b.loop(".wave", {"skewY": -4}, {"skewY": 4}, 0.55)
    stars = "".join(g(art.star(rnd.uniform(6, 14)), rnd.uniform(0, W), rnd.uniform(0, H), 1, cls="hs") for _ in range(40))
    b.tw(".hs", {"opacity": 0.1}, {"opacity": 0.45}, 0, duration=1.2, stagger={"amount": 2, "from": "random"}, yoyo=True, repeat=max(1, int(b.d / 3)))
    back = svg(f'<rect width="{W}" height="{H}" fill="url(#{b.id}-sky)"/><rect width="{W}" height="{H}" fill="#000" opacity=".45"/><g fill="var(--glow)">{stars}</g>', sky_defs(b))
    kenburns(b, 1.0, 1.05)
    return back + (f'<div class="h-row">{medal(v["icon"])}<div class="h-text"><div class="h-name">{E(v["name"])}</div>'
                   f'<div class="h-role">{E(v["role"])}</div><div class="h-years">{E(v["years"])}</div></div></div>')


def r_heroes(b, v):
    b.pal = "kz"
    cards = ""
    for i, (name, place, ic) in enumerate(v["items"]):
        cards += f'<div class="hg hg{i}">{medal(ic, 250)}<div class="hg-n">{E(name)}</div><div class="hg-p">{E(place)}</div></div>'
        b.tw(f".hg{i}", {"opacity": 0, "y": 50}, {"opacity": 1, "y": 0}, 0.4 + i * 0.5, duration=0.8, ease="back.out(1.4)")
    back = svg(f'<rect width="{W}" height="{H}" fill="url(#{b.id}-sky)"/><rect width="{W}" height="{H}" fill="#000" opacity=".4"/>' + dust(b, 50, "var(--glow)"), sky_defs(b))
    kenburns(b, 1.0, 1.04)
    return back + f'<div class="hg-title">1916 жылғы көтеріліс басшылары</div><div class="hg-row">{cards}</div>'


def r_train(b, v):
    b.pal = "ww2"
    back, front = landscape(b, sun=(400, 600, 320), ground=860, seed=51)
    train = g(art.locomotive(), 1150, 0, 1) + "".join(g(art.wagon(), 820 - i * 250, 0, 1) for i in range(6))
    train = f'<g class="trn" transform="translate(0,820)">{train}</g>'
    b.tw(".trn", {"x": -300}, {"x": 700}, 2.0, duration=b.d - 2, ease="power1.in")
    b.loop(".wh", {"rotation": 0}, {"rotation": 180}, 0.6, at=2)
    puffs = "".join(f'<circle class="pf pf{i}" cx="1150" cy="620" r="{30+i*8}" fill="#d8d0c8" opacity=".5"/>' for i in range(6))
    for i in range(6):
        b.tw(f".pf{i}", {"x": 0, "y": 0, "opacity": 0.55}, {"x": -300 - i * 60, "y": -200 - i * 30, "opacity": 0}, i * 0.8, duration=max(2, b.d - i * 0.8), ease="none")
    platform = f'<rect x="-50" y="900" width="{W+100}" height="200" fill="var(--ink)"/><rect x="-50" y="890" width="{W+100}" height="14" fill="var(--mid)"/>'
    people = ""
    for i, (x, kind) in enumerate(((200, "woman"), (290, "child"), (420, "woman"), (560, "man"), (700, "woman"), (790, "child"), (1300, "woman"), (1440, "man"), (1560, "woman"), (1680, "child"))):
        people += g(art.person(kind), x, 1010, 1.05, cls=f"pp")
    arms = "".join(f'<g class="wv" transform="translate({x},{1010-150*1.05})"><path d="M0,0 L-28,-60" stroke="var(--ink)" stroke-width="10" stroke-linecap="round"/></g>' for x in (200, 420, 700, 1300, 1560))
    b.loop(".wv", {"rotation": -15}, {"rotation": 15}, 0.5)
    kenburns(b, 1.0, 1.05)
    return svg(f'<g class="cam">{back}{puffs}<g fill="var(--ink)" color="var(--ink)">{train}</g>{front}{platform}<g fill="#0a0708">{people}</g>{arms}</g>', sky_defs(b))


def r_home(b, v):
    b.pal = "kz"
    back, front = landscape(b, sun=(1500, 640, 300), ground=900, seed=61)
    fac = g(art.factory(), 560, 900, 1)
    smoke = "".join(f'<circle class="fsm fsm{i}" cx="{640 + (i%2)*94}" cy="{540 - (i%2)*40}" r="{30+i*6}" fill="#4a3a4a" opacity=".5"/>' for i in range(8))
    for i in range(8):
        b.tw(f".fsm{i}", {"x": 0, "y": 0, "opacity": 0.55}, {"x": 240 + i * 30, "y": -300 - i * 20, "opacity": 0}, i * 0.7, duration=max(2, b.d - i * 0.7), ease="none")
    wheat = "".join(f'<path class="wt wt{i%2}" d="M{x:.0f},960 q4,-50 0,-110" stroke="#e4b55a" stroke-width="4" fill="none"/><ellipse class="wt wt{i%2}" cx="{x:.0f}" cy="845" rx="6" ry="16" fill="#e4b55a"/>'
                    for i, x in enumerate([1100 + k * 14 for k in range(60)]))
    b.loop(".wt0", {"skewX": -5}, {"skewX": 5}, 1.4)
    b.loop(".wt1", {"skewX": 5}, {"skewX": -5}, 1.7)
    ppl = g(art.person("woman"), 1240, 960, 1.1) + g(art.person("child"), 1340, 960, 1.1) + g(art.person("woman"), 1500, 960, 1.15) + g(art.person("man"), 1660, 960, 1.0)
    kenburns(b, 1.0, 1.06)
    return svg(f'<g class="cam">{back}{smoke}<g fill="var(--ink)" color="var(--ink)">{fac}</g>{front}<g fill="var(--ink)">{ppl}</g>{wheat}</g>', sky_defs(b))


def r_forest(b, v):
    b.pal = "forest"
    sky = f'<rect width="{W}" height="{H}" fill="url(#{b.id}-sky)"/>'
    far = "".join(g(art.pine(rnd.uniform(220, 320)), x, 780, 1, extra=' opacity=".45"') for x in range(-40, 2000, 70))
    mid = "".join(g(art.pine(rnd.uniform(380, 520)), x, 860, 1, extra=' opacity=".75"') for x in range(30, 2000, 230))
    birches = "".join(g(art.birch(rnd.uniform(560, 760)), x, 960, 1) for x in (120, 380, 1580, 1820))
    ground = f'<path d="M-50,860 Q500,830 960,860 T1980,850 L1980,1100 L-50,1100 Z" fill="var(--mid)"/><path d="M-50,950 Q600,930 1980,960 L1980,1100 L-50,1100 Z" fill="var(--ink)"/>'
    fg = ""
    if v.get("dig"):
        fg += g(art.digger(), 820, 952, 1.15) + g(art.digger(), 1250, 952, 1.15, flip=True)
        fg += '<ellipse cx="1030" cy="955" rx="170" ry="26" fill="#1d150c"/>'
        b.loop(".dig", {"rotation": -10}, {"rotation": 22}, 0.7)
    medal_html = ""
    if v.get("medal"):
        fg += '<g class="cap" transform="translate(1030,945)"><rect x="-26" y="-9" width="52" height="18" rx="9" fill="#2b2b2b"/><circle r="40" fill="#ffe7a0" opacity=".35" class="capg"/></g>'
        b.loop(".capg", {"scale": 0.7, "opacity": 0.2}, {"scale": 1.3, "opacity": 0.5}, 0.8, svgOrigin="1030 945")
        medal_html = ('<div class="slip"><div class="slip-t">Тегі, аты, әкесінің аты</div><div class="slip-t">Туған жылы: 19__</div>'
                      '<div class="slip-t">Туған жері: ______ ауылы</div><div class="slip-t">Туыстарының мекенжайы: ______</div></div>')
        b.tw(".slip", {"opacity": 0, "y": 40, "rotation": 4}, {"opacity": 1, "y": 0, "rotation": -2}, 1.0, duration=1.0, ease="power3.out")
    rays = "".join(f'<path d="M{700 + i*160},-50 L{560 + i*200},1100 L{620 + i*200},1100 Z" fill="#fff8d0" opacity=".06" class="ray"/>' for i in range(6))
    b.loop(".ray", {"opacity": 0.03}, {"opacity": 0.09}, 2.4)
    kenburns(b, 1.0, 1.07, -30, 0)
    return svg(f'<g class="cam">{sky}{rays}<g fill="var(--far)">{far}</g><g fill="var(--mid)">{mid}</g>{ground}{birches}<g fill="var(--ink)" color="var(--ink)">{fg}</g></g>'
               + dust(b, 60, "#fff8d0", (1, 3), drift=40, op=0.4), sky_defs(b)) + medal_html


def r_reburial(b, v):
    b.pal = "dawn"
    back, front = landscape(b, sun=(960, 760, 520), ground=900, seed=71)
    graves = "".join(g(art.grave_mound(150), x, 905, 1) for x in (320, 520, 1400, 1600))
    flowers = "".join(f'<circle cx="{x+rnd.uniform(-60,60):.0f}" cy="{905+rnd.uniform(-6,4):.0f}" r="7" fill="#d6372b"/>' for x in (320, 520, 1400, 1600) for _ in range(5))
    ppl = "".join(g(art.mourner(), x, 1000, 1.05) for x in (700, 800, 1120, 1220))
    kenburns(b, 1.0, 1.05)
    b.loop(".fl", {"scaleY": 0.86}, {"scaleY": 1.12}, 0.25)
    return svg(f'<g class="cam">{back}<g fill="var(--ink)" color="var(--ink)">{g(art.obelisk(), 960, 905, 1)}{graves}</g>{flowers}{front}<g fill="#0c0c14">{ppl}</g></g>' + dust(b, 40, "#fff", (1, 3)), sky_defs(b))


def r_search(b, v):
    b.pal = "night"
    b.tw(".sr-win", {"opacity": 0, "y": 40, "scale": 0.95}, {"opacity": 1, "y": 0, "scale": 1}, 0.3, duration=0.9, ease="power3.out")
    b.tw(".sr-type", {"width": "0ch"}, {"width": "22ch"}, 1.3, duration=2.2, ease="steps(22)")
    b.tw(".sr-res", {"opacity": 0, "y": 16}, {"opacity": 1, "y": 0}, 3.8, duration=0.5, stagger=0.25)
    back = svg(f'<rect width="{W}" height="{H}" fill="url(#{b.id}-sky)"/>' + dust(b, 40, "#9fb4ff", (1, 3)), sky_defs(b))
    rows = "".join(f'<div class="sr-res"><span class="sr-av"></span><span class="sr-bar" style="width:{w}px"></span><span class="sr-bar s" style="width:{w2}px"></span></div>'
                   for w, w2 in ((420, 220), (360, 260), (460, 180), (390, 240)))
    return back + (f'<div class="sr-win"><div class="sr-top"><i></i><i></i><i></i><span>obd-memorial.ru</span></div>'
                   f'<div class="sr-body"><div class="sr-h">Мемориал — деректер базасы</div>'
                   f'<div class="sr-box"><span class="sr-type">Тегі · Аты · Туған жылы</span></div>{rows}'
                   f'<div class="sr-foot">Сондай-ақ: «Атамның аманаты» қоғамдық бірлестігі</div></div></div>')


def r_bomb(b, v):
    b.pal = "ww2"
    sky = f'<rect width="{W}" height="{H}" fill="url(#{b.id}-sky)"/>'
    r = random.Random(5)
    city = "".join(f'<rect x="{x}" y="{900 - h:.0f}" width="{w}" height="{h:.0f}"/>' for x, w, h in [(x, r.randint(40, 90), r.uniform(40, 170)) for x in range(0, 1960, 70)])
    cloud = g(art.mushroom(), 1150, 1160, 1.15, cls="mush")
    b.tw(".flash", {"opacity": 0}, {"opacity": 0.9}, 0.6, duration=0.15, ease="power4.in")
    b.tw(".flash", {"opacity": 0.9}, {"opacity": 0}, 0.75, duration=2.2, ease="power2.out", immediateRender=False)
    b.tw(".mush", {"scale": 0.3, "y": 120, "opacity": 0}, {"scale": 1.1, "y": 0, "opacity": 1}, 0.8, duration=min(7, b.d - 1), ease="power2.out", transformOrigin="50% 100%")
    text_in(b, ".bm-lab", 2.0)
    defs = sky_defs(b, f'<radialGradient id="mgrad" cx=".5" cy=".3" r=".7"><stop offset="0" stop-color="#fff0c8"/><stop offset=".5" stop-color="#f0a05a"/><stop offset="1" stop-color="#7a4636"/></radialGradient>')
    kenburns(b, 1.0, 1.05)
    return svg(f'<g class="cam">{sky}{cloud}<g fill="var(--ink)">{city}</g><rect x="-50" y="900" width="{W+100}" height="200" fill="var(--ink)"/></g>'
               f'<rect class="flash" width="{W}" height="{H}" fill="#fff8e0" opacity="0"/>', defs) + \
        '<div class="bm-lab">1945 · 6 және 9 тамыз · Хиросима мен Нагасаки</div>'


TABLE = [
    ("", "БІРІНШІ СОҒЫС", "ЕКІНШІ СОҒЫС"),
    ("Жылдары", "1914 – 1918", "1939 – 1945"),
    ("Ұзақтығы", "4 жылдан астам", "6 жыл"),
    ("Кім жеңді", "Антанта", "Одақтастар"),
    ("Қаза тапқандар", "15–22 млн", "70–85 млн"),
    ("Кім көп өлді", "Көбіне сарбаздар", "Көбіне бейбіт халық"),
    ("Соғыс түрі", "Окоп, бір орында", "Жылдам: танк, ұшақ"),
    ("Жаңа қару", "Газ, танк, пулемет", "Атом бомбасы"),
    ("Қазақтар", "1916: жарлық, көтеріліс", "~1,2 млн майданға, 600 мыңнан астамы оралмады"),
]


def r_table(b, v):
    b.pal = "dark"
    upto, prev = v["upto"], v.get("_prev", 0)
    rows = ""
    for i, (a, x, y) in enumerate(TABLE):
        if i > upto:
            break
        cls = "tr hd" if i == 0 else "tr"
        rows += f'<div class="{cls} tr{i}"><div class="ta">{E(a)}</div><div class="tx">{E(x)}</div><div class="ty">{E(y)}</div></div>'
        if i >= prev:
            b.tw(f".tr{i}", {"opacity": 0, "x": -30}, {"opacity": 1, "x": 0}, 0.3 + (i - prev) * 0.4, duration=0.6, ease="power3.out")
    back = svg(f'<rect width="{W}" height="{H}" fill="url(#{b.id}-sky)"/>' + dust(b, 30, "var(--glow)", (1, 2.5), drift=20, op=0.4), sky_defs(b))
    return back + f'<div class="tb">{rows}</div>'


def r_end(b, v):
    b.pal = "dark"
    text_in(b, ".e-t", 0.6, 20, 1.6)
    b.loop(".fl", {"scaleY": 0.86}, {"scaleY": 1.12}, 0.25)
    flame = f'<g fill="#2a221e">{g(art.obelisk(), 960, 1080, 0.9)}</g>'
    back = svg(f'<rect width="{W}" height="{H}" fill="url(#{b.id}-sky)"/>{flame}' + dust(b, 70, "var(--glow)", (1, 3), drift=20, op=0.6), sky_defs(b))
    kenburns(b, 1.0, 1.05)
    lines = "<br>".join(E(x) for x in v["t"].split("\n"))
    return back + f'<div class="e-t">{lines}</div>'


def r_credits(b, v):
    b.pal = "dark"
    text_in(b, ".cr", 0.4, 20, 1.2)
    back = svg(f'<rect width="{W}" height="{H}" fill="var(--sky2)"/>' + dust(b, 40, "var(--glow)", (1, 2.5), drift=20, op=0.4))
    return back + ('<div class="cr"><div class="cr-h">ЕКІ СОҒЫС</div>'
                   '<div>Дауыс: ISSAI KazakhTTS2 (CC BY 4.0), Piper TTS</div>'
                   '<div>Карта: Natural Earth (қоғамдық игілік)</div>'
                   '<div>Дыбыс эффектілері: Pixabay · Музыка: түпнұсқа</div>'
                   '<div>Дерек көздері: gov.kz, e-history.kz, 24.kz, inform.kz, tengrinews.kz, Britannica, Wikipedia</div>'
                   '<div class="cr-n">Сандар шамамен берілген: дерек көздерінде олар әртүрлі.</div></div>')


R = {"card": r_card, "title": r_title, "yurt": r_yurt, "map": r_map, "date": r_date, "march": r_march, "trench": r_trench,
     "tech": r_tech, "battle": r_battle, "stat": r_stat, "compare": r_compare, "winner": r_winner, "list": r_list,
     "note": r_note, "steppe": r_steppe, "decree": r_decree, "hero": r_hero, "heroes": r_heroes, "train": r_train,
     "home": r_home, "forest": r_forest, "reburial": r_reburial, "search": r_search, "bomb": r_bomb, "table": r_table,
     "end": r_end, "credits": r_credits}

SFX = {"card": ("whoosh", 0.35), "title": ("riser", 0.25), "date": ("impact-bass-1", 0.3), "map": ("whoosh-short", 0.3),
       "stat": ("click", 0.25), "hero": ("chime", 0.25), "heroes": ("chime", 0.25), "winner": ("sparkle", 0.3),
       "tech": ("pop", 0.25), "list": ("pop", 0.2), "table": ("pop", 0.2), "note": ("ping", 0.2), "decree": ("impact-bass-1", 0.25),
       "end": ("chime", 0.3), "compare": ("pop", 0.25), "bomb": ("impact-bass-1", 0.4), "battle": ("whoosh", 0.25)}

import subprocess
SFXLEN = {f: float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                   os.path.join(ROOT, "assets", "sfx", f + ".mp3")], capture_output=True, text=True).stdout)
          for f in {v[0] for v in SFX.values()}}

# ------------------------------------------------------------------ CSS
CSS = """
#root{position:absolute;inset:0;overflow:hidden;font-family:'PT Sans',sans-serif;color:var(--text)}
.beat{position:absolute;inset:0;overflow:hidden;color:var(--text)}
.in{position:absolute;inset:0;background:var(--sky2)}
.art{position:absolute;left:0;top:0;width:1920px;height:1080px}
.cam{transform-origin:960px 600px}
.t-box,.d-box{position:absolute;left:0;right:0;top:230px;text-align:center;text-shadow:0 4px 24px rgba(0,0,0,.55)}
.t-main{font-family:'Oswald',sans-serif;font-weight:700;font-size:118px;letter-spacing:.04em;line-height:1.05;color:var(--text)}
.t-rule,.d-rule,.k-line{width:420px;height:6px;margin:28px auto;background:var(--accent);transform-origin:50% 50%}
.t-sub{font-size:44px;max-width:1400px;margin:0 auto;color:var(--text)}
.d-box{top:170px}
.d-year{font-family:'Oswald',sans-serif;font-weight:700;font-size:230px;line-height:1;color:var(--text)}
.d-sub{font-family:'Oswald',sans-serif;font-size:58px;letter-spacing:.03em;color:var(--text)}
.k-wrap{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center}
.k-num{font-family:'Oswald',sans-serif;font-size:46px;letter-spacing:.3em;color:var(--accent)}
.k-title{font-family:'Oswald',sans-serif;font-weight:700;font-size:112px;color:var(--text);text-align:center;max-width:1600px;line-height:1.1}
.photo{position:absolute;left:820px;top:150px}
.ph-in{padding:14px;background:#efe3c8;box-shadow:0 20px 60px rgba(0,0,0,.6)}
.legend{position:absolute;left:70px;top:60px;background:rgba(20,14,8,.78);padding:22px 30px;border-radius:14px;font-size:34px;font-weight:700;color:#fbf1dc}
.legend div{display:flex;align-items:center;gap:16px;margin:6px 0}
.legend i{display:inline-block;width:34px;height:34px;border-radius:6px}
.lg-note{font-size:28px;font-weight:400;opacity:.8}
.mlab{font-size:32px;font-family:'Oswald',sans-serif;font-weight:700;fill:#fff8e8;text-anchor:middle;paint-order:stroke;stroke:#1b120a;stroke-width:6px;letter-spacing:.04em}
.mlab.big{font-size:58px;fill:#fff1c0}
.mlab.sub{font-size:30px;font-weight:400}
.mlab.red{fill:#ffd0c0;font-size:30px}
.tc-row{position:absolute;left:0;right:0;top:210px;display:flex;justify-content:center;gap:50px}
.tc{width:360px;padding:30px 0 34px;background:var(--bg);border-radius:22px;text-align:center;box-shadow:0 20px 50px rgba(0,0,0,.45);--bg:var(--bg)}
.tc-l{font-family:'Oswald',sans-serif;font-weight:700;font-size:52px;color:var(--ink);margin-top:10px}
.s-box{position:absolute;left:0;right:0;top:120px;text-align:center}
.s-label{font-size:46px;font-weight:700;color:var(--text);opacity:.95}
.s-num{font-family:'Oswald',sans-serif;font-weight:700;font-size:210px;line-height:1.1;color:var(--glow);text-shadow:0 6px 40px rgba(0,0,0,.5)}
.s-unit{font-family:'Oswald',sans-serif;font-size:60px;color:var(--text);margin-top:-10px}
.s-grid{margin:28px auto 0;display:flex;flex-wrap:wrap;justify-content:center;gap:10px}
.cp-row{position:absolute;left:0;right:0;top:120px;display:flex;justify-content:center;gap:120px}
.cp{width:720px;text-align:center}
.cp-y{font-family:'Oswald',sans-serif;font-size:64px;font-weight:700}
.cp-n{font-family:'Oswald',sans-serif;font-size:90px;font-weight:700;color:var(--glow)}
.cp-g{display:flex;flex-wrap:wrap;justify-content:center;gap:8px;margin:24px auto 0;max-width:560px}
.cp-note{position:absolute;left:0;right:0;top:820px;text-align:center;font-size:34px;opacity:.85}
.w-box{position:absolute;left:0;right:0;top:60px;text-align:center}
.w-win{position:relative;display:inline-block}
.laurel{display:block;margin:0 auto 0}
.w-tag{font-family:'Oswald',sans-serif;font-size:40px;letter-spacing:.25em;color:var(--glow)}
.w-name{font-family:'Oswald',sans-serif;font-weight:700;font-size:150px;line-height:1.05;color:var(--text)}
.w-sub{font-size:40px;color:var(--text);opacity:.9}
.w-lose{margin-top:40px;font-size:40px;color:var(--text);opacity:.75}
.l-box{position:absolute;left:240px;top:130px;right:240px}
.l-title{font-family:'Oswald',sans-serif;font-weight:700;font-size:86px;color:var(--glow);margin-bottom:26px}
.l-box ul{list-style:none}
.li{font-size:52px;font-weight:700;margin:16px 0;padding-left:34px;border-left:8px solid var(--accent)}
.n-card{position:absolute;left:260px;right:260px;top:200px;padding:56px 70px;background:rgba(251,241,220,.95);color:#1c140c;border-radius:24px;border-left:14px solid var(--accent);box-shadow:0 30px 80px rgba(0,0,0,.6)}
.n-t{font-family:'Oswald',sans-serif;font-weight:700;font-size:72px;margin-bottom:18px}
.n-b{font-size:44px;line-height:1.35}
.dc-paper{position:absolute;left:560px;top:70px;width:800px;height:780px;padding:60px 70px;background:#ead7ae;color:#2a1a0c;border-radius:10px;box-shadow:0 30px 80px rgba(0,0,0,.6);transform-origin:50% 0%;text-align:center}
.dc-h{font-family:'Oswald',sans-serif;font-weight:700;font-size:96px;letter-spacing:.12em}
.dc-d{font-size:40px;margin:6px 0 40px;font-style:italic}
.dc-p{font-size:44px;line-height:1.35;margin:10px 0}
.dc-stamp{position:absolute;right:40px;bottom:30px;width:150px;height:150px;border:8px solid #9a2a1e;border-radius:50%;color:#9a2a1e;font-family:'Oswald',sans-serif;font-weight:700;font-size:46px;display:flex;align-items:center;justify-content:center}
.h-row{position:absolute;left:170px;right:120px;top:150px;display:flex;align-items:center;gap:80px}
.h-text{flex:1}
.h-name{font-family:'Oswald',sans-serif;font-weight:700;font-size:100px;line-height:1.05;color:var(--text)}
.h-role{font-size:46px;margin-top:18px;color:var(--glow);font-weight:700}
.h-years{font-family:'Oswald',sans-serif;font-size:56px;margin-top:14px;opacity:.85}
.hg-title{position:absolute;left:0;right:0;top:90px;text-align:center;font-family:'Oswald',sans-serif;font-weight:700;font-size:64px;color:var(--glow)}
.hg-row{position:absolute;left:0;right:0;top:220px;display:flex;justify-content:center;gap:56px}
.hg{width:360px;text-align:center}
.hg-n{font-family:'Oswald',sans-serif;font-weight:700;font-size:44px;line-height:1.1;margin-top:18px}
.hg-p{font-size:34px;opacity:.85}
.slip{position:absolute;right:150px;top:140px;width:560px;padding:34px 40px;background:#efe3c3;color:#2a1a0c;border-radius:6px;box-shadow:0 20px 60px rgba(0,0,0,.55);font-size:36px;line-height:1.6}
.sr-win{position:absolute;left:310px;top:90px;width:1300px;height:740px;background:#f5f3ee;border-radius:22px;overflow:hidden;box-shadow:0 30px 90px rgba(0,0,0,.6);color:#1c1c24}
.sr-top{height:66px;background:#d9d6cf;display:flex;align-items:center;gap:12px;padding:0 24px;font-size:30px}
.sr-top i{width:18px;height:18px;border-radius:50%;background:#9b958a;display:inline-block}
.sr-top span{margin-left:20px;background:#fff;border-radius:10px;padding:4px 20px}
.sr-body{padding:40px 70px}
.sr-h{font-family:'Oswald',sans-serif;font-weight:700;font-size:58px;margin-bottom:24px}
.sr-box{border:4px solid #3a5a8a;border-radius:14px;padding:16px 24px;font-size:40px;margin-bottom:26px}
.sr-type{display:inline-block;overflow:hidden;white-space:nowrap;vertical-align:bottom;border-right:3px solid #3a5a8a}
.sr-res{display:flex;align-items:center;gap:20px;margin:14px 0}
.sr-av{width:54px;height:54px;border-radius:50%;background:#c9c2b4}
.sr-bar{height:22px;border-radius:11px;background:#c9c2b4}
.sr-bar.s{background:#e2ddd3}
.sr-foot{margin-top:22px;font-size:32px;color:#3a5a8a;font-weight:700}
.bm-lab{position:absolute;left:0;right:0;top:110px;text-align:center;font-family:'Oswald',sans-serif;font-size:54px;color:#fff3e0;text-shadow:0 4px 20px rgba(0,0,0,.6)}
.tb{position:absolute;left:120px;right:120px;top:60px}
.tr{display:grid;grid-template-columns:330px 1fr 1fr;gap:20px;padding:12px 24px;border-bottom:2px solid rgba(255,240,210,.18);font-size:36px;align-items:center}
.tr.hd{font-family:'Oswald',sans-serif;font-weight:700;font-size:44px;color:var(--glow);border-bottom:4px solid var(--accent)}
.ta{font-weight:700;opacity:.8}
.tx,.ty{font-weight:700}
.e-t{position:absolute;left:0;right:0;top:250px;text-align:center;font-family:'Oswald',sans-serif;font-weight:700;font-size:110px;line-height:1.2;color:var(--text);text-shadow:0 6px 30px rgba(0,0,0,.6)}
.cr{position:absolute;left:200px;right:200px;top:200px;text-align:center;font-size:36px;line-height:1.7;color:var(--text)}
.cr-h{font-family:'Oswald',sans-serif;font-weight:700;font-size:96px;color:var(--glow);margin-bottom:30px}
.cr-n{margin-top:26px;opacity:.75}
"""


# ------------------------------------------------------------------ timeline
def plan():
    """Lay out every line and beat on the global clock."""
    t = 0.0
    chapters = []
    for ci, ch in enumerate(CHAPTERS):
        c0 = t
        beats, lines = [], []
        local = 0.0
        if ci > 0:
            beats.append({"t": 0.0, "v": {"k": "card", "num": f"{ci}-БӨЛІМ", "t": ch["title"]}})
            local = CARD
        prev_upto = 0
        for li, ln in enumerate(ch["lines"]):
            if "v" in ln:
                v = dict(ln["v"])
                if v["k"] == "table":
                    v["_prev"] = prev_upto + (1 if prev_upto else 0)
                    prev_upto = v["upto"]
                if beats:
                    local += PREROLL
                beats.append({"t": local, "v": v})
            name = f"{ch['id']}_{li:02d}"
            d = TIMING[name]
            lines.append({"name": name, "t": local, "d": d, "who": ln["who"], "text": ln["t"]})
            local += d + GAP
        if ci == len(CHAPTERS) - 1:
            beats.append({"t": local + 3.0, "v": {"k": "credits"}})
            local += 3.0 + CREDITS
        else:
            local += TAIL
        chapters.append({"id": ch["id"], "start": c0, "dur": local, "beats": beats, "lines": lines})
        t += local
    return chapters, t


def build_chapter(ch):
    cid = ch["id"]
    parts, js = [], []
    nb = len(ch["beats"])
    for i, bt in enumerate(ch["beats"]):
        end = ch["beats"][i + 1]["t"] + XF if i + 1 < nb else ch["dur"]
        b = Beat(cid, i, bt["t"], end - bt["t"], bt["v"])
        b.pal = "ww1"
        body = R[bt["v"]["k"]](b, bt["v"])
        # fade in (the first beat of a chapter fades from black too)
        if not (cid == "ch1" and i == 0):
            b.tw(".in", {"opacity": 0}, {"opacity": 1}, 0, duration=XF, ease="power1.out")
        keep = []
        for line in b.js:
            m = re.match(r'(?:\(function\(\)\{.*?querySelector\(|tl\.fromTo\()"#[\w-]+ \.([\w-]+)', line)
            if m:
                c = m.group(1)
                if c == "cam" and 'class="cam"' not in body:
                    line = line.replace(" .cam\"", " .art\"", 1)
                elif c not in ("in", "art") and not re.search(r'class="[^"]*\b' + c + r'\b', body):
                    continue
            keep.append(line)
        b.js = keep
        parts.append(f'<div id="{b.id}" class="clip beat" data-start="{b.t:.3f}" data-duration="{b.d:.3f}" data-track-index="1" '
                     f'style="z-index:{i+1};{pal_vars(b.pal)}" data-layout-allow-overflow data-layout-allow-overlap>'
                     f'<div class="in">{body}</div></div>')
        js.extend(b.js)
    if True:  # fade the whole chapter out at its end
        js.append(f'tl.fromTo("#{cid}-fade", {{opacity:0}}, {{opacity:1, duration:{min(0.9, TAIL):.2f}}}, {ch["dur"] - min(0.9, TAIL) - 0.05:.3f});')
    fade = f'<div id="{cid}-fade" data-layout-ignore style="position:absolute;inset:0;background:#000;opacity:0;z-index:999"></div>'
    doc = (f'<template>\n<style>\n{FONTS}\n{CSS}\n</style>\n'
           f'<div id="root" data-composition-id="{cid}" data-width="{W}" data-height="{H}" data-duration="{ch["dur"]:.3f}">\n'
           + "\n".join(parts) + f"\n{fade}\n</div>\n<script>\nconst tl = gsap.timeline({{ paused: true }});\n"
           + "\n".join(js) + f'\nwindow.__timelines["{cid}"] = tl;\n</script>\n</template>\n')
    open(os.path.join(ROOT, "compositions", f"{cid}.html"), "w").write(doc)


def split_caption(text, maxlen=78):
    """Split a line into caption chunks at sentence, then comma, boundaries."""
    sents = re.split(r"(?<=[.!?…])\s+", text.strip())
    out = []
    for s in sents:
        while len(s) > maxlen:
            cut = max(s.rfind(", ", 0, maxlen), s.rfind(" — ", 0, maxlen), s.rfind(": ", 0, maxlen))
            if cut < 25:
                cut = s.rfind(" ", 0, maxlen)
            out.append(s[:cut + 1].strip())
            s = s[cut + 1:].strip()
        if s:
            out.append(s)
    # merge very short tails
    merged = []
    for c in out:
        if merged and len(merged[-1]) + len(c) < 60:
            merged[-1] += " " + c
        else:
            merged.append(c)
    return merged


def build_captions(chapters, total):
    clips, js = [], []
    n = 0
    for ch in chapters:
        for ln in ch["lines"]:
            chunks = split_caption(ln["text"])
            weights = [len(c) for c in chunks]
            tot = sum(weights)
            t = ch["start"] + ln["t"]
            for c, w in zip(chunks, weights):
                d = ln["d"] * w / tot
                who = "Ата" if ln["who"] == "A" else "Ерлан"
                cls = "ca" if ln["who"] == "A" else "ce"
                clips.append(f'<div id="cap{n}" class="clip cap {cls}" data-start="{t:.3f}" data-duration="{d + (0.35 if c is chunks[-1] else 0):.3f}" data-track-index="2">'
                             f'<div class="cap-in"><b>{who}:</b> {E(c)}</div></div>')
                js.append(f'tl.fromTo("#cap{n} .cap-in",{{opacity:0,y:10}},{{opacity:1,y:0,duration:0.18}},{t:.3f});')
                t += d
                n += 1
    css = """
#root{position:absolute;inset:0;font-family:'PT Sans',sans-serif}
.cap{position:absolute;left:160px;right:160px;bottom:56px;display:flex;justify-content:center}
.cap-in{max-width:1600px;padding:12px 30px 14px;background:rgba(10,8,6,.72);border-radius:14px;color:#fffaf0;font-size:44px;line-height:1.25;font-weight:700;text-align:center}
.ca b{color:#f2c14e}
.ce b{color:#8fd3ff}
"""
    doc = (f'<template>\n<style>\n{FONTS}\n{css}\n</style>\n<div id="root" data-composition-id="captions" data-width="{W}" data-height="{H}" data-duration="{total:.3f}">\n'
           + "\n".join(clips) + '\n</div>\n<script>\nconst tl = gsap.timeline({ paused: true });\n' + "\n".join(js)
           + '\nwindow.__timelines["captions"] = tl;\n</script>\n</template>\n')
    open(os.path.join(ROOT, "compositions", "captions.html"), "w").write(doc)
    return n


def build_index(chapters, total):
    hosts, audio = [], []
    for ch in chapters:
        hosts.append(f'<div id="{ch["id"]}" data-composition-id="{ch["id"]}" data-composition-src="compositions/{ch["id"]}.html" '
                     f'data-start="{ch["start"]:.3f}" data-duration="{ch["dur"]:.3f}" data-track-index="0" data-track-kind="graphics" '
                     f'data-width="{W}" data-height="{H}"></div>')
        for ln in ch["lines"]:
            audio.append(f'<audio id="v-{ln["name"]}" src="assets/voice/{ln["name"]}.wav" data-start="{ch["start"] + ln["t"]:.3f}" '
                         f'data-duration="{ln["d"]:.3f}" data-track-index="4" data-volume="1"></audio>')
    # sound effects on picture changes, never overlapping on one lane
    sfx, last_end, n = [], {5: -1, 6: -1}, 0
    for ch in chapters:
        for bt in ch["beats"]:
            k = bt["v"]["k"]
            if k not in SFX:
                continue
            f, vol = SFX[k]
            at = ch["start"] + bt["t"] + 0.05
            lane = 5 if last_end[5] < at else 6
            if last_end[lane] >= at:
                continue
            sfx.append(f'<audio id="sfx{n}" src="assets/sfx/{f}.mp3" data-start="{at:.3f}" data-duration="{SFXLEN[f]:.3f}" data-track-index="{lane}" data-volume="{vol}"></audio>')
            last_end[lane] = at + 3.0
            n += 1
    doc = f"""<!doctype html>
<html lang="kk">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1920, height=1080" />
    <script src="assets/gsap.min.js"></script>
    <style>
{FONTS}
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ margin: 0; width: 1920px; height: 1080px; overflow: hidden; background: #000; }}
      #root {{ position: relative; width: 100%; height: 100%; font-family: 'PT Sans', sans-serif; }}
      #vignette {{ position: absolute; inset: 0; z-index: 50; pointer-events: none;
        background: radial-gradient(ellipse at 50% 45%, rgba(0,0,0,0) 55%, rgba(0,0,0,.55) 100%); }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{total:.3f}" data-width="1920" data-height="1080">
{chr(10).join(hosts)}
      <div id="vignette"></div>
      <div id="captions" data-composition-id="captions" data-composition-src="compositions/captions.html" data-start="0" data-duration="{total:.3f}" data-track-index="2" data-track-kind="captions" data-width="1920" data-height="1080" style="z-index:60"></div>
      <audio id="music" src="assets/music/score.mp3" data-start="0" data-duration="{total:.3f}" data-track-index="3" data-volume="0.3" data-timeline-role="music" data-fade-in="3" data-fade-out="6"></audio>
{chr(10).join(audio)}
{chr(10).join(sfx)}
    </div>
    <script>
      const tl = gsap.timeline({{ paused: true }});
      window.__timelines["main"] = tl;
    </script>
  </body>
</html>
"""
    open(os.path.join(ROOT, "index.html"), "w").write(doc)
    return len(sfx)


if __name__ == "__main__":
    chapters, total = plan()
    os.makedirs(os.path.join(ROOT, "compositions"), exist_ok=True)
    for ch in chapters:
        build_chapter(ch)
    ncap = build_captions(chapters, total)
    nsfx = build_index(chapters, total)
    json.dump([{"id": c["id"], "start": round(c["start"], 2), "dur": round(c["dur"], 2),
                "beats": [(round(c["start"] + b["t"], 2), b["v"]["k"]) for b in c["beats"]]} for c in chapters],
              open(os.path.join(HERE, "plan.json"), "w"), ensure_ascii=False, indent=1)
    print(f"total {total:.1f}s ({total/60:.1f} min), {sum(len(c['beats']) for c in chapters)} beats, {ncap} captions, {nsfx} sfx")
