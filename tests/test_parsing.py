from causal_diagram import logical_lines


def test_plain_lines_stay_separate():
    assert logical_lines("3p 3 3\n3p 3 3") == ["3p 3 3", "3p 3 3"]


def test_backslash_continuation_still_works():
    text = "position A: 0,-100,0,@B;\\\n2,-100,0,@C;"
    assert logical_lines(text) == ["position A: 0,-100,0,@B;2,-100,0,@C;"]


def test_trailing_semicolon_does_not_continue():
    # complete position lines end with ';' on real pages -- consecutive
    # declarations must stay separate (use '\' to continue long ones)
    text = "position A: 0,-100,0,@B;\nposition B: 0,100,0,@A;"
    assert logical_lines(text) == [
        "position A: 0,-100,0,@B;",
        "position B: 0,100,0,@A;",
    ]


def test_unclosed_paren_continues():
    text = "3b 3 (2: 0 steal b>L;\n0.25 hand R>cL) 3 3"
    assert logical_lines(text) == ["3b 3 (2: 0 steal b>L; 0.25 hand R>cL) 3 3"]


def test_cosmetic_indentation_is_not_continuation():
    # havana.md and others column-align lines with leading spaces
    text = "3d 3 3c 3\n  3 3 3a 3\n  3 3 3b 3"
    assert logical_lines(text) == ["3d 3 3c 3", "3 3 3a 3", "3 3 3b 3"]


def test_trailing_comma_is_not_continuation():
    # ',' is the red-thick color suffix, e.g. 3p,
    assert logical_lines("3 3 3p,\n3 3 3p") == ["3 3 3p,", "3 3 3p"]


def test_comments_stripped():
    assert logical_lines("3 3 3  # a comment\n3 3 3") == ["3 3 3", "3 3 3"]
