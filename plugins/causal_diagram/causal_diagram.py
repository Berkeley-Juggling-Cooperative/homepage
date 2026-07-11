from nikola.plugin_categories import ShortcodePlugin
from dataclasses import dataclass, replace
import hashlib
import io
import math
import re
import svgwrite

# define several CSS classes that can be used for arrow inside the pattern
COLORS = {
    ",": "arrow-red-thick",
    "$": "arrow-red-thin",
    "@": "arrow-orange-dash",
    ">": "arrow-green-dash",
    "<": "arrow-yellow-dash",
    "^": "arrow-blue-dash",
    "*": "arrow-purple-dash",
}


def logical_lines(text: str) -> list[str]:
    """Split shortcode text into logical lines.

    A logical line continues onto the next physical line while it has
    an unclosed "(" (event blocks spanning lines). A trailing "\\"
    forces continuation (legacy syntax, e.g. long position lines).
    Leading whitespace is insignificant (pages indent cosmetically),
    and a trailing "," or ";" must NOT continue: "," is a color
    suffix, and complete position lines conventionally end with ";".
    """
    lines = []
    current = ""
    glue_next = False  # previous physical line ended with "\"
    for raw in text.split("\n"):
        # strip comments, but a '#' inside a quoted label is content
        in_quote = False
        for i, ch in enumerate(raw):
            if ch == '"':
                in_quote = not in_quote
            elif ch == "#" and not in_quote:
                raw = raw[:i]
                break
        raw = raw.strip()
        if raw.endswith("\\"):
            # legacy continuation: joins without spaces, exactly as before
            raw = raw[:-1].strip()
            if current and raw and not glue_next:
                current += " " + raw
            else:
                current += raw
            glue_next = True
            continue
        if current and raw and not glue_next:
            current += " " + raw
        else:
            current += raw
        glue_next = False
        if not current:
            continue
        if current.count("(") > current.count(")"):
            continue
        lines.append(current)
        current = ""
    if current:
        lines.append(current)
    return lines


def parse_swap(line: str) -> list:
    """ "swap: A->B->C, D->E" -> [["A", "B", "C"], ["D", "E"]].

    After each period the person doing a role's line does the next
    role's line in the chain (the last role wraps to the first).
    """
    chains = []
    for chain in line.removeprefix("swap:").split(","):
        chains.append([r.strip().upper() for r in chain.split("->") if r.strip()])
    return [c for c in chains if c]


@dataclass
class Circle:
    """One circle (hand marker) in the causal diagram."""

    juggler: str
    time: float          # absolute beat (includes wait)
    label: str           # hand letter, "" for empty beats
    css_class: str | None = None


def split_label(token: str) -> tuple:
    """ '3b"lofty"' -> ("3b", "lofty"); no label -> (token, None). """
    if token.endswith('"') and token.count('"') >= 2:
        head, _, rest = token[:-1].partition('"')
        return head, rest
    return token, None


@dataclass
class Event:
    """One sparse action inside an event block.

    src/dst are (juggler, hand) endpoints; juggler None means "self".
    """

    time: float
    action: str
    src: tuple = (None, None)
    dst: tuple = (None, None)
    value: str | None = None
    hand: str | None = None
    label: str | None = None


@dataclass
class Throw:
    """One throw in the causal diagram (a grid token or a 'throw' event)."""

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


def tokenize_pattern(line: str) -> list[str]:
    """Whitespace split keeping (...) groups and "..." labels intact."""
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
    text = text.strip()
    # pull a trailing quoted label off before splitting fields
    label = None
    if text.endswith('"'):
        text, _, rest = text[:-1].rpartition('"')
        label = rest
        text = text.strip()
    parts = text.split()
    time = float(parts[0])
    action = parts[1]
    if action == "throw":
        return Event(time=time, action="throw", value=parts[2],
                     hand=parts[3] if len(parts) > 3 else None,
                     label=label)
    if action == "catch":
        # marks the receiving hand of an incoming pass (only needed for
        # jugglers without grid circles at that beat)
        return Event(time=time, action="catch",
                     hand=parts[2] if len(parts) > 2 else None,
                     label=label)
    if action not in ("steal", "hand", "zip"):
        raise ValueError(f"unknown event action: {action!r}")
    src, dst = parts[2].split(">")
    return Event(time=time, action=action,
                 src=parse_endpoint(src), dst=parse_endpoint(dst),
                 label=label)


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


class CausalDiagramSVG(ShortcodePlugin):
    """A simple script/shortcode to display causal diagrams.

    The syntax of the diagrams was adapted from:
    https://www.jugglingedge.com/help/causaldiagrams.php

    and then modified to allow for SVG animations.
    """

    name = "causal_diagram"

    juggler_names = "ABCDEFGHIJKLMN"
    margin = 10
    radius = 12

    title_height = 25

    # hold lines only mark short carries (catch to release); longer
    # holds would clutter the diagram
    hold_line_max = 1.5

    def __init__(self):
        super().__init__()
        self.juggler = {}
        self.title = ""
        self.diagram_id = ""
        self.bars = []
        self.duration_position = 0
        self.duration_pattern = 0
        self.step_X = 80
        self.step_Y = 100
        self.swap_chains = None
        self.snapshots = []
        # precomputed by parse(): the drawing records the renderers use
        self.throws = []
        self.circles = []
        self.events = {}

    def handler(self, site=None, data=None, lang=None, post=None):
        """This gets executed for the shortcode.

        Nikola keeps one plugin instance around, so we parse each
        diagram on a fresh instance to avoid state leaking between
        diagrams.
        """
        diagram = CausalDiagramSVG()
        diagram.parse(data)
        return diagram.to_svg(), []


    def parse_title(self, line: str) -> None:
        self.title = line[6:].strip()

    def parse_bars(self, line: str) -> None:
        self.bars = [float(x) for x in line[5:].split(",")]

    def parse_position(self, line):
        r"""Parses positions.

        This can be static or include multiple locations for walking patterns.

        Especially for static positions, we allow shortcuts that will
        create positions for all known jugglers (so this should be
        defined after the pattern).

        Currently we support:
        * circle (equidistance on a circle, facing the center)
        * line (two vertical lines, offset for odd numbers, facing across)

        Otherwise, the position needs to include the name of a juggle (A, B, C, ...) and
        have either 2 (x and y), 3 (x, y, angle), or 4 value (time, x, y, angle).

        The time should start at 0 and end in the same value for all jugglers.
        Internally the time is then later scaled to a value between 0 and 1.

        The angle is in degree or can define a location of the center
        (@0) or of a juggler (@A, @B. ,etc.)

        Valid positions lines:

        positions: line
        positions: circle

        position A:  0,-100,   0, @B;\  # feeding
                     2,-100,   0, @C;

        """

        if line.startswith("positions:"):
            line = line.removeprefix("positions:")
            line = line.strip()
            N = len(self.juggler)
            if line == "circle":
                for i, j in enumerate(self.juggler.values()):
                    j["position"] = [
                        [
                            0,
                            100 * math.cos(-2 * math.pi / N * i + math.pi),
                            -100 * math.sin(-2 * math.pi / N * i + math.pi),
                            360 / N * i,
                        ]
                    ]
            elif line == "line":
                left = N // 2
                right = N - left
                start_left = -50 * (left - 1)
                start_right = -50 * (right - 1)
                left_count = 0
                right_count = 0
                for i, j in enumerate(self.juggler.values()):
                    if i % 2:
                        j["position"] = [[0, -100, start_left + 100 * left_count, 0]]
                        left_count += 1
                    else:
                        j["position"] = [[0, 100, start_right + 100 * right_count, 180]]
                        right_count += 1
            return

        line = line.removeprefix("position")
        name, values = line.split(":")
        name = name.strip()
        # an optional role label: position A("feeder"): ...
        role_label = None
        m = re.match(r'^(\w+)\s*\(\s*"([^"]*)"\s*\)$', name)
        if m:
            name, role_label = m.group(1), m.group(2)
        values = values.split(";")
        tmp = []
        for v in values:
            v = v.strip()
            if not v:
                continue
            t = v.split(",")
            # these should be 2-4 numbers: time, x, y, angle
            # time should be in beats
            # if there are only 2, we assume: x,y
            # for 3 we assume, x,y,angle
            # if there are less numbers than 4
            #   we add 0 for time and 0 for angle
            if len(t) == 2:
                t = [0, float(t[0]), float(t[1]), 0]
            elif len(t) == 3:
                t = [0, float(t[0]), float(t[1]), t[2]]
            elif len(t) == 4:
                t = [float(t[0]), float(t[1]), float(t[2]), t[3].strip()]
            tmp.append(t)

        self.juggler[name]["position"] = tmp
        if role_label:
            self.juggler[name]["role_label"] = role_label

    def calc_angle(self):
        """The angle can either be a number or a string.

        If the string starts with "@", then the angle is calculated
        from the position of the juggler and to either the origin (@0)
        or to another juggler (e.g., @A). Otherwise, we assume it's a
        number which will be the orientation direclty in degrees:
          0 = looking to the right
        180 = looking to the left
         90 = ...
        270 = ...

        The angle specification can end with "!" to force the long rotation
        path (e.g., @A! or @B!). By default, we always take the shortest path.

        """
        for j in self.juggler:
            if "position" not in self.juggler[j]:
                continue
            tmp = self.juggler[j]["position"]
            out = []
            use_long_rotation = []  # Track which transitions should use long path

            for t in tmp:
                use_long = False
                if isinstance(t[3], str) and "@" in t[3]:
                    angle_spec = t[3].strip()
                    # Check for ! flag
                    if angle_spec.endswith("!"):
                        use_long = True
                        angle_spec = angle_spec[:-1]  # Remove the !

                    name = angle_spec[1]  # Character after @
                    Ax, Ay = self.get_juggler_position_only(j, t[0])
                    if name == "0":
                        Bx, By = 0, 0
                    else:
                        Bx, By = self.get_juggler_position_only(name, t[0])
                    angle = math.atan2(Ay - By, Ax - Bx)
                    angle = math.degrees(angle) + 180
                    if angle < -180:
                        angle += 360
                    if angle > 180:
                        angle -= 360
                    t[3] = float(angle)
                else:
                    t[3] = float(t[3])

                out.append(t)
                use_long_rotation.append(use_long)

            # Normalize angles to take shortest path (or longest if flagged)
            for i in range(1, len(out)):
                prev_angle = out[i - 1][3]
                curr_angle = out[i][3]

                # Calculate the angular difference
                diff = curr_angle - prev_angle

                # Normalize to [-180, 180] for shortest path
                while diff > 180:
                    diff -= 360
                while diff < -180:
                    diff += 360

                # If ! flag is set, invert to take the long path
                if use_long_rotation[i]:
                    if diff > 0:
                        diff -= 360
                    else:
                        diff += 360

                # Update the current angle to ensure smooth transition
                out[i][3] = prev_angle + diff

            self.juggler[j]["position"] = out

    def parse_pattern(self, line: str) -> None:
        """This is the actual pattern.

        passes are indicated with a lower case letter corresponding to
        the name of the juggler who will catch the pass.

        If there are only two jugglers in the pattern, the letter 'p'
        for pass can also be used.

        Furthermore, colors can be indicated for the pass to highlight
        it (see the global COLORS variable).

        """
        # get new name
        n = len(self.juggler)
        juggler_name = self.juggler_names[n]
        tmp = {}
        tokens = tokenize_pattern(line)
        # parse extra information in () at the start; a "(" group with a
        # ":" is an event block, not the hands/wait prefix
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
        # 'p' for passes are only allowed in 2 person patterns
        # otherwise it should be letters. Replace 'p' with 'a' and 'b'
        # here so that it is easier later in the program. Quoted labels
        # must not be touched (e.g. 3"pelf").
        def replace_p(tok, other):
            head, label = split_label(tok)
            head = head.replace("p", other)
            return f'{head}"{label}"' if label is not None else head

        if any(isinstance(t, str) and "p" in split_label(t)[0] for t in pattern):
            other = "b" if juggler_name == "A" else "a"
            pattern = [replace_p(t, other) if isinstance(t, str) else t
                       for t in pattern]
        tmp["pattern"] = pattern
        # the y-coordinate the juggler line should be drawn in the diagram
        tmp["height"] = self.margin + int(self.step_Y * (n + 0.5))
        self.juggler[juggler_name] = tmp

    def x_of(self, t: float) -> float:
        """Causal-diagram x coordinate for an absolute beat time."""
        return 2 * self.margin + self.step_X * (1 + t)

    def split_throw_token(self, name: str, tok: str) -> tuple:
        """A grid token -> (value, target, style)."""
        tok2, style = self.get_style(tok)
        try:
            value = float(tok2)
            target = name
        except ValueError:
            target = tok2[-1].upper()
            value = float(tok2[:-1])
        return value, target, style

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
                    # hands keep alternating per beat while events happen
                    letter_idx += int(round(tok["beats"]))
                    continue
                tok, label = split_label(tok)
                if tok == "-":
                    beat += 1
                    letter_idx += 1
                    continue
                value, target, style = self.split_throw_token(name, tok)
                throws.append(
                    Throw(
                        juggler=name,
                        time=juggler["wait"] + beat,
                        value=value,
                        target=target,
                        style=style,
                        hand=letters[letter_idx % len(letters)],
                        label=label,
                    )
                )
                beat += 1
                letter_idx += 1
            for e in self.collect_events(name):
                if e.action == "throw":
                    value, target, style = self.split_throw_token(name, e.value)
                    throws.append(
                        Throw(juggler=name, time=e.time, value=value,
                              target=target, style=style, hand=e.hand or "",
                              label=e.label)
                    )
        return throws

    def collect_circles(self) -> list:
        """The circle (hand marker) schedule for the causal diagram."""
        circles = []
        for name, juggler in self.juggler.items():
            beat = 0.0
            letter_idx = 0
            letters = juggler["letters"]
            for tok in juggler["pattern"]:
                t = juggler["wait"] + beat
                if isinstance(tok, dict):
                    for e in tok["events"]:
                        if e.action == "zip":
                            # half a beat from one hand to the other
                            circles.append(
                                Circle(name, t + e.time, e.src[1] or "L"))
                            circles.append(
                                Circle(name, t + e.time + 0.5, e.dst[1] or "R"))
                            continue
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

    def unroll_swap(self):
        """Unroll role-based lines into per-person records.

        The written lines describe roles for one period; `swap:` says
        who moves to which role after each period. We repeat the role
        records until everyone is back in their starting role, mapping
        role letters to the person occupying them at the relevant time.
        Persons are named after their starting role.
        """
        period = self.duration_pattern
        chains = self.swap_chains
        cycles = math.lcm(*[len(c) for c in chains]) if chains else 1

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

        def remap(role_letter, absolute_time):
            k = int(absolute_time // period) % cycles
            return occupant(role_letter, k)

        by_role_throws = {n: [] for n in self.juggler}
        for t in self.throws:
            by_role_throws[t.juggler].append(t)
        by_role_circles = {n: [] for n in self.juggler}
        for c in self.circles:
            by_role_circles[c.juggler].append(c)

        throws, circles = [], []
        events = {n: [] for n in self.juggler}
        positions = {n: [] for n in self.juggler}
        labels = {n: [] for n in self.juggler}
        for person in self.juggler:
            for k in range(cycles):
                role = role_at(person, k)
                shift = k * period
                role_label = self.juggler[role].get("role_label")
                if role_label:
                    labels[person].append((shift, shift + period, role_label))
                for t in by_role_throws[role]:
                    if t.target == role:
                        # a self stays with the person who threw it
                        target = person
                    else:
                        target = remap(t.target, t.time + shift + t.value - 2)
                    throws.append(replace(
                        t, juggler=person, time=t.time + shift, target=target))
                for c in by_role_circles[role]:
                    circles.append(replace(c, juggler=person, time=c.time + shift))
                for e in self.events.get(role, []):
                    src = ((remap(e.src[0], e.time + shift), e.src[1])
                           if e.src[0] else e.src)
                    dst = ((remap(e.dst[0], e.time + shift), e.dst[1])
                           if e.dst[0] else e.dst)
                    events[person].append(
                        replace(e, time=e.time + shift, src=src, dst=dst))
                role_pos = self.juggler[role].get("position")
                # a path longer than one period cannot be a role path;
                # leave it untouched as a per-person path (e.g. Havana,
                # where the feeder feeds from wherever they stand)
                if role_pos and role_pos[-1][0] <= period:
                    for kf in role_pos:
                        angle = kf[3]
                        # facing references name roles: point them at
                        # the person occupying the role this period
                        if isinstance(angle, str) and angle.strip().startswith("@"):
                            spec = angle.strip()
                            bang = "!" if spec.endswith("!") else ""
                            ref = spec.rstrip("!")[1:]
                            if ref != "0":
                                angle = "@" + occupant(ref.upper(), k) + bang
                        positions[person].append(
                            [kf[0] + shift, kf[1], kf[2], angle])

        self.throws, self.circles, self.events = throws, circles, events
        for person in self.juggler:
            if positions[person]:
                self.juggler[person]["position"] = positions[person]
            if labels[person]:
                # the role label follows the role, not the person
                self.juggler[person]["role_labels"] = labels[person]
        self.duration_pattern = period * cycles

    def apply_steals(self, throws: list) -> None:
        """Match steal events to in-flight throws and reroute them.

        A steal (src hand is None) matches a throw by the source juggler
        that is in the air at the event time; if several match, the one
        whose arrival is nearest. Takes (src hand set) grab a held club
        and do not touch the throw list.
        """
        for name in self.juggler:
            for e in self.events.get(name, []):
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
                if e.label and not best.label:
                    best.label = e.label

    def event_circle_hand(self, e) -> str | None:
        """Which hand letter to show in the circle drawn for an event."""
        if e.action == "steal":
            return e.dst[1]      # catching hand
        if e.action == "hand":
            return e.src[1]      # giving hand
        if e.action == "zip":
            return e.dst[1]      # club ends up here
        if e.action in ("throw", "catch"):
            return e.hand
        return None

    def pattern_beats(self, juggler: dict) -> float:
        """Total beats of a pattern (blocks may span several beats)."""
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

    def parse_layout(self, text: str):
        number = int(text.split(":")[1])
        if text.startswith("step_X:"):
            self.step_X = number
        elif text.startswith("step_Y:"):
            self.step_Y = number

    def parse(self, text: str):
        """Take the text in the shortcode and parse it.

        Empty lines are skipped. There should be N lines for the
        pattern. We also allow extra lines for title, bars and positions.
        The positions can also be a list of positions which wil be animated.

        We allow "\" as a marker for continuous lines to be able to
        break up long lines.

        Everything after a "#" is treated as a comment, so "#" cannot
        be used anywhere in the input (including titles).

        """
        # a stable id derived from the input, so rebuilds produce
        # identical output (unlike random ids)
        self.diagram_id = hashlib.md5(text.encode()).hexdigest()[:8]

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
            elif line.startswith("swap:"):
                self.swap_chains = parse_swap(line)
            elif line.startswith("snapshots:"):
                self.snapshots = [
                    float(x) for x in line.removeprefix("snapshots:").split(",")
                ]
            else:
                self.parse_pattern(line)

        # now that we have parsed everything, fix a few things that we
        # can only do now, e.g. addjust the position for each juggler
        # if there is a title (cannot do this on the fly, since title
        # might be defined after the jugglers)

        # for the animation we need to rescale beats to the [0,1] interval
        # we do this already here
        self.duration_pattern = max(
            [self.pattern_beats(j) for j in self.juggler.values()]
        )

        # precompute the drawing records; a swap line unrolls them
        self.throws = self.collect_throws()
        self.circles = self.collect_circles()
        self.events = {name: self.collect_events(name) for name in self.juggler}
        if self.swap_chains:
            self.unroll_swap()
        self.apply_steals(self.throws)

        self.duration_position = 0
        for j in self.juggler.values():
            if "position" in j:
                # get last beat
                N = j["position"][-1][0]
                if N == 0:
                    continue
                # scale to [0, 1]
                for pos in j["position"]:
                    pos[0] = pos[0] / N
                self.duration_position = max(self.duration_position, N + 1)

        if self.title:
            for j in self.juggler.values():
                j["height"] += self.title_height

        # not a walking pattern, just  use the length given in the pattern
        if self.duration_position == 0:
            self.duration_position = self.duration_pattern

        # replace @A, @B, etc with actual angles
        self.calc_angle()

    def draw_circle(self, dwg, x, y, r, label, angle=None, css_class=None):
        """Draw a circel with a letter in it.

        This is used in the causal diagram for each hand and in the
        animation for a juggler.

        x,y are the position
        r is the radius
        label the letter (centered in the circle), skipped if empty
        angle the direction the juggler is looking, will be skipped if None
        css_class an optional class for the circle element

        """
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
        if angle is not None:
            angle = math.radians(angle)
            delta = math.radians(15)

            x1 = x + r * math.cos(angle + delta)
            y1 = y + r * math.sin(angle + delta)
            x2 = x + 1.5 * r * math.cos(angle)
            y2 = y + 1.5 * r * math.sin(angle)
            x3 = x + r * math.cos(angle - delta)
            y3 = y + r * math.sin(angle - delta)

            group.add(
                dwg.polygon(
                    points=[(x1, y1), (x2, y2), (x3, y3), (x1, y1)],
                    fill="black",
                )
            )

        return group

    def draw_arrow(self, dwg, arrow_marker, start_x, start_y, end_x, end_y,
                   css_class):
        """Draw an arrow in the diagram.

        These start and stop at the circle.

        If doubles and other longer throughs that are selves, are drawn
        using an arc.
        """

        dx = end_x - start_x
        dy = end_y - start_y
        length = (dx**2 + dy**2) ** 0.5

        if dx == 0 and dy == 0:
            return

        arrow_offset = self.radius
        start_x += arrow_offset * (dx / length)
        start_y += arrow_offset * (dy / length)
        end_x -= arrow_offset * (dx / length)
        end_y -= arrow_offset * (dy / length)

        is_arc = abs(end_x - start_x) - self.step_X > 10 and dy == 0
        if is_arc:
            # Calculate control point for the Bezier curve
            control_x = (start_x + end_x) / 2
            control_y = start_y - self.step_Y / 2

            # Draw a quadratic Bezier curve
            path_data = (
                f"M {start_x},{start_y} Q {control_x},{control_y} {end_x},{end_y}"
            )
            return dwg.path(
                d=path_data,
                fill="none",
                class_=css_class,
                marker_end=arrow_marker.get_funciri(),
            )

        return dwg.line(
            start=(start_x, start_y),
            end=(end_x, end_y),
            class_=css_class,
            marker_end=arrow_marker.get_funciri(),
        )

    def draw_causal_label(self, dwg, time, row_y, text):
        """A label above the circle where the throw/transfer starts."""
        return dwg.text(
            text,
            insert=(self.x_of(time), row_y - self.radius - 6),
            class_="arrow-label causal-label",
            text_anchor="middle",
        )

    def draw_animated_arrow(
        self,
        dwg,
        arrow_marker,
        start_x,
        start_y,
        end_x,
        end_y,
        start_time,
        end_time,
        css_class,
        label=None,
    ):
        """These are animated arrows for the position diagram.

        An optional label fades in and out together with the arrow.
        """

        dx = end_x - start_x
        dy = end_y - start_y

        if dx == 0 and dy == 0:
            return

        start_x += self.pos_center_x
        start_y += self.pos_center_y
        end_x += self.pos_center_x
        end_y += self.pos_center_y

        keytimes = f"0;{start_time/self.duration_position};{end_time/self.duration_position};{end_time/self.duration_position};1"

        def opacity_animation():
            return svgwrite.animate.Animate(
                attributeName_="opacity",
                values="0;0;1;0;0",
                keyTimes=keytimes,
                begin="0s",
                dur=f"{self.duration_position}s",
                repeatCount="indefinite",
                fill="remove",
            )

        line = dwg.line(
            start=(start_x, start_y),
            end=(end_x, end_y),
            opacity=0,
            class_=css_class,
            marker_end=arrow_marker.get_funciri(),
        )
        line.add(opacity_animation())
        if not label:
            return line

        text = dwg.text(
            label,
            insert=((start_x + end_x) / 2, (start_y + end_y) / 2 - 6),
            opacity=0,
            class_="arrow-label",
            text_anchor="middle",
        )
        text.add(opacity_animation())
        group = dwg.g()
        group.add(line)
        group.add(text)
        return group

    def get_juggler_position_only(self, name: str, time: int | float):
        """The X,Y position of a juggler for the position diagram at a given time.

        This is used when replacing @A, @B, etc. Where we don't have
        any information for the angle yet.

        Just doing a linear interpolation.

        Skipping the angle

        """
        # time is in beats, keyframes are also in beats - no normalization needed
        if "position" not in self.juggler[name]:
            return
        pos = self.juggler[name]["position"]
        t_0, x_0, y_0, _ = pos[0]
        if len(pos) == 1:
            return x_0, y_0
        for t, x, y, angle in pos[1:]:
            if time < t:
                X = (x - x_0) * (time - t_0) / (t - t_0) + x_0
                Y = (y - y_0) * (time - t_0) / (t - t_0) + y_0
                return X, Y
            else:
                t_0 = t
                x_0 = x
                y_0 = y
        # time is past the last keyframe, hold the last position
        return x_0, y_0

    def get_juggler_position(self, name: str, time: int | float):
        """The X,Y position of a juggler for the position diagram at a given time.

        Just doing a linear interpolation.
        """
        # rescale time to [0, 1] interval
        time = time / self.duration_position
        if "position" not in self.juggler[name]:
            return
        pos = self.juggler[name]["position"]
        t_0, x_0, y_0, angle_0 = pos[0]
        if len(pos) == 1:
            return x_0, y_0, angle_0
        for t, x, y, angle in pos[1:]:
            if time < t:
                X = (x - x_0) * (time - t_0) / (t - t_0) + x_0
                Y = (y - y_0) * (time - t_0) / (t - t_0) + y_0
                alpha = (angle - angle_0) * (time - t_0) / (t - t_0) + angle_0
                return X, Y, alpha
            else:
                t_0 = t
                x_0 = x
                y_0 = y
                angle_0 = angle
        # time is past the last keyframe, hold the last position
        return x_0, y_0, angle_0

    def get_juggler_hand_position(
        self, name: str, time: int | float, pass_delay: int | float
    ):
        """Get position of the hand, so slightly offset from the jugglers position.

        Coordinates are relative to the position diagram center.

        This is used for to get the hand of the person who does the pass
        and how does the catch. For the latter, we add `pass_delay`.

        Any delayed start of a juggler is included in pass_delay already.
        """
        hands = self.juggler[name]["letters"]
        idx = round(time + pass_delay) % len(hands)
        return self.get_hand_position(name, time, hands[idx])

    def get_hand_position(self, name: str, time, hand: str):
        """X,Y of a specific hand (R/L), relative to the position center."""
        x, y, angle = self.get_juggler_position(name, time)
        angle = math.radians(angle)
        delta = math.radians(15)
        # y-values have a minus, since the coordinate system is mirrored
        # e.g. y=0 is on top
        if hand == "R":
            X = x + self.radius * 1.6 * math.cos(-(angle + delta))
            Y = y - self.radius * 1.6 * math.sin(-(angle + delta))
        else:
            X = x + self.radius * 1.6 * math.cos(-(angle - delta))
            Y = y - self.radius * 1.6 * math.sin(-(angle - delta))

        return X, Y

    def get_style(self, value: str) -> tuple[str, str]:
        if value[-1] in COLORS:
            return value[:-1], COLORS[value[-1]]
        else:
            return value, "arrow-default"

    def drawing_to_str(self, dwg) -> str:
        """svgwrite can only write to file, so this converts to a str"""
        svg_string_io = io.StringIO()
        dwg.write(svg_string_io)
        svg_content = svg_string_io.getvalue()

        # Round floats to 4 decimal places to reduce file size
        def round_float(match):
            value = float(match.group(0))
            rounded = f"{value:.4f}".rstrip("0").rstrip(".")
            return rounded

        svg_content = re.sub(r"\b\d+\.\d{5,}\b", round_float, svg_content)

        return svg_content

    def add_scroll_data_attributes(
        self,
        svg_content: str,
        width: float,
        x_min: float,
        x_max: float,
        duration: float,
    ) -> str:
        """Add data attributes to SVG for auto-scrolling."""
        svg_id = f"causal-diagram-{self.diagram_id}"

        # Add class and data attributes to the SVG tag
        svg_content = re.sub(
            r"<svg\s+",
            f'<svg class="causal-diagram-svg" id="{svg_id}" data-diagram-width="{width}" data-x-min="{x_min}" data-x-max="{x_max}" data-duration="{duration}" ',
            svg_content,
            count=1,
        )
        return svg_content

    def has_position(self):
        """Check, if all jugglers have position information."""
        has_position = True
        for juggler in self.juggler.values():
            if "position" not in juggler:
                has_position = False
        return has_position

    def get_position_size(self):
        """Calculate bounding box for all juggler positions including all animation frames."""
        X_min, X_max, Y_min, Y_max = 0, 0, 0, 0

        for juggler in self.juggler.values():
            if "position" in juggler:
                # Check ALL position keyframes to find the actual bounding box
                for _, x, y, _ in juggler["position"]:
                    X_min = min(x, X_min)
                    X_max = max(x, X_max)
                    Y_min = min(y, Y_min)
                    Y_max = max(y, Y_max)

        # Add padding for juggler circles, direction indicators, and labels
        # Keep it proportional to content size
        padding = 50  # Fixed 50px padding

        width = X_max - X_min + 2 * padding
        height = Y_max - Y_min + 2 * padding

        # Ensure reasonable minimum size
        min_size = 300
        width = max(width, min_size)
        height = max(height, min_size)

        return (width, height)

    def to_svg(self):
        """Create the SVG(s).

        If positions are defined, returns two separate SVGs wrapped in HTML.
        Otherwise returns a single causal diagram SVG.
        """
        if self.has_position():
            return self.create_split_svgs()
        else:
            return self.create_single_svg()

    def create_split_svgs(self):
        """Create two separate synchronized SVGs for causal + position diagrams."""
        sync_id = self.diagram_id

        # Generate both SVGs
        causal_svg = self.generate_causal_diagram_svg()
        position_svg = self.generate_position_diagram_svg()

        # optional static snapshots below the animated diagrams
        snapshot_section = ""
        if self.snapshots:
            snaps = "".join(
                f'<div class="snapshot">'
                f'<div class="snapshot-caption">beat {t:g}</div>'
                f"{self.generate_snapshot_svg(t)}</div>"
                for t in self.snapshots
            )
            snapshot_section = f'''
    <div class="snapshot-section">
        <h3>Snapshots</h3>
        <div class="snapshot-row">{snaps}</div>
    </div>'''

        # Wrap in synchronized container
        wrapper = f'''<div class="diagram-sync-container" data-sync-id="{sync_id}" data-duration="{self.duration_pattern}">
    <div class="causal-diagram-section">
        <h3>Pattern Diagram</h3>
        {causal_svg}
    </div>
    <div class="position-diagram-section">
        <h3>Position Diagram</h3>
        {position_svg}
    </div>{snapshot_section}
</div>'''
        return wrapper

    def create_single_svg(self):
        """Create single SVG with just causal diagram (no positions)."""
        causal_svg = self.generate_causal_diagram_svg()
        return causal_svg

    def draw_elbow_arrow(self, dwg, arrow_marker, x, y_from, y_to, x_end,
                         css_class):
        """A hand-over in the causal diagram: vertical from the giver at
        the transfer moment, then along the receiver's row, ending at
        the beat where the club gets used."""
        end_x = x_end - self.radius
        if end_x <= x + 2 or y_from == y_to:
            # no room for the elbow: plain vertical transfer
            return self.draw_arrow(dwg, arrow_marker, x, y_from, x, y_to,
                                   css_class)
        start_y = y_from - self.radius if y_to < y_from else y_from + self.radius
        d = f"M {x},{start_y} L {x},{y_to} L {end_x},{y_to}"
        return dwg.path(d=d, fill="none", class_=css_class,
                        marker_end=arrow_marker.get_funciri())

    def draw_causal_events(self, dwg, arrow_marker, throws):
        """Transfer arrows (hand / take / zip) and hold lines.

        `throws` is the record list from phase 2, steals applied.
        """
        catches = {name: [] for name in self.juggler}
        releases = {name: [] for name in self.juggler}
        for name in self.juggler:
            H = self.juggler[name]["height"]
            for e in self.events.get(name, []):
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
                        if e.label:
                            dwg.add(self.draw_causal_label(
                                dwg, e.time, src_h, e.label))
                        releases[e.src[0]].append(e.time)
                elif e.action == "hand":
                    releases[name].append(e.time)
                    tgt = e.dst[0]
                    catches[tgt].append(e.time)
                    tgt_h = self.juggler[tgt]["height"]
                    # elbow: up to the receiver's row, then along it to
                    # their next full beat, where the club gets used
                    wait_t = self.juggler[tgt]["wait"]
                    t_land = wait_t + math.ceil(e.time - wait_t - 1e-9)
                    # if the receiver has no circle at the landing beat,
                    # draw one showing the receiving hand
                    near = [c for c in self.circles
                            if c.juggler == tgt and abs(c.time - t_land) < 0.25]
                    if not near:
                        dwg.add(self.draw_circle(
                            dwg, self.x_of(t_land), tgt_h, self.radius,
                            e.dst[1] or ""))
                    arr = self.draw_elbow_arrow(
                        dwg, arrow_marker, x, H, tgt_h,
                        self.x_of(t_land), css_class="arrow-hand")
                    if arr:
                        dwg.add(arr)
                    if e.label:
                        dwg.add(self.draw_causal_label(dwg, e.time, H, e.label))
                elif e.action == "zip":
                    # a zip takes half a beat: hand at t, other hand at t+0.5
                    releases[name].append(e.time)
                    catches[name].append(e.time + 0.5)
                    arr = self.draw_arrow(
                        dwg, arrow_marker,
                        x, H, self.x_of(e.time + 0.5), H,
                        css_class="arrow-zip")
                    if arr:
                        dwg.add(arr)
                    if e.label:
                        dwg.add(self.draw_causal_label(dwg, e.time, H, e.label))
                elif e.action == "throw":
                    releases[name].append(e.time)
                elif e.action == "catch":
                    catches[name].append(e.time)
        # stolen clubs are catches too
        for t in throws:
            if t.stolen_by:
                catches[t.stolen_by].append(t.steal_time)
        # hold lines: from each catch to the juggler's next release, but
        # only for short carries -- long holds would clutter the diagram
        for name in self.juggler:
            H = self.juggler[name]["height"]
            rel = sorted(releases[name])
            for c in sorted(set(catches[name])):
                nxt = [r for r in rel if r > c + 1e-9]
                if not nxt or nxt[0] - c > self.hold_line_max:
                    continue
                dwg.add(dwg.line(
                    start=(self.x_of(c) + self.radius, H),
                    end=(self.x_of(nxt[0]) - self.radius, H),
                    class_="hold-line"))

    def generate_causal_diagram_svg(self):
        """Generate the causal diagram SVG as a string."""
        N = len(self.juggler)

        width = self.step_X * (self.duration_pattern + 1.5)
        height = self.step_Y * N
        height += 2 * self.margin
        width += 2 * self.margin

        if self.title:
            height += self.title_height

        # Create an SVG drawing and add a box to frame it
        dwg = svgwrite.Drawing(size=(width, height))
        dwg.add(
            dwg.rect(insert=(0, 0), size=(width, height), fill="none", stroke="black")
        )

        # the arrow head as a marker in SVG
        arrow_marker = dwg.marker(
            id="arrowhead", insert=(5, 2.5), size=(5, 5), orient="auto"
        )
        arrow_marker.add(dwg.path(d="M 0 0 L 5 2.5 L 0 5 z", class_="arrow-marker"))

        dwg.defs.add(arrow_marker)

        if self.title:
            dwg.add(
                dwg.text(
                    self.title,
                    insert=(width // 2, self.title_height - 5),
                    fill="black",
                    text_anchor="middle",
                    dominant_baseline="middle",
                )
            )
        min_offset = min([j["wait"] for j in self.juggler.values()])
        y_min = min([j["height"] for j in self.juggler.values()]) - self.step_Y * 0.3
        y_max = max([j["height"] for j in self.juggler.values()]) + self.step_Y * 0.3
        X_min = 2 * self.margin + self.step_X * (1 + min_offset)

        for b in self.bars:
            X = X_min + b * self.step_X
            dwg.add(
                dwg.line(
                    start=(X, y_min),
                    end=(X, y_max),
                    stroke="lightgrey",
                    stroke_width=2,
                    class_="static-bar",
                )
            )

        # draw the causal diagram
        # phase 1: names, circles, empty beats -- also find X_max
        X_max = 0
        for name, juggler in self.juggler.items():
            H = juggler["height"]

            # the juggler names (A, B, C, ...)
            dwg.add(
                dwg.text(
                    f"{name}:",
                    insert=(self.margin, H),
                    fill="black",
                    dominant_baseline="middle",
                )
            )
            for c in self.circles:
                if c.juggler != name:
                    continue
                dwg.add(self.draw_circle(dwg, self.x_of(c.time), H,
                                         self.radius, c.label,
                                         css_class=c.css_class))
                X_max = max(X_max, self.x_of(c.time + 1))

        # phase 2: arrows from the precomputed throws (steals applied)
        throws = self.throws
        for t in throws:
            if t.value == 0:
                continue  # a 0 is an empty hand, no arrow
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
            if t.label:
                dwg.add(self.draw_causal_label(dwg, t.time, start_y, t.label))

        # phase 3: transfer arrows (hand / take / zip) and hold lines
        self.draw_causal_events(dwg, arrow_marker, throws)

        # Add animated red bar for scrolling sync
        min_offset = min([j["wait"] for j in self.juggler.values()])
        y_min = min([j["height"] for j in self.juggler.values()]) - self.step_Y * 0.3
        y_max = max([j["height"] for j in self.juggler.values()]) + self.step_Y * 0.3
        X_min = 2 * self.margin + self.step_X * (1 + min_offset)

        bar = dwg.line(
            start=(X_min, y_min),
            end=(X_min, y_max),
            stroke="red",
            stroke_width=2,
            class_="animated-bar",
        )
        bar.add(
            svgwrite.animate.AnimateTransform(
                transform="translate",
                attributeName_="transform",
                from_="0",
                to=f"{X_max - X_min}",
                dur=f"{self.duration_pattern}s",
                begin="0s",
                repeatCount="indefinite",
            )
        )
        dwg.add(bar)

        svg_str = self.drawing_to_str(dwg)
        return self.add_scroll_data_attributes(
            svg_str, width, X_min, X_max, self.duration_pattern
        )

    def generate_position_diagram_svg(self):
        """Generate the position diagram (walking pattern) SVG as a string."""
        # Calculate dimensions with proper bounding box
        width, height = self.get_position_size()

        self.pos_center_x = width / 2
        self.pos_center_y = height / 2

        # Create SVG (no scaling - use natural coordinates)
        dwg = svgwrite.Drawing(size=(width, height))
        dwg.add(
            dwg.rect(insert=(0, 0), size=(width, height), fill="none", stroke="black")
        )

        # Arrow marker
        arrow_marker = dwg.marker(
            id="arrowhead-pos", insert=(5, 2.5), size=(5, 5), orient="auto"
        )
        arrow_marker.add(dwg.path(d="M 0 0 L 5 2.5 L 0 5 z", class_="arrow-marker"))
        dwg.defs.add(arrow_marker)

        # the position diagram

        # Draw juggler positions
        for i, (name, juggler) in enumerate(self.juggler.items()):
            if "position" not in juggler:
                continue
            x, y, angle = self.get_juggler_position(name, 0)
            X = self.pos_center_x + x
            Y = self.pos_center_y + y
            keyTimes = ";".join([str(x[0]) for x in juggler["position"]])
            values = ";".join([f"{x[1]},{x[2]}" for x in juggler["position"]])
            # rotation happens inside the translated group, so the
            # center is the (static) drawing center
            values_rot = ";".join(
                [
                    f"{x[3] - angle} {self.pos_center_x} {self.pos_center_y}"
                    for x in juggler["position"]
                ]
            )

            if len(juggler["position"]) > 1:
                # start in center, so that all motion is given in relative
                # coordinates (including the step at t=0). Circle and
                # facing triangle rotate in an inner group; the letter
                # lives in the outer group so it stays upright.
                body = self.draw_circle(
                    dwg,
                    self.pos_center_x,
                    self.pos_center_y,
                    self.radius,
                    label="",
                    angle=angle,
                )
                body.add(
                    svgwrite.animate.AnimateTransform(
                        attributeName_="transform",
                        transform="rotate",
                        values=values_rot,
                        keyTimes_=keyTimes,
                        dur=f"{self.duration_position}s",
                        begin="0s",
                        repeatCount="indefinite",
                    )
                )
                pos = dwg.g()
                pos.add(body)
                pos.add(
                    dwg.text(
                        name,
                        insert=(self.pos_center_x, self.pos_center_y),
                        fill="black",
                        text_anchor="middle",
                        dominant_baseline="middle",
                    )
                )
                pos.add(
                    svgwrite.animate.AnimateTransform(
                        attributeName_="transform",
                        transform="translate",
                        values=values,
                        keyTimes_=keyTimes,
                        dur=f"{self.duration_position}s",
                        begin="0s",
                        repeatCount="indefinite",
                        additive="sum",
                    )
                )
            else:
                pos = self.draw_circle(
                    dwg,
                    X,
                    Y,
                    self.radius,
                    label=name,
                    angle=angle,
                )

            if len(juggler["position"]) > 1:
                label_x, label_y = self.pos_center_x, self.pos_center_y
            else:
                label_x, label_y = X, Y
            self.add_role_labels(dwg, pos, juggler, label_x,
                                 label_y + 2.2 * self.radius)
            dwg.add(pos)

        # the arrows in the position diagram
        # NOTE on clocks: positions and animation times historically use
        # the token index without the juggler's wait offset (see the
        # target-hand delay compensating with wait_B/wait_A). We keep
        # that clock: t.time - wait gives the token index back, and
        # event arrows use the initiator's clock the same way.
        throws = self.throws
        repeats = max(1, int(self.duration_position // self.duration_pattern))
        for r in range(repeats):
            shift = r * self.duration_pattern
            for t in throws:
                if t.target == t.juggler and not t.stolen_by:
                    continue  # selves are not drawn (existing behavior)
                wait_A = self.juggler[t.juggler]["wait"]
                i = t.time - wait_A  # token index clock
                start_x, start_y = self.get_juggler_hand_position(
                    t.juggler, shift + i, 0
                )
                if t.stolen_by:
                    end_t = shift + i + (t.steal_time - t.time)
                    hand = self.steal_catch_hand(t)
                    end_x, end_y = self.get_hand_position(
                        t.stolen_by, end_t, hand or "L"
                    )
                    style = "arrow-steal"
                else:
                    end_t = shift + i + t.value - 2
                    wait_B = self.juggler[t.target]["wait"]
                    end_x, end_y = self.get_juggler_hand_position(
                        t.target,
                        shift + i,
                        t.value - 2 - wait_B + wait_A,
                    )
                    style = t.style
                tmp = self.draw_animated_arrow(
                    dwg,
                    arrow_marker,
                    start_x,
                    start_y,
                    end_x,
                    end_y,
                    shift + i,
                    end_t,
                    css_class=style,
                    label=t.label,
                )
                if tmp:
                    dwg.add(tmp)
            for name in self.juggler:
                for e in self.events.get(name, []):
                    self.draw_position_event(dwg, arrow_marker, name, e, shift)

        # Return the SVG
        return self.drawing_to_str(dwg)

    def add_role_labels(self, dwg, group, juggler, x, y):
        """Role label(s) below a juggler circle in the position diagram.

        Static case: one text with the juggler's role_label. With swap,
        role_labels holds (start_beat, end_beat, text) windows -- the
        label follows the role, so each entry is only visible while
        this person occupies that role (discrete opacity animation).

        The text lives inside the juggler's animated group, so it
        walks (and turns) with them.
        """
        schedule = juggler.get("role_labels")
        if schedule:
            for start, end, text in schedule:
                t = dwg.text(text, insert=(x, y), opacity=0,
                             class_="role-label", text_anchor="middle")
                t.add(
                    svgwrite.animate.Animate(
                        attributeName_="opacity",
                        values="0;1;0",
                        keyTimes=f"0;{start / self.duration_position};{end / self.duration_position}",
                        calcMode="discrete",
                        begin="0s",
                        dur=f"{self.duration_position}s",
                        repeatCount="indefinite",
                    )
                )
                group.add(t)
        elif juggler.get("role_label"):
            group.add(dwg.text(juggler["role_label"], insert=(x, y),
                               class_="role-label", text_anchor="middle"))

    def role_label_at(self, juggler, t):
        """The role label a juggler shows at time t (None if none)."""
        schedule = juggler.get("role_labels")
        if schedule is not None:
            for start, end, text in schedule:
                if start <= t < end:
                    return text
            return None
        return juggler.get("role_label")

    def draw_snapshot_arrow(self, dwg, arrow_marker, start, end, css_class,
                            label=None):
        """A static arrow in a snapshot, coordinates relative to center.

        Long arrows (between two jugglers) are trimmed by the circle
        radius so they start and stop just outside the circles; an
        exchange then reads as one double-headed arrow.
        """
        sx, sy = start[0] + self.pos_center_x, start[1] + self.pos_center_y
        ex, ey = end[0] + self.pos_center_x, end[1] + self.pos_center_y
        if sx == ex and sy == ey:
            return
        dx, dy = ex - sx, ey - sy
        length = (dx**2 + dy**2) ** 0.5
        gap = self.radius + 12  # a small gap between arrow and circle
        if length > 2 * gap + 4:
            sx += gap * dx / length
            sy += gap * dy / length
            ex -= gap * dx / length
            ey -= gap * dy / length
        line = dwg.line(start=(sx, sy), end=(ex, ey), class_=css_class,
                        marker_end=arrow_marker.get_funciri())
        if not label:
            return line
        group = dwg.g()
        group.add(line)
        group.add(dwg.text(label, insert=((sx + ex) / 2, (sy + ey) / 2 - 6),
                           class_="arrow-label", text_anchor="middle"))
        return group

    def generate_snapshot_svg(self, t_snap):
        """A static position diagram at one moment in time.

        Shows every juggler where they are at t_snap (with facing and
        role label) plus an arrow for every club in the air and every
        transfer happening around that moment. Uses the same clock as
        the animated position diagram.
        """
        width, height = self.get_position_size()
        self.pos_center_x = width / 2
        self.pos_center_y = height / 2

        dwg = svgwrite.Drawing(size=(width, height))
        dwg.viewbox(0, 0, width, height)
        dwg.add(
            dwg.rect(insert=(0, 0), size=(width, height), fill="none",
                     stroke="black")
        )
        # larger arrow heads than in the animated diagrams
        arrow_marker = dwg.marker(
            id="arrowhead-snap", insert=(9, 4.5), size=(9, 9), orient="auto"
        )
        arrow_marker.add(dwg.path(d="M 0 0 L 9 4.5 L 0 9 z", class_="arrow-marker"))
        dwg.defs.add(arrow_marker)

        # jugglers at their interpolated positions
        for name, juggler in self.juggler.items():
            if "position" not in juggler:
                continue
            x, y, angle = self.get_juggler_position(name, t_snap)
            X = self.pos_center_x + x
            Y = self.pos_center_y + y
            group = self.draw_circle(dwg, X, Y, self.radius, label=name,
                                     angle=angle)
            role = self.role_label_at(juggler, t_snap)
            if role:
                group.add(dwg.text(role, insert=(X, Y + 2.2 * self.radius),
                                   class_="role-label", text_anchor="middle"))
            dwg.add(group)

        # clubs in the air / transfers at t_snap (same clock and windows
        # as the animated arrows)
        repeats = max(1, int(self.duration_position // self.duration_pattern))
        for r in range(repeats):
            shift = r * self.duration_pattern
            for t in self.throws:
                if t.value == 0:
                    continue
                if t.target == t.juggler and not t.stolen_by:
                    continue
                wait_A = self.juggler[t.juggler]["wait"]
                i = t.time - wait_A
                start_t = shift + i
                if t.stolen_by:
                    end_t = start_t + (t.steal_time - t.time)
                else:
                    end_t = start_t + t.value - 2
                if not start_t <= t_snap <= end_t:
                    continue
                # snapshots draw circle center to circle center, at the
                # positions as drawn at t_snap (no L/R hand offsets)
                start = self.get_juggler_position(t.juggler, t_snap)[:2]
                if t.stolen_by:
                    end = self.get_juggler_position(t.stolen_by, t_snap)[:2]
                    style = "arrow-steal"
                else:
                    end = self.get_juggler_position(t.target, t_snap)[:2]
                    style = t.style
                arrow = self.draw_snapshot_arrow(dwg, arrow_marker, start,
                                                 end, style, t.label)
                if arrow:
                    dwg.add(arrow)
            for name in self.juggler:
                for e in self.events.get(name, []):
                    te = shift + e.time - self.juggler[name]["wait"]
                    if e.action == "zip":
                        visible = te <= t_snap <= te + 0.5
                    else:
                        visible = te - 0.5 <= t_snap <= te
                    if not visible:
                        continue
                    if e.action == "zip":
                        # a zip stays hand-to-hand: both "centers" are
                        # the same juggler
                        endpoints = self.position_event_endpoints(name, e, te)
                        if endpoints is None:
                            continue
                        start, end, style = endpoints
                    elif e.action == "hand":
                        start = self.get_juggler_position(name, t_snap)[:2]
                        end = self.get_juggler_position(e.dst[0], t_snap)[:2]
                        style = "arrow-hand"
                    elif e.action == "steal" and e.src[1] is not None:  # take
                        start = self.get_juggler_position(e.src[0], t_snap)[:2]
                        end = self.get_juggler_position(name, t_snap)[:2]
                        style = "arrow-hand"
                    else:
                        continue
                    arrow = self.draw_snapshot_arrow(dwg, arrow_marker, start,
                                                     end, style, e.label)
                    if arrow:
                        dwg.add(arrow)

        return self.drawing_to_str(dwg)

    def steal_catch_hand(self, throw) -> str | None:
        """The hand a stolen throw is caught with (from the steal event)."""
        for e in self.events.get(throw.stolen_by, []):
            if (
                e.action == "steal"
                and e.src[0] == throw.juggler
                and throw.steal_time is not None
                and abs(e.time - throw.steal_time) < 1e-9
            ):
                return e.dst[1]
        return None

    def position_event_endpoints(self, name, e, t):
        """(start, end, style) of a hand/take/zip arrow, or None.

        Coordinates are hand positions relative to the position center,
        evaluated at time t.
        """
        if e.action == "hand":
            return (self.get_hand_position(name, t, e.src[1] or "R"),
                    self.get_hand_position(e.dst[0], t, e.dst[1] or "L"),
                    "arrow-hand")
        if e.action == "steal" and e.src[1] is not None:  # take
            return (self.get_hand_position(e.src[0], t, e.src[1]),
                    self.get_hand_position(name, t, e.dst[1] or "L"),
                    "arrow-hand")
        if e.action == "zip":
            return (self.get_hand_position(name, t, e.src[1] or "L"),
                    self.get_hand_position(name, t, e.dst[1] or "R"),
                    "arrow-zip")
        return None  # steal-from-air via Throw; throw events via collect_throws

    def draw_position_event(self, dwg, arrow_marker, name, e, shift):
        """Animated arrow for hand / take / zip at its absolute time."""
        # initiator's clock: strip the juggler's own wait (see NOTE above)
        t = shift + e.time - self.juggler[name]["wait"]
        window = 0.5  # arrows show for half a beat before the transfer
        endpoints = self.position_event_endpoints(name, e, t)
        if endpoints is None:
            return
        start, end, style = endpoints
        if e.action == "zip":
            # a zip takes half a beat, starting at its event time
            start_t, end_t = t, t + 0.5
        else:
            start_t, end_t = max(0, t - window), t
            if end_t <= start_t:
                start_t = max(0, end_t - 0.1)
        arrow = self.draw_animated_arrow(
            dwg, arrow_marker, start[0], start[1], end[0], end[1],
            start_t, end_t, css_class=style, label=e.label,
        )
        if arrow:
            dwg.add(arrow)
