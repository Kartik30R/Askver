import uuid
from fastapi import HTTPException, status

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.db.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate


class AuthService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def register(self, user_create: UserCreate) -> tuple[User, str, str]:
        existing_user = await self.user_repo.get_by_email(user_create.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        hashed_password = get_password_hash(user_create.password)
        user = await self.user_repo.create(user_create, hashed_password)

        access_token = create_access_token(user.id)
        refresh_token = create_refresh_token(user.id)

        return user, access_token, refresh_token

    async def login(self, email: str, password: str) -> tuple[User, str, str]:
        user = await self.user_repo.get_by_email(email)
        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
            )

        access_token = create_access_token(user.id)
        refresh_token = create_refresh_token(user.id)

        return user, access_token, refresh_token

    async def refresh_tokens(self, refresh_token: str) -> tuple[User, str, str]:
        payload = decode_token(refresh_token, settings.JWT_REFRESH_SECRET_KEY)
        if not payload or payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
            )

        user_id_str = payload.get("sub")
        if not user_id_str:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

        user = await self.user_repo.get_by_id(uuid.UUID(user_id_str))
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        new_access_token = create_access_token(user.id)
        new_refresh_token = create_refresh_token(user.id)

        return user, new_access_token, new_refresh_token