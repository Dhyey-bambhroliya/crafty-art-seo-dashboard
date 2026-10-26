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
    Ensures all 6 authorized Team Leaders exist in the database with role=TEAM_LEADER
    and password set to '12345678'.
    Runs automatically on application startup so it works seamlessly on Supabase & locally.
    """
    updated_or_created = 0
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
            updated_or_created += 1
            logger.info(f"Created Team Leader account: {email}")
        else:
            # Update password to '12345678' and ensure team leader role & active status
            user.hashed_password = hashed_pwd
            user.role = UserRole.TEAM_LEADER
            user.is_active = True
            if not user.full_name or user.full_name.startswith("User"):
                user.full_name = full_name
            updated_or_created += 1
            logger.info(f"Updated Team Leader credentials for: {email}")

    # Ensure manager@craftyart.com also exists with password '12345678'
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
            updated_or_created += 1
            logger.info("Created default Manager account: manager@craftyart.com")
    else:
        manager.hashed_password = hashed_pwd
        logger.info("Updated Manager credentials for: manager@craftyart.com")

    db.commit()
    return updated_or_created
