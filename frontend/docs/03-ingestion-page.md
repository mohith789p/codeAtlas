# CodeAtlas Design System
## 03 — Ingestion Page

**References:** `01 — Foundations & Design Tokens`. All colors, type, spacing, radius, and motion values below are token names defined there — no new values are introduced in this document.

**Purpose of this page:** collect repository information (URL, username, repository name, optional branch) with low cognitive load and high trust, before the user commits their repository to CodeAtlas.

---

## 1. Page Intent

This page sits between the Home Page (marketing threshold) and the Dashboard (workspace). Its job is narrow and specific: get correct repository details from the user with minimal friction and maximum reassurance. It should feel calmer and more procedural than the Home Page — fewer visual flourishes, more clarity.

**Governing principle:** violet should communicate *current interaction*, not decorate the whole page. At rest, this page should look almost entirely neutral — the moment a user engages with an input is the moment violet appears.

---

## 2. Layout

- Centered, single-column form, narrower than the Home Page's headline block (form width should not stretch full-bleed at desktop — recommend a max-width comfortable for a 4-field form, roughly matching the width of the Home Page CTA pair).
- Background: `bg-primary`, consistent with Home Page.
- Form container may sit on `bg-surface` as a single grouped surface (Level 2 elevation) if visual separation from the page background helps scannability — this is the one acceptable use of a card-like surface on this page, since it represents a genuine meaningful grouping (Foundations governing principle on restraint).

---

## 3. Form Fields

Four inputs: Repository URL, Username, Repository Name, Branch (optional).

### 3.1 Field Anatomy

| Element | Token | Notes |
|---|---|---|
| Label | `text-secondary` (default) — **not** `accent-violet-soft` | Labels stay neutral; violet is reserved for the active interaction signal, not applied to static label text |
| Input background | `bg-code` or `bg-primary` (black/charcoal) | Must contrast sufficiently against the surrounding `bg-surface` form container |
| Input text | `text-primary` | High-contrast, warm white |
| Placeholder text | `text-muted` | Validated at 5.7–6.8:1 across surfaces per Foundations §4 |
| Border (default/rest) | `border-subtle` | Neutral — no violet outline at rest |
| Border (hover) | `border-hover` | Slightly more visible; signals "this is interactive" without committing to focus color |
| Border (focus) | `border-focus` (`accent-violet-ui`) | Full violet commitment only on actual focus |
| Focus ring | `accent-violet-ui`, per Foundations §11 | Paired with border transition, 100ms ease-out |

### 3.2 State Progression (Rest → Hover → Focus)

This three-step progression is the core interaction pattern of this page:

1. **Rest:** `border-subtle`, no violet anywhere on the field.
2. **Hover:** `border-hover` — a barely-brighter neutral gray, signaling interactivity without color commitment.
3. **Focus:** `border-focus` + visible focus ring — violet now clearly marks "you are here."

This progression is what makes violet meaningful. If violet appeared at rest across all four fields simultaneously, it would stop signaling anything — this is the direct application of the Foundations rule that borders "communicate separation, not decoration" (§11) and that violet should not become ambient noise (§11 rule).

### 3.3 Optional Field (Branch)

- Label includes "(optional)" in `text-muted`, not a separate color treatment — optionality is communicated through text, not through a different border or background color.
- No visual de-emphasis beyond the label text itself; the input remains fully legible and equally styled to the required fields, since users should not need to guess whether an optional field "counts."

---

## 4. Validation & Error States

| State | Border | Icon/Text | Notes |
|---|---|---|---|
| Valid (optional, on blur) | `border-subtle` (no change) or brief `success` accent if confirming a fetched repo | `success` icon + short label if used | Not required for every field — reserve for meaningful confirmations (e.g. "Repository found") |
| Invalid | `border-error` | `error` icon + explanatory text below field | Never border color alone — text must state what's wrong (Foundations §13 rule 3) |

Error text sits directly below the affected field, in `error` token color, at Secondary text scale (13–14px).

---

## 5. Contextual Reassurance

Per the original design intent, this page must reduce user hesitation about providing repository information. Include a short, quiet reassurance statement near the form — not a banner, not a modal, not an alert-styled callout.

| Property | Value |
|---|---|
| Text color | `text-secondary` |
| Scale | Secondary text (13–14px) |
| Placement | Directly below the form, or inline near the submit action — low visual weight, present but not competing with the form itself |
| Tone | Factual, specific (what CodeAtlas will read, what it won't do) rather than generic trust-badge language |

This element should never use `error`/`warning` colors or an alert-box treatment — it is reassurance, not a warning.

---

## 6. Submit Action

Follows the same CTA pattern as the Home Page primary button (Foundations §6), unmodified:

| State | Fill | Text | Border | Motion |
|---|---|---|---|---|
| Default | `accent-violet-surface` | `text-primary` | none | — |
| Hover | unchanged | unchanged | `accent-violet-ui`, subtle | `translateY(-1px)`, 150ms |
| Focus | unchanged | unchanged | `border-focus` ring | 100ms |
| Pressed | `accent-violet-surface-pressed` | unchanged | none | `scale(0.97)`, 100ms |
| Disabled (form incomplete/invalid) | `bg-surface` | `text-disabled` | `border-subtle` | none |

The submit button should be disabled (not hidden) until required fields are validly filled — this gives the user a persistent, visible target rather than one that appears only once the form is "correct," reducing uncertainty about what's required.

---

## 7. Typography Reference

| Element | Token/Scale |
|---|---|
| Page title (if present, e.g. "Connect a repository") | `text-primary`, Page title scale (28–32px / 600) |
| Field labels | `text-secondary`, Navigation-adjacent scale (13–14px / 500) |
| Input text | `text-primary`, Body scale (14–16px / 400) |
| Placeholder | `text-muted`, Body scale |
| Reassurance copy | `text-secondary`, Secondary text scale (13–14px / 400) |
| Error text | `error`, Secondary text scale (13–14px / 400) |

---

## 8. Motion

| Interaction | Duration | Notes |
|---|---|---|
| Border rest → hover | 100ms ease-out | Subtle, near-instant |
| Border hover/rest → focus | 100ms ease-out | Paired with focus ring appearance |
| Error message appear | 150ms | Simple fade/slide-in below field, no bounce |
| Submit button | Per Foundations §6 | Inherited exactly |

---

## 9. Accessibility Notes Specific to This Page

- Every input must have a visibly associated `<label>` (not placeholder-as-label) — placeholders are supplementary, not a substitute for labels, both for accessibility and because placeholder text disappears on input.
- Focus ring (`border-focus`) must be visible via keyboard navigation for every field and the submit button, in the same order as visual tab order.
- Error text must be programmatically associated with its field (e.g. `aria-describedby`) so screen reader users receive the explanation, not just the color change.
- Disabled submit button must be marked as disabled in a way assistive technology recognizes, not merely styled to look inactive.

---

## 10. What This Page Is Not

- Not a multi-step wizard — all fields appear together; the "low cognitive load" goal is achieved through restraint and clarity of a single screen, not by hiding fields across steps.
- Not a place for violet to appear as a permanent decorative outline on every field — this was explicitly identified as visual noise and ruled out.
- Not a place for repository previews, statistics, or Dashboard-style content — that begins only after successful submission, on the Dashboard itself.

---

*This page inherits all color, type, spacing, radius, and motion tokens from `01 — Foundations & Design Tokens`. Any value not explicitly overridden above follows the Foundations default.*
