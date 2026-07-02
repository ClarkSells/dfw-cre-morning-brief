# DFW Industrial & CRE Morning Brief (v3)

Automated daily morning brief for a DFW investment-sales desk, industrial-first.
The routine researches and writes ONE JSON file per day; this repo's locked
pipeline validates it, renders the brief, and keeps the desk's memory (master
deal log and pipeline tracker). A push of the finished PDF triggers email
delivery via GitHub Actions.

## Structure

```
prompt/     DFW_Industrial_CRE_Morning_Brief_Instructions_v3.md   the spec the routine follows
assets/     dfw_base_map.jpg          fixed DFW base image (never changes)
lib/        build_brief.py            orchestrator: validate -> statuses -> tracker -> figures -> PDF -> logs
            validate.py               pre-render QA gate (dash rule, citations, section contracts)
            dfw_map.py                fixed base map + numbered daily pins
            chart.py                  Treasury line chart + bar panel
templates/  brief.html.j2, brief.css  the locked look (v3 condensed style)
data/       pipeline_tracker.json     persistent What-to-Watch state across runs
briefs_in/  daily JSON inputs from the routine
briefs/     rendered outputs land in briefs/YYYY/MM/
examples/   brief_2026-07-01.json and brief_2026-07-02.json + rendered July 2 PDF (canonical)
.github/workflows/email-brief.yml     emails each new PDF on push
DFW_CRE_Master_Deal_Log.csv           append-only desk memory (drives New/Update/Carry)
```

## Quickstart

```bash
pip install -r requirements.txt
python lib/build_brief.py examples/brief_2026-07-02.json --outdir examples
```

A daily run is `python lib/build_brief.py briefs_in/brief_YYYY-MM-DD.json`
(outputs go to `briefs/YYYY/MM/`). The script exits nonzero with exact
instructions if validation fails or the render exceeds 6 pages.

## The daily JSON schema

Top-level keys: `iso_date`, `date`, `weekday`, `window`, `market_read`,
`temperature` (7 fixed rows: `sector`, `signal`, `rationale`),
`top3` (3 items: `headline`, `lane`, `facts`, `why`, `implication`, `score`,
optional `image` {src, caption} OR `table` {title, rows [[label, value]], caption}),
`industrial_desk` (blocks: `label`, `body`, `inference`),
`deal_watch` (rows: `id` stable slug, optional `status`, `category`, `submarket`,
`asset`, `parties`, `what`, `size`, `angle`, `src` like `[4,5]`),
optional `broader_note`, `broader` (`cls`, `body`, optional `inference`),
`kpis` (3 cards: `label`, `value`, `sub`),
`capital` {`chart` {label, data [[YYYY-MM-DD, value]], caption},
optional `bars` {title, rows [[label, value]], caption}, `items` [{fact, translation}]},
`national` (2 to 4: `headline`, `what`, `why_national`, `why_dfw`),
`radar` (up to 3: `opportunity`, `asset`, `evidence`, `why`, `question`, `confidence`),
`ammo` (exactly 3 strings),
`watch` (rows: `id`, `date`, `catalyst`, `consequence`, optional `status`: `Resolved`),
`move`, `method_note`,
`sources` (`publisher`, `title`, `date`, full `url`, `accessed`).

Inline `[n]` citations in any text field must resolve to `sources`. The map,
status chips, delta strip, CSVs, and tracker all derive automatically.

## Desk memory

- **Master log** (`DFW_CRE_Master_Deal_Log.csv`): every deal row ever filed,
  keyed by `id`. The build compares today's rows against it to assign
  New / Update / Carry, which powers the status chips and the delta strip.
  Never edit by hand except to reset (keep the header line).
- **Pipeline tracker** (`data/pipeline_tracker.json`): open catalysts carry
  forward automatically; a `watch` row with `"status": "Resolved"` closes one
  and shows it as Closed in that day's brief.

## Delivery (email via GitHub Actions)

`.github/workflows/email-brief.yml` fires whenever a PDF lands under `briefs/`
and emails it. Set six repository secrets (Settings -> Secrets and variables ->
Actions): `SMTP_SERVER`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`,
`MAIL_FROM`, `MAIL_TO`. For Gmail use smtp.gmail.com, port 465, and an app
password; for Outlook use smtp.office365.com, port 587.

## The map

`assets/dfw_base_map.jpg` is the fixed picture (OpenStreetMap export via
mapz.com, attribution kept visible). `lib/dfw_map.py` composites numbered pins
at true submarket locations with leader lines and a ten-category legend; pin
numbers match the Src column. Coordinates are calibrated to this exact image via
the affine constants A, B, C, D; if the image is ever replaced, recalibrate.
Unknown submarkets are printed at build time; add lon/lat to LATLON or write the
row as "(noted, not mapped)".

## Rendering

WeasyPrint first, Playwright Chromium fallback (`prefer_css_page_size=True`,
margins matching the CSS `@page`). Page footers come from CSS margin boxes only.
Hard cap: 6 pages, enforced.

## Notes

- Set `--accent` in `templates/brief.css` to Strive's exact brand green.
- No API keys or tokens in the repo; put them in the routine's environment and
  the Actions secrets.
- To reset desk memory for a fresh start: truncate the master log to its header
  and delete `data/pipeline_tracker.json`.
