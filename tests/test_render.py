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


def test_hand_arrow_is_elbow_to_next_beat():
    svg = render("3b 3 3\n3a 3 3\n(3: 0.75 hand R>aL)")
    # C at x_of(0.75)=160 hands to A (row y=60); the arrow goes up and
    # then right, ending one radius before A's beat-1 circle (x=180)
    assert "M 160,248 L 160,60 L 168,60" in svg.replace(".0", "")


def test_no_hold_line_for_long_holds():
    # catch at 0.5, next release at 3 -> gap 2.5 beats, no hold line
    svg = render("3 3 3 3\n(4: 0.5 steal a>L; 3 throw 3 L)")
    assert "hold-line" not in svg


def test_hold_line_for_short_holds():
    # catch at 0.5, release at 1 -> genuine short carry, line drawn
    svg = render("3 3 3 3\n(4: 0.5 steal a>L; 1 throw 3 L)")
    assert "hold-line" in svg


def test_zip_spans_half_a_beat():
    svg = render("3 3 3\n(3: 1 zip L>R)").replace(".0", "")
    # zip at beat 1: from x_of(1)=180 to x_of(1.5)=220, trimmed by the
    # radius -> the arrow runs 192..208; circles L at 180 and R at 220
    assert 'x1="192"' in svg and 'x2="208"' in svg
    assert svg.count('cx="180"') >= 1 and svg.count('cx="220"') >= 1


def test_hand_elbow_lands_on_the_next_beat_with_receiving_circle():
    # the hand-over lands on the receiver's next full beat (5), not on
    # some nearby event circle; since A has no circle at beat 5, one is
    # drawn automatically showing the receiving hand (L)
    svg = render(
        "3 3 3 3 3 (1: 0.25 steal bR>R)\n"
        "(6: 4.5 hand R>aL)"
    ).replace(".0", "")
    # x_of(5) = 20 + 80*6 = 500, minus the radius -> 488
    assert "L 488,60" in svg
    i = svg.index('cx="500" cy="60"')
    group = svg[i:svg.index("</g>", i)]
    assert ">L<" in group.replace("\n", "").replace(" ", "")


def test_animated_arrows_carry_time_window_attributes():
    svg = render(
        "3b 3 3 3\n3a 3 3 3\n"
        "position A: -100, 0, @B\nposition B: 100, 0, @A\n"
    )
    pos = svg.split("position-diagram-section")[1]
    # every animated arrow knows its window, for the paused-stepping UI
    assert 'data-start="0"' in pos.replace('"0.0"', '"0"')
    assert pos.count("data-start") == pos.count("data-end") >= 2


def test_hand_landing_on_wrong_hand_gets_secondary_circle():
    # A's beat-6 grid circle shows R (RL cycle); the hand-in goes to L,
    # so a smaller L circle appears below the row and the elbow lands
    # on it: x_of(6)=580, y = 60 + 12 + 8.4 = 80.4
    svg = render("3 3 3 3 3 3 3 3\n(8: 5.5 hand R>aL)").replace(".0,", ",")
    assert 'r="8.4"' in svg
    assert "L 568,80.4" in svg


def test_hand_landing_on_matching_hand_uses_main_circle():
    # beat-6 circle is R and the club arrives in R: no extra circle
    svg = render("3 3 3 3 3 3 3 3\n(8: 5.5 hand L>aR)")
    assert 'r="8.4"' not in svg


def test_red_bar_travels_exactly_one_step_per_beat():
    # last circle (zip tail at 1.85) lies past duration-1; the bar must
    # still travel step_X * duration = 160, ending at X_min + 160 = 260
    svg = render("(2: 1.35 zip L>R)\n3 3").replace(".0", "")
    assert 'to="160"' in svg
    assert 'data-x-max="260"' in svg
