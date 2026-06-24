# Related Tracks Card — Guidelines

The Related tracks card (`frontend/src/lib/components/library/SimilarTrackCard.svelte`)
is the densest information surface in Kiku: it answers "what mixes well from
here, and *why*?" in one scannable tile. It renders inside the **Related tracks**
section (`frontend/src/lib/components/waveform/SimilarTracks.svelte`) on the track
view.

This doc covers what is **specific** to this card. For everything shared —
capitalization, overflow, number formatting, color-as-meaning, states,
iconography, motion, terminology, composition — see
[`content-conventions.md`](./content-conventions.md). Those rules apply here
without restatement; this doc only notes where the card *applies* or *narrows*
them.

---

## Anatomy

The card stacks three tiers, separated by dividers, reading top-to-bottom from
*what it is* → *why it fits* → *how good + what to do*.

```mermaid
flowchart TB
    subgraph Card["Related tracks card"]
        direction TB
        subgraph T1["Tier 1 — Identity"]
            direction LR
            ART["Artwork 38×38<br/>(music-note fallback)"]
            TXT["Title (1 line, ellipsis)<br/>Artist · Genre (1 line, ellipsis)"]
            ACT["+ add · ⋮ menu"]
            ART --> TXT --> ACT
        end
        D1["── divider ──"]
        subgraph T2["Tier 2 — Attribute chips (the why)"]
            direction LR
            KEY["Key 8A + harmony move<br/>= ▲ ▼ ⇄ ✕"]
            BPM["BPM 128 + delta +4"]
            EN["Energy zone (Peak)<br/>drops → +1 when narrow"]
        end
        D2["── divider ──"]
        subgraph T3["Tier 3 — Track signals (3-col grid)"]
            direction LR
            SIG["score NN/100 | N★ rating | match strength"]
        end
        T1 --> D1 --> T2 --> D2 --> T3
    end
```

- **Tier 1 — Identity**: artwork → title → **artist · genre** subtitle. Who is this
  track? Plus the per-card actions (`+` add to set, `⋮` `<Menu>`). One line each,
  first-letter-capped, full value on hover. **Genre lives here**, not in the chip row:
  it is descriptive identity metadata, not a transition signal, so it belongs with the
  artist on the subtitle line (artist takes priority and ellipsizes first; genre yields
  space but keeps a readable minimum).
- **Tier 2 — Attribute chips / the "why"**: the harmonic and energetic reasons it
  fits, as `<Chip>`s in priority order key → BPM → energy — Camelot key +
  harmony-move icon, BPM + signed delta, energy zone. This tier is the card's
  reason to exist; it's "Show the Why" made visible. See [Chips](#chips).
- **Tier 3 — Track signals**: the quality verdict (match score), the DJ's own
  rating (compact `N★`), and affinity-as-strength — see
  **[Track signals block](#track-signals-block)**.

---

## Title, artist & genre

- **Title** is one line, ellipsis on overflow, **no wrap**. (This replaced the old
  2-line `-webkit-line-clamp: 2`.)
- **Artist and genre share one muted subtitle line** as `artist · genre`. Genre was
  moved out of the chip row into the identity tier because it is descriptive metadata,
  not a transition signal — it belongs with *who the track is*, beside the artist.
  Artist takes priority and ellipsizes first; genre yields space (`flex-shrink: 2`) but
  keeps a readable minimum so the line never wraps. When genre is missing, only the
  artist shows (no dangling `·`).
- Full value exposed on hover/focus via `title` on each span (per
  [content-conventions §2](./content-conventions.md#2-overflow--wrapping)).
- Title, artist, and genre are **first-letter-capped** via the shared `capFirst()` helper —
  the first visible character is forced to a capital, the rest of the string is left
  intact (so `deadmau5` → `Deadmau5` but `MEDUZA` stays `MEDUZA`). This is a USER
  DECISION (spec 023) that overrides the previous "preserve source casing" default;
  the underlying library value is never mutated and the full original is still on
  hover (per [content-conventions §1](./content-conventions.md#1-capitalization)).

---

## Chips

Tier 2 renders a row of chips in a fixed **priority order**:

1. **Key** (Camelot + harmony move) — the harmonic relationship is the strongest
   "why." Transition-critical; always shown.
2. **BPM** (+ signed delta) — tempo compatibility. Transition-critical; always shown.
3. **Energy** (zone) — where it sits in the journey. Lowest priority; **drops first**
   when the card is narrow.

Genre is **no longer a chip** — it moved to the identity tier (see
[Title, artist & genre](#title-artist--genre)).

All three are the shared `<Chip>` primitive (`variant="key|bpm|energy"`) —
no bespoke pills. The key chip carries a `<HarmonyIcon>` glyph for the move.

**Responsive, whole-chip priority hiding**
- The card is a **size container** (`container-type: inline-size`, `container-name:
  relcard`), so the chip row adapts to the card's **real laid-out width** — whatever
  grid density it lands in (4-up ≈250px, 6-up ≈210px, the expanded "Show more" grid).
- Chips **never shrink** (`flex-shrink: 0`), so a chip is **never clipped mid-word** at
  any width. Instead, whole chips are hidden by priority.
- A `@container relcard (max-width: 232px)` query hides the **whole energy chip** when
  the card is narrow (≈6-up and tighter) and surfaces a muted **`+1`** in its place
  (full value on hover). **Key (+ harmony glyph) and BPM stay visible down to the
  narrowest density.** The same query trims the chip-row and signal-row gaps so the
  remaining chips keep breathing room.
- The chip row is still **no-wrap** with `overflow: hidden` as a **final safety net
  only** — the container query is what actually prevents clipping; nothing reaches the
  safety net under normal densities.
- Chip colors come from **semantic tokens by meaning** (the `--zone-*` set for
  energy, `--score-*` for the harmony band, `--bpm-delta-*` via the chip's `tone`
  for the ±6% tension rule) — never hardcoded pastel hex.
- Each color-coded chip pairs color with text/glyph (zone name, harmony glyph,
  signed delta), per §4.

---

## Track signals block

> **STATUS: LOCKED — built in `SimilarTrackCard.svelte` (spec 023, step 5).**

Tier 3 groups the three "how good is this?" signals into **one readable unit**
named **"Track signals."** Previously the match score and stars sat in Tier 3
while the affinity signal lived as a separate dot up in Tier 1; they are now one
left-to-right cluster so the DJ reads the full verdict — *our score, your rating,
your call* — in a single glance.

**What it consolidates**
- **Match score** — `NN/100`, the tool's compatibility verdict.
- **Rating** — the DJ's own rating as a compact `N★` (`StarRating display="compact"`).
- **Affinity strength** — a labelled qualitative strength, NOT a raw number.

**Layout** (token-based, no literals) — a **3-column CSS grid**,
`display: grid; grid-template-columns: auto auto minmax(0, 1fr); align-items:
center; gap: var(--space-md)`, with the same `--space-sm var(--space-md)` padding as
the other tiers. The three explicit columns mean cards in a row read as **aligned
columns**, left → right:

1. **Score `NN/100` (column 1 — lead anchor, heaviest)** — `auto` width. `NN` at
   `--text-lg`, `--font-weight-semibold`, `--text-1`; suffix `/100` at `--text-xs`,
   `--text-3`. It is the headline verdict, so it carries the most weight.
2. **Rating (column 2)** — `auto` width. `<StarRating display="compact" size="sm" />`
   → `N★` when `rating > 0` (the DJ's curation signal beside the tool's verdict); when
   unrated, the canonical muted `—` (content-conventions §3), never a blank gap.
3. **Match strength (column 3 — `minmax(0, 1fr)`, takes the remaining space)** — a
   small 3-segment **strength bar + word**, mapping the match score onto a qualitative
   band so the row never shows a second raw number competing with `NN/100` (§3) and
   never relies on color alone (§4). When the DJ has set an explicit opinion the word
   becomes that opinion ("Great together" / "Not for me"); otherwise it reads the
   strength label. The full opinion + strength is in the `title` tooltip.

**Responsiveness**: because column 3 is `minmax(0, 1fr)` and the affinity bar is
`flex-shrink: 0`, at narrow card widths (≈210px / 6-up) the **word ellipsizes** while
the bar stays intact — the three columns never overlap and never force the row wider
than the card. The narrow `@container` query also trims the inter-column gap.

**Affinity-strength thresholds** (`scoreStrength()` in `SimilarTrackCard.svelte`),
derived from the match score (0–1):

| Score | Label | Bars | Color token |
|-------|-------|------|-------------|
| ≥ 0.80 | **Strong match** | ███ (3) | `--score-excellent` |
| ≥ 0.55 | **Likely match** | ██ (2) | `--score-good` |
| < 0.55 | **Weak match** | █ (1) | `--score-poor` |

**Degradation**
- No score → `—` in the score slot (never blank).
- No rating → muted `—` in the rating slot.
- Explicit affinity set → the word shows the opinion; the bar still reflects score.
- Space-constrained → keep score (the headline); the match **word ellipsizes** in its
  `1fr` column while the bar stays intact. Score and rating columns hold their content.

**Why**: grouping the tool's score next to the DJ's own rating and a plain-language
strength read reinforces "Opinions You Can See Through" — the DJ sees *why* and can
argue back, without two numerics fighting for the same glance.

---

## States

Per [content-conventions §5](./content-conventions.md#5-states). Card-specific
behavior:

| State | Behavior |
|-------|----------|
| **Default** | Resting card; `--surface-2`, `--border-subtle`. |
| **Hover** | `border-color: var(--border-strong)`; transition via `--dur-fast`. |
| **Focus-visible** | Keyboard ring from the global `--focus-ring` rule (card is `role="button"`, `tabindex="0"`). |
| **Selected** | `border: var(--space-2xs) solid var(--accent)`. NOTE: `isSelected` is declared but never set true — wire it or drop the rule (see Open items). |
| **No-artwork fallback** | Inline music-note SVG in `--text-4` on `--surface-1`. |
| **Affinity set/unset** | Set → the Tier-3 strength word reads the opinion ("Great together" / "Not for me") with the full opinion + strength in `title`; unset → the strength word reads the score band ("Strong / Likely / Weak match"). |
| **Loading** | Owned by the wrapper: `<Spinner label="Finding what mixes..." />`. |
| **Empty** | Owned by the wrapper: muted "Nothing in your library mixes cleanly from here yet". |

**Keyboard reachability**: the `+` and `⋮` actions live in Tier 1 and must remain
Tab-reachable and show on focus (content-conventions §5) — they are not
hover-only.

---

## Tokens used

The card consumes the semantic layer (`frontend/src/lib/styles/tokens.semantic.css`)
exclusively. No px/hex literals.

| Category | Tokens |
|----------|--------|
| Surfaces | `--surface-1`, `--surface-2`, `--surface-3`, `--surface-hover` |
| Text | `--text-1`, `--text-2`, `--text-3`, `--text-4` |
| Borders | `--border-subtle`, `--border-strong` |
| Accent / status | `--accent` (selected/primary action), `--destructive` (bad affinity), zone/status ramp for energy chips |
| Spacing | `--space-2xs`, `--space-xs`, `--space-sm`, `--space-md`, `--space-lg`, `--space-xl` |
| Type | `--text-2xs` … `--text-lg`, `--lh-*`, `--font-weight-medium/semibold` |
| Radius | `--radius-md` (artwork), `--radius-sm` (buttons), `--radius-full` (chips/dots), `--radius-xl` (card) |
| Motion | `--dur-fast`, `--ease-standard` |
| Elevation | `--elev-3` (add-to-set popover) |

**Outstanding debt**: the hardcoded `PHASE_PILL_COLORS` / delta-badge pastel hex
are **gone** — chips now derive color from the `--zone-*`, `--score-*`, and
`--bpm-delta-*` token sets via `<Chip>`. The remaining non-token literals are the
artwork's `38px`, the popover's `220px min-width`, and the chip-priority container
query breakpoint (`232px` — a layout threshold, intentionally a raw value since it
encodes a measured fit-width rather than a design-token step).

---

## Open items

Resolved (spec 023, step 5):

1. ~~**Title casing**~~ — **RESOLVED**: titles/artists are now **first-letter-capped**
   (`capFirst()`), overriding preserve-source. `deadmau5` → `Deadmau5`.
2. ~~**"Track signals" block**~~ — **RESOLVED**: built as the locked
   [Track signals block](#track-signals-block); the Tier-1 affinity dot was removed
   and affinity moved to Tier 3 as a labelled strength.
4. ~~**Chip drop order**~~ — **RESOLVED**: genre moved to the identity tier; the chip
   row is now key → BPM → energy. A `@container` query on the card hides the **whole**
   energy chip (never clipped mid-word) at narrow densities and surfaces a `+1`, while
   key + BPM always show. Responsive across 4-up (~250px), 6-up (~210px), and the
   expanded grid — demonstrated at two widths in the `/design-system` showcase.
5. ~~**Zone/status color tokens**~~ — **RESOLVED**: chips consume `--zone-*`,
   `--score-*`, and `--bpm-delta-*` tokens; no hardcoded hex remains on this card.

Still open (needs user confirmation):

3. **Selected state**: `isSelected` is dead (never set true). Wire it to a real
   selection concept or remove the `.selected` rule.
