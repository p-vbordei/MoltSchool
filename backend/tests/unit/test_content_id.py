from kindred.crypto.content_id import compute_content_id


def test_content_id_stable_for_equal_content():
    a = compute_content_id({"x": 1, "y": 2})
    b = compute_content_id({"y": 2, "x": 1})
    assert a == b
    assert a.startswith("sha256:")
    assert len(a) == len("sha256:") + 64


def test_content_id_differs_for_different_content():
    assert compute_content_id({"x": 1}) != compute_content_id({"x": 2})


def test_content_id_from_bytes():
    cid = compute_content_id(b"hello")
    assert cid == "sha256:2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
