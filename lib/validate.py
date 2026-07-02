"""
Pre-render validator for the daily brief JSON. Fails loudly with exact locations
so the routine can fix its data file. Run automatically by build_brief.py.
"""
import re

REQUIRED = ["iso_date", "date", "window", "market_read", "temperature", "top3",
            "industrial_desk", "deal_watch", "broader", "capital", "national",
            "radar", "ammo", "watch", "move", "sources"]

TEMP_ORDER = ["Industrial", "Investment Sales", "Multifamily", "Office", "Retail",
              "Land / Development", "Debt / Capital Markets"]

INDUSTRIAL_LANES = {"industrial", "ios", "logistics", "manufacturing", "data center",
                    "power", "land", "infrastructure", "capital-industrial"}

BAD_DASHES = {"\u2014": "em dash", "\u2013": "en dash"}


def _walk(node, path="b"):
    if isinstance(node, dict):
        for k, v in node.items():
            yield from _walk(v, f"{path}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _walk(v, f"{path}[{i}]")
    elif isinstance(node, str):
        yield path, node


def validate(b):
    errors, warnings = [], []

    for k in REQUIRED:
        if k not in b:
            errors.append(f"missing required key: {k}")
    if errors:
        return errors, warnings

    # no em/en dashes anywhere in content
    for path, s in _walk(b):
        for ch, name in BAD_DASHES.items():
            if ch in s:
                i = s.index(ch)
                errors.append(f"{name} in {path}: ...{s[max(0,i-25):i+25]}...")

    # temperature: seven fixed rows in order
    sectors = [r.get("sector", "") for r in b["temperature"]]
    if sectors != TEMP_ORDER:
        errors.append(f"temperature rows must be exactly {TEMP_ORDER}, got {sectors}")

    # citations resolve
    n_src = len(b["sources"])
    cited = set()
    for path, s in _walk(b):
        if path.startswith("b.sources"):
            continue
        for m in re.finditer(r"\[(\d+(?:\s*,\s*\d+)*)\]", s):
            for num in re.findall(r"\d+", m.group(1)):
                num = int(num)
                cited.add(num)
                if num < 1 or num > n_src:
                    errors.append(f"citation [{num}] in {path} has no source (sources 1..{n_src})")
    uncited = sorted(set(range(1, n_src + 1)) - cited)
    if uncited:
        warnings.append(f"sources never cited in text: {uncited}")

    # top3: exactly 3, industrial leads (>= 2 industrial lanes)
    if len(b["top3"]) != 3:
        errors.append(f"top3 must have exactly 3 items, got {len(b['top3'])}")
    lanes = [str(it.get("lane", "")).strip().lower() for it in b["top3"]]
    if all(lanes):
        n_ind = sum(1 for l in lanes if l in INDUSTRIAL_LANES)
        if n_ind < 2:
            errors.append(f"Top Three rule: need >= 2 industrial-lane items, got {n_ind} ({lanes})")
    else:
        warnings.append("top3 items missing 'lane' key; Top Three rule not machine-checked")

    # deal_watch minimum fields
    for i, r in enumerate(b["deal_watch"]):
        for k in ("category", "submarket", "asset", "what", "src"):
            if not str(r.get(k, "")).strip():
                errors.append(f"deal_watch[{i}] missing '{k}'")

    # ammo: exactly 3
    if len(b.get("ammo", [])) != 3:
        errors.append(f"ammo must have exactly 3 items, got {len(b.get('ammo', []))}")

    # sources have full urls
    for i, s in enumerate(b["sources"]):
        if not str(s.get("url", "")).startswith("http"):
            errors.append(f"sources[{i}] missing full url (domain-only display is derived, full url is required)")

    return errors, warnings
