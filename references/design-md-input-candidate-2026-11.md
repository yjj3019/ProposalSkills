# Candidate: DESIGN.md as a deck design input (2026-11-26)

Status: **adopted in the small form below (2026-11-27)**: `palette_from_design_md.py` reads the `colors` of a file the user supplies,
reports everything it did not use, and checks contrast. No catalog templates are bundled or fetched and nothing uses the network.
The site terms below were not re-read for this change. This is a development record, not legal advice.

## Why it came up

A pasted video summary on building decks with AI named `getdesign.md` as a source of a ready design system (colors, fonts,
layout) to restyle a draft deck. The other ideas in that summary are already covered (see `CHANGELOG.md`, Unreleased:
`plan_coverage.py`, `palette_from_image.py`). This one was left open.

## What was read (2026-11-26, public pages only)

- getdesign README (npm `getdesign@0.6.20`): a CLI, `npx getdesign list` and `npx getdesign add <slug>`, that writes a `DESIGN.md`
  to the project root; Node.js 18 or newer. Its only disclaimer: "These are **inspiration files**, not official design systems."
  It calls each template "an original, independently authored synthesis of a visual style."
- Google Labs `design.md` spec (`docs/spec.md`, status `alpha`): optional YAML front matter plus a Markdown body. Token groups:
  `colors`, `typography`, `rounded`, `spacing`, `motion`, `components`. A color may be any CSS color string; hex `#RRGGBB` is the
  recommended default. Tokens may reference each other as `{colors.primary-60}`. The spec mentions a linter but names no tool or command.

## Terms of the site (read 2026-11-26: the home page and `/terms`, "Last updated: November 24, 2026")

- Operator: "the VoltAgent team"; the legal entity is not named.
- Section 5: the DESIGN.md files in the public directory are "free to browse, download, and use in your projects", provided "as is", and
  "are not official design systems from the listed companies".
- Section 8: brand names are used nominatively and the site is not affiliated with the companies; the files "do not reproduce third-party
  logos, copyrighted imagery, or proprietary source code". Section 7 forbids passing a product off as a third-party brand or copying
  their logos and wordmarks into it, and forbids reselling the paid deliverables as a standalone product.
- The catalog lists entries named after real companies (for example Airbnb, Apple, Stripe, Notion, Vercel).

## What was not found

- Commercial or client-work use of the **free** files is not stated; the words are "use in your projects". Client-project rights are
  spelled out only for the paid Starter Kits.
- No license for the Google Labs spec, and no mention of Google Labs on the site's home or terms page. How the two relate is not shown.
- Pages not read: `/privacy`, `/affiliate/terms`, the catalog entries and any individual template.

## Fit with this repository

- A buyer-prescribed template or palette always wins (`deck-production.md` section 3). A design file would apply only when the buyer
  gives none, the same place `palette_from_image.py` output sits.
- `build_deck.py` takes `meta.palette` as 6-digit hex only. A DESIGN.md color can be any CSS color, so a reader would have to convert
  or reject the non-hex ones and say so, as `build_deck.py` already does for a bad palette.
- Only the color tokens map onto what the generator uses today. Typography, spacing and component tokens have no counterpart in
  `slides.json`, so reading them would be new design work.
- The spec is `alpha`; its keys may change.

## Decision needed before any code

1. Keep to a file the user supplies and never bundle or fetch catalog templates: the free files are "use in your projects" with no
   stated client-work right, and many are named after real brands, so a deck for a buyer must not look like another company's
   identity (terms section 7). If catalog files are ever bundled, get the operator's written answer on client work first.
2. If it goes ahead, keep it small: read the `colors` group of a user-supplied file, convert to the hex tokens, run the existing
   contrast check, and print what was ignored. Take no template catalog and no network access.
3. Add a test that a non-hex color and an unknown group are reported, not silently dropped.
