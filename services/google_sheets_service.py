import logging
from typing import List, Dict, Any
import gspread
from google.oauth2.service_account import Credentials
from config import GOOGLE_SHEETS_CREDENTIALS, GOOGLE_SHEETS_ID

logger = logging.getLogger(__name__)

class GoogleSheetsService:
    """Service for interacting with Google Sheets for vendor data."""
    def __init__(self):
        try:
            scopes = ["https://www.googleapis.com/auth/spreadsheets"]
            creds = Credentials.from_service_account_file(GOOGLE_SHEETS_CREDENTIALS, scopes=scopes)
            client = gspread.authorize(creds)
            self.sheet = client.open_by_key(GOOGLE_SHEETS_ID).sheet1
            logger.info("Google Sheets connection established.")
        except Exception as e:
            logger.error(f"Failed to initialize GoogleSheetsService: {e}")
            raise

    def get_vendor_data(self, vendor_name: str) -> List[Dict[str, Any]]:
        """Return all vendor records matching the vendor_name (case-insensitive substring match)."""
        try:
            records = self.sheet.get_all_records()
            vendor_rows = [r for r in records if vendor_name.lower() in r.get("Nama Perusahaan", "").lower()]
            logger.info(f"Found {len(vendor_rows)} records for vendor '{vendor_name}'.")
            return vendor_rows
        except Exception as e:
            logger.error(f"Error retrieving vendor data: {e}")
            return [] 