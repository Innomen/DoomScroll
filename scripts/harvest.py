#!/usr/bin/env python3
"""
harvest.py — The Doom That Wasn't
Reads curator.txt, fetches Wikipedia articles, parses their tables,
and appends new entries to data/doom.json.

Usage:
    python scripts/harvest.py                  # dry run, prints what it found
    python scripts/harvest.py --write          # actually appends to data/doom.json
    python scripts/harvest.py --write --limit 20   # cap at 20 new entries
"""

import json
import re
import sys
import time
import argparse
import urllib.request
import urllib.parse
from pathlib import Path
from html.parser import HTMLParser

# ── Paths ──────────────────────────────────────────────────────────────────────
ROOT       = Path(__file__).parent.parent
DOOM_JSON  = ROOT / "data" / "doom.json"
CURATOR    = ROOT / "curator.txt"

# ── Category mapping ───────────────────────────────────────────────────────────
VALID_CATEGORIES = [
    "Economic Collapse",
    "Tech Apocalypse",
    "Environmental Doom",
    "Political Catastrophe",
    "Health Crisis",
    "Social Breakdown",
    "Food & Resource Scarcity",
    "War & Conflict",
]

# Simple keyword → category guesser (for Wikipedia rows that don't specify)
CATEGORY_KEYWORDS = {
    "Economic Collapse":     ["economy", "financial", "stock", "crash", "bank", "depression", "debt", "dollar", "inflation", "recession"],
    "Tech Apocalypse":       ["computer", "internet", "ai", "robot", "nuclear plant", "technology", "software", "cyber", "y2k"],
    "Environmental Doom":    ["climate", "ozone", "pollution", "asteroid", "comet", "flood", "ice age", "warming", "cooling", "sea level", "extinction", "biodiversity"],
    "Political Catastrophe": ["war", "election", "government", "fascism", "communism", "dictatorship", "coup", "democracy"],
    "Health Crisis":         ["pandemic", "plague", "virus", "disease", "epidemic", "flu", "cancer", "aids", "ebola", "bacteria"],
    "Social Breakdown":      ["crime", "drugs", "violence", "moral", "youth", "media", "society", "culture"],
    "Food & Resource Scarcity": ["food", "famine", "hunger", "water", "oil", "energy", "resource", "population", "starvation"],
    "War & Conflict":        ["nuclear war", "world war", "armageddon", "invasion", "missile", "bomb", "military"],
}

def guess_category(text):
    text = text.lower()
    scores = {cat: 0 for cat in VALID_CATEGORIES}
    for cat, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                scores[cat] += 1
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "Political Catastrophe"

# ── Wikipedia fetch ────────────────────────────────────────────────────────────
WIKI_API = "https://en.wikipedia.org/w/api.php"
HEADERS  = {"User-Agent": "DoomScroll/1.0 (https://github.com/innomen/DoomScroll; open source project)"}

def wiki_fetch_html(page_title):
    """Fetch parsed HTML for a Wikipedia article via the API."""
    params = urllib.parse.urlencode({
        "action":      "parse",
        "page":        page_title,
        "prop":        "text",
        "formatversion": "2",
        "format":      "json",
    })
    url = f"{WIKI_API}?{params}"
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode())
    if "error" in data:
        raise ValueError(f"Wikipedia error: {data['error'].get('info', data['error'])}")
    return data["parse"]["text"]

# ── HTML table parser ──────────────────────────────────────────────────────────
class TableParser(HTMLParser):
    """Minimal HTML table parser — returns list of rows, each row a list of cell text."""
    def __init__(self):
        super().__init__()
        self.tables = []
        self._current_table = None
        self._current_row = None
        self._current_cell = None
        self._depth = 0  # track nested tables

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self._depth += 1
            if self._depth == 1:
                self._current_table = []
        elif tag in ("tr",) and self._depth == 1:
            self._current_row = []
        elif tag in ("td", "th") and self._depth == 1 and self._current_row is not None:
            self._current_cell = []

    def handle_endtag(self, tag):
        if tag == "table":
            if self._depth == 1 and self._current_table is not None:
                self.tables.append(self._current_table)
                self._current_table = None
            self._depth -= 1
        elif tag == "tr" and self._depth == 1:
            if self._current_row and self._current_table is not None:
                self._current_table.append(self._current_row)
            self._current_row = None
        elif tag in ("td", "th") and self._depth == 1:
            if self._current_cell is not None and self._current_row is not None:
                self._current_row.append(" ".join(self._current_cell).strip())
            self._current_cell = None

    def handle_data(self, data):
        if self._current_cell is not None:
            stripped = data.strip()
            if stripped:
                self._current_cell.append(stripped)

def extract_tables(html):
    parser = TableParser()
    parser.feed(html)
    return parser.tables

def clean(text):
    """Strip citations like [1], [note 2], extra whitespace."""
    text = re.sub(r'\[\d+\]', '', text)
    text = re.sub(r'\[note \d+\]', '', text)
    text = re.sub(r'\[a\]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def slugify(text, year=""):
    s = re.sub(r'[^a-z0-9]+', '-', (str(year) + "-" + text[:40]).lower())
    return s.strip('-')

# ── Row → entry conversion ─────────────────────────────────────────────────────
def row_to_entry(row, hint, existing_ids):
    """
    Try to turn a table row into a doom.json entry.
    Supports two common Wikipedia table shapes:
      Shape A: Date | Claimant | Claim | Outcome   (apocalyptic events article)
      Shape B: Year | Prediction | Source | Outcome (more generic)
    Returns None if the row doesn't look usable.
    """
    if len(row) < 3:
        return None

    # Flatten and clean all cells
    cells = [clean(c) for c in row]

    # Skip header rows
    if any(h in cells[0].lower() for h in ["date", "year", "century", "event", "prediction"]):
        return None

    # Skip rows that are clearly section dividers (single merged cell etc.)
    if len(cells) < 3 or not cells[0]:
        return None

    # Try to extract year from first cell
    year_match = re.search(r'\b(1[0-9]{3}|20[0-2][0-9])\b', cells[0])
    if not year_match:
        return None
    year = int(year_match.group(1))

    # Must be in the past
    if year >= 2026:
        return None

    # Shape detection: if cell[1] looks like a person/org name and cell[2] is longer, it's Shape A
    if len(cells) >= 4:
        claimant   = cells[1]
        prediction = cells[2]
        outcome    = cells[3] if len(cells) > 3 else ""
    else:
        claimant   = cells[1]
        prediction = cells[1]
        outcome    = cells[2] if len(cells) > 2 else ""

    if not prediction or len(prediction) < 15:
        return None

    # Build the entry
    entry_id = slugify(claimant + "-" + prediction[:20], year)
    # Ensure uniqueness
    base_id = entry_id
    counter = 1
    while entry_id in existing_ids:
        entry_id = f"{base_id}-{counter}"
        counter += 1

    # Guess category from prediction + outcome text
    combined = f"{prediction} {outcome} {hint}"
    category = guess_category(combined)

    # Build reality field — use outcome if useful, else generic
    if outcome and len(outcome) > 20 and outcome.lower() not in ("no", "yes", "none", "n/a", "—", "-"):
        reality = outcome
    else:
        reality = f"The predicted event did not occur as described by {year + 5 if year < 2020 else 2025}."

    entry = {
        "id":         entry_id,
        "year":       year,
        "prediction": prediction,
        "source":     claimant if claimant and claimant != prediction else "Unknown",
        "reality":    reality,
        "category":   category,
        "tags":       [],
        "_harvested": True,   # flag so you can filter/review these
    }
    return entry

# ── Curator.txt parser ─────────────────────────────────────────────────────────
def parse_curator(path):
    """
    Parse curator.txt.
    Format per line:
        Wikipedia_Page_Title | hint phrase
        Wikipedia_Page_Title          ← hint optional
        # comment lines ignored
    """
    targets = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|", 1)]
        title = parts[0]
        hint  = parts[1] if len(parts) > 1 else ""
        targets.append((title, hint))
    return targets

# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Harvest Wikipedia tables into doom.json")
    parser.add_argument("--write",  action="store_true", help="Write results to data/doom.json")
    parser.add_argument("--limit",  type=int, default=0, help="Max new entries to add (0 = unlimited)")
    parser.add_argument("--source", type=str, default="", help="Only process lines matching this string")
    args = parser.parse_args()

    # Load existing database
    with open(DOOM_JSON) as f:
        db = json.load(f)
    existing_ids = {e["id"] for e in db["entries"]}
    print(f"📚 Existing entries: {len(existing_ids)}")

    # Parse curator list
    if not CURATOR.exists():
        print(f"❌  {CURATOR} not found. Create it with Wikipedia article titles.")
        sys.exit(1)

    targets = parse_curator(CURATOR)
    if args.source:
        targets = [(t, h) for t, h in targets if args.source.lower() in t.lower()]
    print(f"🎯 Curator targets: {len(targets)}\n")

    new_entries = []

    for title, hint in targets:
        print(f"📡 Fetching: {title} ...", end=" ", flush=True)
        try:
            html  = wiki_fetch_html(title)
            tables = extract_tables(html)
            print(f"{len(tables)} table(s) found")
        except Exception as e:
            print(f"ERROR — {e}")
            time.sleep(1)
            continue

        for table in tables:
            for row in table:
                entry = row_to_entry(row, hint + " " + title, existing_ids | {e["id"] for e in new_entries})
                if entry:
                    new_entries.append(entry)
                    existing_ids.add(entry["id"])
                    if args.limit and len(new_entries) >= args.limit:
                        break
            if args.limit and len(new_entries) >= args.limit:
                break

        time.sleep(0.5)  # be polite to Wikipedia
        if args.limit and len(new_entries) >= args.limit:
            print(f"\n🏁 Limit of {args.limit} reached.")
            break

    print(f"\n✨ Found {len(new_entries)} new entries")

    if not new_entries:
        print("Nothing to add.")
        return

    # Preview
    print("\n── Preview (first 5) ──────────────────────────────")
    for e in new_entries[:5]:
        print(f"  [{e['year']}] {e['source'][:30]:30s}  →  {e['prediction'][:60]}...")
    if len(new_entries) > 5:
        print(f"  ... and {len(new_entries) - 5} more")

    if args.write:
        db["entries"].extend(new_entries)
        with open(DOOM_JSON, "w") as f:
            json.dump(db, f, indent=2, ensure_ascii=False)
        print(f"\n✅  Wrote {len(new_entries)} entries to {DOOM_JSON}")
        print(f"   Total entries now: {len(db['entries'])}")
        print("\n💡 Tip: review entries with _harvested:true before committing.")
        print("   grep for '\"_harvested\": true' to find them.")
    else:
        print("\n⚠️  Dry run — nothing written. Add --write to save.")

if __name__ == "__main__":
    main()
