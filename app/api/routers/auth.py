from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import get_current_user, require_roles
from app.core.rbac import Role
from app.models.auth import Token, UserPublic
from app.services.container import auth_service


router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/token", response_model=Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()) -> Token:
    user = auth_service.authenticate(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return auth_service.issue_token(user)


@router.get("/me", response_model=UserPublic)
def read_me(current_user: dict = Depends(get_current_user)) -> UserPublic:
    return auth_service.as_public(current_user)


@router.get("/users", response_model=list[UserPublic])
def list_users(
    current_user: dict = Depends(require_roles([Role.HR])),
) -> list[UserPublic]:
    _ = current_user
    return auth_service.list_users()
