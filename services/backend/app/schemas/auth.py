from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    phone: str | None = None
    email: str | None = None
    nickname: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=6, max_length=128)


class LoginRequest(BaseModel):
    phone: str | None = None
    email: str | None = None
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    nickname: str
    phone: str | None
    email: str | None
    avatar_url: str
    selected_character_id: str | None

    model_config = {"from_attributes": True}
