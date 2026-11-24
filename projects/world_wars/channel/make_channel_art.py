# -*- coding: utf-8 -*-
"""Make YouTube channel art for «Тарих сөйлейді»: banner 2560x1440 and avatar 800x800.

Usage: python3 projects/world_wars/channel/make_channel_art.py
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
VIDEO = os.path.join(HERE, "..", "video")
sys.path.insert(0, os.path.join(VIDEO, "tools"))
import art
from art import g

fonts = open(os.path.join(VIDEO, "assets", "fonts.css")).read().replace("url('assets/fonts/", "url('../video/assets/fonts/")


def hills(color, base, amp, w, step, seed):
    import random
    r = random.Random(seed)
    pts = [f"-40,{base+900}", f"-40,{base}"]
    x = -40
    while x < w + step:
        x += step
        pts.append(f"{x},{base - r.uniform(0, amp):.0f}")
    pts.append(f"{w+step},{base+900}")
    return f'<polygon points="{" ".join(pts)}" fill="{color}"/>'


def banner():
    W, H = 2560, 1440
    ground = 1010
    figs = (g(art.yurt(), 560, ground, 0.9) + g(art.rider(), 820, ground, 0.85) +
            "".join(g(art.soldier("ww1"), 1640 + i * 70, ground, 0.42) for i in range(4)) +
            g(art.tank2(), 2080, ground, 0.6) + g(art.biplane(), 1900, 520, 0.8))
    stars = "".join(f'<circle cx="{(i*397)%W}" cy="{(i*131)%560}" r="{1.5+(i%3)}" fill="#fff" opacity=".55"/>' for i in range(90))
    svg = f'''<svg viewBox="0 0 {W} {H}" width="{W}" height="{H}">
<defs><linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1b1f3f"/><stop offset=".55" stop-color="#6b4a78"/><stop offset="1" stop-color="#f2a65e"/></linearGradient>
<radialGradient id="sun"><stop offset="0" stop-color="#ffc36b" stop-opacity=".95"/><stop offset="1" stop-color="#ffc36b" stop-opacity="0"/></radialGradient></defs>
<rect width="{W}" height="{H}" fill="url(#sky)"/>{stars}
<circle cx="1280" cy="960" r="560" fill="url(#sun)"/>
{hills("#7a5a86", ground - 120, 90, W, 180, 3)}{hills("#3b2a4d", ground - 40, 50, W, 240, 4)}
<g fill="#1c1426" color="#1c1426" style="--hi:#3b2a4d;--glow:#ffb347;--accent:#d6372b;--bg:#1c1426">{figs}</g>
<rect y="{ground}" width="{W}" height="{H-ground}" fill="#1c1426"/>
</svg>'''
    return W, H, f'''<div style="position:relative;width:{W}px;height:{H}px">{svg}
<div style="position:absolute;left:0;right:0;top:500px;text-align:center;color:#fff6e6;text-shadow:0 6px 30px rgba(0,0,0,.6)">
<div style="font-family:Oswald;font-weight:700;font-size:150px;letter-spacing:.06em;line-height:1">ТАРИХ СӨЙЛЕЙДІ</div>
<div style="width:520px;height:8px;background:#f2c14e;margin:26px auto"></div>
<div style="font-family:'PT Sans';font-weight:700;font-size:52px">Тарихты мультфильммен түсіндіреміз · қазақ тілінде</div>
</div></div>'''


def avatar():
    S = 800
    svg = f'''<svg viewBox="0 0 {S} {S}" width="{S}" height="{S}">
<defs><linearGradient id="a" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2a2550"/><stop offset="1" stop-color="#f2a65e"/></linearGradient>
<radialGradient id="s"><stop offset="0" stop-color="#ffc36b"/><stop offset="1" stop-color="#ffc36b" stop-opacity="0"/></radialGradient></defs>
<rect width="{S}" height="{S}" fill="url(#a)"/><circle cx="400" cy="560" r="300" fill="url(#s)"/>
<g fill="#1c1426" style="--hi:#3b2a4d;--glow:#ffb347">{g(art.yurt(), 400, 640, 1.25)}</g>
<rect y="636" width="{S}" height="170" fill="#1c1426"/></svg>'''
    return S, S, f'''<div style="position:relative;width:{S}px;height:{S}px">{svg}
<div style="position:absolute;left:0;right:0;top:110px;text-align:center;font-family:Oswald;font-weight:700;color:#fff6e6;font-size:118px;line-height:1.02;letter-spacing:.04em;text-shadow:0 6px 24px rgba(0,0,0,.5)">ТАРИХ<br>СӨЙЛЕЙДІ</div>
<div style="position:absolute;left:0;right:0;top:690px;text-align:center;font-family:'PT Sans';font-weight:700;color:#f2c14e;font-size:44px">мультфильм · қазақша</div></div>'''


for name, (w, h, body) in {"banner_2560x1440": banner(), "avatar_800x800": avatar()}.items():
    page = f'<!doctype html><html><head><meta charset="utf-8"><style>{fonts} *{{margin:0;padding:0}} body{{width:{w}px;height:{h}px;overflow:hidden}}</style></head><body>{body}</body></html>'
    open(os.path.join(HERE, name + ".html"), "w").write(page)
print("ok")
