# EnergyAtlas Wiki — UI Design Specification

## 1. Design Intent

Restyle the MkDocs website using the provided reference UI as the primary visual reference for:

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

Example:

```text
Build energy models
at urban scale.
```

The phrase *urban scale* may use Cormorant italic while the rest remains Geist.

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

Use the existing EnergyAtlas palette as the source of truth.

## 4.1 Dark Theme

```css
--ea-primary:        #003978;
--ea-secondary:      #f1392a;
--ea-accent:         #4da3ff;

--ea-text-primary:   #e5e5e5;
--ea-text-secondary: #b0b0b0;
--ea-text-muted:     #808080;

--ea-bg-base:        #000000;
--ea-bg-surface-1:   #1a1a1a;
--ea-bg-surface-2:   #2a2a2a;
--ea-bg-surface-3:   #3a3a3a;

--ea-border:         #404040;
```

### Dark theme usage

- Base page background: `#000000`
- Primary surfaces: `#1a1a1a`
- Secondary surfaces: `#2a2a2a`
- Higher-emphasis surfaces: `#3a3a3a`
- Main text: `#e5e5e5`
- Secondary text: `#b0b0b0`
- Metadata: `#808080`
- Borders: `#404040`
- Main interaction accent: `#4da3ff`
- Stronger branded state: `#003978`
- Secondary accent: `#f1392a`

The interface should remain predominantly monochromatic. Accent colors should be used sparingly.

---

## 4.2 Light Theme

```css
--ea-primary:        #003978;
--ea-secondary:      #c92d22;
--ea-accent:         #125dae;

--ea-text-primary:   #18202c;
--ea-text-secondary: #3f4b5b;
--ea-text-muted:     #6f7a89;

--ea-bg-base:        #ffffff;
--ea-bg-subtle:      #f8fafc;
--ea-bg-surface:     #f4f7fb;
--ea-bg-emphasis:    #e7edf5;

--ea-border:         #cfd8e5;
```

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

Use thin section-index strips for major content areas.

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
border: 1px solid var(--ea-border);
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
- thin borders
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

Example:

```text
Urban energy modeling
for complex cities.
```

Possible treatment:

- `Urban energy modeling` — Geist
- `for complex cities.` — Cormorant italic

Use sparingly.

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
  --font-mono: "Geist Mono", Consolas, monospace;
  --font-serif: "Cormorant Garamond", "Cormorant", Georgia, serif;

  --ea-primary: #003978;
  --ea-secondary: #f1392a;
  --ea-accent: #4da3ff;

  --ea-text-primary: #e5e5e5;
  --ea-text-secondary: #b0b0b0;
  --ea-text-muted: #808080;

  --ea-bg-base: #000000;
  --ea-bg-surface-1: #1a1a1a;
  --ea-bg-surface-2: #2a2a2a;
  --ea-bg-surface-3: #3a3a3a;

  --ea-border: #404040;

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

For light mode, swap the color tokens while preserving structure.

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
