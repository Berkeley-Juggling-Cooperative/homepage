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
