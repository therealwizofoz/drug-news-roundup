"""pixelevent.py — pixel scenes for stories that are not seizures.

Companion to pixelbust.py. Where pixelbust draws *how much* was taken,
this draws *what happened* — for the many stories that carry no weight at
all: vessel strikes, airstrikes, extraditions, indictments, sentencings,
lab destructions, tunnels, policy decrees.

    from pixelevent import render_event
    caption = render_event(headline, body, f"assets/pixel/{slug}.png")
    if caption:   # None -> nothing confidently classifiable, draw nothing

Design rules, deliberately:

  * One scene per story, chosen by the most specific match. When nothing
    matches confidently it returns None — a wrong picture is worse than
    no picture on a news site.
  * No people are ever drawn. Several of these events killed someone;
    rendering a human being destroyed as a sprite would be grotesque. A
    struck vessel is shown as a burning boat, never a crew.
  * Same 160x120 canvas, palette and blocky idiom as pixelbust, so the
    two sit together on a page without looking like different sites.
"""

import re

from PIL import Image, ImageDraw

W, H = 160, 120

# --- palette -------------------------------------------------------------
SKY = (120, 167, 255)
SKY_DUSK = (86, 104, 168)
CLOUD = (252, 252, 252)
SUN = (250, 220, 90)
SEA = (58, 118, 196)
SEA_D = (42, 92, 158)
SEA_L = (108, 164, 224)
GRASS, GRASS_D = (124, 189, 75), (96, 156, 56)
DIRT, DIRT_D = (139, 90, 43), (114, 70, 31)
CANOPY, CANOPY_D = (74, 140, 62), (52, 106, 44)
HULL, HULL_D = (86, 90, 104), (58, 62, 74)
DECK = (168, 168, 176)
WOOD, WOOD_D = (150, 108, 74), (110, 74, 46)
STONE, STONE_D = (196, 196, 200), (152, 152, 158)
IRON, IRON_D = (168, 168, 168), (110, 110, 110)
GOLD, GOLD_L = (250, 200, 70), (255, 232, 150)
FIRE_Y, FIRE_O, FIRE_R = (255, 232, 120), (245, 150, 40), (214, 60, 36)
SMOKE, SMOKE_D = (150, 150, 158), (108, 108, 118)
PAPER, INK = (244, 242, 232), (60, 58, 54)
RED, DARK = (200, 52, 44), (20, 18, 16)
GLASS = (134, 210, 240)


def _px(img):
    return img.load()


def _rect(d, x0, y0, x1, y1, c):
    # normalise: sprites are positioned by arithmetic that can invert the
    # corners (spikes drawn leftward, for one), and Pillow raises on that.
    # A scene must never be able to crash the daily build.
    if x1 < x0:
        x0, x1 = x1, x0
    if y1 < y0:
        y0, y1 = y1, y0
    d.rectangle([x0, y0, x1, y1], fill=c)


# --- backdrops -----------------------------------------------------------

def _clouds(d, spots=((14, 12, 30), (96, 20, 24), (58, 6, 20))):
    for cx, cy, cw in spots:
        _rect(d, cx, cy, cx + cw, cy + 5, CLOUD)
        _rect(d, cx + 5, cy - 4, cx + cw - 5, cy, CLOUD)


def _sun(d):
    _rect(d, 138, 6, 153, 21, SUN)
    _rect(d, 142, 10, 149, 17, (255, 240, 170))


def bg_sea(d, dusk=False):
    _rect(d, 0, 0, W - 1, H - 1, SKY_DUSK if dusk else SKY)
    if not dusk:
        _clouds(d)
        _sun(d)
    _rect(d, 0, 74, W - 1, H - 1, SEA)
    for y in range(78, H, 6):                    # wave rows
        for x in range((y // 6 % 2) * 6, W, 12):
            _rect(d, x, y, x + 5, y + 1, SEA_D)
            _rect(d, x + 6, y + 2, x + 10, y + 2, SEA_L)


def bg_jungle(d):
    _rect(d, 0, 0, W - 1, H - 1, SKY)
    _clouds(d, ((10, 10, 26), (108, 16, 22)))
    _sun(d)
    for x in range(0, W, 16):                    # canopy line
        _rect(d, x, 52, x + 15, 70, CANOPY)
        _rect(d, x + 2, 48, x + 13, 56, CANOPY)
        _rect(d, x + 4, 60, x + 9, 66, CANOPY_D)
    _rect(d, 0, 96, W - 1, 100, GRASS)
    for x in range(0, W, 4):
        if (x // 4) % 3:
            _rect(d, x, 99, x + 1, 100, GRASS_D)
    _rect(d, 0, 101, W - 1, H - 1, DIRT)
    for x in range(2, W - 2, 9):
        for y in (104, 109, 114):
            if (x + y) % 2:
                _rect(d, x, y, x + 2, y + 1, DIRT_D)


def bg_civic(d):
    """Flat interior: a wall and a floor. For court, prison, paperwork."""
    _rect(d, 0, 0, W - 1, H - 1, (44, 46, 62))
    for x in range(0, W, 20):                    # faint masonry
        for y in range(0, 96, 10):
            off = 10 if (y // 10) % 2 else 0
            _rect(d, x + off, y, x + off + 18, y + 8, (50, 52, 70))
    _rect(d, 0, 96, W - 1, H - 1, (34, 36, 48))
    _rect(d, 0, 96, W - 1, 97, (62, 64, 84))


# --- sprites -------------------------------------------------------------

def boat(d, x, y, burning=False):
    """A small go-fast / fishing vessel, side on."""
    _rect(d, x, y + 10, x + 44, y + 17, HULL)          # hull
    _rect(d, x + 2, y + 17, x + 42, y + 19, HULL_D)
    _rect(d, x + 6, y + 4, x + 26, y + 10, DECK)       # cabin
    _rect(d, x + 9, y + 6, x + 14, y + 9, GLASS)       # window
    _rect(d, x + 17, y + 6, x + 22, y + 9, GLASS)
    _rect(d, x + 30, y + 6, x + 31, y + 10, IRON)      # mast
    if burning:
        _rect(d, x, y + 10, x + 44, y + 17, HULL_D)    # scorched


def submarine(d, x, y):
    _rect(d, x, y + 6, x + 52, y + 14, HULL)
    _rect(d, x + 2, y + 14, x + 50, y + 16, HULL_D)
    _rect(d, x + 20, y, x + 30, y + 6, HULL)           # conning tower
    _rect(d, x + 24, y - 4, x + 25, y, IRON)           # snorkel


def plane(d, x, y, small=False):
    s = 1 if small else 2
    _rect(d, x, y + 4 * s, x + 46 * s, y + 8 * s, DECK)          # fuselage
    _rect(d, x + 8 * s, y, x + 22 * s, y + 4 * s, DECK)          # tail fin
    _rect(d, x + 14 * s, y + 8 * s, x + 34 * s, y + 12 * s, DECK)  # wing
    for i in range(3):                                            # windows
        _rect(d, x + (16 + i * 8) * s, y + 5 * s,
              x + (19 + i * 8) * s, y + 6 * s, GLASS)
    _rect(d, x + 44 * s, y + 5 * s, x + 46 * s, y + 7 * s, RED)   # nose


def _burst(d, cx, cy, r, col):
    """A blocky diamond — reads as a starburst, not a rounded blob."""
    for dy in range(-r, r + 1):
        half = r - abs(dy)
        if half > 0:
            _rect(d, cx - half, cy + dy, cx + half, cy + dy, col)


def explosion(d, cx, cy, r=12):
    """Spiky burst: red diamond, orange body, bright core, four spikes.

    Deliberately small. It has to punctuate the thing that was hit, not
    erase it — an explosion covering the boat tells the reader nothing.
    """
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):          # spikes
        _rect(d, cx + dx * r, cy + dy * r,
              cx + dx * (r + 5) + 1, cy + dy * (r + 5) + 1, FIRE_R)
    _burst(d, cx, cy, r, FIRE_R)
    _burst(d, cx, cy, int(r * 0.68), FIRE_O)
    _burst(d, cx, cy, max(2, int(r * 0.34)), FIRE_Y)
    for dx, dy in ((-r - 4, -r - 2), (r + 3, -r), (r + 1, r + 3)):
        _rect(d, cx + dx, cy + dy, cx + dx + 2, cy + dy + 2, FIRE_Y)


def smoke(d, x, y, n=3):
    for i in range(n):
        s = 5 + i * 3
        _rect(d, x - s // 2 + i * 3, y - i * 9 - s, x + s // 2 + i * 3,
              y - i * 9, SMOKE if i % 2 else SMOKE_D)


def courthouse(d, x, y):
    _rect(d, x, y + 30, x + 60, y + 34, STONE_D)        # steps
    _rect(d, x + 4, y + 28, x + 56, y + 30, STONE_D)
    for i in range(4):                                   # columns
        _rect(d, x + 8 + i * 13, y + 10, x + 13 + i * 13, y + 28, STONE)
    _rect(d, x + 2, y + 6, x + 58, y + 10, STONE)        # entablature
    for i in range(7):                                   # pediment
        _rect(d, x + 8 + i * 3, y + 6 - i, x + 52 - i * 3, y + 6 - i, STONE)


def gavel(d, x, y):
    _rect(d, x, y, x + 18, y + 8, WOOD)                  # head
    _rect(d, x + 2, y + 2, x + 16, y + 4, WOOD_D)
    _rect(d, x + 7, y + 8, x + 11, y + 24, WOOD)         # handle
    _rect(d, x - 8, y + 26, x + 26, y + 30, WOOD_D)      # block


def bars(d, x, y):
    _rect(d, x, y, x + 44, y + 40, (26, 28, 38))         # window recess
    for i in range(5):
        _rect(d, x + 4 + i * 9, y, x + 7 + i * 9, y + 40, IRON)
    _rect(d, x, y + 18, x + 44, y + 21, IRON_D)          # cross bar


def document(d, x, y, sealed=True):
    _rect(d, x, y, x + 38, y + 48, PAPER)
    for i in range(6):                                    # text lines
        wdt = 28 if i % 3 else 20
        _rect(d, x + 5, y + 7 + i * 6, x + 5 + wdt, y + 8 + i * 6, INK)
    if sealed:
        _rect(d, x + 22, y + 36, x + 34, y + 44, RED)     # wax seal
        _rect(d, x + 25, y + 38, x + 31, y + 42, (240, 90, 80))


def handcuffs(d, x, y):
    for cx in (x, x + 20):
        _rect(d, cx, y, cx + 14, y + 3, IRON)
        _rect(d, cx, y + 11, cx + 14, y + 14, IRON)
        _rect(d, cx, y, cx + 3, y + 14, IRON)
        _rect(d, cx + 11, y, cx + 14, y + 14, IRON)
    _rect(d, x + 14, y + 6, x + 20, y + 8, IRON_D)        # chain


def hut(d, x, y, burning=False):
    _rect(d, x + 4, y + 12, x + 40, y + 32, WOOD)         # walls
    for i in range(4):
        _rect(d, x + 4, y + 15 + i * 5, x + 40, y + 16 + i * 5, WOOD_D)
    for i in range(9):                                     # thatch roof
        _rect(d, x + i * 2, y + 12 - i, x + 44 - i * 2, y + 12 - i,
              (168, 140, 82) if i % 2 else (140, 114, 66))
    if not burning:
        _rect(d, x + 18, y + 22, x + 26, y + 32, (40, 34, 28))   # doorway


def barrels(d, x, y, n=3):
    for i in range(n):
        bx = x + i * 12
        _rect(d, bx, y, bx + 10, y + 16, (188, 76, 48))
        _rect(d, bx, y + 4, bx + 10, y + 5, (140, 54, 34))
        _rect(d, bx, y + 11, bx + 10, y + 12, (140, 54, 34))


def container(d, x, y, col=(196, 120, 48)):
    _rect(d, x, y, x + 56, y + 26, col)
    for i in range(10):                                    # corrugation
        _rect(d, x + 3 + i * 5, y + 2, x + 5 + i * 5, y + 24,
              tuple(int(c * 0.86) for c in col))
    _rect(d, x, y, x + 56, y + 2, tuple(int(c * 0.7) for c in col))


def tunnel(d):
    """Cross-section: two shafts joined by a passage under a border line."""
    _rect(d, 0, 0, W - 1, H - 1, SKY)
    _clouds(d, ((14, 8, 22), (112, 14, 20)))
    _rect(d, 0, 40, W - 1, 46, GRASS)                      # surface
    for x in range(0, W, 4):
        if (x // 4) % 3:
            _rect(d, x, 45, x + 1, 46, GRASS_D)
    _rect(d, 0, 47, W - 1, H - 1, DIRT)                    # earth
    for x in range(3, W - 3, 11):                          # soil speckle
        for yy in (58, 72, 90, 106):
            if (x + yy) % 3:
                _rect(d, x, yy, x + 2, yy + 1, DIRT_D)

    # the border fence, straddling the two shafts
    _rect(d, 79, 18, 81, 44, IRON_D)
    for yy in range(20, 44, 6):
        _rect(d, 74, yy, 86, yy + 1, IRON)

    void = (26, 22, 18)
    _rect(d, 26, 47, 42, 88, void)                         # left shaft
    _rect(d, 118, 47, 134, 88, void)                       # right shaft
    _rect(d, 26, 76, 134, 88, void)                        # passage
    for i in range(9):                                      # shoring timbers
        _rect(d, 32 + i * 12, 76, 34 + i * 12, 88, WOOD)
    _rect(d, 26, 86, 134, 88, (52, 44, 36))                # floor
    for yy in (52, 60, 68):                                 # ladder rungs
        _rect(d, 29, yy, 39, yy + 1, WOOD)
        _rect(d, 121, yy, 131, yy + 1, WOOD)


# --- scenes --------------------------------------------------------------

def sc_vessel_strike(d):
    bg_sea(d, dusk=True)
    boat(d, 40, 62, burning=True)
    smoke(d, 58, 58, 4)
    explosion(d, 76, 70, 11)      # at the stern, so the hull still reads
    return "vessel struck and destroyed at sea"


def sc_vessel_seized(d):
    bg_sea(d)
    boat(d, 40, 62)
    _rect(d, 96, 60, 132, 66, HULL)          # patrol boat alongside
    _rect(d, 104, 54, 120, 60, DECK)
    return "smuggling vessel stopped at sea"


def sc_submarine(d):
    bg_sea(d)
    submarine(d, 52, 66)
    return "semi-submersible intercepted"


def sc_airstrike(d):
    bg_jungle(d)
    plane(d, 4, 8, small=True)
    hut(d, 84, 62)                # something recognisable being hit
    explosion(d, 104, 84, 12)
    smoke(d, 96, 58, 3)
    return "airstrike on a jungle camp"


def sc_lab(d):
    bg_jungle(d)
    hut(d, 26, 60, burning=True)
    barrels(d, 96, 84, 3)
    explosion(d, 48, 78, 10)
    return "clandestine laboratory destroyed"


def sc_extradition(d):
    bg_sea(d)
    _rect(d, 0, 96, W - 1, H - 1, (78, 78, 88))     # apron
    _rect(d, 0, 104, W - 1, 106, (216, 200, 90))    # runway stripe
    plane(d, 20, 40, small=True)
    handcuffs(d, 62, 82)
    return "suspect flown out for prosecution"


def sc_court(d):
    bg_civic(d)
    courthouse(d, 12, 40)
    gavel(d, 104, 52)
    return "charges filed in federal court"


def sc_sentencing(d):
    bg_civic(d)
    bars(d, 24, 34)
    gavel(d, 92, 46)
    return "prison sentence handed down"


def sc_policy(d):
    bg_civic(d)
    document(d, 26, 30, sealed=True)
    _rect(d, 92, 44, 132, 48, GOLD)                 # official seal bar
    _rect(d, 96, 48, 128, 76, GOLD_L)
    _rect(d, 104, 56, 120, 68, GOLD)
    return "policy or legal designation issued"


def sc_port(d):
    bg_sea(d)
    _rect(d, 0, 74, W - 1, 84, (86, 86, 96))        # quay
    container(d, 18, 52, (196, 120, 48))
    container(d, 84, 52, (72, 120, 176))
    _rect(d, 140, 12, 146, 74, IRON)                # crane
    _rect(d, 96, 12, 146, 17, IRON)
    _rect(d, 100, 17, 103, 40, IRON_D)
    return "container traffic searched at a port"


def sc_tunnel(d):
    tunnel(d)
    return "cross-border smuggling tunnel"


def sc_raid(d):
    bg_civic(d)
    _rect(d, 40, 34, 88, 96, WOOD)                  # door
    _rect(d, 44, 38, 84, 92, WOOD_D)
    _rect(d, 80, 62, 84, 68, GOLD)                  # handle
    handcuffs(d, 100, 60)
    return "raid and arrests"


def sc_money(d):
    bg_civic(d)
    for i, (x, y) in enumerate(((36, 76), (52, 76), (68, 76),
                                (44, 64), (60, 64), (52, 52))):
        _rect(d, x, y, x + 14, y + 10, GOLD)
        _rect(d, x + 2, y + 2, x + 12, y + 4, GOLD_L)
    document(d, 100, 44, sealed=False)
    return "money-laundering network dismantled"


# most specific first; the first pattern that hits wins
EVENTS = [
    ("vessel_strike", sc_vessel_strike,
     r"\b(strike|struck|strikes)\b.{0,40}\b(vessel|boat|craft|ship)\b"
     r"|\b(vessel|boat|craft|ship)\b.{0,40}\b(struck|destroyed|sunk|sank|"
     r"blown up|blew up)\b|lethal strike|kinetic strike|sink\w*\b.{0,20}"
     r"\b(vessel|boat|ship)\b"),
    ("submarine", sc_submarine,
     r"semi-submersible|narco.?sub|submarine|submersible"),
    ("airstrike", sc_airstrike,
     r"airstrike|air strike|aerial bombardment|bombing raid|bombard"),
    ("lab", sc_lab,
     r"\b(lab|laboratory|labs|laboratories)\b.{0,30}\b(destroy|dismantl|"
     r"raid|seiz|dynamit|burn)|clandestine lab|cocaine kitchen|"
     r"processing (site|camp)"),
    ("tunnel", sc_tunnel, r"\btunnel\b|underground passage"),
    ("extradition", sc_extradition,
     r"extradit|deported to face|flown to the united states to face|"
     r"handed over to us authorities"),
    ("port", sc_port,
     r"\bcontainer\b|\bport of\b|quay|dockworker|terminal at the port"),
    ("money", sc_money,
     r"money launder|laundering network|financial network|"
     r"asset forfeiture|sanction\w* (on|against)"),
    ("sentencing", sc_sentencing,
     r"sentenc|years in prison|life sentence|convicted|found guilty|"
     r"pleaded guilty|plea agreement"),
    ("policy", sc_policy,
     # covers decree/directive/order wording, and the several ways a
     # government says "we now call these people terrorists" -- designated,
     # declared, classified, treated as. Smart quotes included, because
     # headlines put that word in quotation marks more often than not.
     r"\b(decree|directive|proclamation|executive order|resolution)\b"
     r"|(designat|declar|classif|treat|label|brand)\w*\s+(?:\w+\s+){0,3}"
     r"as\s+[\"'\u201c\u2018]?(an?\s+)?terrorist"
     r"|\bnew law\b|legislation|policy shift|constitutional court"),
    ("court", sc_court,
     r"indict|charged|charges|grand jury|criminal complaint|arraign|"
     r"prosecutor|federal court|superseding"),
    ("vessel_seized", sc_vessel_seized,
     r"\b(boat|vessel|ship|go.?fast|fishing craft)\b"),
    ("raid", sc_raid,
     r"\braid\b|search warrant|arrested|detained|in custody|takedown|"
     r"dismantl"),
]


def classify(text):
    """Return (key, scene_fn) for the first pattern that matches, else None."""
    low = text.lower()
    for key, fn, pat in EVENTS:
        if re.search(pat, low):
            return key, fn
    return None


def render_event(headline, body, out_path):
    """
    Draw a scene for a story with no drawable quantity.

    Returns the figcaption, or None when nothing matches confidently —
    in which case the story simply gets no picture.
    """
    hit = classify(f"{headline}\n{body}")
    if not hit:
        return None
    key, fn = hit
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    caption = fn(d)
    img.save(out_path)
    return caption


if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "event.png"
    text = " ".join(sys.argv[2:]) or "Marines sink a refuelling vessel"
    print(render_event(text, "", out))
