from datetime import datetime, date, timedelta, timezone
from typing import Optional, Dict, Any, Tuple, Set
from sqlalchemy.orm import Session

from backend.app.models.models import GSCProperty, DailyPageMetrics, SyncRun
from backend.app.services.gsc_service import GSCService
from backend.app.services.metric_service import normalize_url, get_latest_data_date
from backend.app.services.alert_service import evaluate_page_alerts
from backend.app.services.demo_data_service import seed_demo_dataset

def execute_synchronization(
    db: Session,
    property_id: int,
    triggered_by: str = "SYSTEM"
) -> Dict[str, Any]:
    """
    Executes a complete GSC synchronization run:
    1. Fetches daily page metrics from Google Search Console API (or seeds demo if demo property)
    2. Upserts metrics into DailyPageMetrics safely avoiding duplicates
    3. Triggers alert evaluation against new metrics
    4. Logs detailed SyncRun record
    """
    prop = db.query(GSCProperty).filter(GSCProperty.id == property_id).first()
    if not prop:
        raise ValueError(f"Property ID {property_id} not found.")

    start_time = datetime.now(timezone.utc)
    sync_run = SyncRun(
        property_id=prop.id,
        triggered_by=triggered_by,
        start_time=start_time,
        status="RUNNING"
    )
    db.add(sync_run)
    db.commit()
    db.refresh(sync_run)

    try:
        if prop.is_demo:
            # Handle demo property synchronization
            res = seed_demo_dataset(db)
            latest_date = get_latest_data_date(db, property_id=prop.id)
            
            sync_run.status = "SUCCESS"
            sync_run.end_time = datetime.now(timezone.utc)
            sync_run.pages_synced = res.get("pages_count", 0)
            sync_run.records_created = res.get("records_created", 0)
            sync_run.alerts_generated = res.get("alerts_generated", 0)
            sync_run.latest_data_date = latest_date
            sync_run.error_message = None
            db.commit()
            return {"status": "SUCCESS", "pages_synced": sync_run.pages_synced, "records": sync_run.records_created}

        # Real Google Search Console synchronization
        refresh_token = prop.refresh_token
        access_token = prop.access_token
        client_id = prop.client_id
        client_secret = prop.client_secret

        # If this property doesn't have tokens, check if another property in the database does
        if not refresh_token:
            auth_prop = db.query(GSCProperty).filter(
                GSCProperty.refresh_token.isnot(None),
                GSCProperty.refresh_token != ""
            ).order_by(GSCProperty.updated_at.desc()).first()
            if auth_prop:
                refresh_token = auth_prop.refresh_token
                access_token = auth_prop.access_token
                client_id = client_id or auth_prop.client_id
                client_secret = client_secret or auth_prop.client_secret
                prop.refresh_token = refresh_token
                prop.access_token = access_token
                prop.client_id = client_id
                prop.client_secret = client_secret
                db.commit()

        if not refresh_token:
            raise ValueError(f"Property '{prop.site_url}' has no active OAuth credentials. Please authorize Google Search Console in the GSC Connection tab.")

        # Resolve client_id and client_secret from database SystemSetting or settings
        from backend.app.core.config import settings
        from backend.app.services.settings_service import get_system_setting
        client_id = client_id or get_system_setting(db, "GOOGLE_CLIENT_ID", settings.GOOGLE_CLIENT_ID)
        client_secret = client_secret or get_system_setting(db, "GOOGLE_CLIENT_SECRET", settings.GOOGLE_CLIENT_SECRET)

        creds = GSCService.get_valid_credentials(
            refresh_token=refresh_token,
            access_token=access_token,
            client_id=client_id,
            client_secret=client_secret
        )
        if not creds:
            raise ValueError("Google OAuth credentials expired or invalid. Please re-authorize Google Search Console in the GSC Connection tab.")

        # Update cached access token or rotated refresh token
        tokens_changed = False
        if isinstance(getattr(creds, "token", None), str) and creds.token and creds.token != prop.access_token:
            prop.access_token = creds.token
            prop.token_expiry = getattr(creds, "expiry", None)
            tokens_changed = True
        if isinstance(getattr(creds, "refresh_token", None), str) and creds.refresh_token and creds.refresh_token != prop.refresh_token:
            prop.refresh_token = creds.refresh_token
            tokens_changed = True
        if tokens_changed:
            db.commit()

        # Date range: past 56 complete days (GSC standard latency is ~2-3 days)
        end_date = (date.today() - timedelta(days=2)).isoformat()
        start_date = (date.today() - timedelta(days=57)).isoformat()

        # Ingest metrics with pagination support
        records_upserted = 0
        unique_pages = set()
        start_row = 0
        batch_size = 5000
        touched_in_run: Set[Tuple[str, date]] = set()

        active_site_url = prop.site_url

        while True:
            try:
                batch_rows = GSCService.query_page_metrics(
                    credentials=creds,
                    site_url=active_site_url,
                    start_date=start_date,
                    end_date=end_date,
                    row_limit=batch_size,
                    start_row=start_row
                )
            except Exception as query_err:
                err_msg = str(query_err).lower()
                # On the first batch, auto-resolve with Google's verified sites if URL format differed
                if start_row == 0 and ("permission" in err_msg or "not found" in err_msg or "403" in err_msg or "404" in err_msg):
                    try:
                        verified_sites = GSCService.list_properties(creds)
                        clean_prop = prop.site_url.replace("sc-domain:", "").replace("https://", "").replace("http://", "").strip("/")
                        matched_url = None
                        for vs in verified_sites:
                            vs_url = vs.get("site_url", "")
                            vs_clean = vs_url.replace("sc-domain:", "").replace("https://", "").replace("http://", "").strip("/")
                            if vs_clean == clean_prop:
                                matched_url = vs_url
                                break
                        if not matched_url and verified_sites:
                            matched_url = verified_sites[0].get("site_url")
                        if matched_url and matched_url != active_site_url:
                            prop.site_url = matched_url
                            active_site_url = matched_url
                            db.commit()
                            batch_rows = GSCService.query_page_metrics(
                                credentials=creds,
                                site_url=active_site_url,
                                start_date=start_date,
                                end_date=end_date,
                                row_limit=batch_size,
                                start_row=start_row
                            )
                        else:
                            raise query_err
                    except Exception:
                        raise query_err
                else:
                    raise query_err

            if not batch_rows:
                break

            # Aggregate batch rows by (normalized_url, metric_date)
            # This handles cases where multiple URLs returned by GSC (e.g. trailing slashes, params)
            # normalize to the same URL for the same date.
            aggregated_rows: Dict[Tuple[str, date], Dict[str, Any]] = {}
            for r in batch_rows:
                norm_url = r["normalized_url"]
                unique_pages.add(norm_url)
                metric_date = datetime.strptime(r["date"], "%Y-%m-%d").date()
                key = (norm_url, metric_date)

                if key not in aggregated_rows:
                    aggregated_rows[key] = {
                        "page_url": r["page_url"],
                        "normalized_url": norm_url,
                        "date": metric_date,
                        "clicks": r["clicks"],
                        "impressions": r["impressions"],
                        "pos_imp_sum": r["position"] * r["impressions"],
                    }
                else:
                    agg = aggregated_rows[key]
                    agg["clicks"] += r["clicks"]
                    agg["impressions"] += r["impressions"]
                    agg["pos_imp_sum"] += r["position"] * r["impressions"]

            for (norm_url, metric_date), agg in aggregated_rows.items():
                total_clicks = agg["clicks"]
                total_impressions = agg["impressions"]
                ctr = (total_clicks / total_impressions * 100.0) if total_impressions > 0 else 0.0
                position = (agg["pos_imp_sum"] / total_impressions) if total_impressions > 0 else 0.0

                # Check for existing record in database
                existing = db.query(DailyPageMetrics).filter(
                    DailyPageMetrics.property_id == prop.id,
                    DailyPageMetrics.normalized_url == norm_url,
                    DailyPageMetrics.date == metric_date
                ).first()

                if existing:
                    if (norm_url, metric_date) in touched_in_run:
                        # Variant spanned across batches in this run - accumulate
                        combined_clicks = existing.clicks + total_clicks
                        combined_imp = existing.impressions + total_impressions
                        pos_sum = (existing.position * existing.impressions) + agg["pos_imp_sum"]
                        existing.clicks = combined_clicks
                        existing.impressions = combined_imp
                        existing.ctr = (combined_clicks / combined_imp * 100.0) if combined_imp > 0 else 0.0
                        existing.position = (pos_sum / combined_imp) if combined_imp > 0 else existing.position
                    else:
                        # First time seeing this in this sync run - overwrite with fresh data
                        existing.clicks = total_clicks
                        existing.impressions = total_impressions
                        existing.ctr = ctr
                        existing.position = position
                        existing.page_url = agg["page_url"]
                        existing.is_synthetic = False
                        touched_in_run.add((norm_url, metric_date))
                else:
                    db.add(DailyPageMetrics(
                        property_id=prop.id,
                        page_url=agg["page_url"],
                        normalized_url=norm_url,
                        date=metric_date,
                        clicks=total_clicks,
                        impressions=total_impressions,
                        ctr=ctr,
                        position=position,
                        is_synthetic=False
                    ))
                    touched_in_run.add((norm_url, metric_date))

                records_upserted += 1

            db.commit()
            if len(batch_rows) < batch_size:
                break
            start_row += batch_size

        latest_data_date = get_latest_data_date(db, property_id=prop.id)
        
        # Evaluate alerts for all mapped pages
        alerts_count = evaluate_page_alerts(db, property_id=prop.id, evaluation_date=latest_data_date)

        sync_run.status = "SUCCESS"
        sync_run.end_time = datetime.now(timezone.utc)
        sync_run.pages_synced = len(unique_pages)
        sync_run.records_created = records_upserted
        sync_run.alerts_generated = alerts_count
        sync_run.latest_data_date = latest_data_date
        sync_run.error_message = None
        db.commit()

        return {
            "status": "SUCCESS",
            "pages_synced": len(unique_pages),
            "records_upserted": records_upserted,
            "alerts_generated": alerts_count,
            "latest_data_date": str(latest_data_date)
        }

    except Exception as e:
        db.rollback()
        sync_run.status = "FAILED"
        sync_run.end_time = datetime.now(timezone.utc)
        sync_run.error_message = str(e)
        try:
            db.commit()
        except Exception:
            db.rollback()
        raise e

