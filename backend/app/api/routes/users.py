from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.core.database import get_db
from backend.app.core.security import hash_password
from backend.app.models.models import User, UserRole, Category
from backend.app.schemas.schemas import UserCreate, UserUpdate, UserOut
from backend.app.api.deps import require_manager, require_team_leader_or_manager

router = APIRouter(prefix="/users", tags=["Team Management"])

@router.get("", response_model=List[UserOut])
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """Manager only: View all team members and their category assignments."""
    users = db.query(User).order_by(User.role, User.full_name).all()
    results = []
    for u in users:
        cat_count = db.query(Category).filter(Category.assigned_leader_id == u.id).count()
        results.append(UserOut(
            id=u.id,
            email=u.email,
            full_name=u.full_name,
            role=u.role,
            is_active=u.is_active,
            created_at=u.created_at,
            category_count=cat_count
        ))
    return results

@router.get("/leaders", response_model=List[UserOut])
def list_team_leaders(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_team_leader_or_manager)
):
    """View active team leaders (available to both managers and leaders for dropdowns/filters)."""
    leaders = (
        db.query(User)
        .filter(User.role == UserRole.TEAM_LEADER, User.is_active == True)
        .order_by(User.full_name)
        .all()
    )
    results = []
    for u in leaders:
        cat_count = db.query(Category).filter(Category.assigned_leader_id == u.id).count()
        results.append(UserOut(
            id=u.id,
            email=u.email,
            full_name=u.full_name,
            role=u.role,
            is_active=u.is_active,
            created_at=u.created_at,
            category_count=cat_count
        ))
    return results

@router.post("", response_model=UserOut)
def create_user(
    user_in: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """Manager only: Create a new Team Leader or Manager."""
    existing = db.query(User).filter(User.email == user_in.email.lower()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists."
        )
    
    role = UserRole.MANAGER if user_in.role == UserRole.MANAGER else UserRole.TEAM_LEADER
    new_user = User(
        email=user_in.email.lower(),
        full_name=user_in.full_name,
        hashed_password=hash_password(user_in.password),
        role=role,
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return UserOut(
        id=new_user.id,
        email=new_user.email,
        full_name=new_user.full_name,
        role=new_user.role,
        is_active=new_user.is_active,
        created_at=new_user.created_at,
        category_count=0
    )

@router.put("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """Manager only: Edit team member account, role, or toggle active/deactivate status."""
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found."
        )
    
    if user_in.email and user_in.email.lower() != target_user.email:
        conflict = db.query(User).filter(User.email == user_in.email.lower(), User.id != user_id).first()
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is already used by another account."
            )
        target_user.email = user_in.email.lower()

    if user_in.full_name is not None:
        target_user.full_name = user_in.full_name
    
    if user_in.password:
        target_user.hashed_password = hash_password(user_in.password)
        
    if user_in.role is not None:
        target_user.role = user_in.role
        
    if user_in.is_active is not None:
        # Prevent manager from deactivating themselves if they are the only manager
        if not user_in.is_active and target_user.id == current_user.id:
            active_managers = db.query(User).filter(User.role == UserRole.MANAGER, User.is_active == True).count()
            if active_managers <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot deactivate the only active Manager account."
                )
        target_user.is_active = user_in.is_active

    db.commit()
    db.refresh(target_user)
    
    cat_count = db.query(Category).filter(Category.assigned_leader_id == target_user.id).count()
    return UserOut(
        id=target_user.id,
        email=target_user.email,
        full_name=target_user.full_name,
        role=target_user.role,
        is_active=target_user.is_active,
        created_at=target_user.created_at,
        category_count=cat_count
    )

@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """Manager only: Permanently delete a team leader or user account."""
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own manager account."
        )

    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found."
        )

    from backend.app.models.models import Alert
    # Reassign categories owned by this user to current manager to avoid orphaned categories
    db.query(Category).filter(Category.assigned_leader_id == user_id).update(
        {"assigned_leader_id": current_user.id}
    )

    # Reassign or clean alerts
    db.query(Alert).filter(Alert.assigned_leader_id == user_id).update(
        {"assigned_leader_id": current_user.id}
    )
    db.query(Alert).filter(Alert.reviewed_by_user_id == user_id).update(
        {"reviewed_by_user_id": None}
    )

    user_name = target_user.full_name
    db.delete(target_user)
    db.commit()
    return {"message": f"User '{user_name}' deleted successfully."}

