import logging
from typing import List, Dict, Any
import gspread
import os
from google.oauth2.credentials import Credentials as UserCredentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from config import GOOGLE_SHEETS_ID

logger = logging.getLogger(__name__)

# --- New OAuth 2.0 Authentication ---
def get_oauth_credentials():
    """Gets user credentials using OAuth 2.0 flow."""
    creds = None
    # The file token.json stores the user's access and refresh tokens.
    if os.path.exists("token.json"):
        creds = UserCredentials.from_authorized_user_file("token.json")
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "client_secret.json",  # Make sure you have this file
                scopes=["https://www.googleapis.com/auth/spreadsheets"]
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return creds
# --- End of New Authentication ---

class GoogleSheetsService:
    """Service for interacting with Google Sheets for vendor data."""
    def __init__(self):
        try:
            # --- Use the new OAuth function ---
            creds = get_oauth_credentials()
            client = gspread.authorize(creds)
            if not GOOGLE_SHEETS_ID:
                raise ValueError("GOOGLE_SHEETS_ID is not set in the environment.")
            self.sheet = client.open_by_key(GOOGLE_SHEETS_ID).sheet1
            logger.info("Google Sheets connection established using OAuth.")
        except Exception as e:
            logger.error(f"Failed to initialize GoogleSheetsService: {e}")
            raise

    def get_vendor_data(self, vendor_name: str) -> List[Dict[str, Any]]:
        """Return all vendor records matching the vendor_name (case-insensitive substring match)."""
        try:
            records = self.sheet.get_all_records()
            vendor_rows = []
            for r in records:
                company_name = r.get("Nama Perusahaan", "")
                if isinstance(company_name, str) and vendor_name.lower() in company_name.lower():
                    vendor_rows.append(r)
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
                worksheet = self.sheet.spreadsheet.worksheet('Feedback')
            except Exception:
                worksheet = self.sheet
            worksheet.append_row([
                user, channel, thread_ts, feedback, question, answer
            ])
            logger.info(f"Appended feedback from user {user} to Google Sheets.")
        except Exception as e:
            logger.error(f"Error appending feedback: {e}") 