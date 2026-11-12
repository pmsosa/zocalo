# README structure to follow (from Vizsla's README)

Notes for writing Zócalo's README at the end. Structure only; Vizsla's content doesn't apply.

## Top (centred HTML, no markdown headings)
1. `<p align="center"><a href="REPO_URL"><img src="docs/brand/logo.png" alt="Zócalo" width="150"></a></p>`
2. `<h1 align="center">Zócalo</h1>`, the bare name.
3. Centred intro in one `<p align="center">`, lines joined by `<br>`:
   - a bold one-sentence tagline (what it is)
   - one longer sentence over two lines (what you do with it and what it produces)
   - a short closing fragment
4. A centred row of about 5 badgen.net badges (`https://badgen.net/badge/<Label>/<value>/<hex>`): stack, database,
   Docker, frontend, licence. Each has a descriptive alt.
5. Nav row 1: Project · User guide · Technical wiki · Quick Start · Architecture (` · ` separators).
6. Hero screenshot at `width="85%"`, linked to its guide page, then `<sub><i>Caption.</i></sub>`.
7. Nav row 2: Screenshots · Features · Requirements · Development · Configuration · Project Structure · License.
8. A `> [!TIP]` callout starting **New here?**, linking the user guide and the technical wiki.

## Sections
- `## Screenshots`: a one-line note that it's a throw-away demo with made-up data, then a `<table>` of 8 shots, 2 per
  row. Each cell is `<td width="50%" valign="top">` holding:
  - `<a href="GUIDE_PAGE"><img src="..." alt="LONG LITERAL ALT" width="100%"></a><br>`
  - `<b>Title</b><br>`
  - `<sub>1–2 sentences</sub>`
- `## Features`: about 14 bullets, `**Name** - description; clause; clause`.
- `## Architecture`: a Mermaid `flowchart LR` of about 9 nodes, with labelled edges `-->|label|` and stores drawn as
  `[( )]`. Then `### Components`: a table (Component | Description) with paths in backticks.
- `## Requirements`: 3 short bullets.
- `## Quick Start`: one bash block with numbered `# 1. ...` comment steps and `# ...or` alternatives, then two lines
  of prose (next steps with links; an HTTPS note).
- `## Development`: `### Backend` and `### Frontend`, bash blocks with aligned trailing comments.
- `## Configuration`: a few sentences, then a table (Variable | Description | Default), backticked.
- `## Project Structure`: a ```` ```text ```` tree with aligned `# comments`.
- `## License`: one line, `[Apache License 2.0](LICENSE).` (or whichever is chosen).

## Style
Plain, practical, second person, short sentences, no marketing. Bold only for feature names, UI labels and the TIP
opener. Inline code for paths, variables and files.

## Differences from the lab default (glyph-sast style, in CLAUDE.md)
The lab default puts a 21:9 `docs/banner.jpg` on the first line, puts an `<h3>` heading in each screenshot cell, and
keeps images in `docs/images/<app>-<topic>.png`. Vizsla uses a centred logo, a `<b>` title per cell, and `wiki/images/`.
The user asked for Vizsla's structure. Decide on banner vs logo at README time; keeping both (banner on top, logo
in the centred block) is an option to raise.
