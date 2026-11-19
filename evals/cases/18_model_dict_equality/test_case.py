from target import Preferences, is_default, reset


def test_fresh_preferences_are_default():
    assert is_default(Preferences()) is True


def test_changed_preferences_are_not_default():
    assert is_default(Preferences(beta=True)) is False


def test_reset_restores_defaults():
    p = reset(Preferences(theme="dark", page_size=50))
    assert is_default(p) is True
    assert p.theme == "light"
