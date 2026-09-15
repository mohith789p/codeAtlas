# CodeAtlas Design System
## 06 — Files Page

**References:** `01 — Foundations & Design Tokens`, `04 — Dashboard Shell`. All colors, type, spacing, radius, and motion values below are token names defined in Foundations. Sidebar/navigation are inherited exactly from the Shell document and are not redefined here.

**Purpose of this page:** answer the user's second question — *"What is inside this repository?"* — through a VS Code-inspired but not VS Code-cloned browsing experience.

**Governing constraint:** code readability and navigation take priority over visual decoration. This page should feel the most restrained of the three Dashboard pages.

---

## 1. Layout Structure

```
┌───────────┬────────────────────────────────────────┐
│           │  Breadcrumb / path indicator            │
│           ├────────────────────────────────────────┤
│ File Tree │                                          │
│  (left)   │           Code Viewer                    │
│           │           (right)                        │
│           │                                          │
└───────────┴────────────────────────────────────────┘
```

- File tree: fixed-width left panel, within the Dashboard content area (distinct from the persistent Shell sidebar — this is a page-local panel, not global navigation).
- Breadcrumb/path indicator: sits above the code viewer, full width of the right panel.
- Code viewer: fills remaining space, scrolls independently of the file tree.

---

## 2. File Tree

| Property | Value |
|---|---|
| Background | `bg-sidebar` or `bg-primary` — recommend matching the Shell sidebar tone (`bg-sidebar`) so the file tree reads as "structural navigation," visually distinct from the code surface itself |
| Folder/file label (default) | `text-secondary` |
| Folder/file label (hover) | `text-primary`, with `bg-surface`-level row highlight |
| Currently selected file | `text-primary`, with a subtle `accent-violet-ui` left indicator or row tint — same visual language as Shell active-nav-item, applied at file-tree scale |
| Folder/file icons | Single consistent icon family (matches Shell navigation icon style) — no mixed icon sets |
| Indentation | Consistent per nesting level, sufficient to convey hierarchy without excessive horizontal scroll |

**Rule:** the "currently selected file" treatment intentionally echoes the Shell's active-navigation pattern (background tint + border indicator + text brightness) so the user learns one visual language for "this is where I am" and sees it reused consistently across the whole product, not reinvented per page.

---

## 3. Breadcrumb / Path Indicator

| Element | Token |
|---|---|
| Path segments (non-current) | `text-metadata` |
| Separator (`/`) | `text-muted` |
| Current file segment | `text-primary` |
| Interactive segments (clickable to navigate up) | `accent-violet-soft` on hover only — remain `text-metadata` at rest, per the same "violet signals interaction, not permanent decoration" rule used on Ingestion |

**Rule:** breadcrumb segments should not be violet by default — this would repeat the "violet applied everywhere" mistake ruled out in `03 — Ingestion Page`. Violet appears only on hover/interaction.

---

## 4. Code Viewer

| Property | Value |
|---|---|
| Background | `bg-code` — the dedicated semantic surface, separate from the app's elevation ladder (Foundations §10) |
| Line numbers | `text-muted`, monospace, right-aligned within their gutter |
| Code text (default) | `text-primary` as the base, with syntax highlighting applied on top |
| Current line / selection | Subtle `bg-surface`-level or slightly lighter row highlight — not a violet or pink tint, since this needs to read as "editor," not "product chrome" |
| Font | JetBrains Mono (or IBM Plex Mono fallback), Code scale (13–14px / 400) |

**Syntax highlighting:** not specified token-by-token in this document (language-specific highlighting palettes are a separate technical concern), but any highlight colors introduced must be checked against `bg-code` for AA contrast before use, following the same validation discipline as every other token in this system. Recommend a neutral, VS Code-Dark-adjacent highlighting palette rather than introducing CodeAtlas's violet/pink accents into syntax coloring — the code viewer's job is readability, and mixing product-brand colors into syntax highlighting would blur that (per §6 below).

---

## 5. Explicitly Restrained Elements

Per the original design intent, the following are **forbidden** within the code viewer and file tree:

- Pink backgrounds or pink accents of any kind
- Glowing borders or focus rings around the code panel
- Large rounded cards wrapping the code viewer
- Excessive CodeAtlas branding elements inside the code-viewing area

The code viewer's radius should be minimal — per Foundations §9, 0–6px depending on placement, not the 10–12px card scale used elsewhere in the product.

---

## 6. Relationship to Product Brand Colors

This is the one Dashboard page where the product's violet/pink identity is least visible, and that is intentional:

- Violet appears only for the *currently selected file* indicator in the tree and *interactive breadcrumb segments on hover* — both are functional, not decorative.
- Pink does not appear anywhere on this page.
- The code viewer's neutral, VS Code-inspired palette exists specifically so it doesn't compete with or dilute the meaning of syntax highlighting, and so developers can rely on familiar visual conventions for reading code.

This reflects the Foundations governing principle that restraint increases as content density and technical seriousness increase — this page is the most information-dense of the three, so it carries the least decoration.

---

## 7. Typography Reference

| Element | Token/Scale |
|---|---|
| File tree label | `text-secondary` (default) / `text-primary` (selected), 13–14px |
| Breadcrumb (non-current) | `text-metadata`, 12–13px |
| Breadcrumb (current) | `text-primary`, 12–13px |
| Code | `text-primary` (base) + syntax palette, JetBrains Mono, 13–14px / 400 |
| Line numbers | `text-muted`, JetBrains Mono, 13–14px |

---

## 8. Motion

| Interaction | Duration | Notes |
|---|---|---|
| File tree row hover | 100ms ease-out | Background tint only |
| File selection change | 150ms ease-in-out | Indicator + text color transition together, same pattern as Shell active-nav |
| Breadcrumb hover | 100ms | Color transition only, no layout shift |
| Code viewer scroll-to-line (e.g. from a Chat citation) | 200–250ms ease-in-out | Smooth scroll, not instant jump — helps orientation when arriving from Chat |

---

## 9. Accessibility Notes Specific to This Page

- File tree must be fully keyboard-navigable (arrow keys or tab order through visible items), with `border-focus` distinguishable from the "currently selected file" indicator.
- Code viewer must support text selection and copy via standard means — no custom behavior that blocks normal browser text interaction.
- Line numbers and syntax highlighting must not be the sole means of conveying any functional state (e.g. "this line has an error/citation") — pair with an icon or margin indicator, consistent with Foundations §13 rule 3.
- Breadcrumb links must be reachable and operable via keyboard, with visible focus state distinct from hover-only violet.

---

## 10. What This Page Is Not

- Not an attempt to fully reproduce the VS Code interface — CodeAtlas conventions (Shell-consistent active-state language, restrained icon set) take precedence over pixel-matching an external editor.
- Not a place for AI explanation or chat content — this page displays code and structure only; explanation and investigation belong to Chat (`07`), which links back into this page via citations.
- Not a place for violet/pink brand expression beyond the two functional exceptions noted in §6.

---

*This page inherits all color, type, spacing, radius, and motion tokens from `01 — Foundations & Design Tokens`, and inherits sidebar/navigation structure from `04 — Dashboard Shell`.*
