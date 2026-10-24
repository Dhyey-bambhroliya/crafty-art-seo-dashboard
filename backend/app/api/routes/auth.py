from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import verify_password, hash_password, create_access_token
from backend.app.models.models import User, UserRole
from backend.app.schemas.schemas import (
    LoginRequest, TokenResponse, SetupStatusResponse, SetupManagerRequest, UserOut
)
from backend.app.api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.get("/setup-status", response_model=SetupStatusResponse)
def get_setup_status(db: Session = Depends(get_db)):
    """Check if the system has an initialized manager account."""
    manager = db.query(User).filter(User.role == UserRole.MANAGER).first()
    return SetupStatusResponse(
        is_initialized=manager is not None,
        manager_exists=manager is not None
    )

@router.post("/setup-manager", response_model=TokenResponse)
def setup_initial_manager(request: SetupManagerRequest, db: Session = Depends(get_db)):
    """Safe initial setup flow for the very first Manager account."""
    existing_manager = db.query(User).filter(User.role == UserRole.MANAGER).first()
    if existing_manager:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="System is already initialized with an active Manager. Please sign in."
        )
    
    # Check if email taken
    if db.query(User).filter(User.email == request.email.lower()).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists."
        )
    
    manager_user = User(
        email=request.email.lower(),
        full_name=request.full_name,
        hashed_password=hash_password(request.password),
        role=UserRole.MANAGER,
        is_active=True
    )
    db.add(manager_user)
    db.commit()
    db.refresh(manager_user)
    
    token = create_access_token(subject=manager_user.id, role=manager_user.role)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        role=manager_user.role,
        user_id=manager_user.id,
        full_name=manager_user.full_name,
        email=manager_user.email
    )

@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate user with email and password and issue secure JWT."""
    user = db.query(User).filter(User.email == request.email.lower()).first()
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated. Please contact your manager."
        )
    
    token = create_access_token(subject=user.id, role=user.role)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        role=user.role,
        user_id=user.id,
        full_name=user.full_name,
        email=user.email
    )

@router.get("/me", response_model=UserOut)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Get profile of authenticated user."""
    return current_user

@router.post("/logout")
def logout(current_user: User = Depends(get_current_user)):
    """Log out confirmation."""
    return {"message": "Logged out successfully"}
