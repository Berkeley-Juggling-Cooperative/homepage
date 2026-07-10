import pytest
from causal_diagram import (
    CausalDiagramSVG,
    parse_endpoint,
    parse_event,
    parse_event_block,
    tokenize_pattern,
)


def test_tokenize_keeps_event_block_together():
    toks = tokenize_pattern("3b 3 (2: 0 steal b>L; 0.25 hand R>cL) 3")
    assert toks == ["3b", "3", "(2: 0 steal b>L; 0.25 hand R>cL)", "3"]


def test_parse_endpoint():
    assert parse_endpoint("L") == (None, "L")
    assert parse_endpoint("cR") == ("C", "R")
    assert parse_endpoint("b") == ("B", None)


def test_parse_event_steal_from_air():
    e = parse_event("0 steal b>L")
    assert (e.time, e.action, e.src, e.dst) == (0.0, "steal", ("B", None), (None, "L"))


def test_parse_event_take_from_hand():
    e = parse_event("0.5 steal cR>L")
    assert e.src == ("C", "R")
    assert e.dst == (None, "L")


def test_parse_event_hand_and_zip():
    e = parse_event("0.25 hand R>cL")
    assert (e.action, e.src, e.dst) == ("hand", (None, "R"), ("C", "L"))
    z = parse_event("0.5 zip L>R")
    assert (z.action, z.src, z.dst) == ("zip", (None, "L"), (None, "R"))


def test_parse_event_throw():
    e = parse_event("1 throw 3a R")
    assert (e.action, e.value, e.hand) == ("throw", "3a", "R")


def test_parse_event_block():
    b = parse_event_block("(2: 0 steal b>L; 0.25 hand R>cL)")
    assert b["beats"] == 2.0
    assert [e.action for e in b["events"]] == ["steal", "hand"]


def test_event_time_outside_block_raises():
    with pytest.raises(ValueError):
        parse_event_block("(1: 1.5 zip L>R)")


def test_pattern_line_with_block_and_hands_prefix():
    d = CausalDiagramSVG()
    d.parse("(RL 0.5) 3b 3 (2: 0 steal b>L) 3\n3a 3 3 3 3")
    A = d.juggler["A"]
    assert A["wait"] == 0.5
    assert isinstance(A["pattern"][2], dict)
    assert d.pattern_beats(A) == 5.0
    # absolute time: block starts at beat 2, wait 0.5 -> steal at 2.5
    events = d.collect_events("A")
    assert events[0].time == 2.5


def test_block_as_first_token_is_not_hands_prefix():
    d = CausalDiagramSVG()
    d.parse("(1: 0 zip L>R) 3 3\n3 3 3")
    A = d.juggler["A"]
    assert A["letters"] == "RL"       # default, prefix not consumed
    assert isinstance(A["pattern"][0], dict)
