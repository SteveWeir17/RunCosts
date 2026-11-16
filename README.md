# RunCosts

Static site for https://runcosts.co.uk — UK appliance running costs.

- `data/appliances.csv` — the appliance list (typical wattage, usage, sources)
- `src/` — shared stylesheet and calculator script
- `build.py` — generates the site into `dist/`

## Update
1. Edit the price cap in `CAP` at the top of `build.py` (or the data in `data/appliances.csv`).
2. Run `python3 build.py`.
3. Commit and push, including `dist/`. Cloudflare Pages publishes `dist/` automatically.

`python3 build.py --preview` builds a version with `.html` links into `dist-preview/` for previewing without a server.
