from auth import AdminTokenStore


def test_admin_token_has_fixed_expiry():
    now = [100.0]
    store = AdminTokenStore(
        60,
        clock=lambda: now[0],
        token_factory=lambda: "admin-token",
    )

    token = store.issue()

    assert token == "admin-token"
    assert store.expires_at(token) == 160.0
    assert store.validate(token) is True

    now[0] = 159.999
    assert store.validate(token) is True

    now[0] = 160.0
    assert store.validate(token) is False
    assert len(store) == 0


def test_new_admin_token_revokes_the_previous_token():
    tokens = iter(("first", "second"))
    store = AdminTokenStore(60, token_factory=lambda: next(tokens))

    first = store.issue()
    second = store.issue()

    assert store.validate(first) is False
    assert store.validate(second) is True
    assert len(store) == 1


def test_admin_token_can_be_revoked_or_cleared():
    tokens = iter(("first", "second"))
    store = AdminTokenStore(60, token_factory=lambda: next(tokens))

    first = store.issue()
    store.revoke(first)
    assert store.validate(first) is False

    second = store.issue()
    store.clear()
    assert store.validate(second) is False
