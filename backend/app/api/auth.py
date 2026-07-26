"""Authentication endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core.auth_cookies import clear_auth_cookie, set_auth_cookie
from app.core.deps import get_current_user
from app.core.rate_limit import limiter
from app.database import get_db
from app.models import User
from app.schemas import TokenResponse, UserLogin, UserRegister, UserResponse
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("3/hour")
def register(
    request: Request,
    data: UserRegister,
    response: Response,
    db: Session = Depends(get_db),
) -> TokenResponse:
    try:
        user = AuthService.register_user(db, data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    token = AuthService.create_token(user)
    set_auth_cookie(response, token)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
def login(
    request: Request,
    data: UserLogin,
    response: Response,
    db: Session = Depends(get_db),
) -> TokenResponse:
    user = AuthService.authenticate(db, data.email, data.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    token = AuthService.create_token(user)
    set_auth_cookie(response, token)
    return TokenResponse(access_token=token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    clear_auth_cookie(response)


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
