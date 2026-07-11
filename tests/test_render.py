from causal_diagram import CausalDiagramSVG


def render(data):
    out, _ = CausalDiagramSVG().handler(data=data)
    return out


def test_silent_beat_draws_no_arrow():
    svg = render("3 - 3 3\n3 3 3 3")
    assert svg.count("beat-empty") == 1


def test_silent_beat_circle_has_no_letter():
    svg = render("3 - 3 3")
    # the beat-empty circle's group must not carry a hand letter
    empty_idx = svg.index("beat-empty")
    group_end = svg.index("</g>", empty_idx)
    assert "<text" not in svg[empty_idx:group_end]


def test_silent_beat_in_position_diagram_does_not_crash():
    svg = render("3b - 3 3\n3a 3 3 3\npositions: line")
    assert "data-sync-id" in svg


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


def test_hand_in_draws_arrow_and_hold_line():
    svg = render(ROUNDABOUT_SNIPPET)
    assert "arrow-hand" in svg
    assert "arrow-zip" in svg
    assert "hold-line" in svg


def test_event_circles_show_explicit_hand():
    svg = render(ROUNDABOUT_SNIPPET)
    # C's steal catches with L: a circle labeled L exists on C's row
    assert ">L<" in svg


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
    position_part = svg.split("position-diagram-section")[1]
    assert "arrow-steal" in position_part
    assert "arrow-hand" in position_part
    assert "arrow-zip" in position_part


def test_no_events_output_identical_shape():
    # regression: a plain diagram has none of the new markup
    svg = render("3 3 3\n3 3 3")
    assert "arrow-steal" not in svg and "hold-line" not in svg


def test_position_letters_do_not_rotate():
    import xml.etree.ElementTree as ET
    out = render(
        "3b 3\n3a 3\n"
        "position A: 0,-100,0,0; 2,-100,0,180;\n"
        "position B: 0,100,0,180; 2,100,0,0;\n"
    )
    part = out.split("position-diagram-section")[1]
    svg = part[part.index("<svg"):part.index("</svg>") + 6]
    root = ET.fromstring(svg)
    ns = "{http://www.w3.org/2000/svg}"
    letters = 0
    for g in root.iter(f"{ns}g"):
        rotating = any(
            a.get("type") == "rotate"
            for a in g.findall(f"{ns}animateTransform")
        )
        texts = g.findall(f"{ns}text")
        if rotating:
            assert not texts, "juggler letter must not rotate"
        letters += sum(1 for t in texts if t.text and t.text.strip() in "AB")
    assert letters == 2  # the upright letters still exist
