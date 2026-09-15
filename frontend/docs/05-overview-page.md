# CodeAtlas Design System
## 05 — Overview Page

**References:** `01 — Foundations & Design Tokens`, `04 — Dashboard Shell`. All colors, type, spacing, radius, and motion values below are token names defined in Foundations. Sidebar/navigation are inherited exactly from the Shell document and are not redefined here.

**Purpose of this page:** answer the user's first question upon entering the Dashboard — *"What is this repository?"* This is the shallowest, broadest level of the product's progressive-disclosure model.

---

## 1. Content Priority Order

Per the original design intent, content on this page is ordered strictly by importance, top to bottom:

1. **Repository identity** (name, description, links) — strongest visual element
2. **Scale and statistics** (files, folders, contributors, etc.) — compact, scannable
3. **Metadata** (owner, branch, language, URLs) — present but visually quiet
4. **Contributors** — who has worked on this repository

This ordering is not arbitrary — it mirrors how a developer actually orients themselves to an unfamiliar repository: identity first, scale second, details third, people last.

---

## 2. Repository Identity Block

The single strongest visual element on the page.

| Element | Token/Scale |
|---|---|
| Repository name | `text-primary`, Repository name scale (32–40px / 600) — warm-white or slightly warm sand-toned per original intent, achieved via `text-primary` |
| Description | `text-secondary`, Body scale (14–16px / 400), directly below the name |
| Repository links (homepage, external docs, etc.) | `accent-violet-soft` as link text — this is exactly the permitted use case for that token (Foundations §2.3) |

**Layout:** top of content area, no card/border wrapper — this block should feel like a page title, not a boxed widget. Consistent with the restraint principle: identity is established through typographic weight and position, not decoration.

---

## 3. Scale & Statistics

Compact information cards for file count, folder count, contributor count, and similar scale indicators.

| Property | Value |
|---|---|
| Card surface | `bg-surface` (Level 2 elevation) |
| Card border | `border-subtle` |
| Card radius | Larger-card scale, 10–12px |
| Number | `text-primary`, Section heading scale (20–24px / 600) — large enough to scan quickly, not large enough to become a dashboard-tile centerpiece |
| Label (e.g. "Files") | `text-metadata`, Metadata scale (12–13px / 400–500) |

**Sizing constraint:** these cards must not become oversized dashboard tiles. Recommend a compact fixed or content-driven width (roughly 120–180px), arranged in a horizontal row that wraps responsively. Their purpose is fast scanning of scale, not visual centerpiece status — this directly reflects the original instruction that stats "should not become oversized dashboard tiles."

---

## 4. Metadata

Owner, branch, language, repository URL, homepage URL, and similar fields.

| Property | Value |
|---|---|
| Label | `text-metadata` (cool gray-blue tone) |
| Value | `text-secondary` — one step brighter than the label, but still clearly subordinate to identity/statistics |
| Layout | Simple label/value pairs, either a compact two-column list or inline row — no card wrapper needed; this is not a "meaningful grouping" requiring elevation per Foundations restraint principle, just an information list |

Language indicator may use a small colored dot or icon if a language-color convention is desired, but this is a minor decorative accent and must not introduce new palette colors outside Foundations Section 1–2 — reuse existing accent/support tokens if a visual marker is needed.

---

## 5. Contributors

| Element | Token/Scale |
|---|---|
| Avatar | Circular, consistent size across the list |
| Contributor name | `text-primary` or `text-secondary` (recommend `text-secondary` — this section is lower priority than identity/stats per §1) |
| Contribution info (e.g. commit count) | `text-metadata`, Metadata scale |

**Layout guidance (per Foundations §"Cards" behavioral approach — no rigid dimensions mandated):**
- Prefer **compact rows** over large cards, consistent with the design-review decision that contributor entries default to rows unless there's enough information per contributor to justify a card treatment.
- Consistent row height within the list.
- Minimum readable padding; avoid excessive rounding on any row/card container (radius per Foundations §9 — small surface or card scale, not modal scale).

This section sits last in visual priority — it should not compete with the repository identity block or statistics cards for attention.

---

## 6. Surface & Elevation Usage on This Page

| Section | Surface |
|---|---|
| Repository identity | `bg-primary` (no card — page-level content) |
| Statistics | `bg-surface` (Level 2 — meaningful grouping) |
| Metadata | `bg-primary` (no card — simple list) |
| Contributors | `bg-surface` (Level 2, if using row containers) or `bg-primary` (if using a plain list) — either acceptable, but must be consistent across all contributor rows on this page |

Consistent with Foundations restraint principle: only Statistics and (optionally) Contributors receive elevated surfaces, because those are the only two sections representing genuine grouped information rather than a simple identity header or metadata list.

---

## 7. Typography Reference

| Element | Token/Scale |
|---|---|
| Repository name | `text-primary`, 32–40px / 600 |
| Description | `text-secondary`, 14–16px / 400 |
| Links | `accent-violet-soft`, 14–16px / 400 |
| Stat number | `text-primary`, 20–24px / 600 |
| Stat label | `text-metadata`, 12–13px / 400–500 |
| Metadata label | `text-metadata`, 12–13px / 400–500 |
| Metadata value | `text-secondary`, 13–14px / 400 |
| Contributor name | `text-secondary`, 14–16px / 400 |
| Contribution info | `text-metadata`, 12–13px / 400 |

---

## 8. Motion

| Interaction | Duration | Notes |
|---|---|---|
| Page enter (from navigation) | Inherits Shell §5 content-area transition, 200–250ms | Not redefined here |
| Stat card hover (if interactive/clickable) | 100–150ms ease-out | Subtle border brightening only, no fill change |
| Link hover (repository links) | 100ms | Underline or slight brightness shift on `accent-violet-soft` |

---

## 9. Accessibility Notes Specific to This Page

- Statistic cards, if clickable (e.g. linking to Files filtered by folder), must have visible focus states using `border-focus`.
- Contributor avatars must have appropriate alt text (contributor name at minimum) — they are not decorative.
- Metadata label/value pairs should use proper semantic markup (definition lists or equivalent) so the label-value relationship is conveyed to assistive technology, not just through visual proximity.
- Repository links styled in `accent-violet-soft` are pre-validated for text contrast (Foundations §4) — no additional check needed unless placed on a non-standard background.

---

## 10. What This Page Is Not

- Not a data-dense analytics dashboard — statistics are a quick scan, not a detailed breakdown (that level of depth belongs conceptually to Chat's investigative capability, not Overview).
- Not the place to preview file contents or code — that's the Files page's job. Overview answers "what is this repository," not "what's inside it."
- Not a place for oversized tiles, glowing stat cards, or gradient-backed numbers — consistent with Foundations' rejection of oversized dashboard-tile treatments.

---

*This page inherits all color, type, spacing, radius, and motion tokens from `01 — Foundations & Design Tokens`, and inherits sidebar/navigation structure from `04 — Dashboard Shell`.*
