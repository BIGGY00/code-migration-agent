from typing import List
from pydantic import BaseModel, ValidationInfo, field_validator


class Team(BaseModel):
    domain: str
    emails: List[str]

    @field_validator("emails")
    @classmethod
    def same_domain(cls, emails, info: ValidationInfo):
        domain = info.data.get("domain")
        out = []
        for v in emails:
            if domain and not v.lower().endswith("@" + domain):
                raise ValueError(f"{v} is not in {domain}")
            out.append(v.lower())
        return out
