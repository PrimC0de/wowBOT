import logging
from typing import List, Dict, Any
import gspread
from google.oauth2.service_account import Credentials
from config import GOOGLE_SHEETS_CREDENTIALS, GOOGLE_SHEETS_ID

logger = logging.getLogger(__name__)

class GoogleSheetsService:
    """Service for interacting with Google Sheets for procurement data."""
    def __init__(self):
        try:
            scopes = ["https://www.googleapis.com/auth/spreadsheets"]
            creds = Credentials.from_service_account_file(GOOGLE_SHEETS_CREDENTIALS, scopes=scopes)
            client = gspread.authorize(creds)
            self.spreadsheet = client.open_by_key(GOOGLE_SHEETS_ID)
            logger.info("Google Sheets connection established.")
        except Exception as e:
            logger.error(f"Failed to initialize GoogleSheetsService: {e}")
            raise

    def get_sheet_data(self, sheet_name: str) -> List[Dict[str, Any]]:
        """Return all records from the specified worksheet as a list of dicts."""
        try:
            worksheet = self.spreadsheet.worksheet(sheet_name)
            records = worksheet.get_all_records()
            logger.info(f"Fetched {len(records)} records from sheet '{sheet_name}'.")
            return records
        except Exception as e:
            logger.error(f"Error retrieving data from sheet '{sheet_name}': {e}")
            return []

    def get_vendor_data(self, vendor_name: str) -> List[Dict[str, Any]]:
        """Return all vendor records matching the vendor_name (case-insensitive substring match) from the default sheet."""
        try:
            worksheet = self.spreadsheet.sheet1
            records = worksheet.get_all_records()
            vendor_rows = [r for r in records if vendor_name.lower() in r.get("Nama Perusahaan", "").lower()]
            logger.info(f"Found {len(vendor_rows)} records for vendor '{vendor_name}'.")
            return vendor_rows
        except Exception as e:
            logger.error(f"Error retrieving vendor data: {e}")
            return []

    def append_feedback(self, user: str, channel: str, thread_ts: str, feedback: str, question: str, answer: str):
        """Append a feedback entry to the Feedback worksheet (or main sheet if Feedback does not exist)."""
        try:
            # Try to use a worksheet named 'Feedback', else use the main sheet
            try:
                worksheet = self.spreadsheet.worksheet('Feedback')
            except Exception:
                worksheet = self.spreadsheet.sheet1
            worksheet.append_row([
                user, channel, thread_ts, feedback, question, answer
            ])
            logger.info(f"Appended feedback from user {user} to Google Sheets.")
        except Exception as e:
            logger.error(f"Error appending feedback: {e}") 