from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.core.rbac import Role


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime


class TokenData(BaseModel):
    sub: str
    role: Role


class UserPublic(BaseModel):
    user_id: str
    username: str
    full_name: str
    role: Role
    manager_id: Optional[str] = None
    team_members: list[str] = Field(default_factory=list)
    gdpr_consent: bool = True


class UserRecord(UserPublic):
    hashed_password: str
