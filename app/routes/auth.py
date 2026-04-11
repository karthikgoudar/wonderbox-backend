from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.infra.repositories import user_repository
from app.schemas.auth_schema import UserRegister, UserLogin, TokenResponse
from app.services.auth_service import hash_password, create_access_token, authenticate_user, decode_token
from app.side_effects.analytics_service import track_event


router = APIRouter(prefix="/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


@router.post("/register", response_model=TokenResponse)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    existing = user_repository.get_by_email(db, payload.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = user_repository.create(
        db,
        {
            "email": payload.email,
            "name": payload.name,
            "password_hash": hash_password(payload.password),
        },
    )

    track_event(db, "auth.register", user_id=user.id, properties={"email": user.email})
    token = create_access_token(subject=str(user.id))
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = authenticate_user(db, payload.email, payload.password)
    track_event(db, "auth.login", user_id=user.id, properties={"email": user.email})
    token = create_access_token(subject=str(user.id))
    return TokenResponse(access_token=token)


@router.get("/me")
def me(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    user_id = decode_token(token)
    user = user_repository.get_by_id(db, int(user_id))
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return {"id": user.id, "email": user.email, "name": user.name}
