from pydantic import BaseModel, field_validator


class Signup(BaseModel):
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def username_alnum(cls, v: str) -> str:
        if not v.isalnum():
            raise ValueError("username must be alphanumeric")
        return v.lower()
