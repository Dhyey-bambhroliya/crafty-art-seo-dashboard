import logging
from typing import List, Dict
from sqlalchemy.orm import Session
from backend.app.models.models import User, UserRole
from backend.app.core.security import hash_password

logger = logging.getLogger("crafty_art_users")

INITIAL_TEAM_LEADERS: List[Dict[str, str]] = [
    {"email": "craftyartvishal@gmail.com", "full_name": "Vishal"},
    {"email": "goyanisumit09@gmail.com", "full_name": "Sumit Goyani"},
    {"email": "krushivaghani4@gmail.com", "full_name": "Krushi Vaghani"},
    {"email": "roshaniinfi@gmail.com", "full_name": "Roshani"},
    {"email": "zadafiyaurvi@gmail.com", "full_name": "Urvi Zadafiya"},
    {"email": "princybadhanicrafty@gmail.com", "full_name": "Princy Badhani"},
]

DEFAULT_TEAM_LEADER_PASSWORD = "12345678"

def seed_team_leaders(db: Session) -> int:
    """
    Ensures all 6 authorized Team Leaders exist in the database with role=TEAM_LEADER.
    SAFE IDEMPOTENCY:
    - If user does not exist, creates the account with initial default password.
    - If user already exists:
      * NEVER overwrites user's existing hashed_password with default password.
      * NEVER alters user's existing role.
      * NEVER resets user's existing is_active status (respects administrative deactivation).
      * Only populates full_name if empty or generic placeholder.
    """
    created_or_updated = 0
    hashed_pwd = hash_password(DEFAULT_TEAM_LEADER_PASSWORD)

    for leader in INITIAL_TEAM_LEADERS:
        email = leader["email"].strip().lower()
        full_name = leader["full_name"].strip()
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(
                email=email,
                full_name=full_name,
                hashed_password=hashed_pwd,
                role=UserRole.TEAM_LEADER,
                is_active=True
            )
            db.add(user)
            created_or_updated += 1
            logger.info(f"Created Team Leader account: {email}")
        else:
            # SAFE: Preserve existing password, role, and active status.
            # Never overwrite existing password with default password.
            if not user.hashed_password:
                user.hashed_password = hashed_pwd
                created_or_updated += 1
            if not user.full_name or user.full_name.startswith("User"):
                user.full_name = full_name
                created_or_updated += 1

    # Check for manager account safely
    manager = db.query(User).filter(User.email == "manager@craftyart.com").first()
    if not manager:
        existing_mgr = db.query(User).filter(User.role == UserRole.MANAGER).first()
        if not existing_mgr:
            manager = User(
                email="manager@craftyart.com",
                full_name="Crafty Art Manager",
                hashed_password=hashed_pwd,
                role=UserRole.MANAGER,
                is_active=True
            )
            db.add(manager)
            created_or_updated += 1
            logger.info("Created default Manager account: manager@craftyart.com")
    else:
        # SAFE: Preserve manager's existing password, role, and active status.
        if not manager.hashed_password:
            manager.hashed_password = hashed_pwd
            created_or_updated += 1

    db.commit()
    return created_or_updated
