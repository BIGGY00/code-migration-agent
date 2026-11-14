from pydantic import BaseModel, validator


class Signup(BaseModel):
    username: str
    password: str

    @validator("username")
    def username_alnum(cls, v):
        if not v.isalnum():
            raise ValueError("username must be alphanumeric")
        return v.lower()
