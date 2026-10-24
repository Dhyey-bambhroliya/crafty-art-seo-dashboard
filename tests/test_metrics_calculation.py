import pytest
from backend.app.services.metric_service import normalize_url, calculate_comparison_metrics

def test_normalize_url():
    # Test tracking params removal
    url1 = "https://craftyartapp.com/invitation-maker?utm_source=google&utm_medium=cpc#section1"
    assert normalize_url(url1) == "https://craftyartapp.com/invitation-maker"

    # Test trailing slash normalization
    url2 = "https://craftyartapp.com/templates/wedding-invitations/"
    assert normalize_url(url2) == "https://craftyartapp.com/templates/wedding-invitations"

    # Test root domain keeping slash
    url3 = "https://craftyartapp.com/"
    assert normalize_url(url3) == "https://craftyartapp.com/"

    # Test case insensitive scheme and host
    url4 = "HTTPS://CraftyArtApp.COM/Flyer-Maker"
    assert normalize_url(url4) == "https://craftyartapp.com/Flyer-Maker"

def test_calculate_comparison_metrics():
    # Current: 1000 clicks, 20000 impressions, pos_imp_sum = 60000 (avg pos = 3.0)
    # Previous: 1250 clicks, 25000 impressions, pos_imp_sum = 100000 (avg pos = 4.0)
    comp = calculate_comparison_metrics(
        curr_clicks=1000,
        curr_impressions=20000,
        curr_pos_imp_sum=60000.0,
        prev_clicks=1250,
        prev_impressions=25000,
        prev_pos_imp_sum=100000.0
    )

    # Click decline: (1000 - 1250) / 1250 = -20%
    assert comp.click_diff == -250
    assert comp.click_pct_change == -20.0

    # Impression decline: (20000 - 25000) / 25000 = -20%
    assert comp.impression_diff == -5000
    assert comp.impression_pct_change == -20.0

    # CTR: Current 5.0%, Previous 5.0%
    assert comp.current.ctr == 5.0
    assert comp.previous.ctr == 5.0

    # Weighted Average Position:
    # Current = 60000 / 20000 = 3.0
    # Previous = 100000 / 25000 = 4.0
    # Pos diff = 3.0 - 4.0 = -1.0 (Improved rank!)
    assert comp.current.position == 3.0
    assert comp.previous.position == 4.0
    assert comp.position_diff == -1.0
    assert comp.position_status == "IMPROVED"
