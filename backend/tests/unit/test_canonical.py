from kindred.crypto.canonical import canonical_json


def test_canonical_sorts_keys():
    a = canonical_json({"b": 1, "a": 2})
    b = canonical_json({"a": 2, "b": 1})
    assert a == b


def test_canonical_no_whitespace():
    assert b" " not in canonical_json({"x": 1})


def test_canonical_utf8_no_ascii_escape():
    assert "ă".encode("utf-8") in canonical_json({"name": "ănă"})


def test_canonical_nested():
    assert canonical_json({"x": [3, 1, 2]}) == b'{"x":[3,1,2]}'
