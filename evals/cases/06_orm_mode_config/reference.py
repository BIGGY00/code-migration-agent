from pydantic import BaseModel, ConfigDict, Field


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    full_name: str = Field(alias="fullName")


def from_record(record) -> UserOut:
    return UserOut.model_validate(record)
