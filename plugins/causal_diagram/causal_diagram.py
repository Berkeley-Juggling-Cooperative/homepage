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

    def __init__(self):
        super().__init__()
        self.clear()

    def clear(self):
        self.juggler = {}
        self.title = ""
        self.bars = []

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
                tmp["pattern"] = pattern.split()
                tmp["height"] = self.margin + int(self.step_Y * (n + 0.8))
                self.juggler[juggler_name] = tmp
                n += 1

    def draw_arrow(self, dwg, arrow_marker, start_x, start_y, p, end_y, stroke="black"):
        # Add the line part of the arrow and reference the marker

        end_x = start_x + self.step_X * p

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

        if abs(p) != 1 and dy == 0:
            # Calculate control point for the Bezier curve
            control_x = (start_x + end_x) / 2
            control_y = start_y - self.step_Y / 2

            # Draw a quadratic Bezier curve
            path_data = (
                f"M {start_x},{start_y} Q {control_x},{control_y} {end_x},{end_y}"
            )
            dwg.add(
                dwg.path(
                    d=path_data,
                    stroke=stroke,
                    stroke_width=2,
                    fill="none",
                    marker_end=arrow_marker.get_funciri(),
                )
            )
        else:
            dwg.add(
                dwg.line(
                    start=(start_x, start_y),
                    end=(end_x, end_y),
                    stroke=stroke,
                    stroke_width=2,
                    marker_end=arrow_marker.get_funciri(),
                )
            )

    def to_svg(self):
        title_height = 0

        length = 0
        for j in self.juggler.values():
            print(j)
            length = max(length, self.step_X * (len(j["pattern"]) + j["wait"] + 1.5))

        height = 100 * len(self.juggler)

        height += 2 * self.margin
        length += 2 * self.margin

        if self.title:
            title_height = 30

        height += title_height

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
        for b in self.bars:
            min_offset = min([j['wait'] for j in self.juggler.values()])
            y_min = min([j['height'] for j in self.juggler.values()]) - self.step_Y*0.3
            y_max = max([j['height'] for j in self.juggler.values()]) + self.step_Y*0.3
            X = 2 * self.margin + self.step_X * (1 + min_offset) + b*self.step_X
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
                dwg.add(
                    dwg.circle(
                        center=(X, H), r=self.radius, stroke="black", fill="none"
                    )
                )
                dwg.add(
                    dwg.text(
                        hand,
                        insert=(X, H),
                        fill="black",
                        text_anchor="middle",
                        dominant_baseline="middle",
                    )
                )
                highlight = "black"
                if p.endswith(","):
                    p = p[:-1]
                    highlight = "red"

                try:
                    p = int(p) - 2
                    Y = H
                except ValueError:
                    target = p[-1]
                    if target.lower() == "p":
                        for k in self.juggler:
                            if k != name:
                                Y = self.juggler[k]["height"]
                    else:
                        for k in self.juggler:
                            if target.lower() == k.lower():
                                Y = self.juggler[k]["height"]

                    p = int(p[:-1]) - 2
                self.draw_arrow(dwg, arrow_marker, X, H, p, Y, stroke=highlight)
                X += self.step_X

        # Use StringIO to capture the SVG content
        svg_string_io = io.StringIO()
        dwg.write(svg_string_io)
        svg_content = svg_string_io.getvalue()

        return svg_content
