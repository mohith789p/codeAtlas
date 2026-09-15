# CodeAtlas Design System
## 07 — Chat Page

**References:** `01 — Foundations & Design Tokens`, `04 — Dashboard Shell`, `06 — Files Page` (for citation navigation target). All colors, type, spacing, radius, and motion values below are token names defined in Foundations. Sidebar/navigation are inherited exactly from the Shell document and are not redefined here.

**Purpose of this page:** answer the user's third and deepest question — *"Why does the code work this way?"* — through an evidence-driven investigation interface, not a generic chatbot.

**Governing constraint:** this page must not feel like "ChatGPT with a GitHub connector." Its defining feature is the visible, interactive link between every AI claim and the source code that supports it.

---

## 1. Layout Structure

```
┌────────────────────────────────────────────┐
│                                              │
│         Message History (scrollable)        │
│                                              │
│   [AI message + citations]                   │
│                          [User message]      │
│   [AI message + citations]                   │
│                                              │
├────────────────────────────────────────────┤
│         Chat Input (fixed, compact)          │
└────────────────────────────────────────────┘
```

- Message history scrolls independently; input remains anchored at the bottom at all times.
- No sidebar redefinition here — this page sits inside the Dashboard Shell exactly like Overview and Files.

---

## 2. Message Identity — User vs. AI

This is the primary color-coded distinction on the page, and it must follow the token roles exactly as frozen in Foundations.

### 2.1 User Messages

| Property | Value |
|---|---|
| Alignment | Right |
| Surface | `accent-pink-tint` (per Foundations §2.4 — a low-opacity pink tint over `bg-surface`, never solid `accent-pink` as a fill) |
| Text | `text-primary` |
| Radius | Small surface scale, 8px |

**Rule:** this is the one place in the entire product where pink functions as a message surface, not merely a decorative accent — and it is intentionally a *tint*, not a solid fill, so it never needs to satisfy button-fill-level contrast requirements and never risks the kind of failure identified in the original CTA color review.

### 2.2 AI Messages

| Property | Value |
|---|---|
| Alignment | Left |
| Surface | `bg-primary` or `bg-surface` (no tinted background — violet identity comes from the icon/label accent, not a colored bubble) |
| AI identity marker | Small icon or label in `accent-violet-ui` (icon color) or `accent-violet-soft` (if rendered as text, e.g. "CodeAtlas") |
| Response text | `text-primary` — **not** violet. Response text must remain neutral for reading comfort; violet marks *who is speaking*, not the content itself |

**Rule:** this directly implements the original design intent — "the actual AI response text should remain warm white or light gray for readability... color to identify who is speaking without sacrificing reading comfort." Do not tint the entire AI message bubble violet; that would fail exactly the same way a solid pink CTA background failed for text legibility, and more importantly would undermine long-form reading comfort across an entire conversation.

---

## 3. Citations & Source References — Core Feature

This is the single most important interactive element on this page, per the original design intent: it is what makes CodeAtlas trustworthy rather than "an unsupported block of generated text."

### 3.1 Visual Treatment

| Property | Value |
|---|---|
| Text color | `accent-violet-soft` — this is precisely the permitted use case defined in Foundations §2.3 (links, citations) |
| Underline/indicator | Optional subtle underline or icon (e.g. a small file icon) to reinforce that this is a link, not just colored text |
| Background | None at rest — citations are inline text elements, not badges or pills, to avoid visual clutter in dense responses |
| Hover | `accent-violet-ui` border/underline strengthens slightly, or background gains a very subtle `bg-elevated`-level tint to signal "this is clickable" |

### 3.2 Citation Content

Each citation must reference something concrete and specific: a file name, a symbol, or a line range (e.g. `auth/session.py:42–58`). Vague references ("in the codebase") do not qualify as citations and should not receive citation styling.

### 3.3 Citation Interaction

Clicking a citation navigates the user to the referenced location in the Files page (`06`), specifically:
- Opens/selects the referenced file in the file tree
- Scrolls the code viewer to the referenced line range using the smooth-scroll behavior defined in `06 — Files Page` §8
- The referenced line range may receive a brief, temporary highlight in the code viewer (using `bg-surface`-level tint, not violet/pink, to stay consistent with the Files page's restrained palette) to help the user immediately locate what the citation pointed to

### 3.4 Why This Matters (Design Rationale)

Per the original intent, this creates the product's core trust loop: the user sees what CodeAtlas concluded, can see *why* through the citation, and can verify the answer against real code. Every AI response containing a factual claim about the codebase should carry at least one citation — an uncited factual claim is treated as a content-quality issue, not just a style one.

---

## 4. Chat Input

| Property | Value |
|---|---|
| Position | Fixed/anchored at the bottom of the message area |
| Size | Compact — a developer command interface, not an oversized composition box |
| Background | `bg-surface` or `bg-elevated` (recommend `bg-surface`, Level 2, so it feels grounded rather than floating above everything) |
| Border (rest) | `border-subtle` |
| Border (focus) | `border-focus` (`accent-violet-ui`) — same rest→focus violet-commitment pattern used on Ingestion inputs |
| Text | `text-primary` |
| Placeholder | `text-muted` |
| Send action | Icon-based (not a large labeled button), using `accent-violet-ui` for the icon at rest, `accent-violet-surface` treatment only if rendered as a filled button |

**Rule:** the input's neutral-until-focus border behavior is the same pattern established in `03 — Ingestion Page` — one consistent visual language for "you are about to type here" across the whole product.

---

## 5. Empty State

When the user first arrives at Chat with no conversation history, the page must actively teach capability rather than showing a bare "Ask a question" prompt.

| Element | Value |
|---|---|
| Heading (optional) | `text-secondary`, short framing line |
| Example questions | Presented as a small set of clickable prompts (recommend 3–4), each styled as a compact row or chip on `bg-surface` with `border-subtle`, using `text-secondary` for the question text |
| Example question hover | `border-hover`, or a subtle `accent-violet-ui` border — signals interactivity without turning the whole chip violet |
| Clicking an example | Populates the chat input (or sends directly) with that question |

**Example question categories** (per original intent): how authentication works, where a function is used, how modules interact, where a feature is implemented. These are illustrative categories, not literal copy to hardcode — actual example questions should be generated relative to the connected repository where possible.

**Rule:** example-question chips must not use `accent-pink` — pink is reserved for user messages once a conversation exists; introducing it here would blur that meaning before the user has sent anything.

---

## 6. Surface & Elevation Usage on This Page

| Element | Surface |
|---|---|
| Message history background | `bg-primary` |
| User message bubble | `accent-pink-tint` over `bg-surface` |
| AI message | `bg-primary` (no bubble) or `bg-surface` (subtle bubble) — recommend no bubble, consistent with "text identified by icon, not by background" |
| Chat input | `bg-surface` |
| Empty-state example chips | `bg-surface` |

---

## 7. Typography Reference

| Element | Token/Scale |
|---|---|
| User message text | `text-primary`, Body scale (14–16px / 400) |
| AI message text | `text-primary`, Body scale (14–16px / 400) |
| AI identity label | `accent-violet-soft`, Navigation-adjacent scale (13–14px / 500) |
| Citation text | `accent-violet-soft`, Body or Secondary scale (13–16px / 400), inline with surrounding text |
| Chat input text | `text-primary`, Body scale (14–16px / 400) |
| Empty-state example questions | `text-secondary`, Secondary text scale (13–14px / 400) |

---

## 8. Motion

| Interaction | Duration | Notes |
|---|---|---|
| New message appear | 150–200ms ease-out | Simple fade/slight upward motion, no bounce |
| Citation hover | 100ms | Border/underline strengthening only |
| Citation click → navigate to Files | Handled by Files page transition (200–250ms) + code-viewer smooth scroll | Cross-page motion should feel continuous, not a hard cut |
| Chat input focus | 100ms ease-out | Border transition, same as Ingestion inputs |
| Example-question chip hover | 100ms | Border only |

---

## 9. Accessibility Notes Specific to This Page

- Citations must be real interactive elements (links/buttons), not styled `<span>`s — keyboard-reachable with a visible `border-focus` state distinct from hover.
- AI vs. user message distinction must not rely on color/alignment alone for assistive technology — each message should be programmatically labeled with its speaker (e.g. via `aria-label` or equivalent), since a screen reader user won't perceive left/right alignment or pink/neutral tinting.
- The chat input must remain reachable and usable when the message history is long — fixed positioning must not trap focus or break keyboard scroll behavior.
- Example-question chips must be actual buttons/links, keyboard-operable, not click-only `div`s.

---

## 10. What This Page Is Not

- Not a generic chatbot UI — the citation system is not optional polish, it is the defining feature and must be present whenever the AI makes a factual claim about the repository.
- Not a place for the AI response text itself to be tinted violet — violet marks identity (icon/label), never body-text readability.
- Not a place for pink to appear anywhere except the user-message tint — no pink accents, chips, or highlights elsewhere on this page.
- Not an oversized composition box — the input stays compact and command-like, consistent with the "developer investigation workspace" framing rather than a consumer chat product.

---

*This page inherits all color, type, spacing, radius, and motion tokens from `01 — Foundations & Design Tokens`, inherits sidebar/navigation structure from `04 — Dashboard Shell`, and links directly into `06 — Files Page` via its citation system.*

---

# Document Set Complete

This concludes the CodeAtlas Design System:

1. `01 — Foundations & Design Tokens` — source of truth
2. `02 — Home Page`
3. `03 — Ingestion Page`
4. `04 — Dashboard Shell`
5. `05 — Overview Page`
6. `06 — Files Page`
7. `07 — Chat Page`

Every page document inherits its values from Foundations and references the Shell where applicable. No page redefines a color, type, spacing, or radius value independently — any future change to a token must be made once, in `01`, and takes effect everywhere it's referenced.
