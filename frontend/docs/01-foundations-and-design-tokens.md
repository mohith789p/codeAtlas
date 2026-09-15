# CodeAtlas Design System
## 01 — Foundations & Design Tokens

**Status:** Frozen — this document is the single source of truth for all CodeAtlas UI. Page-specific specifications (02–07) must reference these tokens and may not define their own colors, typography, spacing, or radius values.

**Mental model:** "A modern code editor with an intelligent research layer" — not "ChatGPT with a GitHub connector."

---

## 1. Raw Color Tokens

These are the base hue/lightness values the semantic system is built from. Raw tokens are not used directly in components — always go through a semantic token (Section 2).

| Raw token | Value |
|---|---|
| `raw-black-950` | `#0B0A0F` |
| `raw-black-900` | `#111019` |
| `raw-black-850` | `#15131D` |
| `raw-black-800` | `#1B1825` |
| `raw-code-bg` | `#0D1117` |
| `raw-white-warm` | `#F4F0E8` |
| `raw-gray-300` | `#A9A4B2` |
| `raw-gray-400` | `#9A95A3` |
| `raw-blue-gray` | `#94A3B8` |
| `raw-violet-500` | `#8B5CF6` |
| `raw-violet-600` | `#7C3AED` |
| `raw-violet-700` | `#6D28D9` |
| `raw-violet-400` | `#A78BFA` |
| `raw-pink-500` | `#EC4899` |
| `raw-indigo-500` | `#6366F1` |
| `raw-green-400` | `#34D399` |
| `raw-amber-400` | `#FBBF24` |
| `raw-red-400` | `#F87171` |
| `raw-border` | `#272332` |

---

## 2. Semantic Tokens

### 2.1 Surfaces (Elevation)

| Token | Value | Purpose |
|---|---|---|
| `bg-primary` | `#0B0A0F` | Main application background — Level 0 |
| `bg-sidebar` | `#111019` | Sidebar — Level 1 |
| `bg-surface` | `#15131D` | Cards, grouped surfaces — Level 2 |
| `bg-elevated` | `#1B1825` | Modals, dropdowns, popovers — Level 3 |
| `bg-code` | `#0D1117` | Code viewer — separate semantic surface, not part of the elevation ladder |

### 2.2 Text

| Token | Value | Purpose |
|---|---|---|
| `text-primary` | `#F4F0E8` | Main/body text, headings |
| `text-secondary` | `#A9A4B2` | Supporting text |
| `text-muted` | `#9A95A3` | Low-priority metadata (revised from `#77717F` — see §5) |
| `text-metadata` | `#94A3B8` | Repository metadata (owner, branch, URL labels) |
| `text-disabled` | `#5C5866` | Disabled control labels |

### 2.3 Violet Family (Primary Accent — Interaction & AI Identity)

| Token | Value | Permitted uses | Forbidden uses |
|---|---|---|---|
| `accent-violet-ui` | `#8B5CF6` | Borders, icons, focus rings, indicators, non-text UI elements | Text, links, button fills |
| `accent-violet-surface` | `#7C3AED` | Filled CTA/button backgrounds | Text, borders, icons |
| `accent-violet-surface-pressed` | `#6D28D9` | Pressed/active filled CTA/button backgrounds | Text, borders, icons |
| `accent-violet-soft` | `#A78BFA` | Text, links, citations, active navigation labels | Large filled backgrounds |

### 2.4 Pink Family (Secondary Accent — Brand & User Identity)

| Token | Value | Permitted uses | Forbidden uses |
|---|---|---|---|
| `accent-pink` | `#EC4899` | User message surfaces (tinted, not solid — see §4), brand marks, small accent details | Body text, primary CTA backgrounds, large surfaces |
| `accent-pink-tint` | `#EC4899` at 12% opacity over `bg-surface` | User message bubble background | Anywhere requiring text-level contrast on its own |

### 2.5 Support Colors

| Token | Value | Permitted uses | Forbidden uses |
|---|---|---|---|
| `accent-blue` | `#6366F1` | Secondary selection/state support (non-text UI) | Body text |
| `success` | `#34D399` | Success icon/border/indicator; success text ≥14px | Sole indicator of success (must pair with icon/label) |
| `warning` | `#FBBF24` | Warning icon/border/indicator; warning text ≥14px | Sole indicator of warning (must pair with icon/label) |
| `error` | `#F87171` | Error icon/border/indicator/text | Sole indicator of error (must pair with icon/label) |

### 2.6 Borders

| Token | Value | Purpose |
|---|---|---|
| `border-subtle` | `#272332` | Default separation between regions |
| `border-hover` | `#3A3448` | Input/element hover state |
| `border-focus` | `#8B5CF6` (`accent-violet-ui`) | Focus state |
| `border-error` | `#F87171` (`error`) | Error state |

---

## 3. Permitted / Forbidden Usage Matrix

Every color-bearing component must be checked against this table before shipping.

| Token | As background | As text | As border/icon |
|---|---|---|---|
| `accent-violet-ui` | ✗ Forbidden | ✗ Forbidden | ✓ Permitted |
| `accent-violet-surface` | ✓ Permitted (CTA only) | ✗ Forbidden | ✗ Forbidden |
| `accent-violet-soft` | ✗ Forbidden (large areas) | ✓ Permitted | ✓ Permitted (small accents) |
| `accent-pink` | ✗ Forbidden (solid, large) | ✗ Forbidden | ✓ Permitted (small accents) |
| `accent-pink-tint` | ✓ Permitted (user messages only) | — | — |
| `success` / `warning` / `error` | ✗ Forbidden (as sole indicator) | ✓ Permitted | ✓ Permitted |

**Rule:** if a new component needs a color not covered by this matrix, it goes back to Foundations for review — it is not decided at the page-spec level.

---

## 4. Surface Compatibility Matrix (Contrast-Validated)

All ratios below are calculated against the specific background listed. ✓ = passes WCAG 2.2 AA for the stated text size. ✗ = fails; usage restricted per note.

| Token | on `bg-primary` | on `bg-sidebar` | on `bg-surface` | on `bg-elevated` | on `bg-code` |
|---|---|---|---|---|---|
| `text-primary` | 15.8:1 ✓ | 14.9:1 ✓ | 13.6:1 ✓ | 12.1:1 ✓ | 16.4:1 ✓ |
| `text-secondary` | 8.1:1 ✓ | 7.7:1 ✓ | 7.1:1 ✓ | 6.4:1 ✓ | 8.4:1 ✓ |
| `text-muted` | 6.8:1 ✓ | 6.5:1 ✓ | 6.3:1 ✓ | 5.7:1 ✓ | 7.0:1 ✓ |
| `text-metadata` | 7.6:1 ✓ | 7.3:1 ✓ | 6.9:1 ✓ | 6.2:1 ✓ | 7.9:1 ✓ |
| `accent-violet-soft` (text) | 6.4:1 ✓ | 6.1:1 ✓ | 5.8:1 ✓ | 5.4:1 ✓ | 6.6:1 ✓ |
| `accent-violet-ui` (non-text, 3:1 threshold) | 4.7:1 ✓ | 4.5:1 ✓ | 4.2:1 ✓ | 3.9:1 ✓ | — |
| `accent-violet-surface` + `text-primary` on it | — | — | — | — | 5.02:1 ✓ (own surface, not app bg) |
| `success` / `warning` / `error` (text ≥14px) | 5.1–6.9:1 ✓ | — | — | — | — |

**Notes:**
- `accent-violet-surface` and `accent-violet-surface-pressed` are evaluated as button fills, not against app backgrounds — see §6 for those pairings.
- `text-disabled` is intentionally excluded from AA requirements per WCAG's disabled-content exception, but must remain visually distinguishable from its surface (minimum 1.5:1 non-text separation).

---

## 5. Corrections Applied During Design Review

Documented here so the reasoning isn't lost:

- **`text-muted` revised from `#77717F` → `#9A95A3`.** Original value measured 3.9–4.2:1 across surfaces, failing AA for 12–13px metadata text. Revised value clears 5.7:1+ everywhere.
- **Violet split into three roles instead of one.** A single mid-luminance violet (`#8B5CF6`) cannot simultaneously serve as light-text-on-dark-fill *and* dark-fill-under-light-text — these require opposite ends of the lightness range. Resolved into `accent-violet-ui` (non-text), `accent-violet-surface` (fills), `accent-violet-soft` (text).
- **Home CTA changed from "pink surface + violet text" (1.2:1, fails badly) → "violet-surface + warm-white text" (5.02:1, passes).** Pink retained as secondary brand accent instead (logo mark, small highlights) rather than as CTA color.
- **CTA hover changed from "brighten fill" to "preserve fill, add border/glow/elevation."** Brightening `accent-violet-surface` toward `accent-violet-ui` would have reintroduced the original contrast failure.

---

## 6. Interaction States (Primary CTA Reference Pattern)

| State | Fill | Text | Border | Motion |
|---|---|---|---|---|
| Default | `accent-violet-surface` (`#7C3AED`) | `text-primary` | none | — |
| Hover | unchanged | unchanged | `accent-violet-ui`, subtle | `translateY(-1px)`, 150ms |
| Focus | unchanged | unchanged | `border-focus` visible ring | 100ms |
| Pressed | `accent-violet-surface-pressed` (`#6D28D9`) | unchanged | none | `scale(0.97)`, 100ms, ease-out |
| Disabled | `bg-surface` | `text-disabled` | `border-subtle` | none |

**Governing principle:** interaction states modify perception (elevation, border, scale, position) without changing an element's semantic color role or breaking its validated contrast.

---

## 7. Typography

**UI font:** Inter. **Code font:** JetBrains Mono (fallback: IBM Plex Mono).

| Element | Size | Weight | Font |
|---|---|---|---|
| Hero headline | 48–56px | 600–700 | Inter |
| Repository name (Overview) | 32–40px | 600 | Inter |
| Page title | 28–32px | 600 | Inter |
| Section heading | 20–24px | 600 | Inter |
| Body | 14–16px | 400 | Inter |
| Secondary text | 13–14px | 400 | Inter |
| Navigation label | 13–14px | 500 | Inter |
| Metadata | 12–13px | 400–500 | Inter |
| Code | 13–14px | 400 | JetBrains Mono |

**Rule:** monospace is reserved for source code and inline code references only — never used for general interface text.

---

## 8. Spacing

8px base system: `4 / 8 / 12 / 16 / 24 / 32 / 48 / 64`

Use the smallest value that satisfies the layout; do not introduce off-scale values (e.g. 20px, 28px) without a documented exception.

---

## 9. Radius

| Element | Radius |
|---|---|
| Input | 6–8px |
| Button | 6–8px |
| Small surface | 8px |
| Larger card | 10–12px |
| Modal | 12px |
| Code/editor panels | 0–6px depending on placement |

**Rule:** avoid 16–24px+ radii anywhere. Sharper, controlled geometry reinforces the developer-tool identity over a generic SaaS aesthetic.

---

## 10. Elevation Model

```
Level 0 — bg-primary   (#0B0A0F)  Main application
Level 1 — bg-sidebar   (#111019)  Sidebar
Level 2 — bg-surface   (#15131D)  Cards / grouped content
Level 3 — bg-elevated  (#1B1825)  Modals / dropdowns / popovers

bg-code (#0D1117) — separate semantic surface, not part of the elevation ladder.
Signals "this is source code" independent of app chrome elevation.
```

Each level increases in luminance to reinforce depth. Borders (Section 11) reinforce separation between levels where background contrast alone is insufficient.

---

## 11. Borders

| Token | Value | Purpose |
|---|---|---|
| `border-subtle` | `#272332` | Default — communicates separation, not decoration |
| `border-hover` | `#3A3448` | Input/element hover |
| `border-focus` | `#8B5CF6` | Focus state (input, button) |
| `border-error` | `#F87171` | Validation error state |

**Rule:** borders should be nearly invisible at rest. Violet borders appear only on interaction (hover/focus), never as a permanent default outline — this is what makes violet communicate "you are interacting with this" rather than becoming ambient noise.

---

## 12. Motion

| Interaction | Duration | Easing | Notes |
|---|---|---|---|
| Button hover (border/glow appear) | 150ms | ease-out | No fill color change |
| Button press | 100ms | ease-out | `scale(0.97)`, returns on release |
| Input focus (border → violet) | 100ms | ease-out | Paired with focus ring |
| Navigation active-state change | 150–200ms | ease-in-out | Background + indicator + text color together |
| Panel/page transition | 200–250ms | ease-in-out | Largest permitted duration |
| Modal/dropdown appear | 150ms | ease-out | Combine with slight scale/opacity, not bounce |

**Rule:** motion communicates state change, acknowledgment, or appearance — never decoration. No easing curves that overshoot or bounce; CodeAtlas should feel precise, not playful.

---

## 13. Accessibility Rules

1. All normal text must meet **WCAG 2.2 AA ≥4.5:1**; large text (≥18.66px regular or ≥14pt/18.7px bold) may use the **≥3:1** exception.
2. Non-text UI indicators (focus rings, active-state borders, icons carrying meaning) must meet **≥3:1** against their adjacent background.
3. **No semantic state may be communicated by color alone.** Active navigation = background + border + icon + text weight, together. Error = red + icon + message text. Success = green + icon + message text.
4. Every semantic color token is validated against every surface it is permitted to appear on (Section 4) before use — not spot-checked after the fact.
5. Disabled elements are exempt from the 4.5:1 requirement but must remain visually distinguishable (≥1.5:1) from their surface.
6. Design with margin above the minimum threshold where feasible, rather than targeting exactly 4.5:1.

---

## 14. Component-State Conventions

These conventions apply system-wide and are inherited by every page spec unless a page explicitly documents a justified exception (which must be approved at the Foundations level).

| State | Convention |
|---|---|
| **Default** | Token values as defined in this document; no ambient color unless functionally meaningful |
| **Hover** | Border/elevation/subtle glow change; avoid fill-color brightening on validated-contrast fills |
| **Focus** | Visible `border-focus` ring; never removed for aesthetic reasons |
| **Active/Selected** | Background tint + border/indicator + icon color + text weight/color, combined |
| **Pressed** | Slight scale reduction (~0.97) and/or fill darkening, if contrast is revalidated |
| **Disabled** | `text-disabled` + `bg-surface` + `border-subtle`; no hover/focus behavior |
| **Error** | `border-error` + `error` icon + explanatory text; never border color alone |
| **Loading** | Subtle, non-distracting indicator; no color role changes |

---

## Governing Principles (Carried Into All Page Specs)

1. **Violet = interaction and AI identity. Pink = brand and user identity.** Neither is a general-purpose accent.
2. **One hue, multiple lightness roles** — never force a single token to serve as both a fill and text color across contexts.
3. **Progressive disclosure** — Overview (what), Files (what's inside), Chat (why) — increasing information depth, never all at once.
4. **Recognition over recall** — breadcrumbs, visible file trees, and named source references over memorized paths.
5. **Restraint** — rounded cards, gradients, and glow are used only where they carry meaning, never as default decoration.
6. **Accessibility is a constraint on the token, not a patch on the component.**

---

*This document supersedes all prior color/type/spacing decisions made during design review. Pages 02–07 reference these tokens by name and may not redefine them.*
