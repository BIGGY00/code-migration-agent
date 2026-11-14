from pydantic import BaseModel, ConfigDict


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    region: str
    retries: int = 3
