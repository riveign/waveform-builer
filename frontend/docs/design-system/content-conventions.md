# Content & Interaction Conventions

System-wide rules for how Kiku's UI reads and behaves. Every component — chips,
cards, menus, tables, empty states — follows these. When a card or feature spec
needs to say "handle text like everyone else does," it links here instead of
restating the rule.

These conventions exist to keep the interface calm and legible while the DJ is
mid-flow. The voice and tone rules in `BRANDING.md` govern *what* words we use;
this doc governs *how* those words and values are presented and interacted with.

---

## 1. Capitalization

Use **sentence case** everywhere. Capitalize the first letter of a piece of UI
text and nothing else, unless a proper noun demands it.

**Rationale**: Sentence case reads faster and feels like a person talking, not a
system shouting. ALL-CAPS adds visual weight without meaning and hurts
scannability in dense card grids.

| Case | When | Example |
|------|------|---------|
| First-letter-capitalized | Single-word labels | `Peak`, `Techno`, `Warmup` |
| Sentence case | Multi-word labels, sentences | `Mix in key`, `Add to set`, `Related tracks` |
| First-letter-capitalized | Track titles, artist names | `Midnight drive`, `LOUDER`→`LOUDER` (already capped), `deadmau5`→`Deadmau5` |

**Do**
- `Peak` (energy zone chip)
- `Mix in key` (action label)
- Genre chip `Tech house` even if the source tag was `TECH HOUSE` — normalize to sentence case.

**Don't**
- `PEAK`, `MIX IN KEY` (no ALL-CAPS)
- `mix in key` (capitalize the first letter)

**Track titles & artist names — first-letter-capped (USER DECISION, spec 023)**:
titles and artist names render with their **first letter forced to a capital**,
overriding the previous "preserve source casing" default. This only changes the
**first visible character**; the rest of the string is left byte-for-byte intact,
so stylized casing past the first glyph is preserved (`deadmau5` → `Deadmau5`,
but `MEDUZA` and `LOUDER` stay as they are). The underlying library value is never
mutated — it's a presentational cap only, and the full original is always exposed
on hover via `title` (§2). Implemented by the shared `capFirst()` helper in
`SimilarTrackCard.svelte`.

---

## 2. Overflow & Wrapping

Title, artist, and chip labels are **single line + ellipsis**. They never wrap.
Short numerics (BPM, score, key) **never truncate** — they always fit.

**Rationale**: Wrapping text changes a card's height and breaks the equal-height
grid; one tall card drags the whole row out of rhythm. A single line keeps the
grid stable and scannable. But a truncated value the DJ can't read is useless —
so truncation must always be recoverable.

**The rule**: anything that can be truncated MUST expose its full value on
hover/focus. Today that means a native `title` attribute on the element; a
tooltip primitive will replace it later without changing this rule.

**Do**
- Title clamps to one line with `…`; the element carries `title="<full title>"`.
- Artist ellipsis on overflow, full value in `title`.
- `128`, `8A`, `92` render in full, always.

**Don't**
- Wrap a long title to two lines.
- Truncate a BPM or score to fit.
- Truncate anything without a hover/focus fallback for the full value.

---

## 3. Number & Data Formatting

One canonical format per value type. Never vary the form within the app.

| Value | Format | Example | Notes |
|-------|--------|---------|-------|
| BPM | Integer, no decimals | `128` | Never `128.0`. |
| BPM delta | Always signed, direction-colored | `+4`, `−6` | `+`/`−` prefix always present; color by direction (see below). |
| Key | Camelot notation | `8A`, `12B` | Use `formatKey()`; never raw `Am`/`F#`. |
| Score | `NN / 100`, one chosen form | `87 / 100` | Pick one form app-wide and never alternate (no `87%` in one place, `0.87` in another). |
| Missing data | One canonical "absent" treatment | `—` (muted em dash) | Never blank, never `null`, never `0` standing in for "unknown". |

**BPM delta coloring** signals tension, not just magnitude:
- Within ±6% of the source BPM → neutral / good (seamless range).
- Beyond ±6% → warning tone (the transition is getting harder).

**Rationale**: A DJ scans these values dozens of times per set. Consistent
formatting means the eye learns the shape once. Signed, colored deltas turn a
raw number into a *judgment the DJ can read at a glance* — which is the whole
point of "Show the Why."

**Do**
- `128` · `+4` (green) · `8A` · `87 / 100` · `—` for an untagged genre.

**Don't**
- `128.0`, `4` (unsigned delta), `Am`, `87%` next to `0.91 / 100`, an empty cell where a value is missing.

---

## 4. Color as Meaning + Accessibility

**Color is never the only signal.** Any meaning carried by color (energy,
harmony, affinity, score) must also be carried by an icon, a label, or text.

**Rationale**: ~8% of men have some color-vision deficiency, and DJ booths are
dark with colored lighting bleeding onto screens. Color-only meaning fails both.
Pairing color with a glyph or word also makes the UI self-documenting — it states
*what it means*, which is "Opinions You Can See Through."

**Rules**
- Pair every color-coded signal with a non-color cue: affinity dot → also a
  tooltip/label; harmony color → also the move glyph (`= ▲ ▼ ⇄ ✕`); energy color
  → also the zone name.
- Chips derive color from **semantic tokens by meaning**, never hardcoded hex.
  A genre chip uses surface/text tokens; a status chip uses the energy/status
  ramp by what it *means*, not a literal `#854F0B`.
- Reserve the **cerceta primary** (`--accent`) for **primary actions only**.
- Reserve **coral** (`--destructive`) for **destructive actions only**.
- The accent is **never decoration** — no accent borders, dividers, or
  background flourishes "to add color."

**Do**
- Affinity = colored dot **plus** `title="Marked: great together"`.
- Energy zone = colored chip **plus** the word `Peak`.

**Don't**
- A red dot with no label (is it bad affinity? an error? a recording light?).
- `style="background:#FAEEDA;color:#854F0B"` on a chip — use a token by meaning.
- Accent-colored text used just to "brighten" a non-interactive label.

---

## 5. States

Every interactive component defines all of these, even if some collapse visually:

| State | Requirement |
|-------|-------------|
| Default | Resting appearance. |
| Hover | Pointer feedback (border/surface shift). |
| Focus-visible | Keyboard ring via `--focus-ring` tokens (global rule already provides it; don't suppress it). |
| Active / selected | Pressed or currently-chosen appearance. |
| Disabled | Visibly inert + not focusable/operable. |
| Loading | A listening/reading state, not a frozen UI. |
| Empty | A warm, non-blaming message (see Voice in `BRANDING.md`). |

**Rationale**: Missing states are where interfaces feel broken — a button with no
focus ring is invisible to keyboard users; a card with no empty state shows a
confusing blank. Defining them up front is cheaper than retrofitting.

**Two hard rules**
- **Hover-revealed actions MUST also appear on keyboard focus.** Anything that
  only shows on `:hover` is invisible and unreachable to keyboard/AT users. Show
  it on `:focus-within` too.
- **Minimum interactive target ≈ 32–36px.** Icon buttons (`+`, `⋮`) get enough
  padding to meet this even when the glyph is small. The Button primitive's
  `--btn-height: 36px` is the reference.

**Do**
- The `⋮` menu button is reachable by Tab and shows a focus ring.
- Disabled "Add to set" is greyed and removed from the tab order.

**Don't**
- Reveal the `+` button only on card hover.
- A 16px tap target floating in a card.

---

## 6. Iconography

- **One size scale, one stroke weight.** Icons share a consistent size step and
  visual weight; no mixing 12px and 20px glyphs in the same row.
- **Icon-only controls require `aria-label` + a tooltip.** `+`, `⋮`, transport
  controls — each needs an accessible name and a hover hint of what it does.
- **Meaning-bearing icons carry consistent meaning everywhere + a hover
  explanation.** The harmony-move glyphs (`= ▲ ▼ ⇄ ✕`) mean the same thing on
  every card, and each exposes its label on hover ("energy up from this track").

**Rationale**: Inconsistent icon sizing reads as visual noise; an icon-only
button with no label is a guessing game for everyone and a dead end for screen
readers. Consistent meaning is what lets the DJ *learn* the vocabulary — "Grow
the Ear."

**Do**
- `<button aria-label="Add to set" title="Add to set">+</button>`
- `⇄` always means "mood switch (relative major/minor)", with that on hover.

**Don't**
- An icon-only button with neither label nor tooltip.
- The same glyph meaning two different things in two views.

---

## 7. Motion

- State transitions use the **transition tokens** (`--dur-fast` / `--dur-base` /
  `--dur-slow` + `--ease-*`). No literal `0.15s` in component CSS.
- **Respect `prefers-reduced-motion`.** The token layer already collapses
  durations under reduced motion — don't reintroduce hardcoded durations that
  bypass it.
- Hover transitions are **fast** (≤ ~150ms; `--dur-fast` is 120ms).
- **No gratuitous animation.** Motion communicates a state change; it is not
  decoration.

**Rationale**: A DJ working mid-set is sensitive to distraction. Snappy,
purposeful motion confirms an action; slow or decorative motion gets in the way
and can trigger discomfort for motion-sensitive users.

**Do**
- `transition: border-color var(--dur-fast) var(--ease-standard);`

**Don't**
- `transition: all 0.4s;` on a hover.
- A looping pulse/bounce with no informational purpose.

---

## 8. Naming & Terminology

**One term per concept, across the entire UI.** We standardized the related-tracks
surface on **"Related tracks"** (previously "Mix next" / "Sounds like"). Pick one
word for a concept and use it everywhere — labels, tooltips, empty states, docs.

**Rationale**: Synonyms make the DJ wonder if two things are different when they
aren't. One consistent term builds the shared vocabulary the product is trying to
teach (see the word-choice table in `BRANDING.md`).

### Starter glossary

| Term | Meaning |
|------|---------|
| **Set** | A built sequence of tracks (never "playlist"). |
| **Flow** | The ordering/sequencing of a set (never "sequence"). |
| **Track** | A single piece of music (never "song" or "content"). |
| **Related tracks** | The suggestions for what mixes well from the current track. |
| **Energy zone** | A named segment of the energy journey: intro, warmup, build, drive, peak, close. |
| **Camelot key** | Harmonic key in Camelot notation (`8A`, `12B`). |

**Grow the glossary**: when a new concept needs a name, add the chosen term here
*before* shipping it in the UI, so it's used consistently from day one.

---

## 9. Composition Governance

New UI is built from **primitives + tokens** — `Stack`, `Grid`, `Chip`,
`Button` — consuming the semantic token layer (`tokens.semantic.css`). No bespoke
one-off chips, buttons, or spacing literals.

**Rationale**: One-off components drift. Three different "chips" with three
slightly different paddings is how a design system rots. Building from primitives
means a single change to a token or primitive updates every surface at once.

**Do**
- Need a labelled value? Use `<Chip>`. Need spacing? Use `Stack`/`Grid` gaps or
  `--space-*` tokens.
- Add a variant to an existing primitive rather than forking it.

**Don't**
- Hand-roll `.my-special-pill { padding: 5px 9px; border-radius: 7px; }`.
- Hardcode `margin: 13px` instead of a `--space-*` step.

---

## See also

- `BRANDING.md` — voice, tone, word choices, the 7 "Even Over" principles.
- `frontend/src/lib/styles/tokens.semantic.css` — the semantic token vocabulary.
- `frontend/docs/design-system/related-tracks-card.md` — a worked example that
  applies every rule above to one card.
