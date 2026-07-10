# Causal diagram notation: steals, hand-ins, zips, and role-based rotation

Design for extending the `causal_diagram` shortcode language
(`plugins/causal_diagram/causal_diagram.py`) so that patterns like
Roundabout (steals, hand-ins) and moving patterns like Havana
(rotating roles) can be written as diagrams instead of prose.

## Motivation

Two gaps in the current language:

1. **Steals, hand-ins, zips.** In Roundabout, C stands between two
   4-count passers with one club, steals a pass out of the air, and
   hands their club into the other passer's pattern. The current
   language can only express throws on a per-beat grid, so a sparse
   juggler acting at fractional times cannot be written down.
2. **Rotating roles.** In moving patterns (Havana,
   rotating-torture-chamber, ...) the role cycle is short but the
   per-person cycle is the long super-period. Today the super-period
   must be written out by hand (four 40-token lines in havana.md).

## Decisions already made

- Timing: events can occur at **arbitrary fractional beats**.
- A stolen pass renders as **one arrow, thrower to stealer**, in a
  distinctive steal style. No ghost arrow to the intended target.
- Hands for event actions are **explicit** (`R`/`L`), and the diagram
  shows that a juggler is idle/holding (empty beats visible).
- **No club-count validation**: the plugin draws what is written.
  Validation could be layered on later without changing syntax.
- Events are written **inline in the pattern line**, not on a
  separate `events:` line.
- The victim of a steal writes their line as if nothing happened
  (`3a` — the intended target). The steal reroutes the arrow.

## Language additions

### 1. Continuation auto-detection

A logical line continues onto the next physical line when the line so
far is syntactically unfinished:

- it has an **unclosed `(`**, or
- it **ends with `;`** (the separator inside `position` lines and
  event blocks).

The explicit trailing `\` continues to work. Leading whitespace stays
insignificant: existing pages (havana.md, 8-club-PPS.md,
rotating-torture-chamber.md, 6-count-popcorn.md) indent lines
cosmetically for column alignment, so indentation must never mean
continuation. A trailing `,` is **not** a continuation signal because
`,` is a color suffix (`3p,` = red-thick arrow).

### 2. Silent beats: `-`

The grid token `-` occupies one beat with no throw. Rendering: a
faint, letterless, dashed circle (CSS class `beat-empty`) so a
one-club juggler's inactivity is visible at a glance.

### 3. Inline event blocks

```
(<beats>: <time> <action> <args>; <time> <action> <args>; ...)
```

placed like a token inside a pattern line. The block consumes
`<beats>` beats of the grid (float allowed). Each `<time>` is
relative to the start of the block, so blocks can be moved without
rewriting their contents. Event times must lie in `[0, beats)`. Disambiguation from the hands/wait prefix
`(RL 0.5)`: a `(` block containing `:` is an event block; this works
even when the block is the first token on the line.

Transfer endpoints use the form `[juggler][hand]`, with your own
juggler letter implied when omitted, and `>` giving the direction
(source > destination):

| action | example | meaning |
|---|---|---|
| steal (from air) | `steal b>L` | intercept B's in-flight club, catch with my left |
| take (from hand) | `steal cR>L` | take the club held in C's right hand into my left |
| hand-in | `hand R>cL` | place my right-hand club into C's left hand |
| zip | `zip L>R` | hand-across, my left to my right |
| throw | `throw 3a R` | a normal throw token at an off-grid time, from my right |

A source *with* a hand letter means "grab a held club" (take); a
source *without* one means "intercept the club in flight" (steal
proper). `hand`, `zip`, and takes are instantaneous transfers with a
single timestamp; a slow carry is expressed by placing the release
event later.

**Steal matching rule:** at absolute event time `t`, find the club
thrown by the source juggler that is in the air at `t` (thrown at
`t0 <= t`, scheduled causal arrival `t0 + value - 2 >= t`). If
several qualify, take the one whose arrival is nearest `t`. The
matched arrow's endpoint moves to (stealer's row, time `t`) and its
CSS class becomes the steal style.

Example — A passes 4-count, then spends two beats as the thief:

```
A: 3b 3 3 3 (2: 0 steal b>L; 0.25 hand R>cL; 0.5 zip L>R) 3b 3
```

### 4. Arrow labels

Any token or event that draws an arrow can carry a short text label,
shown next to the arrow in both diagrams (e.g. "lofty", "chop"):

- grid tokens: the label is a double-quoted string attached directly
  to the token, after the color suffix if present — `3b"lofty"`,
  `4.5p$"early"`.
- event actions: a trailing quoted string — `steal b>L "chop"`.

Labels may contain spaces; the line tokenizer becomes quote-aware
(quoted regions are never split, and `#` inside quotes is not a
comment). Label placement is at the arrow's midpoint, offset to sit
above the line/curve, CSS class `arrow-label`. In the position
diagram the label animates with the same opacity timing as its
arrow, so it appears and disappears with it. Avoiding label overlap
in dense diagrams is the author's responsibility (consistent with
"just draw it").

### 5. Role-based rotation: `swap:`

```
swap: A->B->C->D
```

- The pattern lines describe **roles** for one period. The period is
  the written length of the lines in beats.
- `A->B` means: after each period, the person currently doing line A
  does line B next (people move through roles; the last role wraps to
  the first).
- Multiple disjoint chains are allowed: `swap: A->B->A, C->D->C`.
- The plugin unrolls until every person is back in their starting
  role (LCM of chain lengths) and renders the full super-period. The
  existing auto-scroll handles the width.
- Rows are labeled by **person**, named after their starting role.
- Target letters in throws (`3a`) and event endpoints (`>cL`) refer
  to **roles** and are remapped to the current person each period.
- `position X:` lines describe role X's path for one period;
  unrolling concatenates the paths per person. Continuity (role A's
  path ends where role B's begins) is the author's responsibility and
  physically true anyway.
- A role line's `(hands wait)` prefix applies within each period:
  when a person occupies role r in period k, their tokens sit at
  `period_start + wait_r + i`.
- `bars:` stays absolute (unrolled coordinates).

## Rendering

New CSS classes in `themes/mytheme/assets/css/custom.css`:

- `arrow-steal` — dashed with open arrowhead (thrower to stealer).
- `arrow-hand` — hand-ins and takes (direction distinguishes them).
- `arrow-zip` — short arrow within one juggler's row.
- `beat-empty` — faint dashed circle for `-` beats.
- `hold-line` — thin horizontal line on a juggler's row from a catch
  event (steal/receive) to the juggler's next release event
  (hand/zip/throw), showing "carrying a club" during walks. (No club
  identity tracking; it simply spans catch to next release.)
- `arrow-label` — text next to an arrow, both diagrams.

Causal diagram: event circles are drawn at their fractional x
position with the specified hand letter. The receiving side of a
hand-in gets no extra circle; the arrowhead landing on the row at
that time is the notation.

Position diagram: event arrows animate exactly like pass arrows
today — from the source hand's position at the event time to the
destination hand's position (the existing
`get_juggler_hand_position` machinery, evaluated at fractional
times). A zip renders as a short arrow between the juggler's own two
hand positions.

## Out of scope

- Club-count validation / physical-possibility warnings.
- Ghost arrows showing a steal's intended target.
- Mid-period swaps or partial-period role changes.
- A separate `events X:` line (inline blocks are the only syntax).

## Implementation stages (one commit each)

1. **Continuation auto-detection** (unclosed `(`, trailing `;`).
   Verify: full site rebuild produces byte-identical output
   (deterministic ids make this diffable).
2. **`-` silent beats** + `beat-empty` rendering.
3. **Event block parsing** into a per-juggler event stream (steal /
   take / hand / zip / throw, `L>cR` endpoints). No rendering yet;
   unit-testable in isolation.
4. **Causal-diagram rendering of events**: fractional-time circles,
   steal arrow rerouting, hold lines, new CSS classes.
5. **Position-diagram rendering of events**: animated arrows at
   fractional times, zip arrows.
6. **Arrow labels**: quote-aware tokenizer, label parsing on grid
   tokens and event actions, rendering in both diagrams.
7. **`swap:` role unrolling**: tokens, target remapping, positions,
   per-period waits.
8. **Documentation**: extend pages/patterns/causal-diagrams.md with
   the new syntax and small live examples.
9. **Pattern pages**: add a diagram to roundabout.md; rewrite
   havana.md with `swap:` notation and verify the rendered diagram
   matches the current hand-unrolled one.

Each stage rebuilds the site and checks that pages not using the new
features are unchanged.
