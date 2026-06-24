from pydantic import BaseModel, EmailStr

class CheckRequest(BaseModel):
    business: str
    category: str
    area: str

class LeadRequest(BaseModel):
    business: str
    email: EmailStr
    category: str
    area: str
    verdict: str = "UNKNOWN"
