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
