import secrets
from fastapi import Header, HTTPException
from sqlalchemy.orm import Session
from .config import settings
from .models import User

def generate_api_key() -> str:
    return secrets.token_urlsafe(32)

def get_user_by_api_key(db: Session, api_key: str) -> User | None:
    return db.query(User).filter(User.api_key == api_key).first()

def require_api_key(x_api_key: str = Header(default=None, alias="X-API-Key")):
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing X-API-Key")
    return x_api_key
