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
    assert e.action == "steal"


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


def test_p_replacement_does_not_touch_labels():
    d = CausalDiagramSVG()
    d.parse('3p 3"pelf" 3\n3p 3 3')
    labels = [t.label for t in d.throws if t.label]
    assert labels == ["pelf"]
    # and the actual p tokens were still replaced
    assert d.throws[0].target == "B"


def test_steal_event_label_lands_on_rerouted_arrow():
    d = CausalDiagramSVG()
    d.parse('3b 3 3 3\n3a 3 3 3\n(4: 1 steal b>L "snatch")')
    stolen = [t for t in d.throws if t.stolen_by]
    assert len(stolen) == 1
    assert stolen[0].label == "snatch"
