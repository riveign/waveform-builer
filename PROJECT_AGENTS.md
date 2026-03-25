# Kiku (聴く — "to listen")

## Mission
Kiku exists to teach DJs why their transitions work — not just find the next track, but build the instinct to know why it's the right one.

## Product Principles — MANDATORY for all agents

Every feature, UI element, error message, and code decision MUST align with these principles. When two principles conflict, the first side of the "even over" wins. Full details with litmus tests and examples: see `BRANDING.md`.

| # | Principle | Even Over | Litmus Test |
|---|-----------|-----------|-------------|
| 1 | **Show the Why** | Teaching even over automating | Does this feature help the DJ understand something, or just produce a result? |
| 2 | **Your Library Is the Lesson** | Your taste even over our algorithms | Does this reference the DJ's actual library, or could it work for any user? |
| 3 | **The Arc Over the Moment** | Journey even over individual transitions | Does this consider the whole set's narrative, or just two adjacent tracks? |
| 4 | **Grow the Ear** | Developing instincts even over removing friction | Does this build a skill the DJ keeps, or create dependency on the tool? |
| 5 | **Opinions You Can See Through** | Transparent scoring even over max flexibility | Can the DJ see exactly why the tool made this suggestion? Could they argue back? |
| 6 | **Every Track Deserves a Chance** | Curation even over popularity | Does this give obscure, unrated, or poorly-tagged tracks a fair shot? |
| 7 | **The Story Comes First** | Serving intent even over showcasing intelligence | Does this serve the DJ's vision, or the tool's need to demonstrate intelligence? |

## Anti-Principles — what Kiku is NOT

1. **Not a DJ autopilot** — never remove the DJ from the creative loop
2. **Not a recommendation engine** — we don't suggest tracks you don't own
3. **Don't replace the DJ's ear** — scores are information, not verdicts
4. **Not a library management tool** — we're the mirror, not the shelf
5. **Don't hide the math** — if we can't explain a suggestion, we shouldn't make it

## Voice & Tone — MANDATORY for all user-facing output

**Character**: The experienced DJ friend who stayed to help you pack up after your first gig. Warm, direct, concise. Wisdom fits in a sentence.

**Word choices** (apply in CLI output, UI copy, error messages, docs):
| Instead of... | Say... |
|---------------|--------|
| playlist | set |
| sequence | flow |
| algorithm | scoring, suggestions |
| optimize | build, plan, craft |
| user | DJ, you |
| content | tracks, music |
| data | your library, your collection |
| loading | listening, reading, exploring |
| error occurred | something went wrong / couldn't do X |
| invalid | doesn't look right / check that... |
| powered by AI | learns from your tags |

**Never use**: smart, powerful, seamless, leverage, magic, synergy, next-level, game-changer

**Surface tone**:
- **CLI**: Warm + informative. Lead with the interesting finding, not the count.
- **Frontend UI**: Clean core, personality at the edges (empty states, tooltips, loading).
- **Errors**: What happened + Why + What to try. Never blame the DJ.
- **Docs/specs**: Richest voice. Use metaphor. Explain philosophy behind decisions.

## Craft Mentorship Tone

All agents embody a **craft mentorship** philosophy:
- Teach through questions, not lectures
- Use the DJ's own library as teaching material
- Explain WHY transitions work, not just that they do
- Frame set building as storytelling, not optimization
- Celebrate growth and effort over perfect execution
- Be concise — wisdom fits in a sentence

### Belt Progression
White (fundamentals) → Yellow (vocabulary) → Green (finding voice) → Brown (artistry) → Black (mastery as beginning). Adapt depth and directness to the DJ's level. Default: Green belt.

## Domain Knowledge

### Scoring System (5 dimensions)
| Dimension | Weight | What it teaches |
|-----------|--------|-----------------|
| Harmonic (Camelot) | 25% | Key relationships — same key (1.0), adjacent (0.85), mode switch (0.8), clash (0.2) |
| Energy fit | 20% | Distance from target energy curve — the set breathes through this |
| BPM compatibility | 20% | ±6% is seamless, double/half time works, beyond 12% = tension |
| Genre coherence | 15% | Same genre (1.0), same family (0.8), compatible families (0.5) |
| Track quality | 20% | Rating, play count, playlist membership — the DJ's curation signal |

### Energy Profile System
Sets are built as energy journeys with named segments. Linear interpolation between boundaries creates natural flow. Default: warmup(0.3) → build(0.6) → peak(0.9) → cooldown(0.4).

### Genre Families
7 families: Techno, House, Groove, Trance, Breaks, Electronic, Other. Cross-family compatibility defines which genre transitions work musically.

## Technical Notes
- Python package at `src/djsetbuilder/`
- CLI: `kiku` (Click-based)
- DB: SQLite at `data/dj_library.db`
- Analysis: Essentia + Librosa (optional extras)
- Music on external drives: `/Volumes/SSD/Musica`, `/Volumes/My Passport/Musica`
- Run commands: `source .venv/bin/activate && kiku <command>`
- Full branding reference: `BRANDING.md`
