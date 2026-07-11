from causal_diagram import CausalDiagramSVG


def render(data):
    out, _ = CausalDiagramSVG().handler(data=data)
    return out


PATTERN = (
    "3b 3 3 3\n"
    "3a 3 3 3\n"
    "position A: -100, 0, @B\n"
    "position B: 100, 0, @A\n"
    "snapshots: 0.5, 2\n"
)


def test_snapshots_parsed():
    d = CausalDiagramSVG()
    d.parse(PATTERN)
    assert d.snapshots == [0.5, 2.0]


def test_snapshot_section_rendered_with_header():
    out = render(PATTERN)
    assert ">Snapshots<" in out
    assert out.count('class="snapshot"') == 2
    assert "beat 0.5" in out and "beat 2" in out


def test_snapshot_shows_in_flight_pass_only():
    out = render(PATTERN)
    snaps = out.split('class="snapshot"')
    # beat 0.5: both passes (thrown at 0, arrive at 1) are in the air
    assert snaps[1].count("arrow-default") == 2
    # beat 2: only selves are in the air, and selves are not drawn
    assert "arrow-default" not in snaps[2]


def test_no_snapshots_line_no_section():
    out = render("3b 3\n3a 3\npositions: line")
    assert "Snapshots" not in out


def test_snapshot_arrows_are_center_to_center_trimmed():
    out = render(PATTERN)
    import re
    snap = out.split('class="snapshot"')[1]
    lines = re.findall(r'<line[^>]*class="arrow-default[^>]*>', snap)
    assert len(lines) == 2
    # A at (-100,0), B at (100,0), canvas 300x300 -> centers (50,150)
    # and (250,150); trimmed by the radius (12): 62 and 238
    coords = set()
    for ln in lines:
        x1 = float(re.search(r'x1="([-\d.]+)"', ln).group(1))
        x2 = float(re.search(r'x2="([-\d.]+)"', ln).group(1))
        y1 = float(re.search(r'y1="([-\d.]+)"', ln).group(1))
        y2 = float(re.search(r'y2="([-\d.]+)"', ln).group(1))
        assert y1 == y2 == 150.0
        coords.add((x1, x2))
    # the exchange: same segment, opposite directions
    assert coords == {(62.0, 238.0), (238.0, 62.0)}
