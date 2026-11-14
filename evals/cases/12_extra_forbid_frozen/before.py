from pydantic import BaseModel, Extra


class Settings(BaseModel):
    region: str
    retries: int = 3

    class Config:
        extra = Extra.forbid
        allow_mutation = False
