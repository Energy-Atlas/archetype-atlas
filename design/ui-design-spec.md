# Energy Archetype Atlas website — UI Design Specification

This specification restyles the Energy Archetype Atlas website into the visual family of the EnergyAtlas Wiki. It began as the EnergyAtlas Wiki UI design specification; section 0 records the decisions taken for the atlas. **Where section 0 and a later section disagree, section 0 wins.**

This folder is not part of the website. The site's Markdown is generated (`scripts/active_site.py`, `scripts/definition_site.py`, `scripts/object_site.py`) into the ignored `build/site-docs/`; styling lives in `website/assets/`, templates in `website/overrides/`.

---

## 0. Atlas Implementation Decisions

Decided on 2026-10-07 by the implementing agent, working autonomously at the owner's instruction ("autonomous task, no human supervision"). Each decision takes the EnergyAtlas family default that the sister BEMGen documentation site's owner settled on the same day, unless the atlas's own structure required otherwise; those departures are marked **Atlas**. The owner may revise any of them; revisions are recorded here. These are implementation rules, not one-off clarifications.

### 0.1 Brand

- The site stays **Energy Archetype Atlas**. This is a visual-family alignment with EnergyAtlas, not a rename.
- Keep the site title and identity, and Material's default logo and favicon (the atlas has no logo of its own). Do not add "EnergyAtlas" branding to the header, title, footer, or pages.
- The family resemblance comes from typography, palette, and UI structure. The atlas's former teal and deep-orange palette is retired.

### 0.2 Sources of truth

- **Reference UI:** the ArtCraft website screenshot of the EnergyAtlas family specification. The image is not available to this repository and is not kept in it; section 0.11 describes it, as recorded for the family.
- **Palette:** the live EnergyAtlas Wiki implementation, `assets/css/main.css` of <https://chengxuan-li.github.io/EnergyAtlasWiki/>. If it diverges from the hex values in this document, the wiki's CSS is authoritative, except where section 0.6 adjusts a value for contrast. The values here were checked against the wiki on 2026-10-07, including its Plotly tokens (section 0.15).

### 0.3 Theme behaviour

- The default theme follows the system preference (`prefers-color-scheme`), and a light/dark toggle is added to the header. Before this change the site was light only.
- Never force dark mode. A visitor whose system prefers light gets light first.
- Dark mode receives the strongest version of the reference visual language; light mode keeps the same grid, typography, and framing.
- **Atlas:** record pages (section 0.14) have no Material runtime and no toggle. A small script in their `<head>` applies the scheme the visitor chose on a full page (Material's stored palette choice), else the system preference; without JavaScript they render light.

### 0.4 Fonts

- Families: **Geist** (primary sans), **Geist Mono** (technical and monospace UI), **Cormorant Garamond** (sparse editorial serif accent, italic 500).
- Self-hosted. The browser contacts no font host when the site is viewed, and builds need no network.
- The Latin and Latin Extended WOFF2 subsets (variable Geist and Geist Mono, Cormorant Garamond italic 500) are byte-identical copies of the family's vendored Google Fonts files, kept with their SIL Open Font License 1.1 texts in `website/assets/fonts/` and declared in `website/assets/fonts.css`. The generator copies `website/assets/` to the site's `assets/`. `theme.font` stays `false`.
- `website/overrides/main.html` preloads `geist-latin.woff2` and `geist-mono-latin.woff2`.

### 0.5 Colour roles

| Role | Dark | Light | Use |
| --- | --- | --- | --- |
| Info / interactive accent | `#4da3ff` | `#125dae` | links, navigation, information, active and selected states, focus |
| Success | `#28a745` | `#188038` | success states |
| Warning | `#ffc107` | `#9a6700` | warnings and provisional status labels |
| Error | `#f44336` | `#c5221f` | errors, destructive actions, failures |
| Primary (brand) | `#003978` | `#003978` | deep branded **fill or background** only |

- Red is restricted to error, destructive, and failure states. Do not use red (`#f1392a`, `#c92d22`) as a decorative secondary brand accent anywhere in the site.
- Amber/yellow means warning, green means success, blue means links, navigation, information, and active/selected states.
- `#003978` is never text or a meaningful border on a dark background (1.86:1 on black). Text on a `#003978` fill is white or `#e5e5e5`.
- Admonition mapping: `note`, `info`, `abstract`, `tip`, `question` use the info blue; `success` green; `warning` amber; `danger`, `failure`, `bug`, `error` red; `example`, `quote` muted.
- **Atlas:** an unknown or not-reported value is a data state, not an error: it stays in the ordinary text colour. Nothing in the atlas styles "Unknown" red.

### 0.6 Contrast

Targets (WCAG 2.2 AA):

- text below 24px (or 18.66px bold), including all 10–12px mono labels: at least 4.5:1 against every surface it sits on;
- large text: at least 3:1;
- borders and edges that convey state or mark an interactive control (inputs, selects, buttons, focus, the active item): at least 3:1;
- decorative grid rules that convey no state may stay lighter.

Adjusted and added tokens:

| Token | Theme | Spec value | Used value | Contrast of used value |
| --- | --- | --- | --- | --- |
| `--ea-text-muted` | dark | `#808080` (4.41:1 on `#1a1a1a`) | `#999999` | 7.37 on `#000000`, 6.11 on `#1a1a1a`, 5.04 on `#2a2a2a` |
| `--ea-text-muted` | light | `#6f7a89` (4.36:1 on white) | `#5f6b7a` (the wiki's own Plotly subtitle colour) | 5.43 on `#ffffff`, 5.19 on `#f8fafc`, 5.05 on `#f4f7fb`, 4.61 on `#e7edf5` |
| `--ea-border-subtle` | dark | `#404040` | `#404040` | decorative grid rules only |
| `--ea-border-subtle` | light | `#cfd8e5` | `#cfd8e5` | decorative grid rules only |
| `--ea-border-interactive` | dark | — | `#6b6b6b` | 3.94 on `#000000`, 3.27 on `#1a1a1a` |
| `--ea-border-interactive` | light | — | `#768599` | 3.76 on `#ffffff`, 3.59 on `#f8fafc`, 3.50 on `#f4f7fb`, 3.19 on `#e7edf5` |

- `--ea-border` in later sections means `--ea-border-subtle` for grid framing, strips, cells, tables, and code blocks, and `--ea-border-interactive` for inputs, selects, buttons, and other controls.
- Focus and active states use the accent colour, which passes everywhere (dark 4.33 or more, light 5.57 or more).
- Do not set muted text on dark `#3a3a3a` (3.99:1), or small state-coloured text on light `#e7edf5` (success 4.26, warning 4.13).

### 0.7 Landing page

A real but restrained hero, followed immediately by the shared-border grid. Not a marketing page.

- The landing page is generated by `scripts/active_site.py`; change it there, never in `build/site-docs/`.
- Headline, on two lines, from the site's existing tagline:

  ```text
  Deterministic energy definitions
  for zoning experiments.
  ```

  `Deterministic energy definitions` in Geist; `for zoning experiments.` in Cormorant Garamond italic.
- Supporting copy is the existing one-sentence description, followed by the release counts as one mono metadata line and one primary button, *Open the catalogue*.
- Below the hero, numbered strips with shared-border grids: the two building families of the catalogue, then the four guides, then sources and notices. The existing text and links stay; only their arrangement changes.
- The landing page hides both sidebars but keeps their widths as empty margins, without their vertical rules, so its text starts where the text of every other page starts. Strips and the top and bottom rules of grids still run from frame to frame.
- The hero headline is sized to the hero's width (container query units), so `Deterministic energy definitions` stays on one line on desktop.
- No oversized CTAs, imagery, or animation.

### 0.8 Numbered section strips

Section strips (`01 / CATALOGUE`, section 7) appear only on the landing page and other deliberately designed overview pages. Do not number `##` headings automatically on ordinary pages. The catalogue's choice pages keep their headings; their choices become shared-border cells (section 0.13).

### 0.9 Content width

- The page frame is 76rem wide, the family's width (the atlas used 88rem).
- The prose measure (section 11) caps long-form paragraphs, lists, and admonitions only. Tables, code, JSON, finders, charts, and grids use the full column.
- Wide tables sit in a bounded horizontal-scrolling container; the viewport itself must never overflow horizontally, at 390px wide included.

### 0.10 Breadcrumbs

- Breadcrumbs are on (`navigation.path`).
- Restrained technical style: small Geist Mono, muted, `/` separators in the same colour, no bar, background, or border.

### 0.11 The reference screenshot, described

What the family takes from the ArtCraft reference:

- **Surface:** near-black page background; content in off-white, secondary text in mid-grey.
- **Page frame:** the content column is bounded by two full-height vertical rules, with empty margins outside them. Horizontal rules run between sections and meet the frame, like a drawing sheet.
- **Header:** low, one line, thin bottom rule. Logo at the left; nav labels in small uppercase, widely tracked monospace. The active item is a small inverted block (light fill, dark text) inside a thin blue rectangular outline.
- **Section strip:** about 48px high between two horizontal rules: `02 / OWNERSHIP` at the left and a right-aligned annotation at the right, both small, uppercase, tracked mono, muted.
- **Hero cell:** generous padding and empty space; a large, very bold sans headline with tight leading over two lines, one phrase set in a serif italic inline; one short supporting paragraph in grey, roughly 60 characters wide.
- **Feature row:** equal cells sharing their borders with each other and with the hero above. Each cell: a one-letter mono index (`A`, `B`, `C`) at the top left in muted grey, a bold title, two lines of grey description, and optionally a small square outlined button with a mono uppercase label.
- **Not adopted:** the right-hand scroll ruler with tick numbers and percentage, the oversized outline section names in the right margin, and `+` registration marks. They are page-specific decoration and conflict with section 19.

### 0.12 Stable page changes

- **Atlas:** `navigation.instant` is **off**, unlike the family default. About 59,000 record pages use a compact shell without Material's page components or runtime, which instant navigation cannot swap in, and the catalogue finders, JSON panels, and schedule plots initialise their scripts on page load.
- `html` reserves the scrollbar's width (`scrollbar-gutter: stable`), so short and long pages have the same content width.
- Fonts are preloaded (section 0.4); a hosted site caches them, so page loads after the first draw without a font swap.

### 0.13 Grid cells

- A cell whose title is a link is clickable as a whole and goes to the title's address; hovering it shifts the surface and turns the title blue. Other links in the cell (its button, a link in its description) keep their own targets.
- A cell's text is padded by the same gutter as the prose, so cell text, strip labels, and paragraphs share one left edge.
- Every cell is closed on all four sides. Where an empty sidebar margin (section 0.7) moves a grid in from the frame, the grid draws its own outer left and right rules at the margin.
- **Atlas:** the catalogue's generated choice links (`.definition-gate`, `.definition-kind`) are styled as the same shared-border cells, through CSS only, with letter indices.

### 0.14 Record pages (compact shell)

**Atlas.** Program, construction, HVAC, schedule, material, component, and evidence pages are rendered by `website/hooks/html_delivery.py` as a compact shell: a one-line header and the article, without Material's navigation markup. They follow the same system:

- the header is the family header in miniature: the site name at the left, mono uppercase links at the right, on the base surface with a thin bottom rule; the markup's ` · ` text separators are hidden and spacing separates the links;
- the article's text starts where the header's links start; the column's two frame rules show where the viewport leaves margins;
- the document column is framed by the two vertical rules, at the record pages' existing width;
- tables are technical data sheets (section 12) that scroll inside their own container; JSON panels, reference lists, and evidence details are square bordered panels; *Copy JSON* and *Load interactive plots* are inverted primary buttons, other buttons outlined (section 10); the copy dialog is a square panel with an interactive border;
- every `<details>` of the site is such a panel, without Material's admonition chrome (the site has no collapsible admonitions);
- the theme follows section 0.3. Evidence pages, which load only the site's own CSS, get the same fonts, tokens, and theme script.

### 0.15 Interactive controls and charts

**Atlas.**

- Filters, selects, inputs, and buttons are square, bordered with `--ea-border-interactive`, with mono uppercase labels; focus is a 2px accent outline. Existing minimum control heights stay.
- Schedule charts (Plotly) take the wiki's Plotly tokens at render time: transparent paper and plot, text `#e5e5e5` / `#18202c`, grid `rgba(255,255,255,0.12)` / `rgba(24,32,44,0.14)`, zero lines `rgba(255,255,255,0.2)` / `rgba(24,32,44,0.24)`, Geist text. The first line trace is the accent; further profiles follow Plotly's default sequence without its red (section 0.5). The heatmap keeps its perceptually uniform Viridis scale, which reads on both themes.

---

## 1. Design Intent

Restyle the MkDocs website using the reference UI (section 0.2) as the primary visual reference for:

- grid structure
- border framing
- typography hierarchy
- card construction
- spacing
- navigation character
- technical/editorial tone

Use the existing **EnergyAtlas Wiki** as the source of truth for brand colors and documentation behavior.

The result should feel:

- technical
- editorial
- architectural
- precise
- minimal
- engineering-oriented
- documentation-first

The design should avoid generic SaaS or stock Material Design patterns.

---

## 2. Visual Priorities

Use the following order of precedence:

1. **Reference UI**
   - framing
   - borders
   - page grid
   - content cells
   - typography hierarchy
   - section indexing
   - navigation treatment
   - spacing

2. **Existing EnergyAtlas Wiki**
   - brand colors
   - light/dark theme palette
   - information architecture
   - documentation structure
   - semantic state colors

3. **Typography**
   - Geist for primary UI and documentation text
   - Geist Mono for technical labels and metadata
   - Cormorant for occasional editorial emphasis

The goal is not to reproduce another site literally. The goal is to transfer its disciplined, grid-based design language into EnergyAtlas.

---

# 3. Typography

## 3.1 Primary Sans Serif

Use **Geist** as the primary typeface across the interface.

Use Geist for:

- page headings
- body text
- navigation
- sidebar
- cards
- buttons
- tables
- search
- captions
- labels where monospacing is not required

Recommended fallback:

```css
font-family: "Geist", "Inter", "Helvetica Neue", Arial, sans-serif;
```

### Heading behavior

Headings should rely on weight, spacing, and scale rather than decorative styling.

Recommended characteristics:

```css
font-weight: 650 750;
line-height: 0.95 1.15;
letter-spacing: -0.02em;
```

Suggested display sizes:

```css
display-xl: 64px;
display-lg: 56px;
display-md: 48px;

h1: 40px;
h2: 30px;
h3: 22px;
h4: 18px;
```

Documentation headings should scale down appropriately on smaller screens.

### Body text

Recommended baseline:

```css
font-size: 16px;
line-height: 1.6;
font-weight: 400;
```

For introductory or prominent body copy:

```css
font-size: 18px;
line-height: 1.6;
```

Use secondary text colors rather than pure white for long-form content.

---

## 3.2 Technical Labels

Use **Geist Mono** where available.

Recommended fallback:

```css
font-family: "Geist Mono", "IBM Plex Mono", Consolas, monospace;
```

Use for:

- section indices
- page metadata
- card labels
- breadcrumbs
- small navigation labels
- technical annotations
- code-adjacent UI
- compact buttons

Recommended treatment:

```css
font-size: 10px 12px;
font-weight: 550 650;
text-transform: uppercase;
letter-spacing: 0.12em 0.16em;
```

Examples:

```text
01 / QUICK START
02 / WORKFLOWS
A
B
C
SYSTEM OVERVIEW
MODEL PIPELINE
```

---

## 3.3 Editorial Serif

Use **Cormorant** or **Cormorant Garamond** for occasional editorial emphasis.

Prefer the Google Fonts version when available.

Use it only for selective phrases in large display headings.

Example (the atlas landing headline, section 0.7):

```text
Deterministic energy definitions
for zoning experiments.
```

The phrase *for zoning experiments.* uses Cormorant italic while the rest remains Geist.

Do not use Cormorant for:

- body copy
- navigation
- tables
- standard documentation headings
- buttons
- sidebars

It should function as a restrained editorial accent.

---

# 4. Color System

Use the existing EnergyAtlas palette as the source of truth: the wiki's `assets/css/main.css` (section 0.2), with the contrast adjustments of section 0.6. The blocks below already include those adjustments.

## 4.1 Dark Theme

```css
--ea-primary:            #003978;  /* deep branded fill only */
--ea-accent:             #4da3ff;

--ea-text-primary:       #e5e5e5;
--ea-text-secondary:     #b0b0b0;
--ea-text-muted:         #999999;  /* wiki: #808080; adjusted, section 0.6 */

--ea-bg-base:            #000000;
--ea-bg-surface-1:       #1a1a1a;
--ea-bg-surface-2:       #2a2a2a;
--ea-bg-surface-3:       #3a3a3a;

--ea-border-subtle:      #404040;  /* decorative grid rules */
--ea-border-interactive: #6b6b6b;  /* controls; added, section 0.6 */

--ea-success:            #28a745;
--ea-warning:            #ffc107;
--ea-error:              #f44336;  /* wiki --secondary-color #f1392a is not used as an accent */
```

### Dark theme usage

- Base page background: `#000000`
- Primary surfaces: `#1a1a1a`
- Secondary surfaces: `#2a2a2a`
- Higher-emphasis surfaces: `#3a3a3a`
- Main text: `#e5e5e5`
- Secondary text: `#b0b0b0`
- Metadata: `#999999`
- Grid borders: `#404040`; control borders: `#6b6b6b`
- Main interaction accent: `#4da3ff`
- Deep branded fill: `#003978` (never text on dark)
- Red only for error, destructive, and failure states (section 0.5)

The interface should remain predominantly monochromatic. Accent colors should be used sparingly.

---

## 4.2 Light Theme

```css
--ea-primary:            #003978;  /* deep branded fill only */
--ea-accent:             #125dae;

--ea-text-primary:       #18202c;
--ea-text-secondary:     #3f4b5b;
--ea-text-muted:         #5f6b7a;  /* wiki: #6f7a89; adjusted, section 0.6 */

--ea-bg-base:            #ffffff;
--ea-bg-surface-1:       #f8fafc;  /* wiki --bg-gradient-dark ("subtle") */
--ea-bg-surface-2:       #f4f7fb;  /* wiki --bg-light ("surface") */
--ea-bg-surface-3:       #e7edf5;  /* wiki --bg-dark-surface ("emphasis") */

--ea-border-subtle:      #cfd8e5;  /* decorative grid rules */
--ea-border-interactive: #768599;  /* controls; added, section 0.6 */

--ea-success:            #188038;
--ea-warning:            #9a6700;
--ea-error:              #c5221f;  /* wiki --secondary-color #c92d22 is not used as an accent */
```

The light surfaces use the same token names as the dark ones, in the same order of emphasis, so components never branch on the theme.

The light theme should preserve the same grid structure, typography hierarchy, and flat framing as the dark theme.

The dark theme should be the stronger expression of the design language.

---

# 5. Core Layout System

The page should be organized around a **continuous rectilinear grid**.

Primary characteristics:

- thin horizontal rules
- thin vertical rules
- aligned content cells
- shared borders
- strong column discipline
- deliberate whitespace
- flat surfaces
- square corners

Recommended base treatment:

```css
border: 1px solid var(--ea-border);
border-radius: 0;
box-shadow: none;
```

Avoid:

- rounded cards
- pills
- floating cards
- decorative gradients
- glassmorphism
- drop shadows
- large icon tiles
- disconnected feature boxes
- excessive use of colored fills

The interface should read as one structured document rather than a collection of independent components.

---

# 6. Grid Framing

Major sections should be aligned to the same page-wide grid.

Prefer shared borders between adjacent cells.

Example:

```text
┌──────────────────────────────────────────────────────┐
│ 02 / WORKFLOWS                      MODEL PIPELINE   │
├──────────────────┬──────────────────┬────────────────┤
│ A                │ B                │ C              │
│                  │                  │                │
│ Urban Data       │ Simulation       │ Results        │
│ ...              │ ...              │ ...            │
│                  │                  │                │
└──────────────────┴──────────────────┴────────────────┘
```

This is preferred over three visually isolated cards.

The grid should create continuity across the page.

---

# 7. Section Headers

Use thin section-index strips for major content areas, on the pages listed in section 0.8 only.

Example:

```text
02 / WORKFLOWS                              MODEL PIPELINE
```

Recommended characteristics:

```css
height: 40px 48px;
border-top: 1px solid var(--ea-border);
border-bottom: 1px solid var(--ea-border);
```

Typography:

```css
font-family: "Geist Mono", monospace;
font-size: 10px 12px;
font-weight: 600;
letter-spacing: 0.14em;
text-transform: uppercase;
```

Use muted text colors.

These strips should feel like:

- technical drawing annotations
- engineering document indexing
- sheet metadata
- system labels

They should not resemble marketing section headers.

---

# 8. Feature Cards

Feature cards should behave as **grid cells**.

Recommended structure:

```text
A

Urban Data Integration
Import and prepare geospatial building datasets.

[ VIEW WORKFLOW ]
```

Recommended styling:

```css
padding: 28px 36px;
background: transparent;
border-radius: 0;
box-shadow: none;
```

Title:

```css
font-family: "Geist", sans-serif;
font-weight: 650 700;
font-size: 24px 28px;
```

Description:

```css
font-family: "Geist", sans-serif;
font-size: 16px;
line-height: 1.55;
color: var(--ea-text-secondary);
```

Card identifier:

```css
font-family: "Geist Mono", monospace;
font-size: 10px 11px;
letter-spacing: 0.14em;
color: var(--ea-text-muted);
```

Hover state:

- slightly brighter border
- slight surface shift
- optional blue title or micro-accent
- no translate animation
- no shadow elevation

---

# 9. Navigation

## 9.1 Top Navigation

The top navigation should be compact and linear.

Recommended characteristics:

- dark background
- thin bottom border
- low vertical height
- small technical typography
- strong horizontal alignment

Navigation labels:

```css
font-family: "Geist Mono", monospace;
font-size: 11px 13px;
font-weight: 600;
letter-spacing: 0.08em 0.14em;
text-transform: uppercase;
```

Active states may use:

- brighter text
- thin bottom rule
- subtle blue outline
- small blue edge
- restrained rectangular selection

Avoid rounded tabs.

---

## 9.2 Sidebar

The sidebar should remain functional and documentation-first.

Use:

- near-black or transparent background
- thin vertical divider
- muted inactive labels
- off-white active label
- blue accent for active state
- restrained indentation
- flat nested navigation

Avoid filled Material-style active blocks.

Hierarchy should come from:

- spacing
- indentation
- typography
- muted color changes
- thin rules

---

# 10. Buttons

Buttons should feel like compact technical controls.

Recommended base:

```css
background: transparent;
border: 1px solid var(--ea-border-interactive);
border-radius: 0;
box-shadow: none;
```

Typography:

```css
font-family: "Geist Mono", monospace;
font-size: 10px 12px;
font-weight: 600;
letter-spacing: 0.08em 0.12em;
text-transform: uppercase;
```

Hover states may:

- brighten the border
- use `#4da3ff`
- invert foreground/background for primary actions

Avoid oversized CTA styling.

---

# 11. Documentation Content

Long-form documentation should remain highly readable.

Recommended article width:

```css
max-width: 760px 900px;
```

This width is for long-form prose only. Reference pages, large diagrams, data matrices, and wide tables are exempt, and wide tables scroll inside a bounded container (section 0.9).

Use generous vertical rhythm.

Suggested section spacing:

```css
h1 margin-top: 0;
h2 margin-top: 64px;
h3 margin-top: 40px;
paragraph margin-bottom: 1.25em;
```

Do not force every content block into a bordered container.

The page shell should provide structure; prose should remain visually open.

---

# 12. Tables

Tables should follow the same technical grid language.

Recommended characteristics:

- square outer edges
- thin row and column rules
- flat background
- no rounded outer wrapper
- subtle hover state
- restrained header styling
- blue only for interaction or selected states

Recommended header treatment:

```css
font-family: "Geist Mono", monospace;
font-size: 11px;
font-weight: 600;
letter-spacing: 0.08em;
text-transform: uppercase;
```

Tables should feel closer to technical data sheets than application widgets.

---

# 13. Code

Use **Geist Mono** where possible.

Code block base:

```css
background: var(--ea-bg-surface-1);
border: 1px solid var(--ea-border);
border-radius: 0;
box-shadow: none;
```

Inline code should be understated.

Avoid pill-shaped inline code.

Recommended inline treatment:

```css
background: var(--ea-bg-surface-1);
padding: 0.1em 0.3em;
border-radius: 0;
```

---

# 14. Admonitions and Callouts

Admonitions should feel like technical panels rather than colorful Material cards.

Example:

```text
NOTE
────────────────────────────────────
Content...
```

Recommended styling:

- square edges
- thin outer rule or leading rule
- small mono heading
- low-contrast surface
- restrained semantic accents

Semantic colors may appear in:

- a thin edge
- small heading
- compact icon
- label text

Avoid large saturated background fills.

---

# 15. Search

Search should match the same technical language.

Use:

- square input geometry
- thin borders in `--ea-border-interactive`
- near-black or white surface depending on theme
- Geist text
- Geist Mono for metadata or keyboard hints
- no floating shadow-heavy search modal

Focus state:

```css
border-color: var(--ea-accent);
outline: none;
```

---

# 16. Spacing System

Recommended spacing scale:

```css
--space-xs:   4px;
--space-sm:   8px;
--space-md:  16px;
--space-lg:  24px;
--space-xl:  32px;
--space-2xl: 48px;
--space-3xl: 64px;
```

Typical usage:

- section strips: compact
- cards: `28px 36px`
- article sections: `40px 64px`
- hero regions: `48px 64px`
- navigation: compact
- sidebars: dense but not cramped

---

# 17. Hero / Landing Page Areas

Landing-page hero sections may use larger scale typography and more negative space.

Recommended characteristics:

```css
padding-top: 64px;
padding-bottom: 72px;
```

Display heading:

```css
font-size: 48px 64px;
line-height: 0.98 1.05;
font-weight: 700;
letter-spacing: -0.03em;
```

Use Cormorant italic selectively within the heading if editorial emphasis is desirable.

The atlas headline (section 0.7):

```text
Deterministic energy definitions
for zoning experiments.
```

Treatment:

- `Deterministic energy definitions` — Geist
- `for zoning experiments.` — Cormorant Garamond italic

Use sparingly. The hero stays restrained and is followed immediately by the shared-border grid.

---

# 18. Borders

Borders are one of the main visual devices.

Use them deliberately.

Recommended default:

```css
border-color: var(--ea-border);
border-width: 1px;
```

Where lower contrast is appropriate:

```css
border-color: color-mix(
  in srgb,
  var(--ea-border) 65%,
  transparent
);
```

Borders should define structure, not decorate every element independently.

Prefer continuous alignment across sections.

---

# 19. Motion

Animation should be minimal.

Allowed:

- subtle color transitions
- border changes
- opacity changes
- small underline or line expansion

Recommended timing:

```css
transition: 120ms 180ms ease;
```

Avoid:

- card lifting
- parallax
- bounce
- large scaling
- exaggerated hover motion
- continuous decorative animation

---

# 20. Responsive Behavior

## Desktop

- 2–3 column content grids
- persistent sidebar where useful
- strong horizontal alignment
- visible shared borders
- wider technical section strips

## Tablet

- reduce 3-column grids to 2 columns
- preserve border continuity
- slightly reduce padding
- maintain typography hierarchy

## Mobile

- stack cells vertically
- preserve square corners
- retain horizontal rules
- collapse navigation conventionally
- keep technical labels compact
- avoid introducing separate mobile card styling

The visual language should remain consistent at all breakpoints.

---

# 21. MkDocs-Specific Guidance

Override the default appearance enough that the result no longer reads as stock MkDocs or stock Material Design.

Priority components:

- header
- sidebar
- page TOC
- search
- tables
- code blocks
- admonitions
- tabs
- navigation states
- content cards
- pagination
- breadcrumbs

Retain MkDocs usability while replacing the default component styling with the EnergyAtlas grid system.

---

# 22. Theme Implementation Guidance

Recommended CSS token structure:

```css
:root {
  --font-sans: "Geist", "Inter", "Helvetica Neue", Arial, sans-serif;
  --font-mono: "Geist Mono", "IBM Plex Mono", Consolas, monospace;
  --font-serif: "Cormorant Garamond", "Cormorant", Georgia, serif;

  --ea-primary: #003978;
  --ea-accent: #4da3ff;

  --ea-text-primary: #e5e5e5;
  --ea-text-secondary: #b0b0b0;
  --ea-text-muted: #999999;

  --ea-bg-base: #000000;
  --ea-bg-surface-1: #1a1a1a;
  --ea-bg-surface-2: #2a2a2a;
  --ea-bg-surface-3: #3a3a3a;

  --ea-border-subtle: #404040;
  --ea-border-interactive: #6b6b6b;

  --ea-success: #28a745;
  --ea-warning: #ffc107;
  --ea-error: #f44336;

  --space-xs: 4px;
  --space-sm: 8px;
  --space-md: 16px;
  --space-lg: 24px;
  --space-xl: 32px;
  --space-2xl: 48px;
  --space-3xl: 64px;

  --radius: 0;
  --shadow: none;
}
```

For light mode, swap the color tokens (section 4.2) while preserving structure. Which set applies follows the active Material scheme (`slate` for dark, `default` for light), chosen by the system preference and the toggle (section 0.3); dark is not the default.

---

# 23. Component Principles

Every component should satisfy the following:

1. **Flat**
   - no visual elevation unless absolutely necessary

2. **Aligned**
   - follows shared page columns and rules

3. **Square**
   - no soft card geometry

4. **Restrained**
   - limited color and motion

5. **Typographic**
   - hierarchy comes mainly from type

6. **Technical**
   - labels and metadata should feel precise

7. **Integrated**
   - components should feel like part of one system rather than isolated widgets

---

# 24. Final Visual Character

The completed site should feel like a combination of:

- technical documentation
- architectural drawing set
- engineering interface
- research publication
- high-end developer documentation

It should remain unmistakably EnergyAtlas through its palette and information architecture, while adopting a more disciplined, grid-based, editorial visual system.

The final design should prioritize:

- structure over decoration
- typography over iconography
- borders over shadows
- alignment over ornament
- information hierarchy over visual novelty
