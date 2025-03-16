from nikola.plugin_categories import ShortcodePlugin
import io
import math
import svgwrite
from itertools import cycle


# define several styles that can be used for arrow inside the pattern
COLORS = {
    ",": "stroke: #d12229; stroke-width: 4",
    "$": "stroke: #d12229; stroke-width: 2",
    "#": "stroke: #f68a1e; stroke-dasharray: 6 3; stroke-width: 2",
    ">": "stroke: #007940; stroke-dasharray: 9 2 9; stroke-width: 2",
    "<": "stroke: #fde01a; stroke-dasharray: 6 6; stroke-width: 3",
    "^": "stroke: #24408e; stroke-dasharray: 12 6; stroke-width: 3",
    "*": "stroke: #732982; stroke-dasharray: 8 2 8 2 8; stroke-width: 3",
}


class CausalDiagramSVG(ShortcodePlugin):
    """A simple script/shortcode to display causal diagrams.

    The syntax of the diagrams was adapted from:
    https://www.jugglingedge.com/help/causaldiagrams.php

    and then modified to allow for SVG animations.
    """

    name = "causal_diagram"

    juggler_names = "ABCDEFGHIJKLNM"
    step_X = 80
    step_Y = 100
    margin = 10
    radius = 12

    title_height = 50

    # values for position
    pos_height = 300

    def __init__(self):
        super().__init__()
        self.clear()

    def clear(self):
        """Needed in case we have several diagrams on one page."""
        self.juggler = {}
        self.title = ""
        self.bars = []
        self.duration_position = 0
        self.duration_pattern = 0

    def handler(self, site=None, data=None, lang=None, post=None):
        """This gets executed for the shortcode."""
        self.clear()
        self.parse(data)
        return self.to_svg(), []

    def parse_hands_and_delay(self, line: str):
        """Parse () in front of a pattern line.

        This should be the letters that will be shown in the circles.
        The default is "RL", but it could be "RRLL" for some patterns.

        If there is a number at the end, this will be the delay.
        """
        if line.startswith("("):
            values, pattern = line[1:].split(")")
            values = values.strip()
            if " " in values:
                hands, wait = values.split()
                wait = float(wait)
            else:
                try:
                    hands = "RL"
                    wait = float(values)
                except ValueError:
                    hands = values
                    wait = 0
        else:
            hands = "RL"
            wait = 0
            pattern = line
        return pattern, hands, wait

    def parse_title(self, line: str) -> None:
        self.title = line[6:].strip()

    def parse_bars(self, line: str) -> None:
        self.bars = [float(x) for x in line[5:].split(",")]

    def parse_position(self, line):
        """Parses positions.

        This can be static or include multiple locations for walking patterns.

        Especially for static positions, we allow shortcuts that will
        create positions for all known jugglers (so this should be
        defined after the pattern).

        Currently we support:
        * circle (equidistance on a circle, facing the center)
        * line (two vertical lines, offset for odd numbers, facing across)

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
                offset = (N % 2) * 50

                """
                2 ->  0....0
                3 ->  0...  -50, 50
                4 -> -50, 50 .... -50, 50
                5 -> --50,50 ... -100, 0, 100
                6 -> -100, 0, 100.....-100,0,100
                """

                left = N // 2
                right = N - left
                start_left = 50 * (left - 1)
                start_right = 50 * (right - 1)
                left_count = 0
                right_count = 0
                for i, j in enumerate(self.juggler.values()):
                    if i % 2:
                        j["position"] = [[0, -100, start_left - 50 * left_count, 0]]
                        left_count += 1
                    else:
                        j["position"] = [[0, 100, start_right - 50 * right_count, 180]]
                        right_count += 1
            return

        line = line.removeprefix("position")
        name, values = line.split(":")
        name = name.strip()
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
            t = [float(x) for x in t]
            if len(t) == 2:
                t = [0, t[0], t[1], 0]
            elif len(t) == 3:
                t = [0, t[0], t[1], t[2]]
            tmp.append(t)
        self.juggler[name]["position"] = tmp

    def parse_pattern(self, line: str) -> None:
        """This is the actual pattern"""
        # get new name
        n = len(self.juggler)
        juggler_name = self.juggler_names[n]
        tmp = {}
        # parse extra information in () at the start
        pattern, hands, wait = self.parse_hands_and_delay(line)
        tmp["letters"] = hands
        tmp["wait"] = wait
        # 'p' for passes are only allowed in 2 person patterns
        # otherwise it should be letters. Replace 'p' with 'a' and 'b'
        # here so that it is easier later in the program
        if "p" in pattern:
            if juggler_name == "A":
                pattern = pattern.replace("p", "b")
            else:
                pattern = pattern.replace("p", "a")
        tmp["pattern"] = pattern.split()
        # the y-coordinate the juggler line should be drawn in the diagram
        tmp["height"] = self.margin + int(self.step_Y * (n + 0.5))
        self.juggler[juggler_name] = tmp

    def parse(self, text: str):
        """Take the text in the shortcode and parse it.

        Empty lines are skipped. There should be N lines for the
        pattern. We also allow extra lines for title, bars and positions.
        The positions can also be a list of positions which wil be animated.

        We allow "\" as a marker for continuous lines to be able to break up long lines.
        """

        # build up the whole input line in case continuous lines are used
        line = ""
        for current_line in text.split("\n"):
            current_line = current_line.strip()

            # handle continuation lines
            if current_line.endswith("\\"):
                line += current_line[:-1].strip()
                continue
            line += current_line
            if not line:
                continue

            # handle the different input options
            if line.startswith("title:"):
                self.parse_title(line)
            elif line.startswith("bars:"):
                self.parse_bars(line)
            elif line.startswith("position"):
                self.parse_position(line)
            else:
                self.parse_pattern(line)
            line = ""

        # for the animation we need to rescale beats to the [0,1] interval
        # we do this already here
        self.duration_pattern = max([len(j["pattern"]) for j in self.juggler.values()])
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
                self.duration_position = max(self.duration_position, N)

        # not a walking pattern, just  use the length given in the pattern
        if self.duration_position == 0:
            self.duration_position = self.duration_pattern

    def draw_circle(self, dwg, x, y, r, label, angle=None):
        """Draw a circel with a letter in it.

        x,y are the position
        r is the radius
        label the letter (centered in the circle)
        angle the direction the juggler is looking, will be skipped if None
        """
        group = dwg.g()
        group.add(dwg.circle(center=(x, y), r=r, stroke="black", fill="none"))
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

    def draw_arrow(self, dwg, arrow_marker, start_x, start_y, end_x, end_y, style):
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

        if abs(end_x - start_x) - self.step_X > 10 and dy == 0:
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
                style=style,
                marker_end=arrow_marker.get_funciri(),
            )

        else:
            return dwg.line(
                start=(start_x, start_y),
                end=(end_x, end_y),
                style=style,
                marker_end=arrow_marker.get_funciri(),
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
        style,
    ):
        """These are animated arrows for the position diagram."""

        dx = end_x - start_x
        dy = end_y - start_y

        if dx == 0 and dy == 0:
            return

        start_x += self.pos_center_x
        start_y += self.pos_center_y
        end_x += self.pos_center_x
        end_y += self.pos_center_y

        line = dwg.line(
            start=(start_x, start_y),
            end=(end_x, end_y),
            opacity=0,
            style=style,
            marker_end=arrow_marker.get_funciri(),
        )
        line.add(
            svgwrite.animate.Animate(
                attributeName_="opacity",
                values="0;0;1;0;0",
                keyTimes=f"0;{start_time/self.duration_position};{end_time/self.duration_position};{end_time/self.duration_position};1",
                begin="0s",
                dur=f"{self.duration_position}s",
                repeatCount="indefinite",
                fill="remove",
            )
        )
        return line

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
        return 0, 0, 0

    def get_juggler_hand_position(
        self, name: str, time: int | float, hand_delay: int | float
    ):
        """Get position of the hand, so slightly offset from the jugglers position.

        Coordinates are relative to the position diagram center.
        """
        x, y, angle = self.get_juggler_position(name, time)
        hands = self.juggler[name]["letters"]
        N = len(hands)

        time = round(time + hand_delay)
        idx = time % N

        hand = hands[idx]

        angle = math.radians(angle)
        delta = math.radians(15)
        # y-values have a minus, since the coordinate system is mirrored
        # e.g. y=0 is on top
        if hand == "L":
            X = x + self.radius * 1.6 * math.cos(-(angle + delta))
            Y = y - self.radius * 1.6 * math.sin(-(angle + delta))
        else:
            X = x + self.radius * 1.6 * math.cos(-(angle - delta))
            Y = y - self.radius * 1.6 * math.sin(-(angle - delta))

        return X, Y

    def get_style(self, value: str) -> list[str, str]:
        if value[-1] in COLORS.keys():
            return [value[:-1], COLORS[value[-1]]]
        else:
            return [value, "stroke: black"]

    def drawing_to_str(self, dwg) -> str:
        """svgwrite can only write to file, so this converts to a str"""
        svg_string_io = io.StringIO()
        dwg.write(svg_string_io)
        svg_content = svg_string_io.getvalue()
        return svg_content

    def has_position(self):
        """Check, if all jugglers have position information."""
        has_position = True
        for juggler in self.juggler.values():
            if "position" not in juggler:
                has_position = False
        return has_position

    def to_svg(self):
        """Create the SVG.

        This create the causal diagram and if positions are defined also
        a position diagram. Possible with animation.
        """
        N = len(self.juggler)

        length = self.step_X * (self.duration_pattern + 1.5)

        height = self.step_Y * N

        height += 2 * self.margin
        length += 2 * self.margin

        if self.title:
            height += self.title_height

        # positions
        if self.has_position():
            height += self.pos_height
            self.pos_length = length
            self.pos_center_y = height - self.pos_height / 2
            self.pos_center_x = length / 2

        # Create an SVG drawing and add a box to frame it
        dwg = svgwrite.Drawing(size=(length, height))
        dwg.add(
            dwg.rect(insert=(0, 0), size=(length, height), fill="none", stroke="black")
        )

        # the arrow head as a marker in SVG
        arrow_marker = dwg.marker(
            id="arrowhead", insert=(5, 2.5), size=(5, 5), orient="auto"
        )
        arrow_marker.add(dwg.path(d="M 0 0 L 5 2.5 L 0 5 z", fill="black"))

        dwg.defs.add(arrow_marker)

        if self.title:
            dwg.add(
                dwg.text(
                    self.title,
                    insert=(length // 2, self.title_height // 2 - 5),
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
                )
            )

        # draw the causal diagram
        for i, (name, juggler) in enumerate(self.juggler.items()):
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
            X = 2 * self.margin + self.step_X * (1 + juggler["wait"])

            # the arrows
            for p, hand in zip(juggler["pattern"], cycle(juggler["letters"])):
                group = self.draw_circle(dwg, X, H, self.radius, hand)
                dwg.add(group)
                p, style = self.get_style(p)
                try:
                    p = int(p) - 2
                    Y = H
                except ValueError:
                    target = p[-1]
                    for k in self.juggler:
                        if target.lower() == k.lower():
                            Y = self.juggler[k]["height"]

                    p = int(p[:-1]) - 2
                end_x = X + self.step_X * p
                arrow = self.draw_arrow(dwg, arrow_marker, X, H, end_x, Y, style=style)
                if arrow:
                    dwg.add(arrow)
                X += self.step_X
                X_max = X

        if not self.has_position():
            return self.drawing_to_str(dwg)

        # the position diagram

        # animate the red bar across the pattern
        bar = dwg.line(
            start=(X_min, y_min),
            end=(X_min, y_max),
            stroke="red",
            stroke_width=2,
        )
        bar.add(
            svgwrite.animate.AnimateTransform(
                transform="translate",
                attributeName_="transform",
                from_="0",
                to=f"{X_max-X_min}",
                dur=f"{self.duration_pattern}s",
                begin="0s",
                repeatCount="indefinite",
            )
        )
        dwg.add(bar)

        # the positions
        for i, (name, juggler) in enumerate(self.juggler.items()):
            if "position" not in juggler:
                continue
            x, y, angle = self.get_juggler_position(name, 0)
            X = self.pos_center_x + x
            Y = self.pos_center_y + y
            keyTimes = ";".join([str(x[0]) for x in juggler["position"]])
            values = ";".join([f"{x[1]},{x[2]}" for x in juggler["position"]])
            values_rot = ";".join(
                [
                    f"{x[3]-angle} {x[1]+self.pos_center_x} {x[2]+self.pos_center_y}"
                    for x in juggler["position"]
                ]
            )

            if len(juggler["position"]) > 1:
                # start in center, so that all motion is given in relative
                # coordinates (inlcuding the step at t=0
                pos = self.draw_circle(
                    dwg,
                    self.pos_center_x,
                    self.pos_center_y,
                    self.radius,
                    label=name,
                    angle=angle,
                )
                pos.add(
                    svgwrite.animate.AnimateTransform(
                        attributeName_="transform",
                        transform="rotate",
                        values=values_rot,
                        keyTimes_=keyTimes,
                        dur=f"{self.duration_position}s",
                        begin="0s",
                        repeatCount="indefinite",
                        additive="sum",
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

            dwg.add(pos)

        # the arrows in the position diagram
        for j in self.juggler:
            if "position" not in self.juggler[j]:
                continue
            repeats = int(self.duration_position // self.duration_pattern)

            for r in range(repeats):
                for i, pat in enumerate(self.juggler[j]["pattern"]):
                    pat = pat.strip()
                    pat, style = self.get_style(pat)
                    try:
                        int(pat)
                    except ValueError:
                        # this is a pass
                        p = int(pat[:-1])
                        target = pat[-1].upper()
                        start_x, start_y = self.get_juggler_hand_position(
                            j, r * self.duration_pattern + i, 0
                        )
                        end_x, end_y = self.get_juggler_hand_position(
                            target, r * self.duration_pattern + i, p - 2
                        )
                        tmp = self.draw_animated_arrow(
                            dwg,
                            arrow_marker,
                            start_x,
                            start_y,
                            end_x,
                            end_y,
                            r * self.duration_pattern + i,
                            r * self.duration_pattern + i + p - 2,
                            style=style,
                        )
                        dwg.add(tmp)

        return self.drawing_to_str(dwg)
