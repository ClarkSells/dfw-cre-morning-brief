#!/usr/bin/env python3
"""
Build one morning brief from a data file.

    python lib/build_brief.py briefs_in/brief_2026-07-02.json           # -> briefs/2026/07/
    python lib/build_brief.py examples/brief_2026-07-02.json --outdir examples

The routine's only job is the JSON (schema in README). This script:
  1. validates the data (dash rule, citations, section contracts) and stops on errors
  2. computes each deal's New / Update / Carry status against the master log
  3. builds the Since-Last-Brief delta strip
  4. merges today's watch items into the persistent pipeline tracker
  5. renders the deal map (fixed base + numbered pins), Treasury chart, and optional bar panel
  6. fills the locked template, renders the PDF, enforces the 6-page cap
  7. writes the daily CSV and appends the master log
"""
import os, sys, csv, json, re, argparse, subprocess
from urllib.parse import urlparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dfw_map
import chart
import validate
from jinja2 import Environment, FileSystemLoader, select_autoescape

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TPL = os.path.join(REPO, "templates")
MASTER = os.path.join(REPO, "DFW_CRE_Master_Deal_Log.csv")
TRACKER = os.path.join(REPO, "data", "pipeline_tracker.json")
PAGE_CAP = 6
CSV_COLS = ["date", "id", "status", "category", "submarket", "asset", "parties",
            "what", "size", "angle", "src"]


def slugify(s, maxlen=48):
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s[:maxlen].rstrip("-")


def deals_from_watch(rows):
    out = []
    for r in rows:
        nums = re.findall(r"\d+", str(r.get("src", "")))
        subs = [s for s in re.split(r"\s*[/,]\s*", re.sub(r"\([^)]*\)", "", r.get("submarket", ""))) if s.strip()]
        out.append({"n": nums[0] if nums else "", "category": r.get("category", ""), "submarkets": subs})
    return out


def load_master():
    """id -> last recorded 'what' text."""
    seen = {}
    if os.path.exists(MASTER):
        with open(MASTER, newline="") as f:
            for row in csv.DictReader(f):
                if row.get("id"):
                    seen[row["id"]] = row.get("what", "")
    return seen


def assign_statuses(b, master):
    """Give every deal a stable id and a verified New/Update/Carry status."""
    for r in b["deal_watch"]:
        r.setdefault("id", slugify(r.get("asset", "") or r.get("what", "")))
        claimed = r.get("status", "").strip().title() or None
        if r["id"] not in master:
            actual = "New"
        elif r.get("what", "") != master[r["id"]]:
            actual = "Update"
        else:
            actual = "Carry"
        if claimed and claimed != actual:
            print(f"  status corrected: {r['id']}: routine said {claimed}, log says {actual}")
        r["status"] = actual


def merge_tracker(b, iso):
    """Upsert today's watch items into the persistent tracker; carry open items."""
    items = []
    if os.path.exists(TRACKER):
        items = json.load(open(TRACKER))
    by_id = {t["id"]: t for t in items}
    touched = set()
    for w in b.get("watch", []):
        wid = w.get("id") or slugify(w.get("catalyst", ""))
        touched.add(wid)
        status = w.get("status", "").title()
        if wid in by_id:
            t = by_id[wid]
            t.update({"date": w.get("date", t.get("date", "")),
                      "catalyst": w.get("catalyst", t.get("catalyst", "")),
                      "consequence": w.get("consequence", t.get("consequence", ""))})
            t["status"] = "Resolved" if status == "Resolved" else "Carry"
            if t["status"] == "Resolved":
                t["resolved"] = iso
        else:
            by_id[wid] = {"id": wid, "first_seen": iso, "status": "New",
                          "date": w.get("date", ""), "catalyst": w.get("catalyst", ""),
                          "consequence": w.get("consequence", "")}
    # untouched open items carry forward automatically
    for t in by_id.values():
        if t["id"] not in touched and t.get("status") != "Resolved":
            t["status"] = "Carry"
    live = [t for t in by_id.values() if t.get("status") != "Resolved" or t.get("resolved") == iso]
    os.makedirs(os.path.dirname(TRACKER), exist_ok=True)
    json.dump([t for t in by_id.values() if t.get("status") != "Resolved"],
              open(TRACKER, "w"), indent=2, ensure_ascii=False)
    return live


def build_delta(b, tracker, iso):
    d = {"new": [], "updated": [], "carried": [], "resolved": []}
    for r in b["deal_watch"]:
        name = r.get("asset", r["id"])
        {"New": d["new"], "Update": d["updated"], "Carry": d["carried"]}[r["status"]].append(name)
    for t in tracker:
        if t.get("status") == "Resolved" and t.get("resolved") == iso:
            d["resolved"].append(t["catalyst"])
    # keep the strip to one line per row type
    for k in d:
        if len(d[k]) > 6:
            d[k] = d[k][:6] + [f"and {len(d[k]) - 6} more"]
    return {k: v for k, v in d.items() if v}


def page_count(pdf_path):
    try:
        out = subprocess.run(["pdfinfo", pdf_path], capture_output=True, text=True).stdout
        m = re.search(r"Pages:\s+(\d+)", out)
        return int(m.group(1)) if m else None
    except FileNotFoundError:
        return None


def render_pdf(html_path, pdf_path):
    try:
        from weasyprint import HTML
        HTML(filename=html_path).write_pdf(pdf_path)
        return "weasyprint"
    except Exception:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            br = p.chromium.launch()
            pg = br.new_page()
            pg.goto("file://" + os.path.abspath(html_path))
            pg.pdf(path=pdf_path, format="Letter", print_background=True,
                   prefer_css_page_size=True,
                   margin={"top": "10mm", "bottom": "13mm", "left": "11mm", "right": "11mm"})
            br.close()
        return "chromium"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data")
    ap.add_argument("--outdir", default=None)
    args = ap.parse_args()

    b = json.load(open(args.data))

    errors, warnings = validate.validate(b)
    for w in warnings:
        print(f"  WARN: {w}")
    if errors:
        print("VALIDATION FAILED, fix the data file and rerun:")
        for e in errors:
            print(f"  ERROR: {e}")
        sys.exit(1)

    iso = b["iso_date"]
    yyyy, mm, _ = iso.split("-")
    outdir = args.outdir or os.path.join(REPO, "briefs", yyyy, mm)
    figs = os.path.join(outdir, "figs")
    os.makedirs(figs, exist_ok=True)

    master = load_master()
    assign_statuses(b, master)
    tracker = merge_tracker(b, iso)
    delta = build_delta(b, tracker, iso)

    dfw_map.render(deals_from_watch(b["deal_watch"]),
                   out=os.path.join(figs, "dfw_map.png"), date=b.get("date"))
    b.setdefault("map", {})["src"] = "figs/dfw_map.png"
    b["map"].setdefault("caption", "Fixed DFW base map with today's deals overlaid; numbered pins match the Src column. Base: OpenStreetMap via mapz.com.")

    ch = b["capital"]["chart"]
    chart.render_series(ch["data"], out=os.path.join(figs, "chart.png"),
                        label=ch.get("label", "10-Year U.S. Treasury Yield"))
    ch["src"] = "figs/chart.png"
    if b["capital"].get("bars"):
        bars = b["capital"]["bars"]
        chart.render_bars(bars["rows"], out=os.path.join(figs, "bars.png"),
                          title=bars.get("title", ""))
        bars["src"] = "figs/bars.png"

    for s in b["sources"]:
        s["domain"] = urlparse(s["url"]).netloc.replace("www.", "")

    env = Environment(loader=FileSystemLoader(TPL), autoescape=select_autoescape(["html"]))
    css = open(os.path.join(TPL, "brief.css")).read()
    html = env.get_template("brief.html.j2").render(b=b, css=css, delta=delta, tracker=tracker)
    html_path = os.path.join(outdir, f"DFW_CRE_Morning_Brief_{iso}.html")
    open(html_path, "w").write(html)

    pdf_path = os.path.join(outdir, f"DFW_CRE_Morning_Brief_{iso}.pdf")
    engine = render_pdf(html_path, pdf_path)

    pages = page_count(pdf_path)
    if pages and pages > PAGE_CAP:
        print(f"PAGE CAP EXCEEDED: rendered {pages} pages, cap is {PAGE_CAP}.")
        print("Cut the lowest-value Carry rows and trim Section 2 prose, then rerun.")
        sys.exit(1)

    day_csv = os.path.join(outdir, f"DFW_CRE_Deal_Log_{iso}.csv")
    def row_of(r):
        return {"date": iso, "id": r["id"], "status": r["status"],
                "category": r.get("category", ""), "submarket": r.get("submarket", ""),
                "asset": r.get("asset", ""), "parties": r.get("parties", ""),
                "what": r.get("what", ""), "size": r.get("size", ""),
                "angle": r.get("angle", ""), "src": r.get("src", "")}
    with open(day_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLS)
        w.writeheader()
        for r in b["deal_watch"]:
            w.writerow(row_of(r))
    new_master = not os.path.exists(MASTER)
    with open(MASTER, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLS)
        if new_master:
            w.writeheader()
        for r in b["deal_watch"]:
            w.writerow(row_of(r))

    print(f"[{engine}] {pages or '?'} pages. Wrote:")
    for p in (pdf_path, html_path, day_csv):
        print(f"  {p}")
    print(f"  appended {MASTER}; tracker updated ({len(tracker)} live items)")


if __name__ == "__main__":
    main()
