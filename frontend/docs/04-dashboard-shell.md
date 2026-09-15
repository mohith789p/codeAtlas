# CodeAtlas Design System
## 04 — Dashboard Shell

**References:** `01 — Foundations & Design Tokens`. All colors, type, spacing, radius, and motion values below are token names defined there — no new values are introduced in this document.

**Purpose of this document:** define the persistent structure — sidebar, navigation, active-state behavior — shared by all three Dashboard pages (`05 — Overview`, `06 — Files`, `07 — Chat`). Those documents describe only their content area; this document is their container.

---

## 1. Shell Intent

Once a repository is connected, CodeAtlas shifts identity: from marketing threshold (Home) and procedural form (Ingestion) into a serious developer workspace — "a combination of a modern IDE and an AI investigation environment." The shell is what carries that shift. It should read as calm, structural, and permanent — the user will spend most of their time inside it.

---

## 2. Layout Structure

```
┌─────────────┬──────────────────────────────────────┐
│             │                                        │
│   Sidebar   │           Content Area                │
│  (Level 1)  │         (page-specific: 05/06/07)      │
│             │                                        │
│             │                                        │
└─────────────┴──────────────────────────────────────┘
```

- **Sidebar:** fixed width, `bg-sidebar` (Level 1 elevation). Persistent across Overview, Files, and Chat.
- **Content area:** `bg-primary` (Level 0) as its base, with individual pages introducing their own Level 2/3 surfaces as needed per their own specs.
- The luminance step from `bg-sidebar` → `bg-primary` should be perceptible but subtle — per Foundations §10, this is a deliberate small step, not a strong visual break. The sidebar should feel like part of the same room as the content, not a separate panel bolted on.

---

## 3. Sidebar Composition

Top to bottom:

1. **CodeAtlas identity** (logo/wordmark, compact)
2. **Primary navigation:** Overview, Files, Chat
3. *(Optional, lower priority, visually de-emphasized if present: repository switcher, settings, account — not specified here as they fall outside the three core pages)*

### 3.1 Identity Block

| Property | Value |
|---|---|
| Background | `bg-sidebar` (inherits, no separate treatment) |
| Text/mark color | `text-primary`, with pink used only as a small accent per Foundations §2.4/§3 (e.g. a mark detail) — never as the dominant color of the lockup |
| Spacing below | One clear step on the 8px scale (recommend `32`) separating identity from navigation |

---

## 4. Primary Navigation

Three items: **Overview**, **Files**, **Chat**. Each has an icon (single consistent icon family — no mixed styles, no emoji) and a label.

### 4.1 Inactive Navigation Item

| Property | Value |
|---|---|
| Background | transparent (`bg-sidebar` shows through) |
| Icon color | `text-secondary` |
| Label color | `text-secondary` |
| Label weight | Navigation scale, 500 |

### 4.2 Active Navigation Item

This is the highest-priority state-communication pattern in the shell, and it must follow the Foundations §13 rule 3 ("no semantic state by color alone") exactly:

| Property | Value |
|---|---|
| Background | subtle violet-blue tint — a low-opacity wash of `accent-violet-ui` or `accent-blue` over `bg-sidebar` (recommend ~8–12% opacity; must not compete with content-area surfaces) |
| Left border/indicator | thin solid bar in `accent-violet-ui` |
| Icon color | `accent-violet-ui` |
| Label color | `text-primary` (brighter than inactive `text-secondary`) |
| Label weight | Navigation scale, 500 (unchanged weight — brightness and color carry the emphasis, not added boldness) |

Four simultaneous signals — background tint, border indicator, icon color, text brightness — combine so the active item is unmistakable even for a user who cannot perceive the violet hue difference alone.

### 4.3 Hover (Inactive Item, Not Active)

| Property | Value |
|---|---|
| Background | very subtle `bg-surface`-level tint, lighter than sidebar background |
| Icon/label color | unchanged (`text-secondary`) — hover signals "clickable," not "selected" |

Do not shift inactive-hover text or icon toward violet — that would blur the distinction between "hovering" and "active," undermining the whole point of the active-state signal above.

### 4.4 Navigation Item Sizing & Spacing

- Consistent row height across all three items.
- Icon and label horizontally aligned with consistent gap (recommend `12` on the spacing scale).
- Vertical gap between items on the 8px scale (recommend `4`–`8`).

---

## 5. Active-State Transition

When the user switches pages (e.g. Overview → Files):

| Element | Motion |
|---|---|
| Background tint | 150–200ms ease-in-out (Foundations §12: Navigation active-state change) |
| Border indicator | fades/slides in with the background, same duration |
| Icon/text color | transitions together with background, not staggered |
| Content area | Page/panel transition, 200–250ms ease-in-out |

All four active-state signals (§4.2) transition together as one unit — not staggered — so the state change reads as a single, immediate event rather than a sequence of small changes.

---

## 6. Borders & Separation

| Boundary | Treatment |
|---|---|
| Sidebar / content area | `border-subtle`, vertical, full height — thin, communicates separation only |
| Within sidebar (between identity and nav) | Spacing-only separation preferred over a visible border; introduce `border-subtle` only if spacing alone proves insufficient in implementation |

Consistent with Foundations §11: borders here are structural, not decorative. No glow, no gradient border treatment on the sidebar edge.

---

## 7. Typography Reference

| Element | Token/Scale |
|---|---|
| Identity/wordmark | `text-primary`, small compact lockup — not Hero scale; this is chrome, not a headline |
| Navigation label (inactive) | `text-secondary`, 13–14px / 500 |
| Navigation label (active) | `text-primary`, 13–14px / 500 |

---

## 8. What Belongs to the Shell vs. the Page Specs

| Belongs here (Shell) | Belongs to page specs (05/06/07) |
|---|---|
| Sidebar background, width, identity block | Content area layout and composition |
| Navigation item states (inactive/hover/active) | Repository data display (Overview) |
| Sidebar/content border | Code viewer, file tree (Files) |
| Active-state transition motion | Chat message layout, citations (Chat) |

Page specs must not redefine navigation states — they inherit this document exactly, the same way this document inherits Foundations.

---

## 9. Accessibility Notes Specific to This Shell

- Navigation items must be reachable via keyboard (tab order top-to-bottom) with `border-focus` visible on focus, distinct from the active-state indicator so a keyboard user can tell "focused" apart from "currently selected page."
- The active page must be announced to assistive technology (e.g. `aria-current="page"`), since the visual signal alone (background tint + border + icon + text color) does not reach screen reader users.
- Sidebar/content border (`border-subtle`) is a visual aid only — do not rely on it as the sole indication of a landmark boundary; use proper semantic regions (`nav`, `main`) underneath.

---

## 10. What This Shell Is Not

- Not a place for the sidebar to become "colorful" — only the active item carries violet; inactive items remain neutral gray, per the original design intent that the sidebar should not read as decorated chrome.
- Not a collapsible/expandable mega-sidebar with nested trees — the file tree lives inside the Files page content area (`06`), not the persistent shell navigation.
- Not a surface for pink — pink does not appear in the Dashboard shell at all; it remains scoped to brand moments (Home) and user-message identity (Chat), per Foundations §2.4.

---

*This document inherits all color, type, spacing, radius, and motion tokens from `01 — Foundations & Design Tokens`. Documents `05 — Overview`, `06 — Files`, and `07 — Chat` inherit this shell structure and describe only their content-area contents.*
