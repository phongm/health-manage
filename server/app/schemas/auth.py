from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    code: str = Field(min_length=1, max_length=128)


class LoginData(BaseModel):
    token: str
    is_new_user: bool
    profile_completed: bool
