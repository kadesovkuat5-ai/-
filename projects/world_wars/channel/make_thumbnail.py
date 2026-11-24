# -*- coding: utf-8 -*-
"""YouTube thumbnail (1280x720) for «Екі соғыс». Writes thumbnail_1280x720.html; shoot it with Playwright."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
VIDEO = os.path.join(HERE, "..", "video")
sys.path.insert(0, os.path.join(VIDEO, "tools"))
import art
from art import g

fonts = open(os.path.join(VIDEO, "assets", "fonts.css")).read().replace("url('assets/fonts/", "url('../video/assets/fonts/")
W, H = 1280, 720
GROUND = 560

left = (g(art.tank1(), 445, GROUND, 0.88) + g(art.soldier("ww1", "aim"), 60, GROUND, 1.05) +
        g(art.biplane(), 300, 300, 0.85) + f'<g>{art.barbed(-20, 620, GROUND)}</g>')
right = (g(art.tank2(), 980, GROUND, 1.05, flip=True) + g(art.soldier("ww2", "aim"), 1200, GROUND, 1.05, flip=True) +
         g(art.fighter(), 1010, 300, 0.95, flip=True))

svg = f'''<svg viewBox="0 0 {W} {H}" width="{W}" height="{H}">
<defs>
 <linearGradient id="l" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#8a6a3e"/><stop offset="1" stop-color="#f0cf8e"/></linearGradient>
 <linearGradient id="r" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#3b1216"/><stop offset="1" stop-color="#ff6a2e"/></linearGradient>
 <radialGradient id="sl"><stop offset="0" stop-color="#fff2c8" stop-opacity=".9"/><stop offset="1" stop-color="#fff2c8" stop-opacity="0"/></radialGradient>
 <radialGradient id="sr"><stop offset="0" stop-color="#ffd27a" stop-opacity=".95"/><stop offset="1" stop-color="#ffd27a" stop-opacity="0"/></radialGradient>
 <clipPath id="cl"><polygon points="0,0 700,0 580,{H} 0,{H}"/></clipPath>
 <clipPath id="cr"><polygon points="700,0 {W},0 {W},{H} 580,{H}"/></clipPath>
</defs>
<g clip-path="url(#cl)">
 <rect width="{W}" height="{H}" fill="url(#l)"/><circle cx="330" cy="520" r="330" fill="url(#sl)"/>
 <g fill="#20160c" color="#20160c" style="--hi:#5a4024">{left}</g>
 <rect y="{GROUND}" width="{W}" height="{H}" fill="#20160c"/>
</g>
<g clip-path="url(#cr)">
 <rect width="{W}" height="{H}" fill="url(#r)"/><circle cx="980" cy="520" r="340" fill="url(#sr)"/>
 <g fill="#140708" color="#140708" style="--hi:#4a1c1c">{right}</g>
 <rect y="{GROUND}" width="{W}" height="{H}" fill="#140708"/>
</g>
<polygon points="694,0 706,0 586,{H} 574,{H}" fill="#fff6e6"/>
</svg>'''

year = "position:absolute;top:18px;font-family:Oswald;font-weight:700;font-size:200px;line-height:1;color:#fff6e6;-webkit-text-stroke:6px #120a06;paint-order:stroke fill;text-shadow:0 8px 30px rgba(0,0,0,.6)"
page = f'''<!doctype html><html><head><meta charset="utf-8"><style>{fonts}*{{margin:0;padding:0}}body{{width:{W}px;height:{H}px;overflow:hidden}}</style></head>
<body><div style="position:relative;width:{W}px;height:{H}px">{svg}
<div style="{year};left:40px">1914</div>
<div style="{year};right:40px">1945</div>
<div style="position:absolute;left:560px;top:205px;width:160px;height:160px;border-radius:50%;background:#d6372b;border:8px solid #fff6e6;
 display:flex;align-items:center;justify-content:center;font-family:Oswald;font-weight:700;font-size:78px;color:#fff6e6;box-shadow:0 10px 30px rgba(0,0,0,.6)">VS</div>
<div style="position:absolute;left:0;right:0;bottom:0;height:150px;background:#f2c14e;display:flex;align-items:center;justify-content:center;
 font-family:Oswald;font-weight:700;font-size:84px;color:#120a06;letter-spacing:.01em">ҚАЗАҚТАР ҚАНША ҚАЗА ТАПТЫ?</div>
</div></body></html>'''
open(os.path.join(HERE, "thumbnail_1280x720.html"), "w").write(page)
print("ok")
