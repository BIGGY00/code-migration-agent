from pydantic import BaseModel, Field


class UserOut(BaseModel):
    id: int
    full_name: str = Field(alias="fullName")

    class Config:
        orm_mode = True
        allow_population_by_field_name = True


def from_record(record) -> UserOut:
    return UserOut.from_orm(record)
