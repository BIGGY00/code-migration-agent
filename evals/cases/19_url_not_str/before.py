from pydantic import BaseModel, HttpUrl


class ApiConfig(BaseModel):
    base_url: HttpUrl
    timeout: float = 5.0


def load(raw: str) -> ApiConfig:
    return ApiConfig.parse_raw(raw)


def endpoint(cfg: ApiConfig, path: str) -> str:
    """Full URL for `path`, which starts with '/'."""
    return cfg.base_url + path


def is_secure(cfg: ApiConfig) -> bool:
    return cfg.base_url.startswith("https://")
