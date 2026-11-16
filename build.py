#!/usr/bin/env python3
"""RunCosts static site generator.

Usage:  python3 build.py            -> dist/          (production: clean URLs)
        python3 build.py --preview  -> dist-preview/  (.html links, preview banner)

Quarterly price-cap update: change CAP below, then re-run the build and upload dist/.
"""
import csv, html, json, os, re, shutil, sys
from datetime import date

# ------------------------------------------------------------------ settings
SITE_NAME = "RunCosts"
SITE_URL  = "https://runcosts.co.uk"
CAP = {
    "rate": 26.32,
    "period": "1 Oct – 31 Dec 2026",
    "label": "Ofgem price cap average for 1 Oct – 31 Dec 2026 (standard variable tariff, Direct Debit, England, Scotland & Wales).",
}
PREVIEW = "--preview" in sys.argv
# Ads, partner boxes and email sign-up only appear once they are real (or in preview builds).
SHOW_ADS = PREVIEW
SHOW_OFFERS = PREVIEW
SHOW_EMAIL = PREVIEW
EXT = ".html" if PREVIEW else ""
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "dist-preview" if PREVIEW else "dist")
DATA = os.path.join(HERE, "data", "appliances.csv")
TODAY = date.today().isoformat()
R = CAP["rate"]

esc = html.escape
def link(slug):
    if slug == "": return "index.html" if PREVIEW else "/"
    return slug + EXT
def money(p): return (f"{p:.1f}" if p < 10 else f"{round(p)}") + "p" if p < 100 else f"£{p/100:.2f}"
def pounds(p): return f"£{round(p/100):,}" if p >= 10000 else f"£{p/100:.2f}"
def mins(m):
    m = float(m)
    if m < 60: return (f"{m:g}") + " minutes"
    h, r = int(m // 60), round(m % 60)
    return f"{h} hour{'s' if h != 1 else ''}" + (f" {r} minutes" if r else "")
def slugify(s): return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")

# ------------------------------------------------------------------ wording
# Noun phrase used in questions; default is "a/an <name in lower case>".
PHRASE = {
 "ceramic-hob-per-ring": ("run", "a ceramic hob"), "induction-hob-per-zone": ("run", "an induction hob"),
 "tv-led-lcd": ("run", "a TV"), "oled-tv": ("run", "an OLED TV"),
 "christmas-lights-led": ("run", "Christmas lights"), "led-strip-lights": ("run", "LED strip lights"),
 "hair-straighteners": ("run", "hair straighteners"), "curling-tongs": ("run", "curling tongs"),
 "dehumidifier-compressor": ("run", "a dehumidifier"), "dehumidifier-desiccant": ("run", "a desiccant dehumidifier"),
 "cordless-vacuum-charging": ("charge", "a cordless vacuum"), "robot-vacuum-charging": ("charge", "a robot vacuum"),
 "electric-toothbrush-charging": ("charge", "an electric toothbrush"), "electric-shaver-charging": ("charge", "an electric shaver"),
 "electric-car-charging-home": ("charge", "an electric car at home"), "e-bike-charging": ("charge", "an e-bike"),
 "e-scooter-charging": ("charge", "an e-scooter"), "mobility-scooter-charging": ("charge", "a mobility scooter"),
 "electric-wheelchair-charging": ("charge", "an electric wheelchair"), "phone-charger": ("charge", "a phone"),
 "tablet-charger": ("charge", "a tablet"), "wi-fi-router": ("run", "a wi-fi router"),
 "electric-underfloor-heating": ("run", "electric underfloor heating"), "3d-printer": ("run", "a 3D printer"),
 "dvd-player": ("run", "a DVD player"), "led-bulb": ("run", "an LED bulb"),
}
UNIT = {"electric-blanket": "night", "heated-throw": "evening", "oil-filled-radiator": "day", "electric-fan-heater": "day",
        "convector-heater": "day", "electric-panel-heater": "day", "halogen-heater": "day", "infrared-heater": "day",
        "storage-heater": "night", "electric-towel-rail": "day", "electric-underfloor-heating": "day", "electric-fire": "evening",
        "dehumidifier-compressor": "day", "dehumidifier-desiccant": "day", "desk-fan": "day", "tower-fan": "day",
        "ceiling-fan": "day", "portable-air-conditioner": "day", "air-purifier": "day", "pond-pump": "day",
        "wi-fi-router": "day", "smart-speaker": "day", "fish-tank": "day", "baby-monitor": "night",
        "led-bulb": "day", "halogen-bulb": "day", "incandescent-bulb": "day", "christmas-lights-led": "day",
        "led-strip-lights": "day", "tv-led-lcd": "day", "oled-tv": "day", "desktop-computer": "day", "laptop": "day",
        "computer-monitor": "day", "air-fryer": "use", "cpap-machine": "night", "electric-toothbrush-charging": "day",
        "electric-wheelchair-charging": "charge", "mobility-scooter-charging": "charge", "e-bike-charging": "charge",
        "e-scooter-charging": "charge", "electric-car-charging-home": "charge", "cordless-vacuum-charging": "charge",
        "robot-vacuum-charging": "charge", "phone-charger": "charge", "tablet-charger": "charge",
        "electric-shaver-charging": "charge", "outdoor-security-light": "day", "immersion-heater": "day"}

INTRO = {
 "air-fryer": "Air fryers are small and heat up fast, so they usually cost much less per meal than a full-size electric oven.",
 "electric-oven": "A conventional electric oven heats a large box of air, which makes it one of the more expensive ways to cook a small meal.",
 "kettle": "A kettle draws a lot of power, but only for a few minutes. The cost depends on how much water you boil, not on the wattage.",
 "electric-blanket": "Electric blankets are one of the cheapest ways to stay warm in bed, because they heat you rather than the room.",
 "oil-filled-radiator": "Oil-filled radiators hold heat well, but every kWh of heat costs a kWh of electricity. That makes them expensive compared with gas central heating or a heat pump.",
 "dehumidifier-compressor": "Compressor dehumidifiers are fairly cheap to run. Desiccant models use more power but also give off some useful heat.",
 "tumble-dryer": "Tumble dryers are among the most expensive appliances in the home to run. Heat pump models use roughly half the energy of vented or condenser dryers.",
 "washing-machine": "Most of the energy goes into heating water, so wash temperature matters far more than the machine itself.",
 "dishwasher": "A full dishwasher on eco mode usually uses less energy and water than washing the same load by hand with hot water.",
 "fridge-freezer": "Fridge freezers run all year, so even a modest one adds up. The yearly kWh figure is printed on the energy label.",
}
TIPS = {
 "air-fryer": ["Don't preheat longer than the recipe needs, because most models are hot in 2–3 minutes.", "Cook in batches back to back while it's already hot.", "Larger baskets aren't less efficient as long as you fill them."],
 "electric-oven": ["Cook several things at once when the oven is on.", "Fan ovens can usually run about 20°C lower than conventional settings.", "Keep the door shut, because each opening loses a lot of heat."],
 "kettle": ["Boil only the water you need, because a full kettle takes roughly three times as long as one mug's worth.", "Descale regularly; limescale slows heating.", "Faster (higher-watt) kettles don't cost more per boil. The energy needed to heat the water is the same."],
 "electric-blanket": ["Pre-warm the bed, then switch to low or off.", "Use a timer or auto-off model.", "Check the blanket each season for wear, and replace it if wires show or it's over 10 years old."],
 "oil-filled-radiator": ["Use the thermostat rather than the highest setting.", "Heat one room with the door closed.", "For long-term heating, compare against a heat pump, which gives around three times more heat per kWh."],
 "dehumidifier-compressor": ["Set a target humidity (around 50%) rather than running it flat out.", "Run it in a closed room for best results.", "Placing it near drying laundry is often cheaper than a tumble dryer."],
 "tumble-dryer": ["Spin clothes at the highest speed your washing machine allows first.", "Don't overfill or underfill the drum.", "Clean the lint filter every cycle."],
 "washing-machine": ["Wash at 30°C, which uses much less energy than 40°C; modern detergents work fine.", "Eco cycles run longer but use less energy.", "Run full loads."],
 "dishwasher": ["Use the eco programme.", "Only run it full.", "Skip pre-rinsing under the hot tap."],
 "fridge-freezer": ["Find the kWh/annum figure on the energy label and set the slider to match.", "Keep the fridge at 3–5°C and the freezer at −18°C.", "Leave space behind for air to circulate, and defrost the freezer if ice builds up."],
}
CAT_TIPS = {
 "Kitchen": ["Use the smallest appliance that does the job: a microwave or air fryer usually beats the oven for small portions.", "Turn things off at the wall if they sit on standby all day.", "Check the energy label when you replace an appliance; running costs over its life often outweigh the price difference."],
 "Laundry": ["Wash at 30°C and run full loads.", "Spin at the highest speed the fabric allows before drying.", "Dry outside or on an airer when you can; heat is the expensive part."],
 "Heating": ["Heat the room you're in, with the door shut, rather than the whole house.", "Use the thermostat and a timer rather than the highest setting.", "Heating yourself (a blanket or heated throw) costs far less than heating the air."],
 "Cooling & air": ["Run it on the lowest setting that does the job.", "Close curtains on the sunny side during the day.", "Use a timer so it isn't left running in an empty room."],
 "Cleaning & garden": ["Corded tools only draw power while running, so costs are small; it's runtime that adds up.", "Charge cordless tools when needed, not continuously.", "Keep filters and blades clean so motors work less hard."],
 "Personal care": ["Most of these cost pennies; the bigger users are anything that heats, like hair dryers.", "Unplug chargers once devices are full.", "Use a lower heat setting where it does the job."],
 "Entertainment & tech": ["Switch off at the wall rather than leaving devices on standby.", "Turn down screen brightness; it's often the biggest single draw on a TV.", "Use power-saving or eco modes on consoles and computers."],
 "Transport": ["Charge on an off-peak or EV tariff if you have one; it can cut the cost by more than half.", "Avoid leaving batteries on charge long after they're full.", "Enter your actual off-peak rate using the rate button to see your real cost."],
 "Lighting": ["Swap halogen and old-style bulbs for LEDs, which use around 80–90% less.", "Use timers or smart plugs for decorative lighting.", "Turn lights off in empty rooms."],
 "Other": ["Check the power rating on the plug or label for the most accurate figure.", "A plug-in energy monitor shows exactly what a device uses.", "Turn things off at the wall when not in use."],
}
OFFER = {"Heating": "lead", "tumble-dryer": "dryer", "washer-dryer": "dryer", "electric-car-charging-home": "ev"}

# ------------------------------------------------------------------ data
apps = []
for r in csv.DictReader(open(DATA, encoding="utf-8")):
    f = lambda k: float(r[k]) if r.get(k) not in (None, "") else None
    a = dict(name=r["appliance"], slug=r["slug"], cat=r["category"], mode=r["mode"], d=f("default"), lo=f("min"), hi=f("max"),
             mins=f("mins_per_use"), uses=f("uses_per_week"), duty=f("duty") or 1.0, mo=int(float(r["months_per_year"] or 12)),
             source=r["source"], note=r["note"])
    verb, noun = PHRASE.get(a["slug"], ("run", ("an " if a["name"][0].lower() in "aeiou" else "a ") + a["name"].lower()))
    a["verb"], a["noun"] = verb, noun
    a["unit"] = "cycle" if a["mode"] == "cycle" else UNIT.get(a["slug"], "use")
    if a["mode"] == "power":
        a["kwh_use"] = a["d"] / 1000 * a["mins"] / 60 * a["duty"]
        a["kwh_year"] = a["kwh_use"] * a["uses"] * 52 * a["mo"] / 12
    elif a["mode"] == "cycle":
        a["kwh_use"] = a["d"]; a["kwh_year"] = a["d"] * a["uses"] * 52 * a["mo"] / 12
    else:
        a["kwh_use"] = None; a["kwh_year"] = a["d"]
    a["year_p"] = a["kwh_year"] * R
    a["use_p"] = a["kwh_use"] * R if a["kwh_use"] is not None else None
    a["title_q"] = f"How much does it cost to {verb} {noun}?"
    apps.append(a)
by_slug = {a["slug"]: a for a in apps}
cats = []
for a in apps:
    if a["cat"] not in cats: cats.append(a["cat"])
cat_slug = {c: "category-" + slugify(c) for c in cats}

def headline(a):
    if a["mode"] == "annual":
        return f'<span data-kwhy="{a["kwh_year"]:.4f}">{pounds(a["year_p"])} a year</span>'
    return f'<span data-kwh="{a["kwh_use"]:.5f}" data-unit="{a["unit"]}">{money(a["use_p"])} per {a["unit"]}</span>'

# ------------------------------------------------------------------ layout
def page(title, desc, path, body, extra_head=""):
    canon = SITE_URL + ("/" if path == "" else "/" + path)
    banner = '<div class="preview">Preview build: ads, partner links and email sign-up are placeholders.</div>' if PREVIEW else ""
    return f"""<!DOCTYPE html>
<html lang="en-GB">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{canon}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:type" content="website">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,700;9..40,800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="style.css">
{extra_head}
</head>
<body>
{banner}
<header><div class="bar"><a class="logo" href="{link('')}">Run<span>Costs</span></a>
<button class="ratechip" id="rateChip" type="button">{R:.2f}p/kWh</button></div></header>
<main>
{body}
</main>
<footer>
<p><a href="{link('how-we-calculate')}">How we calculate</a> · <a href="{link('about')}">About</a> · <a href="{link('privacy')}">Privacy &amp; cookies</a></p>
<p>Costs use the {esc(CAP['label'])} Your rate may differ: tap the rate at the top of any page to use your own. Figures are estimates for typical appliances; check your appliance's label for its actual power.</p>
</footer>
<dialog id="rateDlg"><div class="dlg">
<h2 style="margin-top:0">Your electricity unit rate</h2>
<p class="note">This is the pence per kWh on your bill or app. Don't use the standing charge: you pay that whether an appliance is on or not. On Economy 7 or an EV tariff, use the rate for the time the appliance runs.</p>
<p><input id="rateInput" type="number" step="0.01" min="1" max="200" inputmode="decimal"> p/kWh</p>
<p class="note">Default: {esc(CAP['label'])} {R}p/kWh.</p>
<div class="row"><button class="btn solid" id="rateSave" type="button">Use this rate</button>
<button class="btn" id="rateReset" type="button">Reset to price cap</button>
<button class="btn" id="rateClose" type="button">Close</button></div>
</div></dialog>
<script>window.RC_CAP={json.dumps({"rate": R, "label": CAP["label"]})};</script>
<script src="calc.js"></script>
</body>
</html>"""

def email_box():
    if not SHOW_EMAIL: return ""
    return """<div class="card" style="margin-top:26px"><b>Get an email when the price cap changes</b>
<p class="note" style="margin:4px 0 0">One email a quarter showing what your appliances will cost under the new rates.</p>
<form class="email" data-email><input type="email" placeholder="you@example.com" aria-label="Email address" required><button class="btn solid">Notify me</button></form><div class="msg"></div></div>"""

def ad(label): return "" if not SHOW_ADS else f'<div class="slot"><b>Ad slot</b>{label}</div>'

def offer_box(a):
    if not SHOW_OFFERS: return ""
    kind = OFFER.get(a["slug"]) or OFFER.get(a["cat"]) or "plug"
    if kind == "lead":
        return """<div class="offer"><span class="tag">Lead form placeholder</span>
<p><b>Spending a lot on electric heating?</b> A heat pump delivers roughly three times the heat per kWh. Get free quotes from approved local installers.</p>
<button class="btn solid" type="button" data-proto>Get quotes</button><div class="msg"></div></div>"""
    if kind == "dryer":
        return """<div class="offer"><span class="tag">Affiliate placeholder</span>
<p><b>Switch to a heat pump dryer:</b> at around 1.8 kWh a cycle it would cost about <b id="hpCost"></b> a year at your usage, saving roughly <b id="hpSave"></b>.</p>
<button class="btn solid" type="button" data-proto>See heat pump dryers</button><div class="msg"></div></div>"""
    if kind == "ev":
        return """<div class="offer"><span class="tag">Affiliate placeholder</span>
<p><b>Charging at the standard rate?</b> EV tariffs offer cheap overnight electricity. Enter your off-peak rate with the rate button to see the difference.</p>
<button class="btn solid" type="button" data-proto>Compare EV tariffs</button><div class="msg"></div></div>"""
    return f"""<div class="offer"><span class="tag">Affiliate placeholder</span>
<p><b>Want your real figure?</b> A smart plug with energy monitoring shows exactly what your {esc(a['noun'].split(' ',1)[-1] if a['noun'].startswith(('a ','an ')) else a['noun'])} uses.</p>
<button class="btn solid" type="button" data-proto>See energy-monitoring plugs</button><div class="msg"></div></div>"""

# ------------------------------------------------------------------ appliance pages
def auto_intro(a):
    seasonal = f", for {a['mo']} months of the year" if a["mode"] != "annual" and a["mo"] < 12 else ""
    if a["mode"] == "power":
        rng = f" ({a['lo']:,.0f}–{a['hi']:,.0f}W depending on the model)" if a["lo"] != a["hi"] else ""
        freq = f"{a['uses']:g} {a['unit']}{'s' if a['uses'] != 1 else ''} a week"
        bare = a['noun'].split(' ',1)[1] if a['noun'].startswith(('a ','an ')) else a['noun']
        first = (f"Charging {a['noun']} typically draws about {a['d']:,.0f} watts{rng}. " if a["verb"] == "charge"
                 else f"A typical {bare} uses about {a['d']:,.0f} watts{rng}. ")
        return (first +
                f"Used for {mins(a['mins'])} per {a['unit']}, {freq}{seasonal}, it costs about {money(a['use_p'])} per {a['unit']} "
                f"and {pounds(a['year_p'])} a year at the current price cap rate.")
    if a["mode"] == "cycle":
        return (f"A typical {a['name'].lower()} uses about {a['d']:g} kWh per cycle ({a['lo']:g}–{a['hi']:g} kWh depending on the model and programme). "
                f"That's about {money(a['use_p'])} a cycle, or {pounds(a['year_p'])} a year at {a['uses']:g} cycles a week, at the current price cap rate.")
    return (f"A typical {a['name'].lower()} uses about {a['d']:g} kWh a year ({a['lo']:g}–{a['hi']:g} kWh depending on size and efficiency). "
            f"At the current price cap rate that's about {pounds(a['year_p'])} a year, or {pounds(a['year_p']/12)} a month.")

def faqs(a):
    q = []
    noun = a["noun"]
    if a["mode"] == "power":
        hour = a["d"] / 1000 * a["duty"] * R
        q.append((f"How much does it cost to {a['verb']} {noun} per hour?",
                  f"At {R}p/kWh, a {a['d']:g}W model costs about {money(hour)} an hour" + (f", allowing for it running at full power about {a['duty']:.0%} of the time." if a["duty"] < 1 else " while it's running.")))
    if a["mode"] != "annual":
        q.append((f"How much does it cost to {a['verb']} {noun} per year?",
                  f"About {pounds(a['year_p'])} a year, based on {auto_usage(a)}. Change the sliders above to match how you use yours."))
    else:
        q.append((f"How much does it cost to {a['verb']} {noun} per month?", f"About {pounds(a['year_p']/12)} a month for a model using {a['d']:g} kWh a year, at {R}p/kWh."))
    q.append(("Is the standing charge included?", "No. You pay the standing charge every day whether or not the appliance is used, so it isn't part of the cost of running it."))
    q.append((f"How do I find my {noun.split(' ',1)[1] if noun.startswith(('a ','an ')) else noun}'s actual power use?",
              "Check the rating label, plug or manual for the wattage, or the energy label for kWh figures. A plug-in energy monitor shows exactly what it uses."))
    return q

def auto_usage(a):
    if a["mode"] == "power":
        s = f"{mins(a['mins'])} per {a['unit']}, {a['uses']:g} {a['unit']}{'s' if a['uses'] != 1 else ''} a week"
    else:
        s = f"{a['uses']:g} cycles a week"
    return s + (f", {a['mo']} months a year" if a["mo"] < 12 else "")

def similar(a, n=6):
    pool = [b for b in apps if b["cat"] == a["cat"] and b is not a]
    pool.sort(key=lambda b: abs(b["year_p"] - a["year_p"]))
    pick = sorted(pool[:n], key=lambda b: b["year_p"])
    rows = "".join(f'<tr><td><a href="{link(b["slug"])}">{esc(b["name"])}</a></td><td class="n">{headline(b)}</td></tr>' for b in pick)
    return f'<table>{rows}</table>'

def appliance_page(a):
    data = {"mode": a["mode"], "duty": a["duty"], "mo": a["mo"], "unit": a["unit"]}
    if a["mode"] == "power":
        span = a["hi"] - a["lo"]
        wstep = 1 if span <= 20 else 5 if span <= 200 else 10 if span <= 1000 else 50 if span <= 4000 else 100
        mmax = max(a["mins"] * 3, 30)
        mmax = 1440 if a["mins"] >= 480 else min(mmax, 720)
        mstep = 0.5 if a["mins"] < 5 else 1 if mmax <= 60 else 5 if mmax <= 240 else 15
        data.update(w=[a["lo"], a["hi"], a["d"], wstep], m=[mstep, mmax, a["mins"], mstep], u=[1, max(14, a["uses"] * 2), a["uses"], 1])
    elif a["mode"] == "cycle":
        data.update(k=[a["lo"], a["hi"], a["d"], 0.05], u=[1, 14, a["uses"], 1])
    else:
        data.update(y=[a["lo"], a["hi"], a["d"], 5])
    intro = INTRO.get(a["slug"])
    tips = TIPS.get(a["slug"], CAT_TIPS[a["cat"]])
    fq = faqs(a)
    ld = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": ans}} for q, ans in fq]}
    crumbs_ld = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "All appliances", "item": SITE_URL + "/"},
        {"@type": "ListItem", "position": 2, "name": a["cat"], "item": SITE_URL + "/" + cat_slug[a["cat"]]},
        {"@type": "ListItem", "position": 3, "name": a["name"]}]}
    head = f'<script type="application/ld+json">{json.dumps(ld)}</script><script type="application/ld+json">{json.dumps(crumbs_ld)}</script>'
    if a["mode"] == "annual":
        lab, big, sub = "Cost per year", pounds(a["year_p"]), f"About {pounds(a['year_p']/12)} a month at {R:.2f}p/kWh."
    else:
        lab, big = f"Cost per {a['unit']}", money(a["use_p"])
        sub = f"About {pounds(a['year_p'])} a year at {auto_usage(a)}."
    note = f'<p><b>Worth knowing:</b> {esc(a["note"].rstrip('.'))}.</p>' if a["note"] else ""
    body = f"""
<div class="crumbs"><a href="{link('')}">All appliances</a> › <a href="{link(cat_slug[a['cat']])}">{esc(a['cat'])}</a> › {esc(a['name'])}</div>
<h1>{esc(a['title_q'])}</h1>
<p class="lede">{esc(intro) if intro else esc(auto_intro(a))}</p>
<div class="two">
 <div>
  <div class="answer" aria-live="polite"><div class="lab" id="ansLab">{lab}</div><div class="big" id="ansBig">{big}</div><div class="sub" id="ansSub">{esc(sub)}</div></div>
  <div class="card" style="margin-top:12px"><table class="costs" id="tbl"></table>
  <p class="note" style="margin-bottom:0">Standing charge not included.</p></div>
 </div>
 <div class="card"><b>Adjust for yours</b>
  <div id="controls"><noscript><p class="note">Turn on JavaScript to adjust the figures.</p></noscript></div>
  <div class="ctl"><label>Your unit rate<output id="rateNow">{R:.2f}p/kWh</output></label><small id="rateWhat">{esc(CAP['label'])}</small>
  <button class="btn" type="button" data-rate style="margin-top:8px">Change rate</button></div>
  <button class="btn" type="button" id="resetBtn">Reset to typical</button>
 </div>
</div>
{offer_box(a)}
{ad("Display ad (in-content)")}
<h2>About these figures</h2>
{('<p>' + esc(auto_intro(a)) + '</p>') if intro else ''}
{note}
<p class="note">Source for the typical figure: {esc(a['source'])}. See <a href="{link('how-we-calculate')}">how we calculate</a>.</p>
<h2>Ways to cut the cost</h2>
<ul class="tips">{''.join(f'<li>{esc(t)}</li>' for t in tips)}</ul>
<h2>Compare with similar {esc(a['cat'].lower())} costs</h2>
<div class="card">{similar(a)}</div>
<h2>Questions</h2>
<div class="faq">{''.join(f'<details><summary>{esc(q)}</summary><p>{esc(ans)}</p></details>' for q, ans in fq)}</div>
{email_box()}
<script type="application/json" id="appdata">{json.dumps(data)}</script>"""
    who = a["noun"]
    desc = (f"What it costs to {a['verb']} {who} in the UK: about {big} per {a['unit']}" if a["mode"] != "annual" else f"What it costs to run {who} in the UK: about {big} a year") + \
           f" at the {CAP['period']} price cap. Adjust for your own model, usage and tariff."
    title = f"How much does it cost to {a['verb']} {who}? (UK {CAP['period'][-4:]}) – {SITE_NAME}"
    return page(title, desc, a["slug"], body, head)

# ------------------------------------------------------------------ index pages
def cat_list(c, limit=None):
    items = [a for a in apps if a["cat"] == c]
    lis = "".join(f'<li><a href="{link(a["slug"])}">{esc(a["name"])}</a><span>{headline(a)}</span></li>' for a in items[:limit])
    return f'<section><h3><a href="{link(cat_slug[c])}">{esc(c)}</a></h3><ul>{lis}</ul></section>'

def home():
    top = sorted(apps, key=lambda a: -a["year_p"])[:10]
    toprows = "".join(f'<tr><td><a href="{link(a["slug"])}">{esc(a["name"])}</a></td><td class="n"><span data-kwhy="{a["kwh_year"]:.4f}">{pounds(a["year_p"])} a year</span></td></tr>' for a in top)
    search_items = "".join(f'<a class="tile" href="{link(a["slug"])}" data-n="{esc(a["name"].lower())} {esc(a["cat"].lower())}"><div class="n">{esc(a["name"])}</div><div class="c">{headline(a)}</div></a>' for a in apps)
    body = f"""
<h1>How much does it cost to run?</h1>
<p class="lede">Running costs for {len(apps)} household appliances at <b data-rateval>{R:.2f}p/kWh</b>. Pick one, then adjust for your own model, usage and tariff.</p>
<input class="search" id="q" type="search" placeholder="Search appliances, e.g. air fryer" aria-label="Search appliances">
<div class="grid" id="results" hidden>{search_items}</div>
<div id="browse">
<div class="cats">{''.join(cat_list(c) for c in cats)}</div>
{ad("Display ad (homepage)")}
<h2>The biggest costs in a typical home</h2>
<div class="card"><table>{toprows}</table><p class="note" style="margin-bottom:0">Typical usage; heating items assume winter use only.</p></div>
</div>
{email_box()}
<script>
(function(){{var q=document.getElementById("q"),r=document.getElementById("results"),b=document.getElementById("browse");
q.addEventListener("input",function(){{var t=q.value.trim().toLowerCase();r.hidden=!t;b.hidden=!!t;
r.querySelectorAll(".tile").forEach(function(el){{el.style.display=el.dataset.n.indexOf(t)>-1?"":"none"}})}})}})();
</script>"""
    return page(f"How much does it cost to run? UK appliance running costs {CAP['period'][-4:]} – {SITE_NAME}",
                f"Find out what {len(apps)} household appliances cost to run in the UK at the current Ofgem price cap, then adjust for your own usage and tariff.",
                "", body)

def category(c):
    items = sorted([a for a in apps if a["cat"] == c], key=lambda a: -a["year_p"])
    rows = "".join(f'<tr><td><a href="{link(a["slug"])}">{esc(a["name"])}</a></td><td class="n">{headline(a)}</td><td class="n"><span data-kwhy="{a["kwh_year"]:.4f}">{pounds(a["year_p"])} a year</span></td></tr>' for a in items)
    body = f"""
<div class="crumbs"><a href="{link('')}">All appliances</a> › {esc(c)}</div>
<h1>{esc(c)} appliance running costs</h1>
<p class="lede">What {len(items)} {esc(c.lower())} appliances cost to run at <b data-rateval>{R:.2f}p/kWh</b>, most expensive per year first. Tap one to adjust for your own usage.</p>
<div class="card"><table><tr><th>Appliance</th><th class="n">Typical cost</th><th class="n">Per year</th></tr>{rows}</table></div>
{ad("Display ad (category)")}
<h2>Ways to cut {esc(c.lower())} costs</h2>
<ul class="tips">{''.join(f'<li>{esc(t)}</li>' for t in CAT_TIPS[c])}</ul>"""
    return page(f"{c} appliance running costs (UK) – {SITE_NAME}",
                f"Running costs for {len(items)} {c.lower()} appliances in the UK at the current price cap, from most to least expensive.",
                cat_slug[c], body)

def simple(path, title, h1, inner, desc):
    return page(f"{title} – {SITE_NAME}", desc, path, f'<div class="crumbs"><a href="{link("")}">All appliances</a> › {esc(h1)}</div><h1>{esc(h1)}</h1><div class="card">{inner}</div>')

METHOD = f"""<p><b>Appliances measured in watts:</b> cost = power (kW) × hours used × share of time at full power × your unit rate. Thermostatic appliances such as ovens and heaters switch on and off, so each page states the share it assumes.</p>
<p><b>Appliances that run in cycles</b> (washing machines, dishwashers, tumble dryers): cost = kWh per cycle × your unit rate. Use the figure on your energy label for accuracy.</p>
<p><b>Always-on appliances</b> (fridges and freezers): cost = kWh per year from the energy label × your unit rate.</p>
<p><b>Seasonal appliances:</b> heaters, dehumidifiers and fans are counted only for the months they're typically used. You can change this on each page.</p>
<p><b>Unit rate:</b> the default is the {esc(CAP['label'])}: {R}p/kWh. Fixed, Economy 7, EV and other time-of-use tariffs, and regional rates, differ, so you can enter your own; we remember it on your device.</p>
<p><b>Standing charge:</b> not included, because you pay it whether the appliance is used or not.</p>
<p><b>Typical figures:</b> default wattages come from the Centre for Sustainable Energy's "What uses watt?" table where it lists the appliance, and from typical manufacturer ranges otherwise. Each page names its source.</p>
<p style="margin-bottom:0">Last updated {TODAY}.</p>"""
ABOUT = f"""<p>{SITE_NAME} answers one question for everyday household appliances: what does it cost to run? Every page starts from typical figures, then lets you set your own appliance's power, how you use it and your own electricity rate.</p>
<p style="margin-bottom:0">Some pages contain adverts and links to partners, which may pay us a commission. This never changes the running-cost figures.</p>"""
PRIVACY = """<p><b>Placeholder: needs a proper policy before launch.</b></p>
<p>The calculator stores your chosen electricity rate in your browser so it's remembered between pages. It never leaves your device.</p>
<p style="margin-bottom:0">Advertising, analytics and email sign-up will be described here when they're added, along with a cookie consent banner where required.</p>"""

# ------------------------------------------------------------------ write
shutil.rmtree(OUT, ignore_errors=True); os.makedirs(OUT)
def w(name, s): open(os.path.join(OUT, name), "w", encoding="utf-8").write(s)
for f in ("style.css", "calc.js"): shutil.copy(os.path.join(HERE, "src", f), OUT)
w("index.html", home())
for c in cats: w(cat_slug[c] + ".html", category(c))
for a in apps: w(a["slug"] + ".html", appliance_page(a))
w("how-we-calculate.html", simple("how-we-calculate", "How we calculate", "How we calculate running costs", METHOD, "How " + SITE_NAME + " works out appliance running costs."))
w("about.html", simple("about", "About", "About " + SITE_NAME, ABOUT, "About " + SITE_NAME + "."))
w("privacy.html", simple("privacy", "Privacy and cookies", "Privacy and cookies", PRIVACY, "Privacy and cookie information."))
w("404.html", page("Page not found – " + SITE_NAME, "Page not found.", "404", f'<h1>Page not found</h1><p><a href="{link("")}">See all appliances</a></p>'))
urls = [""] + [cat_slug[c] for c in cats] + [a["slug"] for a in apps] + ["how-we-calculate", "about"]
w("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
  "".join(f"  <url><loc>{SITE_URL}/{u}</loc><lastmod>{TODAY}</lastmod></url>\n" for u in urls) + "</urlset>\n")
w("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n")
print(f"Built {len(os.listdir(OUT))} files into {OUT}")
