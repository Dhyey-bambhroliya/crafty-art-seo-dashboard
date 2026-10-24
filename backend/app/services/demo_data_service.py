import random
import math
from datetime import date, datetime, timedelta, timezone
from typing import List, Dict, Tuple, Optional, Any
from sqlalchemy.orm import Session

from backend.app.models.models import (
    User, UserRole, GSCProperty, Category, CategoryPage, DailyPageMetrics, SyncRun
)
from backend.app.core.security import hash_password
from backend.app.services.metric_service import normalize_url
from backend.app.services.alert_service import evaluate_page_alerts

CRAFTY_ART_CATEGORIES = [
    {
        "name": "Invitation Templates & Cards",
        "description": "High-intent digital and printable invitations for weddings, birthdays, and celebrations.",
        "leader_email": "priya.sharma@craftyartapp.com",
        "leader_name": "Priya Sharma",
        "pages": [
            ("https://craftyartapp.com/invitation-maker", "stable_growth", 850, 18500, 3.8),
            ("https://craftyartapp.com/templates/wedding-invitations", "growing", 640, 12800, 4.2),
            ("https://craftyartapp.com/templates/birthday-invitations", "declining_warning", 410, 9200, 6.5),  # ~12% decline
            ("https://craftyartapp.com/templates/baby-shower-invitations", "declining_critical", 320, 7100, 8.1), # ~24% decline
            ("https://craftyartapp.com/templates/save-the-date", "position_drop", 290, 6400, 5.0), # rank drop to 8.8
            ("https://craftyartapp.com/templates/anniversary-cards", "growing", 220, 4800, 7.3),
            ("https://craftyartapp.com/templates/party-invitations", "stable", 380, 8100, 5.9),
            ("https://craftyartapp.com/templates/graduation-invitations", "stable", 180, 3900, 9.1),
        ]
    },
    {
        "name": "Flyer & Poster Maker",
        "description": "Print and digital promotional flyers and event posters for SMBs and organizations.",
        "leader_email": "rahul.verma@craftyartapp.com",
        "leader_name": "Rahul Verma",
        "pages": [
            ("https://craftyartapp.com/flyer-maker", "stable_growth", 920, 21000, 3.2),
            ("https://craftyartapp.com/templates/business-flyers", "declining_critical", 550, 13400, 4.8), # ~22% decline
            ("https://craftyartapp.com/poster-maker", "growing", 780, 16800, 3.9),
            ("https://craftyartapp.com/templates/event-posters", "declining_warning", 340, 7900, 7.2), # ~14% decline
            ("https://craftyartapp.com/templates/music-concert-flyers", "stable", 210, 4600, 8.4),
            ("https://craftyartapp.com/templates/real-estate-flyers", "growing", 430, 9800, 5.1),
            ("https://craftyartapp.com/templates/hiring-posters", "position_drop", 195, 4200, 6.2), # rank drop to 9.7
        ]
    },
    {
        "name": "Social Media Graphics & Banners",
        "description": "Graphics for YouTube, Instagram, Facebook, and LinkedIn creators and brands.",
        "leader_email": "priya.sharma@craftyartapp.com",
        "leader_name": "Priya Sharma",
        "pages": [
            ("https://craftyartapp.com/banner-maker", "growing", 1100, 25000, 2.9),
            ("https://craftyartapp.com/youtube-thumbnail-maker", "growing", 1450, 31000, 2.4),
            ("https://craftyartapp.com/templates/instagram-story-templates", "declining_warning", 620, 14200, 5.5), # ~11% decline
            ("https://craftyartapp.com/templates/linkedin-banners", "stable", 310, 6800, 6.8),
            ("https://craftyartapp.com/templates/facebook-covers", "declining_critical", 280, 6100, 8.3), # ~25% decline
            ("https://craftyartapp.com/templates/podcast-cover-art", "growing", 240, 5200, 7.9),
        ]
    },
    {
        "name": "Brochures & Marketing Collateral",
        "description": "Bi-fold, tri-fold brochures, restaurant menus, and corporate sales sheets.",
        "leader_email": "rahul.verma@craftyartapp.com",
        "leader_name": "Rahul Verma",
        "pages": [
            ("https://craftyartapp.com/brochure-maker", "growing", 680, 15000, 4.1),
            ("https://craftyartapp.com/templates/trifold-brochures", "stable", 420, 9400, 5.6),
            ("https://craftyartapp.com/menu-maker", "declining_critical", 590, 12900, 4.4), # ~21% decline
            ("https://craftyartapp.com/templates/restaurant-menus", "declining_warning", 330, 7200, 6.7), # ~13% decline
            ("https://craftyartapp.com/templates/catalogs", "growing", 210, 4700, 7.5),
        ]
    }
]

def seed_demo_dataset(db: Session, manager_user_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Seeds complete, realistic demonstration data for Crafty Art.
    Clearly marks all data as is_synthetic=True and property is_demo=True.
    """
    # 1. Create or get Demo GSC Property
    demo_prop = db.query(GSCProperty).filter(GSCProperty.site_url == "sc-domain:craftyartapp.com").first()
    if not demo_prop:
        demo_prop = GSCProperty(
            site_url="sc-domain:craftyartapp.com",
            permission_level="siteOwner",
            is_active=True,
            is_demo=True,
            connected_by_user_id=manager_user_id
        )
        db.add(demo_prop)
        db.commit()
        db.refresh(demo_prop)

    # 2. Create or verify Team Leaders
    leaders_map = {}
    default_password_hash = hash_password("TeamLeader@2026")
    
    for cat_spec in CRAFTY_ART_CATEGORIES:
        email = cat_spec["leader_email"]
        if email not in leaders_map:
            user = db.query(User).filter(User.email == email).first()
            if not user:
                user = User(
                    email=email,
                    full_name=cat_spec["leader_name"],
                    hashed_password=default_password_hash,
                    role=UserRole.TEAM_LEADER,
                    is_active=True
                )
                db.add(user)
                db.commit()
                db.refresh(user)
            leaders_map[email] = user

    # 3. Create Categories and Category Pages
    all_pages_spec = []
    for cat_spec in CRAFTY_ART_CATEGORIES:
        leader = leaders_map[cat_spec["leader_email"]]
        category = db.query(Category).filter(Category.name == cat_spec["name"]).first()
        if not category:
            category = Category(
                name=cat_spec["name"],
                description=cat_spec["description"],
                assigned_leader_id=leader.id,
                status="ACTIVE"
            )
            db.add(category)
            db.commit()
            db.refresh(category)
        
        for full_url, behavior, base_clicks, base_imps, base_pos in cat_spec["pages"]:
            norm_url = normalize_url(full_url)
            page = db.query(CategoryPage).filter(
                CategoryPage.category_id == category.id,
                CategoryPage.normalized_url == norm_url
            ).first()
            if not page:
                page = CategoryPage(
                    category_id=category.id,
                    full_url=full_url,
                    normalized_url=norm_url,
                    status="ACTIVE"
                )
                db.add(page)
            all_pages_spec.append((full_url, norm_url, behavior, base_clicks, base_imps, base_pos))
    
    db.commit()

    # 4. Generate 56 Days of Daily Page Metrics
    # Latest complete data date = 2 days ago
    latest_date = date.today() - timedelta(days=2)
    start_date = latest_date - timedelta(days=55)  # 56 complete days
    
    # Check if metrics already seeded
    existing_count = db.query(DailyPageMetrics).filter(
        DailyPageMetrics.property_id == demo_prop.id,
        DailyPageMetrics.is_synthetic == True
    ).count()
    
    records_created = 0
    if existing_count == 0:
        random.seed(42)  # Deterministic realistic curves
        metrics_to_insert = []
        
        for full_url, norm_url, behavior, base_clicks_28d, base_imps_28d, base_pos in all_pages_spec:
            # Base daily averages
            daily_avg_clicks = base_clicks_28d / 28.0
            daily_avg_imps = base_imps_28d / 28.0
            
            day_idx = 0
            curr_date = start_date
            while curr_date <= latest_date:
                # Day of week factor (weekday vs weekend)
                weekday = curr_date.weekday()
                weekend_factor = 0.85 if weekday in [5, 6] else 1.05
                
                # Determine multiplier based on behavior
                # First 28 days = previous period; second 28 days = current period
                is_current_period = (curr_date > (latest_date - timedelta(days=28)))
                
                if behavior == "growing":
                    mult = 1.25 if is_current_period else 1.0
                    pos_shift = -0.6 if is_current_period else 0.0
                elif behavior == "declining_warning":
                    mult = 0.87 if is_current_period else 1.0  # -13% clicks
                    pos_shift = 0.4 if is_current_period else 0.0
                elif behavior == "declining_critical":
                    mult = 0.76 if is_current_period else 1.0  # -24% clicks
                    pos_shift = 0.9 if is_current_period else 0.0
                elif behavior == "position_drop":
                    mult = 0.82 if is_current_period else 1.0
                    pos_shift = 3.6 if is_current_period else 0.0 # +3.6 drop in rank
                else:  # stable / stable_growth
                    mult = 1.04 if is_current_period else 1.0
                    pos_shift = -0.1 if is_current_period else 0.0
                
                noise = random.uniform(0.92, 1.08)
                day_clicks = max(1, int(daily_avg_clicks * mult * weekend_factor * noise))
                day_imps = max(day_clicks * 5, int(daily_avg_imps * mult * weekend_factor * noise))
                ctr = round((day_clicks / day_imps) * 100.0, 2)
                pos = round(max(1.0, base_pos + pos_shift + random.uniform(-0.3, 0.3)), 2)
                
                metrics_to_insert.append(DailyPageMetrics(
                    property_id=demo_prop.id,
                    page_url=full_url,
                    normalized_url=norm_url,
                    date=curr_date,
                    clicks=day_clicks,
                    impressions=day_imps,
                    ctr=ctr,
                    position=pos,
                    is_synthetic=True
                ))
                records_created += 1
                curr_date += timedelta(days=1)
                day_idx += 1
        
        # Batch insert
        db.bulk_save_objects(metrics_to_insert)
        db.commit()

    # 5. Evaluate Alerts for Demo dataset
    alerts_generated = evaluate_page_alerts(db, property_id=demo_prop.id, evaluation_date=latest_date)

    # 6. Record Sync Run
    sync_run = SyncRun(
        property_id=demo_prop.id,
        triggered_by="DEMO_SEED_SERVICE",
        start_time=datetime.now(timezone.utc) - timedelta(minutes=1),
        end_time=datetime.now(timezone.utc),
        status="SUCCESS",
        pages_synced=len(all_pages_spec),
        records_created=records_created,
        alerts_generated=alerts_generated,
        latest_data_date=latest_date,
        error_message=None
    )
    db.add(sync_run)
    db.commit()

    return {
        "status": "success",
        "message": "Demo data initialized successfully with realistic Crafty Art metrics and alerts.",
        "property": demo_prop.site_url,
        "categories_count": len(CRAFTY_ART_CATEGORIES),
        "pages_count": len(all_pages_spec),
        "records_created": records_created,
        "alerts_generated": alerts_generated,
        "latest_data_date": str(latest_date)
    }

def purge_demo_dataset(db: Session, purge_all: bool = False, keep_manager_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Purges synthetic Crafty Art demonstration data so the user can operate with clean real data.
    - If purge_all is False: Only purges demo properties, synthetic metrics, demo categories, demo alerts, and demo team leaders.
    - If purge_all is True: Resets all categories, pages, metrics, properties, and alerts, keeping only the Manager account.
    """
    from backend.app.models.models import Alert

    deleted_counts = {}

    if purge_all:
        # Full workspace reset (wipes everything except the Manager)
        deleted_counts["metrics"] = db.query(DailyPageMetrics).delete()
        deleted_counts["alerts"] = db.query(Alert).delete()
        deleted_counts["pages"] = db.query(CategoryPage).delete()
        deleted_counts["categories"] = db.query(Category).delete()
        deleted_counts["sync_runs"] = db.query(SyncRun).delete()
        deleted_counts["properties"] = db.query(GSCProperty).delete()
        
        # Delete all non-manager users or users other than keep_manager_id
        user_query = db.query(User).filter(User.role != UserRole.MANAGER)
        if keep_manager_id:
            user_query = user_query.filter(User.id != keep_manager_id)
        deleted_counts["users"] = user_query.delete()
        
        db.commit()
        return {
            "status": "success",
            "message": "Entire workspace cleared successfully. You can now configure your real Search Console properties and team from scratch.",
            "deleted": deleted_counts
        }

    # Targeted Demo Purge:
    # 1. Identify demo properties
    demo_props = db.query(GSCProperty).filter(
        (GSCProperty.is_demo == True) | (GSCProperty.site_url == "sc-domain:craftyartapp.com")
    ).all()
    demo_prop_ids = [p.id for p in demo_props]

    # 2. Delete synthetic metrics
    deleted_counts["metrics"] = db.query(DailyPageMetrics).filter(
        (DailyPageMetrics.is_synthetic == True) | (DailyPageMetrics.property_id.in_(demo_prop_ids))
    ).delete(synchronize_session=False)

    # 3. Delete demo categories and their pages
    demo_cat_names = [c["name"] for c in CRAFTY_ART_CATEGORIES]
    demo_cats = db.query(Category).filter(Category.name.in_(demo_cat_names)).all()
    demo_cat_ids = [c.id for c in demo_cats]

    # Delete alerts referencing demo categories or demo pages
    deleted_counts["alerts"] = db.query(Alert).filter(
        (Alert.category_id.in_(demo_cat_ids)) | (Alert.assigned_leader_id.in_([
            u.id for u in db.query(User.id).filter(User.email.in_(["priya.sharma@craftyartapp.com", "rahul.verma@craftyartapp.com"])).all()
        ]))
    ).delete(synchronize_session=False)

    deleted_counts["pages"] = db.query(CategoryPage).filter(
        CategoryPage.category_id.in_(demo_cat_ids)
    ).delete(synchronize_session=False)

    deleted_counts["categories"] = db.query(Category).filter(
        Category.id.in_(demo_cat_ids)
    ).delete(synchronize_session=False)

    # 4. Delete demo sync runs
    deleted_counts["sync_runs"] = db.query(SyncRun).filter(
        SyncRun.property_id.in_(demo_prop_ids)
    ).delete(synchronize_session=False)

    # 5. Delete demo properties
    deleted_counts["properties"] = db.query(GSCProperty).filter(
        GSCProperty.id.in_(demo_prop_ids)
    ).delete(synchronize_session=False)

    # 6. Delete demo team leaders (Priya & Rahul)
    deleted_counts["users"] = db.query(User).filter(
        User.email.in_(["priya.sharma@craftyartapp.com", "rahul.verma@craftyartapp.com"])
    ).delete(synchronize_session=False)

    db.commit()
    return {
        "status": "success",
        "message": "Demo test data removed successfully! You can now connect your verified Search Console property and add your real categories.",
        "deleted": deleted_counts
    }
