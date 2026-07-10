# Causal Diagram Steals, Labels & Roles Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the `causal_diagram` Nikola shortcode language with silent beats, inline event blocks (steals/takes/hand-ins/zips/off-grid throws), arrow labels, and role-based rotation (`swap:`), per the spec in `docs/superpowers/specs/2026-07-09-causal-diagram-steals-roles-design.md`.

**Architecture:** All logic lives in the single plugin file `plugins/causal_diagram/causal_diagram.py` (class `CausalDiagramSVG`). Task 4 refactors causal-arrow drawing into a collect-then-draw pipeline (throw records), which Task 7's role unrolling then operates on. Parsing changes are pure functions where possible so they can be unit tested without Nikola.

**Tech Stack:** Python 3.13+, svgwrite, pytest (added in Task 1), uv for env/deps, Nikola static site generator. Jinja is only used by page templates, not by the plugin.

## Global Constraints

- The plugin must keep producing byte-identical output for diagrams that do not use new features (deterministic ids are already in place; verify by rebuilding the site and diffing `output/`).
- Leading whitespace in shortcode input must remain insignificant (existing pages indent cosmetically).
- A trailing `,` must never trigger line continuation (`,` is the red-thick color suffix).
- No club-count validation anywhere — the plugin draws what is written.
- Event hands are only `R` or `L`.
- New CSS classes go in `themes/mytheme/assets/css/custom.css`: `arrow-steal`, `arrow-hand`, `arrow-zip`, `arrow-label`, `beat-empty`, `hold-line`.
- Run all tests with: `uv run pytest tests/ -v` from the repo root.
- Build the site with: `uv run nikola build` from the repo root.
- Each task = one commit, message style: lowercase, `causal diagram: <what>`.

## How the plugin works today (context for every task)

- `CausalDiagramSVG.handler(site, data, lang, post)` is the shortcode entry point; it creates a fresh instance, calls `parse(data)`, returns `(self.to_svg(), [])`.
- `parse(text)` splits input into lines, strips `#` comments, joins `\` continuations, and dispatches: `title:` / `bars:` / `position...` / `step...` lines, everything else is a juggler pattern line handled by `parse_pattern(line)`.
- `parse_pattern` auto-names jugglers `A`, `B`, ... (class attr `juggler_names`), pulls an optional `(hands wait)` prefix via `parse_hands_and_delay`, and stores per juggler: `letters` (hand cycle string, default `"RL"`), `wait` (float beat offset), `pattern` (list of whitespace-split token strings), `height` (row y in the causal SVG).
- Tokens: `3` self, `3b` pass to juggler B (lowercase target), optional color suffix from the module-level `COLORS` dict (e.g. `3b,` red). `get_style(token) -> (token_without_color, css_class)`.
- Causal arrow geometry: token at beat index `i` sits at `X = 2*margin + step_X * (1 + wait + i)`; the arrow spans `value - 2` beats horizontally; `draw_arrow` handles line vs bezier (long selves).
- Position diagram: `position X:` keyframes per juggler; `get_juggler_position(name, t)` interpolates; `get_juggler_hand_position(name, t, delay)` offsets to the R/L hand by cycling `letters`; `draw_animated_arrow` draws pass arrows with SMIL opacity animation over `duration_position` seconds.
- `to_svg()` returns a single causal SVG, or a synced pair (causal + position) when all jugglers have positions.

---

### Task 1: pytest setup + continuation auto-detection

**Files:**
- Modify: `pyproject.toml` (dev dependency via `uv add --dev pytest`)
- Create: `tests/conftest.py`
- Create: `tests/test_parsing.py`
- Modify: `plugins/causal_diagram/causal_diagram.py` (extract `logical_lines`, use in `parse`)

**Interfaces:**
- Produces: module-level function `logical_lines(text: str) -> list[str]` in `causal_diagram.py` — comment-stripped, continuation-joined logical lines. `parse()` iterates its result. Later tasks (6) will make its comment stripping quote-aware.

- [ ] **Step 1: Add pytest and test scaffolding**

```bash
uv add --dev pytest
```

Create `tests/conftest.py`:

```python
import sys
from pathlib import Path

# the plugin lives in a Nikola plugin directory, not a package
sys.path.insert(0, str(Path(__file__).parent.parent / "plugins" / "causal_diagram"))
```

- [ ] **Step 2: Write failing tests for logical_lines**

Create `tests/test_parsing.py`:

```python
from causal_diagram import logical_lines


def test_plain_lines_stay_separate():
    assert logical_lines("3p 3 3\n3p 3 3") == ["3p 3 3", "3p 3 3"]


def test_backslash_continuation_still_works():
    text = "position A: 0,-100,0,@B;\\\n2,-100,0,@C;"
    assert logical_lines(text) == ["position A: 0,-100,0,@B;2,-100,0,@C;"]


def test_trailing_semicolon_continues():
    text = "position A: 0,-100,0,@B;\n    2,-100,0,@C;"
    assert logical_lines(text) == ["position A: 0,-100,0,@B; 2,-100,0,@C;"]


def test_unclosed_paren_continues():
    text = "3b 3 (2: 0 steal b>L;\n0.25 hand R>cL) 3 3"
    assert logical_lines(text) == ["3b 3 (2: 0 steal b>L; 0.25 hand R>cL) 3 3"]


def test_cosmetic_indentation_is_not_continuation():
    # havana.md and others column-align lines with leading spaces
    text = "3d 3 3c 3\n  3 3 3a 3\n  3 3 3b 3"
    assert logical_lines(text) == ["3d 3 3c 3", "3 3 3a 3", "3 3 3b 3"]


def test_trailing_comma_is_not_continuation():
    # ',' is the red-thick color suffix, e.g. 3p,
    assert logical_lines("3 3 3p,\n3 3 3p") == ["3 3 3p,", "3 3 3p"]


def test_comments_stripped():
    assert logical_lines("3 3 3  # a comment\n3 3 3") == ["3 3 3", "3 3 3"]
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/test_parsing.py -v`
Expected: FAIL with `ImportError: cannot import name 'logical_lines'`

- [ ] **Step 4: Implement logical_lines and use it in parse**

In `plugins/causal_diagram/causal_diagram.py`, add after the `COLORS` dict:

```python
def logical_lines(text: str) -> list[str]:
    """Split shortcode text into logical lines.

    A logical line continues onto the next physical line when it is
    syntactically unfinished: an unclosed "(" or a trailing ";".
    A trailing "\\" forces continuation (legacy syntax). Leading
    whitespace is insignificant (pages indent cosmetically), and a
    trailing "," must NOT continue (it is a color suffix).
    """
    lines = []
    current = ""
    for raw in text.split("\n"):
        if "#" in raw:
            raw = raw.split("#")[0]
        raw = raw.strip()
        if raw.endswith("\\"):
            current += raw[:-1].strip()
            continue
        if current and raw:
            current += " " + raw
        else:
            current += raw
        if not current:
            continue
        if current.count("(") > current.count(")") or current.endswith(";"):
            continue
        lines.append(current)
        current = ""
    if current:
        lines.append(current)
    return lines
```

Then replace the line-joining loop at the top of `parse` (the `line = ""` / `for current_line in text.split("\n")` block) so it dispatches over `logical_lines(text)` instead:

```python
        for line in logical_lines(text):
            # handle the different input options
            if line.startswith("title:"):
                self.parse_title(line)
            elif line.startswith("bars:"):
                self.parse_bars(line)
            elif line.startswith("position"):
                self.parse_position(line)
            elif line.startswith("step"):
                self.parse_layout(line)
            else:
                self.parse_pattern(line)
```

(The rest of `parse` — duration computation, title height, `calc_angle` — is unchanged.)

Note one deliberate behavior change: `\` and `;`/`(` continuations now join with a single space when both sides are non-empty. Token splitting and `position` parsing are whitespace/`;`-tolerant, so this is safe; the backslash test in Step 2 pins the no-space case (`;` at the join point produces `;2,...` → strip handles it — the test asserts the actual expected string, adjust implementation until tests pass, not the tests).

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_parsing.py -v`
Expected: all PASS. If `test_backslash_continuation_still_works` fails on the space, special-case the `\` branch to join without a space (shown above) — that preserves today's exact behavior.

- [ ] **Step 6: Verify site output is unchanged**

```bash
uv run nikola build
git status --porcelain output/ | head    # if output/ is gitignored, instead:
uv run python - <<'EOF'
import hashlib, pathlib
h = hashlib.md5()
for p in sorted(pathlib.Path("output").rglob("*.html")):
    h.update(p.read_bytes())
print(h.hexdigest())
EOF
```

Run the hash snippet before starting the task (on a clean build) and after; the two hashes must match. `output/` is gitignored, so the hash comparison is the check.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml uv.lock tests/ plugins/causal_diagram/causal_diagram.py
git commit -m "causal diagram: auto-detect continuation lines, add pytest"
```

---

### Task 2: `-` silent beats

**Files:**
- Modify: `plugins/causal_diagram/causal_diagram.py` (`draw_circle`, causal + position render loops)
- Modify: `themes/mytheme/assets/css/custom.css` (add `.beat-empty`)
- Test: `tests/test_render.py` (create)

**Interfaces:**
- Consumes: nothing new.
- Produces: grid token `-` = one silent beat. `draw_circle(dwg, x, y, r, label, angle=None, css_class=None)` gains the optional `css_class` kwarg (applied to the circle element). Later tasks may draw empty circles the same way.

- [ ] **Step 1: Write failing tests**

Create `tests/test_render.py`:

```python
from causal_diagram import CausalDiagramSVG


def render(data):
    out, _ = CausalDiagramSVG().handler(data=data)
    return out


def test_silent_beat_draws_no_arrow():
    svg = render("3 - 3 3\n3 3 3 3")
    # juggler A has 3 arrows, B has 4; each throw of value 3 -> one line/path
    assert svg.count("beat-empty") == 1


def test_silent_beat_circle_has_no_letter():
    svg = render("3 - 3 3")
    # the beat-empty circle must not carry a hand letter next to it
    empty_idx = svg.index("beat-empty")
    # crude but effective: no <text> within the empty group snippet
    assert "<text" not in svg[empty_idx:empty_idx + 200]


def test_silent_beat_in_position_diagram_does_not_crash():
    svg = render("3b - 3 3\n3a 3 3 3\npositions: line")
    assert "data-sync-id" in svg
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_render.py -v`
Expected: FAIL (`beat-empty` not found; the position test may raise in the pass branch).

- [ ] **Step 3: Implement**

(a) `draw_circle` — add `css_class=None` parameter; when set, pass `class_=css_class` to `dwg.circle(...)` and skip the text element when `label` is empty:

```python
    def draw_circle(self, dwg, x, y, r, label, angle=None, css_class=None):
        group = dwg.g()
        circle_kwargs = {"center": (x, y), "r": r, "stroke": "black", "fill": "none"}
        if css_class:
            circle_kwargs["class_"] = css_class
        group.add(dwg.circle(**circle_kwargs))
        if label:
            group.add(
                dwg.text(
                    label,
                    insert=(x, y),
                    fill="black",
                    text_anchor="middle",
                    dominant_baseline="middle",
                )
            )
        # ... angle triangle code unchanged ...
        return group
```

(b) In `generate_causal_diagram_svg`, inside the `for p, hand in zip(juggler["pattern"], cycle(juggler["letters"]))` loop, before anything else:

```python
                if p == "-":
                    group = self.draw_circle(
                        dwg, X, H, self.radius, "", css_class="beat-empty"
                    )
                    dwg.add(group)
                    X += self.step_X
                    X_max = X
                    continue
```

(c) In `generate_position_diagram_svg`, inside the `for i, pat in enumerate(...)` loop, first line:

```python
                    if pat.strip() == "-":
                        continue
```

(d) Append to `themes/mytheme/assets/css/custom.css` after the arrow styles:

```css
/* silent beat (juggler idle / holding) */
.beat-empty {
  stroke-dasharray: 3 3;
  opacity: 0.35;
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/ -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/causal_diagram/causal_diagram.py themes/mytheme/assets/css/custom.css tests/test_render.py
git commit -m "causal diagram: add '-' silent beats"
```

---

### Task 3: event block parsing

**Files:**
- Modify: `plugins/causal_diagram/causal_diagram.py`
- Test: `tests/test_events.py` (create)

**Interfaces:**
- Consumes: `logical_lines` (Task 1).
- Produces (all module-level in `causal_diagram.py`, used by Tasks 4, 5, 6, 7):

```python
@dataclass
class Event:
    time: float            # relative to block start at parse time;
                           # collect_events() returns absolute copies
    action: str            # "steal" | "hand" | "zip" | "throw"
    src: tuple[str | None, str | None] = (None, None)  # (juggler, hand); juggler None = self
    dst: tuple[str | None, str | None] = (None, None)
    value: str | None = None   # throw only: the token, e.g. "3a"
    hand: str | None = None    # throw only: throwing hand
    label: str | None = None   # filled in Task 6

def tokenize_pattern(line: str) -> list[str]      # whitespace split, ()-aware
def parse_endpoint(s: str) -> tuple[str | None, str | None]
def parse_event(text: str) -> Event
def parse_event_block(token: str) -> dict         # {"beats": float, "events": [Event, ...]}
```

- `juggler["pattern"]` entries become `str | dict` (dict = event block).
- New instance method `CausalDiagramSVG.pattern_beats(juggler: dict) -> float` — total beats of a pattern (1 per str token, `block["beats"]` per block). Replaces `len(j["pattern"])` in duration computation.
- New instance method `CausalDiagramSVG.collect_events(name: str) -> list[Event]` — all events of a juggler with `time` converted to absolute beats (block start beat + `wait` + relative time).

- [ ] **Step 1: Write failing tests**

Create `tests/test_events.py`:

```python
import pytest
from causal_diagram import (
    CausalDiagramSVG,
    parse_endpoint,
    parse_event,
    parse_event_block,
    tokenize_pattern,
)


def test_tokenize_keeps_event_block_together():
    toks = tokenize_pattern("3b 3 (2: 0 steal b>L; 0.25 hand R>cL) 3")
    assert toks == ["3b", "3", "(2: 0 steal b>L; 0.25 hand R>cL)", "3"]


def test_parse_endpoint():
    assert parse_endpoint("L") == (None, "L")
    assert parse_endpoint("cR") == ("C", "R")
    assert parse_endpoint("b") == ("B", None)


def test_parse_event_steal_from_air():
    e = parse_event("0 steal b>L")
    assert (e.time, e.action, e.src, e.dst) == (0.0, "steal", ("B", None), (None, "L"))


def test_parse_event_take_from_hand():
    e = parse_event("0.5 steal cR>L")
    assert e.src == ("C", "R")
    assert e.dst == (None, "L")


def test_parse_event_hand_and_zip():
    e = parse_event("0.25 hand R>cL")
    assert (e.action, e.src, e.dst) == ("hand", (None, "R"), ("C", "L"))
    z = parse_event("0.5 zip L>R")
    assert (z.action, z.src, z.dst) == ("zip", (None, "L"), (None, "R"))


def test_parse_event_throw():
    e = parse_event("1 throw 3a R")
    assert (e.action, e.value, e.hand) == ("throw", "3a", "R")


def test_parse_event_block():
    b = parse_event_block("(2: 0 steal b>L; 0.25 hand R>cL)")
    assert b["beats"] == 2.0
    assert [e.action for e in b["events"]] == ["steal", "hand"]


def test_event_time_outside_block_raises():
    with pytest.raises(ValueError):
        parse_event_block("(1: 1.5 zip L>R)")


def test_pattern_line_with_block_and_hands_prefix():
    d = CausalDiagramSVG()
    d.parse("(RL 0.5) 3b 3 (2: 0 steal b>L) 3\n3a 3 3 3 3")
    A = d.juggler["A"]
    assert A["wait"] == 0.5
    assert isinstance(A["pattern"][2], dict)
    assert d.pattern_beats(A) == 5.0
    # absolute time: block starts at beat 2, wait 0.5 -> steal at 2.5
    events = d.collect_events("A")
    assert events[0].time == 2.5


def test_block_as_first_token_is_not_hands_prefix():
    d = CausalDiagramSVG()
    d.parse("(1: 0 zip L>R) 3 3\n3 3 3")
    A = d.juggler["A"]
    assert A["letters"] == "RL"       # default, prefix not consumed
    assert isinstance(A["pattern"][0], dict)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_events.py -v`
Expected: FAIL with ImportError (names don't exist yet).

- [ ] **Step 3: Implement parsing**

In `causal_diagram.py` add `from dataclasses import dataclass, replace` to the imports (`replace` is used by `collect_events` below), then after `logical_lines`:

```python
@dataclass
class Event:
    time: float
    action: str
    src: tuple = (None, None)
    dst: tuple = (None, None)
    value: str | None = None
    hand: str | None = None
    label: str | None = None


def tokenize_pattern(line: str) -> list[str]:
    """Whitespace split that keeps (...) groups (event blocks) intact."""
    tokens, cur, depth = [], "", 0
    for ch in line:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch.isspace() and depth == 0:
            if cur:
                tokens.append(cur)
            cur = ""
        else:
            cur += ch
    if cur:
        tokens.append(cur)
    return tokens


def parse_endpoint(s: str) -> tuple:
    """ "L" -> (None, "L"); "cR" -> ("C", "R"); "b" -> ("B", None).

    Own juggler is implied by None. Hands are only R or L; any other
    letter is a juggler name.
    """
    juggler, hand = None, None
    for ch in s.strip():
        if ch in "RL":
            hand = ch
        elif ch.isalpha():
            juggler = ch.upper()
    return juggler, hand


def parse_event(text: str) -> Event:
    parts = text.split()
    time = float(parts[0])
    action = parts[1]
    if action == "throw":
        return Event(time=time, action="throw", value=parts[2],
                     hand=parts[3] if len(parts) > 3 else None)
    if action not in ("steal", "hand", "zip"):
        raise ValueError(f"unknown event action: {action!r}")
    src, dst = parts[2].split(">")
    return Event(time=time, action=action,
                 src=parse_endpoint(src), dst=parse_endpoint(dst))


def parse_event_block(token: str) -> dict:
    """ "(2: 0 steal b>L; 0.25 hand R>cL)" -> {"beats": 2.0, "events": [...]}. """
    inner = token[1:-1]
    beats_str, rest = inner.split(":", 1)
    beats = float(beats_str)
    events = [parse_event(e) for e in rest.split(";") if e.strip()]
    for e in events:
        if not 0 <= e.time < beats:
            raise ValueError(
                f"event time {e.time} outside block of {beats} beats: {token}"
            )
    return {"beats": beats, "events": events}
```

- [ ] **Step 4: Wire into parse_pattern and the class**

Replace the body of `parse_pattern` so it tokenizes paren-aware and recognizes event blocks. The hands/wait prefix is only consumed when the first token is a `(...)` group **without** a `:`:

```python
    def parse_pattern(self, line: str) -> None:
        n = len(self.juggler)
        juggler_name = self.juggler_names[n]
        tmp = {}
        tokens = tokenize_pattern(line)
        hands, wait = "RL", 0
        if tokens and tokens[0].startswith("(") and ":" not in tokens[0]:
            prefix = tokens.pop(0)[1:-1].strip()
            if " " in prefix:
                hands, wait_str = prefix.rsplit(None, 1)
                wait = float(wait_str)
            else:
                try:
                    wait = float(prefix)
                except ValueError:
                    hands = prefix
        tmp["letters"] = hands
        tmp["wait"] = wait
        pattern = []
        for tok in tokens:
            if tok.startswith("(") and ":" in tok:
                pattern.append(parse_event_block(tok))
            else:
                pattern.append(tok)
        # 'p' passes only in 2-person patterns (existing behavior)
        if any(isinstance(t, str) and "p" in t for t in pattern):
            other = "b" if juggler_name == "A" else "a"
            pattern = [t.replace("p", other) if isinstance(t, str) else t
                       for t in pattern]
        tmp["pattern"] = pattern
        tmp["height"] = self.margin + int(self.step_Y * (n + 0.5))
        self.juggler[juggler_name] = tmp
```

`parse_hands_and_delay` becomes unused by `parse_pattern`; delete it (nothing else calls it — verify with grep before deleting).

Add the two instance methods:

```python
    def pattern_beats(self, juggler: dict) -> float:
        total = 0.0
        for t in juggler["pattern"]:
            total += t["beats"] if isinstance(t, dict) else 1
        return total

    def collect_events(self, name: str) -> list:
        """All events of a juggler, times converted to absolute beats."""
        juggler = self.juggler[name]
        out = []
        beat = float(juggler["wait"])
        for t in juggler["pattern"]:
            if isinstance(t, dict):
                for e in t["events"]:
                    out.append(replace(e, time=beat + e.time))
                beat += t["beats"]
            else:
                beat += 1
        return out
```

(`from dataclasses import dataclass, replace` — adjust the import.)

In `parse`, change the duration line to use beats:

```python
        self.duration_pattern = max(
            [self.pattern_beats(j) for j in self.juggler.values()]
        )
```

- [ ] **Step 5: Run tests**

Run: `uv run pytest tests/ -v`
Expected: all PASS, including Tasks 1–2 tests (regression check on the parse_pattern rewrite; the WOMBLE multi-letter hands case is covered by `test_pattern_line_with_block_and_hands_prefix`-style parsing, and existing pages verify at build time).

- [ ] **Step 6: Verify site output unchanged**

Same hash check as Task 1 Step 6. `parse_pattern` was rewritten, so this build-diff matters most here.

- [ ] **Step 7: Commit**

```bash
git add plugins/causal_diagram/causal_diagram.py tests/test_events.py
git commit -m "causal diagram: parse inline event blocks (steal/hand/zip/throw)"
```

---

### Task 4: causal-diagram rendering of events

**Files:**
- Modify: `plugins/causal_diagram/causal_diagram.py`
- Modify: `themes/mytheme/assets/css/custom.css`
- Test: `tests/test_render.py` (extend)

**Interfaces:**
- Consumes: `Event`, `collect_events(name)`, `pattern_beats(juggler)` (Task 3); `draw_circle(..., css_class=)` (Task 2).
- Produces (used by Tasks 5, 6, 7):

```python
@dataclass
class Throw:
    juggler: str            # thrower name ("A", ...)
    time: float             # absolute throw beat (includes wait)
    value: float            # numeric throw value
    target: str             # intended target juggler (== juggler for selves)
    style: str              # css class from get_style
    hand: str               # letter drawn in the throw circle
    label: str | None = None
    stolen_by: str | None = None   # set by apply_steals
    steal_time: float | None = None

    @property
    def arrival(self) -> float:
        return self.time + self.value - 2

def CausalDiagramSVG.collect_throws(self) -> list[Throw]
def CausalDiagramSVG.apply_steals(self, throws: list[Throw]) -> None   # mutates
def CausalDiagramSVG.x_of(self, t: float) -> float   # beat -> causal x coordinate
```

`generate_causal_diagram_svg` is refactored: circles and the beat cursor stay in a per-juggler loop, but **all arrows** come from the `Throw` list (collect → apply_steals → draw). Task 7 injects unrolled throws through the same list.

- [ ] **Step 1: Write failing tests**

Append to `tests/test_render.py`:

```python
ROUNDABOUT_SNIPPET = (
    "3b 3 3 3\n"
    "3a 3 3 3\n"
    "(RL 1) (4: 0 steal a>L; 0.25 hand R>bL; 0.5 zip L>R)\n"
)
# line 3 = juggler C: hands RL, waits 1 beat, then steals A's pass (thrown
# at beat 0, in the air until beat 1), hands own club to B, zips.


def test_steal_reroutes_and_styles_arrow():
    svg = render(ROUNDABOUT_SNIPPET)
    assert svg.count("arrow-steal") == 1
    # A threw one pass and it was stolen: no plain pass arrow may remain
    # for that throw. A's other three throws are selves (3 -> value-2=1).


def test_hand_in_draws_arrow_and_hold_line():
    svg = render(ROUNDABOUT_SNIPPET)
    assert "arrow-hand" in svg
    assert "arrow-zip" in svg
    assert "hold-line" in svg


def test_event_circles_show_explicit_hand():
    svg = render(ROUNDABOUT_SNIPPET)
    # C's steal catches with L: a circle labeled L exists on C's row.
    # Rendering details vary; assert the letter appears after the steal x.
    assert ">L<" in svg


def test_no_events_output_identical_shape():
    # regression: a plain diagram still renders one arrow per throw
    svg = render("3 3 3\n3 3 3")
    assert "arrow-steal" not in svg and "hold-line" not in svg
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_render.py -v`
Expected: new tests FAIL (`arrow-steal` etc. absent).

- [ ] **Step 3: Implement Throw collection**

Add the `Throw` dataclass (module level, after `Event`) exactly as in the Interfaces block, then these methods on `CausalDiagramSVG`:

```python
    def x_of(self, t: float) -> float:
        """Causal-diagram x coordinate for an absolute beat time."""
        return 2 * self.margin + self.step_X * (1 + t)

    def collect_throws(self) -> list:
        """All grid throws plus explicit 'throw' events, as Throw records."""
        throws = []
        for name, juggler in self.juggler.items():
            beat = 0.0
            letter_idx = 0
            letters = juggler["letters"]
            for tok in juggler["pattern"]:
                if isinstance(tok, dict):
                    beat += tok["beats"]
                    # hands alternate per beat while events happen
                    letter_idx += int(round(tok["beats"]))
                    continue
                if tok == "-":
                    beat += 1
                    letter_idx += 1
                    continue
                tok2, style = self.get_style(tok)
                try:
                    value = float(tok2)
                    target = name
                except ValueError:
                    target = tok2[-1].upper()
                    value = float(tok2[:-1])
                throws.append(
                    Throw(
                        juggler=name,
                        time=juggler["wait"] + beat,
                        value=value,
                        target=target,
                        style=style,
                        hand=letters[letter_idx % len(letters)],
                    )
                )
                beat += 1
                letter_idx += 1
            for e in self.collect_events(name):
                if e.action == "throw":
                    tok2, style = self.get_style(e.value)
                    try:
                        value = float(tok2)
                        target = name
                    except ValueError:
                        target = tok2[-1].upper()
                        value = float(tok2[:-1])
                    throws.append(
                        Throw(juggler=name, time=e.time, value=value,
                              target=target, style=style, hand=e.hand or "")
                    )
        return throws

    def apply_steals(self, throws: list) -> None:
        """Match steal events to in-flight throws and reroute them.

        A steal (src hand is None) matches a throw by the source juggler
        that is in the air at the event time; if several match, the one
        whose arrival is nearest. Takes (src hand set) grab a held club
        and do not touch the throw list.
        """
        for name in self.juggler:
            for e in self.collect_events(name):
                if e.action != "steal" or e.src[1] is not None:
                    continue
                source = e.src[0]
                candidates = [
                    t for t in throws
                    if t.juggler == source and t.stolen_by is None
                    and t.time <= e.time <= t.arrival + 1e-9
                ]
                if not candidates:
                    continue  # just draw it: nothing to reroute
                best = min(candidates, key=lambda t: abs(t.arrival - e.time))
                best.stolen_by = name
                best.steal_time = e.time
```

- [ ] **Step 4: Refactor generate_causal_diagram_svg**

Replace the `# draw the causal diagram` block (the `for i, (name, juggler) in enumerate(self.juggler.items())` loop that draws names, circles, and arrows) with three phases. Keep everything before it (frame, marker, title, bars) and after it (animated red bar) unchanged, except `X_max` now comes from phase 1.

```python
        # phase 1: names, circles, empty beats -- also find X_max
        X_max = 0
        for name, juggler in self.juggler.items():
            H = juggler["height"]
            dwg.add(
                dwg.text(f"{name}:", insert=(self.margin, H),
                         fill="black", dominant_baseline="middle")
            )
            beat = 0.0
            letter_idx = 0
            letters = juggler["letters"]
            for tok in juggler["pattern"]:
                X = self.x_of(juggler["wait"] + beat)
                if isinstance(tok, dict):
                    for e in tok["events"]:
                        ex = self.x_of(juggler["wait"] + beat + e.time)
                        hand = self.event_circle_hand(e)
                        if hand is not None:
                            dwg.add(self.draw_circle(dwg, ex, H, self.radius, hand))
                    beat += tok["beats"]
                    letter_idx += int(round(tok["beats"]))
                elif tok == "-":
                    dwg.add(self.draw_circle(dwg, X, H, self.radius, "",
                                             css_class="beat-empty"))
                    beat += 1
                    letter_idx += 1
                else:
                    dwg.add(self.draw_circle(
                        dwg, X, H, self.radius,
                        letters[letter_idx % len(letters)]))
                    beat += 1
                    letter_idx += 1
                X_max = max(X_max, self.x_of(juggler["wait"] + beat))

        # phase 2: throws -> steals -> arrows
        throws = self.collect_throws()
        self.apply_steals(throws)
        for t in throws:
            start_x = self.x_of(t.time)
            start_y = self.juggler[t.juggler]["height"]
            if t.stolen_by:
                end_x = self.x_of(t.steal_time)
                end_y = self.juggler[t.stolen_by]["height"]
                style = "arrow-steal"
            else:
                end_x = self.x_of(t.arrival)
                end_y = self.juggler[t.target]["height"]
                style = t.style
            arrow = self.draw_arrow(dwg, arrow_marker, start_x, start_y,
                                    end_x, end_y, css_class=style)
            if arrow:
                dwg.add(arrow)

        # phase 3: transfer arrows (hand / take / zip) and hold lines
        self.draw_causal_events(dwg, arrow_marker, throws)
```

Add the two helpers:

```python
    def event_circle_hand(self, e) -> str | None:
        """Which hand letter to show in the circle drawn for an event."""
        if e.action == "steal":
            return e.dst[1]      # catching hand
        if e.action == "hand":
            return e.src[1]      # giving hand
        if e.action == "zip":
            return e.dst[1]      # club ends up here
        if e.action == "throw":
            return e.hand
        return None

    def draw_causal_events(self, dwg, arrow_marker, throws):
        catches = {name: [] for name in self.juggler}   # (time, juggler)
        releases = {name: [] for name in self.juggler}
        for name in self.juggler:
            H = self.juggler[name]["height"]
            for e in self.collect_events(name):
                x = self.x_of(e.time)
                if e.action == "steal":
                    catches[name].append(e.time)
                    if e.src[1] is not None:      # take from a held hand
                        src_h = self.juggler[e.src[0]]["height"]
                        arr = self.draw_arrow(dwg, arrow_marker,
                                              x, src_h, x, H,
                                              css_class="arrow-hand")
                        if arr:
                            dwg.add(arr)
                        releases[e.src[0]].append(e.time)
                elif e.action == "hand":
                    releases[name].append(e.time)
                    tgt = e.dst[0]
                    catches[tgt].append(e.time)
                    tgt_h = self.juggler[tgt]["height"]
                    arr = self.draw_arrow(dwg, arrow_marker, x, H,
                                          x, tgt_h, css_class="arrow-hand")
                    if arr:
                        dwg.add(arr)
                elif e.action == "zip":
                    releases[name].append(e.time)
                    catches[name].append(e.time)
                    arr = self.draw_arrow(
                        dwg, arrow_marker,
                        x - 0.2 * self.step_X, H, x + 0.2 * self.step_X, H,
                        css_class="arrow-zip")
                    if arr:
                        dwg.add(arr)
                elif e.action == "throw":
                    releases[name].append(e.time)
        # stolen clubs are catches too (throws is the parameter passed
        # in from generate_causal_diagram_svg phase 2, steals applied)
        for t in throws:
            if t.stolen_by:
                catches[t.stolen_by].append(t.steal_time)
        # hold lines: from each catch to the juggler's next release
        for name in self.juggler:
            H = self.juggler[name]["height"]
            rel = sorted(releases[name])
            for c in sorted(catches[name]):
                nxt = [r for r in rel if r > c + 1e-9]
                if not nxt:
                    continue
                dwg.add(dwg.line(
                    start=(self.x_of(c) + self.radius, H),
                    end=(self.x_of(nxt[0]) - self.radius, H),
                    class_="hold-line"))
```

- [ ] **Step 5: Add CSS**

Append to `themes/mytheme/assets/css/custom.css`:

```css
/* steal: intercepted pass */
.arrow-steal {
  stroke: crimson;
  fill: none;
  stroke-width: 2;
  stroke-dasharray: 6 3;
}

/* hand-in / take: club placed directly into a hand */
.arrow-hand {
  stroke: teal;
  fill: none;
  stroke-width: 2;
}

/* zip: own hand to own hand */
.arrow-zip {
  stroke: grey;
  fill: none;
  stroke-width: 1.5;
}

/* carrying a club between a catch and the next release */
.hold-line {
  stroke: grey;
  stroke-width: 1.5;
  opacity: 0.5;
}
```

- [ ] **Step 6: Run tests, verify old pages unchanged**

Run: `uv run pytest tests/ -v` — all PASS.
Then the Task 1 Step 6 hash check: plain diagrams must be byte-identical.
The refactor changes how arrows are generated, so element *order* inside the
SVG may differ even when geometry is identical. If the hash differs, diff one
page (`diff <(git stash? no) ...`) — practical method: `cp -r output /tmp/out-before`
before starting the task, rebuild after, and
`diff -r /tmp/out-before output | head -50`. Reorder the drawing phases
(circles first, then arrows, matching the old interleaved order is NOT
required) — if only ordering inside the SVG changed and the rendered result
is visually identical, accept it, note it in the commit message, and update
the stored hash baseline for later tasks.

- [ ] **Step 7: Commit**

```bash
git add plugins/causal_diagram/causal_diagram.py themes/mytheme/assets/css/custom.css tests/test_render.py
git commit -m "causal diagram: render steals, hand-ins, zips, and hold lines"
```

---

### Task 5: position-diagram rendering of events

**Files:**
- Modify: `plugins/causal_diagram/causal_diagram.py` (`generate_position_diagram_svg`, new hand-position helper)
- Test: `tests/test_render.py` (extend)

**Interfaces:**
- Consumes: `Throw`, `collect_throws`, `apply_steals`, `collect_events` (Tasks 3–4); existing `get_juggler_position(name, t)`, `draw_animated_arrow(...)`.
- Produces: `get_hand_position(name: str, time: float, hand: str) -> tuple[float, float]` — like `get_juggler_hand_position` but with an explicit `"R"`/`"L"` instead of cycling `letters`. Task 6 reuses it for label placement.

- [ ] **Step 1: Write failing test**

Append to `tests/test_render.py`:

```python
ROUNDABOUT_WITH_POSITIONS = (
    "3b 3 3 3\n"
    "3a 3 3 3\n"
    "(RL 1) (3: 0 steal a>L; 0.25 hand R>bL; 0.5 zip L>R)\n"
    "position A: -100, 0, @B\n"
    "position B: 100, 0, @A\n"
    "position C: 0, 40, @0\n"
)


def test_position_diagram_animates_event_arrows():
    svg = render(ROUNDABOUT_WITH_POSITIONS)
    # split output: causal + position SVGs; the position part must contain
    # animated steal and hand arrows too
    position_part = svg.split("position-diagram-section")[1]
    assert "arrow-steal" in position_part
    assert "arrow-hand" in position_part
    assert "arrow-zip" in position_part
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_render.py -v`
Expected: FAIL (event arrows absent from the position SVG; may also crash in the old pass loop when it hits a dict token — that crash is what this task fixes).

- [ ] **Step 3: Implement**

(a) The explicit-hand helper (near `get_juggler_hand_position`, same math with `hand` passed in):

```python
    def get_hand_position(self, name: str, time, hand: str):
        """X,Y of a specific hand (R/L), relative to the position center."""
        x, y, angle = self.get_juggler_position(name, time)
        angle = math.radians(angle)
        delta = math.radians(15)
        if hand == "R":
            X = x + self.radius * 1.6 * math.cos(-(angle + delta))
            Y = y - self.radius * 1.6 * math.sin(-(angle + delta))
        else:
            X = x + self.radius * 1.6 * math.cos(-(angle - delta))
            Y = y - self.radius * 1.6 * math.sin(-(angle - delta))
        return X, Y
```

Refactor `get_juggler_hand_position` to delegate (DRY):

```python
    def get_juggler_hand_position(self, name, time, pass_delay):
        hands = self.juggler[name]["letters"]
        idx = round(time + pass_delay) % len(hands)
        return self.get_hand_position(name, time, hands[idx])
```

(b) In `generate_position_diagram_svg`, replace the arrows section (the
`for j in self.juggler:` loop over `self.juggler[j]["pattern"]`) with a
Throw/Event based version:

```python
        # the arrows in the position diagram
        throws = self.collect_throws()
        self.apply_steals(throws)
        repeats = max(1, int(self.duration_position // self.duration_pattern))
        for r in range(repeats):
            shift = r * self.duration_pattern
            for t in throws:
                if t.target == t.juggler and not t.stolen_by:
                    continue  # selves are not drawn (existing behavior)
                start = self.get_juggler_hand_position(t.juggler, shift + t.time, 0)
                if t.stolen_by:
                    end_t = shift + t.steal_time
                    # steal event knows the catching hand; find it
                    hand = self.steal_catch_hand(t)
                    end = self.get_hand_position(t.stolen_by, end_t, hand or "L")
                    style = "arrow-steal"
                else:
                    end_t = shift + t.arrival
                    wait_a = self.juggler[t.juggler]["wait"]
                    wait_b = self.juggler[t.target]["wait"]
                    end = self.get_juggler_hand_position(
                        t.target, shift + t.time, t.value - 2 - wait_b + wait_a)
                    style = t.style
                arrow = self.draw_animated_arrow(
                    dwg, arrow_marker, start[0], start[1], end[0], end[1],
                    shift + t.time, end_t, css_class=style)
                if arrow:
                    dwg.add(arrow)
            for name in self.juggler:
                for e in self.collect_events(name):
                    self.draw_position_event(dwg, arrow_marker, name, e, shift)
```

(c) The two helpers:

```python
    def steal_catch_hand(self, throw) -> str | None:
        """The hand a stolen throw is caught with (from the steal event)."""
        for e in self.collect_events(throw.stolen_by):
            if e.action == "steal" and e.src[0] == throw.juggler \
               and abs(e.time - throw.steal_time) < 1e-9:
                return e.dst[1]
        return None

    def draw_position_event(self, dwg, arrow_marker, name, e, shift):
        """Animated arrow for hand / take / zip at its absolute time."""
        t = shift + e.time
        window = 0.5  # arrows are visible for half a beat before the transfer
        if e.action == "hand":
            start = self.get_hand_position(name, t, e.src[1] or "R")
            end = self.get_hand_position(e.dst[0], t, e.dst[1] or "L")
            style = "arrow-hand"
        elif e.action == "steal" and e.src[1] is not None:  # take
            start = self.get_hand_position(e.src[0], t, e.src[1])
            end = self.get_hand_position(name, t, e.dst[1] or "L")
            style = "arrow-hand"
        elif e.action == "zip":
            start = self.get_hand_position(name, t, e.src[1] or "L")
            end = self.get_hand_position(name, t, e.dst[1] or "R")
            style = "arrow-zip"
        else:
            return  # steal-from-air handled via Throw; throw via collect_throws
        arrow = self.draw_animated_arrow(
            dwg, arrow_marker, start[0], start[1], end[0], end[1],
            max(0, t - window), t, css_class=style)
        if arrow:
            dwg.add(arrow)
```

Note: `draw_animated_arrow` requires `start_time < end_time` for valid SMIL
keyTimes; the `max(0, t - window)` guard plus `t > 0` for all real events
keeps that true. If an event sits at absolute time 0, the arrow shows from 0
to 0 — guard with `if end_t <= start_t: start_t = max(0, end_t - 0.1)`.

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/ -v`
Expected: all PASS.

- [ ] **Step 5: Verify visually**

```bash
uv run nikola build && uv run nikola serve --port 8123 &
```

Open `http://localhost:8123/patterns/causal-diagrams/` — existing animations must look unchanged. Kill the server afterwards. (A test page with the new syntax comes in Task 8; for a quick manual check, paste `ROUNDABOUT_WITH_POSITIONS` into any pattern page locally without committing.)

- [ ] **Step 6: Commit**

```bash
git add plugins/causal_diagram/causal_diagram.py tests/test_render.py
git commit -m "causal diagram: animate steals, hand-ins, and zips in the position diagram"
```

---

### Task 6: arrow labels

**Files:**
- Modify: `plugins/causal_diagram/causal_diagram.py` (quote-aware `logical_lines` + `tokenize_pattern`, label split, rendering in both diagrams)
- Modify: `themes/mytheme/assets/css/custom.css` (`.arrow-label`)
- Test: `tests/test_labels.py` (create)

**Interfaces:**
- Consumes: `logical_lines`, `tokenize_pattern`, `parse_event`, `Throw`, `Event` (all earlier tasks).
- Produces: module-level `split_label(token: str) -> tuple[str, str | None]` — strips a trailing `"..."` from a token. `Throw.label` and `Event.label` get populated; `draw_arrow` and `draw_animated_arrow` gain an optional `label=None` parameter.

- [ ] **Step 1: Write failing tests**

Create `tests/test_labels.py`:

```python
from causal_diagram import (
    CausalDiagramSVG,
    logical_lines,
    parse_event,
    split_label,
    tokenize_pattern,
)


def render(data):
    out, _ = CausalDiagramSVG().handler(data=data)
    return out


def test_split_label():
    assert split_label('3b"lofty"') == ("3b", "lofty")
    assert split_label('4.5p$"early"') == ("4.5p$", "early")
    assert split_label("3b") == ("3b", None)


def test_label_may_contain_spaces():
    assert split_label('3b"very lofty"') == ("3b", "very lofty")
    toks = tokenize_pattern('3b"very lofty" 3 3')
    assert toks == ['3b"very lofty"', "3", "3"]


def test_hash_inside_quotes_is_not_comment():
    lines = logical_lines('3b"throw #2" 3\n3 3')
    assert lines == ['3b"throw #2" 3', "3 3"]


def test_event_label():
    e = parse_event('0 steal b>L "chop"')
    assert e.label == "chop"


def test_label_rendered_in_causal_svg():
    svg = render('3b"lofty" 3 3\n3a 3 3')
    assert "arrow-label" in svg
    assert ">lofty<" in svg


def test_label_animated_in_position_svg():
    svg = render(
        '3b"lofty" 3 3\n3a 3 3\n'
        "position A: -100, 0, @B\nposition B: 100, 0, @A\n"
    )
    pos = svg.split("position-diagram-section")[1]
    assert "arrow-label" in pos and ">lofty<" in pos
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_labels.py -v`
Expected: FAIL with ImportError (`split_label`).

- [ ] **Step 3: Make the tokenizer and comment stripping quote-aware**

(a) `split_label` (module level):

```python
def split_label(token: str) -> tuple:
    """ '3b"lofty"' -> ("3b", "lofty"); no label -> (token, None). """
    if token.endswith('"') and token.count('"') >= 2:
        head, _, rest = token[:-1].partition('"')
        return head, rest
    return token, None
```

(b) In `logical_lines`, replace the `if "#" in raw: raw = raw.split("#")[0]` with a scan that ignores `#` inside quotes:

```python
        in_quote = False
        for i, ch in enumerate(raw):
            if ch == '"':
                in_quote = not in_quote
            elif ch == "#" and not in_quote:
                raw = raw[:i]
                break
```

(c) In `tokenize_pattern`, track quotes so spaces inside labels don't split and parens inside quotes don't count:

```python
def tokenize_pattern(line: str) -> list[str]:
    tokens, cur, depth = [], "", 0
    in_quote = False
    for ch in line:
        if ch == '"':
            in_quote = not in_quote
        elif not in_quote:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
        if ch.isspace() and depth == 0 and not in_quote:
            if cur:
                tokens.append(cur)
            cur = ""
        else:
            cur += ch
    if cur:
        tokens.append(cur)
    return tokens
```

(d) In `parse_event`, pull a trailing quoted label off before splitting fields:

```python
def parse_event(text: str) -> Event:
    text = text.strip()
    label = None
    if text.endswith('"'):
        text, _, rest = text[:-1].rpartition('"')
        label = rest
        text = text.strip()
    parts = text.split()
    ...  # unchanged, but pass label=label into every Event(...) constructor
```

(e) In `collect_throws` (both the grid-token branch and the throw-event branch), call `split_label` **before** `get_style` and store the label:

```python
                tok, label = split_label(tok)
                tok2, style = self.get_style(tok)
                ...
                throws.append(Throw(..., label=label))
```

Also strip labels in the phase-1 circle loop of `generate_causal_diagram_svg` (a labeled token is still one beat: `tok, _ = split_label(tok)` before the `tok == "-"` check).

- [ ] **Step 4: Render labels**

(a) `draw_arrow(..., label=None)`: after computing start/end (and before returning), when `label` is set wrap arrow + text in a group:

```python
        # at the end of draw_arrow, replace the two `return dwg...` with
        # building `element` first, then:
        if label and element is not None:
            group = dwg.g()
            group.add(element)
            mid_x = (start_x + end_x) / 2
            mid_y = (start_y + end_y) / 2 - 8
            if abs(end_x - start_x) - self.step_X > 10 and dy == 0:
                mid_y -= self.step_Y / 4   # bezier arcs bulge upward
            group.add(dwg.text(label, insert=(mid_x, mid_y),
                               class_="arrow-label", text_anchor="middle"))
            return group
        return element
```

(b) `draw_animated_arrow(..., label=None)`: when set, build a `dwg.text` at the midpoint with `class_="arrow-label"`, attach a `svgwrite.animate.Animate` with **the same `values`/`keyTimes`/`dur`** as the line's opacity animation, and return a group of both.

(c) Pass `label=t.label` at both call sites in phase 2 of `generate_causal_diagram_svg` and in the position-diagram throw loop, and `label=e.label` in `draw_causal_events` / `draw_position_event`.

(d) CSS:

```css
/* text next to an arrow */
.arrow-label {
  font-size: 0.75em;
  fill: #555;
}
```

- [ ] **Step 5: Run all tests, hash-check the site**

Run: `uv run pytest tests/ -v` — all PASS.
Rebuild and compare against the Task 4/5 baseline: pages without labels must be unchanged.

- [ ] **Step 6: Commit**

```bash
git add plugins/causal_diagram/causal_diagram.py themes/mytheme/assets/css/custom.css tests/test_labels.py
git commit -m "causal diagram: arrow labels (quoted text next to arrows)"
```

---

### Task 7: `swap:` role-based rotation

**Files:**
- Modify: `plugins/causal_diagram/causal_diagram.py`
- Test: `tests/test_swap.py` (create)

**Interfaces:**
- Consumes: `Throw`, `Event`, `collect_throws`, `collect_events` (Tasks 3–4).
- Produces:
  - module-level `parse_swap(line: str) -> list[list[str]]` — `"swap: A->B->C, D->E"` → `[["A","B","C"], ["D","E"]]`.
  - `Circle` dataclass: `juggler: str, time: float, label: str, css_class: str | None` — one causal-diagram circle.
  - `CausalDiagramSVG.collect_circles(self) -> list[Circle]` — the circle schedule (grid hands, empty beats, event hands).
  - **Pipeline change:** `parse()` ends by precomputing `self.throws`, `self.circles`, `self.events` (dict name → list[Event]) and, when a swap line was seen, transforming them via `unroll_swap()`; `apply_steals(self.throws)` runs last. The renderers (Tasks 4–5 code) switch from calling `collect_*` to reading these attributes.

- [ ] **Step 1: Write failing tests**

Create `tests/test_swap.py`:

```python
from causal_diagram import CausalDiagramSVG, parse_swap


def test_parse_swap():
    assert parse_swap("swap: A->B->C, D->E") == [["A", "B", "C"], ["D", "E"]]


def make(text):
    d = CausalDiagramSVG()
    d.parse(text)
    return d


def test_two_role_swap_unrolls_two_periods():
    d = make("swap: A->B\n3b 3\n3a 3")
    # period 2 beats, cycle length 2 -> total 4 beats per person
    assert d.duration_pattern == 4
    a_throws = sorted(
        [t for t in d.throws if t.juggler == "A"], key=lambda t: t.time
    )
    assert [t.time for t in a_throws] == [0, 1, 2, 3]
    # period 0: person A plays role A -> pass to person doing role B (=B)
    assert a_throws[0].target == "B"
    # period 1: person A plays role B -> its "3a" targets role A,
    # whose occupant in period 1 is person B
    assert a_throws[2].target == "B"


def test_swap_remaps_event_endpoints():
    d = make(
        "swap: A->B\n"
        "3 3\n"
        "(1: 0.5 hand R>aL) -\n"
    )
    b_events = d.events["B"]
    # period 0: person B in role B hands to role A -> person A
    assert b_events[0].dst[0] == "A"
    # period 1: person B in role A runs role A's line (no events);
    # person A in role B hands to role A -> occupant is person B
    a_events = d.events["A"]
    assert a_events[0].dst[0] == "B"
    assert a_events[0].time == 2.5


def test_swap_concatenates_positions():
    d = make(
        "swap: A->B\n"
        "3b 3\n"
        "3a 3\n"
        "position A: 0, -100, 0, 0; 2, 100, 0, 180;\n"
        "position B: 0, 100, 0, 180; 2, -100, 0, 0;\n"
    )
    # person A: role A's path (period 0) then role B's path (period 1)
    pos = d.juggler["A"]["position"]
    # keyframe times are normalized to [0,1] by parse; last raw beat was 4
    assert pos[0][0] == 0.0 and pos[-1][0] == 1.0
    assert len(pos) == 4


def test_no_swap_line_changes_nothing():
    d = make("3b 3 3\n3a 3 3")
    assert d.duration_pattern == 3
    assert len(d.throws) == 6
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_swap.py -v`
Expected: FAIL (`parse_swap` missing; `d.throws` attribute missing).

- [ ] **Step 3: Implement the pipeline change**

(a) Module level:

```python
def parse_swap(line: str) -> list:
    chains = []
    for chain in line.removeprefix("swap:").split(","):
        chains.append([r.strip().upper() for r in chain.split("->") if r.strip()])
    return chains


@dataclass
class Circle:
    juggler: str
    time: float          # absolute beat (includes wait)
    label: str           # hand letter, "" for empty beats
    css_class: str | None = None
```

(b) `collect_circles` — extract phase 1 of `generate_causal_diagram_svg`
(Task 4) into a record producer; the renderer loop then just draws
`self.circles`:

```python
    def collect_circles(self) -> list:
        circles = []
        for name, juggler in self.juggler.items():
            beat = 0.0
            letter_idx = 0
            letters = juggler["letters"]
            for tok in juggler["pattern"]:
                t = juggler["wait"] + beat
                if isinstance(tok, dict):
                    for e in tok["events"]:
                        hand = self.event_circle_hand(e)
                        if hand is not None:
                            circles.append(Circle(name, t + e.time, hand))
                    beat += tok["beats"]
                    letter_idx += int(round(tok["beats"]))
                elif split_label(tok)[0] == "-":
                    circles.append(Circle(name, t, "", "beat-empty"))
                    beat += 1
                    letter_idx += 1
                else:
                    circles.append(
                        Circle(name, t, letters[letter_idx % len(letters)]))
                    beat += 1
                    letter_idx += 1
        return circles
```

(c) In `parse`: recognize the swap line in the dispatch
(`elif line.startswith("swap:"): self.swap_chains = parse_swap(line)`;
initialize `self.swap_chains = None` in `__init__`). At the end of
`parse`, **before** the position rescaling block, add:

```python
        self.throws = self.collect_throws()
        self.circles = self.collect_circles()
        self.events = {name: self.collect_events(name) for name in self.juggler}
        if self.swap_chains:
            self.unroll_swap()
        self.apply_steals(self.throws)
```

and change `self.duration_pattern = max(...)` to run before this block
(unroll_swap multiplies it). Renderer call sites from Tasks 4–5 change:
`generate_causal_diagram_svg` phase 1 iterates `self.circles`
(`x = self.x_of(c.time)`, row from `self.juggler[c.juggler]["height"]`),
phase 2 iterates `self.throws` (no collect/apply there anymore), and
`draw_causal_events` / the position loops read `self.events[name]` and
`self.throws`.

(d) `unroll_swap`:

```python
    def unroll_swap(self):
        import math as _math
        period = self.duration_pattern
        chains = self.swap_chains
        cycle_lengths = [len(c) for c in chains] or [1]
        cycles = _math.lcm(*cycle_lengths)

        chain_of = {}
        for chain in chains:
            for i, role in enumerate(chain):
                chain_of[role] = (chain, i)

        def role_at(person, k):
            if person not in chain_of:
                return person
            chain, i = chain_of[person]
            return chain[(i + k) % len(chain)]

        def occupant(role, k):
            if role not in chain_of:
                return role
            chain, i = chain_of[role]
            return chain[(i - k) % len(chain)]

        def remap(juggler_letter, absolute_time):
            k = int(absolute_time // period) % cycles
            return occupant(juggler_letter, k)

        by_role_throws = {}
        by_role_circles = {}
        for name in self.juggler:
            by_role_throws[name] = [t for t in self.throws if t.juggler == name]
            by_role_circles[name] = [c for c in self.circles if c.juggler == name]

        throws, circles, events = [], [], {n: [] for n in self.juggler}
        positions = {n: [] for n in self.juggler}
        for person in self.juggler:
            for k in range(cycles):
                role = role_at(person, k)
                shift = k * period
                for t in by_role_throws[role]:
                    throws.append(replace(
                        t, juggler=person, time=t.time + shift,
                        target=remap(t.target, t.time + shift + t.value - 2)))
                for c in by_role_circles[role]:
                    circles.append(replace(c, juggler=person, time=c.time + shift))
                for e in self.events.get(role, []):
                    src = (remap(e.src[0], e.time + shift), e.src[1]) \
                        if e.src[0] else e.src
                    dst = (remap(e.dst[0], e.time + shift), e.dst[1]) \
                        if e.dst[0] else e.dst
                    events[person].append(
                        replace(e, time=e.time + shift, src=src, dst=dst))
                role_pos = self.juggler[role].get("position")
                if role_pos:
                    for kf in role_pos:
                        positions[person].append(
                            [kf[0] + shift, kf[1], kf[2], kf[3]])

        self.throws, self.circles, self.events = throws, circles, events
        for person in self.juggler:
            if positions[person]:
                self.juggler[person]["position"] = positions[person]
        self.duration_pattern = period * cycles
```

Notes for the implementer:
- `Throw.target` of a **self** must remap too — a self by role X in period
  k is caught by the same person, and `remap(X, ...)` with the arrival in
  the same period returns the person; near a period boundary a long self
  crossing periods still lands on the same *person* only if the arrival
  remap is skipped for selves. Handle explicitly: `if t.target == t.juggler
  (role-level): target = person`. Add this to the loop before the generic
  remap.
- Steal events inside blocks unroll with `events`; `apply_steals` runs
  after unrolling, so matching happens against unrolled throw times.
  That is why the parse-end block orders unroll before apply_steals.
- Role position keyframes must cover exactly one period (author's
  contract, spec section "Role-based rotation"); duplicate boundary
  keyframes (end of period k == start of k+1) are harmless in SMIL.

- [ ] **Step 4: Run all tests**

Run: `uv run pytest tests/ -v`
Expected: all PASS, including all earlier tasks (the pipeline refactor
touches every renderer).

- [ ] **Step 5: Hash-check the site**

Rebuild; pages without `swap:` must be unchanged from the Task 6 baseline.

- [ ] **Step 6: Commit**

```bash
git add plugins/causal_diagram/causal_diagram.py tests/test_swap.py
git commit -m "causal diagram: role-based rotation via swap: lines"
```

---

### Task 8: documentation page

**Files:**
- Modify: `pages/patterns/causal-diagrams.md`

**Interfaces:**
- Consumes: every feature from Tasks 1–7 (live examples must build).
- Produces: user-facing docs; no code.

- [ ] **Step 1: Append documentation sections**

Add to the end of `pages/patterns/causal-diagrams.md` (keep the existing
raw-block-then-live-example convention used throughout that page):

~~~markdown
# Silent beats

A `-` marks a beat where a juggler does nothing (idle or holding a club).
It renders as a faint dashed circle.

    {{% raw %}}
    {{% causal_diagram %}}
    3 - 3 3
    3 3 3 3
    {{% /causal_diagram %}}
    {{% /raw %}}

{{% causal_diagram %}}
3 - 3 3
3 3 3 3
{{% /causal_diagram %}}

# Steals, hand-ins, and zips

Sparse actions are written in an inline event block
`(<beats>: <time> <action>; ...)` that takes the place of grid tokens.
Times are relative to the start of the block and can be fractional.
Transfers use `source>destination`, each side `[juggler][hand]`, with
your own juggler implied when omitted:

* `steal b>L` — intercept B's club in flight, catch with the left hand
* `steal cR>L` — take the club held in C's right hand
* `hand R>cL` — place your right-hand club into C's left hand
* `zip L>R` — hand-across, own left to own right
* `throw 3a R` — a normal throw at an off-grid time

The victim of a steal writes their line as if the pass were normal — the
steal reroutes the arrow.

    {{% raw %}}
    {{% causal_diagram %}}
    3b 3 3 3
    3a 3 3 3
    (RL 1) (3: 0 steal a>L; 0.25 hand R>bL; 0.5 zip L>R)
    {{% /causal_diagram %}}
    {{% /raw %}}

{{% causal_diagram %}}
3b 3 3 3
3a 3 3 3
(RL 1) (3: 0 steal a>L; 0.25 hand R>bL; 0.5 zip L>R)
{{% /causal_diagram %}}

# Arrow labels

Attach a quoted text to any throw or event and it is drawn next to the
arrow (in both diagrams):

    {{% raw %}}
    {{% causal_diagram %}}
    3b"lofty" 3 3 3
    3a 3 3"chop" 3
    {{% /causal_diagram %}}
    {{% /raw %}}

{{% causal_diagram %}}
3b"lofty" 3 3 3
3a 3 3"chop" 3
{{% /causal_diagram %}}

# Moving patterns: roles and swaps

For patterns where people rotate through positions, write the pattern
lines for the **roles** over one short cycle and add a `swap:` line.
`swap: A->B` means: whoever is doing line A does line B in the next
cycle. The diagram unrolls automatically until everyone is back in
their starting role; rows are labeled by person (named after their
starting role), and pass targets always mean "whoever is in that role".

    {{% raw %}}
    {{% causal_diagram %}}
    swap: A->B
    3b 3 3 3
    3a 3 3 3
    {{% /causal_diagram %}}
    {{% /raw %}}

{{% causal_diagram %}}
swap: A->B
3b 3 3 3
3a 3 3 3
{{% /causal_diagram %}}

# Long lines

Lines can be broken up for readability: a line continues automatically
when a parenthesis is still open or when it ends with `;` (the trailing
`\` also still works). Leading whitespace never matters.
~~~

- [ ] **Step 2: Build and inspect**

```bash
uv run nikola build
```

Expected: zero ERROR lines. Open
`output/patterns/causal-diagrams/index.html` in a browser and check every
new example renders (dashed empty circle, crimson dashed steal arrow, teal
hand arrows, labels, the unrolled 8-beat swap diagram).

- [ ] **Step 3: Commit**

```bash
git add pages/patterns/causal-diagrams.md
git commit -m "patterns: document silent beats, events, labels, and swap notation"
```

---

### Task 9: pattern pages (roundabout diagram, havana via swap)

**Files:**
- Modify: `pages/patterns/roundabout.md`
- Modify: `pages/patterns/havana.md`

**Interfaces:**
- Consumes: all features. No code produced.

- [ ] **Step 1: Add a diagram to roundabout.md**

Insert after the first paragraph of `pages/patterns/roundabout.md`:

```markdown
{{% causal_diagram %}}
title: Roundabout (start; C steals B's pass and feeds A)
3b 3 3 3 3b 3 3 3
3a 3 3 3 3a 3 3 3
(RL 1) (7: 0 steal b>L; 0.25 hand R>aL; 0.5 zip L>R; 4 steal a>R "pelf")
{{% /causal_diagram %}}
```

**The beat timings above are a starting point, not gospel** — they encode:
C steals B's first pass (thrown at beat 0, stolen at absolute beat 1),
immediately hands their right-hand club into A's pattern, zips, and later
steals A's pelf. Build the page, look at the diagram, and adjust
times/hands against the prose description in the same file. Mark anything
you cannot resolve from the prose with a `<!-- TODO(user): verify timing -->`
HTML comment for the site owner rather than guessing silently.

- [ ] **Step 2: Rewrite havana.md with swap notation — verified equivalence**

The current `havana.md` contains the hand-unrolled super-period (four
jugglers, 40 beats, 3 role-cycles). The role form must produce the **same
throw schedule**. Do not eyeball this — compare records:

```bash
uv run python - <<'EOF'
import sys
sys.path.insert(0, "plugins/causal_diagram")
from causal_diagram import CausalDiagramSVG

OLD = """<paste the four pattern lines currently in havana.md>"""
NEW = """swap: <candidate chain>
<first-period role lines>"""

def schedule(text):
    d = CausalDiagramSVG(); d.parse(text)
    return sorted((t.juggler, t.time, t.value, t.target) for t in d.throws)

old, new = schedule(OLD), schedule(NEW)
print("match" if old == new else "MISMATCH")
for a, b in zip(old, new):
    if a != b:
        print(a, "!=", b); break
EOF
```

Derive the candidate: the super-period is 40 beats over what should be 4
periods of 10 (chain length 4) or 2 of 20 (two 2-chains) — slice the
existing lines at those widths and test each slicing with the script until
`match`. If no candidate matches, **leave havana.md unchanged**, keep the
script output in the commit message of a docs-only note, and flag it for
the site owner — do not commit a wrong diagram.

- [ ] **Step 3: Build and visually verify**

```bash
uv run nikola build
```

Open `output/patterns/roundabout/index.html` and
`output/patterns/havana/index.html`; the havana diagram must look
identical to the pre-change build (compare against a screenshot or the
old HTML kept in `/tmp`).

- [ ] **Step 4: Commit**

```bash
git add pages/patterns/roundabout.md pages/patterns/havana.md
git commit -m "patterns: roundabout diagram; havana via swap notation"
```

---

## Verification baseline (applies to every task)

Before Task 1, capture a clean-build baseline once:

```bash
uv run nikola build
cp -r output /tmp/causal-baseline
```

After each task's build, `diff -r /tmp/causal-baseline output | head -50`
must show changes **only** where that task intends them (Tasks 1–3, 6, 7:
no changes at all for existing pages; Task 4 may reorder SVG elements —
see its Step 6; Tasks 8–9 change exactly the two docs/pattern pages).
Refresh the baseline (`cp -r output /tmp/causal-baseline`) after any task
that legitimately changed output.
