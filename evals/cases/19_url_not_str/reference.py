from pydantic import BaseModel, HttpUrl


class ApiConfig(BaseModel):
    base_url: HttpUrl
    timeout: float = 5.0


def load(raw: str) -> ApiConfig:
    return ApiConfig.model_validate_json(raw)


def endpoint(cfg: ApiConfig, path: str) -> str:
    """Full URL for `path`, which starts with '/'."""
    return str(cfg.base_url).rstrip("/") + path


def is_secure(cfg: ApiConfig) -> bool:
    return str(cfg.base_url).startswith("https://")
