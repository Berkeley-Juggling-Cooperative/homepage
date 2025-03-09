from nikola.plugin_categories import ShortcodePlugin
import io
import svgwrite
from itertools import cycle


class CausalDiagramSVG(ShortcodePlugin):
    """A simple script to display causal diagrams.

    The syntax of the diagrams was adapted from:
    https://www.jugglingedge.com/help/causaldiagrams.php
    """

    name = "causal_diagram"

    juggler_names = "ABCDEFGHIJ"
    step_X = 80
    step_Y = 100
    margin = 10
    radius = 12

    # values for position
    pos_height = 300

    def __init__(self):
        super().__init__()
        self.clear()

    def clear(self):
        self.juggler = {}
        self.title = ""
        self.bars = []
        self.duration = 0

    def handler(self, site=None, data=None, lang=None, post=None):
        # Call your program that converts text input to SVG
        self.clear()
        self.parse_pattern(data)
        svg_output = self.to_svg()
        return svg_output, []

    def parse_pattern(self, text):
        n = 0
        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue
            if line.startswith("title:"):
                self.title = line[6:].strip()
            elif line.startswith("bars:"):
                self.bars = [float(x) for x in line[5:].split(",")]
            elif line.startswith("position"):
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
                    t = [float(x) for x in t]
                    tmp.append(t)
                self.juggler[name]["position"] = tmp
            else:
                juggler_name = self.juggler_names[n]
                tmp = {}
                if line.startswith("("):
                    names, pattern = line[1:].split(")")
                    if " " in names:
                        names, wait = names.split()
                        wait = float(wait)
                    else:
                        wait = 0
                else:
                    names = "RL"
                    wait = 0
                    pattern = line

                tmp["letters"] = names
                tmp["wait"] = wait
                if "p" in pattern:
                    if juggler_name == "A":
                        pattern = pattern.replace("p", "b")
                    else:
                        pattern = pattern.replace("p", "a")
                tmp["pattern"] = pattern.split()
                tmp["height"] = self.margin + int(self.step_Y * (n + 0.8))
                self.juggler[juggler_name] = tmp
                n += 1
        for j in self.juggler:
            N = len(self.juggler[j]["pattern"])
            if "position" in self.juggler[j]:
                for pos in self.juggler[j]["position"]:
                    pos[0] = pos[0] / N
            self.duration = max(self.duration, (N + self.juggler[j]["wait"]))



    def draw_circle(self, dwg, x, y, r, hand):
        group = dwg.g()
        group.add(dwg.circle(center=(x, y), r=r, stroke="black", fill="none"))
        group.add(
            dwg.text(
                hand,
                insert=(x, y),
                fill="black",
                text_anchor="middle",
                dominant_baseline="middle",
            )
        )
        return group

    def draw_arrow(
        self, dwg, arrow_marker, start_x, start_y, end_x, end_y, stroke="black"
    ):
        # Add the line part of the arrow and reference the marker

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
                stroke=stroke,
                stroke_width=2,
                fill="none",
                marker_end=arrow_marker.get_funciri(),
            )

        else:
            return dwg.line(
                start=(start_x, start_y),
                end=(end_x, end_y),
                stroke=stroke,
                stroke_width=2,
                marker_end=arrow_marker.get_funciri(),
            )

    def draw_animated_arrow(
        self, dwg, arrow_marker, start_x, start_y, end_x, end_y, start_time, end_time
    ):
        # Add the line part of the arrow and reference the marker

        dx = end_x - start_x
        dy = end_y - start_y
        length = (dx**2 + dy**2) ** 0.5

        if dx == 0 and dy == 0:
            return

        start_x += self.pos_center_x
        start_y += self.pos_center_y
        end_x += self.pos_center_x
        end_y += self.pos_center_y

        arrow_offset = self.radius
        start_x += arrow_offset * (dx / length)
        start_y += arrow_offset * (dy / length)
        end_x -= arrow_offset * (dx / length)
        end_y -= arrow_offset * (dy / length)

        line = dwg.line(
            start=(start_x, start_y),
            end=(end_x, end_y),
            stroke="black",
            opacity=0,
            stroke_width=2,
            marker_end=arrow_marker.get_funciri(),
        )
        line.add(
            svgwrite.animate.Animate(
                attributeName_="opacity",
                values="0;0;1;0;0",
                keyTimes=f"0;{start_time/self.duration};{end_time/self.duration};{end_time/self.duration};1",
                begin=f"0s",
                dur=f"{self.duration}s",
                repeatCount="indefinite",
                fill="remove",
            )
        )
        return line

    def get_juggler_position(self, name, time):
        time = time/self.duration
        print(name, time)
        if 'position' not in self.juggler[name]:
            return
        pos = self.juggler[name]["position"]
        t_0, x_0, y_0 = pos[0]
        if len(pos) == 1:
            return x_0, y_0
        for t, x, y in pos[1:]:
            print(t, x, y, name, time)
            if time <= t:
                print('yes')
                X = (x - x_0) * (time - t_0) / (t - t_0) + x_0
                Y = (y - y_0) * (time - t_0) / (t - t_0) + y_0
                return X, Y
            else:
                print('no')
                t_0 = t
                x_0 = x
                y_0 = y
        return 0, 0

    def to_svg(self):
        N = len(self.juggler)

        length = self.step_X * (self.duration + 1.5)

        height = 100 * N

        height += 2 * self.margin
        length += 2 * self.margin

        title_height = 30 if self.title else 0

        height += title_height

        # positions
        height += self.pos_height
        self.pos_length = length
        self.pos_center_y = height - self.pos_height / 2
        self.pos_center_x = length / 2

        # Create an SVG drawing
        dwg = svgwrite.Drawing(size=(length, height))
        dwg.add(
            dwg.rect(insert=(0, 0), size=(length, height), fill="none", stroke="black")
        )

        arrow_marker = dwg.marker(
            id="arrowhead", insert=(5, 2.5), size=(5, 5), orient="auto"
        )
        arrow_marker.add(dwg.path(d="M 0 0 L 5 2.5 L 0 5 z", fill="black"))

        dwg.defs.add(arrow_marker)

        if self.title:
            dwg.add(
                dwg.text(
                    self.title,
                    insert=(length // 2, 10 + title_height // 2),
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

            for p, hand in zip(juggler["pattern"], cycle(juggler["letters"])):
                group = self.draw_circle(dwg, X, H, self.radius, hand)
                dwg.add(group)
                highlight = "black"
                if p.endswith(","):
                    p = p[:-1]
                    highlight = "red"

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
                arrow = self.draw_arrow(
                    dwg, arrow_marker, X, H, end_x, Y, stroke=highlight
                )
                if arrow:
                    dwg.add(arrow)
                X += self.step_X
                X_max = X

        # animate bar across the pattern
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
                dur=f"{self.duration}s",
                begin="0s",
                repeatCount="indefinite",
            )
        )
        dwg.add(bar)

        for i, (name, juggler) in enumerate(self.juggler.items()):
            if "position" not in juggler:
                continue
            X = self.pos_center_x + juggler["position"][0][1]
            Y = self.pos_center_y + juggler["position"][0][2]
            keyTimes = ";".join([str(x[0]) for x in juggler["position"]])
            values = ";".join([f"{x[1]},{x[2]}" for x in juggler["position"]])

            pos = self.draw_circle(
                dwg, self.pos_center_x, self.pos_center_y, self.radius, hand=name
            )
            pos.add(
                svgwrite.animate.AnimateTransform(
                    transform="translate",
                    attributeName_="transform",
                    values=values,
                    keyTimes_=keyTimes,
                    dur=f"{self.duration}s",
                    begin="0s",
                    repeatCount="indefinite",
                    additive="sum",
                )
            )
            dwg.add(pos)

        for j in self.juggler:
            if 'position' not in self.juggler[j]:
                continue
            for i, pat in enumerate(self.juggler[j]["pattern"]):
                pat = pat.strip()
                if pat.endswith(","):
                    pat = pat[:-1]
                try:
                    int(pat)
                except ValueError:
                    # this is a pass
                    p = int(pat[:-1])
                    target = pat[-1].upper()
                    start_x, start_y = self.get_juggler_position(j, i)
                    end_x, end_y = self.get_juggler_position(target, i + (p - 2))

                    print(i, i+(p-2))
                    print(j, start_x, start_y,)
                    print(target,  end_x, end_y)
                    tmp = self.draw_animated_arrow(
                        dwg,
                        arrow_marker,
                        start_x,
                        start_y,
                        end_x,
                        end_y,
                        i,
                        i + p - 2,
                    )
                    print(tmp)
                    dwg.add(tmp)

        svg_string_io = io.StringIO()
        dwg.write(svg_string_io)
        svg_content = svg_string_io.getvalue()

        return svg_content
