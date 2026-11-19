from typing import List
from pydantic import BaseModel, validator


class Team(BaseModel):
    domain: str
    emails: List[str]

    @validator("emails", each_item=True)
    def same_domain(cls, v, values):
        domain = values.get("domain")
        if domain and not v.lower().endswith("@" + domain):
            raise ValueError(f"{v} is not in {domain}")
        return v.lower()
