# -*- coding: utf-8 -*-
"""Hand-drawn SVG silhouettes for the film. Everything is filled with currentColor
unless a colour is given, so a scene sets one ink colour per layer.

Each figure function returns an SVG <g> drawn with its origin at the ground,
facing right, about 200 units tall for a standing person.
"""


def g(body, x=0, y=0, s=1.0, flip=False, cls="", extra=""):
    sx = -s if flip else s
    inner = f'<g transform="translate({x},{y}) scale({sx},{s})"{extra}>{body}</g>'
    # a class goes on an untransformed wrapper, so GSAP x/y tweens move the figure relative to its place
    return f'<g class="{cls}">{inner}</g>' if cls else inner


# ------------------------------------------------------------------ people
def soldier(era="ww1", pose="march", rifle=True):
    """A soldier. Legs carry classes lg1/lg2 so a scene can swing them."""
    if era == "ww1":
        helmet = '<path d="M-20,-183 Q4,-212 28,-183 Z"/><rect x="-24" y="-186" width="56" height="6" rx="3"/>'
    else:
        helmet = '<path d="M-14,-178 Q-14,-204 6,-204 Q26,-204 25,-178 L28,-174 L-14,-174 Z"/>'
    legs = ('<g class="lg1" style="transform-origin:0px -98px"><rect x="-9" y="-100" width="15" height="96" rx="6"/>'
            '<ellipse cx="4" cy="-5" rx="13" ry="6"/></g>'
            '<g class="lg2" style="transform-origin:0px -98px"><rect x="-5" y="-100" width="15" height="96" rx="6"/>'
            '<ellipse cx="8" cy="-5" rx="13" ry="6"/></g>')
    torso = ('<path d="M-15,-163 Q4,-170 22,-163 L18,-96 L-13,-96 Z"/>'
             '<rect x="-29" y="-158" width="16" height="44" rx="4"/>'  # pack
             '<rect x="-1" y="-172" width="11" height="12"/>'  # neck
             '<circle cx="5" cy="-180" r="13"/>')
    gun = ""
    if rifle:
        if pose == "march":
            gun = ('<path d="M-6,-150 L52,-232" stroke="currentColor" stroke-width="6" stroke-linecap="round"/>'
                   '<path d="M52,-232 L64,-252" stroke="currentColor" stroke-width="2.5"/>')
        else:  # aiming / charging
            gun = ('<path d="M0,-145 L95,-150" stroke="currentColor" stroke-width="7" stroke-linecap="round"/>'
                   '<path d="M95,-150 L122,-151" stroke="currentColor" stroke-width="2.5"/>')
    arm = '<path d="M10,-160 Q30,-140 18,-122" stroke="currentColor" stroke-width="11" fill="none" stroke-linecap="round"/>'
    return legs + torso + helmet + gun + arm


def person(kind="man"):
    """A civilian standing: man, woman (long dress + headscarf), child."""
    if kind == "woman":
        return ('<path d="M-22,0 L-12,-110 Q0,-120 12,-110 L24,0 Z"/>'
                '<path d="M-13,-108 Q0,-150 14,-108"/>'
                '<circle cx="0" cy="-150" r="14"/>'
                '<path d="M-17,-148 Q0,-180 17,-148 L20,-125 L-20,-125 Z"/>')
    if kind == "child":
        return ('<rect x="-9" y="-62" width="8" height="62" rx="4"/><rect x="2" y="-62" width="8" height="62" rx="4"/>'
                '<path d="M-14,-108 Q0,-114 14,-108 L12,-60 L-12,-60 Z"/><circle cx="0" cy="-122" r="12"/>')
    return ('<rect x="-12" y="-98" width="11" height="98" rx="5"/><rect x="1" y="-98" width="11" height="98" rx="5"/>'
            '<path d="M-17,-162 Q0,-170 17,-162 L15,-94 L-15,-94 Z"/><circle cx="0" cy="-180" r="14"/>'
            '<path d="M-15,-186 Q0,-206 15,-186 Z"/>')


def mourner():
    """A standing figure with a bowed head."""
    return ('<rect x="-12" y="-98" width="11" height="98" rx="5"/><rect x="1" y="-98" width="11" height="98" rx="5"/>'
            '<path d="M-17,-160 Q0,-168 17,-160 L15,-94 L-15,-94 Z"/><circle cx="7" cy="-170" r="14"/>')


def elder():
    """Ата, seated cross-legged, tall felt hat (қалпақ), beard, a long robe (шапан)."""
    return ('<path d="M-70,0 Q-70,-30 -30,-34 L40,-34 Q75,-30 72,0 Z"/>'          # crossed legs / robe hem
            '<path d="M-38,-30 Q-44,-120 -10,-140 L22,-140 Q50,-120 44,-30 Z"/>'    # robe
            '<rect x="-4" y="-152" width="16" height="16"/>'
            '<circle cx="4" cy="-170" r="20"/>'
            '<path d="M-6,-160 Q8,-112 22,-160 Z"/>'                                # beard
            '<path d="M-18,-180 L-10,-222 Q4,-232 18,-222 L26,-180 Q4,-174 -18,-180 Z"/>'  # hat
            '<path d="M-22,-182 Q4,-170 30,-182 L28,-176 Q4,-166 -20,-176 Z"/>'
            '<path d="M40,-110 Q70,-80 60,-50" stroke="currentColor" stroke-width="16" fill="none" stroke-linecap="round"/>')


def boy():
    """Ерлан, a seated boy, hugging his knees."""
    return ('<path d="M-30,0 Q-34,-60 -6,-70 L20,-70 Q34,-60 30,0 Z"/>'
            '<path d="M18,-66 Q44,-60 42,-24 L30,-24 Z"/>'
            '<circle cx="4" cy="-88" r="17"/>'
            '<path d="M-14,-94 Q4,-118 22,-94 Z"/>')


def rider():
    """A Kazakh horseman of 1916 with a fur hat (тымақ) and a spear. Legs: lg1/lg2."""
    horse = ('<g class="lg1" style="transform-origin:45px -88px"><rect x="38" y="-92" width="12" height="90" rx="5"/></g>'
             '<g class="lg2" style="transform-origin:-48px -88px"><rect x="-55" y="-92" width="12" height="90" rx="5"/></g>'
             '<g class="lg2" style="transform-origin:58px -88px"><rect x="52" y="-92" width="12" height="90" rx="5"/></g>'
             '<g class="lg1" style="transform-origin:-36px -88px"><rect x="-42" y="-92" width="12" height="90" rx="5"/></g>'
             '<ellipse cx="0" cy="-108" rx="80" ry="32"/>'
             '<path d="M50,-128 L92,-190 L112,-180 L80,-110 Z"/>'
             '<path d="M88,-196 Q120,-196 134,-168 L128,-158 Q104,-166 86,-170 Z"/>'
             '<path d="M92,-196 L96,-212 L102,-194 Z"/>'
             '<path d="M-76,-120 Q-110,-110 -112,-50 Q-96,-90 -74,-100 Z"/>')
    man = ('<path d="M-18,-140 Q-6,-150 14,-140 L16,-200 Q0,-210 -16,-200 Z"/>'
           '<path d="M0,-140 L22,-100" stroke="currentColor" stroke-width="12" stroke-linecap="round"/>'
           '<circle cx="0" cy="-222" r="14"/>'
           '<path d="M-20,-222 Q0,-262 22,-222 L26,-200 L16,-208 L-14,-208 L-24,-198 Z"/>'
           '<path d="M-40,-170 L130,-282" stroke="currentColor" stroke-width="4"/>'
           '<path d="M130,-282 L142,-292 L136,-278 Z"/>')
    return horse + man


# ------------------------------------------------------------------ machines
def tank1():
    """British Mark I rhomboid tank (1916), tail wheels, side gun."""
    return ('<path d="M-160,0 L150,0 Q182,-6 178,-46 L122,-120 L-112,-120 L-176,-46 Q-182,-6 -160,0 Z"/>'
            '<path d="M-150,-10 L140,-10 Q166,-14 162,-44 L116,-108" fill="none" stroke="var(--hi)" stroke-width="3" stroke-dasharray="10 8" class="tread"/>'
            '<rect x="-34" y="-92" width="78" height="46" rx="6"/>'
            '<rect x="40" y="-78" width="54" height="10"/>'
            '<circle cx="-200" cy="-18" r="18"/><circle cx="-236" cy="-18" r="18"/>'
            '<path d="M-176,-24 L-236,-24" stroke="currentColor" stroke-width="8"/>')


def tank2():
    """A WWII medium tank with sloped armour. Wheels: class wh."""
    wheels = "".join(f'<g class="wh" style="transform-origin:{x}px -22px"><circle cx="{x}" cy="-22" r="19"/>'
                     f'<path d="M{x-14},-22 L{x+14},-22 M{x},-36 L{x},-8" stroke="var(--hi)" stroke-width="3"/></g>'
                     for x in (-118, -66, -14, 38, 90))
    return ('<rect x="-158" y="-46" width="300" height="46" rx="23"/>' + wheels +
            '<path d="M-160,-46 L150,-46 L176,-70 L124,-98 L-128,-98 L-166,-70 Z"/>'
            '<path d="M-70,-98 L54,-98 L44,-140 Q-6,-152 -56,-138 Z"/>'
            '<rect x="44" y="-128" width="150" height="11" rx="3"/>'
            '<rect x="-30" y="-152" width="30" height="10" rx="3"/>')


def biplane():
    return ('<ellipse cx="0" cy="0" rx="78" ry="12"/>'
            '<rect x="-30" y="-44" width="64" height="8" rx="4"/><rect x="-30" y="10" width="64" height="8" rx="4"/>'
            '<path d="M-20,-36 L-14,10 M20,-36 L26,10" stroke="currentColor" stroke-width="3"/>'
            '<path d="M-78,-2 L-96,-30 L-84,-30 L-60,-6 Z"/><rect x="-96" y="-4" width="26" height="6"/>'
            '<circle cx="-4" cy="-16" r="8"/>'
            '<g class="prop" style="transform-origin:82px 0px"><ellipse cx="82" cy="0" rx="4" ry="30"/></g>')


def fighter():
    return ('<path d="M-110,0 Q-40,-16 70,-12 Q96,-8 100,0 Q96,8 70,12 Q-40,14 -110,4 Z"/>'
            '<path d="M-10,-2 L40,-2 L22,26 L-26,26 Z"/>'
            '<path d="M-104,-2 L-124,-36 L-108,-36 L-80,-6 Z"/>'
            '<path d="M10,-12 Q24,-30 46,-12 Z"/>'
            '<g class="prop" style="transform-origin:104px 0px"><ellipse cx="104" cy="0" rx="4" ry="34"/></g>')


def bomber():
    return ('<path d="M-150,0 Q-60,-20 110,-14 Q140,-6 140,0 Q140,8 110,12 Q-60,16 -150,6 Z"/>'
            '<path d="M-30,-4 L60,-4 L20,46 L-60,46 Z" opacity=".85"/>'
            '<path d="M-144,-2 L-170,-46 L-150,-46 L-118,-8 Z"/>')


def mg_icon():
    return ('<path d="M-60,-60 L70,-60 L70,-44 L-60,-44 Z"/><rect x="70" y="-56" width="70" height="8"/>'
            '<rect x="-80" y="-74" width="40" height="44" rx="6"/>'
            '<path d="M-10,-44 L-60,30 M-10,-44 L40,30 M-10,-44 L-10,30" stroke="currentColor" stroke-width="8" stroke-linecap="round"/>')


def gasmask_icon():
    return ('<path d="M-70,-40 Q-70,-120 0,-124 Q70,-120 70,-40 Q60,20 0,30 Q-60,20 -70,-40 Z"/>'
            '<circle cx="-30" cy="-60" r="20" fill="var(--bg)"/><circle cx="30" cy="-60" r="20" fill="var(--bg)"/>'
            '<rect x="-20" y="10" width="40" height="40" rx="10"/><rect x="-28" y="46" width="56" height="30" rx="8"/>')


def officer_icon():
    return ('<path d="M-80,60 Q-80,-10 -30,-20 L30,-20 Q80,-10 80,60 Z"/><circle cx="0" cy="-60" r="40"/>'
            '<path d="M-52,-80 Q0,-130 52,-80 L58,-70 L-58,-70 Z"/><rect x="-46" y="-74" width="92" height="12" rx="4"/>'
            '<path d="M-20,-10 L0,20 L20,-10" fill="var(--bg)"/>')


def sniper_icon():
    return ('<path d="M-110,10 L60,-10 L60,4 L-110,26 Z"/><rect x="-20" y="-24" width="60" height="12" rx="6"/>'
            '<rect x="60" y="-8" width="60" height="6"/><path d="M-110,10 L-130,40 L-100,40 Z"/>'
            '<circle cx="-40" cy="-60" r="26"/><path d="M-80,-36 Q-40,-50 -10,-30 L-20,0 L-90,10 Z"/>')


def pilot_icon():
    return g(fighter(), 0, 0, 1.0) + '<circle cx="0" cy="-70" r="0"/>'


def flag_icon():
    return ('<rect x="-50" y="-110" width="8" height="190" rx="3"/>'
            '<path class="wave" d="M-42,-110 Q0,-124 40,-104 Q80,-86 100,-100 L100,-30 Q70,-16 40,-34 Q0,-54 -42,-40 Z" fill="var(--accent)"/>')


def dombra_icon():
    return ('<ellipse cx="-30" cy="20" rx="44" ry="60" transform="rotate(-35 -30 20)"/>'
            '<path d="M-6,-20 L90,-150" stroke="currentColor" stroke-width="14" stroke-linecap="round"/>'
            '<circle cx="-34" cy="24" r="10" fill="var(--bg)"/>')


def star(r=40, cls=""):
    import math
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.42
        pts.append(f"{rr*math.cos(a):.1f},{rr*math.sin(a):.1f}")
    c = f' class="{cls}"' if cls else ""
    return f'<polygon{c} points="{" ".join(pts)}"/>'


def icon(kind):
    return {"mg": mg_icon, "gas": gasmask_icon, "tank1": lambda: g(tank1(), 10, 50, 0.72),
            "plane1": lambda: g(biplane(), 0, -20, 1.1), "officer": officer_icon, "sniper": sniper_icon,
            "pilot": lambda: g(fighter(), 0, -10, 0.95), "flag": flag_icon, "poet": dombra_icon,
            "rider": lambda: g(rider(), -10, 110, 0.6)}[kind]()


# ------------------------------------------------------------------ places
def yurt():
    lattice = "".join(f'<path d="M{x},-110 L{x+40},0 M{x+40},-110 L{x},0" stroke="var(--hi)" stroke-width="2" opacity=".35"/>'
                      for x in range(-160, 160, 40))
    return ('<rect x="-165" y="-112" width="330" height="112"/>' + lattice +
            '<path d="M-180,-108 Q-120,-200 -30,-228 L30,-228 Q120,-200 180,-108 Z"/>'
            '<rect x="-34" y="-236" width="68" height="12" rx="4"/>'
            '<rect x="-34" y="-92" width="68" height="92" fill="var(--glow)" class="door"/>')


def campfire():
    return ('<path d="M-40,0 L40,-10 M-40,-10 L40,0" stroke="#2a1608" stroke-width="10" stroke-linecap="round"/>'
            '<g class="fl" style="transform-origin:0px 0px"><path d="M-28,-6 Q-34,-50 -4,-86 Q-8,-50 10,-40 Q16,-70 8,-96 Q44,-60 30,-6 Z" fill="#f08a24"/>'
            '<path d="M-14,-6 Q-18,-34 2,-56 Q4,-30 18,-6 Z" fill="#ffd36a"/></g>')


def pine(h=260):
    w = h * 0.42
    return (f'<rect x="-6" y="-{h*0.18:.0f}" width="12" height="{h*0.18:.0f}"/>'
            f'<path d="M0,-{h} L{w*0.55:.0f},-{h*0.6:.0f} L{w*0.3:.0f},-{h*0.6:.0f} L{w*0.75:.0f},-{h*0.33:.0f} L{w*0.4:.0f},-{h*0.33:.0f} '
            f'L{w:.0f},-{h*0.14:.0f} L-{w:.0f},-{h*0.14:.0f} L-{w*0.4:.0f},-{h*0.33:.0f} L-{w*0.75:.0f},-{h*0.33:.0f} '
            f'L-{w*0.3:.0f},-{h*0.6:.0f} L-{w*0.55:.0f},-{h*0.6:.0f} Z"/>')


def birch(h=300):
    h = int(h)
    return (f'<rect x="-7" y="-{h}" width="14" height="{h}" fill="#d9d2c2"/>'
            + "".join(f'<rect x="-7" y="-{y}" width="{8 if y%2 else 10}" height="4" fill="#2a2a2a"/>' for y in range(30, h, 37)))


def digger():
    """A search volunteer kneeling with a small shovel. Arm: class dig."""
    return ('<path d="M-50,0 Q-52,-40 -20,-44 L10,-44 L16,0 Z"/>'
            '<path d="M-26,-44 Q-34,-110 6,-118 Q30,-110 26,-60 Z"/>'
            '<circle cx="16" cy="-132" r="15"/><path d="M0,-140 Q16,-160 34,-140 Z"/>'
            '<g class="dig" style="transform-origin:10px -100px"><path d="M10,-100 L60,-40" stroke="currentColor" stroke-width="10" stroke-linecap="round"/>'
            '<path d="M60,-40 L80,-6" stroke="currentColor" stroke-width="5"/><path d="M72,-12 L92,-4 L80,10 L66,0 Z"/></g>')


def locomotive():
    wheels = "".join(f'<g class="wh" style="transform-origin:{x}px -26px"><circle cx="{x}" cy="-26" r="{r}"/>'
                     f'<path d="M{x-r+4},-26 L{x+r-4},-26" stroke="var(--hi)" stroke-width="3"/></g>'
                     for x, r in ((-110, 26), (-50, 34), (20, 34), (80, 22)))
    return (wheels + '<rect x="-150" y="-128" width="200" height="80" rx="30"/>'
            '<rect x="40" y="-170" width="90" height="122"/><rect x="58" y="-156" width="34" height="34" fill="var(--glow)"/>'
            '<rect x="-128" y="-186" width="26" height="60"/><rect x="-136" y="-192" width="42" height="12"/>'
            '<path d="M-150,-52 L-180,-20 L-150,-20 Z"/><rect x="30" y="-178" width="110" height="12"/>')


def wagon(lit=True):
    win = '<rect x="-40" y="-120" width="80" height="34" fill="var(--glow)" opacity=".85"/>' if lit else ""
    return ('<circle cx="-70" cy="-22" r="22" class="wh2"/><circle cx="70" cy="-22" r="22" class="wh2"/>'
            '<rect x="-110" y="-150" width="220" height="110" rx="6"/>' + win +
            '<path d="M-116,-150 Q0,-176 116,-150 Z"/>')


def factory():
    return ('<rect x="-260" y="-160" width="520" height="160"/>'
            '<path d="M-260,-160 L-200,-210 L-200,-160 L-140,-210 L-140,-160 L-80,-210 L-80,-160 L-20,-210 L-20,-160 Z"/>'
            '<rect x="60" y="-360" width="40" height="200"/><rect x="150" y="-320" width="34" height="160"/>'
            + "".join(f'<rect x="{x}" y="-120" width="44" height="40" fill="var(--glow)"/>' for x in (-230, -160, -90, -20, 50, 120, 190)))


def obelisk():
    return ('<rect x="-120" y="-30" width="240" height="30"/><rect x="-90" y="-60" width="180" height="30"/>'
            '<path d="M-40,-60 L-26,-440 L0,-470 L26,-440 L40,-60 Z"/>'
            + g(star(30), 0, -390, 1.0) +
            '<g class="fl" style="transform-origin:0px -60px"><path d="M-24,-60 Q-30,-100 -4,-130 Q-6,-100 8,-92 Q14,-116 6,-138 Q40,-100 26,-60 Z" fill="#f08a24"/></g>')


def grave_mound(w=180):
    return f'<path d="M-{w/2},0 Q0,-{w*0.28:.0f} {w/2},0 Z"/><rect x="-6" y="-{w*0.5:.0f}" width="12" height="{w*0.4:.0f}"/>' + g(star(16), 0, -w * 0.52, 1)


def reichstag():
    cols = "".join(f'<rect x="{x}" y="-250" width="16" height="140"/>' for x in range(-110, 120, 40))
    return ('<rect x="-330" y="-110" width="660" height="110"/><rect x="-330" y="-290" width="160" height="180"/>'
            '<rect x="170" y="-290" width="160" height="180"/><rect x="-140" y="-270" width="280" height="160" opacity=".7"/>' + cols +
            '<path d="M-160,-270 L0,-330 L160,-270 Z"/>'
            '<path d="M-120,-330 Q0,-470 120,-330 Z" fill="none" stroke="currentColor" stroke-width="10"/>'
            '<path d="M-90,-345 L90,-345 M-60,-400 L60,-400 M0,-430 L0,-330 M-70,-330 L-40,-420 M70,-330 L40,-420" stroke="currentColor" stroke-width="5"/>'
            '<rect x="-4" y="-560" width="8" height="140"/>'
            '<path class="wave" d="M4,-560 Q50,-574 90,-556 Q130,-540 160,-552 L160,-490 Q130,-478 90,-494 Q50,-512 4,-498 Z" fill="var(--accent)"/>')


def mushroom():
    return ('<path d="M-46,0 Q-30,-140 -40,-300 L40,-300 Q30,-140 46,0 Z" fill="#c98a5e"/>'
            '<ellipse cx="0" cy="-330" rx="210" ry="110" fill="#b9704c"/>'
            '<ellipse cx="0" cy="-370" rx="170" ry="92" fill="#e7a873"/>'
            '<ellipse cx="-20" cy="-400" rx="110" ry="56" fill="#f6d6a4"/>'
            '<ellipse cx="0" cy="-180" rx="120" ry="22" fill="#d99a6a" opacity=".8"/>')


def person_icon():
    return '<circle cx="0" cy="-30" r="6"/><path d="M-8,0 L-8,-18 Q0,-24 8,-18 L8,0 Z"/>'


def barbed(x0, x1, y):
    posts = "".join(f'<path d="M{x-14},{y} L{x+14},{y-70} M{x+14},{y} L{x-14},{y-70}" stroke="currentColor" stroke-width="7"/>'
                    for x in range(x0, x1, 170))
    zig = " ".join(f"{x},{y-55 + (12 if (x//30)%2 else -12)}" for x in range(x0, x1, 30))
    zig2 = " ".join(f"{x+15},{y-25 + (10 if (x//30)%2 else -10)}" for x in range(x0, x1, 30))
    return posts + f'<polyline points="{zig}" fill="none" stroke="currentColor" stroke-width="3"/>' \
                   f'<polyline points="{zig2}" fill="none" stroke="currentColor" stroke-width="3"/>'


def sandbags(x0, x1, y):
    out = []
    for row in range(3):
        for x in range(x0 + (row % 2) * 30, x1, 60):
            out.append(f'<ellipse cx="{x}" cy="{y - row*26}" rx="34" ry="16"/>')
    return "".join(out)
