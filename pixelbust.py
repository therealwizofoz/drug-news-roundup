"""pixelbust.py — Minecraft-style pixel evidence scenes for the Drug News Roundup.

Call once per story that has a quantity chip; it parses the chip text,
draws a 160x120 blocky-overworld scene (sky, sun, grass ledge, item
stacks) and returns the figcaption. Requires Pillow.

    from pixelbust import render_scene
    caption = render_scene(qty_chip_text, f"site/assets/pixel/{slug}.png")
    if caption:  # None -> nothing drawable, emit no figure
        html += (f'<figure class="shot">'
                 f'<img class="pixel" src="assets/pixel/{slug}.png" '
                 f'width="160" height="120" alt="Pixel art of the seized items">'
                 f'<figcaption>{caption}</figcaption></figure>')
        # and: class="story has-shot", text wrapped in <div class="story-text">

Sprite key: cocaine/generic kilos = white wool blocks · heroin/opium/
hash = dirt blocks · meth = diamond-ore blocks · fentanyl/tablets =
potion bottles · cannabis/khat = leaf blocks · unspecified bulk =
chests · guns = a rack of iron swords · cash = gold ingots · packages =
a wall of mini blocks. One sprite = one real-world unit (1 kg block,
25 kg leaf block, 50 kg chest...), scaling x10 when a haul would need
more than 40 sprites; the caption states the scale.
"""

import math
import re

from PIL import Image, ImageDraw

PAL = {"K": (20, 18, 16), "w": (249, 249, 246), "x": (216, 214, 208),
       "e": (255, 255, 255), "t": (150, 108, 74), "T": (110, 74, 46),
       "q": (134, 96, 60), "c": (93, 219, 213), "C": (182, 245, 241),
       "d": (41, 151, 146), "G": (88, 148, 64), "g": (62, 110, 44),
       "l": (122, 182, 92), "u": (134, 134, 134), "U": (98, 98, 98),
       "v": (168, 168, 168), "y": (250, 200, 70), "Y": (255, 232, 150),
       "o": (240, 140, 40), "r": (226, 60, 44), "b": (250, 235, 215)}
SKY, CLOUD, SUN = (120, 167, 255), (252, 252, 252), (250, 220, 90)
GRASS, GRASS_D = (124, 189, 75), (96, 156, 56)
DIRT, DIRT_D = (139, 90, 43), (114, 70, 31)

WOOL = ["KKKKKKKKKKKK", "KeeeeeeeeeeK", "KwwxwwwxwwwK", "KwxwwwxwwwxK",
        "KwwwxwwwxwwK", "KxwwwxwwwxwK", "KwwxwwwxwwwK", "KwxwwwxwwxwK",
        "KxxwxxwxxwxK", "KKKKKKKKKKKK"]
DIRTB = ["KKKKKKKKKKKK", "KttqttqtttqK", "KtTtttTttttK", "KttttqtttTtK",
         "KtqtTtttqttK", "KttttttTtttK", "KtTtqttttqtK", "KttttTtqtttK",
         "KqtTtttttTtK", "KKKKKKKKKKKK"]
ORE = ["KKKKKKKKKKKK", "KvuuuuuuuuvK", "KuuccuuuuuuK", "KuccccuuucuK",
       "KuuccuuuccuK", "KuuuuuucccuK", "KucuuuuuccuK", "KuccuuUuuuuK",
       "KuuuUuuuuUuK", "KKKKKKKKKKKK"]
LEAF = ["KKKKKKKKKKKK", "KlGGgGGlGGgK", "KGgGGGgGGGGK", "KGGlGgGGgGlK",
        "KgGGGGGlGGGK", "KGGgGlGGGgGK", "KlGGGGgGGGGK", "KGgGGGGGlGgK",
        "KgGgGgGgGGgK", "KKKKKKKKKKKK"]
CHEST = ["KKKKKKKKKKKK", "KqqqqqqqqqqK", "KqtqqqqqqtqK", "KKKKKKKKKKKK",
         "KqqqqKyKqqqK", "KqqqqKyKqqqK", "KqtqqqqqqtqK", "KqqqqqqqqqqK",
         "KKKKKKKKKKKK"]
MINI = ["KKKKKK", "KweewK", "KwxxwK", "KKKKKK"]
SWORD = ["..K..", ".KwK.", ".KwK.", ".KwK.", ".KwK.", ".KwK.",
         ".KwK.", "KKKKK", ".KtK.", ".KtK.", "..K.."]
INGOT = ["..KKKKKK..", ".KyYYYYyK.", "KyYYyyyyyK", "KyyyyyyyyK",
         "KKKKKKKKKK"]
POTION = ["..KKK..", "..KbK..", ".KKKKK.", ".KcCcK.", "KcCcccK",
          "KcccccK", "KccdccK", ".KKKKK."]
PLANE = [".KK", ".KrrK", ".KrrrKK", ".KwwwwwKKKKKKKKKKKKKKK",
         "KwwwwwwwwwwwwwwwwwwwwwK", "KwccwccwccwwwwwwwwwwwwK",
         ".KKKKKKwwwwwwwwwwwwKKK", "......KKKKwwwwKKKK"]

# substance pattern -> (sprite, base grams per sprite)
FAMILIES = [
    (r"cocaine|coke", WOOL, 1000),
    (r"heroin|opium|hash|hashish|charas", DIRTB, 1000),
    (r"meth|ice|crystal", ORE, 1000),
    (r"fentanyl|oxy|xanax|mdma|ecstasy", POTION, 500),
    (r"cannabis|marijuana|ganja|skunk|weed|khat", LEAF, 25000),
    (r"narcotic|drug", CHEST, 50000),
]
UNIT_G = {"g": 1, "gram": 1, "grams": 1, "kg": 1000, "kilo": 1000,
          "kilos": 1000, "kilogram": 1000, "kilograms": 1000, "lb": 453.6,
          "lbs": 453.6, "pound": 453.6, "pounds": 453.6, "t": 1e6,
          "ton": 1e6, "tons": 1e6, "tonne": 1e6, "tonnes": 1e6, "oz": 28.35}


def parse_quantities(text):
    items, seen_cash = [], False
    for part in re.split(r"[\u00b7|,;]|\s\+\s| and ", text):
        part = part.strip().lstrip("~\u2248 ")
        if not part:
            continue
        if re.search(r"\$|\u20ac|\u00a3|cash|currency", part, re.I):
            if not seen_cash:
                items.append({"kind": "cash"})
                seen_cash = True
            continue
        if re.search(r"aircraft|airplane|plane\b", part, re.I):
            items.append({"kind": "plane"})
            continue
        m = re.match(r"([\d,.]+)\s*\+?\s*(\w+)?\s*(.*)", part)
        if not m:
            continue
        try:
            num = float(m.group(1).replace(",", ""))
        except ValueError:
            continue
        unit = (m.group(2) or "").lower()
        rest = ((m.group(3) or "") + " " + unit).strip()
        rest = re.sub(r"\(.*?\)", "", rest)  # "(101 kg opium)" asides
        if re.search(r"gun|firearm|rifle|pistol|weapon", rest, re.I):
            items.append({"kind": "guns", "count": num})
        elif re.search(r"package|packet|parcel|brick", rest, re.I):
            items.append({"kind": "packages", "count": num})
        elif re.search(r"pill|tablet|dose|blotter", rest, re.I):
            items.append({"kind": "pills"})
        else:
            grams = num * UNIT_G.get(unit, 0)
            fam = _family(rest)
            if grams > 0 and fam:
                items.append({"kind": "weight", "grams": grams,
                              "sprite": fam[0], "base": fam[1],
                              "name": fam[2]})
    return items


def _family(text):
    for pat, sprite, base in FAMILIES:
        m = re.search(pat, text, re.I)
        if m:
            name = m.group(0).lower()
            return sprite, base, {"drug": "drugs",
                                  "narcotic": "narcotics"}.get(name, name)
    return None


W, H = 160, 120


def _stamp(px, rows, x, y, sc=1):
    for r, row in enumerate(rows):
        for c, ch in enumerate(row):
            col = PAL.get(ch)
            if col:
                for dy in range(sc):
                    for dx in range(sc):
                        px_x = x + c * sc + dx
                        px_y = y + r * sc + dy
                        # clip rather than raise: an off-canvas sprite is a
                        # cosmetic problem, a crash is a missing edition
                        if 0 <= px_x < W and 0 <= px_y < H:
                            px[px_x, px_y] = col


def _stamp_b(px, rows, x, bottom, sc=1):
    _stamp(px, rows, x, bottom - len(rows) * sc, sc)


def _overworld(draw, px):
    draw.rectangle([0, 0, 159, 119], fill=SKY)
    for cx, cy, cw in ((14, 12, 30), (96, 20, 24), (58, 6, 20)):
        draw.rectangle([cx, cy, cx + cw, cy + 5], fill=CLOUD)
        draw.rectangle([cx + 5, cy - 4, cx + cw - 5, cy], fill=CLOUD)
    draw.rectangle([138, 6, 153, 21], fill=SUN)          # square sun
    draw.rectangle([142, 10, 149, 17], fill=(255, 240, 170))
    draw.rectangle([0, 102, 159, 106], fill=GRASS)       # grass ledge
    for x in range(0, 160, 4):
        if (x // 4) % 3:
            draw.rectangle([x, 105, x + 1, 106], fill=GRASS_D)
        if (x // 4) % 4 == 1:
            draw.rectangle([x, 100, x, 101], fill=GRASS)  # blades
    draw.rectangle([0, 107, 159, 119], fill=DIRT)
    for x in range(2, 158, 9):
        for y in (109, 114, 117):
            if (x + y) % 2:
                draw.rectangle([x, y, x + 2, y + 1], fill=DIRT_D)


def render_scene(qty_text, out_path):
    """Draw the overworld PNG; return the caption string, or None."""
    items = parse_quantities(qty_text)
    if not items:
        return None
    img = Image.new("RGB", (160, 120))
    draw = ImageDraw.Draw(img)
    _overworld(draw, img.load())
    px = img.load()
    caption = []
    weights = sorted([i for i in items if i["kind"] == "weight"],
                     key=lambda i: -i["grams"])
    guns = next((i for i in items if i["kind"] == "guns"), None)
    extras = [i["kind"] for i in items
              if i["kind"] in ("cash", "pills", "plane", "packages")]
    if "plane" in extras:
        _stamp(px, PLANE, 52, 26, 2)
    right_edge = 132 if ("cash" in extras or "pills" in extras) else 156
    cursor = 6
    for w in weights[:3]:
        unit = w["base"]
        while w["grams"] / unit > 40:
            unit *= 10
        n = max(1, round(w["grams"] / unit))
        sc = 2 if (n <= 3 or (n <= 6 and len(weights) == 1 and not guns)) \
            else 1
        sw = (len(w["sprite"][0]) + 1) * sc
        cols = max(1, min(n, (right_edge - cursor) // sw))
        rows_h = len(w["sprite"]) * sc          # blocks stack flush
        for i in range(n):
            r, c = divmod(i, cols)
            _stamp_b(px, w["sprite"], cursor + c * sw, 103 - r * rows_h, sc)
        cursor += min(n, cols) * sw + 8
        if n == 1:
            caption.append(f"{_fmt(w['grams'])} {w['name']}")
        elif abs(n * unit - w["grams"]) <= 0.02 * w["grams"]:
            caption.append(f"{n} \u00d7 {_fmt(unit)} {w['name']}")
        else:
            caption.append(
                f"{n} \u00d7 {_fmt(unit)} \u2248 {_fmt(w['grams'])} "
                f"{w['name']}")
    if guns:
        per = 1 if guns["count"] <= 15 else 10
        n = min(15, max(1, round(guns["count"] / per)))
        per_row = 8
        # the rack is drawn right-and-down; start it far enough left that the
        # widest row still fits
        gx = min(max(cursor, 8), W - per_row * 8 - 2)
        for i in range(n):
            r, c = divmod(i, per_row)
            _stamp(px, SWORD, gx + c * 8 - r * 4, 56 + r * 22)
        caption.append(f"1 sword = {per} guns" if per > 1
                       else f"all {int(guns['count'])} guns")
    for it in items:
        if it["kind"] == "packages":
            n = int(min(it["count"], 220))
            for i in range(n):
                r, c = divmod(i, 21)
                _stamp_b(px, MINI, 6 + c * 7, 103 - r * 5)
            caption.append(f"all {int(it['count'])} packages")
        elif it["kind"] == "pills":
            _stamp_b(px, POTION, 136, 95)
            _stamp_b(px, POTION, 144, 103)
            caption.append("plus the tablets")
        elif it["kind"] == "cash":
            _stamp_b(px, INGOT, 136, 103)
            _stamp_b(px, INGOT, 141, 97)
            _stamp_b(px, INGOT, 146, 91)
            caption.append("and the cash")
        elif it["kind"] == "plane":
            caption.append("plus the plane")
    img.save(out_path)
    return " \u00b7 ".join(caption[:4]) if caption else None


def _fmt(grams):
    if grams >= 1e6:
        v = grams / 1e6
    elif grams >= 1000:
        v = grams / 1000
    else:
        v = grams
    v = round(v) if v >= 10 or v == int(v) else round(v, 1)
    unit = "t" if grams >= 1e6 else ("kg" if grams >= 1000 else "g")
    return f"{v:g} {unit}"


if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "scene.png"
    qty = " ".join(sys.argv[2:]) or "352 kg cocaine \u00b7 10 guns"
    print(render_scene(qty, out))
