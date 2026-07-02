"""
DFW deal map overlay.

The base image (assets/dfw_base_map.jpg) is the FIXED picture and is never
modified. render() opens it, marks each deal's true submarket location with a
small dot, and places a numbered category pin offset with a leader line so labels
stay legible in dense areas. Pin numbers match the Src column in the Deal &
Development Watch table. No network, no map API.

    from dfw_map import render
    render(deals, out="figs/dfw_map.png", date="July 1, 2026")
    # deals: [{"n": 5, "category": "Data Center", "submarkets": ["Red Oak"]}, ...]

Calibration constants A, B, C, D are tied to THIS base image. If the base image
is replaced, recalibrate (see README) and update them.
"""
import os, re
from PIL import Image, ImageDraw, ImageFont

_HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(_HERE, "..", "assets", "dfw_base_map.jpg")

# affine calibrated to dfw_base_map.jpg (1169 x 827): x = A*lon + B, y = C*lat + D
A, B = 764.3, 74564.0
C, D = -925.9, 30822.0

# 10-category palette (matches the brief legend)
CATEGORY_COLORS = {
    "industrial": (31, 122, 77), "logistics": (31, 122, 77), "manufacturing": (31, 122, 77),
    "ios": (21, 154, 138),
    "data center": (217, 138, 31),
    "land": (176, 165, 43),
    "multifamily": (192, 57, 43), "distress": (192, 57, 43),
    "office": (47, 111, 176),
    "infrastructure": (107, 112, 117),
    "public incentives": (138, 125, 31),
    "sports": (176, 51, 140), "entertainment": (176, 51, 140),
    "major employer": (47, 143, 107),
    "retail": (107, 63, 160), "mixed-use": (107, 63, 160), "hospitality": (107, 63, 160),
}
LEGEND = [
    ("Industrial", (31, 122, 77)), ("IOS", (21, 154, 138)),
    ("Data Center", (217, 138, 31)), ("Land", (176, 165, 43)),
    ("Multifamily", (192, 57, 43)), ("Office", (47, 111, 176)),
    ("Infrastructure", (107, 112, 117)), ("Public Incentives", (138, 125, 31)),
    ("Sports / Entertainment", (176, 51, 140)), ("Major Employer", (47, 143, 107)),
]

LATLON = {
    "Alliance": (-97.31, 32.98), "DFW Airport": (-97.038, 32.897),
    "Las Colinas": (-96.957, 32.888), "Irving": (-96.9489, 32.814),
    "Uptown Dallas": (-96.802, 32.797), "Downtown Dallas": (-96.797, 32.7767),
    "North Dallas": (-96.80, 32.90), "South Dallas": (-96.785, 32.725),
    "Plano": (-96.6989, 33.0198), "Frisco": (-96.8236, 33.1507),
    "McKinney": (-96.6153, 33.1976), "Allen": (-96.6706, 33.1032),
    "Richardson": (-96.7297, 32.9483), "Garland": (-96.6389, 32.9126),
    "Mesquite": (-96.5989, 32.7668), "Rockwall": (-96.4597, 32.9312),
    "Red Oak": (-96.8047, 32.5182), "DeSoto": (-96.857, 32.5896),
    "Mansfield": (-97.1417, 32.5632), "Grand Prairie": (-96.995, 32.7459),
    "Arlington": (-97.1081, 32.7357), "Fort Worth": (-97.3308, 32.7555),
    "Denton": (-97.1331, 33.2148), "Duncanville": (-96.9083, 32.6518),
    "Blue Mound": (-97.3392, 32.8618), "Hutchins": (-96.7130, 32.6490),
    "Wilmer": (-96.6847, 32.5885), "Coppell": (-96.9900, 32.9546),
    "Carrollton": (-96.8900, 32.9756), "Lewisville": (-96.9944, 33.0462),
    "Kennedale": (-97.2258, 32.6407), "Forest Hill": (-97.2692, 32.6721),
    "Everman": (-97.2892, 32.6310), "Flower Mound": (-97.0570, 33.0146),
    "The Colony": (-96.8861, 33.0806), "Lancaster": (-96.7561, 32.5921),
    "Cedar Hill": (-96.9561, 32.5885), "Wylie": (-96.5386, 33.0151),
    "Rowlett": (-96.5639, 32.9029), "Balch Springs": (-96.6228, 32.7287),
    "Grapevine": (-97.0781, 32.9343), "Southlake": (-97.1342, 32.9412),
    "Haltom City": (-97.2692, 32.7996), "Roanoke": (-97.2258, 33.0040),
}
ALIASES = {
    "uptown": "Uptown Dallas", "downtown": "Downtown Dallas",
    "downtown dallas": "Downtown Dallas", "dallas": "Downtown Dallas",
    "north fort worth": "Alliance", "alliancetexas": "Alliance",
    "south fort worth": "Fort Worth", "las colinas / irving": "Las Colinas",
    "dfw airport submarket": "DFW Airport",
}


def _resolve(name):
    n = name.strip()
    if n in LATLON:
        return n
    return ALIASES.get(n.lower())


def _cat_color(cat):
    c = cat.strip().lower()
    if c in CATEGORY_COLORS:
        return CATEGORY_COLORS[c]
    for part in re.split(r"[/,]", c):
        if part.strip() in CATEGORY_COLORS:
            return CATEGORY_COLORS[part.strip()]
    return (90, 90, 90)


def px(lon, lat):
    return (A * lon + B, C * lat + D)


FONT_BOLD = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
             "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
             "C:/Windows/Fonts/arialbd.ttf", "/Library/Fonts/Arial Bold.ttf",
             "/usr/local/lib/python3.12/dist-packages/matplotlib/mpl-data/fonts/ttf/DejaVuSans-Bold.ttf"]
FONT_REG = ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "C:/Windows/Fonts/arial.ttf", "/Library/Fonts/Arial.ttf",
            "/usr/local/lib/python3.12/dist-packages/matplotlib/mpl-data/fonts/ttf/DejaVuSans.ttf"]


def _font(size, bold=True):
    for p in (FONT_BOLD if bold else FONT_REG):
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


def render(deals, out="dfw_map.png", date=None, base=BASE):
    im = Image.open(base).convert("RGBA")
    W, H = im.size
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)

    per_pt, missing = {}, []
    for dl in deals:
        color = _cat_color(dl.get("category", ""))
        for sm in dl.get("submarkets", []):
            key = _resolve(sm)
            if key is None:
                missing.append(sm)
                continue
            per_pt.setdefault(key, []).append((dl.get("n", ""), color))

    numf = _font(15, True)
    for key, marks in per_pt.items():
        x, y = px(*LATLON[key])
        # true-location dot
        od.ellipse([x - 4, y - 4, x + 4, y + 4], fill=(35, 39, 43, 255), outline=(255, 255, 255, 255), width=1)
        # offset numbered pins with leader lines (fan when several share a point)
        k = len(marks)
        span = 27 * (k - 1)
        ox, oy = x + 26, y - 28
        for i, (num, color) in enumerate(marks):
            mx = ox - span / 2 + i * 27
            my = oy
            od.line([x, y, mx, my], fill=(70, 74, 78, 200), width=2)
            r = 13
            od.ellipse([mx - r + 1, my - r + 2, mx + r + 1, my + r + 2], fill=(0, 0, 0, 70))
            od.ellipse([mx - r, my - r, mx + r, my + r], fill=color + (255,), outline=(255, 255, 255, 255), width=3)
            t = str(num)
            tb = od.textbbox((0, 0), t, font=numf)
            od.text((mx - (tb[2] - tb[0]) / 2, my - (tb[3] - tb[1]) / 2 - tb[1]), t, fill="white", font=numf)

    im = Image.alpha_composite(im, ov)
    d = ImageDraw.Draw(im)
    _legend_panel(d, date)
    if missing:
        print("Unresolved submarkets (add to LATLON or leave noted-not-mapped):", sorted(set(missing)))
    im.convert("RGB").save(out, quality=95)
    return out


def _legend_panel(d, date):
    tf, lf = _font(17, True), _font(12, False)
    x0, y0, w = 18, 18, 344
    rows = 5
    h = 40 + rows * 21
    d.rounded_rectangle([x0, y0, x0 + w, y0 + h], radius=10, fill=(255, 255, 255, 235),
                        outline=(210, 214, 218), width=1)
    title = "DFW deal map" if not date else "DFW deal map, " + date
    d.text((x0 + 14, y0 + 11), title, fill=(20, 24, 28), font=tf)
    colx = [x0 + 16, x0 + 182]
    for i, (label, color) in enumerate(LEGEND):
        col, row = i // rows, i % rows
        cx = colx[col]
        cy = y0 + 42 + row * 21 + 7
        d.ellipse([cx, cy - 6, cx + 12, cy + 6], fill=color, outline="white", width=1)
        d.text((cx + 18, cy - 8), label, fill=(70, 76, 82), font=lf)


if __name__ == "__main__":
    demo = [
        {"n": 1, "category": "Industrial", "submarkets": ["Alliance"]},
        {"n": 2, "category": "Industrial", "submarkets": ["Fort Worth"]},
        {"n": 3, "category": "IOS", "submarkets": ["Duncanville", "Blue Mound"]},
        {"n": 5, "category": "Data Center", "submarkets": ["Red Oak"]},
        {"n": 6, "category": "Data Center", "submarkets": ["Kennedale"]},
        {"n": 8, "category": "Data Center", "submarkets": ["Las Colinas"]},
        {"n": 10, "category": "Land", "submarkets": ["McKinney"]},
        {"n": 14, "category": "Major Employer", "submarkets": ["Richardson"]},
        {"n": 15, "category": "Office", "submarkets": ["Uptown Dallas"]},
        {"n": 17, "category": "Office", "submarkets": ["North Dallas"]},
        {"n": 18, "category": "Multifamily", "submarkets": ["Downtown Dallas", "Arlington", "Fort Worth"]},
        {"n": 19, "category": "Sports / Entertainment", "submarkets": ["North Dallas"]},
    ]
    render(demo, "dfw_map_demo.png", date="July 1, 2026")
    print("wrote dfw_map_demo.png")
