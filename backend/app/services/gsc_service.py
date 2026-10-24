from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Any
import requests
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from backend.app.core.config import settings
from backend.app.services.metric_service import normalize_url

SCOPES = [settings.GSC_READONLY_SCOPE]

class GSCService:
    @staticmethod
    def get_oauth_flow(redirect_uri: Optional[str] = None) -> Optional[Flow]:
        """Creates standard Google OAuth Flow using backend environment configuration."""
        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
            return None
        
        client_config = {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [redirect_uri or settings.GOOGLE_REDIRECT_URI]
            }
        }
        
        flow = Flow.from_client_config(
            client_config,
            scopes=SCOPES,
            redirect_uri=redirect_uri or settings.GOOGLE_REDIRECT_URI
        )
        return flow

    @staticmethod
    def generate_authorization_url(redirect_uri: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
        """
        Returns (auth_url, state)
        Uses access_type='offline' and prompt='consent' so Google returns a refresh token.
        """
        flow = GSCService.get_oauth_flow(redirect_uri)
        if not flow:
            return None, "Google Client ID or Client Secret not configured in environment."
        
        auth_url, state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent"
        )
        return auth_url, None

    @staticmethod
    def exchange_code(code: str, redirect_uri: Optional[str] = None) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Exchanges authorization code for credentials tokens server-side."""
        flow = GSCService.get_oauth_flow(redirect_uri)
        if not flow:
            return None, "Google OAuth not configured."
        
        try:
            flow.fetch_token(code=code)
            credentials = flow.credentials
            
            token_data = {
                "access_token": credentials.token,
                "refresh_token": credentials.refresh_token,
                "token_expiry": credentials.expiry,
                "client_id": credentials.client_id,
                "client_secret": credentials.client_secret,
            }
            return token_data, None
        except Exception as e:
            return None, f"Token exchange failed: {str(e)}"

    @staticmethod
    def get_valid_credentials(
        refresh_token: str,
        access_token: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None
    ) -> Optional[Credentials]:
        """Constructs Google Credentials and refreshes access token if needed."""
        cid = client_id or settings.GOOGLE_CLIENT_ID
        csec = client_secret or settings.GOOGLE_CLIENT_SECRET
        
        creds = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=cid,
            client_secret=csec,
            scopes=SCOPES
        )
        
        if not access_token or creds.expired:
            try:
                from google.auth.transport.requests import Request
                creds.refresh(Request())
            except Exception:
                return None
        
        return creds

    @staticmethod
    def list_properties(credentials: Credentials) -> List[Dict[str, str]]:
        """
        Retrieves all accessible Search Console properties (Domain and URL-prefix).
        Returns list of dicts: [{'site_url': '...', 'permission_level': '...'}]
        """
        try:
            service = build("searchconsole", "v1", credentials=credentials, cache_discovery=False)
            result = service.sites().list().execute()
            site_entries = result.get("siteEntry", [])
            
            properties = []
            for entry in site_entries:
                properties.append({
                    "site_url": entry.get("siteUrl", ""),
                    "permission_level": entry.get("permissionLevel", "siteRestrictedUser")
                })
            return properties
        except HttpError as e:
            raise RuntimeError(f"GSC API error fetching sites: {e.reason}")
        except Exception as e:
            raise RuntimeError(f"Error fetching GSC sites: {str(e)}")

    @staticmethod
    def query_page_metrics(
        credentials: Credentials,
        site_url: str,
        start_date: str,
        end_date: str,
        row_limit: int = 25000,
        start_row: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Queries Search Analytics API with page and date dimensions.
        Returns list of metric rows:
        [{ 'page_url': '...', 'normalized_url': '...', 'date': 'YYYY-MM-DD', 'clicks': x, 'impressions': y, 'ctr': z, 'position': w }]
        """
        try:
            service = build("searchconsole", "v1", credentials=credentials, cache_discovery=False)
            request_body = {
                "startDate": start_date,
                "endDate": end_date,
                "dimensions": ["page", "date"],
                "rowLimit": row_limit,
                "startRow": start_row,
                "aggregationType": "byPage"
            }
            
            response = service.searchanalytics().query(siteUrl=site_url, body=request_body).execute()
            rows = response.get("rows", [])
            
            parsed_rows = []
            for row in rows:
                keys = row.get("keys", [])
                if len(keys) >= 2:
                    page_url = keys[0]
                    date_str = keys[1]
                    clicks = int(row.get("clicks", 0))
                    impressions = int(row.get("impressions", 0))
                    ctr = float(row.get("ctr", 0.0)) * 100.0  # Convert to percentage
                    position = float(row.get("position", 0.0))
                    
                    parsed_rows.append({
                        "page_url": page_url,
                        "normalized_url": normalize_url(page_url),
                        "date": date_str,
                        "clicks": clicks,
                        "impressions": impressions,
                        "ctr": ctr,
                        "position": position
                    })
            
            return parsed_rows
        except HttpError as e:
            raise RuntimeError(f"GSC Analytics Query error: {e.reason} (Status {e.resp.status})")
        except Exception as e:
            raise RuntimeError(f"Failed querying Search Console: {str(e)}")
