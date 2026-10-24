import pytest
from datetime import date
from unittest.mock import patch, MagicMock
from backend.app.models.models import GSCProperty, DailyPageMetrics
from backend.app.services.sync_service import execute_synchronization

def test_sync_deduplicates_and_aggregates_same_day_variants(db_session):
    """
    Ensures that when Google Search Console returns multiple URLs that normalize
    to the same URL on the same date (e.g. trailing slash vs no trailing slash),
    the sync engine aggregates them without throwing SQLite UNIQUE constraint errors.
    """
    db = db_session
    # Create test property
    prop = GSCProperty(
        site_url="https://www.craftyartapp.com/",
        permission_level="siteOwner",
        is_demo=False,
        refresh_token="mock_refresh",
        access_token="mock_access",
        client_id="mock_client",
        client_secret="mock_secret"
    )
    db.add(prop)
    db.commit()
    db.refresh(prop)

    # Mock GSCService.get_valid_credentials and query_page_metrics
    mock_creds = MagicMock()
    mock_creds.token = "mock_access"
    mock_creds.expiry = None

    # Return two distinct URLs on the same date that normalize to 'https://craftyartapp.com/templates'
    mock_rows = [
        {
            "page_url": "https://www.craftyartapp.com/templates",
            "normalized_url": "https://craftyartapp.com/templates",
            "date": "2026-09-15",
            "clicks": 2,
            "impressions": 9,
            "ctr": 22.22,
            "position": 2.7
        },
        {
            "page_url": "https://www.craftyartapp.com/templates/",
            "normalized_url": "https://craftyartapp.com/templates",
            "date": "2026-09-15",
            "clicks": 5,
            "impressions": 20,
            "ctr": 25.0,
            "position": 3.1
        }
    ]

    with patch("backend.app.services.sync_service.GSCService.get_valid_credentials", return_value=mock_creds):
        with patch("backend.app.services.sync_service.GSCService.query_page_metrics", side_effect=[mock_rows, []]):
            result = execute_synchronization(db, prop.id, triggered_by="TEST")

    assert result["status"] == "SUCCESS"
    assert result["records_upserted"] == 1

    # Verify database record
    stored = db.query(DailyPageMetrics).filter(
        DailyPageMetrics.property_id == prop.id,
        DailyPageMetrics.normalized_url == "https://craftyartapp.com/templates"
    ).all()

    assert len(stored) == 1
    record = stored[0]
    assert record.clicks == 7  # 2 + 5
    assert record.impressions == 29  # 9 + 20
    assert record.date == date(2026, 9, 15)
