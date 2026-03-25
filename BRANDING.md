# Kiku (聴く) — Branding Principles

## Table of Contents
- Mission Statement
- Product Principles
  - 1. Show the Why
  - 2. Your Library Is the Lesson
  - 3. The Arc Over the Moment
  - 4. Grow the Ear
  - 5. Opinions You Can See Through
  - 6. Every Track Deserves a Chance
  - 7. The Story Comes First
- Voice & Tone Guide
  - Character
  - Tone Spectrum
  - Word Choices
  - Surface-Specific Guidance
  - Before & After Examples
- Anti-Principles

## Executive Summary

- **Deliverable**: Complete branding principles document with mission, 7 "Even Over" product principles, comprehensive voice & tone guide, and 5 anti-principles
- **Format**: "Even Over" statements with litmus tests and concrete product examples, per user workshop decision
- **Principles evolved from**: 5 existing philosophical values (respect for music, dancefloor service, patience, balance, deep listening) + 2 new principles (teaching over automation, journey over destination)
- **Voice character**: "The experienced DJ friend who stayed to help you pack up" -- warm, direct, musical, never corporate
- **Surface guidance**: CLI (warm + informative), Frontend UI (clean with personality at edges), Errors (educational), Docs (richest voice)

### Next Steps
- **Recommended action**: Integrate this document as the canonical brand reference; begin UX copy audit using the voice guide's before/after patterns
- **Dependencies**: Audit report at `/home/mantis/Development/mantis-dev/waveform-builer/tmp/mux/20260314-2230-branding-principles/audit/001-existing-principles.md`, research at `/home/mantis/Development/mantis-dev/waveform-builer/tmp/mux/20260314-2230-branding-principles/research/001-branding-frameworks.md`
- **Routing hint**: This document is ready for user review; a follow-up implementation agent should use the voice guide to rewrite frontend UX copy and CLI messages

---

## Mission Statement

**Kiku exists to teach DJs why their transitions work -- not just find the next track, but build the instinct to know why it's the right one.**

Every DJ tool on the market will help you mix. We're the one that helps you understand. The scoring, the energy arcs, the harmonic relationships -- they're not automation. They're a mirror held up to your own taste, reflecting back what your ear already knows and naming the things it doesn't yet.

---

## Product Principles

Seven principles that guide every product decision. Each is framed as a real tradeoff between two good things. When they conflict, the first side wins.

---

### 1. Show the Why
**We value explaining why a transition works even over finding the perfect transition automatically.**

A tool that hands you the answer teaches you nothing. A tool that shows you why two tracks belong together -- the key relationship, the energy fit, the BPM math -- gives you something you carry to the next set, and the one after that. Every score breakdown, every transition detail, every suggestion should leave the DJ knowing more than they did before.

**Litmus test**: Does this feature help the user understand something, or just produce a result?

**In the product**: The 5-dimension score breakdown on every transition doesn't just say "good" or "bad." It shows exactly how much harmonic compatibility, energy fit, BPM closeness, genre coherence, and track quality contributed. The DJ sees the recipe, not just the dish.

**In the product**: When the energy autotagger runs, it shows "What drives predictions" with visual feature importance bars. The DJ learns what the algorithm sees in their tracks -- spectral centroid, RMS energy, onset rate -- and starts hearing those features themselves.

---

### 2. Your Library Is the Lesson
**We value using the DJ's own tracks as teaching material even over generic examples or external recommendations.**

Your library is 3,000 tracks of accumulated taste. Every rating, every play count, every genre tag is a decision you made. We don't teach with textbook examples -- we teach with your music. When we show you a gap in your Camelot coverage, it's your gap. When we surface a hidden gem, it's a track you already own and already loved enough to import. The curriculum is personal because the craft is personal.

**Litmus test**: Does this feature reference the user's actual library, or could it work identically for any user?

**In the product**: The Taste DNA visualization is your library's musical fingerprint -- not a generic profile. It shows your genre distribution, your energy tendencies, your harmonic coverage. The gaps it reveals are specific to your collection.

**In the product**: The autotagger trains on your energy tags, learning what you mean by "peak" or "deep." It doesn't impose a universal definition of energy. Your tags are the ground truth.

---

### 3. The Arc Over the Moment
**We value the energy journey of a complete set even over the perfection of any single transition.**

A DJ set is a story. It has a beginning that earns trust, a middle that builds tension, a peak that pays it off, and an ending that lets the room breathe. The best individual transition in the world means nothing if it breaks the arc. We score tracks against where they sit in the story, not in isolation. A 6/10 transition in the right place beats a 10/10 transition that derails the energy.

**Litmus test**: Does this feature consider the whole set's narrative, or just the relationship between two adjacent tracks?

**In the product**: Energy profiles define the arc before track selection begins. "Journey" (0.3 to 0.6 to 0.9 to 0.4) is the default because the classic narrative arc is the most universal story. The warmup matters as much as the peak -- a mountain is only tall because of the valley beside it.

**In the product**: Energy fit scoring (20% weight) evaluates each track against its target position on the curve, not against the previous track alone. The algorithm serves the arc.

---

### 4. Grow the Ear
**We value developing DJ instincts even over removing friction from the workflow.**

The fastest path isn't always the best teacher. We could auto-generate entire sets with one click. We don't, because the act of selecting tracks, evaluating transitions, and adjusting energy is where learning happens. Every manual choice is a rep. Every override of a suggestion is a moment where your ear disagrees with the math -- and sometimes your ear is right. We build tools that sharpen judgment, not replace it.

**Litmus test**: Does this feature build a skill the DJ keeps, or does it create a dependency on the tool?

**In the product**: The Energy Tinder review flow asks the DJ to confirm or correct the model's energy predictions. When the DJ overrides a prediction, the tool shows which audio features confused the model. That's the Miyagi moment: the DJ teaches the machine, and the machine teaches the DJ back.

**In the product**: The beam search builds sets but always shows its work -- the scores, the alternatives considered, the tradeoffs made. The DJ sees the decision space, not just the decision.

---

### 5. Opinions You Can See Through
**We value strong defaults with visible reasoning even over maximum flexibility or total user control.**

We have opinions about what makes a good transition. Harmonic compatibility gets 25% of the score because key relationships are foundational. Genre coherence gets 15% because good mixing transcends genre boundaries. These aren't arbitrary -- they encode decades of DJ craft. But we never hide our reasoning. Every weight is visible. Every score is decomposed. If you disagree with our opinions, you can see exactly where and why. Opinionated and transparent are not opposites.

**Litmus test**: Can the user see exactly why the tool made this suggestion? Could they argue back?

**In the product**: The scoring weights (harmonic 25%, energy 20%, BPM 20%, quality 20%, genre 15%) are documented and visible. They represent a philosophy: harmonic integrity is the north star, genre is the most flexible dimension. A DJ who disagrees with this ranking at least knows what they're disagreeing with.

**In the product**: Energy presets have names from DJ culture -- "warmup," "peak-time," "journey," "afterhours" -- not technical labels. Each tells you what the tool thinks that kind of set sounds like, and you can see the exact energy values behind the name.

---

### 6. Every Track Deserves a Chance
**We value treating every track as worthy of consideration even over optimizing for popular or highly-rated tracks.**

Your library has no filler. Every track you imported was a choice. The deep cut with two plays and no rating might be the perfect 3AM afterhours closer. We don't bury tracks for lacking metadata or penalize them for being obscure. When we don't know a track's key or energy, we give it a neutral score -- 0.5, not 0.0 -- because absence of information is not absence of value. Hidden gems are called hidden for a reason.

**Litmus test**: Does this feature give obscure, unrated, or poorly-tagged tracks a fair shot?

**In the product**: Unknown values across all five scoring dimensions default to 0.5 (neutral) rather than 0.0 (penalty). A track with no Camelot key still gets considered. The system assumes potential, not worthlessness.

**In the product**: The "Hidden Gems" feature specifically surfaces tracks that are highly rated but rarely played -- the library's overlooked treasures. Artist cooldown (5-track minimum between same-artist repeats) ensures variety over familiarity.

---

### 7. The Story Comes First
**We value serving the DJ's creative intent even over showcasing the tool's capabilities.**

The DJ is the storyteller. We're the notebook they plan in. Every feature should amplify what the DJ wants to say to the room, not impose what the algorithm thinks is "optimal." When the product says "optimized" it should mean "aligned with your intent," not "mathematically superior." The dancefloor doesn't care about F1 scores. It cares whether the DJ took them on a journey.

**Litmus test**: Does this feature serve the DJ's vision for their set, or does it serve the tool's need to demonstrate intelligence?

**In the product**: Custom energy profiles let DJs define their own arc. The presets are starting points, not prescriptions. A DJ who wants to sustain a hypnotic afterhours groove at 0.3 energy for twenty minutes can do that -- the tool follows their intent.

**In the product**: The transition detail view shows score breakdowns as context for the DJ's decisions, not as verdicts. A low-scoring transition isn't "wrong" -- it's information. The DJ might keep it because they know something the algorithm doesn't.

---

## Voice & Tone Guide

### Character

If Kiku were a person, it would be **the experienced DJ friend who stayed to help you pack up after your first gig.**

They've been mixing for fifteen years. They've played warehouses and weddings, sunrise sets and opening slots. They don't lecture. When you ask why that last transition felt rough, they cue up both tracks and say, "Listen to the kick patterns -- hear how they fight? Now try this one." They teach by doing. They use your records, not theirs.

They're warm but direct. They'll tell you a transition doesn't work, but they'll show you why and suggest what would. They never make you feel stupid for not knowing something. They remember what it was like to not know.

They're concise. Wisdom fits in a sentence.

### Tone Spectrum

The product's tone is not a single note -- it moves between warmth and precision depending on context:

**Warm & Encouraging** (teaching moments, empty states, onboarding, celebrations)
- When the DJ discovers something new about their library
- When a set comes together well
- When explaining a concept for the first time
- When things go wrong and the DJ needs guidance

**Direct & Informative** (data display, scoring, controls, status)
- When showing transition scores
- When displaying library statistics
- When reporting progress on operations
- When presenting search results

**Precise & Technical** (documentation, advanced features, developer-facing)
- When explaining scoring algorithms in depth
- When documenting API endpoints
- When the DJ is at Brown or Black belt and wants the raw details

The default voice sits right between warm and direct -- informed warmth. Think "knowledgeable friend," not "customer service rep" and not "professor."

### Word Choices

Words we reach for:

| Instead of... | We say... | Why |
|---------------|-----------|-----|
| playlist | set | A set has intention and arc; a playlist is just a list |
| sequence | flow | Flow implies movement and continuity |
| segue | transition | Industry-standard and precise |
| algorithm | scoring, suggestions | The DJ doesn't need to think about algorithms |
| optimize / optimized | build, plan, craft | Building is intentional; optimizing is mechanical |
| output | suggestion, result | The tool suggests; the DJ decides |
| user | DJ, you | They're a DJ first, a user of software second |
| content | tracks, music | Content is for platforms; music is for people |
| data | your library, your collection | Personal, not clinical |
| error occurred | something went wrong / couldn't do X | Human, not robotic |
| invalid | doesn't look right / check that... | Guide, don't judge |
| loading | listening, reading, exploring | Context-specific activity |
| empty / null | not yet, waiting for | Implies future possibility |
| feature | tool, ability | Features are for marketing; tools are for craft |
| powered by AI / ML | learns from your tags | Describe the effect, not the technology |

Words we avoid entirely:

| Word | Why |
|------|-----|
| smart / intelligent | Anthropomorphizes the tool; the DJ is smart, the tool is a mirror |
| powerful | Empty marketing adjective |
| seamless | Overused, means nothing |
| leverage | Corporate jargon |
| curate (as verb for the tool) | The DJ curates; the tool assists |
| magic / automagic | Obscures how things work -- the opposite of our teaching philosophy |
| synergy | No |
| next-level | No |
| game-changer | No |

### Surface-Specific Guidance

#### CLI: Warm, Informative, Moderate Personality

The CLI is a conversation between the tool and the DJ in a terminal. It should feel like a knowledgeable assistant, not a database query interface.

- **Status messages**: Active voice, present tense. "Reading your library..." not "Loading database."
- **Results**: Lead with the interesting finding, not the count. "3 hidden gems in your Techno collection" not "Found 3 tracks matching criteria."
- **Errors**: Say what happened, what it means, and what to try. "Couldn't find any tracks in 8A -- try broadening to include adjacent keys (7A, 9A, 8B)?" not "No tracks found matching your filters."
- **Personality lives in**: section headers, summary lines, empty-state messages, completion messages.
- **Personality stays out of**: raw data output, piped/scripted output, flag names.

#### Frontend UI: Clean Core, Personality at the Edges

The web UI should be crisp and professional in its data-heavy areas (library table, timeline canvas, score numbers) but warm and inviting at the edges (empty states, tooltips, onboarding, transitions between views).

**Where personality shows:**
- Empty states ("An empty set -- your story starts here")
- Tooltips and hover explanations ("Adjacent keys on the Camelot wheel -- this transition will feel natural")
- Onboarding and first-run experience
- Tab labels and section headers ("Taste DNA," not "Library Statistics")
- Loading states ("Listening to your library..." not "Loading...")
- Success/celebration moments

**Where to stay clean:**
- Data tables (track name, BPM, key -- just the facts)
- Score numbers and breakdowns (precision matters here)
- Transport controls (play, pause, seek -- universal and unlabeled)
- Form inputs and filters
- Menu items and navigation labels (clear trumps clever)

#### Error Messages: Helpful and Educational

Errors are teaching moments. The DJ hit a wall -- help them understand it and get past it.

**Structure**: What happened + Why + What to try.

```
What happened:  Couldn't build a set with these constraints.
Why:            Only 4 tracks match both the key range (8A-10A)
                and the energy profile you selected.
What to try:    Broaden the key range, or switch to the
                "journey" energy profile which uses a wider
                energy band.
```

Never blame the DJ. Never say "invalid input." Never show a stack trace in a user-facing surface. If metadata is missing, frame it as an opportunity: "This track doesn't have a key tag yet -- analyzing it would unlock harmonic scoring."

#### Documentation and Specs: Richest Voice

Docs are where the product's soul lives at full volume. This is teaching mode.

- Use metaphor freely ("the set breathes through energy fit")
- Explain the philosophy behind decisions ("Genre coherence gets the lowest weight because we believe good mixing transcends genre boundaries")
- Speak in the mentor's voice: direct, opinionated, warm
- Use the DJ's world as the reference frame, not the developer's

### Before & After Examples

**1. Empty set state**

Before:
> No tracks in this set.

After:
> An empty set -- your story starts here. Add tracks from the library to begin building.

---

**2. Loading the library**

Before:
> Loading...

After:
> Reading your library...

---

**3. No search results**

Before:
> No tracks found.

After:
> Nothing matched those filters. Try loosening the BPM range or removing a genre filter?

---

**4. Transition tooltip**

Before:
> Harmonic score: 0.85

After:
> Adjacent key (8A to 9A) -- this transition will feel natural and seamless. Harmonic score: 0.85

---

**5. CLI set generation complete**

Before:
> Set generated. 15 tracks, total score: 0.82.

After:
> Built a 15-track journey. Overall flow score: 0.82. Strongest transitions at positions 4-5 (harmonic lock in 7B) and 11-12 (perfect energy lift into the peak).

---

**6. Error: missing audio files**

Before:
> Error: File not found for 3 tracks.

After:
> 3 tracks are missing their audio files -- they might have moved since the last Rekordbox export. The set will still build, but waveform previews won't be available for those tracks.

---

**7. Autotagger results**

Before:
> Model accuracy: 0.84. Classified 1,847 tracks.

After:
> Your energy language is getting clearer. The model now understands 1,847 of your tracks with 84% confidence. Biggest improvement: it's better at telling "deep" apart from "chill."

---

## Anti-Principles

Five things Kiku is explicitly not. These prevent scope creep and protect the product's identity.

### 1. We are not a DJ autopilot.
We will never generate a complete set and tell the DJ to press play. The tool plans, suggests, and teaches. The DJ decides. Full automation is the opposite of our mission -- it builds dependency, not skill. If a feature removes the DJ from the creative loop entirely, it doesn't belong here.

### 2. We are not Spotify's recommendation engine.
We don't suggest tracks you don't own. We don't chase trends. We don't optimize for engagement metrics. Your library is the boundary and the curriculum. External recommendations pull the DJ away from knowing their own collection deeply. We go inward, not outward.

### 3. We don't replace the DJ's ear.
Scores are information, not verdicts. A transition the algorithm rates poorly might be exactly what the room needs at 4AM. We never override the DJ's judgment. We inform it. The moment a DJ trusts the score more than their own instinct, we've failed.

### 4. We are not a library management tool.
Rekordbox manages your library. We understand it. We don't import, tag, organize, or sync files. We read what you've already built and reflect it back with insight. Library intelligence, not library management. The distinction matters: we're the mirror, not the shelf.

### 5. We don't hide the math.
"It just works" is not our philosophy. When we score a transition, we show every dimension. When we suggest a track, we show why. Hiding the reasoning would be faster and simpler, but it would kill the teaching. Transparency is not a feature -- it's the foundation. If we can't explain a suggestion, we shouldn't make it.
