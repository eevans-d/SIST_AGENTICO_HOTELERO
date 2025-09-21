# [PROMPT GA-02] app/core/security.py

from datetime import datetime, timedelta
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from .settings import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/admin/token")


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    jwt_exp_minutes = int(getattr(settings, "jwt_expiration_minutes", 60))
    jwt_alg = getattr(settings, "jwt_algorithm", "HS256")
    secret = settings.secret_key.get_secret_value()
    expire = datetime.utcnow() + timedelta(minutes=jwt_exp_minutes)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, secret, algorithm=jwt_alg)


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        jwt_alg = getattr(settings, "jwt_algorithm", "HS256")
        payload = jwt.decode(token, settings.secret_key.get_secret_value(), algorithms=[jwt_alg])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    return {"username": username}
