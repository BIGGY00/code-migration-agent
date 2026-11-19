from pydantic import BaseModel

DEFAULTS = {"theme": "light", "page_size": 20, "beta": False}


class Preferences(BaseModel):
    theme: str = "light"
    page_size: int = 20
    beta: bool = False


def is_default(prefs: Preferences) -> bool:
    """True if every setting still has its default value."""
    return prefs == DEFAULTS


def reset(prefs: Preferences) -> Preferences:
    return prefs.copy(update=DEFAULTS)
