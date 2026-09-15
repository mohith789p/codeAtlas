# CodeAtlas Design System
## 02 — Home Page

**References:** `01 — Foundations & Design Tokens`. All colors, type, spacing, radius, and motion values below are token names defined there — no new values are introduced in this document.

**Purpose of this page:** establish what CodeAtlas does before asking the user for anything. This is the only marketing-oriented surface in the product; everything past this page is workspace, not landing page.

---

## 1. Page Intent & Hierarchy

The page must communicate, in order of visual weight:

1. **What CodeAtlas is** (headline)
2. **What it lets you do** (supporting statement)
3. **How to start** (the two entry actions)

The headline and supporting statement carry more visual weight than the buttons. This is a deliberate reversal of typical landing-page hierarchy, where the CTA usually dominates — here, understanding precedes action, consistent with the product's progressive-disclosure principle (Foundations §"Governing Principles").

---

## 2. Layout

- Centered, single-column composition. No sidebar, no navigation chrome — this page exists outside the Dashboard shell entirely.
- Generous vertical whitespace above and below the headline block, built from the 8px spacing scale (recommend `64`–`64` top/bottom margin at desktop widths, scaling down on smaller viewports).
- Background: `bg-primary`. No secondary surface elevation on this page — it should read as one plane, reinforcing its role as a threshold rather than a workspace.

---

## 3. Headline & Supporting Statement

| Element | Token | Notes |
|---|---|---|
| Headline text | `text-primary`, Hero headline scale (48–56px, weight 600–700) | e.g. "Understand your codebase." |
| Supporting statement | `text-secondary`, Body scale (14–16px, weight 400) | One to two sentences: explore files, discover architecture, ask questions about the repository. |

The supporting statement should not exceed ~2 lines at desktop width — this is a threshold, not a feature list. If more explanation is needed, it belongs in the Ingestion page's contextual reassurance copy (see `03 — Ingestion Page`), not here.

---

## 4. Repository Entry Actions

Two entry options, presented as a pair, visually secondary to the headline but still prominent enough to be immediately actionable.

### 4.1 Primary CTA

| Property | Value |
|---|---|
| Background (default) | `accent-violet-surface` |
| Text | `text-primary` |
| Border (default) | none |
| Radius | Button scale, 6–8px |
| Contrast | 5.02:1 — passes AA (validated in Foundations §4, §5) |

**States** (inherits the Foundations §6 CTA reference pattern exactly — do not modify):

| State | Fill | Border | Motion |
|---|---|---|---|
| Default | `accent-violet-surface` | none | — |
| Hover | unchanged | `accent-violet-ui`, subtle | `translateY(-1px)`, 150ms ease-out |
| Focus | unchanged | `border-focus` ring, visible | 100ms |
| Pressed | `accent-violet-surface-pressed` | none | `scale(0.97)`, 100ms ease-out, returns on release |

Do not brighten the fill on hover under any circumstance — this was a resolved contrast failure in Foundations review (§5) and must not be reintroduced at the page level.

### 4.2 Secondary Entry Option

The second repository-entry path (e.g. "Browse a public repository" or equivalent — exact copy TBD by product) should be visually subordinate to the primary CTA:

| Property | Value |
|---|---|
| Background | transparent or `bg-surface` |
| Text | `accent-violet-soft` |
| Border | `border-subtle`, becoming `border-hover` on hover |
| Radius | Button scale, 6–8px |

This keeps only one filled, high-commitment action on the page, with the second option available but clearly lower-emphasis — consistent with the "one primary action per view" restraint principle.

---

## 5. Brand Accent (Pink)

Pink appears on this page only as a **brand accent**, never as a CTA color or large surface fill (per Foundations §2.4, §3).

Acceptable placements:
- A small mark or detail within the CodeAtlas logo/wordmark
- A subtle accent line, dot, or gradient sliver near the headline (restrained — not a glowing background wash)
- If a violet-to-pink gradient is used at all, it is confined to a small decorative element (e.g. a logo mark or thin accent line), never a full-bleed background treatment

**Explicitly forbidden on this page:** pink as button fill, pink as body text, pink as a large background wash. These were the original design's contrast failure points and are closed per Foundations §5.

---

## 6. Typography Reference

| Element | Token/Scale |
|---|---|
| Headline | `text-primary`, Hero headline (48–56px / 600–700) |
| Supporting statement | `text-secondary`, Body (14–16px / 400) |
| Button label | `text-primary` (primary CTA) / `accent-violet-soft` (secondary) — Navigation-scale weight (500) recommended for button labels, 14–16px |

---

## 7. Motion

| Interaction | Duration | Notes |
|---|---|---|
| Page load / headline appear | 200–250ms | Simple fade/slight upward motion; no bounce |
| Primary CTA hover/press | Per Foundations §6 / §12 | Inherited exactly, not redefined |
| Secondary CTA hover | 150ms ease-out | Border transition only |

No scroll-triggered animation, no parallax, no glowing ambient background motion — this page communicates confidence through restraint, not spectacle.

---

## 8. Accessibility Notes Specific to This Page

- Both entry actions must be reachable and operable via keyboard, with `border-focus` visible on tab-focus for each.
- Headline and supporting statement contrast are pre-validated via `text-primary`/`text-secondary` on `bg-primary` (Foundations §4) — no further checks needed unless the background token changes.
- If a decorative gradient or accent mark is added near the headline, it must not reduce headline text contrast below the validated ratio — decorative elements sit behind or beside text, never as a scrim under it without re-verification.

---

## 9. What This Page Is Not

- Not a feature-tour or scrolling marketing page with multiple sections, testimonials, or pricing.
- Not the place for repository metadata, product screenshots, or dashboard previews — those risk pulling visual weight away from the headline and previewing the workspace before the user has committed to entering it.
- Not a surface for the violet/pink gradient to "dominate" — Foundations explicitly rules this out as a generic-AI-startup signal to avoid.

---

*This page inherits all color, type, spacing, radius, and motion tokens from `01 — Foundations & Design Tokens`. Any value not explicitly overridden above follows the Foundations default.*
