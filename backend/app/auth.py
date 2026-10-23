"""
Minimal JWT-based authentication.

For this portfolio project there is a single demo user defined via
environment variables (no user database/signup flow yet — that would be a
natural next extension). Passwords are hashed with bcrypt; tokens are signed
JWTs with an expiry.
"""
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

from app.config import get_settings

settings = get_settings()

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# Demo user. In a real system this would live in the `employees` table (or a
# dedicated `users` table) with per-user hashed passwords.
DEMO_USERNAME = settings.demo_username
DEMO_PASSWORD_HASH = bcrypt.hashpw(settings.demo_password.encode(), bcrypt.gensalt())

security = HTTPBearer()


def authenticate(username: str, password: str) -> bool:
    if username != DEMO_USERNAME:
        return False
    return bcrypt.checkpw(password.encode(), DEMO_PASSWORD_HASH)


def create_access_token(username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": username, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
        return username
    except JWTError:
        raise credentials_exception


credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid or expired authentication token",
    headers={"WWW-Authenticate": "Bearer"},
)
