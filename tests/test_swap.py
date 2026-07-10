from causal_diagram import CausalDiagramSVG, parse_swap


def test_parse_swap():
    assert parse_swap("swap: A->B->C, D->E") == [["A", "B", "C"], ["D", "E"]]


def make(text):
    d = CausalDiagramSVG()
    d.parse(text)
    return d


def test_two_role_swap_unrolls_two_periods():
    d = make("swap: A->B\n3b 3\n3a 3")
    # period 2 beats, cycle length 2 -> total 4 beats per person
    assert d.duration_pattern == 4
    a_throws = sorted(
        [t for t in d.throws if t.juggler == "A"], key=lambda t: t.time
    )
    assert [t.time for t in a_throws] == [0, 1, 2, 3]
    # period 0: person A plays role A -> pass to person doing role B (=B)
    assert a_throws[0].target == "B"
    # period 1: person A plays role B -> its "3a" targets role A,
    # whose occupant in period 1 is person B
    assert a_throws[2].target == "B"
    # selves stay with the person
    assert a_throws[1].target == "A"
    assert a_throws[3].target == "A"


def test_swap_remaps_event_endpoints():
    d = make(
        "swap: A->B\n"
        "3 3\n"
        "(1: 0.5 hand R>aL) -\n"
    )
    b_events = sorted(d.events["B"], key=lambda e: e.time)
    # period 0: person B in role B hands to role A -> person A
    assert b_events[0].dst[0] == "A"
    assert b_events[0].time == 0.5
    # period 1: person A plays role B; its hand to role A goes to the
    # period-1 occupant of role A, which is person B
    a_events = sorted(d.events["A"], key=lambda e: e.time)
    assert a_events[0].dst[0] == "B"
    assert a_events[0].time == 2.5


def test_swap_concatenates_positions():
    d = make(
        "swap: A->B\n"
        "3b 3\n"
        "3a 3\n"
        "position A: 0, -100, 0, 0; 2, 100, 0, 180;\n"
        "position B: 0, 100, 0, 180; 2, -100, 0, 0;\n"
    )
    pos = d.juggler["A"]["position"]
    # keyframe times are normalized to [0,1]; raw last beat was 4
    assert pos[0][0] == 0.0 and pos[-1][0] == 1.0
    assert len(pos) == 4


def test_no_swap_line_changes_nothing():
    d = make("3b 3 3\n3a 3 3")
    assert d.duration_pattern == 3
    assert len(d.throws) == 6


def test_swap_renders():
    out, _ = CausalDiagramSVG().handler(data="swap: A->B\n3b 3 3 3\n3a 3 3 3")
    assert "<svg" in out
