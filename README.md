# The Doom That Wasn't 📰

> *A curated archive of catastrophes that failed to materialize.*

A static web app and growing database of real historical predictions of doom — sourced from experts, governments, and major media — that didn't come true. Upvote entries to tune your feed. Add new entries to expand the archive.

**[View Live Demo →](https://yourusername.github.io/doom-scroll)**

---

## Getting it running

### On GitHub Pages (recommended)

1. Fork this repo
2. Go to **Settings → Pages**
3. Set source to `main` branch, `/ (root)` folder
4. Your site will be live at `https://yourusername.github.io/doom-scroll`

That's it. No build step, no dependencies, no server required.

### Locally

```bash
# Clone it
git clone https://github.com/yourusername/doom-scroll.git
cd doom-scroll

# Serve it (any static server works)
python3 -m http.server 8000
# or: npx serve .
# or: open index.html directly in a browser
```

---

## Adding entries to the database

All entries live in `data/doom.json`. To add a new entry, open that file and add an object to the `entries` array:

```json
{
  "id": "unique-slug-no-spaces",
  "year": 1999,
  "prediction": "The original scary prediction, as it was framed at the time.",
  "source": "Who made it — publication, institution, named expert",
  "reality": "What actually happened instead.",
  "category": "Economic Collapse",
  "tags": ["optional", "search", "tags"]
}
```

### Categories

Pick one of these exactly:

| Category | Emoji |
|---|---|
| `Economic Collapse` | 📉 |
| `Tech Apocalypse` | 🤖 |
| `Environmental Doom` | 🌍 |
| `Political Catastrophe` | 🏛️ |
| `Health Crisis` | 🦠 |
| `Social Breakdown` | 👥 |
| `Food & Resource Scarcity` | 🌾 |
| `War & Conflict` | ⚔️ |

### Guidelines for entries

- **Must be real.** The prediction should be verifiable and sourced from a credible publication, institution, or named expert.
- **Must have clearly not come true** (or significantly not come true at the scale predicted).
- **No snark in the reality field.** State what happened matter-of-factly. The contrast speaks for itself.
- **Avoid highly contested events.** We're not making political arguments — only archiving predictions that are clearly, factually wrong in retrospect.
- **IDs must be unique.** Use kebab-case: `my-prediction-slug`.

### Submitting entries

1. Fork the repo
2. Edit `data/doom.json`
3. Open a Pull Request with the new entries

---

## How the algo works

The feed is locally personalized — no server, no tracking. When you click **reassuring** on a card, that category gets a +1 weight stored in your browser's `localStorage`. Future loads bias toward your preferred categories. Clear your browser storage to reset.

---

## Project structure

```
doom-scroll/
├── index.html       ← The entire app (vanilla JS, no framework)
├── data/
│   └── doom.json    ← The database — edit this to add entries
└── README.md
```

---

## Philosophy

*"Just go back to last year's doom and gloom reports and notice how none of it actually came to pass."*

This project is not a denial of real problems. Climate change is real. Antibiotic resistance is real. Many of the concerns behind these predictions were legitimate. The point is that human beings have a consistent tendency to forecast catastrophe at a scale and timeline that systematically exceeds what materializes — and there's genuine comfort in seeing that pattern documented.

---

## License

MIT. Do whatever you want with it. Add entries, fork it, make it your own.
