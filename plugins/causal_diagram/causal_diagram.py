from nikola.plugin_categories import ShortcodePlugin
import io
import svgwrite


class CausalDiagramSVG(ShortcodePlugin):
    name = "causal_diagram"

    def handler(self, site=None, data=None, lang=None, post=None):
        # Call your program that converts text input to SVG
        print("in plugin handler", data, lang, post)
        svg_output = self.convert_text_to_svg(data)
        return svg_output, []

    def convert_text_to_svg(self, text):
        text = "--modified text---" + text + "---mod2---"

        # Create an SVG drawing
        dwg = svgwrite.Drawing(size=(200, 200))

        # Add some elements to the drawing
        dwg.add(dwg.rect(insert=(10, 10), size=(180, 180), fill="blue"))
        dwg.add(dwg.text("Hello, SVG!", insert=(20, 30), fill="white"))

        # Use StringIO to capture the SVG content
        svg_string_io = io.StringIO()
        dwg.write(svg_string_io)
        svg_content = svg_string_io.getvalue()

        return svg_content
