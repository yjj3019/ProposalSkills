# Candidate: DESIGN.md as a deck design input (2026-11-26)

Status: **not adopted; recorded for a later decision.** Nothing in this repository reads a `DESIGN.md` today. This is a
development record, not legal advice.

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

## What was not found

Not on either page: who runs getdesign.md, any template names, any license or trademark terms for the templates, any license
for the spec. A template's reuse terms are therefore **unknown**. I did not open the catalog pages or any individual template.

## Fit with this repository

- A buyer-prescribed template or palette always wins (`deck-production.md` section 3). A design file would apply only when the buyer
  gives none, the same place `palette_from_image.py` output sits.
- `build_deck.py` takes `meta.palette` as 6-digit hex only. A DESIGN.md color can be any CSS color, so a reader would have to convert
  or reject the non-hex ones and say so, as `build_deck.py` already does for a bad palette.
- Only the color tokens map onto what the generator uses today. Typography, spacing and component tokens have no counterpart in
  `slides.json`, so reading them would be new design work.
- The spec is `alpha`; its keys may change.

## Decision needed before any code

1. Confirm the reuse terms of the template source, or restrict input to a file the user supplies.
2. If it goes ahead, keep it small: read the `colors` group of a user-supplied file, convert to the hex tokens, run the existing
   contrast check, and print what was ignored. Take no template catalog and no network access.
3. Add a test that a non-hex color and an unknown group are reported, not silently dropped.
